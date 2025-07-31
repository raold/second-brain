"""
Memory Management API Routes

Handles CRUD operations for memories with cognitive type classification
and advanced search capabilities.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from app.utils.logging_config import get_logger
from app.dependencies import get_current_user, get_db_instance
from app.shared import verify_api_key
from app.database import get_database
from app.services.service_factory import get_memory_service
from app.models.api_models import (
    MemoryRequest, SearchRequest, SemanticMemoryRequest, 
    EpisodicMemoryRequest, ProceduralMemoryRequest, ContextualSearchRequest,
    SecondBrainException, ValidationException, NotFoundException, 
    UnauthorizedException, RateLimitExceededException
)

class MemoryResponse(BaseModel):
    """Memory response model"""
    id: str
    user_id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

logger = get_logger(__name__)
router = APIRouter(prefix="/memories", tags=["Memories"])


def convert_metadata_to_dict(metadata):
    """Convert Pydantic metadata to dict if needed."""
    if metadata is None:
        return None
    if hasattr(metadata, "dict"):
        return metadata.dict()
    return metadata


@router.get("/test", response_model=Dict[str, str])
async def test_memory_routes():
    """Test endpoint for memory routes"""
    return {"status": "Memory routes working", "service": "memory"}


@router.post("/", response_model=MemoryResponse)
async def create_memory(
    request: MemoryRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Create a new memory"""
    try:
        memory_service = get_memory_service()
        
        # Create memory with service
        memory = await memory_service.create_memory(
            content=request.content,
            importance_score=request.importance_score,
            tags=request.tags
        )
        
        return MemoryResponse(
            id=memory["id"],
            user_id=current_user.get("id", "unknown"),
            content=memory["content"],
            memory_type="general",
            importance_score=memory["importance_score"],
            created_at=memory["created_at"],
            updated_at=memory["created_at"],
            metadata=memory.get("metadata", {}),
            tags=memory.get("tags", [])
        )
        
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Get a specific memory by ID"""
    try:
        memory_service = get_memory_service()
        memory = await memory_service.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return MemoryResponse(
            id=memory["id"],
            user_id=current_user.get("id", "unknown"),
            content=memory["content"],
            memory_type="general",
            importance_score=memory["importance_score"],
            created_at=memory["created_at"],
            updated_at=memory["created_at"],
            metadata=memory.get("metadata", {}),
            tags=memory.get("tags", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@router.get("/", response_model=List[MemoryResponse])
async def list_memories(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """List memories with pagination"""
    try:
        memory_service = get_memory_service()
        memories = await memory_service.get_memories(limit=limit, offset=offset)
        
        return [
            MemoryResponse(
                id=memory["id"],
                user_id=current_user.get("id", "unknown"),
                content=memory["content"],
                memory_type="general",
                importance_score=memory["importance_score"],
                created_at=memory["created_at"],
                updated_at=memory["created_at"],
                metadata=memory.get("metadata", {}),
                tags=memory.get("tags", [])
            )
            for memory in memories
        ]
        
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(e)}")


@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Search memories by content similarity"""
    try:
        memory_service = get_memory_service()
        memories = await memory_service.search_memories(
            query=request.query,
            limit=request.limit
        )
        
        return [
            MemoryResponse(
                id=memory["id"],
                user_id=current_user.get("id", "unknown"),
                content=memory["content"],
                memory_type="general",
                importance_score=memory["importance_score"],
                created_at=memory["created_at"],
                updated_at=memory["created_at"],
                metadata=memory.get("metadata", {}),
                tags=memory.get("tags", [])
            )
            for memory in memories
        ]
        
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.post("/semantic")
async def create_semantic_memory(
    request: SemanticMemoryRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Create a semantic memory (facts, knowledge)"""
    try:
        memory_service = get_memory_service()
        
        memory = await memory_service.create_memory(
            content=request.content,
            importance_score=request.importance_score,
            tags=request.tags + ["semantic"]
        )
        
        return {
            "status": "success",
            "memory_id": memory["id"],
            "type": "semantic",
            "message": "Semantic memory created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create semantic memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create semantic memory: {str(e)}")


@router.post("/episodic")
async def create_episodic_memory(
    request: EpisodicMemoryRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Create an episodic memory (personal experiences)"""
    try:
        memory_service = get_memory_service()
        
        memory = await memory_service.create_memory(
            content=request.content,
            importance_score=request.importance_score,
            tags=request.tags + ["episodic", request.context]
        )
        
        return {
            "status": "success",
            "memory_id": memory["id"],
            "type": "episodic",
            "context": request.context,
            "message": "Episodic memory created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create episodic memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create episodic memory: {str(e)}")


@router.post("/procedural")
async def create_procedural_memory(
    request: ProceduralMemoryRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Create a procedural memory (how-to knowledge)"""
    try:
        memory_service = get_memory_service()
        
        memory = await memory_service.create_memory(
            content=request.content,
            importance_score=request.importance_score,
            tags=request.tags + ["procedural", f"skill:{request.skill}"]
        )
        
        return {
            "status": "success",
            "memory_id": memory["id"],
            "type": "procedural",
            "skill": request.skill,
            "message": "Procedural memory created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create procedural memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create procedural memory: {str(e)}")


@router.post("/contextual-search")
async def contextual_search(
    request: ContextualSearchRequest,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Perform intelligent contextual search"""
    try:
        memory_service = get_memory_service()
        
        # Enhanced search with context
        memories = await memory_service.search_memories(
            query=f"{request.query} {request.context}",
            limit=request.limit
        )
        
        return {
            "status": "success",
            "query": request.query,
            "context": request.context,
            "results": len(memories),
            "memories": [
                {
                    "id": memory["id"],
                    "content": memory["content"][:200] + "..." if len(memory["content"]) > 200 else memory["content"],
                    "similarity_score": memory.get("similarity_score", 0),
                    "tags": memory.get("tags", [])
                }
                for memory in memories
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to perform contextual search: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to perform contextual search: {str(e)}")


# Health check for memory service
@router.get("/health/status")
async def memory_service_health():
    """Health check for memory service"""
    try:
        memory_service = get_memory_service()
        # Try a simple operation to verify service works
        await memory_service.get_memories(limit=1)
        
        return {
            "status": "healthy",
            "service": "memory",
            "timestamp": "2025-07-31T16:00:00Z"
        }
    except Exception as e:
        logger.error(f"Memory service health check failed: {e}")
        return {
            "status": "unhealthy", 
            "service": "memory",
            "error": str(e),
            "timestamp": "2025-07-31T16:00:00Z"
        }