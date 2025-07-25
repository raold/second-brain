"""
Monitoring API routes for real-time system monitoring.

Provides endpoints for accessing log analytics, performance metrics,
alerts, and system health data.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.routes.auth import get_current_user
from app.services.monitoring import AlertLevel, get_analytics_service, get_metrics_collector
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


class DashboardResponse(BaseModel):
    """Response model for monitoring dashboard data."""
    timestamp: str
    metrics_count: int
    recent_activity: dict[str, Any]
    operation_stats: dict[str, Any]
    performance_metrics: dict[str, Any]
    active_alerts: list[dict[str, Any]]


class AlertResponse(BaseModel):
    """Response model for alerts."""
    id: str
    level: str
    title: str
    message: str
    timestamp: str
    operation: str
    context: dict[str, Any]


class PerformanceResponse(BaseModel):
    """Response model for performance metrics."""
    operation: str
    avg_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    total_calls: int
    error_rate: float
    avg_memory_mb: float
    last_updated: str


class SystemHealthResponse(BaseModel):
    """Response model for system health."""
    status: str
    uptime_seconds: float
    total_operations: int
    error_rate: float
    avg_response_time_ms: float
    active_alerts_count: int
    memory_usage_mb: float
    top_operations: list[dict[str, Any]]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_monitoring_dashboard(
    current_user: dict = Depends(get_current_user)
):
    """Get real-time monitoring dashboard data."""
    try:
        analytics = get_analytics_service()
        data = analytics.get_dashboard_data()

        logger.info("Monitoring dashboard accessed", extra={
            "user_id": current_user.get("user_id"),
            "metrics_count": data["metrics_count"],
            "active_alerts": len(data["active_alerts"])
        })

        return DashboardResponse(**data)

    except Exception as e:
        logger.exception("Failed to get monitoring dashboard", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    level: Optional[str] = Query(None, description="Filter by alert level"),
    hours: int = Query(1, ge=1, le=24, description="Hours of alert history"),
    current_user: dict = Depends(get_current_user)
):
    """Get system alerts."""
    try:
        analytics = get_analytics_service()

        # Filter alerts by time
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in analytics.alerts if a.timestamp > cutoff]

        # Filter by level if specified
        if level:
            try:
                alert_level = AlertLevel(level.lower())
                alerts = [a for a in alerts if a.level == alert_level]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")

        # Convert to response format
        response_alerts = [
            AlertResponse(
                id=alert.id,
                level=alert.level.value,
                title=alert.title,
                message=alert.message,
                timestamp=alert.timestamp.isoformat(),
                operation=alert.source_operation,
                context=alert.context
            )
            for alert in alerts
        ]

        logger.info("Alerts retrieved", extra={
            "user_id": current_user.get("user_id"),
            "alert_count": len(response_alerts),
            "filter_level": level,
            "hours": hours
        })

        return response_alerts

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get alerts", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/performance", response_model=list[PerformanceResponse])
async def get_performance_metrics(
    operation: Optional[str] = Query(None, description="Filter by operation"),
    current_user: dict = Depends(get_current_user)
):
    """Get performance metrics for operations."""
    try:
        analytics = get_analytics_service()

        metrics = analytics.performance_cache

        # Filter by operation if specified
        if operation:
            if operation not in metrics:
                raise HTTPException(status_code=404, detail=f"No metrics found for operation: {operation}")
            metrics = {operation: metrics[operation]}

        # Convert to response format
        response_metrics = [
            PerformanceResponse(
                operation=perf.operation,
                avg_duration_ms=perf.avg_duration_ms,
                p95_duration_ms=perf.p95_duration_ms,
                p99_duration_ms=perf.p99_duration_ms,
                total_calls=perf.total_calls,
                error_rate=perf.error_rate,
                avg_memory_mb=perf.avg_memory_mb,
                last_updated=perf.last_updated.isoformat()
            )
            for perf in metrics.values()
        ]

        logger.info("Performance metrics retrieved", extra={
            "user_id": current_user.get("user_id"),
            "metrics_count": len(response_metrics),
            "filter_operation": operation
        })

        return response_metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get performance metrics", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: dict = Depends(get_current_user)
):
    """Get overall system health status."""
    try:
        analytics = get_analytics_service()

        # Calculate health metrics
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(minutes=5)
        recent_metrics = [m for m in analytics.metrics_buffer if m.timestamp > recent_cutoff]

        if not recent_metrics:
            status = "idle"
            error_rate = 0.0
            avg_response_time = 0.0
        else:
            # Calculate error rate
            error_count = sum(1 for m in recent_metrics if m.level in ['ERROR', 'CRITICAL'])
            error_rate = error_count / len(recent_metrics)

            # Calculate average response time
            durations = [m.duration_ms for m in recent_metrics if m.duration_ms is not None]
            avg_response_time = sum(durations) / len(durations) if durations else 0

            # Determine status
            if error_rate > 0.1:
                status = "critical"
            elif error_rate > 0.05 or avg_response_time > 2000:
                status = "warning"
            else:
                status = "healthy"

        # Get active alerts
        active_alerts = [a for a in analytics.alerts if (now - a.timestamp) < timedelta(minutes=30)]

        # Get top operations
        operation_counts = {}
        for metric in recent_metrics:
            operation_counts[metric.operation] = operation_counts.get(metric.operation, 0) + 1

        top_operations = [
            {"operation": op, "count": count}
            for op, count in sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Get memory usage (rough estimate from recent metrics)
        memory_values = [m.memory_mb for m in recent_metrics if m.memory_mb is not None]
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0

        health_data = SystemHealthResponse(
            status=status,
            uptime_seconds=0,  # Would need to track application start time
            total_operations=len(analytics.metrics_buffer),
            error_rate=error_rate,
            avg_response_time_ms=avg_response_time,
            active_alerts_count=len(active_alerts),
            memory_usage_mb=avg_memory,
            top_operations=top_operations
        )

        logger.info("System health checked", extra={
            "user_id": current_user.get("user_id"),
            "health_status": status,
            "error_rate": error_rate,
            "avg_response_time_ms": avg_response_time
        })

        return health_data

    except Exception as e:
        logger.exception("Failed to get system health", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to get system health")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge an alert (remove from active alerts)."""
    try:
        analytics = get_analytics_service()

        # Find and remove alert
        original_count = len(analytics.alerts)
        analytics.alerts = [a for a in analytics.alerts if a.id != alert_id]

        if len(analytics.alerts) == original_count:
            raise HTTPException(status_code=404, detail="Alert not found")

        logger.info("Alert acknowledged", extra={
            "user_id": current_user.get("user_id"),
            "alert_id": alert_id
        })

        return {"message": "Alert acknowledged", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to acknowledge alert", extra={
            "user_id": current_user.get("user_id"),
            "alert_id": alert_id,
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/operations")
async def get_operation_list(
    current_user: dict = Depends(get_current_user)
):
    """Get list of all tracked operations."""
    try:
        analytics = get_analytics_service()

        # Get unique operations from recent metrics
        operations = set()
        for metric in analytics.metrics_buffer:
            operations.add(metric.operation)

        operation_list = sorted(list(operations))

        logger.info("Operations list retrieved", extra={
            "user_id": current_user.get("user_id"),
            "operation_count": len(operation_list)
        })

        return {"operations": operation_list}
    except Exception as e:
        logger.error(f"Error getting operations list: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get operations list")


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get metrics in Prometheus format for scraping."""
    try:
        collector = get_metrics_collector()
        metrics = collector.get_prometheus_metrics()

        logger.debug("Prometheus metrics exported", extra={
            "metrics_length": len(metrics),
            "operation": "prometheus_export"
        })

        return metrics

    except Exception as e:
        logger.exception("Failed to export Prometheus metrics", extra={
            "error_type": type(e).__name__
        })
        return "# Error exporting metrics\n"


@router.get("/metrics/json")
async def get_json_metrics(
    current_user: dict = Depends(get_current_user)
):
    """Get detailed metrics in JSON format."""
    try:
        collector = get_metrics_collector()
        metrics = collector.get_json_metrics()

        logger.info("JSON metrics exported", extra={
            "user_id": current_user.get("user_id"),
            "counters_count": len(metrics["counters"]),
            "gauges_count": len(metrics["gauges"])
        })

        return metrics

    except Exception as e:
        logger.exception("Failed to export JSON metrics", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/metrics/summary")
async def get_metrics_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get high-level metrics summary."""
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary_stats()

        logger.info("Metrics summary retrieved", extra={
            "user_id": current_user.get("user_id"),
            "total_operations": summary["total_operations"],
            "error_rate": summary["error_rate"]
        })

        return summary

    except Exception as e:
        logger.exception("Failed to get metrics summary", extra={
            "user_id": current_user.get("user_id"),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to get metrics summary")
