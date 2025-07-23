"""
Spaced Repetition Scheduler Service - v2.8.2

Service for implementing spaced repetition algorithms including
SuperMemo 2, Anki-style, and Leitner box system.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import asyncpg
import numpy as np

from app.models.synthesis.repetition_models import (
    BulkReviewRequest,
    LearningStatistics,
    MemoryStrength,
    RepetitionAlgorithm,
    RepetitionConfig,
    ReviewDifficulty,
    ReviewResult,
    ReviewSchedule,
    ReviewSession,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class SpacedRepetitionEngine:
    """Engine for calculating spaced repetition intervals."""

    def __init__(self, algorithm: RepetitionAlgorithm = RepetitionAlgorithm.SM2):
        self.algorithm = algorithm
        self.config = RepetitionConfig(algorithm=algorithm)

    def calculate_next_interval(
        self,
        current_interval: int,
        ease_factor: float,
        difficulty: ReviewDifficulty,
        repetitions: int,
    ) -> Tuple[int, float]:
        """Calculate next interval and updated ease factor."""
        if self.algorithm == RepetitionAlgorithm.SM2:
            return self._sm2_algorithm(current_interval, ease_factor, difficulty, repetitions)
        elif self.algorithm == RepetitionAlgorithm.ANKI:
            return self._anki_algorithm(current_interval, ease_factor, difficulty, repetitions)
        elif self.algorithm == RepetitionAlgorithm.LEITNER:
            return self._leitner_algorithm(current_interval, difficulty, repetitions)
        else:
            # Custom algorithm
            return current_interval * 2, ease_factor

    def _sm2_algorithm(
        self,
        current_interval: int,
        ease_factor: float,
        difficulty: ReviewDifficulty,
        repetitions: int,
    ) -> Tuple[int, float]:
        """SuperMemo 2 algorithm implementation."""
        # Update ease factor based on difficulty
        if difficulty == ReviewDifficulty.AGAIN:
            new_ease = ease_factor - 0.8
            new_interval = 1
            repetitions = 0
        elif difficulty == ReviewDifficulty.HARD:
            new_ease = ease_factor - 0.15
            new_interval = int(current_interval * 1.2)
        elif difficulty == ReviewDifficulty.GOOD:
            new_ease = ease_factor
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                new_interval = int(current_interval * ease_factor)
        else:  # EASY
            new_ease = ease_factor + 0.15
            new_interval = int(current_interval * ease_factor * self.config.easy_bonus)

        # Ensure ease factor stays within bounds
        new_ease = max(self.config.minimum_ease, new_ease)

        # Ensure minimum interval
        new_interval = max(self.config.minimum_interval, new_interval)

        return new_interval, new_ease

    def _anki_algorithm(
        self,
        current_interval: int,
        ease_factor: float,
        difficulty: ReviewDifficulty,
        repetitions: int,
    ) -> Tuple[int, float]:
        """Anki-style algorithm implementation."""
        # Similar to SM2 but with Anki's modifications
        if difficulty == ReviewDifficulty.AGAIN:
            new_ease = max(1.3, ease_factor - 0.2)
            new_interval = max(1, int(current_interval * 0.5))
        elif difficulty == ReviewDifficulty.HARD:
            new_ease = max(1.3, ease_factor - 0.15)
            new_interval = int(current_interval * 1.2)
        elif difficulty == ReviewDifficulty.GOOD:
            new_ease = ease_factor
            new_interval = int(current_interval * ease_factor)
        else:  # EASY
            new_ease = ease_factor + 0.15
            new_interval = int(current_interval * ease_factor * 1.3)

        # Add some randomness to prevent clustering
        fuzz = self._calculate_fuzz(new_interval)
        new_interval = int(new_interval * (1 + fuzz))

        return max(1, new_interval), new_ease

    def _leitner_algorithm(
        self,
        current_interval: int,
        difficulty: ReviewDifficulty,
        repetitions: int,
    ) -> Tuple[int, float]:
        """Leitner box system implementation."""
        # Box intervals: 1, 2, 4, 8, 16, 32, 64 days
        boxes = [1, 2, 4, 8, 16, 32, 64]

        # Find current box
        current_box = 0
        for i, interval in enumerate(boxes):
            if current_interval <= interval:
                current_box = i
                break

        if difficulty == ReviewDifficulty.AGAIN:
            # Move back to first box
            new_interval = boxes[0]
        elif difficulty == ReviewDifficulty.HARD:
            # Stay in same box
            new_interval = boxes[current_box]
        else:  # GOOD or EASY
            # Move to next box
            next_box = min(current_box + 1, len(boxes) - 1)
            new_interval = boxes[next_box]

        # Ease factor doesn't change in Leitner
        return new_interval, 2.5

    def _calculate_fuzz(self, interval: int) -> float:
        """Calculate fuzz factor to prevent clustering."""
        if interval < 3:
            return 0
        elif interval < 7:
            return np.random.uniform(-0.15, 0.15)
        else:
            return np.random.uniform(-0.05, 0.05)

    def calculate_optimal_review_time(
        self,
        user_performance: Dict[int, float],
        timezone: str = "UTC",
    ) -> str:
        """Calculate optimal review time based on past performance."""
        if not user_performance:
            return "09:00"  # Default morning time

        # Find hour with best performance
        best_hour = max(user_performance.items(), key=lambda x: x[1])[0]
        return f"{best_hour:02d}:00"

    def calculate_forgetting_curve(
        self,
        interval: int,
        time_elapsed: int,
        stability: float = 1.0,
    ) -> float:
        """Calculate retention probability using forgetting curve."""
        # R = e^(-t/S) where t is time elapsed and S is stability
        return math.exp(-time_elapsed / (stability * interval))


class RepetitionScheduler:
    """Service for managing spaced repetition schedules."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.engines = {
            RepetitionAlgorithm.SM2: SpacedRepetitionEngine(RepetitionAlgorithm.SM2),
            RepetitionAlgorithm.ANKI: SpacedRepetitionEngine(RepetitionAlgorithm.ANKI),
            RepetitionAlgorithm.LEITNER: SpacedRepetitionEngine(RepetitionAlgorithm.LEITNER),
        }

    async def schedule_review(
        self,
        memory_id: str,
        algorithm: RepetitionAlgorithm = RepetitionAlgorithm.SM2,
        config: Optional[RepetitionConfig] = None,
    ) -> ReviewSchedule:
        """Schedule a memory for review."""
        # Get or create memory strength
        strength = await self._get_or_create_strength(memory_id)

        # Calculate next review date
        engine = self.engines[algorithm]
        if config:
            engine.config = config

        # For new memories, use graduating interval
        if strength.repetitions == 0:
            interval_days = config.graduating_interval if config else 1
        else:
            interval_days = strength.interval

        next_review = datetime.utcnow() + timedelta(days=interval_days)

        # Calculate review window
        window_size = max(1, int(interval_days * 0.1))  # 10% window
        earliest = next_review - timedelta(days=window_size)
        latest = next_review + timedelta(days=window_size)

        # Get optimal review time
        user_performance = await self._get_user_performance(memory_id)
        optimal_time = engine.calculate_optimal_review_time(user_performance)

        # Create schedule
        schedule = ReviewSchedule(
            memory_id=memory_id,
            scheduled_date=next_review,
            interval_days=interval_days,
            priority=self._calculate_priority(strength),
            earliest_date=earliest,
            latest_date=latest,
            optimal_time=optimal_time,
            algorithm=algorithm,
            strength=strength,
        )

        # Save to database
        await self._save_schedule(schedule)

        return schedule

    async def bulk_schedule_reviews(
        self,
        request: BulkReviewRequest,
    ) -> List[ReviewSchedule]:
        """Schedule reviews for multiple memories."""
        schedules = []

        # Get memory priorities if needed
        if request.prioritize_by == "importance":
            priorities = await self._get_memory_priorities(request.memory_ids)
        else:
            priorities = {mid: 1.0 for mid in request.memory_ids}

        # Sort memories by priority
        sorted_memories = sorted(
            request.memory_ids,
            key=lambda x: priorities.get(x, 0),
            reverse=True,
        )

        # Schedule each memory
        for i, memory_id in enumerate(sorted_memories):
            # Distribute over days if requested
            if request.distribute_over_days:
                days_offset = i % request.distribute_over_days
                config = RepetitionConfig(
                    algorithm=request.algorithm,
                    graduating_interval=1 + days_offset,
                )
            else:
                config = request.config

            schedule = await self.schedule_review(
                memory_id,
                request.algorithm,
                config,
            )
            schedules.append(schedule)

        return schedules

    async def record_review(
        self,
        memory_id: str,
        difficulty: ReviewDifficulty,
        time_taken_seconds: int,
        session_id: str,
        confidence_level: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> ReviewResult:
        """Record the result of a review."""
        # Get current strength
        strength = await self._get_or_create_strength(memory_id)
        previous_strength = strength.copy()

        # Get engine for algorithm
        engine = self.engines[strength.algorithm if hasattr(strength, 'algorithm') else RepetitionAlgorithm.SM2]

        # Calculate new interval and ease
        new_interval, new_ease = engine.calculate_next_interval(
            strength.interval,
            strength.ease_factor,
            difficulty,
            strength.repetitions,
        )

        # Update strength
        strength.ease_factor = new_ease
        strength.interval = new_interval
        strength.repetitions = strength.repetitions + 1 if difficulty != ReviewDifficulty.AGAIN else 0
        strength.last_review = datetime.utcnow()
        strength.next_review = datetime.utcnow() + timedelta(days=new_interval)

        # Update success rate
        total_reviews = await self._get_total_reviews(memory_id)
        successful_reviews = await self._get_successful_reviews(memory_id)
        if difficulty != ReviewDifficulty.AGAIN:
            successful_reviews += 1
        strength.success_rate = successful_reviews / (total_reviews + 1)

        # Update average difficulty
        avg_difficulty = await self._get_average_difficulty(memory_id)
        strength.average_difficulty = (avg_difficulty * total_reviews + difficulty.value) / (total_reviews + 1)

        # Calculate new retrievability
        strength.retrievability = 1.0  # Just reviewed
        strength.retention_rate = engine.calculate_forgetting_curve(new_interval, 0)

        # Save updated strength
        await self._save_strength(strength)

        # Create result
        result = ReviewResult(
            memory_id=memory_id,
            session_id=session_id,
            time_taken_seconds=time_taken_seconds,
            difficulty=difficulty,
            previous_strength=previous_strength,
            new_strength=strength,
            next_review=strength.next_review,
            interval_change=new_interval - previous_strength.interval,
            confidence_level=confidence_level,
            notes=notes,
        )

        # Save review result
        await self._save_review_result(result)

        # Update session
        await self._update_session(session_id, difficulty, time_taken_seconds)

        return result

    async def get_due_reviews(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        include_overdue: bool = True,
    ) -> List[ReviewSchedule]:
        """Get memories due for review."""
        now = datetime.utcnow()

        query = """
            SELECT
                rs.*,
                ms.ease_factor,
                ms.interval,
                ms.repetitions,
                ms.success_rate,
                ms.last_review,
                ms.retrievability
            FROM review_schedules rs
            JOIN memory_strengths ms ON rs.memory_id = ms.memory_id
            WHERE rs.scheduled_date <= $1
        """

        params = [now + timedelta(minutes=20)]  # Include reviews due in next 20 mins

        if user_id:
            query += " AND rs.user_id = $2"
            params.append(user_id)

        if not include_overdue:
            query += f" AND rs.scheduled_date >= ${len(params) + 1}"
            params.append(now - timedelta(days=7))  # Exclude reviews older than 7 days

        query += f" ORDER BY rs.priority DESC, rs.scheduled_date ASC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        schedules = []
        for row in rows:
            strength = MemoryStrength(
                memory_id=row['memory_id'],
                ease_factor=row['ease_factor'],
                interval=row['interval'],
                repetitions=row['repetitions'],
                success_rate=row['success_rate'],
                last_review=row['last_review'],
                retrievability=row['retrievability'],
            )

            schedule = ReviewSchedule(
                memory_id=row['memory_id'],
                scheduled_date=row['scheduled_date'],
                interval_days=row['interval_days'],
                priority=row['priority'],
                earliest_date=row['earliest_date'],
                latest_date=row['latest_date'],
                optimal_time=row['optimal_time'],
                algorithm=RepetitionAlgorithm(row['algorithm']),
                strength=strength,
            )
            schedules.append(schedule)

        return schedules

    async def start_review_session(self, user_id: str) -> ReviewSession:
        """Start a new review session."""
        session = ReviewSession(
            id=f"session_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
        )

        # Save to database
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO review_sessions (id, user_id, started_at)
                VALUES ($1, $2, $3)
            """, session.id, session.user_id, session.started_at)

        return session

    async def end_review_session(self, session_id: str) -> ReviewSession:
        """End a review session and calculate statistics."""
        async with self.pool.acquire() as conn:
            # Get session
            session_data = await conn.fetchrow("""
                SELECT * FROM review_sessions WHERE id = $1
            """, session_id)

            if not session_data:
                raise ValueError(f"Session {session_id} not found")

            # Calculate statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_reviews,
                    COUNT(CASE WHEN difficulty != 1 THEN 1 END) as correct_count,
                    AVG(time_taken_seconds) as avg_time,
                    MAX(streak) as best_streak
                FROM review_results
                WHERE session_id = $1
            """, session_id)

            # Get difficulty distribution
            diff_dist = await conn.fetch("""
                SELECT difficulty, COUNT(*) as count
                FROM review_results
                WHERE session_id = $1
                GROUP BY difficulty
            """, session_id)

            # Update session
            ended_at = datetime.utcnow()
            duration = int((ended_at - session_data['started_at']).total_seconds() / 60)

            await conn.execute("""
                UPDATE review_sessions
                SET ended_at = $1, duration_minutes = $2,
                    total_reviews = $3, completed_reviews = $3,
                    correct_count = $4, accuracy_rate = $5,
                    average_time_seconds = $6, best_streak = $7
                WHERE id = $8
            """, ended_at, duration, stats['total_reviews'],
                stats['correct_count'],
                stats['correct_count'] / stats['total_reviews'] if stats['total_reviews'] > 0 else 0,
                stats['avg_time'] or 0, stats['best_streak'] or 0, session_id)

        # Return updated session
        return await self.get_session(session_id)

    async def get_learning_statistics(
        self,
        user_id: str,
        period: str = "all_time",
    ) -> LearningStatistics:
        """Get comprehensive learning statistics for a user."""
        # Determine date range
        if period == "today":
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
        elif period == "week":
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == "month":
            start_date = datetime.utcnow() - timedelta(days=30)
        else:
            start_date = datetime.min

        async with self.pool.acquire() as conn:
            # Get review statistics
            review_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_reviews,
                    SUM(time_taken_seconds) / 60 as total_time_minutes,
                    COUNT(DISTINCT DATE(reviewed_at)) as active_days
                FROM review_results rr
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = $1 AND rr.reviewed_at >= $2
            """, user_id, start_date)

            # Get retention rates
            retention = await conn.fetchrow("""
                SELECT
                    AVG(CASE WHEN difficulty != 1 THEN 1 ELSE 0 END) as overall_retention,
                    AVG(CASE WHEN ms.interval > 21 AND difficulty != 1 THEN 1 ELSE 0 END) as mature_retention,
                    AVG(CASE WHEN ms.interval <= 21 AND difficulty != 1 THEN 1 ELSE 0 END) as young_retention
                FROM review_results rr
                JOIN memory_strengths ms ON rr.memory_id = ms.memory_id
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = $1 AND rr.reviewed_at >= $2
            """, user_id, start_date)

            # Get memory counts
            memory_counts = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT m.id) as total_memories,
                    COUNT(DISTINCT CASE WHEN ms.interval > 21 THEN m.id END) as mature_memories,
                    COUNT(DISTINCT CASE WHEN DATE(m.created_at) = CURRENT_DATE THEN m.id END) as learned_today
                FROM memories m
                LEFT JOIN memory_strengths ms ON m.id = ms.memory_id
                WHERE m.user_id = $1
            """, user_id)

            # Get current streak
            streak_data = await self._calculate_streak(user_id)

            # Get review time distribution
            time_dist = await conn.fetch("""
                SELECT
                    EXTRACT(HOUR FROM reviewed_at) as hour,
                    COUNT(*) as count
                FROM review_results rr
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = $1 AND rr.reviewed_at >= $2
                GROUP BY hour
                ORDER BY hour
            """, user_id, start_date)

            # Get difficulty distribution
            diff_dist = await conn.fetch("""
                SELECT
                    CASE
                        WHEN difficulty = 1 THEN 'again'
                        WHEN difficulty = 2 THEN 'hard'
                        WHEN difficulty = 3 THEN 'good'
                        WHEN difficulty = 4 THEN 'easy'
                    END as difficulty,
                    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
                FROM review_results rr
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = $1 AND rr.reviewed_at >= $2
                GROUP BY difficulty
            """, user_id, start_date)

            # Get upcoming reviews
            upcoming = await conn.fetch("""
                SELECT
                    COUNT(CASE WHEN scheduled_date <= CURRENT_DATE THEN 1 END) as due_today,
                    COUNT(CASE WHEN scheduled_date <= CURRENT_DATE + INTERVAL '7 days' THEN 1 END) as due_week
                FROM review_schedules rs
                JOIN memories m ON rs.memory_id = m.id
                WHERE m.user_id = $1
            """, user_id)

        # Calculate derived metrics
        days = max(1, (datetime.utcnow() - start_date).days)
        avg_daily = review_stats['total_reviews'] / days if review_stats['total_reviews'] else 0

        # Determine best review time
        best_hour = max(time_dist, key=lambda x: x['count'])['hour'] if time_dist else 9

        # Determine workload trend
        workload_trend = "stable"  # Would calculate based on historical data

        return LearningStatistics(
            user_id=user_id,
            period=period,
            total_reviews=review_stats['total_reviews'] or 0,
            total_time_minutes=int(review_stats['total_time_minutes'] or 0),
            average_daily_reviews=avg_daily,
            overall_retention_rate=retention['overall_retention'] or 0,
            mature_retention_rate=retention['mature_retention'] or 0,
            young_retention_rate=retention['young_retention'] or 0,
            total_memories=memory_counts['total_memories'] or 0,
            mature_memories=memory_counts['mature_memories'] or 0,
            learned_today=memory_counts['learned_today'] or 0,
            current_streak_days=streak_data['current'],
            best_streak_days=streak_data['best'],
            best_review_time=f"{int(best_hour):02d}:00",
            review_time_distribution={int(r['hour']): r['count'] for r in time_dist},
            difficulty_distribution={r['difficulty']: r['percentage'] for r in diff_dist},
            reviews_due_today=upcoming[0]['due_today'] if upcoming else 0,
            reviews_due_week=upcoming[0]['due_week'] if upcoming else 0,
            workload_trend=workload_trend,
        )

    async def _get_or_create_strength(self, memory_id: str) -> MemoryStrength:
        """Get or create memory strength record."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM memory_strengths WHERE memory_id = $1
            """, memory_id)

            if row:
                return MemoryStrength(**dict(row))

            # Create new strength
            strength = MemoryStrength(memory_id=memory_id)

            await conn.execute("""
                INSERT INTO memory_strengths
                (memory_id, ease_factor, interval, repetitions, success_rate,
                 average_difficulty, retention_rate, stability, retrievability, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, strength.memory_id, strength.ease_factor, strength.interval,
                strength.repetitions, strength.success_rate, strength.average_difficulty,
                strength.retention_rate, strength.stability, strength.retrievability,
                strength.created_at)

            return strength

    async def _save_strength(self, strength: MemoryStrength):
        """Save memory strength to database."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE memory_strengths
                SET ease_factor = $2, interval = $3, repetitions = $4,
                    success_rate = $5, average_difficulty = $6,
                    retention_rate = $7, stability = $8, retrievability = $9,
                    last_review = $10, next_review = $11
                WHERE memory_id = $1
            """, strength.memory_id, strength.ease_factor, strength.interval,
                strength.repetitions, strength.success_rate, strength.average_difficulty,
                strength.retention_rate, strength.stability, strength.retrievability,
                strength.last_review, strength.next_review)

    async def _save_schedule(self, schedule: ReviewSchedule):
        """Save review schedule to database."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO review_schedules
                (memory_id, scheduled_date, interval_days, priority,
                 earliest_date, latest_date, optimal_time, algorithm)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (memory_id) DO UPDATE
                SET scheduled_date = $2, interval_days = $3, priority = $4,
                    earliest_date = $5, latest_date = $6, optimal_time = $7,
                    algorithm = $8
            """, schedule.memory_id, schedule.scheduled_date, schedule.interval_days,
                schedule.priority, schedule.earliest_date, schedule.latest_date,
                schedule.optimal_time, schedule.algorithm.value)

    async def _save_review_result(self, result: ReviewResult):
        """Save review result to database."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO review_results
                (memory_id, session_id, reviewed_at, time_taken_seconds,
                 difficulty, interval_change, confidence_level, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, result.memory_id, result.session_id, result.reviewed_at,
                result.time_taken_seconds, result.difficulty.value,
                result.interval_change, result.confidence_level, result.notes)

    async def _update_session(self, session_id: str, difficulty: ReviewDifficulty, time_taken: int):
        """Update session statistics."""
        async with self.pool.acquire() as conn:
            # Update counts
            await conn.execute("""
                UPDATE review_sessions
                SET total_reviews = total_reviews + 1,
                    completed_reviews = completed_reviews + 1,
                    correct_count = correct_count + CASE WHEN $2 != 1 THEN 1 ELSE 0 END
                WHERE id = $1
            """, session_id, difficulty.value)

            # Update difficulty distribution
            diff_name = difficulty.name.lower()
            await conn.execute(f"""
                UPDATE review_sessions
                SET difficulty_distribution =
                    jsonb_set(difficulty_distribution, '{{{diff_name}}}',
                    (COALESCE(difficulty_distribution->>'{diff_name}', '0')::int + 1)::text::jsonb)
                WHERE id = $1
            """, session_id)

    async def _get_total_reviews(self, memory_id: str) -> int:
        """Get total number of reviews for a memory."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT COUNT(*) FROM review_results WHERE memory_id = $1
            """, memory_id) or 0

    async def _get_successful_reviews(self, memory_id: str) -> int:
        """Get number of successful reviews."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT COUNT(*) FROM review_results
                WHERE memory_id = $1 AND difficulty != 1
            """, memory_id) or 0

    async def _get_average_difficulty(self, memory_id: str) -> float:
        """Get average difficulty rating."""
        async with self.pool.acquire() as conn:
            avg = await conn.fetchval("""
                SELECT AVG(difficulty) FROM review_results WHERE memory_id = $1
            """, memory_id)
            return float(avg) if avg else 3.0

    async def _get_user_performance(self, memory_id: str) -> Dict[int, float]:
        """Get user performance by hour of day."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    EXTRACT(HOUR FROM reviewed_at) as hour,
                    AVG(CASE WHEN difficulty != 1 THEN 1 ELSE 0 END) as success_rate
                FROM review_results rr
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = (SELECT user_id FROM memories WHERE id = $1)
                GROUP BY hour
            """, memory_id)

            return {int(row['hour']): row['success_rate'] for row in rows}

    async def _get_memory_priorities(self, memory_ids: List[str]) -> Dict[str, float]:
        """Get importance scores for memories."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, COALESCE(importance_score, 0.5) as priority
                FROM memories
                WHERE id = ANY($1)
            """, memory_ids)

            return {row['id']: row['priority'] for row in rows}

    def _calculate_priority(self, strength: MemoryStrength) -> float:
        """Calculate review priority based on various factors."""
        # Higher priority for:
        # - Lower retrievability (more likely to forget)
        # - Higher importance
        # - Overdue reviews

        base_priority = 1.0 - strength.retrievability

        # Adjust for overdue
        if strength.next_review and strength.next_review < datetime.utcnow():
            days_overdue = (datetime.utcnow() - strength.next_review).days
            base_priority *= (1 + 0.1 * days_overdue)  # 10% increase per day overdue

        return min(10.0, base_priority)  # Cap at 10

    async def _calculate_streak(self, user_id: str) -> Dict[str, int]:
        """Calculate current and best streaks."""
        async with self.pool.acquire() as conn:
            # Get all review dates
            dates = await conn.fetch("""
                SELECT DISTINCT DATE(reviewed_at) as review_date
                FROM review_results rr
                JOIN memories m ON rr.memory_id = m.id
                WHERE m.user_id = $1
                ORDER BY review_date DESC
            """, user_id)

            if not dates:
                return {"current": 0, "best": 0}

            # Calculate current streak
            current_streak = 0
            expected_date = datetime.utcnow().date()

            for row in dates:
                if row['review_date'] == expected_date:
                    current_streak += 1
                    expected_date -= timedelta(days=1)
                elif row['review_date'] == expected_date - timedelta(days=1):
                    # Allow one day gap
                    break
                else:
                    break

            # Calculate best streak
            best_streak = current_streak
            streak = 1

            for i in range(1, len(dates)):
                diff = (dates[i-1]['review_date'] - dates[i]['review_date']).days
                if diff == 1:
                    streak += 1
                    best_streak = max(best_streak, streak)
                else:
                    streak = 1

            return {"current": current_streak, "best": best_streak}

    async def get_session(self, session_id: str) -> ReviewSession:
        """Get review session by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM review_sessions WHERE id = $1
            """, session_id)

            if not row:
                raise ValueError(f"Session {session_id} not found")

            return ReviewSession(**dict(row))