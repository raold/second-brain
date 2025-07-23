"""
Unit tests for spaced repetition scheduler - v2.8.2
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import asyncpg

from app.models.synthesis.repetition_models import (
    RepetitionAlgorithm,
    ReviewDifficulty,
    MemoryStrength,
    RepetitionConfig,
    ReviewSchedule,
    ReviewResult,
    ReviewSession,
    LearningStatistics,
    BulkReviewRequest,
)
from app.services.synthesis.repetition_scheduler import RepetitionScheduler


class TestRepetitionScheduler:
    """Test spaced repetition scheduler service."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock database pool."""
        pool = AsyncMock(spec=asyncpg.Pool)
        return pool
    
    @pytest.fixture
    async def scheduler(self, mock_pool):
        """Create scheduler instance."""
        scheduler = RepetitionScheduler(mock_pool)
        return scheduler
    
    async def test_schedule_review_sm2(self, scheduler, mock_pool):
        """Test scheduling a review with SM2 algorithm."""
        memory_id = "mem_123"
        
        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)  # No existing schedule
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        schedule = await scheduler.schedule_review(
            memory_id,
            RepetitionAlgorithm.SM2,
            RepetitionConfig()
        )
        
        assert isinstance(schedule, ReviewSchedule)
        assert schedule.memory_id == memory_id
        assert schedule.algorithm == RepetitionAlgorithm.SM2
        assert schedule.current_strength.ease_factor == 2.5
        assert schedule.current_strength.interval == 1
        assert schedule.scheduled_date > datetime.utcnow()
    
    async def test_schedule_review_anki(self, scheduler, mock_pool):
        """Test scheduling a review with Anki algorithm."""
        memory_id = "mem_456"
        config = RepetitionConfig(
            initial_ease_factor=2.0,
            easy_bonus=1.5,
            graduating_interval=2
        )
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        schedule = await scheduler.schedule_review(
            memory_id,
            RepetitionAlgorithm.ANKI,
            config
        )
        
        assert schedule.memory_id == memory_id
        assert schedule.algorithm == RepetitionAlgorithm.ANKI
        assert schedule.current_strength.ease_factor == 2.0
    
    async def test_schedule_review_leitner(self, scheduler, mock_pool):
        """Test scheduling a review with Leitner algorithm."""
        memory_id = "mem_789"
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        schedule = await scheduler.schedule_review(
            memory_id,
            RepetitionAlgorithm.LEITNER
        )
        
        assert schedule.memory_id == memory_id
        assert schedule.algorithm == RepetitionAlgorithm.LEITNER
        assert schedule.current_strength.interval == 1  # Box 1
    
    async def test_bulk_schedule_reviews(self, scheduler, mock_pool):
        """Test bulk scheduling of reviews."""
        request = BulkReviewRequest(
            memory_ids=["mem_1", "mem_2", "mem_3"],
            algorithm=RepetitionAlgorithm.SM2,
            force_schedule=True
        )
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        schedules = await scheduler.bulk_schedule_reviews(request)
        
        assert len(schedules) == 3
        for schedule in schedules:
            assert isinstance(schedule, ReviewSchedule)
            assert schedule.algorithm == RepetitionAlgorithm.SM2
    
    async def test_get_due_reviews(self, scheduler, mock_pool):
        """Test getting due reviews."""
        # Mock database response with due reviews
        mock_reviews = [
            {
                "memory_id": "mem_1",
                "scheduled_date": datetime.utcnow() - timedelta(hours=1),
                "algorithm": "sm2",
                "ease_factor": 2.5,
                "interval": 1,
                "repetitions": 0,
                "last_review": None,
            },
            {
                "memory_id": "mem_2",
                "scheduled_date": datetime.utcnow() + timedelta(hours=1),
                "algorithm": "anki",
                "ease_factor": 2.3,
                "interval": 2,
                "repetitions": 1,
                "last_review": datetime.utcnow() - timedelta(days=2),
            },
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_reviews)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        schedules = await scheduler.get_due_reviews("user_123", limit=10)
        
        assert len(schedules) == 2
        assert schedules[0].memory_id == "mem_1"
        assert schedules[0].overdue_days == 0  # Less than a day overdue
        assert schedules[1].memory_id == "mem_2"
        assert schedules[1].overdue_days == 0  # Not overdue
    
    async def test_record_review_easy(self, scheduler, mock_pool):
        """Test recording an easy review."""
        memory_id = "mem_123"
        
        # Mock existing schedule
        mock_schedule = {
            "memory_id": memory_id,
            "algorithm": "sm2",
            "ease_factor": 2.5,
            "interval": 1,
            "repetitions": 0,
            "last_review": None,
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_schedule)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        result = await scheduler.record_review(
            memory_id,
            ReviewDifficulty.EASY,
            time_taken_seconds=5,
            session_id="session_123",
            confidence_level=0.9
        )
        
        assert isinstance(result, ReviewResult)
        assert result.memory_id == memory_id
        assert result.difficulty == ReviewDifficulty.EASY
        assert result.new_strength.interval > 1  # Interval should increase
        assert result.new_strength.ease_factor >= 2.5  # Ease should increase
        assert result.interval_change > 0
    
    async def test_record_review_hard(self, scheduler, mock_pool):
        """Test recording a hard review."""
        memory_id = "mem_456"
        
        mock_schedule = {
            "memory_id": memory_id,
            "algorithm": "sm2",
            "ease_factor": 2.5,
            "interval": 7,
            "repetitions": 3,
            "last_review": datetime.utcnow() - timedelta(days=7),
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_schedule)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        result = await scheduler.record_review(
            memory_id,
            ReviewDifficulty.HARD,
            time_taken_seconds=30,
            confidence_level=0.4
        )
        
        assert result.difficulty == ReviewDifficulty.HARD
        assert result.new_strength.ease_factor < 2.5  # Ease should decrease
        assert result.new_strength.interval < 7  # Interval should decrease
    
    async def test_record_review_again(self, scheduler, mock_pool):
        """Test recording a failed review."""
        memory_id = "mem_789"
        
        mock_schedule = {
            "memory_id": memory_id,
            "algorithm": "sm2",
            "ease_factor": 2.0,
            "interval": 10,
            "repetitions": 5,
            "last_review": datetime.utcnow() - timedelta(days=10),
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_schedule)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        result = await scheduler.record_review(
            memory_id,
            ReviewDifficulty.AGAIN,
            time_taken_seconds=60
        )
        
        assert result.difficulty == ReviewDifficulty.AGAIN
        assert result.new_strength.interval == 1  # Reset to 1 day
        assert result.new_strength.repetitions == 0  # Reset repetitions
    
    async def test_start_review_session(self, scheduler, mock_pool):
        """Test starting a review session."""
        user_id = "user_123"
        
        # Mock due reviews count
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=15)  # 15 due reviews
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        session = await scheduler.start_review_session(user_id)
        
        assert isinstance(session, ReviewSession)
        assert session.user_id == user_id
        assert session.total_reviews == 15
        assert session.completed_reviews == 0
        assert session.algorithm == RepetitionAlgorithm.SM2
    
    async def test_end_review_session(self, scheduler, mock_pool):
        """Test ending a review session."""
        session_id = "session_123"
        
        # Mock session data
        mock_session = {
            "id": session_id,
            "user_id": "user_123",
            "started_at": datetime.utcnow() - timedelta(minutes=30),
            "algorithm": "anki",
            "total_reviews": 20,
        }
        
        # Mock review statistics
        mock_stats = {
            "completed": 18,
            "correct": 15,
            "again_count": 2,
            "hard_count": 3,
            "good_count": 10,
            "easy_count": 3,
            "avg_time": 15.5,
            "total_time": 279,
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=[mock_session, mock_stats])
        mock_conn.execute = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        session = await scheduler.end_review_session(session_id)
        
        assert session.id == session_id
        assert session.completed_reviews == 18
        assert session.correct_reviews == 15
        assert session.average_time_seconds == 15.5
        assert isinstance(session.ended_at, datetime)
        assert session.statistics.good_count == 10
    
    async def test_get_learning_statistics(self, scheduler, mock_pool):
        """Test getting learning statistics."""
        user_id = "user_123"
        
        # Mock statistics data
        mock_data = {
            "total_memories": 500,
            "scheduled_memories": 450,
            "overdue_memories": 25,
            "total_reviews": 2000,
            "perfect_reviews": 1700,
            "streak_days": 10,
            "best_streak": 30,
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_data)
        mock_conn.fetch = AsyncMock(return_value=[])  # Empty forgetting curves
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        stats = await scheduler.get_learning_statistics(user_id, "month")
        
        assert isinstance(stats, LearningStatistics)
        assert stats.total_memories == 500
        assert stats.scheduled_memories == 450
        assert stats.overdue_memories == 25
        assert stats.average_retention_rate == 0.85  # 1700/2000
        assert stats.streak_days == 10
    
    def test_sm2_algorithm(self, scheduler):
        """Test SM2 algorithm implementation."""
        # Test easy response
        new_interval, new_ease = scheduler._sm2_algorithm(
            current_interval=1,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.EASY,
            repetitions=0
        )
        
        assert new_interval == 1  # First repetition
        assert new_ease > 2.5  # Ease increases for easy
        
        # Test good response after several repetitions
        new_interval, new_ease = scheduler._sm2_algorithm(
            current_interval=6,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.GOOD,
            repetitions=3
        )
        
        assert new_interval == 15  # 6 * 2.5
        assert new_ease == 2.5  # No change for good
        
        # Test hard response
        new_interval, new_ease = scheduler._sm2_algorithm(
            current_interval=10,
            ease_factor=2.0,
            difficulty=ReviewDifficulty.HARD,
            repetitions=5
        )
        
        assert new_interval < 10  # Interval decreases
        assert new_ease < 2.0  # Ease decreases
        
        # Test again response
        new_interval, new_ease = scheduler._sm2_algorithm(
            current_interval=20,
            ease_factor=1.8,
            difficulty=ReviewDifficulty.AGAIN,
            repetitions=10
        )
        
        assert new_interval == 1  # Reset to 1
        assert new_ease < 1.8  # Ease decreases further
    
    def test_anki_algorithm(self, scheduler):
        """Test Anki algorithm implementation."""
        config = RepetitionConfig(
            easy_bonus=1.3,
            hard_factor=0.8,
            learning_steps=[1, 10]
        )
        
        # Test learning phase
        new_interval, new_ease = scheduler._anki_algorithm(
            current_interval=1,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.GOOD,
            repetitions=0,
            config=config
        )
        
        assert new_interval == 10  # Next learning step
        
        # Test graduating from learning
        new_interval, new_ease = scheduler._anki_algorithm(
            current_interval=10,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.GOOD,
            repetitions=1,
            config=config
        )
        
        assert new_interval == config.graduating_interval
        
        # Test review phase with easy
        new_interval, new_ease = scheduler._anki_algorithm(
            current_interval=5,
            ease_factor=2.5,
            difficulty=ReviewDifficulty.EASY,
            repetitions=3,
            config=config
        )
        
        assert new_interval == int(5 * 2.5 * config.easy_bonus)
    
    def test_leitner_algorithm(self, scheduler):
        """Test Leitner algorithm implementation."""
        # Test promotion (good/easy)
        new_interval, box = scheduler._leitner_algorithm(
            current_interval=1,  # Box 1
            difficulty=ReviewDifficulty.GOOD
        )
        
        assert new_interval == 3  # Box 2
        assert box == 2.5  # Using ease_factor to track box
        
        # Test demotion (again)
        new_interval, box = scheduler._leitner_algorithm(
            current_interval=7,  # Box 3
            difficulty=ReviewDifficulty.AGAIN
        )
        
        assert new_interval == 1  # Back to Box 1
        assert box == 2.5  # Default ease
        
        # Test staying in same box (hard)
        new_interval, box = scheduler._leitner_algorithm(
            current_interval=3,  # Box 2
            difficulty=ReviewDifficulty.HARD
        )
        
        assert new_interval == 3  # Stay in Box 2
        assert box == 2.5
    
    def test_calculate_forgetting_curve(self, scheduler):
        """Test forgetting curve calculation."""
        initial_retention = 1.0
        stability = 2.0
        
        # Test retention over time
        retention_day1 = scheduler._calculate_retention(1, stability, initial_retention)
        retention_day7 = scheduler._calculate_retention(7, stability, initial_retention)
        retention_day30 = scheduler._calculate_retention(30, stability, initial_retention)
        
        assert 0 < retention_day30 < retention_day7 < retention_day1 <= 1.0
        assert retention_day1 > 0.5  # Should retain > 50% after 1 day
        assert retention_day30 < 0.5  # Should retain < 50% after 30 days