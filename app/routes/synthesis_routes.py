"""
Synthesis Routes - v2.8.2

API endpoints for synthesis features including report generation,
spaced repetition, and WebSocket connections.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from fastapi.responses import StreamingResponse

from app.models.synthesis.repetition_models import (
    BulkReviewRequest,
    LearningStatistics,
    RepetitionAlgorithm,
    RepetitionConfig,
    ReviewDifficulty,
    ReviewSchedule,
    ReviewSession,
)
from app.models.synthesis.report_models import (
    ReportFilter,
    ReportFormat,
    ReportRequest,
    ReportResponse,
    ReportSchedule,
    ReportTemplate,
)
from app.models.synthesis.websocket_models import (
    EventType,
    SubscriptionRequest,
    WebSocketMetrics,
)
from app.services.synthesis import (
    RepetitionScheduler,
    ReportGenerator,
    ReportGeneratorConfig,
    WebSocketService,
)
from app.shared import get_db_instance, verify_api_key

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/synthesis", tags=["synthesis"])

# Initialize services (would be dependency injected in production)
websocket_service = WebSocketService()
report_generator = None
repetition_scheduler = None


async def get_report_generator() -> ReportGenerator:
    """Get report generator instance."""
    global report_generator
    if not report_generator:
        db = await get_db_instance()
        config = ReportGeneratorConfig()
        # Would get memory service from dependency injection
        from app.services.memory_service import MemoryService
        memory_service = MemoryService(db)
        report_generator = ReportGenerator(db.pool, memory_service, config)
    return report_generator


async def get_repetition_scheduler() -> RepetitionScheduler:
    """Get repetition scheduler instance."""
    global repetition_scheduler
    if not repetition_scheduler:
        db = await get_db_instance()
        repetition_scheduler = RepetitionScheduler(db.pool)
    return repetition_scheduler


# Report Generation Endpoints

@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    api_key: str = Depends(verify_api_key),
    generator: ReportGenerator = Depends(get_report_generator),
):
    """
    Generate a new report.

    Supports multiple report types and formats with AI-powered summaries.
    """
    try:
        report = await generator.generate_report(request)

        # Broadcast report completion event
        await websocket_service.event_broadcaster.broadcast_report_event(
            EventType.REPORT_COMPLETED,
            report.id,
            api_key,  # Using API key as user ID for now
            {"title": report.title, "format": report.format.value},
        )

        return report

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    filter: ReportFilter = Depends(),
    api_key: str = Depends(verify_api_key),
):
    """
    List generated reports with filtering options.
    """
    # In production, would query from database
    return []


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get a specific report by ID.
    """
    # In production, would fetch from database
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    format: Optional[ReportFormat] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    """
    Download a report in the specified format.
    """
    # In production, would stream file from storage
    return StreamingResponse(
        iter([b"Report content"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.pdf"},
    )


@router.post("/reports/schedule", response_model=ReportSchedule)
async def schedule_report(
    schedule: ReportSchedule,
    api_key: str = Depends(verify_api_key),
):
    """
    Schedule automated report generation.
    """
    # In production, would save to database and set up cron job
    return schedule


@router.get("/reports/schedules", response_model=list[ReportSchedule])
async def list_schedules(
    api_key: str = Depends(verify_api_key),
):
    """
    List all report schedules.
    """
    # In production, would query from database
    return []


@router.delete("/reports/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Delete a report schedule.
    """
    return {"message": "Schedule deleted"}


@router.post("/reports/templates", response_model=ReportTemplate)
async def create_template(
    template: ReportTemplate,
    api_key: str = Depends(verify_api_key),
):
    """
    Create a reusable report template.
    """
    # In production, would save to database
    template.id = f"tpl_{datetime.utcnow().timestamp()}"
    return template


@router.get("/reports/templates", response_model=list[ReportTemplate])
async def list_templates(
    api_key: str = Depends(verify_api_key),
):
    """
    List available report templates.
    """
    # In production, would query from database
    return []


# Spaced Repetition Endpoints

@router.post("/repetition/schedule", response_model=ReviewSchedule)
async def schedule_review(
    memory_id: str,
    algorithm: RepetitionAlgorithm = RepetitionAlgorithm.SM2,
    config: Optional[RepetitionConfig] = None,
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Schedule a memory for spaced repetition review.
    """
    try:
        schedule = await scheduler.schedule_review(memory_id, algorithm, config)

        # Broadcast review scheduled event
        await websocket_service.event_broadcaster.broadcast_memory_event(
            EventType.REVIEW_SCHEDULED,
            memory_id,
            api_key,
            {"next_review": schedule.scheduled_date.isoformat()},
        )

        return schedule

    except Exception as e:
        logger.error(f"Failed to schedule review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repetition/bulk-schedule", response_model=list[ReviewSchedule])
async def bulk_schedule_reviews(
    request: BulkReviewRequest,
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Schedule multiple memories for review.
    """
    try:
        schedules = await scheduler.bulk_schedule_reviews(request)
        return schedules

    except Exception as e:
        logger.error(f"Failed to bulk schedule reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repetition/due", response_model=list[ReviewSchedule])
async def get_due_reviews(
    limit: int = Query(100, ge=1, le=1000),
    include_overdue: bool = Query(True),
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Get memories due for review.
    """
    try:
        schedules = await scheduler.get_due_reviews(
            user_id=api_key,  # Using API key as user ID
            limit=limit,
            include_overdue=include_overdue,
        )
        return schedules

    except Exception as e:
        logger.error(f"Failed to get due reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repetition/sessions/start", response_model=ReviewSession)
async def start_review_session(
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Start a new review session.
    """
    try:
        session = await scheduler.start_review_session(api_key)
        return session

    except Exception as e:
        logger.error(f"Failed to start review session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repetition/sessions/{session_id}/end", response_model=ReviewSession)
async def end_review_session(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    End a review session and calculate statistics.
    """
    try:
        session = await scheduler.end_review_session(session_id)
        return session

    except Exception as e:
        logger.error(f"Failed to end review session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repetition/review/{memory_id}")
async def record_review(
    memory_id: str,
    session_id: str,
    difficulty: ReviewDifficulty,
    time_taken_seconds: int,
    confidence_level: Optional[float] = None,
    notes: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Record the result of a memory review.
    """
    try:
        result = await scheduler.record_review(
            memory_id,
            difficulty,
            time_taken_seconds,
            session_id,
            confidence_level,
            notes,
        )

        # Broadcast review completed event
        await websocket_service.event_broadcaster.broadcast_memory_event(
            EventType.REVIEW_COMPLETED,
            memory_id,
            api_key,
            {
                "difficulty": difficulty.name,
                "next_review": result.next_review.isoformat(),
                "interval_change": result.interval_change,
            },
        )

        return {
            "success": True,
            "next_review": result.next_review,
            "new_interval": result.new_strength.interval,
            "ease_factor": result.new_strength.ease_factor,
        }

    except Exception as e:
        logger.error(f"Failed to record review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repetition/statistics", response_model=LearningStatistics)
async def get_learning_statistics(
    period: str = Query("all_time", pattern="^(all_time|today|week|month)$"),
    api_key: str = Depends(verify_api_key),
    scheduler: RepetitionScheduler = Depends(get_repetition_scheduler),
):
    """
    Get comprehensive learning statistics.
    """
    try:
        stats = await scheduler.get_learning_statistics(api_key, period)
        return stats

    except Exception as e:
        logger.error(f"Failed to get learning statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoints

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(...),
):
    """
    WebSocket endpoint for real-time updates.

    Requires API key as query parameter for authentication.
    """
    # Verify API key
    try:
        await verify_api_key(api_key)
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid API key")
        return

    # Handle connection
    connection_id = await websocket_service.handle_connection(
        websocket,
        api_key,  # Using API key as user ID
        {
            "user_agent": websocket.headers.get("User-Agent"),
            "ip_address": websocket.client.host if websocket.client else None,
        },
    )

    logger.info(f"WebSocket connection closed: {connection_id}")


@router.post("/websocket/subscribe")
async def subscribe_to_events(
    request: SubscriptionRequest,
    connection_id: str = Query(...),
    api_key: str = Depends(verify_api_key),
):
    """
    Subscribe to specific event types.

    Used for HTTP-based subscription management.
    """
    try:
        subscription = await websocket_service.connection_manager.subscribe(
            connection_id,
            request,
        )
        return subscription

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to subscribe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/websocket/subscribe/{subscription_id}")
async def unsubscribe_from_events(
    subscription_id: str,
    connection_id: str = Query(...),
    api_key: str = Depends(verify_api_key),
):
    """
    Unsubscribe from events.
    """
    await websocket_service.connection_manager.unsubscribe(
        connection_id,
        subscription_id,
    )
    return {"message": "Unsubscribed successfully"}


@router.get("/websocket/metrics", response_model=WebSocketMetrics)
async def get_websocket_metrics(
    api_key: str = Depends(verify_api_key),
):
    """
    Get WebSocket service metrics.
    """
    return websocket_service.connection_manager.get_metrics()


# Utility Endpoints

@router.get("/synthesis/status")
async def get_synthesis_status(
    api_key: str = Depends(verify_api_key),
):
    """
    Get status of all synthesis services.
    """
    return {
        "report_generator": {
            "status": "operational",
            "version": "2.8.2",
        },
        "repetition_scheduler": {
            "status": "operational",
            "algorithms": ["sm2", "anki", "leitner"],
        },
        "websocket_service": {
            "status": "operational",
            "connections": len(websocket_service.connection_manager._connections),
            "metrics": websocket_service.connection_manager.get_metrics().dict(),
        },
    }


# Note: WebSocket service initialization is handled by the service itself
# The start/stop methods are called when needed, not at app startup/shutdown
# This prevents issues with the deprecated @router.on_event pattern
