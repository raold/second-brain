"""
Importance Scoring API Routes
Provides endpoints for automated importance scoring features
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


from app.utils.logging_config import get_logger
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from fastapi import Query
from fastapi import Depends
from fastapi import HTTPException
from fastapi import APIRouter
from pydantic import BaseModel
from pydantic import Field
logger = get_logger(__name__)

router = APIRouter(prefix="/api/importance", tags=["importance"])


class UserFeedbackRequest(BaseModel):
    """User feedback for memory importance"""

    memory_id: str = Field(..., description="Memory ID")
    feedback_type: str = Field(..., description="Type of feedback: upvote, downvote, save, share")
    feedback_value: int | None = Field(None, description="Numeric feedback value")
    feedback_text: str | None = Field(None, description="Text feedback")


class ImportanceBreakdownResponse(BaseModel):
    """Detailed importance score breakdown"""

    memory_id: str
    current_score: float
    breakdown: dict[str, float]
    explanation: str
    history: list[dict[str, Any]]


@router.post("/setup")
async def setup_importance_tracking():
    """
    Initialize importance tracking schema and engine
    Creates necessary database tables and indexes
    """
    try:
        database = await get_database()

        if hasattr(database, "pool") and database.pool:
            success = await setup_importance_tracking_schema(database.pool)
            if success:
                return {
                    "status": "success",
                    "message": "Importance tracking schema initialized successfully",
                    "features": [
                        "Access pattern logging",
                        "Search result tracking",
                        "User feedback collection",
                        "Automated score calculation",
                    ],
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to setup importance tracking schema")
        else:
            return {
                "status": "mock_mode",
                "message": "Running in mock database mode - importance tracking disabled",
                "note": "Use real PostgreSQL database for full importance scoring features",
            }

    except Exception as e:
        logger.error(f"Error setting up importance tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.get("/analytics")
async def get_importance_analytics():
    """
    Get comprehensive importance analytics
    Shows distribution of importance scores and memory statistics
    """
    try:
        database = await get_database()
        engine = get_importance_engine(database)

        analytics = await engine.get_importance_analytics()

        if "error" in analytics:
            return {
                "status": "limited",
                "message": "Analytics unavailable - using mock database",
                "mock_data": {
                    "total_memories": 0,
                    "avg_importance": 0.5,
                    "distribution": [
                        {"importance_level": "high", "count": 0, "avg_score": 0.8},
                        {"importance_level": "medium", "count": 0, "avg_score": 0.6},
                        {"importance_level": "low", "count": 0, "avg_score": 0.3},
                    ],
                },
            }

        return {"status": "success", "analytics": analytics, "insights": _generate_analytics_insights(analytics)}

    except Exception as e:
        logger.error(f"Error getting importance analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


@router.get("/memory/{memory_id}/breakdown")
async def get_memory_importance_breakdown(memory_id: str) -> ImportanceBreakdownResponse:
    """
    Get detailed importance score breakdown for a specific memory
    Shows all factors contributing to the importance score
    """
    try:
        database = await get_database()
        engine = get_importance_engine(database)

        # Get memory details
        memory = await database.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Calculate importance breakdown
        score = await engine.calculate_importance_score(
            memory_id=memory_id,
            content=memory["content"],
            memory_type=memory["memory_type"],
            current_score=memory.get("importance_score", 0.5),
        )

        # Get importance history if available
        history = []
        if hasattr(database, "pool") and database.pool:
            try:
                from app.database_importance_schema import get_memory_importance_history

                history = await get_memory_importance_history(database.pool, memory_id, 10)
            except Exception as e:
                logger.debug(f"Could not get importance history: {e}")

        return ImportanceBreakdownResponse(
            memory_id=memory_id,
            current_score=score.final_score,
            breakdown={
                "frequency_score": score.frequency_score,
                "recency_score": score.recency_score,
                "search_relevance_score": score.search_relevance_score,
                "content_quality_score": score.content_quality_score,
                "type_weight": score.type_weight,
                "decay_factor": score.decay_factor,
                "confidence": score.confidence,
            },
            explanation=score.explanation,
            history=history,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting importance breakdown for {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Breakdown failed: {str(e)}")


@router.post("/feedback")
async def add_user_feedback(feedback: UserFeedbackRequest):
    """
    Add user feedback for a memory
    This helps improve importance scoring accuracy over time
    """
    try:
        database = await get_database()
        engine = get_importance_engine(database)

        # Validate feedback type
        valid_feedback_types = ["upvote", "downvote", "save", "share", "edit", "delete"]
        if feedback.feedback_type not in valid_feedback_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid feedback type. Must be one of: {', '.join(valid_feedback_types)}"
            )

        # Check if memory exists
        memory = await database.get_memory(feedback.memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Add feedback if database supports it
        if hasattr(database, "pool") and database.pool:
            try:
                async with database.pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO user_feedback_log
                        (memory_id, feedback_type, feedback_value, feedback_text)
                        VALUES ($1, $2, $3, $4)
                    """,
                        feedback.memory_id,
                        feedback.feedback_type,
                        feedback.feedback_value,
                        feedback.feedback_text,
                    )

                # Log as access for importance calculation
                await engine.log_memory_access(
                    memory_id=feedback.memory_id, access_type="user_feedback", user_action=feedback.feedback_type
                )

                return {
                    "status": "success",
                    "message": f"Feedback '{feedback.feedback_type}' recorded for memory {feedback.memory_id}",
                    "impact": "Importance score will be updated automatically",
                }

            except Exception as e:
                logger.error(f"Database feedback error: {e}")
                return {
                    "status": "partial",
                    "message": "Feedback noted but not persisted (mock database mode)",
                    "feedback": feedback.dict(),
                }
        else:
            return {
                "status": "mock_mode",
                "message": "Feedback noted but not persisted (mock database mode)",
                "feedback": feedback.dict(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback failed: {str(e)}")


@router.post("/recalculate")
async def recalculate_importance_scores(
    limit: int = Query(default=100, description="Number of memories to recalculate", ge=1, le=1000),
):
    """
    Manually trigger importance score recalculation
    Useful for maintenance or after configuration changes
    """
    try:
        database = await get_database()
        engine = get_importance_engine(database)

        logger.info(f"Starting manual importance recalculation for {limit} memories")
        result = await engine.batch_recalculate_importance(limit)

        if "error" in result:
            return {
                "status": "unavailable",
                "message": "Recalculation not available in mock database mode",
                "note": "Use real PostgreSQL database for importance recalculation",
            }

        return {
            "status": "success",
            "result": result,
            "message": f"Recalculated importance for {result.get('updated', 0)} out of {result.get('processed', 0)} memories",
        }

    except Exception as e:
        logger.error(f"Error recalculating importance scores: {e}")
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


@router.get("/high-importance")
async def get_high_importance_memories(
    limit: int = Query(default=20, description="Number of memories to return", ge=1, le=100),
):
    """
    Get memories with highest importance scores
    Useful for finding the most valuable content
    """
    try:
        database = await get_database()

        if hasattr(database, "pool") and database.pool:
            async with database.pool.acquire() as conn:
                memories = await conn.fetch(
                    """
                    SELECT id, content[1:200] as content_preview, memory_type,
                           importance_score, access_count, last_accessed,
                           created_at
                    FROM memories
                    ORDER BY importance_score DESC, access_count DESC
                    LIMIT $1
                """,
                    limit,
                )

                return {
                    "status": "success",
                    "memories": [dict(memory) for memory in memories],
                    "total_returned": len(memories),
                }
        else:
            return {
                "status": "mock_mode",
                "message": "High importance memories not available in mock database mode",
                "mock_data": {"memories": [], "note": "Connect to PostgreSQL database to see real importance rankings"},
            }

    except Exception as e:
        logger.error(f"Error getting high importance memories: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/log-access/{memory_id}")
async def log_memory_access(
    memory_id: str,
    access_type: str = Query(default="api_access", description="Type of access"),
    search_position: int | None = Query(default=None, description="Position in search results"),
    user_action: str | None = Query(default=None, description="User action performed"),
):
    """
    Manually log memory access for importance tracking
    Useful for tracking programmatic access or external integrations
    """
    try:
        database = await get_database()
        engine = get_importance_engine(database)

        # Check if memory exists
        memory = await database.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Log the access
        await engine.log_memory_access(
            memory_id=memory_id, access_type=access_type, search_position=search_position, user_action=user_action
        )

        return {
            "status": "success",
            "message": f"Access logged for memory {memory_id}",
            "access_details": {
                "memory_id": memory_id,
                "access_type": access_type,
                "search_position": search_position,
                "user_action": user_action,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging memory access: {e}")
        raise HTTPException(status_code=500, detail=f"Access logging failed: {str(e)}")


@router.delete("/cleanup-logs")
async def cleanup_old_logs(days_to_keep: int = Query(default=90, description="Days of logs to keep", ge=7, le=365)):
    """
    Clean up old access logs to prevent database bloat
    Removes detailed logs older than specified days while preserving summary data
    """
    try:
        database = await get_database()

        if hasattr(database, "pool") and database.pool:
            from app.database_importance_schema import cleanup_old_access_logs

            result = await cleanup_old_access_logs(database.pool, days_to_keep)

            if "error" in result:
                raise HTTPException(status_code=500, detail=result["error"])

            return {
                "status": "success",
                "cleanup_result": result,
                "message": f"Cleaned up logs older than {days_to_keep} days",
            }
        else:
            return {
                "status": "mock_mode",
                "message": "Log cleanup not available in mock database mode",
                "note": "No logs to clean in mock mode",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


def _generate_analytics_insights(analytics: dict[str, Any]) -> list[str]:
    """Generate insights from importance analytics"""
    insights = []

    if "distribution" in analytics:
        for level in analytics["distribution"]:
            count = level.get("count", 0)
            if level.get("importance_level") == "high" and count > 0:
                insights.append(f"Found {count} high-importance memories")
            elif level.get("importance_level") == "low" and count > 10:
                insights.append(f"Consider reviewing {count} low-importance memories for cleanup")

    if "total_memories" in analytics:
        total = analytics["total_memories"]
        if total > 1000:
            insights.append("Large memory collection detected - importance scoring helps prioritize content")
        elif total < 50:
            insights.append("Small memory collection - importance scores will improve with more usage data")

    if "type_analysis" in analytics:
        for type_info in analytics["type_analysis"]:
            memory_type = type_info.get("memory_type", "")
            avg_importance = type_info.get("avg_importance", 0)
            if avg_importance > 0.8:
                insights.append(f"{memory_type.title()} memories show high importance on average")

    return insights if insights else ["Importance analytics available - system learning from usage patterns"]
