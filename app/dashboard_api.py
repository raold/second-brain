#!/usr/bin/env python3
"""
Dashboard API Endpoints - Live Project Data Service
Provides real-time project metrics, visual data, and automatic updates
"""

import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.dashboard import Status, get_dashboard
from app.docs import Priority

# Create router for dashboard endpoints
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class FeatureRequest(BaseModel):
    """Request model for adding new features"""

    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    priority: str = Field(default="high", description="Feature priority")


class MetricUpdate(BaseModel):
    """Request model for updating technical metrics"""

    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit of measurement")
    target: float | None = Field(default=None, description="Target value")


class ConversationContext(BaseModel):
    """Model for processing conversation context and extracting project updates"""

    message: str = Field(..., description="Conversation message from CTO")
    sender: str = Field(default="CTO", description="Message sender")


@dashboard_router.get("/")
async def get_dashboard_overview():
    """Get comprehensive dashboard overview for CTO"""
    try:
        dashboard = get_dashboard()
        summary = dashboard.get_dashboard_summary()

        return {
            "status": "success",
            "data": summary,
            "visual_report": dashboard.generate_visual_report(),
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@dashboard_router.get("/metrics")
async def get_technical_metrics():
    """Get current technical metrics with timeseries data"""
    try:
        dashboard = get_dashboard()
        latest_metrics = dashboard.get_latest_metrics()

        # Generate timeseries data for each metric
        timeseries_data = {}
        for metric_name in set(m.metric_name for m in dashboard.metrics):
            metric_history = [
                {"timestamp": m.timestamp, "value": m.value, "status": m.status}
                for m in dashboard.metrics
                if m.metric_name == metric_name
            ]
            timeseries_data[metric_name] = sorted(metric_history, key=lambda x: x["timestamp"])

        return {
            "status": "success",
            "latest_metrics": latest_metrics,
            "timeseries": timeseries_data,
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")


@dashboard_router.get("/milestones")
async def get_project_milestones():
    """Get all project milestones with progress tracking"""
    try:
        dashboard = get_dashboard()

        milestones_data = []
        for milestone in dashboard.milestones.values():
            # Get milestone tasks
            milestone_tasks = [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status.value,
                    "progress": 1.0 if t.status == Status.COMPLETED else 0.5 if t.status == Status.IN_PROGRESS else 0.0,
                }
                for t in dashboard.tasks.values()
                if t.milestone_id == milestone.id
            ]

            milestones_data.append(
                {
                    "id": milestone.id,
                    "name": milestone.name,
                    "description": milestone.description,
                    "target_date": milestone.target_date,
                    "completion_date": milestone.completion_date,
                    "status": milestone.status.value,
                    "progress": milestone.progress,
                    "dependencies": milestone.dependencies,
                    "tasks": milestone_tasks,
                    "created_at": milestone.created_at,
                }
            )

        return {
            "status": "success",
            "milestones": milestones_data,
            "total_count": len(milestones_data),
            "completed_count": sum(1 for m in milestones_data if m["status"] == "completed"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Milestones error: {str(e)}")


@dashboard_router.get("/sprints")
async def get_sprint_data():
    """Get current and historical sprint data"""
    try:
        dashboard = get_dashboard()
        current_sprint = dashboard.get_current_sprint()

        sprints_data = []
        for sprint in dashboard.sprints.values():
            sprint_progress = dashboard.calculate_sprint_progress(sprint.id)
            days_remaining = dashboard.get_sprint_days_remaining(sprint.id)

            sprints_data.append(
                {
                    "id": sprint.id,
                    "name": sprint.name,
                    "start_date": sprint.start_date,
                    "end_date": sprint.end_date,
                    "goals": sprint.goals,
                    "status": sprint.status.value,
                    "progress": sprint_progress,
                    "days_remaining": days_remaining,
                    "velocity": sprint.velocity,
                    "burn_down_data": sprint.burn_down_data,
                    "is_current": sprint.id == (current_sprint.id if current_sprint else None),
                }
            )

        return {
            "status": "success",
            "sprints": sprints_data,
            "current_sprint": current_sprint.id if current_sprint else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprints error: {str(e)}")


@dashboard_router.get("/risks")
async def get_project_risks():
    """Get current project risks and issues"""
    try:
        dashboard = get_dashboard()
        risks = dashboard.assess_project_risks()

        # Categorize risks
        risk_categories = {
            "critical": [r for r in risks if r["level"] == "high"],
            "warnings": [r for r in risks if r["level"] == "medium"],
            "minor": [r for r in risks if r["level"] == "low"],
        }

        return {
            "status": "success",
            "risks": risks,
            "categories": risk_categories,
            "risk_count": len(risks),
            "critical_count": len(risk_categories["critical"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risks error: {str(e)}")


@dashboard_router.post("/features")
async def add_feature(feature_request: FeatureRequest):
    """Add new feature based on CTO input"""
    try:
        priority_map = {
            "critical": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }

        priority = priority_map.get(feature_request.priority.lower(), Priority.HIGH)

        dashboard = get_dashboard()
        milestone_id = dashboard.add_new_feature_context(feature_request.name, feature_request.description, priority)

        updated_report = dashboard.generate_visual_report()

        return {
            "status": "success",
            "message": f"Added feature '{feature_request.name}' to project roadmap",
            "milestone_id": milestone_id,
            "updated_dashboard": updated_report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature addition error: {str(e)}")


@dashboard_router.post("/metrics")
async def update_metric(metric_update: MetricUpdate):
    """Update technical metric value"""
    try:
        dashboard = get_dashboard()
        dashboard.record_metric(
            metric_update.metric_name, metric_update.value, metric_update.unit, metric_update.target
        )

        return {
            "status": "success",
            "message": f"Updated metric '{metric_update.metric_name}' to {metric_update.value}{metric_update.unit}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metric update error: {str(e)}")


@dashboard_router.post("/context")
async def process_conversation_context(context: ConversationContext, background_tasks: BackgroundTasks):
    """
    Process conversation context and automatically update dashboard
    This is the key feature for automatic dashboard updates based on CTO discussions
    """
    try:
        message = context.message.lower()

        # Pattern matching for feature discussions
        feature_patterns = [
            r"(?:let'?s talk about|discuss|implement|add|create) (?:the )?(.+?)(?:\s|$)",
            r"(?:we need|i want|let'?s build) (?:a |an |the )?(.+?)(?:\s|$)",
            r"(?:automated|automatic) (.+?)(?:\s|$)",
            r"(?:new feature|feature) (?:called |named )?(.+?)(?:\s|$)",
        ]

        detected_features = []
        for pattern in feature_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                feature_name = match.strip().rstrip(".,!?").title()
                if len(feature_name) > 3 and feature_name not in detected_features:
                    detected_features.append(feature_name)

        # Process detected features
        updates = []
        dashboard = get_dashboard()

        for feature_name in detected_features:
            # Generate description based on context
            description = f"Feature discussed by {context.sender}: {feature_name}"

            # Add to dashboard
            milestone_id = dashboard.add_new_feature_context(feature_name, description)
            updates.append({"feature": feature_name, "milestone_id": milestone_id, "action": "added_to_roadmap"})

        # Generate updated dashboard view
        updated_report = dashboard.generate_visual_report()

        return {
            "status": "success",
            "message": f"Processed conversation context from {context.sender}",
            "detected_features": detected_features,
            "updates": updates,
            "updated_dashboard": updated_report if updates else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context processing error: {str(e)}")


@dashboard_router.get("/visual")
async def get_visual_dashboard():
    """Get visual dashboard data optimized for web display"""
    try:
        dashboard = get_dashboard()
        summary = dashboard.get_dashboard_summary()

        # Format data for visual components
        visual_data = {
            "overview": {
                "project_name": dashboard.project_name,
                "health_status": summary["overall_health"]["status"],
                "progress_percentage": round(summary["overall_health"]["progress"] * 100),
                "milestones_completed": summary["overall_health"]["milestones_completed"],
                "sprint_progress": round(summary["current_sprint"]["progress"] * 100),
                "last_updated": summary["last_updated"],
            },
            "metrics_chart": [
                {
                    "name": metric["name"].replace("_", " ").title(),
                    "current": metric["value"],
                    "target": metric["target"] or 0,
                    "unit": metric["unit"],
                    "status": metric["status"],
                    "percentage": min(100, (metric["value"] / metric["target"] * 100)) if metric["target"] else 0,
                }
                for metric in summary["technical_metrics"]
            ],
            "milestones_timeline": [
                {
                    "name": milestone["name"],
                    "progress": round(milestone["progress"] * 100),
                    "target_date": milestone["target_date"],
                    "status": milestone["status"],
                    "days_until": (datetime.fromisoformat(milestone["target_date"]) - datetime.now()).days,
                }
                for milestone in summary["upcoming_milestones"]
            ],
            "risk_summary": {
                "total_risks": len(summary["risks"]),
                "high_risk_count": len([r for r in summary["risks"] if r["level"] == "high"]),
                "risk_items": summary["risks"],
            },
            "recent_activity": summary["recent_completions"],
        }

        return {
            "status": "success",
            "visual_data": visual_data,
            "charts_config": {
                "progress_chart": "donut",
                "metrics_chart": "bar_horizontal",
                "timeline_chart": "gantt",
                "risk_chart": "alert_list",
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual dashboard error: {str(e)}")


@dashboard_router.get("/health")
async def dashboard_health():
    """Dashboard service health check"""
    try:
        dashboard = get_dashboard()
        return {
            "status": "healthy",
            "service": "project_dashboard",
            "milestones_count": len(dashboard.milestones),
            "tasks_count": len(dashboard.tasks),
            "metrics_count": len(dashboard.metrics),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard health check failed: {str(e)}")


# Convenience function for integration with main app
def setup_dashboard_routes(app):
    """Setup dashboard routes in main FastAPI app"""
    app.include_router(dashboard_router)
    return dashboard_router
