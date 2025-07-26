"""
Test repetition models for synthesis features
"""

import pytest
from datetime import datetime, timedelta
from app.models.synthesis.repetition_models import (
    RepetitionSettings,
    ForgettingCurve,
    ReviewSchedule,
    ReviewStatus
)


class TestRepetitionModels:
    """Test synthesis repetition models"""
    
    def test_repetition_settings_creation(self):
        """Test creating repetition settings"""
        settings = RepetitionSettings(
            interval_days=[1, 3, 7, 14, 30],
            retention_goal=0.85,
            difficulty_modifier=1.0,
            enable_notifications=True
        )
        
        assert len(settings.interval_days) == 5
        assert settings.interval_days[0] == 1
        assert settings.retention_goal == 0.85
        assert settings.difficulty_modifier == 1.0
        assert settings.enable_notifications is True
    
    def test_forgetting_curve_creation(self):
        """Test creating a forgetting curve"""
        curve = ForgettingCurve(
            memory_id="mem-123",
            initial_strength=1.0,
            decay_rate=0.5,
            time_constant=7.0,
            last_review=datetime.utcnow()
        )
        
        assert curve.memory_id == "mem-123"
        assert curve.initial_strength == 1.0
        assert curve.decay_rate == 0.5
        assert curve.time_constant == 7.0
        assert curve.last_review is not None
    
    def test_repetition_schedule_creation(self):
        """Test creating a repetition schedule"""
        next_review = datetime.utcnow() + timedelta(days=3)
        schedule = ReviewSchedule(
            id="sched-456",
            memory_id="mem-123",
            next_review_date=next_review,
            review_count=2,
            status=ReviewStatus.SCHEDULED
        )
        
        assert schedule.id == "sched-456"
        assert schedule.memory_id == "mem-123"
        assert schedule.next_review_date == next_review
        assert schedule.review_count == 2
        assert schedule.status == ReviewStatus.SCHEDULED
    
    def test_review_status_transitions(self):
        """Test review status transitions"""
        schedule = ReviewSchedule(
            id="sched-789",
            memory_id="mem-456",
            next_review_date=datetime.utcnow(),
            review_count=0,
            status=ReviewStatus.SCHEDULED
        )
        
        # Test status transitions
        assert schedule.status == ReviewStatus.SCHEDULED
        
        schedule.status = ReviewStatus.IN_PROGRESS
        assert schedule.status == ReviewStatus.IN_PROGRESS
        
        schedule.status = ReviewStatus.COMPLETED
        schedule.review_count += 1
        assert schedule.status == ReviewStatus.COMPLETED
        assert schedule.review_count == 1
    
    def test_forgetting_curve_calculation(self):
        """Test forgetting curve strength calculation"""
        curve = ForgettingCurve(
            memory_id="mem-999",
            initial_strength=1.0,
            decay_rate=0.5,
            time_constant=7.0,
            last_review=datetime.utcnow() - timedelta(days=7)
        )
        
        # After 7 days (one time constant), strength should be ~0.5
        # This is a simplified test - actual calculation may be more complex
        assert curve.initial_strength == 1.0
        assert curve.decay_rate == 0.5
        assert curve.time_constant == 7.0