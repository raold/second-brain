"""
Memory Management API Routes

Handles CRUD operations for memories with cognitive type classification
and advanced search capabilities.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.docs import (
    ContextualSearchRequest, EpisodicMemoryRequest, MemoryRequest,
    MemoryResponse, MemoryType, ProceduralMemoryRequest, SearchRequest,
    SemanticMemoryRequest
)
from app.services.service_factory import get_memory_service
from app.security import SecurityManager, get_security_manager
from app.shared import get_db_instance
# For compatibility with existing code, alias the shared instance
get_database = get_db_instance


def setup_memory_service_factory(db, security_manager):
    """Set up the service factory with database and security manager."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    factory.set_database(db)
    factory.set_security_manager(security_manager)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memories", tags=["Memories"])


# Local API key verification to avoid circular imports
async def verify_api_key(api_key: str = Query(..., alias="api_key")):
    """Verify API key for memory operations."""
    import os
    
    valid_tokens = os.getenv("API_TOKENS", "").split(",")
    valid_tokens = [token.strip() for token in valid_tokens if token.strip()]
    
    if not valid_tokens:
        raise HTTPException(status_code=500, detail="No API tokens configured")
    
    if api_key not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key


def convert_metadata_to_dict(metadata):
    """Convert Pydantic metadata to dict if needed."""
    if metadata is None:
        return None
    if hasattr(metadata, 'dict'):
        return metadata.dict()
    return metadata


@router.post(
    "",
    response_model=MemoryResponse,
    summary="Store Memory",
    description="Store a new memory with optional metadata and cognitive type"
)
async def store_memory(
    request: MemoryRequest,
    request_obj: Request,
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Store a new memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type=request.memory_type,
            semantic_metadata=convert_metadata_to_dict(request.semantic_metadata),
            episodic_metadata=convert_metadata_to_dict(request.episodic_metadata),
            procedural_metadata=convert_metadata_to_dict(request.procedural_metadata),
            importance_score=request.importance_score
        )
        
        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")
        
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memories = await service.search_memories(
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Store a semantic memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type=MemoryType.SEMANTIC,
            semantic_metadata=convert_metadata_to_dict(request.semantic_metadata),
            episodic_metadata=None,
            procedural_metadata=None,
            importance_score=request.importance_score
        )
        
        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")
        
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Store an episodic memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type=MemoryType.EPISODIC,
            semantic_metadata=None,
            episodic_metadata=convert_metadata_to_dict(request.episodic_metadata),
            procedural_metadata=None,
            importance_score=request.importance_score
        )
        
        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")
        
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Store a procedural memory."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memory_id = await service.store_memory(
            content=request.content,
            memory_type=MemoryType.PROCEDURAL,
            semantic_metadata=None,
            episodic_metadata=None,
            procedural_metadata=convert_metadata_to_dict(request.procedural_metadata),
            importance_score=request.importance_score
        )
        
        # Get the stored memory to return full response
        memory = await service.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")
        
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Perform contextual search with advanced filtering."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        
        # Convert string memory types to enums if provided
        memory_types = None
        if request.memory_types:
            memory_types = [str(mt) for mt in request.memory_types]
        
        results = await service.search_memories(
            query=request.query,
            memory_types=memory_types,
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
    db=Depends(get_database),
    _: str = Depends(verify_api_key)
):
    """Get a specific memory by ID."""
    try:
        # Setup service with dependencies
        security_manager = get_security_manager()
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        memory = await service.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return memory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory") 