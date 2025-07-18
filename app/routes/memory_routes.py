"""
Memory Routes - Thin route handlers for memory operations.
All business logic is delegated to MemoryService.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from app.docs import (
    MemoryRequest,
    MemoryResponse,
    SearchRequest,
    SemanticMemoryRequest,
    EpisodicMemoryRequest,
    ProceduralMemoryRequest,
    ContextualSearchRequest,
    MemoryType
)
from app.services.service_factory import get_memory_service
from app.security import SecurityManager, get_security_manager
from app.app import get_db_instance, verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memories", tags=["Memories"])


@router.post(
    "",
    response_model=MemoryResponse,
    summary="Store Memory",
    description="Store a new memory with optional metadata and cognitive type"
)
async def store_memory(
    request: MemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Store a new memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        memory = await memory_service.store_memory(
            content=request.content,
            memory_type=request.memory_type,
            semantic_metadata=request.semantic_metadata,
            episodic_metadata=request.episodic_metadata,
            procedural_metadata=request.procedural_metadata,
            importance_score=request.importance_score,
            metadata=request.metadata
        )
        return memory
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store memory")


@router.post(
    "/search",
    response_model=List[MemoryResponse],
    summary="Search Memories",
    description="Semantic search across stored memories"
)
async def search_memories(
    request: SearchRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        memories = await memory_service.search_memories(
            query=request.query,
            limit=request.limit or 10
        )
        return memories
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.post(
    "/semantic",
    response_model=MemoryResponse,
    summary="Store Semantic Memory",
    description="Store a semantic memory (facts, concepts, knowledge)"
)
async def store_semantic_memory(
    request: SemanticMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Store a semantic memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        memory = await memory_service.store_memory(
            content=request.content,
            memory_type=MemoryType.SEMANTIC,
            semantic_metadata=request.semantic_metadata,
            importance_score=request.importance_score
        )
        return memory
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store semantic memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store semantic memory")


@router.post(
    "/episodic",
    response_model=MemoryResponse,
    summary="Store Episodic Memory",
    description="Store an episodic memory (experiences, events)"
)
async def store_episodic_memory(
    request: EpisodicMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Store an episodic memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        memory = await memory_service.store_memory(
            content=request.content,
            memory_type=MemoryType.EPISODIC,
            episodic_metadata=request.episodic_metadata,
            importance_score=request.importance_score
        )
        return memory
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store episodic memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store episodic memory")


@router.post(
    "/procedural",
    response_model=MemoryResponse,
    summary="Store Procedural Memory",
    description="Store a procedural memory (how-to, processes, skills)"
)
async def store_procedural_memory(
    request: ProceduralMemoryRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Store a procedural memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        memory = await memory_service.store_memory(
            content=request.content,
            memory_type=MemoryType.PROCEDURAL,
            procedural_metadata=request.procedural_metadata,
            importance_score=request.importance_score
        )
        return memory
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store procedural memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to store procedural memory")


@router.post(
    "/search/contextual",
    response_model=List[dict],
    summary="Contextual Search",
    description="Advanced search with cognitive memory type filtering and contextual scoring"
)
async def contextual_search(
    request: ContextualSearchRequest,
    request_obj: Request,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Perform contextual search with advanced filtering."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        memory_service = get_memory_service()
        
        # Convert string memory types to enums if provided
        memory_types = None
        if request.memory_types:
            memory_types = [MemoryType(mt) for mt in request.memory_types]
        
        results = await memory_service.contextual_search(
            query=request.query,
            memory_types=memory_types,
            temporal_filter=request.temporal_filter,
            importance_threshold=request.importance_threshold,
            limit=request.limit
        )
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Contextual search failed: {e}")
        raise HTTPException(status_code=500, detail="Contextual search failed")


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get Memory",
    description="Retrieve a specific memory by ID"
)
async def get_memory(
    memory_id: str,
    db=Depends(get_db_instance),
    _: str = Depends(verify_api_key)
):
    """Get a specific memory by ID."""
    try:
        memory_service = get_memory_service()
        memory = await memory_service.get_memory_by_id(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return memory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory") 