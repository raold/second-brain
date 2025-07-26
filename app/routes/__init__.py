"""
Route handlers for Second Brain API.
Thin controllers that delegate business logic to service layer.
"""

from .analysis_routes import router as analysis_router
from .bulk_operations_routes import bulk_router as bulk_operations_router
from .dashboard_routes import router as dashboard_router
from .github_routes import router as github_router
from .google_drive_routes import router as google_drive_router
from .graph_routes import router as graph_router
from .health_routes import router as health_router
from .importance_routes import router as importance_router
from .ingestion_routes import router as ingestion_router
from .insights import router as insights_router
from .memory_routes import router as memory_router
from .migration_routes import router as migration_router
from .relationship_routes import router as relationship_router
from .report_routes import router as report_router
from .session_routes import router as session_router
from .synthesis_routes import router as synthesis_router
from .todo_routes import router as todo_router
from .visualization_routes import router as visualization_router
from .websocket_routes import router as websocket_router

__all__ = [
    "analysis_router",
    "bulk_operations_router", 
    "dashboard_router",
    "github_router",
    "google_drive_router",
    "graph_router",
    "health_router",
    "importance_router",
    "ingestion_router",
    "insights_router",
    "memory_router",
    "migration_router",
    "relationship_router",
    "report_router",
    "session_router",
    "synthesis_router",
    "todo_router",
    "visualization_router",
    "websocket_router",
]
