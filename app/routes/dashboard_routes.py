"""
Dashboard Routes - Thin route handlers for dashboard operations.
All business logic is delegated to DashboardService.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from app.services.service_factory import get_dashboard_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class FeatureRequest(BaseModel):
    """Request model for adding new features"""
    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    priority: str = Field(default="high", description="Feature priority")


class MilestoneProgress(BaseModel):
    """Request model for updating milestone progress"""
    milestone_id: str = Field(..., description="Milestone ID")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    notes: str | None = Field(default=None, description="Progress notes")


@router.get("/")
async def get_dashboard_overview():
    """Get comprehensive dashboard overview."""
    try:
        dashboard_service = get_dashboard_service()
        summary = await dashboard_service.get_dashboard_summary()
        
        return {
            "status": "success",
            "data": summary,
            "api_version": "2.0"
        }
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard overview")


@router.get("/stats")
async def get_project_stats():
    """Get project statistics and metrics."""
    try:
        dashboard_service = get_dashboard_service()
        stats = await dashboard_service.get_project_stats()
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Project stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project statistics")


@router.get("/milestones/upcoming")
async def get_upcoming_milestones(limit: int = 5):
    """Get upcoming project milestones."""
    try:
        dashboard_service = get_dashboard_service()
        milestones = await dashboard_service.get_upcoming_milestones(limit=limit)
        
        return {
            "status": "success",
            "milestones": milestones,
            "count": len(milestones)
        }
        
    except Exception as e:
        logger.error(f"Upcoming milestones error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get upcoming milestones")


@router.put("/milestones/progress")
async def update_milestone_progress(request: MilestoneProgress):
    """Update progress for a specific milestone."""
    try:
        dashboard_service = get_dashboard_service()
        updated = await dashboard_service.update_milestone_progress(
            milestone_id=request.milestone_id,
            progress=request.progress,
            notes=request.notes
        )
        
        return {
            "status": "success",
            "milestone": updated
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Milestone update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update milestone progress")


@router.get("/features/progress")
async def get_feature_progress():
    """Get feature development progress."""
    try:
        dashboard_service = get_dashboard_service()
        progress = await dashboard_service.get_feature_progress()
        
        return {
            "status": "success",
            "progress": progress
        }
        
    except Exception as e:
        logger.error(f"Feature progress error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature progress")


@router.get("/productivity")
async def get_productivity_metrics():
    """Get productivity and efficiency metrics."""
    try:
        dashboard_service = get_dashboard_service()
        metrics = await dashboard_service.get_productivity_metrics()
        
        return {
            "status": "success",
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Productivity metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get productivity metrics")


@router.get("/report/{period}")
async def generate_progress_report(period: str = "week"):
    """Generate a progress report for the specified period."""
    if period not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be 'day', 'week', or 'month'")
    
    try:
        dashboard_service = get_dashboard_service()
        report = await dashboard_service.generate_progress_report(period=period)
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Progress report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate progress report")


@router.get("/roadmap/visualization")
async def get_roadmap_visualization():
    """Get data for roadmap visualization."""
    try:
        dashboard_service = get_dashboard_service()
        roadmap = await dashboard_service.get_roadmap_visualization()
        
        return {
            "status": "success",
            "roadmap": roadmap
        }
        
    except Exception as e:
        logger.error(f"Roadmap visualization error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get roadmap visualization") 