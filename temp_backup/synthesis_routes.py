"""
API routes for v2.8.2 Synthesis features
Handles memory consolidation, summarization, and suggestions
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from fastapi.responses import StreamingResponse

from app.models.synthesis import (
    ConsolidatedMemory,
    ConsolidationCandidate,
    ConsolidationPreview,
    ConsolidationRequest,
    ExecutiveSummary,
    GraphMetrics,
    MetricsDashboard,
    Suggestion,
    TopicSummary,
)
from app.routes.auth import get_current_user
from app.services.service_factory import ServiceFactory

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


# Consolidation endpoints

@router.get("/consolidate/candidates", response_model=list[ConsolidationCandidate])
async def get_consolidation_candidates(
    similarity_threshold: float = Query(0.85, ge=0.5, le=1.0),
    time_window_days: int = Query(30, ge=1, le=365),
    max_candidates: int = Query(10, ge=1, le=50),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> list[ConsolidationCandidate]:
    """Get suggested memories to consolidate"""
    try:
        engine = services.get_consolidation_engine()
        candidates = await engine.find_consolidation_candidates(
            similarity_threshold=similarity_threshold,
            time_window_days=time_window_days,
            max_candidates=max_candidates
        )
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding candidates: {str(e)}")


@router.post("/consolidate/preview", response_model=ConsolidationPreview)
async def preview_consolidation(
    request: ConsolidationRequest,
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ConsolidationPreview:
    """Preview memory consolidation without executing"""
    try:
        engine = services.get_consolidation_engine()
        preview = await engine.preview_consolidation(request)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating preview: {str(e)}")


@router.post("/consolidate", response_model=ConsolidatedMemory)
async def consolidate_memories(
    request: ConsolidationRequest,
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ConsolidatedMemory:
    """Execute memory consolidation"""
    try:
        engine = services.get_consolidation_engine()
        result = await engine.consolidate_memories(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consolidation failed: {str(e)}")


# Summarization endpoints

@router.post("/summarize/topic", response_model=TopicSummary)
async def summarize_topic(
    topic: str = Query(..., min_length=1, max_length=100),
    days_back: int = Query(30, ge=1, le=365),
    max_memories: int = Query(50, ge=1, le=200),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> TopicSummary:
    """Generate summary for a specific topic"""
    try:
        summarizer = services.get_knowledge_summarizer()

        time_range = {
            "start": datetime.utcnow() - timedelta(days=days_back),
            "end": datetime.utcnow()
        }

        summary = await summarizer.summarize_topic(
            topic=topic,
            time_range=time_range,
            max_memories=max_memories
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.post("/summarize/executive", response_model=ExecutiveSummary)
async def generate_executive_summary(
    memory_ids: list[UUID],
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ExecutiveSummary:
    """Generate executive summary for selected memories"""
    if not memory_ids:
        raise HTTPException(status_code=400, detail="No memory IDs provided")

    if len(memory_ids) > 100:
        raise HTTPException(status_code=400, detail="Too many memories (max 100)")

    try:
        summarizer = services.get_knowledge_summarizer()
        summary = await summarizer.generate_executive_summary(memory_ids)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@router.get("/summarize/weekly")
async def get_weekly_summary(
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> ExecutiveSummary:
    """Get weekly knowledge summary"""
    try:
        summarizer = services.get_knowledge_summarizer()

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        summary = await summarizer.summarize_time_period(
            start_date=start_date,
            end_date=end_date,
            focus_areas=None  # Auto-detect
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weekly summary failed: {str(e)}")


# Suggestion endpoints

@router.get("/suggestions", response_model=list[Suggestion])
async def get_suggestions(
    context_memory_id: Optional[UUID] = None,
    suggestion_types: Optional[list[str]] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> list[Suggestion]:
    """Get smart suggestions based on context"""
    try:
        suggestion_engine = services.get_suggestion_engine()

        # Get current context
        if context_memory_id:
            db = services.get_database()
            current_memory = await db.get_memory(context_memory_id)
            if not current_memory:
                raise HTTPException(status_code=404, detail="Context memory not found")
        else:
            current_memory = None

        # Get user history
        recent_memories = await services.get_database().get_recent_memories(limit=20)

        suggestions = await suggestion_engine.get_contextual_suggestions(
            current_memory=current_memory,
            user_history=recent_memories,
            suggestion_types=suggestion_types
        )

        return suggestions[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")


@router.get("/suggestions/next-memories")
async def suggest_next_memories(
    limit: int = Query(5, ge=1, le=10),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> list[dict]:
    """Suggest what memories to explore next"""
    try:
        suggestion_engine = services.get_suggestion_engine()
        db = services.get_database()

        # Get recent memories for context
        recent_memories = await db.get_recent_memories(limit=10)

        suggestions = await suggestion_engine.suggest_next_memories(
            recent_memories=recent_memories,
            limit=limit
        )

        return [s.dict() for s in suggestions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest memories: {str(e)}")


# Metrics endpoints

@router.get("/metrics/current", response_model=GraphMetrics)
async def get_current_metrics(
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> GraphMetrics:
    """Get current graph metrics"""
    try:
        metrics_service = services.get_graph_metrics_service()
        metrics = await metrics_service.calculate_realtime_metrics("main")
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics calculation failed: {str(e)}")


@router.get("/metrics/dashboard", response_model=MetricsDashboard)
async def get_metrics_dashboard(
    days_back: int = Query(7, ge=1, le=30),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> MetricsDashboard:
    """Get comprehensive metrics dashboard"""
    try:
        metrics_service = services.get_graph_metrics_service()
        dashboard = await metrics_service.get_metrics_dashboard(days_back=days_back)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@router.websocket("/metrics/stream")
async def stream_metrics(
    websocket: WebSocket,
    services: ServiceFactory = Depends(ServiceFactory)
):
    """WebSocket endpoint for real-time metrics streaming"""
    await websocket.accept()

    try:
        metrics_service = services.get_graph_metrics_service()
        await metrics_service.stream_metrics_updates(websocket)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


# Automation endpoints

@router.post("/schedule/review")
async def schedule_memory_review(
    memory_id: UUID,
    review_strategy: str = "spaced_repetition",
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
) -> dict:
    """Schedule a memory for review"""
    try:
        # This would integrate with a task scheduler
        return {
            "status": "scheduled",
            "memory_id": str(memory_id),
            "strategy": review_strategy,
            "next_review": datetime.utcnow() + timedelta(days=1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


@router.post("/report/generate")
async def generate_report(
    report_type: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    format: str = Query("json", regex="^(json|pdf|html)$"),
    current_user: str = Depends(get_current_user),
    services: ServiceFactory = Depends(ServiceFactory)
):
    """Generate automated report"""
    try:
        # This would generate different report formats
        if format == "json":
            return {
                "report_type": report_type,
                "generated_at": datetime.utcnow(),
                "summary": "Report content here"
            }
        else:
            # Return file response for PDF/HTML
            return StreamingResponse(
                content=b"Report content",
                media_type=f"application/{format}",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{report_type}.{format}"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
