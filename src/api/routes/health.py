"""
Health check endpoints.

Provides health and readiness checks.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import get_dependencies
from src.application import Dependencies

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(
    deps: Annotated[Dependencies, Depends(get_dependencies)]
):
    """
    Readiness check.
    
    Verifies all dependencies are available.
    """
    # Check database connection
    try:
        db = await deps.get_db_connection()
        async with db.get_session() as session:
            await session.execute("SELECT 1")
        
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
            }
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "checks": {
                "database": f"error: {str(e)}",
            }
        }