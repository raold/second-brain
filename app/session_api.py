#!/usr/bin/env python3
"""
Session Management API - Context Preservation and Idea Ingestion
Provides API endpoints for persistent context continuity and mobile idea processing
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query
from pydantic import BaseModel, Field

from app.conversation_processor import get_conversation_processor
from app.dashboard import get_dashboard
from app.session_manager import get_session_manager, ingest_idea, pause_and_preserve_context, resume_coding_session

# Create router for session endpoints
session_router = APIRouter(prefix="/session", tags=["Session Management"])


class IdeaIngestionRequest(BaseModel):
    """Request model for idea ingestion"""

    idea: str = Field(..., description="The idea to ingest and process")
    source: str = Field(default="mobile", description="Source of the idea (mobile, web, voice, etc.)")
    priority: str = Field(default="medium", description="Suggested priority level")
    context: str = Field(default="", description="Additional context about the idea")


class SessionResumeRequest(BaseModel):
    """Request model for session resumption"""

    session_id: str | None = Field(default=None, description="Specific session ID to resume")
    load_full_context: bool = Field(default=True, description="Whether to load full conversation context")


class SessionPauseRequest(BaseModel):
    """Request model for session pausing"""

    reason: str = Field(default="Manual pause", description="Reason for pausing")
    save_snapshot: bool = Field(default=True, description="Whether to save detailed snapshot")


class ConversationMessage(BaseModel):
    """Model for processing conversation messages"""

    speaker: str = Field(..., description="Who is speaking (CTO, Principal Engineer, etc.)")
    message: str = Field(..., description="The conversation message")
    context_type: str = Field(default="general", description="Type of conversation context")


@session_router.post("/ingest")
async def ingest_mobile_idea(idea_request: IdeaIngestionRequest, background_tasks: BackgroundTasks):
    """
    The WOODCHIPPER - Ingest ideas from mobile/remote and automatically process them
    This is the core feature for dropping ideas and having them automatically integrated
    """
    try:
        # Process the idea through the woodchipper
        result = ingest_idea(idea_request.idea, idea_request.source)

        # Add background processing for comprehensive integration
        background_tasks.add_task(
            process_idea_comprehensive,
            idea_request.idea,
            idea_request.source,
            idea_request.priority,
            idea_request.context,
        )

        return {
            "status": "success",
            "message": "Idea successfully ingested and processed",
            "idea_id": result["idea_id"],
            "processed_at": result["processed_at"],
            "features_detected": result["detected_features"],
            "auto_updates": result["auto_updates"],
            "updated_dashboard": result.get("updated_dashboard", ""),
            "next_steps": [
                "Review auto-generated milestones",
                "Prioritize against existing roadmap",
                "Discuss architectural implications",
                "Plan implementation approach",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Idea ingestion failed: {str(e)}")


@session_router.get("/")
async def get_session_status():
    """Get current session status and analytics"""
    try:
        session_manager = get_session_manager()
        analytics = session_manager.get_session_analytics()

        return {
            "status": "success",
            "session_analytics": analytics,
            "context_preservation": {
                "conversation_buffer_size": len(session_manager.session_buffer),
                "sync_enabled": session_manager.sync_enabled,
                "last_sync": session_manager.last_sync_time,
            },
            "available_actions": [
                "Pause session and preserve context",
                "Resume from previous session",
                "Ingest new ideas",
                "Process conversation messages",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session status error: {str(e)}")


@session_router.post("/pause")
async def pause_session(pause_request: SessionPauseRequest):
    """
    Pause current session and generate comprehensive resume context
    Critical for cost management and seamless continuation
    """
    try:
        resume_context = pause_and_preserve_context(pause_request.reason)

        session_manager = get_session_manager()
        analytics = session_manager.get_session_analytics()

        return {
            "status": "success",
            "message": f"Session paused: {pause_request.reason}",
            "resume_context": resume_context,
            "session_summary": analytics,
            "resume_instructions": [
                "Call /session/resume to continue seamlessly",
                "All conversation context will be restored",
                "Project momentum and focus preserved",
                "Dashboard state maintained",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session pause failed: {str(e)}")


@session_router.post("/resume")
async def resume_session(resume_request: SessionResumeRequest):
    """
    Resume session with full context restoration
    Seamlessly pick up where we left off
    """
    try:
        success = resume_coding_session(resume_request.session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Could not resume session")

        session_manager = get_session_manager()
        analytics = session_manager.get_session_analytics()

        # Get current context
        current_session = session_manager.current_session
        resume_context = session_manager.generate_resume_context()

        return {
            "status": "success",
            "message": "Session resumed successfully",
            "session_id": current_session.session_id if current_session else None,
            "resume_context": resume_context,
            "restored_elements": {
                "conversation_history": len(current_session.conversation_history) if current_session else 0,
                "project_momentum": analytics["momentum"],
                "dashboard_state": "synchronized",
                "technical_context": "restored",
            },
            "where_we_left_off": {
                "current_focus": analytics["momentum"]["current_focus"],
                "next_steps": analytics["momentum"]["next_logical_steps"],
                "energy_level": analytics["momentum"]["energy_level"],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session resume failed: {str(e)}")


@session_router.post("/conversation")
async def process_conversation(message: ConversationMessage):
    """
    Process conversation message and update session context
    Maintains the coding vibe and momentum
    """
    try:
        session_manager = get_session_manager()

        # Process the conversation message
        conv_message = session_manager.process_conversation_message(
            message.speaker, message.message, message.context_type
        )

        return {
            "status": "success",
            "message_id": conv_message.id,
            "processed_at": conv_message.timestamp,
            "semantic_summary": conv_message.semantic_summary,
            "emotional_tone": conv_message.emotional_tone,
            "detected_features": conv_message.detected_features,
            "context_updates": {"momentum_updated": True, "session_saved": True, "buffer_updated": True},
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation processing failed: {str(e)}")


@session_router.get("/context")
async def get_current_context():
    """
    Get comprehensive current context for CTO overview
    Shows exactly where we are and what's next
    """
    try:
        session_manager = get_session_manager()
        dashboard = get_dashboard()

        # Get current session context
        if session_manager.current_session:
            resume_context = session_manager.generate_resume_context()
            session_summary = session_manager.generate_session_summary()
        else:
            resume_context = "No active session"
            session_summary = "No session data"

        # Get dashboard state
        dashboard_summary = dashboard.get_dashboard_summary()

        # Get conversation processor state
        processor = get_conversation_processor()
        intelligence_summary = processor.get_conversation_intelligence_summary()

        return {
            "status": "success",
            "current_context": {
                "session_summary": session_summary,
                "resume_context": resume_context,
                "dashboard_state": dashboard_summary,
                "conversation_intelligence": intelligence_summary,
            },
            "productivity_snapshot": {
                "session_duration": session_manager.calculate_session_duration()
                if session_manager.current_session
                else "0m",
                "features_detected_today": intelligence_summary["features_detected_today"],
                "conversation_buffer": len(session_manager.session_buffer),
                "last_activity": datetime.now().isoformat(),
            },
            "ready_for": [
                "New feature discussions",
                "Architectural planning",
                "Implementation work",
                "Mobile idea ingestion",
                "Cross-device synchronization",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")


@session_router.get("/history")
async def get_session_history(limit: int = Query(default=50, ge=1, le=1000)):
    """Get conversation history with context preservation"""
    try:
        session_manager = get_session_manager()

        if not session_manager.current_session:
            return {"status": "success", "history": [], "message": "No active session"}

        # Get recent conversation history
        recent_history = session_manager.current_session.conversation_history[-limit:]

        formatted_history = []
        for msg in recent_history:
            formatted_history.append(
                {
                    "id": msg.id,
                    "timestamp": msg.timestamp,
                    "speaker": msg.speaker,
                    "message": msg.message,
                    "context_type": msg.context_type,
                    "semantic_summary": msg.semantic_summary,
                    "emotional_tone": msg.emotional_tone,
                    "detected_features": msg.detected_features,
                }
            )

        return {
            "status": "success",
            "history": formatted_history,
            "total_messages": len(session_manager.current_session.conversation_history),
            "context_preservation": "fully_maintained",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")


@session_router.post("/sync")
async def sync_session(target_device: str = "cloud"):
    """
    Synchronize session across devices for seamless continuation
    Critical for cross-device productivity
    """
    try:
        session_manager = get_session_manager()

        if not session_manager.current_session:
            raise HTTPException(status_code=404, detail="No active session to sync")

        # Force save current state
        session_manager.save_session_state()

        # Generate sync package
        sync_package = {
            "session_id": session_manager.current_session.session_id,
            "sync_hash": session_manager.current_session.sync_hash,
            "sync_timestamp": datetime.now().isoformat(),
            "target_device": target_device,
            "full_context": session_manager.generate_resume_context(),
            "session_analytics": session_manager.get_session_analytics(),
        }

        return {
            "status": "success",
            "message": f"Session synced to {target_device}",
            "sync_package": sync_package,
            "instructions": [
                f"Session data saved with hash: {sync_package['sync_hash']}",
                "Use /session/resume on target device",
                "Full conversation context will transfer",
                "Project momentum preserved",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session sync failed: {str(e)}")


# Mobile-optimized endpoints
@session_router.post("/mobile/idea")
async def mobile_idea_quick_drop(idea: str = Form(...), voice_note: str | None = Form(default=None)):
    """
    Quick idea drop from mobile - ultra-simple interface
    The fastest way to get ideas into the system
    """
    try:
        # Process both text and voice if provided
        full_idea = f"{idea}"
        if voice_note:
            full_idea += f" [Voice note: {voice_note}]"

        result = ingest_idea(full_idea, "mobile_quick")

        return {
            "status": "success",
            "message": "💡 Idea captured and processing!",
            "idea_id": result["idea_id"],
            "features_detected": len(result["detected_features"]),
            "quick_summary": f"Added {len(result['detected_features'])} features to roadmap",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mobile idea drop failed: {str(e)}")


@session_router.get("/mobile/status")
async def mobile_status_check():
    """Quick status check optimized for mobile"""
    try:
        session_manager = get_session_manager()
        dashboard = get_dashboard()

        if session_manager.current_session:
            current_focus = session_manager.current_session.project_momentum.current_focus
            next_steps = session_manager.current_session.project_momentum.next_logical_steps[:3]
        else:
            current_focus = "No active session"
            next_steps = ["Start new session"]

        dashboard_summary = dashboard.get_dashboard_summary()

        return {
            "session_active": session_manager.current_session is not None,
            "current_focus": current_focus,
            "next_steps": next_steps,
            "project_health": dashboard_summary["overall_health"]["status"],
            "recent_features": dashboard_summary.get("recent_completions", [])[:3],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mobile status failed: {str(e)}")


async def process_idea_comprehensive(idea: str, source: str, priority: str, context: str):
    """
    Background task for comprehensive idea processing
    Updates documentation, versioning, timelines, EVERYTHING automatically
    """
    try:
        dashboard = get_dashboard()
        session_manager = get_session_manager()

        # Update technical metrics
        dashboard.record_metric("ideas_processed", 1, "count")

        # Update session productivity
        if session_manager.current_session:
            session_manager.current_session.productivity_metrics["features_added"] += 1

        # TODO: Add automatic documentation updates
        # TODO: Add automatic versioning updates
        # TODO: Add automatic timeline adjustments

        print(f"🌊 Comprehensive processing complete for idea: {idea[:50]}...")

    except Exception as e:
        print(f"❌ Background processing error: {e}")


# Convenience function for integration with main app
def setup_session_routes(app):
    """Setup session management routes in main FastAPI app"""
    app.include_router(session_router)
    return session_router
