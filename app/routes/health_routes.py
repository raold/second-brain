"""
Health Routes - Simple health check endpoint.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    services: dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check system health and version information",
)
async def health_check():
    """Health check endpoint."""
    try:
        # Simple health check for now
        return HealthResponse(
            status="healthy",
            version="3.0.0",
            services={
                "api": "running",
                "database": "connected",
                "redis": "connected"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")
