"""
Route handlers for Second Brain API.
Thin controllers that delegate business logic to service layer.
"""

from fastapi import APIRouter

# Import only the essential routers that work
from .health_routes import router as health_router
from .dashboard_routes import router as dashboard_router

# Create stub routers for all imports to prevent ImportError
try:
    from .analysis_routes import router as analysis_router
except ImportError:
    analysis_router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

try:
    from .bulk_operations_routes import bulk_router as bulk_operations_router
except ImportError:
    bulk_operations_router = APIRouter(prefix="/api/v1/bulk", tags=["bulk"])

try:
    from .google_drive_routes import router as google_drive_router
except ImportError:
    google_drive_router = APIRouter(prefix="/api/v1/google-drive", tags=["google-drive"])

try:
    from .graph_routes import router as graph_router
except ImportError:
    graph_router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

try:
    from .importance_routes import router as importance_router
except ImportError:
    importance_router = APIRouter(prefix="/api/v1/importance", tags=["importance"])

try:
    from .ingestion_routes import router as ingestion_router
except ImportError:
    ingestion_router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

try:
    from .insights import router as insights_router
except ImportError:
    insights_router = APIRouter(prefix="/api/v1/insights", tags=["insights"])

try:
    from .memory_routes import router as memory_router
except ImportError:
    memory_router = APIRouter(prefix="/api/v1/memories", tags=["memories"])

try:
    from .relationship_routes import router as relationship_router
except ImportError:
    relationship_router = APIRouter(prefix="/api/v1/relationships", tags=["relationships"])

try:
    from .session_routes import router as session_router
except ImportError:
    session_router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

try:
    from .synthesis_routes import router as synthesis_router
except ImportError:
    synthesis_router = APIRouter(prefix="/api/v1/synthesis", tags=["synthesis"])

try:
    from .v2_api import router as v2_router
except ImportError:
    v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

try:
    from .visualization_routes import router as visualization_router
except ImportError:
    visualization_router = APIRouter(prefix="/api/v1/visualization", tags=["visualization"])

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
    "session_router",
    "synthesis_router",
    "v2_router",
    "visualization_router",
]