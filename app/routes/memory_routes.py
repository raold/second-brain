"""
Memory Management API Routes

Handles CRUD operations for memories with cognitive type classification
and advanced search capabilities.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.docs import (
    ContextualSearchRequest,
    EpisodicMemoryRequest,
    MemoryRequest,
    MemoryResponse,
    MemoryType,
    ProceduralMemoryRequest,
    SearchRequest,
    SemanticMemoryRequest,
)
from app.security import get_security_manager
from app.services.service_factory import get_memory_service
from app.shared import get_db_instance
from app.pagination import PaginationParams, PaginatedResponse
from app.pagination.utils import PaginationHelper, extract_pagination_params

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
    if hasattr(metadata, "dict"):
        return metadata.dict()
    return metadata


@router.get(
    "",
    response_model=PaginatedResponse[MemoryResponse],
    summary="List Memories",
    description="List memories with cursor-based pagination for efficient navigation of large datasets",
)
async def list_memories(
    request_obj: Request,
    db=Depends(get_database),
    _: str = Depends(verify_api_key),
    limit: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    direction: str = Query("forward", regex="^(forward|backward)$", description="Pagination direction"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    memory_type: Optional[MemoryType] = Query(None, description="Filter by memory type"),
    include_total: bool = Query(False, description="Include total count (expensive for large datasets)"),
):
    """List memories with cursor-based pagination."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        setup_memory_service_factory(db, security_manager)
        
        # Extract pagination params
        pagination_params = PaginationParams(
            limit=limit,
            cursor=cursor,
            direction=direction,
            sort_by=sort_by,
            sort_order=sort_order,
            include_total=include_total
        )
        
        # Build base query
        base_query = """
            SELECT 
                id,
                content,
                memory_type,
                created_at,
                updated_at,
                embedding,
                metadata,
                importance_score,
                last_accessed,
                access_count,
                similarity_score
            FROM memories
            WHERE 1=1
        """
        
        query_params = []
        
        # Add memory type filter if specified
        if memory_type:
            base_query += " AND memory_type = %s"
            query_params.append(memory_type.value)
        
        # Count query for total if requested
        count_query = None
        if include_total:
            count_query = "SELECT COUNT(*) FROM memories WHERE 1=1"
            if memory_type:
                count_query += " AND memory_type = %s"
        
        # Use pagination helper
        helper = PaginationHelper()
        
        # Get the base URL for navigation links
        base_url = str(request_obj.url).split('?')[0]
        
        # Paginate the query
        response = await helper.paginate(
            db=db,
            query=base_query,
            params=pagination_params,
            count_query=count_query,
            query_params=query_params,
            base_url=base_url
        )
        
        # Convert raw results to MemoryResponse objects
        memories = []
        for item in response.data:
            # Parse metadata from JSON if stored as string
            if isinstance(item.get('metadata'), str):
                import json
                try:
                    item['metadata'] = json.loads(item['metadata'])
                except:
                    pass
            
            memories.append(MemoryResponse(**item))
        
        # Create final response with typed data
        return PaginatedResponse(
            data=memories,
            pagination=response.pagination
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to list memories")


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
            importance_score=request.importance_score,
            metadata=request.metadata,
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
    response_model=PaginatedResponse[MemoryResponse],
    summary="Search Memories",
    description="Semantic search across stored memories with cursor pagination",
)
async def search_memories(
    request: SearchRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Search memories using vector similarity with pagination."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Delegate to service
    try:
        setup_memory_service_factory(db, security_manager)
        service = get_memory_service()
        
        # For now, use the existing search and wrap in pagination response
        # TODO: Update memory service to support cursor pagination natively
        memories = await service.search_memories(query=request.query, limit=request.limit or 50)
        
        # Create pagination metadata
        from app.pagination.models import PageInfo, PaginationMetadata
        page_info = PageInfo(
            has_next_page=False,  # Simple implementation for now
            has_previous_page=False,
            start_cursor=None,
            end_cursor=None
        )
        
        metadata = PaginationMetadata(
            page_info=page_info,
            page_size=len(memories),
            total_count=len(memories)
        )
        
        return PaginatedResponse(
            data=memories,
            pagination=metadata
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


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
            importance_score=request.importance_score,
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
    description="Store an episodic memory (experiences, events)",
)
async def store_episodic_memory(
    request: EpisodicMemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
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
            importance_score=request.importance_score,
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
    description="Store a procedural memory (how-to, processes, skills)",
)
async def store_procedural_memory(
    request: ProceduralMemoryRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
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
            importance_score=request.importance_score,
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
    response_model=PaginatedResponse[dict],
    summary="Contextual Search",
    description="Advanced search with cognitive memory type filtering and contextual scoring",
)
async def contextual_search(
    request: ContextualSearchRequest, request_obj: Request, db=Depends(get_database), _: str = Depends(verify_api_key)
):
    """Perform contextual search with advanced filtering and pagination."""
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
            limit=request.limit,
        )
        
        # Wrap in pagination response
        from app.pagination.models import PageInfo, PaginationMetadata
        page_info = PageInfo(
            has_next_page=False,
            has_previous_page=False,
            start_cursor=None,
            end_cursor=None
        )
        
        metadata = PaginationMetadata(
            page_info=page_info,
            page_size=len(results),
            total_count=len(results)
        )
        
        return PaginatedResponse(
            data=results,
            pagination=metadata
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Contextual search failed: {e}")
        raise HTTPException(status_code=500, detail="Contextual search failed")


@router.get(
    "/export/stream",
    summary="Stream Export Memories",
    description="Stream all memories in JSON, CSV, or JSONL format for large exports",
    responses={
        200: {
            "description": "Streaming response with memories",
            "content": {
                "application/json": {"description": "JSON array format"},
                "text/csv": {"description": "CSV format"},
                "application/x-ndjson": {"description": "JSON Lines format"}
            }
        }
    }
)
async def stream_export_memories(
    request_obj: Request,
    db=Depends(get_database),
    _: str = Depends(verify_api_key),
    format: str = Query("json", regex="^(json|csv|jsonl)$", description="Export format"),
    memory_type: Optional[MemoryType] = Query(None, description="Filter by memory type"),
    chunk_size: int = Query(100, ge=10, le=1000, description="Chunk size for streaming"),
):
    """Stream export memories for large datasets."""
    # Security validation
    security_manager = get_security_manager()
    if not security_manager.validate_request(request_obj):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        from app.pagination.streaming import StreamingPaginator
        
        # Build query
        query = """
            SELECT 
                id,
                content,
                memory_type,
                created_at,
                updated_at,
                metadata,
                importance_score,
                last_accessed,
                access_count
            FROM memories
            WHERE 1=1
        """
        
        query_params = []
        
        if memory_type:
            query += " AND memory_type = %s"
            query_params.append(memory_type.value)
        
        query += " ORDER BY created_at DESC"
        
        # Create streaming paginator
        paginator = StreamingPaginator(chunk_size=chunk_size)
        
        # Determine media type and filename
        if format == "csv":
            media_type = "text/csv"
            filename = "memories_export.csv"
            generator = paginator.stream_to_csv(db, query, query_params)
        elif format == "jsonl":
            media_type = "application/x-ndjson"
            filename = "memories_export.jsonl"
            
            # Custom JSONL generator
            async def jsonl_generator():
                import json
                async for chunk in paginator.stream_query(db, query, query_params):
                    for item in chunk:
                        yield json.dumps(item, default=str) + "\n"
            
            generator = jsonl_generator()
        else:  # json
            media_type = "application/json"
            filename = "memories_export.json"
            generator = paginator.stream_to_json(db, query, query_params)
        
        # Create streaming response
        return paginator.create_streaming_response(
            generator=generator,
            media_type=media_type,
            filename=filename
        )

    except Exception as e:
        logger.error(f"Failed to stream export memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to export memories")


@router.get(
    "/{memory_id}", response_model=MemoryResponse, summary="Get Memory", description="Retrieve a specific memory by ID"
)
async def get_memory(memory_id: str, db=Depends(get_database), _: str = Depends(verify_api_key)):
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
