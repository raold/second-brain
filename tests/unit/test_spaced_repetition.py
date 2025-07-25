"""
Comprehensive tests for spaced repetition scheduling system
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.synthesis.repetition_models import (
    RepetitionAlgorithm,
    RepetitionSettings,
    ReviewDifficulty,
    ReviewResult,
    ReviewStatus,
)
from app.services.synthesis.repetition_scheduler import SpacedRepetitionScheduler


@pytest.fixture
async def repetition_scheduler():
    """Create a repetition scheduler instance with mocked database."""
    mock_db = AsyncMock()
    scheduler = SpacedRepetitionScheduler(mock_db)
    return scheduler, mock_db


class TestSpacedRepetitionAlgorithms:
    """Test suite for spaced repetition algorithms."""

    async def test_sm2_algorithm(self, repetition_scheduler):
        """Test SuperMemo 2 algorithm implementation."""
        scheduler, mock_db = repetition_scheduler

        # Test initial review
        interval, ease = scheduler._calculate_sm2_interval(
            previous_interval=0,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.GOOD,
            settings=RepetitionSettings()
        )

        assert interval == 1  # First interval should be 1 day
        assert ease == 2.5  # Ease should remain the same for GOOD

        # Test subsequent reviews
        test_cases = [
            (ReviewDifficulty.AGAIN, 0, 1.3),  # Reset to 0, decrease ease
            (ReviewDifficulty.HARD, 1, 2.18),  # Minimum interval, decrease ease
            (ReviewDifficulty.GOOD, 6, 2.5),   # 2.5x interval, same ease
            (ReviewDifficulty.EASY, 10, 2.6),  # Interval with bonus, increase ease
        ]

        for difficulty, expected_min_interval, expected_ease in test_cases:
            interval, ease = scheduler._calculate_sm2_interval(
                previous_interval=2,
                ease_factor=2.5,
                difficulty=difficulty,
                settings=RepetitionSettings()
            )

            assert interval >= expected_min_interval
            assert abs(ease - expected_ease) < 0.1

    async def test_anki_algorithm(self, repetition_scheduler):
        """Test Anki algorithm implementation."""
        scheduler, mock_db = repetition_scheduler

        settings = RepetitionSettings(
            algorithm=RepetitionAlgorithm.ANKI,
            learning_steps=[1, 10],
            graduating_interval=1,
            easy_interval=4
        )

        # Test learning phase
        interval = scheduler._calculate_anki_interval(
            step=0,
            is_learning=True,
            difficulty=ReviewDifficulty.GOOD,
            settings=settings
        )

        assert interval == 10 / 1440  # 10 minutes in days

        # Test graduation
        interval = scheduler._calculate_anki_interval(
            step=1,
            is_learning=True,
            difficulty=ReviewDifficulty.GOOD,
            settings=settings
        )

        assert interval == 1  # Graduating interval

        # Test easy graduation
        interval = scheduler._calculate_anki_interval(
            step=0,
            is_learning=True,
            difficulty=ReviewDifficulty.EASY,
            settings=settings
        )

        assert interval == 4  # Easy interval

    async def test_leitner_algorithm(self, repetition_scheduler):
        """Test Leitner box system implementation."""
        scheduler, mock_db = repetition_scheduler

        settings = RepetitionSettings(
            algorithm=RepetitionAlgorithm.LEITNER,
            leitner_boxes=5
        )

        # Test box progression
        test_cases = [
            (1, ReviewDifficulty.GOOD, 2, 2),    # Box 1 -> Box 2 (2 days)
            (2, ReviewDifficulty.GOOD, 3, 4),    # Box 2 -> Box 3 (4 days)
            (3, ReviewDifficulty.GOOD, 4, 8),    # Box 3 -> Box 4 (8 days)
            (4, ReviewDifficulty.GOOD, 5, 16),   # Box 4 -> Box 5 (16 days)
            (5, ReviewDifficulty.GOOD, 5, 32),   # Box 5 stays (32 days)
            (3, ReviewDifficulty.AGAIN, 1, 1),   # Box 3 -> Box 1 (1 day)
        ]

        for current_box, difficulty, expected_box, expected_interval in test_cases:
            new_box, interval = scheduler._calculate_leitner_interval(
                current_box=current_box,
                difficulty=difficulty,
                settings=settings
            )

            assert new_box == expected_box
            assert interval == expected_interval

    async def test_schedule_review(self, repetition_scheduler):
        """Test scheduling a memory for review."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"
        memory_id = uuid4()

        # Mock database response
        mock_db.fetchrow.return_value = None  # No existing review
        mock_db.execute.return_value = None

        review = await scheduler.schedule_review(
            user_id, memory_id, RepetitionAlgorithm.SM2
        )

        assert review.memory_id == memory_id
        assert review.user_id == user_id
        assert review.algorithm == RepetitionAlgorithm.SM2
        assert review.status == ReviewStatus.SCHEDULED
        assert review.scheduled_for > datetime.utcnow()

    async def test_get_due_reviews(self, repetition_scheduler):
        """Test getting due reviews."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"

        # Mock due reviews
        mock_reviews = [
            {
                "id": str(uuid4()),
                "memory_id": str(uuid4()),
                "scheduled_for": datetime.utcnow() - timedelta(hours=1),
                "status": "overdue",
                "interval_days": 1,
                "ease_factor": 2.5,
                "review_count": 3
            },
            {
                "id": str(uuid4()),
                "memory_id": str(uuid4()),
                "scheduled_for": datetime.utcnow() + timedelta(hours=1),
                "status": "scheduled",
                "interval_days": 2,
                "ease_factor": 2.3,
                "review_count": 5
            }
        ]

        mock_db.fetch.return_value = mock_reviews

        reviews = await scheduler.get_due_reviews(user_id, limit=10)

        assert len(reviews) == 2
        assert reviews[0].status == ReviewStatus.OVERDUE
        assert reviews[1].status == ReviewStatus.SCHEDULED

    async def test_record_review(self, repetition_scheduler):
        """Test recording a review completion."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"
        review_id = uuid4()

        # Mock existing review
        mock_db.fetchrow.return_value = {
            "id": str(review_id),
            "memory_id": str(uuid4()),
            "interval_days": 2,
            "ease_factor": 2.5,
            "algorithm": "sm2",
            "review_count": 3
        }

        result = ReviewResult(
            memory_id=uuid4(),
            difficulty=ReviewDifficulty.GOOD,
            time_taken_seconds=30,
            confidence_score=0.8
        )

        # Mock settings
        with patch.object(scheduler, '_get_user_settings', return_value=RepetitionSettings()):
            next_review = await scheduler.record_review(user_id, review_id, result)

        assert next_review.interval_days > 2  # Interval should increase
        assert next_review.status == ReviewStatus.SCHEDULED
        assert mock_db.execute.called  # Should update database

    async def test_memory_strength_calculation(self, repetition_scheduler):
        """Test memory strength calculation."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"
        memory_id = uuid4()

        # Mock review history
        mock_db.fetch.return_value = [
            {
                "difficulty": "good",
                "interval_days": 1,
                "reviewed_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "difficulty": "easy",
                "interval_days": 3,
                "reviewed_at": datetime.utcnow() - timedelta(days=4)
            }
        ]

        # Mock current review
        mock_db.fetchrow.return_value = {
            "interval_days": 7,
            "ease_factor": 2.6,
            "last_reviewed": datetime.utcnow() - timedelta(days=3)
        }

        strength = await scheduler.get_memory_strength(user_id, memory_id)

        assert 0 <= strength.strength <= 1
        assert strength.stability_days > 0
        assert strength.retrievability > 0
        assert strength.review_count == 2

    async def test_review_statistics(self, repetition_scheduler):
        """Test review statistics calculation."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"

        # Mock statistics data
        mock_db.fetchrow.side_effect = [
            {"total": 100},  # Total reviews
            {"completed": 85},  # Completed reviews
            {  # Difficulty breakdown
                "again_count": 10,
                "hard_count": 20,
                "good_count": 45,
                "easy_count": 10
            },
            {"avg_interval": 5.5},  # Average interval
            {"daily_avg": 12},  # Daily average
            {"current_streak": 7, "longest_streak": 15}  # Streaks
        ]

        stats = await scheduler.get_review_statistics(user_id, "week")

        assert stats.total_reviews == 100
        assert stats.reviews_completed == 85
        assert stats.success_rate == 0.85
        assert stats.average_difficulty == pytest.approx(2.8, 0.1)
        assert stats.current_streak == 7
        assert stats.longest_streak == 15

    async def test_optimal_review_time(self, repetition_scheduler):
        """Test optimal review time calculation."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"

        # Mock performance by hour
        mock_db.fetch.return_value = [
            {"hour": 9, "avg_score": 0.85, "review_count": 50},
            {"hour": 14, "avg_score": 0.75, "review_count": 30},
            {"hour": 20, "avg_score": 0.90, "review_count": 40}
        ]

        optimal_time = await scheduler.get_optimal_review_time(user_id)

        assert optimal_time.recommended_hour == 20  # Highest performance
        assert optimal_time.performance_by_hour[20] == 0.90
        assert optimal_time.confidence_score > 0

    async def test_learning_curve_generation(self, repetition_scheduler):
        """Test learning curve generation."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"
        subject = str(uuid4())  # Memory ID

        # Mock historical data
        mock_db.fetch.return_value = [
            {
                "date": datetime.utcnow() - timedelta(days=i),
                "performance": 0.6 + (0.3 * (1 - 1/(i+1))),  # Improving over time
                "review_count": 2
            }
            for i in range(30, 0, -1)
        ]

        curve = await scheduler.generate_learning_curve(user_id, subject, 30)

        assert len(curve.data_points) == 30
        assert curve.trend == "improving"
        assert curve.current_mastery > curve.initial_mastery
        assert curve.projected_mastery > curve.current_mastery

    async def test_review_session_creation(self, repetition_scheduler):
        """Test review session creation."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"

        # Mock due reviews
        mock_db.fetch.return_value = [
            {
                "id": str(uuid4()),
                "memory_id": str(uuid4()),
                "scheduled_for": datetime.utcnow(),
                "priority_score": 0.9
            }
            for _ in range(20)
        ]

        session = await scheduler.create_review_session(
            user_id, "daily", review_limit=10
        )

        assert session.session_type == "daily"
        assert len(session.review_ids) == 10
        assert session.status == "active"
        assert session.total_reviews == 10

    async def test_fuzz_factor(self, repetition_scheduler):
        """Test fuzz factor application to intervals."""
        scheduler, mock_db = repetition_scheduler

        settings = RepetitionSettings(enable_fuzz=True)

        # Test multiple times to ensure randomness
        intervals = []
        for _ in range(10):
            interval = scheduler._apply_fuzz(10.0, settings)
            intervals.append(interval)

        # All intervals should be different due to fuzz
        assert len(set(intervals)) > 1
        # All should be within ±10% of original
        assert all(9.0 <= i <= 11.0 for i in intervals)

    async def test_settings_persistence(self, repetition_scheduler):
        """Test user settings persistence."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"

        settings = RepetitionSettings(
            user_id=user_id,
            algorithm=RepetitionAlgorithm.ANKI,
            daily_review_limit=30,
            new_memories_per_day=15,
            initial_ease=2.3,
            easy_bonus=1.5
        )

        # Test settings validation
        assert settings.algorithm == RepetitionAlgorithm.ANKI
        assert settings.daily_review_limit == 30
        assert settings.initial_ease == 2.3

    async def test_bulk_scheduling(self, repetition_scheduler):
        """Test bulk memory scheduling."""
        scheduler, mock_db = repetition_scheduler
        user_id = "test_user"
        memory_ids = [uuid4() for _ in range(5)]

        mock_db.fetchrow.return_value = None  # No existing reviews
        mock_db.execute.return_value = None

        reviews = []
        for memory_id in memory_ids:
            review = await scheduler.schedule_review(user_id, memory_id)
            reviews.append(review)

        assert len(reviews) == 5
        assert all(r.status == ReviewStatus.SCHEDULED for r in reviews)
        # Initial reviews should be spaced out
        scheduled_times = [r.scheduled_for for r in reviews]
        assert len(set(scheduled_times)) > 1


class TestSpacedRepetitionAPI:
    """Test suite for spaced repetition API endpoints."""

    @pytest.mark.asyncio
    async def test_schedule_review_endpoint(self, test_client):
        """Test scheduling a memory for review."""
        memory_id = str(uuid4())

        response = await test_client.post(
            f"/synthesis/repetition/schedule/{memory_id}",
            params={"algorithm": "sm2"},
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        review = response.json()
        assert review["memory_id"] == memory_id
        assert review["algorithm"] == "sm2"

    @pytest.mark.asyncio
    async def test_get_due_reviews_endpoint(self, test_client):
        """Test getting due reviews."""
        response = await test_client.get(
            "/synthesis/repetition/due",
            params={"limit": 20, "include_overdue": True},
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        reviews = response.json()
        assert isinstance(reviews, list)

    @pytest.mark.asyncio
    async def test_complete_review_endpoint(self, test_client):
        """Test completing a review."""
        review_id = str(uuid4())

        result_data = {
            "memory_id": str(uuid4()),
            "difficulty": "good",
            "time_taken_seconds": 25,
            "confidence_score": 0.85
        }

        response = await test_client.post(
            f"/synthesis/repetition/review/{review_id}/complete",
            json=result_data,
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        next_review = response.json()
        assert "scheduled_for" in next_review

    @pytest.mark.asyncio
    async def test_get_statistics_endpoint(self, test_client):
        """Test getting review statistics."""
        response = await test_client.get(
            "/synthesis/repetition/statistics",
            params={"period": "week"},
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        stats = response.json()
        assert "total_reviews" in stats
        assert "success_rate" in stats
        assert "current_streak" in stats
