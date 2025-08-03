"""
V2 API routers collection
Organized by functionality with proper OpenAPI tags
"""

from fastapi import APIRouter

from .memories import router as memories_router
from .search import router as search_router
from .health import router as health_router
from .websocket import router as websocket_router

# Create main v2 router
v2_router = APIRouter(prefix="/api/v2")

# Include all sub-routers
v2_router.include_router(memories_router)
v2_router.include_router(search_router)
v2_router.include_router(health_router)
v2_router.include_router(websocket_router)

__all__ = [
    "v2_router",
    "memories_router",
    "search_router",
    "health_router",
    "websocket_router"
]