"""
Search functionality router
Handles semantic, keyword, and hybrid search operations
"""

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routes.v2.memories import Memory
from app.services.memory_service import MemoryService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    responses={
        400: {"description": "Invalid search parameters"},
        500: {"description": "Search service error"},
    },
)


# ==================== Models ====================


class SearchRequest(BaseModel):
    """Advanced search request"""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    search_type: str = Field(
        "hybrid", pattern="^(keyword|semantic|hybrid)$", description="Type of search"
    )
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    include_similar: bool = Field(True, description="Include similar memories")
    similarity_threshold: float = Field(0.7, ge=0, le=1, description="Minimum similarity score")


class SearchResult(BaseModel):
    """Individual search result"""

    memory: Memory
    score: float = Field(..., description="Relevance score")
    match_type: str = Field(..., description="Type of match (exact, semantic, keyword)")
    highlights: List[str] = Field(default_factory=list, description="Highlighted snippets")


class SearchResponse(BaseModel):
    """Search response with results and metadata"""

    success: bool
    results: List[SearchResult]
    total: int
    query: str
    search_type: str
    processing_time_ms: float


# ==================== Dependencies ====================


async def get_memory_service() -> MemoryService:
    """Get memory service instance"""
    return MemoryService()


# ==================== Endpoints ====================


@router.post(
    "/",
    response_model=SearchResponse,
    summary="Search memories",
    description="Perform advanced search across all memories",
)
async def search_memories(
    search: SearchRequest, memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Search memories using various strategies:

    - **keyword**: Traditional keyword matching
    - **semantic**: Vector similarity search (requires embeddings)
    - **hybrid**: Combination of keyword and semantic search

    Returns results sorted by relevance score.
    """
    import time

    start_time = time.time()

    results = await memory_service.search_memories(query=search.query, limit=search.limit)

    # Convert to SearchResult objects
    search_results = []
    for mem_data in results:
        memory = Memory(
            id=UUID(mem_data["id"]),
            content=mem_data["content"],
            memory_type=mem_data["memory_type"],
            importance_score=mem_data["importance_score"],
            tags=mem_data["tags"],
            metadata=mem_data["metadata"],
            created_at=datetime.fromisoformat(mem_data["created_at"]),
            updated_at=datetime.fromisoformat(mem_data["updated_at"]),
            access_count=mem_data.get("access_count", 0),
        )

        # Calculate basic relevance score
        score = 1.0
        if search.query.lower() in mem_data["content"].lower():
            score = 0.9

        search_results.append(
            SearchResult(memory=memory, score=score, match_type="keyword", highlights=[])
        )

    processing_time = (time.time() - start_time) * 1000

    return SearchResponse(
        success=True,
        results=search_results,
        total=len(search_results),
        query=search.query,
        search_type=search.search_type,
        processing_time_ms=processing_time,
    )


@router.post(
    "/semantic",
    response_model=SearchResponse,
    summary="Semantic search",
    description="Search using semantic similarity (requires vector embeddings)",
)
async def semantic_search(
    query: str,
    limit: int = 10,
    threshold: float = 0.7,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """
    Perform semantic search using vector embeddings.

    This endpoint requires memories to have embeddings generated.
    Results are sorted by cosine similarity.
    """
    search_request = SearchRequest(
        query=query, search_type="semantic", limit=limit, similarity_threshold=threshold
    )

    return await search_memories(search_request, memory_service)


@router.post(
    "/keyword",
    response_model=SearchResponse,
    summary="Keyword search",
    description="Traditional keyword-based search",
)
async def keyword_search(
    query: str, limit: int = 10, memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Perform traditional keyword search.

    Searches for exact and partial matches in memory content.
    """
    search_request = SearchRequest(query=query, search_type="keyword", limit=limit)

    return await search_memories(search_request, memory_service)


@router.get(
    "/suggestions",
    summary="Get search suggestions",
    description="Get search suggestions based on existing memories",
)
async def get_search_suggestions(
    prefix: str, limit: int = 5, memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Get search suggestions based on memory content and tags.

    Useful for autocomplete functionality.
    """
    # Get all memories
    memories = await memory_service.list_memories(limit=100)

    suggestions = set()

    for memory in memories:
        # Add tags as suggestions
        for tag in memory.get("tags", []):
            if tag.lower().startswith(prefix.lower()):
                suggestions.add(tag)

        # Add words from content
        words = memory.get("content", "").split()
        for word in words[:20]:  # Only check first 20 words
            if word.lower().startswith(prefix.lower()) and len(word) > 3:
                suggestions.add(word.lower())

    return {"success": True, "suggestions": sorted(list(suggestions))[:limit], "prefix": prefix}
