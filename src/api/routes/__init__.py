"""
API routes.

Organizes all API endpoints.
"""

from fastapi import FastAPI

from .attachments import router as attachments_router
from .auth import router as auth_router
from .health import router as health_router
from .memories import router as memories_router
from .metrics import router as metrics_router
from .sessions import router as sessions_router
from .tags import router as tags_router
from .users import router as users_router


def setup_routes(app: FastAPI) -> None:
    """
    Setup API routes.
    
    Args:
        app: FastAPI application instance
    """
    # Health check
    app.include_router(
        health_router,
        prefix="/api/health",
        tags=["health"],
    )
    
    # Authentication
    app.include_router(
        auth_router,
        prefix="/api/auth",
        tags=["auth"],
    )
    
    # Users
    app.include_router(
        users_router,
        prefix="/api/users",
        tags=["users"],
    )
    
    # Memories
    app.include_router(
        memories_router,
        prefix="/api/memories",
        tags=["memories"],
    )
    
    # Sessions
    app.include_router(
        sessions_router,
        prefix="/api/sessions",
        tags=["sessions"],
    )
    
    # Tags
    app.include_router(
        tags_router,
        prefix="/api/tags",
        tags=["tags"],
    )
    
    # Attachments
    app.include_router(
        attachments_router,
        prefix="/api",
        tags=["attachments"],
    )
    
    # Metrics (Prometheus)
    app.include_router(
        metrics_router,
        prefix="",  # No prefix, metrics at /metrics
    )