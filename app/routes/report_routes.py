"""
API routes for automated report generation
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.models.synthesis.report_models import (
    GeneratedReport,
    ReportFormat,
    ReportRequest,
    ReportSchedule,
    ReportTemplate,
    ReportType,
)
from app.services.service_factory import ServiceFactory
from app.services.synthesis.report_generator import ReportGenerator

router = APIRouter(prefix="/synthesis/reports", tags=["Reports"])


@router.post("/generate", response_model=GeneratedReport)
async def generate_report(
    request: ReportRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    services: ServiceFactory = Depends(ServiceFactory)
) -> GeneratedReport:
    """
    Generate a report based on request parameters.

    Report types:
    - daily: Daily activity summary
    - weekly: Weekly progress report
    - monthly: Monthly comprehensive report
    - quarterly: Quarterly analysis
    - annual: Annual review
    - insights: AI-powered insights report
    - progress: Learning progress report
    - knowledge_map: Visual knowledge map
    - learning_path: Personalized learning path
    """
    try:
        generator = ReportGenerator(db)
        report = await generator.generate_report(current_user, request)

        # Send notification via WebSocket
        if services.websocket_service:
            await services.websocket_service.emit_synthesis_event(
                user_id=current_user,
                synthesis_type="report",
                resource_id=report.id,
                title=report.title,
                preview=report.executive_summary[:200],
                action_url=f"/reports/{report.id}",
                priority=0.8
            )

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=list[ReportTemplate])
async def get_report_templates(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[ReportTemplate]:
    """Get available report templates."""
    # In production, load from database
    templates = [
        ReportTemplate(
            name="Weekly Summary",
            description="Comprehensive weekly activity summary",
            report_type=ReportType.WEEKLY,
            sections=["executive_summary", "highlights", "new_discoveries", "statistics", "recommendations"],
            include_visualizations=True,
            include_metrics=True,
            include_recommendations=True
        ),
        ReportTemplate(
            name="Monthly Insights",
            description="AI-powered monthly insights and analysis",
            report_type=ReportType.INSIGHTS,
            sections=["executive_summary", "patterns", "emerging_topics", "knowledge_gaps", "growth_metrics", "recommendations"],
            include_visualizations=True,
            include_metrics=True,
            include_recommendations=True
        ),
        ReportTemplate(
            name="Learning Progress",
            description="Track your learning progress and achievements",
            report_type=ReportType.PROGRESS,
            sections=["executive_summary", "progress_overview", "learning_metrics", "achievements", "comparisons", "recommendations"],
            include_visualizations=True,
            include_metrics=True,
            include_recommendations=True
        )
    ]

    return templates


@router.post("/templates", response_model=ReportTemplate)
async def create_report_template(
    template: ReportTemplate,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReportTemplate:
    """Create a custom report template."""
    # In production, save to database
    template.created_at = datetime.utcnow()
    template.updated_at = datetime.utcnow()

    return template


@router.get("/schedules", response_model=list[ReportSchedule])
async def get_report_schedules(
    enabled_only: bool = Query(True, description="Only return enabled schedules"),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[ReportSchedule]:
    """Get user's report schedules."""
    # In production, load from database
    schedules = []

    if not enabled_only or True:  # Placeholder logic
        schedules.append(
            ReportSchedule(
                user_id=current_user,
                template_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
                report_type=ReportType.WEEKLY,
                format=ReportFormat.EMAIL,
                schedule_type="weekly",
                schedule_config={"day_of_week": "monday", "time": "09:00"},
                recipients=[f"{current_user}@example.com"],
                enabled=True,
                next_scheduled=datetime.utcnow()
            )
        )

    return schedules


@router.post("/schedules", response_model=ReportSchedule)
async def create_report_schedule(
    schedule: ReportSchedule,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReportSchedule:
    """Schedule automated report generation."""
    schedule.user_id = current_user
    schedule.created_at = datetime.utcnow()

    # In production, save to database and schedule job

    return schedule


@router.put("/schedules/{schedule_id}", response_model=ReportSchedule)
async def update_report_schedule(
    schedule_id: UUID,
    updates: dict,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReportSchedule:
    """Update a report schedule."""
    # In production, update in database

    # Return mock updated schedule
    schedule = ReportSchedule(
        id=schedule_id,
        user_id=current_user,
        template_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        report_type=ReportType.WEEKLY,
        format=ReportFormat.EMAIL,
        schedule_type="weekly",
        schedule_config=updates.get("schedule_config", {"day_of_week": "monday", "time": "09:00"}),
        recipients=updates.get("recipients", [f"{current_user}@example.com"]),
        enabled=updates.get("enabled", True),
        next_scheduled=datetime.utcnow()
    )

    return schedule


@router.delete("/schedules/{schedule_id}")
async def delete_report_schedule(
    schedule_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a report schedule."""
    # In production, delete from database

    return {"success": True, "message": "Schedule deleted successfully"}


@router.get("/history", response_model=list[GeneratedReport])
async def get_report_history(
    report_type: ReportType | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[GeneratedReport]:
    """Get user's report generation history."""
    # In production, load from database

    # Return mock history
    history = []
    for i in range(min(limit, 5)):
        report = GeneratedReport(
            user_id=current_user,
            report_type=report_type or ReportType.WEEKLY,
            title=f"Weekly Report #{i+1}",
            subtitle="January 15-22, 2025",
            executive_summary="This week showed significant progress in knowledge acquisition...",
            sections=[],
            format=ReportFormat.HTML,
            generation_time_ms=1234,
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow()
        )
        history.append(report)

    return history


@router.get("/{report_id}", response_model=GeneratedReport)
async def get_report(
    report_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GeneratedReport:
    """Get a specific generated report."""
    # In production, load from database

    report = GeneratedReport(
        id=report_id,
        user_id=current_user,
        report_type=ReportType.WEEKLY,
        title="Weekly Progress Report",
        subtitle="January 15-22, 2025",
        executive_summary="This week showed significant progress in knowledge acquisition and retention.",
        sections=[],
        format=ReportFormat.HTML,
        generation_time_ms=1234,
        period_start=datetime.utcnow(),
        period_end=datetime.utcnow()
    )

    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    format: ReportFormat | None = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a generated report in specified format."""
    # In production, return file response

    return {
        "download_url": f"/reports/{report_id}/download/{format or 'pdf'}",
        "expires_at": datetime.utcnow().isoformat()
    }


@router.post("/{report_id}/share")
async def share_report(
    report_id: UUID,
    recipients: list[str],
    message: str | None = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Share a report with other users."""
    # In production, send emails or create share links

    return {
        "success": True,
        "shared_with": recipients,
        "share_link": f"/reports/shared/{report_id}",
        "expires_at": datetime.utcnow().isoformat()
    }
