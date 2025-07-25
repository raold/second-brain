"""
Data models for spaced repetition scheduling
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RepetitionAlgorithm(str, Enum):
    """Spaced repetition algorithms"""
    SM2 = "sm2"  # SuperMemo 2
    ANKI = "anki"  # Anki's algorithm
    LEITNER = "leitner"  # Leitner box system
    CUSTOM = "custom"  # Custom algorithm


class ReviewDifficulty(str, Enum):
    """Review difficulty ratings"""
    AGAIN = "again"  # Complete blackout
    HARD = "hard"  # Difficult recall
    GOOD = "good"  # Correct with hesitation
    EASY = "easy"  # Perfect recall


class ReviewStatus(str, Enum):
    """Status of scheduled reviews"""
    PENDING = "pending"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    SUSPENDED = "suspended"


class MemoryStrength(BaseModel):
    """Current strength of a memory"""
    memory_id: UUID
    stability: float = Field(..., ge=0.0, description="Days until 90% retention")
    difficulty: float = Field(..., ge=0.0, le=1.0, description="Inherent difficulty")
    retrievability: float = Field(..., ge=0.0, le=1.0, description="Current recall probability")
    last_review: Optional[datetime] = None
    next_review: datetime
    review_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "123e4567-e89b-12d3-a456-426614174000",
                "stability": 2.5,
                "difficulty": 0.3,
                "retrievability": 0.85,
                "last_review": "2025-01-20T10:00:00Z",
                "next_review": "2025-01-23T10:00:00Z",
                "review_count": 5,
                "success_rate": 0.8
            }
        }


class ScheduledReview(BaseModel):
    """A scheduled review for a memory"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    memory_id: UUID
    scheduled_for: datetime
    review_window: timedelta = Field(default=timedelta(hours=8), description="Flexibility window")
    status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    algorithm: RepetitionAlgorithm
    interval_days: float = Field(..., ge=0, description="Days since last review")
    ease_factor: float = Field(default=2.5, ge=1.3, description="SM2 ease factor")
    lapses: int = Field(default=0, ge=0, description="Number of failures")
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def is_overdue(self) -> bool:
        """Check if review is overdue"""
        return (
            self.status == ReviewStatus.PENDING and
            datetime.utcnow() > self.scheduled_for + self.review_window
        )


class ReviewSession(BaseModel):
    """A review session containing multiple reviews"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    session_type: str = Field(..., pattern="^(daily|focus|catch_up|custom)$")
    reviews: list[ScheduledReview]
    total_reviews: int
    completed_reviews: int = Field(default=0)
    average_difficulty: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_duration_minutes: int
    actual_duration_minutes: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def completion_rate(self) -> float:
        """Calculate session completion rate"""
        if self.total_reviews == 0:
            return 0.0
        return self.completed_reviews / self.total_reviews


class ReviewResult(BaseModel):
    """Result of a single review"""
    review_id: UUID
    memory_id: UUID
    difficulty: ReviewDifficulty
    time_taken_seconds: int = Field(..., ge=0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    recalled_correctly: bool
    notes: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewHistory(BaseModel):
    """Historical review data for a memory"""
    memory_id: UUID
    reviews: list[dict[str, Any]]  # List of review results
    total_reviews: int
    successful_reviews: int
    average_difficulty: float
    average_interval: float  # Days
    last_review: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_reviews == 0:
            return 0.0
        return self.successful_reviews / self.total_reviews


class RepetitionSettings(BaseModel):
    """User settings for spaced repetition"""
    user_id: str
    algorithm: RepetitionAlgorithm = Field(default=RepetitionAlgorithm.SM2)
    daily_review_limit: int = Field(default=20, ge=1, le=200)
    new_memories_per_day: int = Field(default=10, ge=1, le=50)

    # Time preferences
    preferred_review_time: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="UTC")

    # Algorithm parameters
    initial_ease: float = Field(default=2.5, ge=1.3, le=4.0)
    easy_bonus: float = Field(default=1.3, ge=1.0, le=2.0)
    hard_penalty: float = Field(default=0.8, ge=0.5, le=1.0)

    # Learning steps (minutes)
    learning_steps: list[int] = Field(default=[1, 10], min_items=1)
    relearning_steps: list[int] = Field(default=[10], min_items=1)

    # Lapse handling
    lapse_new_interval: float = Field(default=0.0, ge=0.0, le=1.0, description="Multiplier for new interval after lapse")

    # Features
    bury_related: bool = Field(default=True, description="Bury related memories after review")
    enable_fuzz: bool = Field(default=True, description="Add randomness to intervals")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewSchedule(BaseModel):
    """Complete review schedule for a user"""
    user_id: str
    date: datetime

    # Reviews by category
    new_reviews: list[ScheduledReview] = Field(default_factory=list)
    learning_reviews: list[ScheduledReview] = Field(default_factory=list)
    due_reviews: list[ScheduledReview] = Field(default_factory=list)
    overdue_reviews: list[ScheduledReview] = Field(default_factory=list)

    # Statistics
    total_scheduled: int
    estimated_time_minutes: int

    # Suggestions
    optimal_review_time: Optional[datetime] = None
    suggested_order: list[UUID] = Field(default_factory=list)

    @property
    def all_reviews(self) -> list[ScheduledReview]:
        """Get all reviews in suggested order"""
        return self.overdue_reviews + self.due_reviews + self.learning_reviews + self.new_reviews


class ReviewStatistics(BaseModel):
    """Statistics for spaced repetition performance"""
    user_id: str
    period: str  # "day", "week", "month", "all_time"

    # Review counts
    reviews_completed: int
    reviews_due: int
    reviews_overdue: int

    # Performance metrics
    average_success_rate: float
    average_ease: float
    average_interval: float  # Days
    retention_rate: float

    # Time metrics
    total_time_minutes: int
    average_time_per_review: float  # Seconds

    # Streaks
    current_streak: int
    longest_streak: int

    # By difficulty
    difficulty_breakdown: dict[str, int]  # ReviewDifficulty -> count

    # Progress
    mature_memories: int  # Interval > 21 days
    young_memories: int   # Interval < 21 days
    learning_memories: int  # In learning phase

    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class OptimalReviewTime(BaseModel):
    """Optimal time for reviews based on user patterns"""
    user_id: str
    recommended_time: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Factors
    historical_success_by_hour: dict[int, float]  # Hour -> success rate
    historical_volume_by_hour: dict[int, int]  # Hour -> review count
    circadian_score: float = Field(..., ge=0.0, le=1.0)

    # Reasoning
    reasoning: list[str]
    alternative_times: list[datetime] = Field(default_factory=list, max_items=3)


class ReviewReminder(BaseModel):
    """Reminder for upcoming reviews"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    scheduled_for: datetime
    review_count: int
    estimated_duration_minutes: int
    message: str
    sent: bool = Field(default=False)
    sent_at: Optional[datetime] = None
    channels: list[str] = Field(default_factory=list)  # "email", "push", "in_app"


class LearningCurve(BaseModel):
    """Learning curve analysis for a topic or memory"""
    subject: str  # Topic or memory ID
    data_points: list[dict[str, Any]]  # [{date, retention_rate, review_count}]

    # Curve parameters
    initial_learning_rate: float
    plateau_level: float
    time_to_plateau_days: int

    # Current state
    current_retention: float
    current_stability: float
    predicted_retention_7d: float
    predicted_retention_30d: float

    # Recommendations
    optimal_review_frequency: str
    suggested_modifications: list[str]
