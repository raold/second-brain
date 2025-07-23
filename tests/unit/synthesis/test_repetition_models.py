"""
Unit tests for spaced repetition models - v2.8.2
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.models.synthesis.repetition_models import (
    RepetitionAlgorithm,
    ReviewDifficulty,
    MemoryStrength,
    RepetitionConfig,
    ReviewSchedule,
    ReviewResult,
    ReviewSession,
    SessionStatistics,
    LearningStatistics,
    ForgettingCurve,
    BulkReviewRequest,
)


class TestRepetitionModels:
    """Test spaced repetition models."""
    
    def test_repetition_algorithm_enum(self):
        """Test RepetitionAlgorithm enum values."""
        assert RepetitionAlgorithm.SM2.value == "sm2"
        assert RepetitionAlgorithm.ANKI.value == "anki"
        assert RepetitionAlgorithm.LEITNER.value == "leitner"
        assert RepetitionAlgorithm.CUSTOM.value == "custom"
    
    def test_review_difficulty_enum(self):
        """Test ReviewDifficulty enum values."""
        assert ReviewDifficulty.AGAIN.value == "again"
        assert ReviewDifficulty.HARD.value == "hard"
        assert ReviewDifficulty.GOOD.value == "good"
        assert ReviewDifficulty.EASY.value == "easy"
    
    def test_memory_strength_model(self):
        """Test MemoryStrength model."""
        strength = MemoryStrength(
            ease_factor=2.5,
            interval=1,
            repetitions=0,
            retention_rate=0.9,
            stability=1.0,
            last_review=datetime.utcnow()
        )
        
        assert strength.ease_factor == 2.5
        assert strength.interval == 1
        assert strength.repetitions == 0
        assert strength.retention_rate == 0.9
        assert strength.stability == 1.0
        assert isinstance(strength.last_review, datetime)
    
    def test_memory_strength_validation(self):
        """Test MemoryStrength validation."""
        # Valid ease factor range
        MemoryStrength(ease_factor=1.3)  # Minimum
        MemoryStrength(ease_factor=5.0)  # Maximum
        
        # Invalid ease factor
        with pytest.raises(ValidationError):
            MemoryStrength(ease_factor=1.2)  # Too low
        
        with pytest.raises(ValidationError):
            MemoryStrength(ease_factor=5.1)  # Too high
        
        # Invalid interval
        with pytest.raises(ValidationError):
            MemoryStrength(interval=0)
        
        # Invalid retention rate
        with pytest.raises(ValidationError):
            MemoryStrength(retention_rate=-0.1)
        
        with pytest.raises(ValidationError):
            MemoryStrength(retention_rate=1.1)
    
    def test_repetition_config_model(self):
        """Test RepetitionConfig model."""
        config = RepetitionConfig(
            initial_ease_factor=2.5,
            minimum_ease_factor=1.3,
            easy_bonus=1.3,
            hard_factor=0.8,
            again_factor=0.5,
            learning_steps=[1, 10],
            graduating_interval=1,
            easy_interval=4,
            maximum_interval=365,
            leech_threshold=8,
            leech_action="suspend"
        )
        
        assert config.initial_ease_factor == 2.5
        assert config.easy_bonus == 1.3
        assert len(config.learning_steps) == 2
        assert config.maximum_interval == 365
        assert config.leech_action == "suspend"
    
    def test_repetition_config_defaults(self):
        """Test RepetitionConfig default values."""
        config = RepetitionConfig()
        
        assert config.initial_ease_factor == 2.5
        assert config.minimum_ease_factor == 1.3
        assert config.easy_bonus == 1.3
        assert config.hard_factor == 0.8
        assert config.again_factor == 0.5
        assert config.learning_steps == [1, 10]
        assert config.graduating_interval == 1
        assert config.easy_interval == 4
        assert config.maximum_interval == 365
        assert config.leech_threshold == 8
        assert config.leech_action == "suspend"
    
    def test_review_schedule_model(self):
        """Test ReviewSchedule model."""
        scheduled_date = datetime.utcnow() + timedelta(days=1)
        schedule = ReviewSchedule(
            memory_id="mem_123",
            scheduled_date=scheduled_date,
            algorithm=RepetitionAlgorithm.SM2,
            current_strength=MemoryStrength(),
            overdue_days=0,
            priority_score=0.8
        )
        
        assert schedule.memory_id == "mem_123"
        assert schedule.scheduled_date == scheduled_date
        assert schedule.algorithm == RepetitionAlgorithm.SM2
        assert schedule.overdue_days == 0
        assert schedule.priority_score == 0.8
        assert isinstance(schedule.created_at, datetime)
    
    def test_review_result_model(self):
        """Test ReviewResult model."""
        result = ReviewResult(
            memory_id="mem_123",
            difficulty=ReviewDifficulty.GOOD,
            previous_strength=MemoryStrength(),
            new_strength=MemoryStrength(interval=3),
            next_review=datetime.utcnow() + timedelta(days=3),
            interval_change=2,
            time_taken_seconds=10,
            confidence_level=0.8
        )
        
        assert result.memory_id == "mem_123"
        assert result.difficulty == ReviewDifficulty.GOOD
        assert result.new_strength.interval == 3
        assert result.interval_change == 2
        assert result.time_taken_seconds == 10
        assert result.confidence_level == 0.8
        assert isinstance(result.reviewed_at, datetime)
    
    def test_review_session_model(self):
        """Test ReviewSession model."""
        session = ReviewSession(
            id="session_123",
            user_id="user_123",
            algorithm=RepetitionAlgorithm.ANKI,
            total_reviews=10,
            completed_reviews=5,
            correct_reviews=4,
            average_time_seconds=15.5,
            statistics=SessionStatistics()
        )
        
        assert session.id == "session_123"
        assert session.user_id == "user_123"
        assert session.algorithm == RepetitionAlgorithm.ANKI
        assert session.total_reviews == 10
        assert session.completed_reviews == 5
        assert session.correct_reviews == 4
        assert session.average_time_seconds == 15.5
        assert isinstance(session.started_at, datetime)
    
    def test_session_statistics_model(self):
        """Test SessionStatistics model."""
        stats = SessionStatistics(
            again_count=2,
            hard_count=3,
            good_count=10,
            easy_count=5,
            average_ease_change=-0.1,
            average_interval_change=2.5,
            retention_rate=0.85,
            total_time_seconds=300
        )
        
        assert stats.again_count == 2
        assert stats.hard_count == 3
        assert stats.good_count == 10
        assert stats.easy_count == 5
        assert stats.average_ease_change == -0.1
        assert stats.average_interval_change == 2.5
        assert stats.retention_rate == 0.85
        assert stats.total_time_seconds == 300
    
    def test_learning_statistics_model(self):
        """Test LearningStatistics model."""
        stats = LearningStatistics(
            total_memories=1000,
            scheduled_memories=800,
            overdue_memories=50,
            average_retention_rate=0.87,
            daily_review_goal=20,
            streak_days=15,
            best_streak_days=30,
            total_reviews=5000,
            perfect_reviews=4000,
            learning_velocity=3.5,
            forgetting_curves=[
                ForgettingCurve(
                    days=[1, 2, 3, 4, 5],
                    retention_rates=[0.9, 0.8, 0.7, 0.6, 0.5]
                )
            ],
            difficulty_distribution={
                "again": 0.1,
                "hard": 0.2,
                "good": 0.5,
                "easy": 0.2
            },
            time_distribution={
                "morning": 0.3,
                "afternoon": 0.4,
                "evening": 0.3
            }
        )
        
        assert stats.total_memories == 1000
        assert stats.scheduled_memories == 800
        assert stats.overdue_memories == 50
        assert stats.average_retention_rate == 0.87
        assert stats.daily_review_goal == 20
        assert stats.streak_days == 15
        assert stats.best_streak_days == 30
        assert stats.learning_velocity == 3.5
        assert len(stats.forgetting_curves) == 1
        assert sum(stats.difficulty_distribution.values()) == 1.0
        assert sum(stats.time_distribution.values()) == 1.0
    
    def test_forgetting_curve_model(self):
        """Test ForgettingCurve model."""
        curve = ForgettingCurve(
            days=[1, 2, 3, 4, 5, 6, 7],
            retention_rates=[0.9, 0.82, 0.75, 0.68, 0.62, 0.56, 0.51],
            algorithm=RepetitionAlgorithm.SM2,
            sample_size=100
        )
        
        assert len(curve.days) == 7
        assert len(curve.retention_rates) == 7
        assert curve.algorithm == RepetitionAlgorithm.SM2
        assert curve.sample_size == 100
        
        # Test validation - arrays must be same length
        with pytest.raises(ValidationError):
            ForgettingCurve(
                days=[1, 2, 3],
                retention_rates=[0.9, 0.8]  # Mismatched length
            )
    
    def test_bulk_review_request_model(self):
        """Test BulkReviewRequest model."""
        request = BulkReviewRequest(
            memory_ids=["mem_1", "mem_2", "mem_3"],
            algorithm=RepetitionAlgorithm.ANKI,
            config=RepetitionConfig(initial_ease_factor=2.0),
            force_schedule=True
        )
        
        assert len(request.memory_ids) == 3
        assert request.algorithm == RepetitionAlgorithm.ANKI
        assert request.config.initial_ease_factor == 2.0
        assert request.force_schedule is True
    
    def test_bulk_review_request_defaults(self):
        """Test BulkReviewRequest default values."""
        request = BulkReviewRequest(
            memory_ids=["mem_1"]
        )
        
        assert len(request.memory_ids) == 1
        assert request.algorithm == RepetitionAlgorithm.SM2
        assert request.config is None
        assert request.force_schedule is False


class TestRepetitionModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_memory_strength_serialization(self):
        """Test MemoryStrength serialization."""
        strength = MemoryStrength(
            ease_factor=2.8,
            interval=7,
            repetitions=3,
            retention_rate=0.85
        )
        
        # Serialize
        data = strength.dict()
        assert data["ease_factor"] == 2.8
        assert data["interval"] == 7
        assert data["repetitions"] == 3
        assert data["retention_rate"] == 0.85
        
        # Deserialize
        strength2 = MemoryStrength(**data)
        assert strength2.ease_factor == 2.8
        assert strength2.interval == 7
    
    def test_review_result_json_serialization(self):
        """Test ReviewResult JSON serialization."""
        result = ReviewResult(
            memory_id="test_123",
            difficulty=ReviewDifficulty.HARD,
            previous_strength=MemoryStrength(),
            new_strength=MemoryStrength(interval=2),
            next_review=datetime.utcnow() + timedelta(days=2),
            interval_change=1,
            time_taken_seconds=20
        )
        
        # Serialize to JSON
        json_data = result.json()
        assert "test_123" in json_data
        assert "hard" in json_data
        
        # Parse back
        import json
        data = json.loads(json_data)
        assert data["memory_id"] == "test_123"
        assert data["difficulty"] == "hard"
        assert data["interval_change"] == 1
    
    def test_learning_statistics_serialization(self):
        """Test LearningStatistics serialization."""
        stats = LearningStatistics(
            total_memories=500,
            scheduled_memories=400,
            forgetting_curves=[
                ForgettingCurve(
                    days=[1, 2, 3],
                    retention_rates=[0.9, 0.7, 0.5]
                )
            ]
        )
        
        # Serialize
        data = stats.dict()
        assert data["total_memories"] == 500
        assert data["scheduled_memories"] == 400
        assert len(data["forgetting_curves"]) == 1
        assert len(data["forgetting_curves"][0]["days"]) == 3
        
        # Deserialize
        stats2 = LearningStatistics(**data)
        assert stats2.total_memories == 500
        assert len(stats2.forgetting_curves) == 1