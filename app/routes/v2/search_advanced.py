"""
Advanced search router with PostgreSQL pgvector capabilities
Provides vector search, hybrid search, and relationship exploration
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.memory_service_postgres import MemoryServicePostgres
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/search",
    tags=["Advanced Search"],
    responses={
        404: {"description": "Memory not found"},
        503: {"description": "Service unavailable"},
    },
)


# ==================== Models ====================


class VectorSearchRequest(BaseModel):
    """Vector similarity search request"""

    query: str = Field(..., description="Search query for embedding generation")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    generate_embedding: bool = Field(True, description="Generate embedding from query")


class HybridSearchRequest(BaseModel):
    """Hybrid search combining vector and text"""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    vector_weight: float = Field(
        0.5, ge=0.0, le=1.0, description="Weight for vector search (0=text only, 1=vector only)"
    )
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum combined score")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class RelationshipSearchRequest(BaseModel):
    """Search for related memories"""

    memory_id: str = Field(..., description="Source memory ID")
    relationship_type: Optional[str] = Field(None, description="Filter by relationship type")
    min_strength: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relationship strength")
    depth: int = Field(1, ge=1, le=3, description="Depth for graph traversal")
    limit: int = Field(10, ge=1, le=50, description="Maximum results per level")


class SearchResponse(BaseModel):
    """Search result response"""

    results: List[Dict[str, Any]]
    total: int
    search_type: str
    execution_time_ms: float


class KnowledgeGraphResponse(BaseModel):
    """Knowledge graph response"""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    center: str
    depth: int


class DuplicateCheckResponse(BaseModel):
    """Duplicate check response"""

    duplicates: List[Dict[str, Any]]
    total_found: int
    similarity_threshold: float


# ==================== Dependencies ====================


async def get_memory_service() -> MemoryServicePostgres:
    """Get memory service instance"""
    service = MemoryServicePostgres()
    await service.initialize()
    return service


# ==================== Endpoints ====================


@router.post(
    "/vector",
    response_model=SearchResponse,
    summary="Vector similarity search",
    description="Search using vector embeddings for semantic similarity",
)
async def vector_search(
    request: VectorSearchRequest, service: MemoryServicePostgres = Depends(get_memory_service)
):
    """
    Perform vector similarity search using embeddings.

    This uses OpenAI embeddings to find semantically similar memories.
    """
    import time

    start = time.time()

    try:
        results = await service.semantic_search(
            query=request.query, limit=request.limit, min_similarity=request.min_similarity
        )

        execution_time = (time.time() - start) * 1000

        return SearchResponse(
            results=results,
            total=len(results),
            search_type="vector",
            execution_time_ms=execution_time,
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector search temporarily unavailable",
        )


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Hybrid search",
    description="Combine vector and text search for best results",
)
async def hybrid_search(
    request: HybridSearchRequest, service: MemoryServicePostgres = Depends(get_memory_service)
):
    """
    Perform hybrid search combining vector similarity and full-text search.

    Adjustable weighting between semantic (vector) and keyword (text) matching.
    """
    import time

    start = time.time()

    try:
        results = await service.search_memories(
            query=request.query,
            limit=request.limit,
            search_type="hybrid",
            min_score=request.min_score,
            filters=request.filters,
        )

        execution_time = (time.time() - start) * 1000

        return SearchResponse(
            results=results,
            total=len(results),
            search_type="hybrid",
            execution_time_ms=execution_time,
        )
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hybrid search temporarily unavailable",
        )


@router.post(
    "/related",
    response_model=SearchResponse,
    summary="Find related memories",
    description="Find memories related through explicit relationships",
)
async def find_related(
    request: RelationshipSearchRequest, service: MemoryServicePostgres = Depends(get_memory_service)
):
    """
    Find memories related to a given memory through relationships.
    """
    import time

    start = time.time()

    try:
        results = await service.get_related_memories(
            memory_id=request.memory_id,
            relationship_type=request.relationship_type,
            min_strength=request.min_strength,
            limit=request.limit,
        )

        execution_time = (time.time() - start) * 1000

        return SearchResponse(
            results=results,
            total=len(results),
            search_type="relationship",
            execution_time_ms=execution_time,
        )
    except Exception as e:
        logger.error(f"Relationship search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find related memories: {str(e)}",
        )


@router.get(
    "/knowledge-graph/{memory_id}",
    response_model=KnowledgeGraphResponse,
    summary="Build knowledge graph",
    description="Build a knowledge graph around a memory",
)
async def build_knowledge_graph(
    memory_id: str,
    depth: int = Query(2, ge=1, le=3, description="Graph traversal depth"),
    min_strength: float = Query(0.5, ge=0.0, le=1.0, description="Minimum relationship strength"),
    service: MemoryServicePostgres = Depends(get_memory_service),
):
    """
    Build a knowledge graph centered around a specific memory.

    Traverses relationships up to the specified depth.
    """
    try:
        graph = await service.build_knowledge_graph(
            center_memory_id=memory_id, depth=depth, min_strength=min_strength
        )

        return KnowledgeGraphResponse(
            nodes=graph["nodes"], edges=graph["edges"], center=graph["center"], depth=depth
        )
    except Exception as e:
        logger.error(f"Knowledge graph generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build knowledge graph: {str(e)}",
        )


@router.get(
    "/duplicates",
    response_model=DuplicateCheckResponse,
    summary="Find duplicate memories",
    description="Find potentially duplicate memories based on similarity",
)
async def find_duplicates(
    similarity_threshold: float = Query(0.95, ge=0.8, le=1.0, description="Similarity threshold"),
    limit: int = Query(10, ge=1, le=100, description="Maximum pairs to return"),
    service: MemoryServicePostgres = Depends(get_memory_service),
):
    """
    Find duplicate or near-duplicate memories based on embedding similarity.
    """
    try:
        duplicates = await service.find_duplicate_memories(similarity_threshold)

        # Format results
        formatted_duplicates = []
        for memory1_id, memory2_id, similarity in duplicates[:limit]:
            formatted_duplicates.append(
                {"memory1_id": memory1_id, "memory2_id": memory2_id, "similarity": similarity}
            )

        return DuplicateCheckResponse(
            duplicates=formatted_duplicates,
            total_found=len(duplicates),
            similarity_threshold=similarity_threshold,
        )
    except Exception as e:
        logger.error(f"Duplicate detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find duplicates: {str(e)}",
        )


@router.post(
    "/consolidate-duplicates",
    summary="Consolidate duplicate memories",
    description="Automatically consolidate duplicate memories",
)
async def consolidate_duplicates(
    similarity_threshold: float = Query(0.95, ge=0.8, le=1.0, description="Similarity threshold"),
    dry_run: bool = Query(True, description="Perform dry run without changes"),
    service: MemoryServicePostgres = Depends(get_memory_service),
):
    """
    Automatically consolidate duplicate memories into single entries.

    Use dry_run=true to preview what would be consolidated.
    """
    try:
        results = await service.auto_consolidate_duplicates(
            similarity_threshold=similarity_threshold, dry_run=dry_run
        )

        return {
            "found": results["found"],
            "consolidated": results["consolidated"],
            "errors": results["errors"],
            "dry_run": results["dry_run"],
            "message": "Dry run completed" if dry_run else "Consolidation completed",
        }
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consolidate duplicates: {str(e)}",
        )


@router.get(
    "/suggestions",
    summary="Get search suggestions",
    description="Get search suggestions based on history",
)
async def get_search_suggestions(
    prefix: str = Query(..., min_length=2, description="Search prefix"),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
    service: MemoryServicePostgres = Depends(get_memory_service),
):
    """
    Get search suggestions based on previous searches and memory content.
    """
    try:
        # This could be enhanced with actual search history analysis
        # For now, search for memories matching the prefix
        results = await service.keyword_search(prefix, limit=limit)

        suggestions = []
        for memory in results:
            # Extract key phrases from content
            content = memory.get("content", "")
            if len(content) > 50:
                content = content[:50] + "..."
            suggestions.append(content)

        return {"suggestions": suggestions, "prefix": prefix}
    except Exception as e:
        logger.error(f"Suggestions failed: {e}")
        return {"suggestions": [], "prefix": prefix}


@router.post(
    "/reindex", summary="Reindex memories", description="Regenerate embeddings and search indexes"
)
async def reindex_memories(
    batch_size: int = Query(20, ge=1, le=100, description="Batch size for processing"),
    max_memories: int = Query(1000, ge=1, le=10000, description="Maximum memories to process"),
    service: MemoryServicePostgres = Depends(get_memory_service),
):
    """
    Regenerate embeddings for memories that don't have them.

    This is useful after importing memories from other sources.
    """
    try:
        results = await service.generate_embeddings_for_all(
            batch_size=batch_size, max_memories=max_memories
        )

        return {
            "processed": results["processed"],
            "success": results["success"],
            "errors": results["errors"],
            "skipped": results["skipped"],
            "message": f"Reindexing completed: {results['success']}/{results['processed']} successful",
        }
    except Exception as e:
        logger.error(f"Reindexing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reindex memories: {str(e)}",
        )
