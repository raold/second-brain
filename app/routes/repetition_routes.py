"""
API routes for spaced repetition scheduling
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis.repetition_models import (
    LearningCurve,
    MemoryStrength,
    OptimalReviewTime,
    RepetitionAlgorithm,
    RepetitionSettings,
    ReviewHistory,
    ReviewResult,
    ReviewSchedule,
    ReviewSession,
    ReviewStatistics,
    ReviewStatus,
    ScheduledReview,
)
from app.routes.auth import get_current_user
from app.services.service_factory import ServiceFactory
from app.services.synthesis.repetition_scheduler import SpacedRepetitionScheduler
from app.shared import get_db_instance as get_db

router = APIRouter(prefix="/synthesis/repetition", tags=["Spaced Repetition"])


@router.post("/schedule/{memory_id}", response_model=ScheduledReview)
async def schedule_memory_review(
    memory_id: UUID,
    algorithm: Optional[RepetitionAlgorithm] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ScheduledReview:
    """
    Schedule a memory for spaced repetition review.

    Algorithms:
    - sm2: SuperMemo 2 algorithm (default)
    - anki: Anki-style algorithm
    - leitner: Leitner box system
    - custom: Custom algorithm
    """
    try:
        scheduler = SpacedRepetitionScheduler(db)
        review = await scheduler.schedule_review(current_user, memory_id, algorithm)

        # Send notification via WebSocket
        if services.websocket_service:
            memory = await services.memory_service.get_memory(current_user, memory_id)
            await services.websocket_service.emit_review_event(
                user_id=current_user,
                memory_id=memory_id,
                memory_title=memory.title if memory else "Unknown",
                action="scheduled",
                review_id=review.id,
                next_review=review.scheduled_for
            )

        return review

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due", response_model=list[ScheduledReview])
async def get_due_reviews(
    date: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    include_overdue: bool = Query(True, description="Include overdue reviews"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[ScheduledReview]:
    """Get reviews due for a specific date (defaults to today)."""
    scheduler = SpacedRepetitionScheduler(db)
    reviews = await scheduler.get_due_reviews(current_user, date, limit)

    if not include_overdue:
        reviews = [r for r in reviews if r.status != ReviewStatus.OVERDUE]

    return reviews


@router.post("/session", response_model=ReviewSession)
async def create_review_session(
    session_type: str = Query("daily", regex="^(daily|focus|catch_up|custom)$"),
    review_limit: Optional[int] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReviewSession:
    """
    Create a review session with optimal review order.

    Session types:
    - daily: Regular daily reviews
    - focus: Focus on specific topics
    - catch_up: Catch up on overdue reviews
    - custom: Custom session
    """
    scheduler = SpacedRepetitionScheduler(db)
    session = await scheduler.create_review_session(
        current_user, session_type, review_limit
    )

    return session


@router.post("/review/{review_id}/complete", response_model=ScheduledReview)
async def complete_review(
    review_id: UUID,
    result: ReviewResult,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ScheduledReview:
    """
    Record the completion of a review and schedule the next one.

    Difficulty ratings:
    - again: Complete blackout, needs to be reviewed again soon
    - hard: Difficult recall, struggled to remember
    - good: Correct recall with some hesitation
    - easy: Perfect recall, very easy
    """
    try:
        scheduler = SpacedRepetitionScheduler(db)
        next_review = await scheduler.record_review(current_user, review_id, result)

        # Send notification via WebSocket
        if services.websocket_service:
            # Get streak info
            stats = await scheduler.get_review_statistics(current_user, "day")
            streak_info = {
                "current_streak": stats.current_streak,
                "longest_streak": stats.longest_streak
            }

            memory = await services.memory_service.get_memory(current_user, result.memory_id)
            await services.websocket_service.emit_review_event(
                user_id=current_user,
                memory_id=result.memory_id,
                memory_title=memory.title if memory else "Unknown",
                action="completed",
                review_id=review_id,
                next_review=next_review.scheduled_for,
                performance=result.difficulty.value,
                streak_info=streak_info
            )

        return next_review

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strength/{memory_id}", response_model=MemoryStrength)
async def get_memory_strength(
    memory_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MemoryStrength:
    """Get the current strength and retention metrics for a memory."""
    scheduler = SpacedRepetitionScheduler(db)
    strength = await scheduler.get_memory_strength(current_user, memory_id)

    return strength


@router.get("/statistics", response_model=ReviewStatistics)
async def get_review_statistics(
    period: str = Query("week", regex="^(day|week|month|all_time)$"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReviewStatistics:
    """
    Get review statistics for a time period.

    Periods:
    - day: Last 24 hours
    - week: Last 7 days
    - month: Last 30 days
    - all_time: All time statistics
    """
    scheduler = SpacedRepetitionScheduler(db)
    stats = await scheduler.get_review_statistics(current_user, period)

    return stats


@router.get("/optimal-time", response_model=OptimalReviewTime)
async def get_optimal_review_time(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OptimalReviewTime:
    """Get the optimal time for reviews based on user's historical performance."""
    scheduler = SpacedRepetitionScheduler(db)
    optimal_time = await scheduler.get_optimal_review_time(current_user)

    return optimal_time


@router.get("/learning-curve/{subject}", response_model=LearningCurve)
async def get_learning_curve(
    subject: str,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LearningCurve:
    """
    Get learning curve analysis for a topic or memory.

    Subject can be:
    - A memory ID (UUID format)
    - A topic name (string)
    """
    scheduler = SpacedRepetitionScheduler(db)
    curve = await scheduler.generate_learning_curve(current_user, subject, days)

    return curve


@router.get("/settings", response_model=RepetitionSettings)
async def get_repetition_settings(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RepetitionSettings:
    """Get user's spaced repetition settings."""
    # In production, load from database
    settings = RepetitionSettings(
        user_id=current_user,
        algorithm=RepetitionAlgorithm.SM2,
        daily_review_limit=20,
        new_memories_per_day=10,
        preferred_review_time="09:00",
        timezone="UTC",
        initial_ease=2.5,
        easy_bonus=1.3,
        hard_penalty=0.8,
        learning_steps=[1, 10],
        relearning_steps=[10],
        lapse_new_interval=0.5,
        bury_related=True,
        enable_fuzz=True
    )

    return settings


@router.put("/settings", response_model=RepetitionSettings)
async def update_repetition_settings(
    settings: RepetitionSettings,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RepetitionSettings:
    """Update user's spaced repetition settings."""
    settings.user_id = current_user
    settings.updated_at = datetime.utcnow()

    # In production, save to database

    return settings


@router.get("/schedule", response_model=ReviewSchedule)
async def get_review_schedule(
    date: Optional[datetime] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReviewSchedule:
    """Get complete review schedule for a date."""
    scheduler = SpacedRepetitionScheduler(db)

    # Get all reviews
    all_reviews = await scheduler.get_due_reviews(current_user, date)

    # Categorize reviews
    new_reviews = []
    learning_reviews = []
    due_reviews = []
    overdue_reviews = []

    for review in all_reviews:
        if review.status == ReviewStatus.OVERDUE:
            overdue_reviews.append(review)
        elif review.interval_days <= 1:
            learning_reviews.append(review)
        elif review.review_count == 0:
            new_reviews.append(review)
        else:
            due_reviews.append(review)

    # Calculate statistics
    total_scheduled = len(all_reviews)
    estimated_time = total_scheduled * 30 // 60  # 30 seconds per review

    # Get optimal time
    optimal_time = await scheduler.get_optimal_review_time(current_user)

    schedule = ReviewSchedule(
        user_id=current_user,
        date=date or datetime.utcnow(),
        new_reviews=new_reviews,
        learning_reviews=learning_reviews,
        due_reviews=due_reviews,
        overdue_reviews=overdue_reviews,
        total_scheduled=total_scheduled,
        estimated_time_minutes=estimated_time,
        optimal_review_time=optimal_time.recommended_time,
        suggested_order=[r.id for r in overdue_reviews + due_reviews + learning_reviews + new_reviews]
    )

    return schedule


@router.post("/bulk-schedule", response_model=list[ScheduledReview])
async def bulk_schedule_reviews(
    memory_ids: list[UUID],
    algorithm: Optional[RepetitionAlgorithm] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[ScheduledReview]:
    """Schedule multiple memories for review at once."""
    scheduler = SpacedRepetitionScheduler(db)
    reviews = []

    for memory_id in memory_ids:
        try:
            review = await scheduler.schedule_review(current_user, memory_id, algorithm)
            reviews.append(review)
        except Exception:
            # Log error but continue with other memories
            pass

    return reviews


@router.get("/history/{memory_id}", response_model=ReviewHistory)
async def get_review_history(
    memory_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReviewHistory:
    """Get review history for a specific memory."""
    # In production, load from database

    history = ReviewHistory(
        memory_id=memory_id,
        reviews=[
            {
                "date": "2025-01-20T10:00:00Z",
                "difficulty": "good",
                "time_taken": 25,
                "interval_before": 1,
                "interval_after": 2
            },
            {
                "date": "2025-01-18T09:30:00Z",
                "difficulty": "hard",
                "time_taken": 45,
                "interval_before": 0,
                "interval_after": 1
            }
        ],
        total_reviews=2,
        successful_reviews=2,
        average_difficulty=3.5,
        average_interval=1.5,
        last_review=datetime.utcnow(),
        next_scheduled=datetime.utcnow()
    )

    return history


@router.delete("/review/{review_id}")
async def skip_review(
    review_id: UUID,
    reason: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Skip a scheduled review."""
    # In production, update review status to SKIPPED

    return {
        "success": True,
        "message": "Review skipped",
        "next_review_scheduled": datetime.utcnow().isoformat()
    }


@router.post("/suspend/{memory_id}")
async def suspend_reviews(
    memory_id: UUID,
    until: Optional[datetime] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Suspend reviews for a memory temporarily."""
    # In production, update all pending reviews to SUSPENDED

    return {
        "success": True,
        "suspended_until": until.isoformat() if until else "indefinitely",
        "affected_reviews": 3
    }
