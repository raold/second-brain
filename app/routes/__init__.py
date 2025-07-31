"""
Route handlers for Second Brain API.
Thin controllers that delegate business logic to service layer.
"""

# DISABLED: from .analysis_routes import router as analysis_router
# DISABLED: from .bulk_operations_routes import bulk_router as bulk_operations_router
# DISABLED: from .dashboard_routes import router as dashboard_router
# DISABLED: from .google_drive_routes import router as google_drive_router
# DISABLED: from .graph_routes import router as graph_router
from .health_routes import router as health_router

# DISABLED: from .importance_routes import router as importance_router
# DISABLED: from .ingestion_routes import router as ingestion_router
# DISABLED: from .insights import router as insights_router
# DISABLED: from .memory_routes import router as memory_router
# DISABLED: from .relationship_routes import router as relationship_router
# DISABLED: from .report_routes import router as report_router
# DISABLED: from .session_routes import router as session_router
# DISABLED: from .synthesis_routes import router as synthesis_router
# DISABLED: from .v2_api import router as v2_router
# DISABLED: from .visualization_routes import router as visualization_router
# DISABLED: from .websocket_routes import router as websocket_router

__all__ = [
    "analysis_router",
    "bulk_operations_router",
    "dashboard_router",
    "google_drive_router",
    "graph_router",
    "health_router",
    "importance_router",
    "ingestion_router",
    "insights_router",
    "memory_router",
    "relationship_router",
    "report_router",
    "session_router",
    "synthesis_router",
    "v2_router",
    "visualization_router",
    "websocket_router",
]
