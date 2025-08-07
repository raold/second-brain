"""Repetition models for spaced repetition and review scheduling"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Status of memory review"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class RepetitionSettings(BaseModel):
    """Settings for spaced repetition"""
    initial_interval_days: int = 1
    multiplier: float = 2.5
    minimum_interval_days: int = 1
    maximum_interval_days: int = 365
    ease_bonus: float = 1.3
    ease_penalty: float = 0.8
    graduation_interval_days: int = 21


class ForgettingCurve(BaseModel):
    """Model for forgetting curve calculations"""
    memory_id: str
    retention_strength: float = 1.0
    last_review: Optional[datetime] = None
    review_count: int = 0
    ease_factor: float = 2.5
    interval_days: int = 1
    next_review: Optional[datetime] = None
    
    def calculate_next_review(self) -> datetime:
        """Calculate next review date based on current parameters"""
        if self.last_review is None:
            return datetime.now()
        return self.last_review + timedelta(days=self.interval_days)


class ReviewSchedule(BaseModel):
    """Schedule for memory reviews"""
    schedule_id: str = Field(default_factory=lambda: f"rev_{datetime.now().timestamp()}")
    memory_id: str
    user_id: str
    scheduled_date: datetime
    status: ReviewStatus = ReviewStatus.PENDING
    difficulty_rating: Optional[float] = None
    time_spent_seconds: Optional[float] = None
    notes: Optional[str] = None
    forgetting_curve: Optional[ForgettingCurve] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None