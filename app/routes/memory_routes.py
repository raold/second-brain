"""
Memory Management API Routes

Handles CRUD operations for memories with cognitive type classification
and advanced search capabilities.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


from app.utils.logging_config import get_logger
from app.dependencies import get_current_user, get_db_instance
from app.shared import verify_api_key
from app.database import get_database
from app.core.dependencies import get_memory_service
from app.models.api_models import (
    MemoryRequest, SearchRequest, SemanticMemoryRequest, 
    EpisodicMemoryRequest, ProceduralMemoryRequest, ContextualSearchRequest,
    SecondBrainException, ValidationException, NotFoundException, 
    UnauthorizedException, RateLimitExceededException
)
from fastapi import Request
from typing import Optional, Dict, List, Any

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


@router.post(
    "",
    response_model=MemoryResponse,
    summary="Store Memory",
    description="Store a new memory with optional metadata and cognitive type",
)
async def store_memory(
    request: MemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Store a new memory."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type=request.memory_type,
            semantic_metadata=convert_metadata_to_dict(request.semantic_metadata),
            episodic_metadata=convert_metadata_to_dict(request.episodic_metadata),
            procedural_metadata=convert_metadata_to_dict(request.procedural_metadata),
            importance_score=request.importance_score,
            metadata=request.metadata,
        )

        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise SecondBrainException(message="Failed to retrieve stored memory")

        return memory

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise SecondBrainException(message="Failed to store memory")


@router.post(
    "/search",
    response_model=list[MemoryResponse],
    summary="Search Memories",
    description="Semantic search across stored memories",
)
async def search_memories(
    request: SearchRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()
        memories = await service.search_memories(query=request.query, limit=request.limit or 10)
        return memories

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise SecondBrainException(message="Search failed")


@router.post(
    "/semantic",
    response_model=MemoryResponse,
    summary="Store Semantic Memory",
    description="Store a semantic memory (facts, concepts, knowledge)",
)
async def store_semantic_memory(
    request: SemanticMemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Store a semantic memory."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type="semantic",
            semantic_metadata=convert_metadata_to_dict(request.semantic_metadata),
            episodic_metadata=None,
            procedural_metadata=None,
            importance_score=request.importance_score,
        )

        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise SecondBrainException(message="Failed to retrieve stored memory")

        return memory

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Failed to store semantic memory: {e}")
        raise SecondBrainException(message="Failed to store semantic memory")


@router.post(
    "/episodic",
    response_model=MemoryResponse,
    summary="Store Episodic Memory",
    description="Store an episodic memory (experiences, events)",
)
async def store_episodic_memory(
    request: EpisodicMemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Store an episodic memory."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type="episodic",
            semantic_metadata=None,
            episodic_metadata=convert_metadata_to_dict(request.episodic_metadata),
            procedural_metadata=None,
            importance_score=request.importance_score,
        )

        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise SecondBrainException(message="Failed to retrieve stored memory")

        return memory

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Failed to store episodic memory: {e}")
        raise SecondBrainException(message="Failed to store episodic memory")


@router.post(
    "/procedural",
    response_model=MemoryResponse,
    summary="Store Procedural Memory",
    description="Store a procedural memory (how-to, processes, skills)",
)
async def store_procedural_memory(
    request: ProceduralMemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Store a procedural memory."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type="procedural",
            semantic_metadata=None,
            episodic_metadata=None,
            procedural_metadata=convert_metadata_to_dict(request.procedural_metadata),
            importance_score=request.importance_score,
        )

        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise SecondBrainException(message="Failed to retrieve stored memory")

        return memory

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Failed to store procedural memory: {e}")
        raise SecondBrainException(message="Failed to store procedural memory")


@router.post(
    "/search/contextual",
    response_model=list[dict],
    summary="Contextual Search",
    description="Advanced search with cognitive memory type filtering and contextual scoring",
)
async def contextual_search(
    request: ContextualSearchRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Perform contextual search with advanced filtering."""
    # Basic validation
    if not request.content or not request.content.strip():
        raise ValidationException(message="Content cannot be empty")

    # Delegate to service
    try:
        service = get_memory_service()

        # Convert string memory types to enums if provided
        memory_types = None
        if request.memory_types:
            memory_types = [str(mt) for mt in request.memory_types]

        results = await service.search_memories(
            query=request.query,
            memory_types=memory_types,
            importance_threshold=request.importance_threshold,
            limit=request.limit,
        )
        return results

    except ValueError as e:
        raise ValidationException(message=str(e))
    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Contextual search failed: {e}")
        raise SecondBrainException(message="Contextual search failed")


@router.get(
    "/{memory_id}", response_model=MemoryResponse, summary="Get Memory", description="Retrieve a specific memory by ID"
)
async def get_memory(memory_id: str, db=Depends(get_database), _: str = Depends(verify_api_key)):
    """Get a specific memory by ID."""
    try:
        # Setup service with dependencies
        security_manager = get_security_manager()
        service = get_memory_service()
        memory = await service.get_memory(memory_id)

        if not memory:
            raise NotFoundException(resource="Memory", identifier=memory_id)

        return memory

    except SecondBrainException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        raise SecondBrainException(message="Failed to retrieve memory")


@router.get(
    "/stats",
    summary="Get Memory Statistics",
    description="Get statistics about stored memories",
)
async def get_memory_stats(db=Depends(get_database), _: str = Depends(verify_api_key)):
    """Get memory statistics."""
    try:
        # Setup service with dependencies
        security_manager = get_security_manager()
        service = get_memory_service()
        
        # Get total count of memories
        total_memories = await service.get_total_memory_count()
        
        # Get insights count (we'll use the insights service when available)
        total_insights = 0  # Placeholder for now
        
        # Get connections count from relationship service
        total_connections = 0  # Placeholder for now
        
        return {
            "total_memories": total_memories,
            "total_insights": total_insights,
            "total_connections": total_connections,
        }

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise SecondBrainException(message="Failed to get memory stats")
