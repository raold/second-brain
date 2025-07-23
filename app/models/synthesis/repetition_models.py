"""
Spaced Repetition Models - v2.8.2

Data models for spaced repetition learning system including algorithms,
scheduling, and learning statistics.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class RepetitionAlgorithm(str, Enum):
    """Supported spaced repetition algorithms."""

    SM2 = "sm2"  # SuperMemo 2
    ANKI = "anki"  # Anki-style algorithm
    LEITNER = "leitner"  # Leitner box system
    CUSTOM = "custom"  # Custom algorithm


class ReviewStatus(str, Enum):
    """Status of a memory review."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ReviewDifficulty(int, Enum):
    """Difficulty rating for a review."""

    AGAIN = 1  # Complete failure
    HARD = 2   # Difficult but recalled
    GOOD = 3   # Normal difficulty
    EASY = 4   # Very easy


class MemoryStrength(BaseModel):
    """Represents the strength of a memory."""

    memory_id: str = Field(..., description="Memory ID")

    # Core metrics
    ease_factor: float = Field(2.5, ge=1.3, description="Ease factor (difficulty)")
    interval: int = Field(1, ge=1, description="Current interval in days")
    repetitions: int = Field(0, ge=0, description="Number of successful reviews")

    # Performance metrics
    success_rate: float = Field(0.0, ge=0.0, le=1.0, description="Success rate")
    average_difficulty: float = Field(3.0, ge=1.0, le=4.0, description="Average difficulty")

    # Forgetting curve parameters
    retention_rate: float = Field(0.9, ge=0.0, le=1.0, description="Current retention probability")
    stability: float = Field(1.0, ge=0.1, description="Memory stability")
    retrievability: float = Field(1.0, ge=0.0, le=1.0, description="Current retrievability")

    # Timestamps
    last_review: Optional[datetime] = Field(None, description="Last review date")
    next_review: Optional[datetime] = Field(None, description="Next scheduled review")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_retrievability(self, current_time: datetime) -> float:
        """Calculate current retrievability based on forgetting curve."""
        if not self.last_review:
            return 1.0

        time_elapsed = (current_time - self.last_review).days
        # R = e^(-t/S) where t is time elapsed and S is stability
        import math
        return math.exp(-time_elapsed / self.stability)


class ReviewSchedule(BaseModel):
    """Schedule for memory reviews."""

    memory_id: str = Field(..., description="Memory ID")
    scheduled_date: datetime = Field(..., description="Scheduled review date")

    # Scheduling metadata
    interval_days: int = Field(..., description="Days until review")
    priority: float = Field(1.0, description="Review priority (higher = more important)")
    overdue_days: int = Field(0, description="Days overdue (negative if not due yet)")

    # Review window
    earliest_date: datetime = Field(..., description="Earliest review date")
    latest_date: datetime = Field(..., description="Latest review date")
    optimal_time: Optional[str] = Field(None, description="Optimal time of day for review")

    # Context
    algorithm: RepetitionAlgorithm = Field(..., description="Algorithm used")
    strength: MemoryStrength = Field(..., description="Current memory strength")

    @validator('overdue_days', always=True)
    def calculate_overdue(cls, v, values):
        """Calculate overdue days."""
        if 'scheduled_date' in values:
            days_diff = (datetime.utcnow() - values['scheduled_date']).days
            return max(0, days_diff)
        return v


class RepetitionConfig(BaseModel):
    """Configuration for spaced repetition system."""

    algorithm: RepetitionAlgorithm = Field(
        RepetitionAlgorithm.SM2,
        description="Repetition algorithm to use"
    )

    # Algorithm parameters
    initial_ease: float = Field(2.5, description="Initial ease factor")
    minimum_ease: float = Field(1.3, description="Minimum ease factor")
    easy_bonus: float = Field(1.3, description="Bonus multiplier for easy reviews")

    # Intervals
    learning_steps: List[int] = Field(
        [1, 10],  # minutes
        description="Learning steps in minutes"
    )
    graduating_interval: int = Field(1, description="First review interval in days")
    easy_interval: int = Field(4, description="Interval for 'easy' on first review")

    # Lapses
    relearning_steps: List[int] = Field(
        [10],  # minutes
        description="Relearning steps in minutes"
    )
    lapse_multiplier: float = Field(0.5, description="Interval multiplier on lapse")
    minimum_interval: int = Field(1, description="Minimum interval in days")

    # Review timing
    review_ahead_time: int = Field(20, description="Minutes to review ahead")
    bury_related: bool = Field(True, description="Bury related memories")

    # Optimization
    optimize_for_retention: float = Field(
        0.9,
        ge=0.7,
        le=0.99,
        description="Target retention rate"
    )

    # Daily limits
    new_per_day: int = Field(20, description="New memories per day")
    review_per_day: int = Field(200, description="Reviews per day")


class ReviewSession(BaseModel):
    """A review session containing multiple reviews."""

    id: Optional[str] = Field(None, description="Session ID")
    user_id: str = Field(..., description="User ID")

    # Session info
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(None, description="Session end time")
    duration_minutes: Optional[int] = Field(None, description="Session duration")

    # Reviews
    total_reviews: int = Field(0, description="Total reviews in session")
    completed_reviews: int = Field(0, description="Completed reviews")

    # Performance
    correct_count: int = Field(0, description="Correct answers")
    accuracy_rate: float = Field(0.0, description="Accuracy percentage")
    average_time_seconds: float = Field(0.0, description="Average review time")

    # Reviews by difficulty
    difficulty_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"again": 0, "hard": 0, "good": 0, "easy": 0},
        description="Distribution of difficulty ratings"
    )

    # Streaks
    current_streak: int = Field(0, description="Current correct streak")
    best_streak: int = Field(0, description="Best streak in session")


class ReviewResult(BaseModel):
    """Result of a single memory review."""

    memory_id: str = Field(..., description="Memory ID")
    session_id: str = Field(..., description="Session ID")

    # Review data
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    time_taken_seconds: int = Field(..., description="Time taken to review")
    difficulty: ReviewDifficulty = Field(..., description="Difficulty rating")

    # Before/after strength
    previous_strength: MemoryStrength = Field(..., description="Strength before review")
    new_strength: MemoryStrength = Field(..., description="Strength after review")

    # Scheduling
    next_review: datetime = Field(..., description="Next scheduled review")
    interval_change: int = Field(..., description="Change in interval (days)")

    # User feedback
    confidence_level: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="User's confidence level"
    )
    notes: Optional[str] = Field(None, description="Review notes")


class LearningStatistics(BaseModel):
    """Overall learning statistics for a user."""

    user_id: str = Field(..., description="User ID")
    period: str = Field("all_time", description="Statistics period")

    # Review statistics
    total_reviews: int = Field(0, description="Total reviews completed")
    total_time_minutes: int = Field(0, description="Total time spent reviewing")
    average_daily_reviews: float = Field(0.0, description="Average reviews per day")

    # Performance metrics
    overall_retention_rate: float = Field(0.0, description="Overall retention rate")
    mature_retention_rate: float = Field(0.0, description="Retention for mature cards")
    young_retention_rate: float = Field(0.0, description="Retention for young cards")

    # Memory statistics
    total_memories: int = Field(0, description="Total memories in system")
    mature_memories: int = Field(0, description="Memories with interval > 21 days")
    learned_today: int = Field(0, description="New memories learned today")

    # Streaks
    current_streak_days: int = Field(0, description="Current daily streak")
    best_streak_days: int = Field(0, description="Best daily streak")

    # Time distribution
    best_review_time: Optional[str] = Field(None, description="Best time for reviews")
    review_time_distribution: Dict[int, int] = Field(
        default_factory=dict,
        description="Reviews by hour of day"
    )

    # Difficulty distribution
    difficulty_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage by difficulty"
    )

    # Projections
    reviews_due_today: int = Field(0, description="Reviews due today")
    reviews_due_week: int = Field(0, description="Reviews due this week")
    workload_trend: str = Field("stable", description="Workload trend: increasing, stable, decreasing")


class BulkReviewRequest(BaseModel):
    """Request to schedule reviews for multiple memories."""

    memory_ids: List[str] = Field(..., description="Memory IDs to schedule")
    algorithm: RepetitionAlgorithm = Field(
        RepetitionAlgorithm.SM2,
        description="Algorithm to use"
    )
    config: Optional[RepetitionConfig] = Field(None, description="Custom configuration")
    distribute_over_days: Optional[int] = Field(
        None,
        description="Distribute reviews over N days"
    )
    prioritize_by: str = Field(
        "importance",
        description="Prioritization: importance, age, random"
    )