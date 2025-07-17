"""
Simple FastAPI application for Second Brain.
Minimal dependencies, direct database access.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
import time

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from pydantic import BaseModel, Field

from app.database import get_database
from app.database_mock import MockDatabase
from app.docs import (
    HealthResponse,
    MemoryRequest,
    MemoryResponse,
    StatusResponse,
    setup_openapi_documentation,
)
from app.version import get_version_info
from app.security import SecurityManager, SecurityConfig, get_security_manager
from app.connection_pool import initialize_pool, close_pool, get_pool_manager, PoolConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Global mock database instance for testing
_mock_db_instance = None

# Security configuration
security_config = SecurityConfig(
    max_requests_per_minute=100,  # Increased for better UX
    max_requests_per_hour=5000,
    max_content_length=50000,  # 50KB for larger memories
    enable_rate_limiting=True,
    enable_input_validation=True,
    enable_security_headers=True
)

# Initialize security manager
security_manager = SecurityManager(security_config)


# Global mock database instance for testing
_mock_db_instance = None


# Database dependency with mock support
async def get_db_instance():
    """Get database instance, using mock if configured."""
    global _mock_db_instance

    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        if _mock_db_instance is None:
            logger.info("Creating mock database instance for testing")
            _mock_db_instance = MockDatabase()
            await _mock_db_instance.initialize()
        return _mock_db_instance
    else:
        return await get_database()


# Legacy search request model (keeping for backward compatibility)
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int | None = Field(default=10, ge=1, le=100, description="Maximum results")


# Authentication
async def verify_api_key(api_key: str = Query(..., alias="api_key")):
    """Simple API key authentication."""
    # Allow bypassing authentication in test mode
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        valid_tokens = ["test-key-1", "test-key-2"]
    else:
        valid_tokens = os.getenv("API_TOKENS", "").split(",")
        valid_tokens = [token.strip() for token in valid_tokens if token.strip()]

    if not valid_tokens or api_key not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Starting Second Brain application")

    # Initialize database connection pool
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/secondbrain")
    pool_config = PoolConfig(
        min_connections=5,
        max_connections=20,
        max_inactive_connection_lifetime=300.0
    )
    
    try:
        await initialize_pool(database_url, pool_config)
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        # Fallback to regular database connection
        db = await get_database()
        logger.info("Database initialized (fallback mode)")

    yield

    # Cleanup
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
app = FastAPI(
    title="Second Brain API", description="Simple memory storage and search system", version="2.0.0", lifespan=lifespan
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
                "method": request.method
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed information."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation Error",
                "type": "ValidationError",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.errors()
            }
        }
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
                "error_id": error_id
            }
        }
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


# Store memory
@app.post(
    "/memories",
    response_model=MemoryResponse,
    tags=["Memories"],
    summary="Store Memory",
    description="Store a new memory with optional metadata",
)
async def store_memory(request: MemoryRequest, request_obj: Request, db=Depends(get_db_instance), _: str = Depends(verify_api_key)):
    """Store a new memory."""
    try:
        # Security validation
        if not security_manager.validate_request(request_obj):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Input validation
        validator = security_manager.input_validator
        validated_content = validator.validate_memory_content(request.content)
        validated_metadata = validator.validate_metadata(request.metadata or {})
        
        memory_id = await db.store_memory(validated_content, validated_metadata)
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

        return MemoryResponse(**memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store memory")


# Search memories
@app.post(
    "/memories/search",
    response_model=list[MemoryResponse],
    tags=["Search"],
    summary="Search Memories",
    description="Semantic search across stored memories",
)
async def search_memories(request: SearchRequest, request_obj: Request, db=Depends(get_db_instance), _: str = Depends(verify_api_key)):
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
    try:
        limit = request.limit or 10
        results = await db.search_memories(request.query, limit)

        return [MemoryResponse(**result) for result in results]

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
            "timestamp": datetime.utcnow()
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
        import psutil
        import time
        
        # System metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used // 1024 // 1024,
            "memory_available_mb": psutil.virtual_memory().available // 1024 // 1024,
            "disk_percent": psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0,
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
            "environment": "test" if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true" else "production"
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics,
            "security": security_stats,
            "database": pool_health,
            "application": app_metrics,
            "uptime_formatted": f"{system_metrics['uptime_seconds'] // 3600:.0f}h {(system_metrics['uptime_seconds'] % 3600) // 60:.0f}m"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
