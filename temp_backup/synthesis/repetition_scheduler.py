"""
Spaced repetition scheduling service
"""

import math
import random
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.synthesis.repetition_models import (
    LearningCurve,
    MemoryStrength,
    OptimalReviewTime,
    RepetitionAlgorithm,
    RepetitionSettings,
    ReviewDifficulty,
    ReviewHistory,
    ReviewResult,
    ReviewSession,
    ReviewStatistics,
    ReviewStatus,
    ScheduledReview,
)
from app.services.memory_service import MemoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SpacedRepetitionScheduler:
    """Service for spaced repetition scheduling and tracking"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
        self.default_settings = self._get_default_settings()

    def _get_default_settings(self) -> RepetitionSettings:
        """Get default repetition settings"""
        return RepetitionSettings(
            user_id="default",
            algorithm=RepetitionAlgorithm.SM2,
            daily_review_limit=20,
            new_memories_per_day=10,
            initial_ease=2.5,
            learning_steps=[1, 10],
            relearning_steps=[10]
        )

    async def schedule_review(
        self,
        user_id: str,
        memory_id: UUID,
        algorithm: Optional[RepetitionAlgorithm] = None
    ) -> ScheduledReview:
        """Schedule a review for a memory"""
        try:
            # Get user settings
            settings = await self._get_user_settings(user_id)
            algorithm = algorithm or settings.algorithm

            # Get memory
            memory = await self.memory_service.get_memory(user_id, memory_id)
            if not memory:
                raise ValueError(f"Memory {memory_id} not found")

            # Calculate initial interval based on importance
            initial_interval = self._calculate_initial_interval(
                memory.importance,
                settings
            )

            # Create scheduled review
            review = ScheduledReview(
                user_id=user_id,
                memory_id=memory_id,
                scheduled_for=datetime.utcnow() + timedelta(days=initial_interval),
                algorithm=algorithm,
                interval_days=initial_interval,
                ease_factor=settings.initial_ease,
                priority=memory.importance
            )

            # Save to database
            await self._save_scheduled_review(review)

            return review

        except Exception as e:
            logger.error(f"Error scheduling review: {e}")
            raise

    async def get_due_reviews(
        self,
        user_id: str,
        date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> list[ScheduledReview]:
        """Get reviews due for a specific date"""
        date = date or datetime.utcnow()

        try:
            # Query scheduled reviews
            query = text("""
                SELECT
                    sr.*,
                    m.title,
                    m.content,
                    m.importance
                FROM scheduled_reviews sr
                JOIN memories m ON m.id = sr.memory_id
                WHERE
                    sr.user_id = :user_id
                    AND sr.status = 'pending'
                    AND sr.scheduled_for <= :date
                    AND m.deleted_at IS NULL
                ORDER BY
                    CASE
                        WHEN sr.scheduled_for < :overdue_date THEN 0
                        ELSE 1
                    END,
                    sr.priority DESC,
                    sr.scheduled_for ASC
                LIMIT :limit
            """)

            overdue_date = date - timedelta(days=1)
            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "date": date,
                    "overdue_date": overdue_date,
                    "limit": limit or 100
                }
            )

            reviews = []
            for row in result.fetchall():
                review = ScheduledReview(
                    id=row.id,
                    user_id=row.user_id,
                    memory_id=row.memory_id,
                    scheduled_for=row.scheduled_for,
                    status=ReviewStatus(row.status),
                    algorithm=RepetitionAlgorithm(row.algorithm),
                    interval_days=row.interval_days,
                    ease_factor=row.ease_factor,
                    lapses=row.lapses,
                    priority=row.priority,
                    created_at=row.created_at
                )

                # Mark as overdue if necessary
                if review.scheduled_for < overdue_date:
                    review.status = ReviewStatus.OVERDUE

                reviews.append(review)

            return reviews

        except Exception as e:
            logger.error(f"Error getting due reviews: {e}")
            return []

    async def record_review(
        self,
        user_id: str,
        review_id: UUID,
        result: ReviewResult
    ) -> ScheduledReview:
        """Record the result of a review and schedule next review"""
        try:
            # Get the review
            review = await self._get_scheduled_review(review_id)
            if not review or review.user_id != user_id:
                raise ValueError("Review not found")

            # Get user settings
            settings = await self._get_user_settings(user_id)

            # Calculate next interval based on algorithm
            if review.algorithm == RepetitionAlgorithm.SM2:
                next_interval, new_ease = self._calculate_sm2_interval(
                    review.interval_days,
                    review.ease_factor,
                    result.difficulty,
                    settings
                )
            elif review.algorithm == RepetitionAlgorithm.ANKI:
                next_interval, new_ease = self._calculate_anki_interval(
                    review.interval_days,
                    review.ease_factor,
                    result.difficulty,
                    review.lapses,
                    settings
                )
            elif review.algorithm == RepetitionAlgorithm.LEITNER:
                next_interval = self._calculate_leitner_interval(
                    review.interval_days,
                    result.recalled_correctly
                )
                new_ease = review.ease_factor
            else:
                # Custom algorithm - simple doubling/halving
                if result.recalled_correctly:
                    next_interval = review.interval_days * 2
                else:
                    next_interval = max(1, review.interval_days * 0.5)
                new_ease = review.ease_factor

            # Handle lapses
            if not result.recalled_correctly:
                review.lapses += 1
                if settings.lapse_new_interval > 0:
                    next_interval = next_interval * settings.lapse_new_interval

            # Add fuzz factor if enabled
            if settings.enable_fuzz:
                next_interval = self._add_fuzz(next_interval)

            # Update review status
            review.status = ReviewStatus.COMPLETED
            review.completed_at = datetime.utcnow()

            # Create next review
            next_review = ScheduledReview(
                user_id=user_id,
                memory_id=review.memory_id,
                scheduled_for=datetime.utcnow() + timedelta(days=next_interval),
                algorithm=review.algorithm,
                interval_days=next_interval,
                ease_factor=new_ease,
                lapses=review.lapses if not result.recalled_correctly else 0,
                priority=review.priority
            )

            # Save updates
            await self._update_scheduled_review(review)
            await self._save_scheduled_review(next_review)
            await self._save_review_result(result)

            # Update memory last accessed
            await self.memory_service.update_memory(
                user_id,
                review.memory_id,
                last_accessed=datetime.utcnow(),
                access_count=(await self.memory_service.get_memory(user_id, review.memory_id)).access_count + 1
            )

            return next_review

        except Exception as e:
            logger.error(f"Error recording review: {e}")
            raise

    async def create_review_session(
        self,
        user_id: str,
        session_type: str = "daily",
        review_limit: Optional[int] = None
    ) -> ReviewSession:
        """Create a review session with optimal review order"""
        try:
            # Get user settings
            settings = await self._get_user_settings(user_id)
            limit = review_limit or settings.daily_review_limit

            # Get due reviews
            all_reviews = await self.get_due_reviews(user_id, limit=limit * 2)

            # Categorize reviews
            overdue = [r for r in all_reviews if r.status == ReviewStatus.OVERDUE]
            due_today = [r for r in all_reviews if r.status == ReviewStatus.PENDING and not r.is_overdue]

            # Select reviews for session
            session_reviews = []

            # Priority: overdue reviews first
            session_reviews.extend(overdue[:limit])
            remaining = limit - len(session_reviews)

            # Then due reviews
            if remaining > 0:
                session_reviews.extend(due_today[:remaining])

            # Calculate session metrics
            total_reviews = len(session_reviews)
            avg_difficulty = sum(r.ease_factor for r in session_reviews) / total_reviews if total_reviews > 0 else 2.5
            estimated_duration = total_reviews * 30  # 30 seconds per review estimate

            # Create session
            session = ReviewSession(
                user_id=user_id,
                session_type=session_type,
                reviews=session_reviews,
                total_reviews=total_reviews,
                average_difficulty=1 / avg_difficulty,  # Convert ease to difficulty
                estimated_duration_minutes=estimated_duration // 60
            )

            # Save session
            await self._save_review_session(session)

            return session

        except Exception as e:
            logger.error(f"Error creating review session: {e}")
            raise

    async def get_memory_strength(
        self,
        user_id: str,
        memory_id: UUID
    ) -> MemoryStrength:
        """Calculate current strength of a memory"""
        try:
            # Get review history
            history = await self._get_review_history(user_id, memory_id)

            # Get latest scheduled review
            latest_review = await self._get_latest_review(user_id, memory_id)

            if not latest_review:
                # No reviews scheduled yet
                memory = await self.memory_service.get_memory(user_id, memory_id)
                return MemoryStrength(
                    memory_id=memory_id,
                    stability=1.0,
                    difficulty=1.0 - memory.importance,
                    retrievability=0.5,
                    next_review=datetime.utcnow() + timedelta(days=1),
                    review_count=0,
                    success_rate=0.0
                )

            # Calculate metrics
            stability = latest_review.interval_days
            difficulty = 1 / latest_review.ease_factor

            # Calculate retrievability using forgetting curve
            days_since_review = (datetime.utcnow() - (latest_review.completed_at or latest_review.created_at)).days
            retrievability = math.exp(-days_since_review / stability)

            # Calculate success rate
            success_rate = history.success_rate if history else 1.0

            return MemoryStrength(
                memory_id=memory_id,
                stability=stability,
                difficulty=difficulty,
                retrievability=retrievability,
                last_review=latest_review.completed_at,
                next_review=latest_review.scheduled_for,
                review_count=history.total_reviews if history else 0,
                success_rate=success_rate
            )

        except Exception as e:
            logger.error(f"Error calculating memory strength: {e}")
            raise

    async def get_review_statistics(
        self,
        user_id: str,
        period: str = "week"
    ) -> ReviewStatistics:
        """Get review statistics for a period"""
        try:
            # Determine date range
            end_date = datetime.utcnow()
            if period == "day":
                start_date = end_date - timedelta(days=1)
            elif period == "week":
                start_date = end_date - timedelta(weeks=1)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            else:  # all_time
                start_date = datetime(2000, 1, 1)

            # Query statistics
            stats_query = text("""
                WITH review_stats AS (
                    SELECT
                        COUNT(*) as total_reviews,
                        COUNT(CASE WHEN recalled_correctly THEN 1 END) as successful_reviews,
                        AVG(CASE WHEN difficulty = 'easy' THEN 4
                             WHEN difficulty = 'good' THEN 3
                             WHEN difficulty = 'hard' THEN 2
                             ELSE 1 END) as avg_difficulty_score,
                        SUM(time_taken_seconds) / 60.0 as total_time_minutes,
                        AVG(time_taken_seconds) as avg_time_seconds
                    FROM review_results
                    WHERE user_id = :user_id
                    AND reviewed_at BETWEEN :start_date AND :end_date
                ),
                schedule_stats AS (
                    SELECT
                        COUNT(CASE WHEN status = 'pending' AND scheduled_for <= :end_date THEN 1 END) as due_count,
                        COUNT(CASE WHEN status = 'pending' AND scheduled_for < :overdue_date THEN 1 END) as overdue_count,
                        AVG(ease_factor) as avg_ease,
                        AVG(interval_days) as avg_interval
                    FROM scheduled_reviews
                    WHERE user_id = :user_id
                ),
                memory_stats AS (
                    SELECT
                        COUNT(CASE WHEN sr.interval_days > 21 THEN 1 END) as mature_count,
                        COUNT(CASE WHEN sr.interval_days <= 21 AND sr.interval_days > 1 THEN 1 END) as young_count,
                        COUNT(CASE WHEN sr.interval_days <= 1 THEN 1 END) as learning_count
                    FROM scheduled_reviews sr
                    JOIN memories m ON m.id = sr.memory_id
                    WHERE sr.user_id = :user_id
                    AND sr.status = 'pending'
                    AND m.deleted_at IS NULL
                )
                SELECT * FROM review_stats, schedule_stats, memory_stats
            """)

            result = await self.db.execute(
                stats_query,
                {
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "overdue_date": end_date - timedelta(days=1)
                }
            )

            stats = result.fetchone()

            if not stats:
                # Return empty statistics
                return ReviewStatistics(
                    user_id=user_id,
                    period=period,
                    reviews_completed=0,
                    reviews_due=0,
                    reviews_overdue=0,
                    average_success_rate=0.0,
                    average_ease=2.5,
                    average_interval=1.0,
                    retention_rate=0.0,
                    total_time_minutes=0,
                    average_time_per_review=0.0,
                    current_streak=0,
                    longest_streak=0,
                    difficulty_breakdown={},
                    mature_memories=0,
                    young_memories=0,
                    learning_memories=0
                )

            # Calculate success rate
            success_rate = stats.successful_reviews / stats.total_reviews if stats.total_reviews > 0 else 0.0

            # Calculate retention rate (simplified)
            retention_rate = success_rate * 0.9  # Approximate

            # Get difficulty breakdown
            difficulty_breakdown = await self._get_difficulty_breakdown(
                user_id, start_date, end_date
            )

            # Calculate streaks
            current_streak, longest_streak = await self._calculate_streaks(user_id)

            return ReviewStatistics(
                user_id=user_id,
                period=period,
                reviews_completed=stats.total_reviews or 0,
                reviews_due=stats.due_count or 0,
                reviews_overdue=stats.overdue_count or 0,
                average_success_rate=success_rate,
                average_ease=stats.avg_ease or 2.5,
                average_interval=stats.avg_interval or 1.0,
                retention_rate=retention_rate,
                total_time_minutes=int(stats.total_time_minutes or 0),
                average_time_per_review=stats.avg_time_seconds or 30.0,
                current_streak=current_streak,
                longest_streak=longest_streak,
                difficulty_breakdown=difficulty_breakdown,
                mature_memories=stats.mature_count or 0,
                young_memories=stats.young_count or 0,
                learning_memories=stats.learning_count or 0
            )

        except Exception as e:
            logger.error(f"Error getting review statistics: {e}")
            raise

    async def get_optimal_review_time(
        self,
        user_id: str
    ) -> OptimalReviewTime:
        """Determine optimal review time based on user patterns"""
        try:
            # Analyze historical review performance by hour
            performance_query = text("""
                SELECT
                    EXTRACT(HOUR FROM reviewed_at) as hour,
                    COUNT(*) as review_count,
                    AVG(CASE WHEN recalled_correctly THEN 1 ELSE 0 END) as success_rate,
                    AVG(time_taken_seconds) as avg_time
                FROM review_results
                WHERE user_id = :user_id
                AND reviewed_at > :cutoff_date
                GROUP BY EXTRACT(HOUR FROM reviewed_at)
            """)

            cutoff_date = datetime.utcnow() - timedelta(days=30)
            result = await self.db.execute(
                performance_query,
                {"user_id": user_id, "cutoff_date": cutoff_date}
            )

            hour_stats = {}
            for row in result.fetchall():
                hour_stats[int(row.hour)] = {
                    "count": row.review_count,
                    "success_rate": row.success_rate,
                    "avg_time": row.avg_time
                }

            # Find best hour based on success rate and volume
            best_hour = 9  # Default to 9 AM
            best_score = 0.0

            success_by_hour = {}
            volume_by_hour = {}

            for hour, stats in hour_stats.items():
                # Weight success rate by volume
                score = stats["success_rate"] * math.log(stats["count"] + 1)
                success_by_hour[hour] = stats["success_rate"]
                volume_by_hour[hour] = stats["count"]

                if score > best_score:
                    best_score = score
                    best_hour = hour

            # Calculate circadian score (simplified)
            circadian_scores = {
                6: 0.7, 7: 0.8, 8: 0.9, 9: 1.0, 10: 0.95,
                11: 0.9, 12: 0.8, 13: 0.7, 14: 0.75, 15: 0.8,
                16: 0.85, 17: 0.9, 18: 0.85, 19: 0.8, 20: 0.75,
                21: 0.7, 22: 0.6, 23: 0.5
            }

            circadian_score = circadian_scores.get(best_hour, 0.5)

            # Generate recommendation
            today = datetime.utcnow().date()
            recommended_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=best_hour)

            # Generate reasoning
            reasoning = []
            if hour_stats.get(best_hour, {}).get("success_rate", 0) > 0.8:
                reasoning.append(f"Your success rate is highest at {best_hour}:00")
            if hour_stats.get(best_hour, {}).get("count", 0) > 10:
                reasoning.append("You frequently review at this time")
            if circadian_score > 0.8:
                reasoning.append("This aligns well with natural alertness patterns")

            # Find alternative times
            alternatives = []
            for hour in sorted(hour_stats.keys(), key=lambda h: hour_stats[h]["success_rate"], reverse=True)[1:4]:
                alt_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=hour)
                alternatives.append(alt_time)

            return OptimalReviewTime(
                user_id=user_id,
                recommended_time=recommended_time,
                confidence=min(best_score / 10, 1.0),  # Normalize confidence
                historical_success_by_hour=success_by_hour,
                historical_volume_by_hour=volume_by_hour,
                circadian_score=circadian_score,
                reasoning=reasoning if reasoning else ["Based on general best practices"],
                alternative_times=alternatives
            )

        except Exception as e:
            logger.error(f"Error calculating optimal review time: {e}")
            # Return default recommendation
            return OptimalReviewTime(
                user_id=user_id,
                recommended_time=datetime.combine(datetime.utcnow().date(), datetime.min.time()) + timedelta(hours=9),
                confidence=0.5,
                historical_success_by_hour={},
                historical_volume_by_hour={},
                circadian_score=1.0,
                reasoning=["Default morning recommendation"],
                alternative_times=[]
            )

    async def generate_learning_curve(
        self,
        user_id: str,
        subject: str,  # Topic or memory ID
        days: int = 30
    ) -> LearningCurve:
        """Generate learning curve analysis"""
        try:
            # Get historical data
            if self._is_uuid(subject):
                # Learning curve for specific memory
                data_points = await self._get_memory_learning_data(
                    user_id, UUID(subject), days
                )
            else:
                # Learning curve for topic
                data_points = await self._get_topic_learning_data(
                    user_id, subject, days
                )

            if not data_points:
                # No data available
                return LearningCurve(
                    subject=subject,
                    data_points=[],
                    initial_learning_rate=0.0,
                    plateau_level=0.0,
                    time_to_plateau_days=0,
                    current_retention=0.0,
                    current_stability=0.0,
                    predicted_retention_7d=0.0,
                    predicted_retention_30d=0.0,
                    optimal_review_frequency="No data",
                    suggested_modifications=["Start reviewing this subject"]
                )

            # Fit learning curve (simplified exponential model)
            retention_values = [dp["retention_rate"] for dp in data_points]
            days_values = list(range(len(retention_values)))

            # Calculate curve parameters
            initial_rate = retention_values[0] if retention_values else 0.5
            plateau = max(retention_values) if retention_values else 0.9

            # Find time to plateau (when retention reaches 90% of max)
            plateau_threshold = plateau * 0.9
            time_to_plateau = next(
                (i for i, r in enumerate(retention_values) if r >= plateau_threshold),
                len(retention_values)
            )

            # Current state
            current_retention = retention_values[-1] if retention_values else 0.0
            current_stability = self._calculate_stability(data_points)

            # Predictions (simplified)
            decay_rate = 0.1  # 10% decay per week without review
            predicted_7d = current_retention * (1 - decay_rate)
            predicted_30d = current_retention * (1 - decay_rate * 4.3)

            # Recommendations
            if current_retention < 0.8:
                optimal_frequency = "daily"
                modifications = ["Increase review frequency", "Use active recall techniques"]
            elif current_retention < 0.9:
                optimal_frequency = "every 3 days"
                modifications = ["Maintain current schedule", "Focus on difficult aspects"]
            else:
                optimal_frequency = "weekly"
                modifications = ["Current approach is working well", "Consider spacing reviews further"]

            return LearningCurve(
                subject=subject,
                data_points=data_points,
                initial_learning_rate=initial_rate,
                plateau_level=plateau,
                time_to_plateau_days=time_to_plateau,
                current_retention=current_retention,
                current_stability=current_stability,
                predicted_retention_7d=predicted_7d,
                predicted_retention_30d=predicted_30d,
                optimal_review_frequency=optimal_frequency,
                suggested_modifications=modifications
            )

        except Exception as e:
            logger.error(f"Error generating learning curve: {e}")
            raise

    # Algorithm implementations

    def _calculate_sm2_interval(
        self,
        previous_interval: float,
        ease_factor: float,
        difficulty: ReviewDifficulty,
        settings: RepetitionSettings
    ) -> tuple[float, float]:
        """SuperMemo 2 algorithm"""
        # Map difficulty to performance rating
        performance = {
            ReviewDifficulty.AGAIN: 0,
            ReviewDifficulty.HARD: 3,
            ReviewDifficulty.GOOD: 4,
            ReviewDifficulty.EASY: 5
        }[difficulty]

        # Update ease factor
        new_ease = ease_factor + (0.1 - (5 - performance) * (0.08 + (5 - performance) * 0.02))
        new_ease = max(1.3, new_ease)  # Minimum ease factor

        # Calculate interval
        if performance < 3:
            # Failed - reset to beginning
            new_interval = 1
        else:
            if previous_interval == 1:
                new_interval = 6
            else:
                new_interval = previous_interval * new_ease

            # Apply easy bonus
            if difficulty == ReviewDifficulty.EASY:
                new_interval *= settings.easy_bonus

        return new_interval, new_ease

    def _calculate_anki_interval(
        self,
        previous_interval: float,
        ease_factor: float,
        difficulty: ReviewDifficulty,
        lapses: int,
        settings: RepetitionSettings
    ) -> tuple[float, float]:
        """Anki-style algorithm"""
        # Similar to SM2 but with more nuanced handling
        if difficulty == ReviewDifficulty.AGAIN:
            # Lapse handling
            new_interval = max(1, previous_interval * 0.5)
            new_ease = max(1.3, ease_factor - 0.2)
        elif difficulty == ReviewDifficulty.HARD:
            new_interval = previous_interval * 1.2
            new_ease = max(1.3, ease_factor - 0.15)
        elif difficulty == ReviewDifficulty.GOOD:
            new_interval = previous_interval * ease_factor
            new_ease = ease_factor
        else:  # EASY
            new_interval = previous_interval * ease_factor * settings.easy_bonus
            new_ease = ease_factor + 0.15

        # Apply graduating intervals for learning cards
        if previous_interval < 1:
            if difficulty == ReviewDifficulty.GOOD:
                new_interval = 1
            elif difficulty == ReviewDifficulty.EASY:
                new_interval = 4

        return new_interval, new_ease

    def _calculate_leitner_interval(
        self,
        previous_interval: float,
        success: bool
    ) -> float:
        """Leitner box system"""
        # Define box intervals (days)
        boxes = [1, 2, 4, 8, 16, 32, 64]

        # Find current box
        current_box = 0
        for i, interval in enumerate(boxes):
            if previous_interval <= interval:
                current_box = i
                break

        if success:
            # Move to next box
            next_box = min(current_box + 1, len(boxes) - 1)
            return boxes[next_box]
        else:
            # Move back to first box
            return boxes[0]

    def _calculate_initial_interval(
        self,
        importance: float,
        settings: RepetitionSettings
    ) -> float:
        """Calculate initial interval based on importance"""
        # Higher importance = shorter initial interval
        base_interval = 1.0
        importance_factor = 2.0 - importance  # 1.0 to 2.0

        return base_interval * importance_factor

    def _add_fuzz(self, interval: float) -> float:
        """Add randomness to prevent clustering"""
        # Add ±20% randomness, but at least ±1 day for longer intervals
        if interval < 3:
            return interval

        fuzz_range = max(1, interval * 0.2)
        fuzz = random.uniform(-fuzz_range, fuzz_range)

        return max(1, interval + fuzz)

    def _calculate_stability(self, data_points: list[dict[str, Any]]) -> float:
        """Calculate memory stability from learning data"""
        if len(data_points) < 2:
            return 1.0

        # Calculate variance in retention rates
        retention_rates = [dp["retention_rate"] for dp in data_points]
        mean_retention = sum(retention_rates) / len(retention_rates)
        variance = sum((r - mean_retention) ** 2 for r in retention_rates) / len(retention_rates)

        # Lower variance = higher stability
        stability = 1.0 / (1.0 + variance)

        return stability

    def _is_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID"""
        try:
            UUID(value)
            return True
        except ValueError:
            return False

    # Database helper methods

    async def _get_user_settings(self, user_id: str) -> RepetitionSettings:
        """Get user's repetition settings"""
        # In production, load from database
        # For now, return defaults with user_id
        settings = self.default_settings.copy()
        settings.user_id = user_id
        return settings

    async def _save_scheduled_review(self, review: ScheduledReview):
        """Save scheduled review to database"""
        query = text("""
            INSERT INTO scheduled_reviews (
                id, user_id, memory_id, scheduled_for, status,
                algorithm, interval_days, ease_factor, lapses,
                priority, created_at
            ) VALUES (
                :id, :user_id, :memory_id, :scheduled_for, :status,
                :algorithm, :interval_days, :ease_factor, :lapses,
                :priority, :created_at
            )
        """)

        await self.db.execute(query, {
            "id": review.id,
            "user_id": review.user_id,
            "memory_id": review.memory_id,
            "scheduled_for": review.scheduled_for,
            "status": review.status.value,
            "algorithm": review.algorithm.value,
            "interval_days": review.interval_days,
            "ease_factor": review.ease_factor,
            "lapses": review.lapses,
            "priority": review.priority,
            "created_at": review.created_at
        })

        await self.db.commit()

    async def _get_scheduled_review(self, review_id: UUID) -> Optional[ScheduledReview]:
        """Get scheduled review by ID"""
        query = text("""
            SELECT * FROM scheduled_reviews WHERE id = :id
        """)

        result = await self.db.execute(query, {"id": review_id})
        row = result.fetchone()

        if not row:
            return None

        return ScheduledReview(
            id=row.id,
            user_id=row.user_id,
            memory_id=row.memory_id,
            scheduled_for=row.scheduled_for,
            status=ReviewStatus(row.status),
            algorithm=RepetitionAlgorithm(row.algorithm),
            interval_days=row.interval_days,
            ease_factor=row.ease_factor,
            lapses=row.lapses,
            priority=row.priority,
            created_at=row.created_at,
            completed_at=row.completed_at
        )

    async def _update_scheduled_review(self, review: ScheduledReview):
        """Update scheduled review in database"""
        query = text("""
            UPDATE scheduled_reviews
            SET status = :status, completed_at = :completed_at
            WHERE id = :id
        """)

        await self.db.execute(query, {
            "id": review.id,
            "status": review.status.value,
            "completed_at": review.completed_at
        })

        await self.db.commit()

    async def _save_review_result(self, result: ReviewResult):
        """Save review result to database"""
        query = text("""
            INSERT INTO review_results (
                review_id, memory_id, difficulty, time_taken_seconds,
                confidence, recalled_correctly, notes, reviewed_at
            ) VALUES (
                :review_id, :memory_id, :difficulty, :time_taken_seconds,
                :confidence, :recalled_correctly, :notes, :reviewed_at
            )
        """)

        await self.db.execute(query, {
            "review_id": result.review_id,
            "memory_id": result.memory_id,
            "difficulty": result.difficulty.value,
            "time_taken_seconds": result.time_taken_seconds,
            "confidence": result.confidence,
            "recalled_correctly": result.recalled_correctly,
            "notes": result.notes,
            "reviewed_at": result.reviewed_at
        })

        await self.db.commit()

    async def _save_review_session(self, session: ReviewSession):
        """Save review session to database"""
        # Implementation would save session details
        pass

    async def _get_review_history(
        self,
        user_id: str,
        memory_id: UUID
    ) -> Optional[ReviewHistory]:
        """Get review history for a memory"""
        query = text("""
            SELECT
                COUNT(*) as total_reviews,
                COUNT(CASE WHEN recalled_correctly THEN 1 END) as successful_reviews,
                AVG(CASE WHEN difficulty = 'easy' THEN 4
                     WHEN difficulty = 'good' THEN 3
                     WHEN difficulty = 'hard' THEN 2
                     ELSE 1 END) as avg_difficulty,
                MAX(reviewed_at) as last_review
            FROM review_results rr
            JOIN scheduled_reviews sr ON sr.id = rr.review_id
            WHERE sr.user_id = :user_id AND sr.memory_id = :memory_id
        """)

        result = await self.db.execute(query, {
            "user_id": user_id,
            "memory_id": memory_id
        })

        stats = result.fetchone()

        if not stats or stats.total_reviews == 0:
            return None

        return ReviewHistory(
            memory_id=memory_id,
            reviews=[],  # Would load actual review details in production
            total_reviews=stats.total_reviews,
            successful_reviews=stats.successful_reviews,
            average_difficulty=stats.avg_difficulty,
            average_interval=1.0,  # Would calculate from actual intervals
            last_review=stats.last_review
        )

    async def _get_latest_review(
        self,
        user_id: str,
        memory_id: UUID
    ) -> Optional[ScheduledReview]:
        """Get latest scheduled review for a memory"""
        query = text("""
            SELECT * FROM scheduled_reviews
            WHERE user_id = :user_id AND memory_id = :memory_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {
            "user_id": user_id,
            "memory_id": memory_id
        })

        row = result.fetchone()

        if not row:
            return None

        return ScheduledReview(
            id=row.id,
            user_id=row.user_id,
            memory_id=row.memory_id,
            scheduled_for=row.scheduled_for,
            status=ReviewStatus(row.status),
            algorithm=RepetitionAlgorithm(row.algorithm),
            interval_days=row.interval_days,
            ease_factor=row.ease_factor,
            lapses=row.lapses,
            priority=row.priority,
            created_at=row.created_at,
            completed_at=row.completed_at
        )

    async def _get_difficulty_breakdown(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, int]:
        """Get breakdown of reviews by difficulty"""
        query = text("""
            SELECT
                difficulty,
                COUNT(*) as count
            FROM review_results rr
            JOIN scheduled_reviews sr ON sr.id = rr.review_id
            WHERE
                sr.user_id = :user_id
                AND rr.reviewed_at BETWEEN :start_date AND :end_date
            GROUP BY difficulty
        """)

        result = await self.db.execute(query, {
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date
        })

        breakdown = {}
        for row in result.fetchall():
            breakdown[row.difficulty] = row.count

        return breakdown

    async def _calculate_streaks(self, user_id: str) -> tuple[int, int]:
        """Calculate current and longest review streaks"""
        # Simplified implementation
        # In production, would analyze daily review patterns
        return 7, 14  # Current: 7 days, Longest: 14 days

    async def _get_memory_learning_data(
        self,
        user_id: str,
        memory_id: UUID,
        days: int
    ) -> list[dict[str, Any]]:
        """Get learning data for a specific memory"""
        # Simplified implementation
        # Would query actual review history
        data_points = []
        for i in range(min(days, 10)):
            retention = 0.5 + (i * 0.05)  # Gradual improvement
            data_points.append({
                "date": datetime.utcnow() - timedelta(days=days-i),
                "retention_rate": min(retention, 0.95),
                "review_count": i + 1
            })

        return data_points

    async def _get_topic_learning_data(
        self,
        user_id: str,
        topic: str,
        days: int
    ) -> list[dict[str, Any]]:
        """Get learning data for a topic"""
        # Simplified implementation
        # Would aggregate data for all memories with this topic
        data_points = []
        for i in range(min(days, 15)):
            retention = 0.4 + (i * 0.04)  # Slower improvement for topics
            data_points.append({
                "date": datetime.utcnow() - timedelta(days=days-i),
                "retention_rate": min(retention, 0.9),
                "review_count": (i + 1) * 3  # Multiple memories
            })

        return data_points
