import os
from datetime import datetime

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.redis_manager import get_redis_client
from app.database import get_database
from app.models.memory import MemoryType
from app.utils.logging_config import get_logger

"""
Second Brain API Application Module

This module defines the main FastAPI application for Second Brain.
It handles:
- Application lifecycle (startup/shutdown)
- Security configuration
- Route registration
- Middleware setup
- Error handling

The application is initialized and run from main.py in the project root.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.connection_pool import PoolConfig, close_pool, get_pool_manager, initialize_pool
from app.conversation_processor import setup_conversation_monitoring
from app.core.exceptions import register_exception_handlers
from app.core.logging import LogConfig, LoggingRoute, configure_logging, get_logger
from app.core.monitoring import (
    MetricDefinition,
    MetricType,
    export_metrics,
    get_health_checker,
    get_metrics_collector,
    get_request_tracker,
)
from app.core.rate_limiting import setup_rate_limiting
from app.core.redis_manager import (
    cleanup_redis,
    get_redis_manager,
    redis_health_check,
)
from app.core.security_audit import (
    SecurityHeadersManager,
    get_security_auditor,
    get_security_monitor,
)
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
    health_router,
    memory_router,
    visualization_router,
)
from app.routes import (
    session_router as new_session_router,
)
from app.routes.analysis_routes import router as analysis_router
from app.routes.bulk_operations_routes import bulk_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.google_drive_routes import router as google_drive_router
from app.routes.graph_routes import router as graph_router
from app.routes.importance_routes import router as importance_router
from app.routes.ingestion_routes import router as ingestion_router
from app.routes.insights import router as insights_router
from app.routes.relationship_routes import router as relationship_router
from app.routes.synthesis_routes import router as synthesis_router
from app.routes.v2_unified_api import router as v2_unified_router

# from app.routes.v2_api import router as v2_router  # Replaced by v2_unified_router
from app.security import SecurityConfig, SecurityManager

# from app.services.service_factory import get_service_factory  # Not needed
from app.session_manager import get_session_manager

# Version info
__version__ = "3.1.0"


# Simple replacements for archived functions
async def get_db_instance():
    """Get database instance"""
    from app.database import get_database

    return await get_database()


async def verify_api_key(api_key: str = Query(..., alias="api_key")):
    """Simple API key verification"""
    if api_key != os.getenv("API_KEY", "test-key"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def get_version_info():
    """Get version information"""
    return {"version": __version__, "api_version": "v1", "python_version": "3.10+"}


# Configure structured logging
log_config = LogConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="json" if os.getenv("ENVIRONMENT", "production") == "production" else "text",
    enable_file=True,
    file_path="logs/second-brain.log",
    enable_performance_logging=True,
    enable_audit_logging=True,
    enable_request_logging=True,
)
configure_logging(log_config)
logger = get_logger(__name__)

# Initialize monitoring
metrics_collector = get_metrics_collector()
health_checker = get_health_checker()
request_tracker = get_request_tracker()


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


# Legacy search request model (keeping for backward compatibility)
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int | None = Field(default=10, ge=1, le=100, description="Maximum results")


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info(
        "Starting Second Brain application",
        version=__version__,
        environment=os.getenv("ENVIRONMENT", "production"),
    )

    # Register custom metrics
    metrics_collector.register_custom_metric(
        MetricDefinition(
            name="memory_searches",
            type=MetricType.COUNTER,
            description="Number of memory searches",
            labels=["query_type"],
        )
    )

    metrics_collector.register_custom_metric(
        MetricDefinition(
            name="operation_duration",
            type=MetricType.HISTOGRAM,
            description="Operation duration in seconds",
            labels=["operation", "status"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
        )
    )

    metrics_collector.register_custom_metric(
        MetricDefinition(
            name="operation_errors",
            type=MetricType.COUNTER,
            description="Number of operation errors",
            labels=["operation", "error_type"],
        )
    )

    # Initialize database - mock database removed, always use real PostgreSQL
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/secondbrain")
    pool_config = PoolConfig(
        min_connections=5, max_connections=20, max_inactive_connection_lifetime=300.0
    )

    try:
        await initialize_pool(database_url, pool_config)
        logger.info(
            "Database connection pool initialized",
            min_connections=pool_config.min_connections,
            max_connections=pool_config.max_connections,
        )

        # Register database health check
        db = await get_database()

        async def check_db():
            return await health_checker.check_database(db)

        health_checker.register_check("database", check_db)
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        # Fallback to regular database connection
        db = await get_database()
        logger.info("Database initialized (fallback mode)")

    # Initialize Redis for caching and rate limiting
    await get_redis_manager()
    redis_client = await get_redis_client()

    if redis_client:
        logger.info("Redis initialized for caching and rate limiting")
        # Register Redis health check
        health_checker.register_check("redis", redis_health_check)
    else:
        logger.warning("Redis not available - rate limiting will be disabled")

    # Service factory initialization removed - services use dependency injection
    logger.info("Service factory initialized")

    yield

    # Cleanup - always cleanup real database
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

    # Cleanup Redis
    try:
        await cleanup_redis()
        logger.info("Redis cleanup complete")
    except Exception as e:
        logger.error(f"Error cleaning up Redis: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI app with custom route class for logging
app = FastAPI(
    title="Second Brain API",
    description="Simple memory storage and search system",
    version=__version__,
    lifespan=lifespan,
    route_class=LoggingRoute,
)

# Setup OpenAPI documentation
setup_openapi_documentation(app)


# Register exception handlers from the new exception handling system
register_exception_handlers(app)


# Setup rate limiting middleware (before other middleware)
async def setup_rate_limiting_if_redis():
    """Setup rate limiting if Redis is available"""
    redis_client = await get_redis_client()
    if redis_client:
        setup_rate_limiting(app, redis_client)
        logger.info("Rate limiting middleware enabled")
    else:
        logger.info("Rate limiting middleware disabled (Redis not available)")


# We'll call this during startup, but need to define it here for later use


# Add request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    # Track request
    response = await request_tracker.track_request(request, call_next)

    # Apply security headers
    SecurityHeadersManager.apply_security_headers(response)

    # Monitor for suspicious activity
    security_monitor = get_security_monitor()
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                activities = security_monitor.detect_suspicious_activity(request, body.decode())
                if activities:
                    await security_monitor.log_security_event(
                        event_type="SUSPICIOUS_ACTIVITY",
                        severity="HIGH",
                        source_ip=request.client.host if request.client else "unknown",
                        details={"activities": activities},
                    )
        except Exception:
            pass  # Don't break request processing

    return response


# Add security middleware
for middleware_class, middleware_kwargs in security_manager.get_security_middleware():
    app.add_middleware(middleware_class, **middleware_kwargs)

# Add CORS middleware with secure configuration
allowed_origins = security_config.allowed_origins or []
if not allowed_origins:
    # Default to localhost for development only
    if os.getenv("ENVIRONMENT", "development") == "development":
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    else:
        # Production requires explicit origins
        allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
)

# Include refactored routers with API version prefix
app.include_router(memory_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(new_session_router, prefix="/api/v1")
app.include_router(visualization_router, prefix="/api/v1")
app.include_router(importance_router, prefix="/api/v1")
app.include_router(relationship_router, prefix="/api/v1")
app.include_router(bulk_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")

# Include insights router
app.include_router(insights_router, prefix="/api/v1")

# Include bulk operations routes

# Include synthesis routes (v2.8.2)
app.include_router(synthesis_router, prefix="/api/v1")

# Include ingestion routes (v2.8.3)
app.include_router(ingestion_router, prefix="/api/v1")

# Include Google Drive routes (v2.8.3)
app.include_router(google_drive_router, prefix="/api/v1")

# Include Dashboard routes (v3.0.0)
app.include_router(dashboard_router)

# Include unified v2 API routes (combines v1 robustness with v2 features)
app.include_router(v2_unified_router)

# Setup conversation monitoring
setup_conversation_monitoring()

# Initialize session management
session_manager = get_session_manager()
logger.info("Session management initialized for persistent context continuity")

# Serve static files for dashboard
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Serve v2 static files
try:
    app.mount("/v2", StaticFiles(directory="app/static/v2", html=True), name="v2")
except Exception as e:
    logger.warning(f"Could not mount v2 static files: {e}")


# Landing page
@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the main landing page"""
    # For now, redirect to v2 interface
    return HTMLResponse(
        content="""
        <html>
        <head>
            <title>Second Brain v3.0.0</title>
            <meta http-equiv="refresh" content="0; url=/v2">
        </head>
        <body>
            <h1>🧠 Second Brain</h1>
            <p>Redirecting to v2 interface... <a href="/v2">Click here if not redirected</a></p>
        </body>
        </html>
        """
    )


# Documentation library
@app.get("/documentation", response_class=HTMLResponse)
async def documentation_library():
    """Serve the documentation library interface"""
    try:
        with open("static/library.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head><title>Documentation Library - Second Brain</title></head>
        <body>
        <h1>📚 Documentation Library</h1>
        <p>Documentation library is initializing... Please check your installation.</p>
        </body>
        </html>
        """
        )


# Serve documentation files
@app.get("/docs/{file_path:path}")
async def serve_doc_file(file_path: str):
    """Serve documentation markdown files"""
    from pathlib import Path

    # Security: prevent directory traversal
    safe_path = Path(file_path).resolve()
    docs_root = Path("docs").resolve()

    # Handle root docs directory files
    if file_path and not file_path.startswith("docs/"):
        # Check if it's a root level file like README.md or CHANGELOG.md
        root_file = Path(file_path).resolve()
        if root_file.exists() and root_file.is_file() and root_file.suffix == ".md":
            try:
                with open(root_file, encoding="utf-8") as f:
                    content = f.read()
                return Response(content=content, media_type="text/markdown")
            except Exception as e:
                logger.error(f"Error reading doc file: {e}")
                raise HTTPException(status_code=404, detail="Documentation file not found")

    # Handle docs directory files
    full_path = docs_root / safe_path

    # Ensure the path is within docs directory
    try:
        full_path.relative_to(docs_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if full_path.exists() and full_path.is_file():
        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()
            return Response(content=content, media_type="text/markdown")
        except Exception as e:
            logger.error(f"Error reading doc file: {e}")
            raise HTTPException(status_code=500, detail="Error reading documentation")
    else:
        raise HTTPException(status_code=404, detail="Documentation file not found")


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


# API Documentation
@app.get("/api", response_class=HTMLResponse)
async def api_documentation():
    """Serve the API documentation page"""
    try:
        with open("static/api-docs.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head>
            <title>API Documentation - Second Brain</title>
        </head>
        <body>
        <h1>📚 API Documentation</h1>
        <p>API documentation is not available. Please check your installation.</p>
        </body>
        </html>
        """
        )


# File Ingestion Dashboard
@app.get("/ingestion", response_class=HTMLResponse)
async def ingestion_dashboard():
    """Serve the file ingestion dashboard"""
    try:
        with open("static/ingestion-dashboard.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head>
            <title>File Ingestion - Second Brain</title>
        </head>
        <body>
        <h1>📁 File Ingestion Dashboard</h1>
        <p>Ingestion dashboard is not available. Please check your installation.</p>
        </body>
        </html>
        """
        )


# Favicon route
@app.get("/favicon.ico")
async def favicon():
    """Redirect favicon.ico requests to the SVG favicon"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/static/favicon.svg")


# Development Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def development_dashboard():
    """Serve the development dashboard"""
    try:
        with open("static/dashboard.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
        <html>
        <head>
            <title>Development Dashboard - Second Brain</title>
        </head>
        <body>
        <h1>📊 Development Dashboard</h1>
        <p>Dashboard is not available. Please check your installation.</p>
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
    return HealthResponse(
        status="healthy", version=version_info["version"], timestamp=datetime.utcnow()
    )


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
                "create_index": not stats["index_ready"]
                and stats["memories_with_embeddings"] >= 1000,
                "index_type": (
                    "HNSW (preferred)"
                    if stats["hnsw_index_exists"]
                    else "IVFFlat (fallback)" if stats["ivf_index_exists"] else "None"
                ),
                "performance_note": (
                    "Index recommended for 1000+ memories"
                    if stats["memories_with_embeddings"] < 1000
                    else "Index should be active for optimal performance"
                ),
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
    request: SearchRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
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
    "/memories/{memory_id}",
    tags=["Memories"],
    summary="Delete Memory",
    description="Delete a specific memory by ID",
)
async def delete_memory(
    memory_id: str, db=Depends(get_db_instance), _: str = Depends(verify_api_key)
):
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
    request: SemanticMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
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
    request: EpisodicMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key),
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

        procedural_metadata = (
            request.procedural_metadata.dict() if request.procedural_metadata else {}
        )

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

        return {
            "security": security_stats,
            "database_pool": pool_health,
            "timestamp": datetime.utcnow(),
        }
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
            "disk_percent": (
                psutil.disk_usage("/").percent if hasattr(psutil.disk_usage("/"), "percent") else 0
            ),
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
            "environment": os.getenv("ENVIRONMENT", "production"),
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

    # Get comprehensive version info
    version_info = get_version_info()
    dashboard_info = {"dashboard_version": "1.0.0", "features": ["memory", "search", "insights"]}

    return {
        "version": version_info["version"],
        "version_string": f"v{version_info['version']}",
        "display_name": "Second Brain v3",
        "codename": "Phoenix",
        "release_date": "2025-07-25",
        "build": "stable",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "git_commit": "latest",
        "build_timestamp": datetime.now().isoformat(),
        "dashboard": dashboard_info,
        "roadmap": {"next_version": "3.1.0", "features": ["enhanced AI", "better search"]},
    }


# Monitoring endpoints
@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics_endpoint():
    """Export Prometheus metrics"""
    return await export_metrics()


@app.get("/health/detailed", tags=["Health"], summary="Detailed Health Check")
async def detailed_health_check():
    """Get detailed health check results"""
    results = await health_checker.run_checks()
    status_code = 200 if results["status"] == "healthy" else 503
    return JSONResponse(content=results, status_code=status_code)


@app.get("/monitoring/summary", tags=["Monitoring"], summary="Monitoring Summary")
async def monitoring_summary():
    """Get monitoring metrics summary"""
    # Collect system metrics
    await metrics_collector.collect_system_metrics()

    # Get summary
    summary = metrics_collector.get_metrics_summary()

    # Add request stats
    if request_tracker.request_history:
        recent_requests = list(request_tracker.request_history)[-100:]
        avg_duration = sum(r["duration_ms"] for r in recent_requests) / len(recent_requests)
        summary["requests"] = {
            "active": request_tracker.active_requests,
            "recent_count": len(recent_requests),
            "average_duration_ms": avg_duration,
        }

    return summary


# Security audit endpoint
@app.get("/security/audit", tags=["Security"], summary="Run Security Audit")
async def run_security_audit(_: str = Depends(verify_api_key)):
    """Run comprehensive security audit"""
    auditor = get_security_auditor()

    # Run audit
    results = await auditor.run_full_audit()

    # Generate report
    report = auditor.generate_audit_report(results)

    return report


# Application is now run from main.py in the root directory
