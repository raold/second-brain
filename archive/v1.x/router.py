"""
Simplified router for Second Brain application.
Focuses on core functionality without over-engineering.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from app.auth import verify_token
from app.models import Payload, PayloadType, Priority
from app.storage.storage_handler import get_storage_handler
from app.storage.postgres_client import get_postgres_client
from app.storage.qdrant_client import qdrant_search
from app.utils.logger import logger

router = APIRouter()


@router.post("/ingest")
async def ingest_memory(
    payload: Payload,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """
    Ingest a new memory into the system.
    
    Args:
        payload: The memory payload to store
        background_tasks: FastAPI background tasks
        token: Authentication token
        
    Returns:
        JSON response with memory ID and status
    """
    try:
        # Get storage handler
        storage = await get_storage_handler()
        
        # Store the memory
        memory_id, embedding = await storage.store_memory(
            payload_id=payload.id,
            text_content=payload.data.get("note", ""),
            intent_type=payload.intent or "note",
            priority=payload.priority.value if payload.priority else "normal",
            tags=payload.data.get("tags", []),
            user=payload.data.get("user"),
            metadata=payload.meta or {}
        )
        
        logger.info(f"Memory ingested: {memory_id}")
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "message": "Memory ingested successfully",
            "has_embedding": embedding is not None
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest memory: {str(e)}")


@router.get("/search")
async def search_memories(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    intent_type: Optional[str] = Query(None, description="Filter by intent type"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    token: str = Depends(verify_token)
):
    """
    Search memories using semantic search.
    
    Args:
        query: Search query string
        limit: Number of results to return
        intent_type: Optional intent type filter
        priority: Optional priority filter
        tags: Optional tags filter
        token: Authentication token
        
    Returns:
        JSON response with search results
    """
    try:
        # Get storage handler
        storage = await get_storage_handler()
        
        # Search memories
        results = await storage.search_memories(
            query_text=query,
            limit=limit,
            intent_types=[intent_type] if intent_type else None,
            tags=tags,
            priority=priority
        )
        
        logger.info(f"Search completed: {len(results)} results for query '{query[:50]}...'")
        
        return {
            "status": "success",
            "results": results,
            "total": len(results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: str,
    token: str = Depends(verify_token)
):
    """
    Get a specific memory by ID.
    
    Args:
        memory_id: The memory ID to retrieve
        token: Authentication token
        
    Returns:
        JSON response with memory details
    """
    try:
        # Get storage handler
        storage = await get_storage_handler()
        
        # Get memory
        memory = await storage.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "status": "success",
            "memory": memory
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        System health status
    """
    try:
        # Check PostgreSQL
        postgres_client = await get_postgres_client()
        postgres_health = await postgres_client.health_check()
        
        # Check Qdrant (simplified)
        try:
            qdrant_results = qdrant_search("test", top_k=1)
            qdrant_healthy = True
        except Exception:
            qdrant_healthy = False
        
        # Overall health
        healthy = postgres_health.get("healthy", False) and qdrant_healthy
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "postgres": postgres_health.get("healthy", False),
                "qdrant": qdrant_healthy
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
