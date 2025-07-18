"""
Health Routes - Thin route handlers for health and status operations.
All business logic is delegated to HealthService.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from app.docs import HealthResponse, StatusResponse
from app.services.service_factory import get_health_service
from app.app import get_db_instance, verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check system health and version information"
)
async def health_check():
    """Health check endpoint."""
    try:
        health_service = get_health_service()
        health_status = await health_service.get_health_status()
        
        return HealthResponse(
            status=health_status["status"],
            version=health_status["version"],
            timestamp=health_status["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="System Status",
    description="Get database and performance metrics",
    dependencies=[Depends(verify_api_key)]
)
async def get_status(db=Depends(get_db_instance)):
    """Get database and index status for performance monitoring."""
    try:
        health_service = get_health_service()
        system_status = await health_service.get_system_status()
        
        return StatusResponse(
            database=system_status["database"],
            index_status=system_status["index_status"],
            recommendations=system_status["recommendations"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


@router.get(
    "/diagnostics",
    summary="Run Diagnostics",
    description="Run comprehensive system diagnostics",
    dependencies=[Depends(verify_api_key)]
)
async def run_diagnostics(db=Depends(get_db_instance)):
    """Run system diagnostics and return results."""
    try:
        health_service = get_health_service()
        diagnostics = await health_service.run_diagnostics()
        
        # Return appropriate status code based on overall status
        status_code = 200
        if diagnostics["overall_status"] == "degraded":
            status_code = 207  # Multi-Status
        elif diagnostics["overall_status"] == "critical":
            status_code = 503  # Service Unavailable
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail="Diagnostics failed")


@router.get(
    "/metrics",
    summary="Get Performance Metrics",
    description="Get detailed performance metrics",
    dependencies=[Depends(verify_api_key)]
)
async def get_performance_metrics(db=Depends(get_db_instance)):
    """Get performance metrics."""
    try:
        health_service = get_health_service()
        metrics = await health_service.get_performance_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics") 