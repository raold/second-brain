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

from app.database import Database, get_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Pydantic models
class MemoryRequest(BaseModel):
    content: str = Field(..., description="Memory content")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class MemoryResponse(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    similarity: float | None = None


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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "second-brain"}


# Store memory
@app.post("/memories", response_model=MemoryResponse)
async def store_memory(request: MemoryRequest, db: Database = Depends(get_database), _: str = Depends(verify_api_key)):
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
@app.post("/memories/search", response_model=list[MemoryResponse])
async def search_memories(
    request: SearchRequest, db: Database = Depends(get_database), _: str = Depends(verify_api_key)
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
@app.get("/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str, db: Database = Depends(get_database), _: str = Depends(verify_api_key)):
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
@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, db: Database = Depends(get_database), _: str = Depends(verify_api_key)):
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
@app.get("/memories", response_model=list[MemoryResponse])
async def list_memories(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Database = Depends(get_database),
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
