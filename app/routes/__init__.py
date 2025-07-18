"""
Route handlers for Second Brain API.
Thin controllers that delegate business logic to service layer.
"""

from .memory_routes import router as memory_router
from .health_routes import router as health_router
from .session_routes import router as session_router
from .dashboard_routes import router as dashboard_router
from .todo_routes import router as todo_router
from .github_routes import router as github_router
from .migration_routes import router as migration_router
from .visualization_routes import router as visualization_router

__all__ = [
    "memory_router",
    "health_router",
    "session_router",
    "dashboard_router",
    "todo_router",
    "github_router",
    "migration_router",
    "visualization_router"
] 