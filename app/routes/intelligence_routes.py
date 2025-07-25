"""
API routes for v2.8.3 Intelligence features.

This module provides endpoints for analytics dashboard, predictive insights,
anomaly detection, and knowledge gap analysis.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.intelligence.analytics_models import (
    AnalyticsDashboard,
    AnalyticsQuery,
    Anomaly,
    AnomalyType,
    InsightCategory,
    KnowledgeGap,
    MetricThreshold,
    MetricType,
    PerformanceBenchmark,
    PredictiveInsight,
    TimeGranularity,
)
from app.routes.auth import get_current_user
from app.services.intelligence.analytics_dashboard import AnalyticsDashboardService
from app.services.intelligence.anomaly_detection import AnomalyDetectionService
from app.services.intelligence.knowledge_gap_analysis import KnowledgeGapAnalyzer
from app.services.intelligence.predictive_insights import PredictiveInsightsService

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


def get_analytics_service() -> AnalyticsDashboardService:
    """Get analytics dashboard service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_analytics_service()


def get_insights_service() -> PredictiveInsightsService:
    """Get predictive insights service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_insights_service()


def get_anomaly_service() -> AnomalyDetectionService:
    """Get anomaly detection service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_anomaly_service()


def get_gap_analyzer() -> KnowledgeGapAnalyzer:
    """Get knowledge gap analyzer."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_gap_analyzer()


@router.post("/analytics/dashboard", response_model=AnalyticsDashboard)
async def generate_analytics_dashboard(
    query: AnalyticsQuery,
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """
    Generate a comprehensive analytics dashboard.

    The dashboard includes:
    - Time series metrics for various KPIs
    - Predictive insights and recommendations
    - Anomaly detection results
    - Knowledge gap analysis
    """
    try:
        # Add user context to query if not specified
        if not query.user_id:
            query.user_id = current_user["user_id"]

        dashboard = await analytics_service.generate_dashboard(query)
        return dashboard

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/metrics", response_model=list[str])
async def list_available_metrics(
    current_user: dict = Depends(get_current_user)
):
    """List all available metric types for analytics."""
    return [metric.value for metric in MetricType]


@router.get("/analytics/insights", response_model=list[PredictiveInsight])
async def get_predictive_insights(
    category: Optional[InsightCategory] = None,
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    min_impact: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """
    Get predictive insights based on current metrics.

    Insights are filtered by:
    - Category (performance, knowledge, behavior, etc.)
    - Minimum confidence score
    - Minimum impact score
    """
    try:
        # Generate minimal dashboard to get insights
        query = AnalyticsQuery(
            user_id=current_user["user_id"],
            granularity=TimeGranularity.HOUR,
            include_insights=True,
            include_anomalies=False,
            include_knowledge_gaps=False
        )

        dashboard = await analytics_service.generate_dashboard(query)

        # Filter insights
        insights = dashboard.insights

        if category:
            insights = [i for i in insights if i.category == category]

        insights = [
            i for i in insights
            if i.confidence >= min_confidence and i.impact_score >= min_impact
        ]

        return insights[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/anomalies", response_model=list[Anomaly])
async def get_detected_anomalies(
    metric_type: Optional[MetricType] = None,
    anomaly_type: Optional[AnomalyType] = None,
    min_severity: float = Query(0.5, ge=0.0, le=1.0),
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """
    Get detected anomalies in metrics.

    Filter by:
    - Metric type
    - Anomaly type (spike, drop, pattern break, etc.)
    - Minimum severity
    - Time window (hours)
    """
    try:
        # Generate dashboard with anomaly detection
        query = AnalyticsQuery(
            user_id=current_user["user_id"],
            granularity=TimeGranularity.HOUR,
            include_insights=False,
            include_anomalies=True,
            include_knowledge_gaps=False
        )

        dashboard = await analytics_service.generate_dashboard(query)

        # Filter anomalies
        anomalies = dashboard.get_recent_anomalies(hours)

        if metric_type:
            anomalies = [a for a in anomalies if a.metric_type == metric_type]

        if anomaly_type:
            anomalies = [a for a in anomalies if a.anomaly_type == anomaly_type]

        anomalies = [a for a in anomalies if a.severity >= min_severity]

        return anomalies

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/knowledge-gaps", response_model=list[KnowledgeGap])
async def analyze_knowledge_gaps(
    limit: int = Query(20, ge=1, le=50),
    focus_areas: Optional[list[str]] = Query(None),
    current_user: dict = Depends(get_current_user),
    gap_analyzer: KnowledgeGapAnalyzer = Depends(get_gap_analyzer)
):
    """
    Analyze knowledge gaps in the memory base.

    Identifies:
    - Under-represented topics
    - Missing connections between concepts
    - Unanswered questions
    - Incomplete knowledge areas
    """
    try:
        gaps = await gap_analyzer.analyze_knowledge_gaps(
            user_id=current_user["user_id"],
            limit=limit,
            focus_areas=focus_areas
        )

        return gaps

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/benchmarks", response_model=list[PerformanceBenchmark])
async def get_performance_benchmarks(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """Get current performance benchmarks for various operations."""
    try:
        benchmarks = await analytics_service.get_performance_benchmarks()
        return benchmarks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/thresholds", response_model=dict)
async def set_metric_threshold(
    threshold: MetricThreshold,
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """Set alerting threshold for a metric."""
    try:
        success = await analytics_service.set_metric_threshold(threshold)
        return {"success": success, "message": "Threshold configured successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/thresholds", response_model=list[MetricThreshold])
async def get_metric_thresholds(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """Get all configured metric thresholds."""
    try:
        thresholds = await analytics_service.get_metric_thresholds()
        return thresholds

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/export")
async def export_analytics_data(
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """
    Export analytics data in JSON or CSV format.

    Note: CSV export is simplified and may not include all nested data.
    """
    try:
        query = AnalyticsQuery(
            user_id=current_user["user_id"],
            start_date=start_date,
            end_date=end_date,
            granularity=TimeGranularity.DAY
        )

        dashboard = await analytics_service.generate_dashboard(query)

        if format == "json":
            return dashboard.dict()
        else:
            # Simplified CSV export
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow([
                "Metric", "Timestamp", "Value", "Trend", "Average"
            ])

            # Write metric data
            for metric_type, series in dashboard.metrics.items():
                for point in series.data_points:
                    writer.writerow([
                        metric_type.value,
                        point.timestamp.isoformat(),
                        point.value,
                        series.trend.value,
                        series.average
                    ])

            return {
                "content": output.getvalue(),
                "media_type": "text/csv",
                "filename": f"analytics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/refresh")
async def refresh_analytics_cache(
    current_user: dict = Depends(get_current_user),
    analytics_service: AnalyticsDashboardService = Depends(get_analytics_service)
):
    """Force refresh of analytics cache."""
    try:
        # Clear the metrics cache
        analytics_service._metrics_cache.clear()

        return {
            "success": True,
            "message": "Analytics cache cleared successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
