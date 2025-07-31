"""
Spaced Repetition Models - v2.8.2

Data models for spaced repetition learning system including algorithms,
scheduling, and learning statistics.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RepetitionAlgorithm(str, Enum):
    """Supported spaced repetition algorithms."""

    SM2 = "sm2"  # SuperMemo 2
    ANKI = "anki"  # Anki-style algorithm
    LEITNER = "leitner"  # Leitner box system
    CUSTOM = "custom"  # Custom algorithm


class ReviewStatus(str, Enum):
    """Status of a memory review."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ReviewDifficulty(str, Enum):
    """Difficulty rating for a review."""

    AGAIN = "again"  # Complete failure
    HARD = "hard"   # Difficult but recalled
    GOOD = "good"   # Normal difficulty
    EASY = "easy"   # Very easy


class RepetitionSettings(BaseModel):
    """Settings for spaced repetition system"""
    algorithm: str = Field(default="sm2")
    initial_interval: int = Field(default=1, gt=0)
    easy_multiplier: float = Field(default=2.5, gt=1)
    hard_multiplier: float = Field(default=0.5, gt=0, lt=1)
    
    # Additional fields expected by tests
    interval_days: List[int] = Field(default_factory=lambda: [1, 3, 7, 14, 30])
    retention_goal: float = Field(default=0.9, ge=0.0, le=1.0)
    difficulty_modifier: float = Field(default=1.0, gt=0)
    enable_notifications: bool = Field(default=True)


class ForgettingCurve(BaseModel):
    """Model for forgetting curve calculations"""
    days: List[int] = Field(default_factory=list, description="Days after review")
    retention_rates: List[float] = Field(default_factory=list, description="Retention rates at each day")
    algorithm: Optional[RepetitionAlgorithm] = Field(None, description="Algorithm used")
    sample_size: Optional[int] = Field(None, description="Number of samples")
    
    # Additional fields expected by tests
    memory_id: Optional[str] = Field(None, description="Memory ID")
    initial_strength: float = Field(1.0, ge=0.0, le=1.0, description="Initial memory strength")
    decay_rate: float = Field(0.5, gt=0.0, le=1.0, description="Decay rate")
    time_constant: float = Field(7.0, gt=0, description="Time constant in days")
    last_review: Optional[datetime] = Field(None, description="Last review date")
    
    @field_validator('retention_rates')
    def validate_same_length(cls, v, info):
        """Ensure days and retention_rates have same length"""
        if info.data.get('days') and len(v) != len(info.data['days']):
            raise ValueError("days and retention_rates must have same length")
        return v
    
    def calculate_retention(self, day: int) -> float:
        """Calculate retention for specific day"""
        if day in self.days:
            idx = self.days.index(day)
            return self.retention_rates[idx]
        # Use forgetting curve formula with new fields
        import math
        if self.last_review and self.time_constant > 0:
            # Use Ebbinghaus forgetting curve: R = e^(-t/s) where t is time, s is strength
            return self.initial_strength * math.exp(-day * self.decay_rate / self.time_constant)
        elif self.retention_rates:
            return self.retention_rates[0] * math.exp(-day / 30)
        return 0.9 * math.exp(-day / 30)


class SessionStatistics(BaseModel):
    """Statistics for a review session"""
    # Basic counts
    total_reviewed: int = Field(default=0, ge=0)
    correct_answers: int = Field(default=0, ge=0)
    
    # Difficulty counts
    again_count: int = Field(default=0, ge=0)
    hard_count: int = Field(default=0, ge=0)
    good_count: int = Field(default=0, ge=0)
    easy_count: int = Field(default=0, ge=0)
    
    # Performance metrics
    average_difficulty: float = Field(default=0.0, ge=0, le=5)
    average_time_per_card: float = Field(default=0.0, ge=0)
    session_duration: float = Field(default=0.0, ge=0)
    average_ease_change: float = Field(default=0.0)
    average_interval_change: float = Field(default=0.0)
    retention_rate: float = Field(default=0.0, ge=0, le=1)
    total_time_seconds: int = Field(default=0, ge=0)
    
    @property
    def accuracy_rate(self) -> float:
        if self.total_reviewed == 0:
            return 0.0
        return self.correct_answers / self.total_reviewed


class MemoryStrength(BaseModel):
    """Represents the strength of a memory."""

    memory_id: Optional[str] = Field(None, description="Memory ID")

    # Core metrics
    ease_factor: float = Field(2.5, ge=1.3, le=5.0, description="Ease factor (difficulty)")
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
    
    # Primary fields expected by tests
    id: Optional[str] = Field(None, description="Schedule ID")
    memory_id: str = Field(..., description="Memory ID")
    next_review_date: datetime = Field(..., description="Next review date")
    review_count: int = Field(0, description="Number of reviews completed")
    status: ReviewStatus = Field(ReviewStatus.SCHEDULED, description="Review status")
    
    # Original fields for backward compatibility
    scheduled_date: Optional[datetime] = Field(None, description="Scheduled review date")
    interval_days: Optional[int] = Field(None, description="Days until review")
    priority_score: float = Field(1.0, description="Review priority (higher = more important)")
    overdue_days: int = Field(0, description="Days overdue (negative if not due yet)")
    earliest_date: Optional[datetime] = Field(None, description="Earliest review date")
    latest_date: Optional[datetime] = Field(None, description="Latest review date")
    optimal_time: Optional[str] = Field(None, description="Optimal time of day for review")
    algorithm: Optional[RepetitionAlgorithm] = Field(None, description="Algorithm used")
    current_strength: Optional[MemoryStrength] = Field(None, description="Current memory strength")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('overdue_days', mode='before')
    def calculate_overdue(cls, v, info):
        """Calculate overdue days."""
        if info.data.get('next_review_date'):
            days_diff = (datetime.utcnow() - info.data['next_review_date']).days
            return max(0, days_diff)
        elif info.data.get('scheduled_date'):
            days_diff = (datetime.utcnow() - info.data['scheduled_date']).days
            return max(0, days_diff)
        return v


class RepetitionConfig(BaseModel):
    """Configuration for spaced repetition system."""

    algorithm: RepetitionAlgorithm = Field(
        RepetitionAlgorithm.SM2,
        description="Repetition algorithm to use"
    )

    # Algorithm parameters
    initial_ease_factor: float = Field(2.5, description="Initial ease factor")
    minimum_ease_factor: float = Field(1.3, description="Minimum ease factor")
    easy_bonus: float = Field(1.3, description="Bonus multiplier for easy reviews")
    hard_factor: float = Field(0.8, description="Factor for hard reviews")
    again_factor: float = Field(0.5, description="Factor for again reviews")

    # Intervals
    learning_steps: list[int] = Field(
        [1, 10],  # minutes
        description="Learning steps in minutes"
    )
    graduating_interval: int = Field(1, description="First review interval in days")
    easy_interval: int = Field(4, description="Interval for 'easy' on first review")

    # Lapses
    relearning_steps: list[int] = Field(
        [10],  # minutes
        description="Relearning steps in minutes"
    )
    lapse_multiplier: float = Field(0.5, description="Interval multiplier on lapse")
    minimum_interval: int = Field(1, description="Minimum interval in days")
    maximum_interval: int = Field(365, description="Maximum interval in days")
    
    # Leech handling
    leech_threshold: int = Field(8, description="Number of lapses before marking as leech")
    leech_action: str = Field("suspend", description="Action to take for leeches")

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
    
    # Algorithm
    algorithm: Optional[RepetitionAlgorithm] = Field(None, description="Algorithm used")

    # Session info
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(None, description="Session end time")
    duration_minutes: Optional[int] = Field(None, description="Session duration")

    # Reviews
    total_reviews: int = Field(0, description="Total reviews in session")
    completed_reviews: int = Field(0, description="Completed reviews")
    
    # Additional fields from test
    correct_reviews: Optional[int] = Field(None, description="Number of correct reviews")
    statistics: Optional[SessionStatistics] = Field(None, description="Session statistics")

    # Performance
    correct_count: int = Field(0, description="Correct answers")
    accuracy_rate: float = Field(0.0, description="Accuracy percentage")
    average_time_seconds: float = Field(0.0, description="Average review time")

    # Reviews by difficulty
    difficulty_distribution: dict[str, int] = Field(
        default_factory=lambda: {"again": 0, "hard": 0, "good": 0, "easy": 0},
        description="Distribution of difficulty ratings"
    )

    # Streaks
    current_streak: int = Field(0, description="Current correct streak")
    best_streak: int = Field(0, description="Best streak in session")


class ReviewResult(BaseModel):
    """Result of a single memory review."""

    memory_id: str = Field(..., description="Memory ID")
    session_id: Optional[str] = Field(None, description="Session ID")

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

    user_id: Optional[str] = Field(None, description="User ID")
    period: Optional[str] = Field("all_time", description="Statistics period")

    # Memory statistics
    total_memories: int = Field(0, description="Total memories in system")
    scheduled_memories: int = Field(0, description="Scheduled memories")
    overdue_memories: int = Field(0, description="Overdue memories")
    mature_memories: int = Field(0, description="Memories with interval > 21 days")
    learned_today: int = Field(0, description="New memories learned today")

    # Review statistics
    total_reviews: int = Field(0, description="Total reviews completed")
    perfect_reviews: int = Field(0, description="Perfect reviews")
    total_time_minutes: int = Field(0, description="Total time spent reviewing")
    average_daily_reviews: float = Field(0.0, description="Average reviews per day")

    # Performance metrics
    average_retention_rate: float = Field(0.0, description="Average retention rate")
    overall_retention_rate: float = Field(0.0, description="Overall retention rate")
    mature_retention_rate: float = Field(0.0, description="Retention for mature cards")
    young_retention_rate: float = Field(0.0, description="Retention for young cards")
    
    # Learning metrics
    learning_velocity: float = Field(0.0, description="Learning velocity")
    daily_review_goal: int = Field(0, description="Daily review goal")

    # Streaks
    streak_days: int = Field(0, description="Current daily streak")
    current_streak_days: int = Field(0, description="Current daily streak")
    best_streak_days: int = Field(0, description="Best daily streak")

    # Time distribution
    best_review_time: Optional[str] = Field(None, description="Best time for reviews")
    review_time_distribution: dict[int, int] = Field(
        default_factory=dict,
        description="Reviews by hour of day"
    )
    time_distribution: Optional[dict[str, float]] = Field(
        None,
        description="Time period distribution"
    )

    # Difficulty distribution
    difficulty_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage by difficulty"
    )
    
    # Forgetting curves
    forgetting_curves: List[ForgettingCurve] = Field(
        default_factory=list,
        description="Forgetting curves data"
    )

    # Projections
    reviews_due_today: int = Field(0, description="Reviews due today")
    reviews_due_week: int = Field(0, description="Reviews due this week")
    workload_trend: str = Field("stable", description="Workload trend: increasing, stable, decreasing")


class BulkReviewRequest(BaseModel):
    """Request to schedule reviews for multiple memories."""

    memory_ids: list[str] = Field(..., description="Memory IDs to schedule")
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
    force_schedule: bool = Field(
        False,
        description="Force scheduling even if not due"
    )
