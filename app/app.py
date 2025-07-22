"""
Simple FastAPI application for Second Brain.
Minimal dependencies, direct database access.
"""

import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.connection_pool import PoolConfig, close_pool, get_pool_manager, initialize_pool
from app.conversation_processor import setup_conversation_monitoring

# Dashboard and conversation processing imports
from app.dashboard_api import setup_dashboard_routes
from app.database import get_database
from app.docs import (
    ContextualSearchRequest,
    EpisodicMemoryRequest,
    HealthResponse,
    MemoryResponse,
    MemoryType,
    ProceduralMemoryRequest,
    SemanticMemoryRequest,
    StatusResponse,
    setup_openapi_documentation,
)
from app.routes import (
    dashboard_router as new_dashboard_router,
)
from app.routes import (
    github_router,
    health_router,
    memory_router,
    migration_router,
    todo_router,
    visualization_router,
)
from app.routes import (
    session_router as new_session_router,
)
from app.routes.graph_routes import router as graph_router
from app.routes.analysis_routes import router as analysis_router

# Import bulk operations routes
from app.routes.bulk_operations_routes import bulk_router

# Import importance routes
from app.routes.importance_routes import router as importance_router

# Import relationship routes
from app.routes.relationship_routes import router as relationship_router
from app.security import SecurityConfig, SecurityManager

# Import service factory and refactored routes
from app.services.service_factory import get_service_factory
from app.session_api import setup_session_routes
from app.session_manager import get_session_manager
from app.version import get_version_info

from .routes.bulk_routes import get_bulk_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Security configuration
security_config = SecurityConfig(
    max_requests_per_minute=100,  # Increased for better UX
    max_requests_per_hour=5000,
    max_content_length=50000,  # 50KB for larger memories
    enable_rate_limiting=True,
    enable_input_validation=True,
    enable_security_headers=True,
    allowed_origins=["http://localhost:3000", "http://localhost:8000"],
)

# Create security manager
security_manager = SecurityManager(security_config)


# Import shared utilities
from app.shared import get_db_instance, verify_api_key


# Legacy search request model (keeping for backward compatibility)
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int | None = Field(default=10, ge=1, le=100, description="Maximum results")


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Starting Second Brain application")

    # Check if using mock database
    use_mock = os.getenv("USE_MOCK_DATABASE", "false").lower() == "true"

    # Initialize database
    db = None
    if use_mock:
        logger.info("Using mock database - skipping PostgreSQL initialization")
        # Initialize mock database
        from app.database_mock import MockDatabase

        db = MockDatabase()
        await db.initialize()
        logger.info("Mock database initialized")
    else:
        # Initialize database connection pool
        database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/secondbrain")
        pool_config = PoolConfig(min_connections=5, max_connections=20, max_inactive_connection_lifetime=300.0)

        try:
            await initialize_pool(database_url, pool_config)
            logger.info("Database connection pool initialized")
            db = await get_database()
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            # Fallback to regular database connection
            db = await get_database()
            logger.info("Database initialized (fallback mode)")

    # Initialize service factory with dependencies
    service_factory = get_service_factory()
    service_factory.set_database(db)
    service_factory.set_security_manager(security_manager)
    logger.info("Service factory initialized")

    # Initialize automation service
    from app.services.automation_service import automation_service
    
    try:
        await automation_service.initialize()
        logger.info("Automation service initialized - scheduled tasks and triggers active")
    except Exception as e:
        logger.error(f"Failed to initialize automation service: {e}")
        logger.warning("Application running without automated tasks")

    yield

    # Cleanup
    
    # Shutdown automation service
    try:
        await automation_service.shutdown()
        logger.info("Automation service shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down automation service: {e}")
    
    use_mock = os.getenv("USE_MOCK_DATABASE", "false").lower() == "true"

    if use_mock:
        logger.info("Mock database cleanup - no action needed")
    else:
        try:
            await close_pool()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            # Fallback cleanup
            try:
                db = await get_database()
                await db.close()
                logger.info("Database closed (fallback mode)")
            except Exception as cleanup_error:
                logger.error(f"Error in fallback cleanup: {cleanup_error}")

    logger.info("Application shutdown complete")


# Create FastAPI app
from app.version import __version__

app = FastAPI(
    title="Second Brain API",
    description="Simple memory storage and search system",
    version=__version__,
    lifespan=lifespan,
)

# Setup OpenAPI documentation
setup_openapi_documentation(app)


# Add comprehensive error handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "method": request.method,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed feedback."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "type": "ValidationError",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with proper logging."""
    error_id = f"error_{int(time.time())}"
    logger.error(f"Unexpected error {error_id}: {exc}\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error occurred",
                "type": "InternalServerError",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "error_id": error_id,
            }
        },
    )


# Add security middleware
for middleware_class, middleware_kwargs in security_manager.get_security_middleware():
    app.add_middleware(middleware_class, **middleware_kwargs)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_config.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include refactored routers
app.include_router(memory_router)
app.include_router(health_router)
app.include_router(new_session_router)
app.include_router(new_dashboard_router)
app.include_router(todo_router)
app.include_router(github_router)
app.include_router(migration_router)
app.include_router(visualization_router)
app.include_router(importance_router)
app.include_router(relationship_router)
app.include_router(bulk_router)
app.include_router(graph_router)
app.include_router(analysis_router)

# Include insights router
from app.routes.insights import router as insights_router
from app.routes.batch_routes import router as batch_router
from app.routes.automation_routes import router as automation_router

app.include_router(insights_router)
app.include_router(batch_router, dependencies=[Depends(verify_api_key)])
app.include_router(automation_router, dependencies=[Depends(verify_api_key)])

# Include bulk operations routes
app.include_router(get_bulk_routes(), dependencies=[Depends(verify_api_key)])

# Include multimodal routes
try:
    from multimodal.api import router as multimodal_router
    app.include_router(multimodal_router, dependencies=[Depends(verify_api_key)])
    logger.info("Multimodal routes successfully integrated")
except ImportError as e:
    logger.warning(f"Could not import multimodal routes: {e}")
except Exception as e:
    logger.error(f"Error integrating multimodal routes: {e}")

# Setup legacy dashboard and session routes (temporary until full migration)
setup_dashboard_routes(app)
setup_session_routes(app)
setup_conversation_monitoring()

# Initialize session management
session_manager = get_session_manager()
logger.info("Session management initialized for persistent context continuity")

# Serve static files for dashboard
from fastapi.staticfiles import StaticFiles

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


# Dashboard homepage
@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the project dashboard homepage"""
    try:
        with open("static/dashboard.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head><title>Project Pipeline Dashboard</title></head>
        <body>
        <h1>🎯 Project Pipeline Dashboard</h1>
        <p>Dashboard is initializing... Please visit <a href="/dashboard/">/dashboard/</a> for API access.</p>
        <p>Or visit <a href="/docs">/docs</a> for the API documentation.</p>
        </body>
        </html>
        """
        )


# Mobile interface
@app.get("/mobile", response_class=HTMLResponse)
async def mobile_interface():
    """Serve the mobile-optimized interface"""
    try:
        with open("static/mobile.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head>
            <title>Mobile - Second Brain</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
        <h1>📱 Mobile Interface</h1>
        <p>Mobile interface is not available. Please check your installation.</p>
        </body>
        </html>
        """
        )


# AI Insights Dashboard
@app.get("/insights", response_class=HTMLResponse)
async def insights_dashboard():
    """Serve the AI insights dashboard"""
    try:
        with open("static/insights-dashboard.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head>
            <title>AI Insights - Second Brain</title>
        </head>
        <body>
        <h1>🧠 AI Insights Dashboard</h1>
        <p>Insights dashboard is not available. Please check your installation.</p>
        </body>
        </html>
        """
        )


# Health check
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check system health and version information",
    response_model=HealthResponse,
)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime

    version_info = get_version_info()
    return HealthResponse(status="healthy", version=version_info["version"], timestamp=datetime.utcnow())


# Database and index status
@app.get(
    "/status",
    tags=["Health"],
    summary="System Status",
    description="Get database and performance metrics",
    response_model=StatusResponse,
)
async def get_status(db=Depends(get_db_instance), _: str = Depends(verify_api_key)):
    """Get database and index status for performance monitoring."""
    try:
        stats = await db.get_index_stats()
        return StatusResponse(
            database="connected",
            index_status=stats,
            recommendations={
                "create_index": not stats["index_ready"] and stats["memories_with_embeddings"] >= 1000,
                "index_type": "HNSW (preferred)"
                if stats["hnsw_index_exists"]
                else "IVFFlat (fallback)"
                if stats["ivf_index_exists"]
                else "None",
                "performance_note": "Index recommended for 1000+ memories"
                if stats["memories_with_embeddings"] < 1000
                else "Index should be active for optimal performance",
            },
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# Search memories
@app.post(
    "/memories/search",
    response_model=list[MemoryResponse],
    tags=["Search"],
    summary="Search Memories",
    description="Semantic search across stored memories",
)
async def search_memories(
    request: SearchRequest, request_obj: Request, db=Depends(get_db_instance), _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input validation
        validator = security_manager.input_validator
        validated_query = validator.validate_search_query(request.query)
        validated_limit = validator.validate_search_limit(request.limit or 10)

        memories = await db.search_memories(validated_query, validated_limit)
        return [MemoryResponse(**memory) for memory in memories]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to search memories")


# Get memory by ID
@app.get(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    tags=["Memories"],
    summary="Get Memory",
    description="Retrieve a specific memory by ID",
)
async def get_memory(memory_id: str, db=Depends(get_db_instance), _: str = Depends(verify_api_key)):
    """Get a specific memory by ID."""
    try:
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return MemoryResponse(**memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to get memory")


# Delete memory
@app.delete(
    "/memories/{memory_id}", tags=["Memories"], summary="Delete Memory", description="Delete a specific memory by ID"
)
async def delete_memory(memory_id: str, db=Depends(get_db_instance), _: str = Depends(verify_api_key)):
    """Delete a memory by ID."""
    try:
        deleted = await db.delete_memory(memory_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {"message": "Memory deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete memory")


# Type-specific memory storage endpoints
@app.post(
    "/memories/semantic",
    response_model=MemoryResponse,
    tags=["Memory Types"],
    summary="Store Semantic Memory",
    description="Store a semantic memory (facts, concepts, general knowledge)",
)
async def store_semantic_memory(
    request: SemanticMemoryRequest, request_obj: Request, db=Depends(get_db_instance), _: str = Depends(verify_api_key)
):
    """Store a semantic memory with domain-specific metadata."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input validation
        validator = security_manager.input_validator
        validated_content = validator.validate_memory_content(request.content)

        semantic_metadata = request.semantic_metadata.dict() if request.semantic_metadata else {}

        memory_id = await db.store_memory(
            content=validated_content,
            memory_type=MemoryType.SEMANTIC.value,
            semantic_metadata=semantic_metadata,
            importance_score=request.importance_score or 0.5,
        )
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

        return MemoryResponse(**memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store semantic memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store semantic memory")


@app.post(
    "/memories/episodic",
    response_model=MemoryResponse,
    tags=["Memory Types"],
    summary="Store Episodic Memory",
    description="Store an episodic memory (time-bound experiences, contextual events)",
)
async def store_episodic_memory(
    request: EpisodicMemoryRequest, request_obj: Request, db=Depends(get_db_instance), _: str = Depends(verify_api_key)
):
    """Store an episodic memory with temporal and contextual metadata."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input validation
        validator = security_manager.input_validator
        validated_content = validator.validate_memory_content(request.content)

        episodic_metadata = request.episodic_metadata.dict() if request.episodic_metadata else {}

        memory_id = await db.store_memory(
            content=validated_content,
            memory_type=MemoryType.EPISODIC.value,
            episodic_metadata=episodic_metadata,
            importance_score=request.importance_score or 0.5,
        )
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

        return MemoryResponse(**memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store episodic memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store episodic memory")


@app.post(
    "/memories/procedural",
    response_model=MemoryResponse,
    tags=["Memory Types"],
    summary="Store Procedural Memory",
    description="Store a procedural memory (process knowledge, workflows, instructions)",
)
async def store_procedural_memory(
    request: ProceduralMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
):
    """Store a procedural memory with skill and process metadata."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input validation
        validator = security_manager.input_validator
        validated_content = validator.validate_memory_content(request.content)

        procedural_metadata = request.procedural_metadata.dict() if request.procedural_metadata else {}

        memory_id = await db.store_memory(
            content=validated_content,
            memory_type=MemoryType.PROCEDURAL.value,
            procedural_metadata=procedural_metadata,
            importance_score=request.importance_score or 0.5,
        )
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

        return MemoryResponse(**memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store procedural memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store procedural memory")


# Enhanced contextual search endpoint
@app.post(
    "/memories/search/contextual",
    response_model=list[MemoryResponse],
    tags=["Search"],
    summary="Contextual Memory Search",
    description="Advanced search with memory type filtering and multi-dimensional scoring",
)
async def contextual_search(
    request: ContextualSearchRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
):
    """Perform contextual search with cognitive memory filtering."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Input validation
        validator = security_manager.input_validator
        validated_query = validator.validate_search_query(request.query)

        # Convert memory types to string values
        memory_types = [mt.value for mt in request.memory_types] if request.memory_types else None

        memories = await db.contextual_search(
            query=validated_query,
            limit=request.limit,
            memory_types=memory_types,
            importance_threshold=request.importance_threshold,
            timeframe=request.timeframe,
            include_archived=request.include_archived,
        )

        return [MemoryResponse(**memory) for memory in memories]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform contextual search: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform contextual search")


# Security status endpoint
@app.get(
    "/security/status",
    tags=["Security"],
    summary="Security Status",
    description="Get security metrics and health status",
)
async def get_security_status(_: str = Depends(verify_api_key)):
    """Get security monitoring statistics."""
    try:
        security_stats = security_manager.get_security_stats()

        # Get pool health if available
        pool_health = {}
        pool_manager = get_pool_manager()
        if pool_manager:
            pool_health = await pool_manager.health_check()

        return {"security": security_stats, "database_pool": pool_health, "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security status")


# Comprehensive monitoring endpoint
@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Performance Metrics",
    description="Get comprehensive system performance and health metrics",
)
async def get_metrics(_: str = Depends(verify_api_key)):
    """Get comprehensive system metrics for monitoring."""
    try:
        import time

        import psutil

        # System metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used // 1024 // 1024,
            "memory_available_mb": psutil.virtual_memory().available // 1024 // 1024,
            "disk_percent": psutil.disk_usage("/").percent if hasattr(psutil.disk_usage("/"), "percent") else 0,
            "uptime_seconds": time.time() - psutil.boot_time(),
        }

        # Security metrics
        security_stats = security_manager.get_security_stats()

        # Database pool metrics
        pool_health = {}
        pool_manager = get_pool_manager()
        if pool_manager:
            pool_health = await pool_manager.health_check()

        # Application metrics
        app_metrics = {
            "version": get_version_info()["version"],
            "environment": "test" if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true" else "production",
        }

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics,
            "security": security_stats,
            "database": pool_health,
            "application": app_metrics,
            "uptime_formatted": f"{system_metrics['uptime_seconds'] // 3600:.0f}h {(system_metrics['uptime_seconds'] % 3600) // 60:.0f}m",
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


# List all memories
@app.get(
    "/memories",
    response_model=list[MemoryResponse],
    tags=["Memories"],
    summary="List All Memories",
    description="Retrieve all memories with pagination support",
)
async def list_memories(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
):
    """List all memories with pagination."""
    try:
        memories = await db.get_all_memories(limit, offset)

        return [MemoryResponse(**memory) for memory in memories]

    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to list memories")


# Version endpoint for dashboard
@app.get("/version", summary="Get version information", response_model=dict)
async def get_version_endpoint():
    """Get comprehensive version information for dashboard and API clients."""
    from app.version import get_dashboard_version, get_version_info

    # Get comprehensive version info
    version_info = get_version_info()
    dashboard_info = get_dashboard_version()

    return {
        "version": version_info["version"],
        "version_string": version_info["version_string"],
        "display_name": version_info["display_name"],
        "codename": version_info["codename"],
        "release_date": version_info["release_date"],
        "build": version_info["build"],
        "environment": version_info["environment"],
        "git_commit": version_info["git_commit"],
        "build_timestamp": version_info["build_timestamp"],
        "dashboard": dashboard_info,
        "roadmap": version_info["roadmap_info"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
