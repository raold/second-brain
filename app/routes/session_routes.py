"""
Session Routes - Thin route handlers for session operations.
All business logic is delegated to SessionService.
"""

import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from app.services.service_factory import get_session_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["Session"])


class IdeaIngestionRequest(BaseModel):
    """Request model for idea ingestion (woodchipper)"""
    idea: str = Field(..., description="The idea to process")
    source: str = Field(default="mobile", description="Source of the idea")
    priority: str = Field(default="medium", description="Priority level")
    context: Optional[str] = Field(default=None, description="Additional context")


class SessionPauseRequest(BaseModel):
    """Request model for pausing a session"""
    reason: str = Field(default="User requested", description="Reason for pausing")


class SessionResumeRequest(BaseModel):
    """Request model for resuming a session"""
    session_id: Optional[str] = Field(default=None, description="Session ID to resume")
    device_context: Optional[str] = Field(default=None, description="Device/platform context")


class ConversationMessage(BaseModel):
    """Request model for processing conversation messages"""
    message: str = Field(..., description="The conversation message")
    context_type: str = Field(default="general", description="Type of conversation context")


@router.post("/ingest")
async def ingest_mobile_idea(
    idea_request: IdeaIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    The WOODCHIPPER - Ingest ideas from mobile/remote and automatically process them.
    This is the core feature for dropping ideas and having them automatically integrated.
    """
    try:
        session_service = get_session_service()
        result = await session_service.ingest_idea(
            idea=idea_request.idea,
            source=idea_request.source,
            priority=idea_request.priority,
            context=idea_request.context
        )
        
        return {
            "status": "success",
            "message": "Idea successfully ingested and processed",
            **result
        }
        
    except Exception as e:
        logger.error(f"Idea ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Idea ingestion failed: {str(e)}")


@router.get("/")
async def get_session_status():
    """Get current session status and analytics."""
    try:
        session_service = get_session_service()
        status = await session_service.get_session_status()
        
        return {
            "status": "success",
            **status
        }
        
    except Exception as e:
        logger.error(f"Session status error: {e}")
        raise HTTPException(status_code=500, detail=f"Session status error: {str(e)}")


@router.post("/pause")
async def pause_session(pause_request: SessionPauseRequest):
    """
    Pause current session and generate comprehensive resume context.
    Critical for cost management and seamless continuation.
    """
    try:
        session_service = get_session_service()
        result = await session_service.pause_session(reason=pause_request.reason)
        
        return {
            "status": "success",
            "message": f"Session paused: {pause_request.reason}",
            **result,
            "resume_instructions": [
                "Call /session/resume to continue seamlessly",
                "All conversation context will be restored",
                "Project momentum and focus preserved",
                "Dashboard state maintained"
            ]
        }
        
    except Exception as e:
        logger.error(f"Session pause failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session pause failed: {str(e)}")


@router.post("/resume")
async def resume_session(resume_request: SessionResumeRequest):
    """
    Resume a previous session with full context restoration.
    Supports cross-device synchronization.
    """
    try:
        session_service = get_session_service()
        result = await session_service.resume_session(
            session_id=resume_request.session_id,
            device_context=resume_request.device_context
        )
        
        return {
            "status": "success",
            "message": "Session successfully resumed",
            **result
        }
        
    except Exception as e:
        logger.error(f"Session resume failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session resume failed: {str(e)}")


@router.post("/conversation/process")
async def process_conversation(message: ConversationMessage):
    """
    Process conversation messages to extract insights and update project state.
    Monitors for technical discussions and feature requests.
    """
    try:
        session_service = get_session_service()
        result = await session_service.process_conversation_message(
            message=message.message,
            context_type=message.context_type
        )
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"Conversation processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation processing failed: {str(e)}") 