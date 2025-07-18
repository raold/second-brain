"""
Memory Visualization API Routes.
Provides endpoints for interactive memory graphs, advanced search, and relationship analysis.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database
from app.memory_visualization import AdvancedSearchEngine, MemoryVisualizationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualization", tags=["visualization"])


# Request/Response Models
class GraphRequest(BaseModel):
    """Request model for memory graph generation."""

    memory_types: Optional[list[str]] = Field(None, description="Filter by memory types")
    importance_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum importance score")
    time_range_days: Optional[int] = Field(None, gt=0, description="Include memories from last N days")
    max_nodes: Optional[int] = Field(500, gt=0, le=2000, description="Maximum number of nodes")
    include_relationships: bool = Field(True, description="Include similarity relationships")
    cluster_method: str = Field("semantic", pattern="^(kmeans|dbscan|semantic)$", description="Clustering algorithm")


class AdvancedSearchRequest(BaseModel):
    """Request model for advanced search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    search_type: str = Field("hybrid", pattern="^(semantic|temporal|importance|hybrid)$")
    memory_types: Optional[list[str]] = Field(None, description="Filter by memory types")
    importance_range: Optional[list[float]] = Field(None, description="Min/max importance scores [min, max]")
    date_range: Optional[list[str]] = Field(None, description="ISO date strings [start, end]")
    topic_filters: Optional[list[str]] = Field(None, description="Filter by topics/keywords")
    limit: int = Field(50, gt=0, le=200, description="Maximum results")
    include_clusters: bool = Field(True, description="Include cluster analysis")
    include_relationships: bool = Field(True, description="Include relationship analysis")


class GraphResponse(BaseModel):
    """Response model for memory graph."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    clusters: list[dict[str, Any]]
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Response model for advanced search."""

    query: str
    search_type: str
    results: list[dict[str, Any]]
    clusters: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    metadata: dict[str, Any]


# Create async API key verification function
async def verify_api_key_async(api_key: str):
    """Async wrapper for API key verification."""
    import os

    expected_key = os.getenv("API_KEY")
    if not expected_key:
        return True  # No API key required
    return api_key == expected_key


@router.post("/graph", response_model=GraphResponse)
async def generate_memory_graph(
    request: GraphRequest, api_key: str = Query(None, description="API key for authentication")
):
    """
    Generate interactive memory graph with nodes, edges, and clusters.

    Creates a comprehensive visualization of memory relationships based on:
    - Semantic similarity between memories
    - Memory type classifications (semantic, episodic, procedural)
    - Importance scores and temporal patterns
    - Topic clustering and relationship analysis

    Returns graph data suitable for D3.js or similar visualization libraries.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Initialize visualization engine
        db = await get_database()
        viz_engine = MemoryVisualizationEngine(db)

        # Convert importance_range from list to tuple if provided
        importance_threshold = request.importance_threshold

        # Generate graph
        graph_data = await viz_engine.generate_memory_graph(
            memory_types=request.memory_types,
            importance_threshold=importance_threshold,
            time_range_days=request.time_range_days,
            max_nodes=request.max_nodes,
            include_relationships=request.include_relationships,
            cluster_method=request.cluster_method,
        )

        logger.info(f"Generated graph with {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")

        return GraphResponse(**graph_data)

    except Exception as e:
        logger.error(f"Error generating memory graph: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate memory graph: {str(e)}")


@router.get("/graph/quick")
async def generate_quick_graph(
    memory_types: Optional[str] = Query(None, description="Comma-separated memory types"),
    importance_threshold: float = Query(0.3, ge=0.0, le=1.0),
    max_nodes: int = Query(100, gt=0, le=500),
    api_key: str = Query(None, description="API key for authentication"),
):
    """
    Generate a quick memory graph with simplified parameters.
    Useful for dashboard widgets and previews.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Parse memory types
        memory_type_list = memory_types.split(",") if memory_types else None

        # Initialize visualization engine
        db = await get_database()
        viz_engine = MemoryVisualizationEngine(db)

        # Generate simplified graph
        graph_data = await viz_engine.generate_memory_graph(
            memory_types=memory_type_list,
            importance_threshold=importance_threshold,
            max_nodes=max_nodes,
            include_relationships=True,
            cluster_method="semantic",
        )

        # Simplify response for quick rendering
        simplified_data = {
            "nodes": graph_data["nodes"][:max_nodes],
            "edges": graph_data["edges"][:100],  # Limit edges for performance
            "metadata": {
                "node_count": len(graph_data["nodes"]),
                "edge_count": len(graph_data["edges"]),
                "generated_at": graph_data["metadata"]["generated_at"],
            },
        }

        return simplified_data

    except Exception as e:
        logger.error(f"Error generating quick graph: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quick graph: {str(e)}")


@router.post("/search/advanced", response_model=SearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest, api_key: str = Query(None, description="API key for authentication")
):
    """
    Perform advanced multi-dimensional memory search.

    Supports multiple search modes:
    - Semantic: Based on content similarity using embeddings
    - Temporal: Time-based search with date filtering
    - Importance: Weighted by memory importance scores
    - Hybrid: Combines all dimensions for comprehensive results

    Includes clustering analysis and relationship detection.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Initialize search engine
        db = await get_database()
        search_engine = AdvancedSearchEngine(db)

        # Convert list parameters to tuples
        importance_range = tuple(request.importance_range) if request.importance_range else None
        date_range = tuple(request.date_range) if request.date_range else None

        # Perform search
        search_results = await search_engine.advanced_search(
            query=request.query,
            search_type=request.search_type,
            memory_types=request.memory_types,
            importance_range=importance_range,
            date_range=date_range,
            topic_filters=request.topic_filters,
            limit=request.limit,
            include_clusters=request.include_clusters,
            include_relationships=request.include_relationships,
        )

        logger.info(f"Advanced search returned {len(search_results['results'])} results")

        return SearchResponse(**search_results)

    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")


@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, description="Partial search query"),
    limit: int = Query(10, gt=0, le=50),
    api_key: str = Query(None, description="API key for authentication"),
):
    """
    Get search suggestions based on partial query.
    Returns suggested topics, memory types, and related terms.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        db = await get_database()

        # Simple suggestion implementation
        # In a production system, this could be enhanced with proper indexing
        async with db.pool.acquire() as conn:
            # Get memories that contain the query term
            suggestions = await conn.fetch(
                """
                SELECT DISTINCT content, memory_type 
                FROM memories 
                WHERE content ILIKE $1 
                ORDER BY importance_score DESC 
                LIMIT $2
            """,
                f"%{query}%",
                limit,
            )

        # Extract keywords and memory types
        suggested_terms = set()
        memory_types = set()

        for row in suggestions:
            content = row["content"].lower()
            memory_types.add(row["memory_type"])

            # Extract words containing the query
            words = content.split()
            matching_words = [word for word in words if query.lower() in word.lower() and len(word) > 2]
            suggested_terms.update(matching_words[:3])  # Top 3 words per memory

        return {
            "query": query,
            "suggestions": {
                "terms": list(suggested_terms)[:limit],
                "memory_types": list(memory_types),
                "topics": [],  # Could be enhanced with topic extraction
            },
        }

    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/analytics/memory-stats")
async def get_memory_analytics(api_key: str = Query(None, description="API key for authentication")):
    """
    Get comprehensive memory analytics and statistics.
    Provides insights into memory distribution, importance patterns, and relationships.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        db = await get_database()

        async with db.pool.acquire() as conn:
            # Basic memory statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_memories,
                    AVG(importance_score) as avg_importance,
                    MAX(importance_score) as max_importance,
                    MIN(importance_score) as min_importance,
                    COUNT(DISTINCT memory_type) as memory_types_count
                FROM memories
            """)

            # Memory type distribution
            type_distribution = await conn.fetch("""
                SELECT memory_type, COUNT(*) as count
                FROM memories
                GROUP BY memory_type
                ORDER BY count DESC
            """)

            # Temporal distribution (memories per day over last 30 days)
            temporal_stats = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count,
                    AVG(importance_score) as avg_importance
                FROM memories
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)

            # High importance memories
            important_memories = await conn.fetch("""
                SELECT id, content, importance_score, memory_type, created_at
                FROM memories
                WHERE importance_score >= 0.8
                ORDER BY importance_score DESC
                LIMIT 10
            """)

        analytics = {
            "overview": {
                "total_memories": stats["total_memories"],
                "average_importance": float(stats["avg_importance"]) if stats["avg_importance"] else 0,
                "importance_range": {
                    "min": float(stats["min_importance"]) if stats["min_importance"] else 0,
                    "max": float(stats["max_importance"]) if stats["max_importance"] else 0,
                },
                "memory_types_count": stats["memory_types_count"],
            },
            "distribution": {"by_type": {row["memory_type"]: row["count"] for row in type_distribution}},
            "temporal_patterns": [
                {
                    "date": row["date"].isoformat(),
                    "count": row["count"],
                    "avg_importance": float(row["avg_importance"]) if row["avg_importance"] else 0,
                }
                for row in temporal_stats
            ],
            "high_importance_memories": [
                {
                    "id": str(row["id"]),
                    "content_preview": row["content"][:100] + ("..." if len(row["content"]) > 100 else ""),
                    "importance_score": float(row["importance_score"]),
                    "memory_type": row["memory_type"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in important_memories
            ],
        }

        return analytics

    except Exception as e:
        logger.error(f"Error getting memory analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/relationships/{memory_id}")
async def get_memory_relationships(
    memory_id: str,
    limit: int = Query(20, gt=0, le=100),
    similarity_threshold: float = Query(0.5, ge=0.0, le=1.0),
    api_key: str = Query(None, description="API key for authentication"),
):
    """
    Get relationships for a specific memory.
    Returns similar memories and their relationship strengths.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        db = await get_database()

        # Get the target memory
        async with db.pool.acquire() as conn:
            target_memory = await conn.fetchrow(
                """
                SELECT id, content, embedding, memory_type, importance_score
                FROM memories 
                WHERE id = $1
            """,
                memory_id,
            )

            if not target_memory:
                raise HTTPException(status_code=404, detail="Memory not found")

            # Get potential related memories
            related_memories = await conn.fetch(
                """
                SELECT id, content, embedding, memory_type, importance_score, 
                       created_at
                FROM memories 
                WHERE id != $1 AND embedding IS NOT NULL
                ORDER BY importance_score DESC
                LIMIT 100
            """,
                memory_id,
            )

        if not related_memories or not target_memory["embedding"]:
            return {
                "memory_id": memory_id,
                "relationships": [],
                "metadata": {"total_found": 0, "similarity_threshold": similarity_threshold},
            }

        # Calculate relationships using the visualization engine
        viz_engine = MemoryVisualizationEngine(db)

        # Convert embeddings and calculate similarities
        target_embedding = [float(x.strip()) for x in str(target_memory["embedding"]).strip("[]").split(",")]
        relationships = []

        for memory in related_memories:
            if memory["embedding"]:
                memory_embedding = [float(x.strip()) for x in str(memory["embedding"]).strip("[]").split(",")]

                # Calculate cosine similarity
                target_norm = np.linalg.norm(target_embedding)
                memory_norm = np.linalg.norm(memory_embedding)

                if target_norm > 0 and memory_norm > 0:
                    similarity = np.dot(target_embedding, memory_embedding) / (target_norm * memory_norm)

                    if similarity >= similarity_threshold:
                        relationships.append(
                            {
                                "memory_id": str(memory["id"]),
                                "content_preview": memory["content"][:100]
                                + ("..." if len(memory["content"]) > 100 else ""),
                                "memory_type": memory["memory_type"],
                                "importance_score": float(memory["importance_score"]),
                                "similarity": float(similarity),
                                "relationship_type": viz_engine._classify_relationship(
                                    {"memory_type": target_memory["memory_type"]},
                                    {"memory_type": memory["memory_type"]},
                                ),
                                "created_at": memory["created_at"].isoformat(),
                            }
                        )

        # Sort by similarity and limit results
        relationships.sort(key=lambda x: x["similarity"], reverse=True)
        relationships = relationships[:limit]

        return {
            "memory_id": memory_id,
            "target_memory": {
                "content_preview": target_memory["content"][:100]
                + ("..." if len(target_memory["content"]) > 100 else ""),
                "memory_type": target_memory["memory_type"],
                "importance_score": float(target_memory["importance_score"]),
            },
            "relationships": relationships,
            "metadata": {
                "total_found": len(relationships),
                "similarity_threshold": similarity_threshold,
                "max_similarity": max([r["similarity"] for r in relationships], default=0),
                "avg_similarity": np.mean([r["similarity"] for r in relationships]) if relationships else 0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {str(e)}")


@router.get("/clusters")
async def get_memory_clusters(
    cluster_method: str = Query("semantic", pattern="^(kmeans|dbscan|semantic)$"),
    memory_types: Optional[str] = Query(None, description="Comma-separated memory types"),
    min_cluster_size: int = Query(3, gt=1),
    api_key: str = Query(None, description="API key for authentication"),
):
    """
    Get memory clusters using specified clustering algorithm.
    Returns grouped memories with cluster metadata.
    """
    try:
        # Verify API key
        if not await verify_api_key_async(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Parse memory types
        memory_type_list = memory_types.split(",") if memory_types else None

        # Initialize visualization engine and generate clusters
        db = await get_database()
        viz_engine = MemoryVisualizationEngine(db)

        graph_data = await viz_engine.generate_memory_graph(
            memory_types=memory_type_list,
            max_nodes=200,  # Reasonable limit for clustering
            include_relationships=False,  # Focus on clustering
            cluster_method=cluster_method,
        )

        # Filter clusters by minimum size
        filtered_clusters = [cluster for cluster in graph_data["clusters"] if cluster["size"] >= min_cluster_size]

        # Enhance cluster data with member details
        enhanced_clusters = []
        for cluster in filtered_clusters:
            # Get detailed information for cluster members
            member_details = []
            for node in graph_data["nodes"]:
                if node["id"] in cluster["members"]:
                    member_details.append(
                        {
                            "id": node["id"],
                            "content_preview": node["label"],
                            "memory_type": node["memory_type"],
                            "importance_score": node["importance_score"],
                        }
                    )

            enhanced_cluster = {
                **cluster,
                "member_details": member_details,
                "dominant_type": max(
                    set(detail["memory_type"] for detail in member_details),
                    key=lambda x: len([d for d in member_details if d["memory_type"] == x]),
                )
                if member_details
                else "unknown",
                "avg_importance": np.mean([detail["importance_score"] for detail in member_details])
                if member_details
                else 0,
            }
            enhanced_clusters.append(enhanced_cluster)

        return {
            "clusters": enhanced_clusters,
            "metadata": {
                "cluster_method": cluster_method,
                "total_clusters": len(enhanced_clusters),
                "total_memories_clustered": sum(cluster["size"] for cluster in enhanced_clusters),
                "min_cluster_size": min_cluster_size,
                "filters": {"memory_types": memory_type_list},
            },
        }

    except Exception as e:
        logger.error(f"Error getting memory clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get clusters: {str(e)}")


# Health check for visualization services
@router.get("/health")
async def visualization_health():
    """Health check for visualization services."""
    try:
        db = await get_database()
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT COUNT(*) FROM memories LIMIT 1")

        return {
            "status": "healthy",
            "services": {"database": "connected", "visualization_engine": "ready", "search_engine": "ready"},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Visualization health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
