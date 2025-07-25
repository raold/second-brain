"""
Metrics endpoint for Prometheus.

Exposes application metrics in Prometheus format.
"""

from fastapi import APIRouter, Response

from src.infrastructure.observability import get_metrics_collector

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def get_metrics() -> Response:
    """
    Get application metrics in Prometheus format.
    
    Returns:
        Prometheus formatted metrics
    """
    metrics_collector = get_metrics_collector()
    metrics_data = metrics_collector.get_metrics()
    
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4",
    )