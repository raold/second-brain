"""
Simple FastAPI application for Second Brain.
Minimal dependencies, direct database access.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.database import get_database
from app.database_mock import MockDatabase
from app.version import get_version_info
from app.docs import setup_openapi_documentation, MemoryResponse, SearchResponse, HealthResponse, StatusResponse, MemoryRequest, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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

    # Initialize database
    db = await get_database()
    logger.info("Database initialized")

    yield

    # Cleanup
    await db.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Second Brain API", description="Simple memory storage and search system", version="2.0.0", lifespan=lifespan
)

# Setup OpenAPI documentation
setup_openapi_documentation(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health", tags=["Health"], summary="Health Check", description="Check system health and version information", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    version_info = get_version_info()
    return HealthResponse(
        status="healthy",
        version=version_info["version"],
        timestamp=datetime.utcnow()
    )


# Database and index status
@app.get("/status", tags=["Health"], summary="System Status", description="Get database and performance metrics", response_model=StatusResponse)
async def get_status(db = Depends(get_db_instance), _: str = Depends(verify_api_key)):
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
            }
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# Store memory
@app.post("/memories", response_model=MemoryResponse, tags=["Memories"], summary="Store Memory", description="Store a new memory with optional metadata")
async def store_memory(request: MemoryRequest, db = Depends(get_db_instance), _: str = Depends(verify_api_key)):
    """Store a new memory."""
    try:
        memory_id = await db.store_memory(request.content, request.metadata)
        memory = await db.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

        return MemoryResponse(**memory)

    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store memory")


# Search memories
@app.post("/memories/search", response_model=list[MemoryResponse], tags=["Search"], summary="Search Memories", description="Semantic search across stored memories")
async def search_memories(
    request: SearchRequest, db = Depends(get_db_instance), _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity."""
    try:
        limit = request.limit or 10
        results = await db.search_memories(request.query, limit)

        return [MemoryResponse(**result) for result in results]

    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to search memories")


# Get memory by ID
@app.get("/memories/{memory_id}", response_model=MemoryResponse, tags=["Memories"], summary="Get Memory", description="Retrieve a specific memory by ID")
async def get_memory(memory_id: str, db = Depends(get_db_instance), _: str = Depends(verify_api_key)):
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
@app.delete("/memories/{memory_id}", tags=["Memories"], summary="Delete Memory", description="Delete a specific memory by ID")
async def delete_memory(memory_id: str, db = Depends(get_db_instance), _: str = Depends(verify_api_key)):
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


# List all memories
@app.get("/memories", response_model=list[MemoryResponse], tags=["Memories"], summary="List All Memories", description="Retrieve all memories with pagination support")
async def list_memories(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db = Depends(get_db_instance),
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
