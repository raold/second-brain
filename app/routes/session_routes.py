"""
Session Routes - Thin route handlers for session operations.
All business logic is delegated to SessionService.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


from app.utils.logging_config import get_logger
from app.core.dependencies import get_session_service_dep
from app.models.api_models import SecondBrainException
from fastapi import BackgroundTasks, Form
from typing import Optional, Dict, List, Any
logger = get_logger(__name__)
router = APIRouter(prefix="/session", tags=["Session"])


class IdeaIngestionRequest(BaseModel):
    """Request model for idea ingestion (woodchipper)"""

    idea: str = Field(..., description="The idea to process")
    source: str = Field(default="mobile", description="Source of the idea")
    priority: str = Field(default="medium", description="Priority level")
    context: str | None = Field(default=None, description="Additional context")


class SessionPauseRequest(BaseModel):
    """Request model for pausing a session"""

    reason: str = Field(default="User requested", description="Reason for pausing")


class SessionResumeRequest(BaseModel):
    """Request model for resuming a session"""

    session_id: str | None = Field(default=None, description="Session ID to resume")
    device_context: str | None = Field(default=None, description="Device/platform context")


class ConversationMessage(BaseModel):
    """Request model for processing conversation messages"""

    message: str = Field(..., description="The conversation message")
    context_type: str = Field(default="general", description="Type of conversation context")


@router.post("/ingest")
async def ingest_mobile_idea(idea_request: IdeaIngestionRequest, background_tasks: BackgroundTasks, session_service=Depends(get_session_service_dep)):
    """
    The WOODCHIPPER - Ingest ideas from mobile/remote and automatically process them.
    This is the core feature for dropping ideas and having them automatically integrated.
    """
    try:
        result = await session_service.ingest_idea(
            idea=idea_request.idea,
            source=idea_request.source,
            priority=idea_request.priority,
            context=idea_request.context,
        )

        return {"status": "success", "message": "Idea successfully ingested and processed", **result}

    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Idea ingestion failed: {e}")
        raise SecondBrainException(message=f"Idea ingestion failed: {str(e)}")


@router.get("/")
async def get_session_status(session_service=Depends(get_session_service_dep)):
    """Get current session status and analytics."""
    try:
        status = await session_service.get_session_status()

        return {"status": "success", **status}

    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Session status error: {e}")
        raise SecondBrainException(message=f"Session status error: {str(e)}")


@router.post("/pause")
async def pause_session(pause_request: SessionPauseRequest, session_service=Depends(get_session_service_dep)):
    """
    Pause current session and generate comprehensive resume context.
    Critical for cost management and seamless continuation.
    """
    try:
        result = await session_service.pause_session(reason=pause_request.reason)

        return {
            "status": "success",
            "message": f"Session paused: {pause_request.reason}",
            **result,
            "resume_instructions": [
                "Call /session/resume to continue seamlessly",
                "All conversation context will be restored",
                "Project momentum and focus preserved",
                "Dashboard state maintained",
            ],
        }

    except Exception as e:
        logger.error(f"Session pause failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session pause failed: {str(e)}")


@router.post("/resume")
async def resume_session(resume_request: SessionResumeRequest, session_service=Depends(get_session_service_dep)):
    """
    Resume a previous session with full context restoration.
    Supports cross-device synchronization.
    """
    try:
        result = await session_service.resume_session(
            session_id=resume_request.session_id, device_context=resume_request.device_context
        )

        return {"status": "success", "message": "Session successfully resumed", **result}

    except Exception as e:
        logger.error(f"Session resume failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session resume failed: {str(e)}")


@router.post("/conversation/process")
async def process_conversation(message: ConversationMessage, session_service=Depends(get_session_service_dep)):
    """
    Process conversation messages to extract insights and update project state.
    Monitors for technical discussions and feature requests.
    """
    try:
        result = await session_service.process_conversation_message(
            message=message.message, context_type=message.context_type
        )

        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Conversation processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation processing failed: {str(e)}")


@router.get("/context")
async def get_current_context(session_service=Depends(get_session_service_dep)):
    """
    Get comprehensive current context for overview.
    Shows exactly where we are and what's next.
    """
    try:
        context = await session_service.get_session_status()
        
        return {"status": "success", "current_context": context}
        
    except Exception as e:
        logger.error(f"Context retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")


@router.get("/history")
async def get_session_history(limit: int = Query(default=50, ge=1, le=1000), session_service=Depends(get_session_service_dep)):
    """Get conversation history with context preservation."""
    try:
        # Note: This would need to be implemented in SessionService
        # For now, return a placeholder
        return {
            "status": "success",
            "history": [],
            "message": "History endpoint needs service implementation"
        }
        
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")


@router.post("/sync")
async def sync_session(target_device: str = "cloud", session_service=Depends(get_session_service_dep)):
    """
    Synchronize session across devices for seamless continuation.
    Critical for cross-device productivity.
    """
    try:
        # Note: This would need to be implemented in SessionService
        # For now, return a placeholder
        return {
            "status": "success",
            "message": f"Session sync to {target_device} initiated",
            "note": "Sync endpoint needs service implementation"
        }
        
    except Exception as e:
        logger.error(f"Session sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session sync failed: {str(e)}")


# Mobile-optimized endpoints
@router.post("/mobile/idea")
async def mobile_idea_quick_drop(idea: str = Form(...), voice_note: str | None = Form(default=None), session_service=Depends(get_session_service_dep)):
    """
    Quick idea drop from mobile - ultra-simple interface.
    The fastest way to get ideas into the system.
    """
    try:
        # Process both text and voice if provided
        full_idea = f"{idea}"
        if voice_note:
            full_idea += f" [Voice note: {voice_note}]"
            
        result = await session_service.ingest_idea(
            idea=full_idea,
            source="mobile_quick",
            priority="medium",
            context=None
        )
        
        return {
            "status": "success",
            "message": "💡 Idea captured and processing!",
            "idea_id": result.get("idea_id"),
            "features_detected": len(result.get("detected_features", [])),
            "quick_summary": f"Added {len(result.get('detected_features', []))} features to roadmap"
        }
        
    except Exception as e:
        logger.error(f"Mobile idea drop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Mobile idea drop failed: {str(e)}")


@router.get("/mobile/status")
async def mobile_status_check(session_service=Depends(get_session_service_dep)):
    """Quick status check optimized for mobile."""
    try:
        status = await session_service.get_session_status()
        
        # Extract mobile-friendly summary
        return {
            "session_active": True,  # Simplified for mobile
            "current_focus": status.get("current_state", {}).get("focus", "Ready"),
            "project_health": "healthy",  # Simplified
            "recent_features": []  # Simplified
        }
        
    except Exception as e:
        logger.error(f"Mobile status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Mobile status failed: {str(e)}")
