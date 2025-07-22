"""
API routes for knowledge graph functionality
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import Database, get_database
from app.security import verify_token
from app.services.graph_query_parser import GraphQueryParser, QueryType
from app.services.knowledge_graph_builder import EntityType, KnowledgeGraphBuilder, RelationshipType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


class BuildGraphRequest(BaseModel):
    """Request model for building a knowledge graph"""
    memory_ids: list[str] = Field(..., min_items=1, max_items=1000, description="List of memory IDs to build graph from")
    extract_entities: bool = Field(True, description="Whether to extract entities")
    extract_relationships: bool = Field(True, description="Whether to extract relationships")
    min_confidence: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    include_stats: bool = Field(True, description="Include graph statistics")

    class Config:
        schema_extra = {
            "example": {
                "memory_ids": ["mem_1", "mem_2", "mem_3"],
                "extract_entities": True,
                "extract_relationships": True,
                "min_confidence": 0.7
            }
        }


class GraphResponse(BaseModel):
    """Response model for graph data"""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    stats: dict[str, Any]
    entity_count: int
    relationship_count: int


class EntityGraphRequest(BaseModel):
    """Request model for entity-centered graph"""
    entity_id: str = Field(..., description="Entity ID to center graph on")
    depth: int = Field(2, ge=1, le=5, description="Depth of graph exploration")


class EntitySearchRequest(BaseModel):
    """Request model for entity search"""
    query: str = Field(..., description="Search query for entities")
    entity_types: list[str] | None = Field(None, description="Filter by entity types")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


@router.post("/build", response_model=GraphResponse)
async def build_knowledge_graph(
    request: BuildGraphRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Build a knowledge graph from specified memories

    Extracts entities and relationships to create a visual graph representation
    """
    try:
        builder = KnowledgeGraphBuilder(db)

        graph_data = await builder.build_graph_from_memories(
            memory_ids=request.memory_ids,
            extract_entities=request.extract_entities,
            extract_relationships=request.extract_relationships,
            min_confidence=request.min_confidence
        )

        logger.info(
            f"Built graph with {graph_data['entity_count']} entities "
            f"and {graph_data['relationship_count']} relationships"
        )

        return GraphResponse(**graph_data)

    except ValueError as e:
        logger.error(f"Invalid graph parameters: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_REQUEST",
                "message": "Invalid graph building parameters",
                "details": str(e)
            }
        )
    except MemoryError:
        logger.error("Out of memory while building graph")
        raise HTTPException(
            status_code=507,
            detail={
                "error": "MEMORY_ERROR",
                "message": "Graph too large to process",
                "suggestion": "Try with fewer memories or reduce depth"
            }
        )
    except Exception as e:
        logger.error(f"Failed to build knowledge graph: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "GRAPH_BUILD_ERROR",
                "message": "Failed to build knowledge graph",
                "details": str(e)
            }
        )


@router.get("/memory/{memory_id}", response_model=GraphResponse)
async def get_memory_graph(
    memory_id: str,
    depth: int = Query(2, ge=1, le=5, description="Depth of exploration"),
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Get the knowledge graph for a specific memory and its connections
    """
    try:
        builder = KnowledgeGraphBuilder(db)

        # First, get all related memories through reasoning paths
        # For now, we'll just use the single memory
        memory_ids = [memory_id]

        # TODO: Use reasoning engine to find related memories
        # related_memories = await get_related_memories(memory_id, depth)
        # memory_ids.extend(related_memories)

        graph_data = await builder.build_graph_from_memories(
            memory_ids=memory_ids,
            extract_entities=True,
            extract_relationships=True
        )

        return GraphResponse(**graph_data)

    except Exception as e:
        logger.error(f"Failed to get memory graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entity", response_model=dict[str, Any])
async def get_entity_graph(
    request: EntityGraphRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Get a subgraph centered on a specific entity

    Shows all relationships and connected entities up to the specified depth
    """
    try:
        builder = KnowledgeGraphBuilder(db)

        graph_data = await builder.get_entity_graph(
            entity_id=request.entity_id,
            depth=request.depth
        )

        return graph_data

    except Exception as e:
        logger.error(f"Failed to get entity graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/entities")
async def search_entities(
    request: EntitySearchRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Search for entities by name or type
    """
    try:
        if not db.pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with db.pool.acquire() as conn:
            # Build query
            query = """
                SELECT
                    id, name, entity_type, description,
                    occurrence_count, importance_score, metadata
                FROM entities
                WHERE 1=1
            """
            params = []
            param_count = 0

            # Text search
            if request.query:
                param_count += 1
                query += f" AND (name ILIKE ${param_count} OR description ILIKE ${param_count})"
                params.append(f"%{request.query}%")

            # Entity type filter
            if request.entity_types:
                param_count += 1
                query += f" AND entity_type = ANY(${param_count})"
                params.append(request.entity_types)

            # Order and limit
            query += " ORDER BY importance_score DESC, occurrence_count DESC"
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(request.limit)

            rows = await conn.fetch(query, *params)

            entities = []
            for row in rows:
                entities.append({
                    "id": str(row["id"]),
                    "name": row["name"],
                    "type": row["entity_type"],
                    "description": row["description"],
                    "occurrence_count": row["occurrence_count"],
                    "importance_score": float(row["importance_score"]),
                    "metadata": row["metadata"]
                })

            return {"entities": entities, "count": len(entities)}

    except Exception as e:
        logger.error(f"Entity search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_statistics(
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Get overall knowledge graph statistics
    """
    try:
        if not db.pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with db.pool.acquire() as conn:
            # Get entity stats
            entity_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_entities,
                    COUNT(DISTINCT entity_type) as entity_types,
                    AVG(occurrence_count) as avg_occurrences,
                    MAX(occurrence_count) as max_occurrences,
                    AVG(importance_score) as avg_importance
                FROM entities
            """)

            # Get relationship stats
            rel_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_relationships,
                    COUNT(DISTINCT relationship_type) as relationship_types,
                    AVG(weight) as avg_weight,
                    AVG(confidence) as avg_confidence
                FROM entity_relationships
            """)

            # Get memory relationship stats
            mem_rel_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_memory_relationships,
                    COUNT(DISTINCT relationship_type) as memory_relationship_types
                FROM memory_relationships
            """)

            # Get entity type distribution
            type_dist = await conn.fetch("""
                SELECT entity_type, COUNT(*) as count
                FROM entities
                GROUP BY entity_type
                ORDER BY count DESC
            """)

            return {
                "entities": {
                    "total": entity_stats["total_entities"],
                    "types": entity_stats["entity_types"],
                    "avg_occurrences": float(entity_stats["avg_occurrences"] or 0),
                    "max_occurrences": entity_stats["max_occurrences"] or 0,
                    "avg_importance": float(entity_stats["avg_importance"] or 0)
                },
                "relationships": {
                    "entity_relationships": {
                        "total": rel_stats["total_relationships"],
                        "types": rel_stats["relationship_types"],
                        "avg_weight": float(rel_stats["avg_weight"] or 0),
                        "avg_confidence": float(rel_stats["avg_confidence"] or 0)
                    },
                    "memory_relationships": {
                        "total": mem_rel_stats["total_memory_relationships"],
                        "types": mem_rel_stats["memory_relationship_types"]
                    }
                },
                "entity_type_distribution": {
                    row["entity_type"]: row["count"] for row in type_dist
                }
            }

    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_graph_types(
    _: str = Depends(verify_token)
):
    """
    Get available entity and relationship types
    """
    return {
        "entity_types": [
            {"value": t.value, "name": t.name, "description": f"{t.value.title()} entities"}
            for t in EntityType
        ],
        "relationship_types": [
            {"value": t.value, "name": t.name, "description": t.value.replace("_", " ").title()}
            for t in RelationshipType
        ]
    }


@router.post("/analyze")
async def analyze_graph_patterns(
    memory_ids: list[str],
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Analyze patterns in the knowledge graph

    Identifies clusters, important nodes, and relationship patterns
    """
    try:
        builder = KnowledgeGraphBuilder(db)

        # Build graph
        graph_data = await builder.build_graph_from_memories(
            memory_ids=memory_ids,
            extract_entities=True,
            extract_relationships=True
        )

        nodes = graph_data["nodes"]
        edges = graph_data["edges"]

        # Find most connected entities (hubs)
        degree_counts = {}
        for edge in edges:
            degree_counts[edge["source"]] = degree_counts.get(edge["source"], 0) + 1
            degree_counts[edge["target"]] = degree_counts.get(edge["target"], 0) + 1

        # Get top hubs
        top_hubs = sorted(
            [(node_id, count) for node_id, count in degree_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Find entity names for hubs
        hub_info = []
        node_lookup = {node["id"]: node for node in nodes}
        for node_id, degree in top_hubs:
            if node_id in node_lookup:
                hub_info.append({
                    "entity": node_lookup[node_id]["label"],
                    "type": node_lookup[node_id]["type"],
                    "connections": degree
                })

        # Analyze relationship patterns
        rel_patterns = {}
        for edge in edges:
            rel_type = edge["type"]
            rel_patterns[rel_type] = rel_patterns.get(rel_type, 0) + 1

        return {
            "graph_summary": graph_data["stats"],
            "top_entities": hub_info,
            "relationship_patterns": rel_patterns,
            "insights": {
                "most_connected": hub_info[0] if hub_info else None,
                "dominant_relationship": max(rel_patterns.items(), key=lambda x: x[1])[0] if rel_patterns else None,
                "graph_density": graph_data["stats"]["density"],
                "connected_components": graph_data["stats"]["connected_components"]
            }
        }

    except Exception as e:
        logger.error(f"Graph analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language graph queries"""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query about the graph")
    memory_ids: list[str] | None = Field(None, max_items=100, description="Specific memories to query (optional)")
    max_results: int = Field(20, ge=1, le=100, description="Maximum results to return")

    class Config:
        schema_extra = {
            "example": {
                "query": "Show connections between Python and machine learning",
                "max_results": 20
            }
        }


class NaturalLanguageQueryResponse(BaseModel):
    """Response model for natural language graph queries"""
    query_type: str
    entities_found: list[dict[str, Any]]
    relationships_found: list[dict[str, Any]]
    insights: list[str]
    visualization_data: dict[str, Any] | None = None


@router.post("/query/natural", response_model=NaturalLanguageQueryResponse)
async def natural_language_query(
    request: NaturalLanguageQueryRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Process natural language queries about the knowledge graph

    Examples:
    - "Show connections between Python and machine learning"
    - "What is related to neural networks?"
    - "Find all people connected to MIT"
    """
    try:
        parser = GraphQueryParser()
        builder = KnowledgeGraphBuilder(db)

        # Parse the query
        parsed = parser.parse(request.query)

        # Build or get graph data
        if request.memory_ids:
            graph_data = await builder.build_graph_from_memories(
                memory_ids=request.memory_ids,
                extract_entities=True,
                extract_relationships=True
            )
        else:
            # Get recent memories for graph
            # This is simplified - in production, you'd have a cached graph
            graph_data = {"nodes": [], "edges": []}

        entities_found = []
        relationships_found = []
        insights = []
        visualization_data = None

        # Process based on query type
        if parsed.query_type == QueryType.FIND_CONNECTIONS:
            # Find path between two entities
            if len(parsed.entities) >= 2:
                entity1_name = parsed.entities[0]
                entity2_name = parsed.entities[1]

                # Find matching nodes
                node1 = next((n for n in graph_data["nodes"]
                             if entity1_name.lower() in n["label"].lower()), None)
                node2 = next((n for n in graph_data["nodes"]
                             if entity2_name.lower() in n["label"].lower()), None)

                if node1 and node2:
                    entities_found = [node1, node2]
                    # Find relationships between them
                    for edge in graph_data["edges"]:
                        if ((edge["source"] == node1["id"] and edge["target"] == node2["id"]) or
                            (edge["source"] == node2["id"] and edge["target"] == node1["id"])):
                            relationships_found.append(edge)

                    insights.append(f"Found {len(relationships_found)} direct connections between {node1['label']} and {node2['label']}")

        elif parsed.query_type == QueryType.FIND_RELATED:
            # Find entities related to a given entity
            if parsed.entities:
                entity_name = parsed.entities[0]
                central_node = next((n for n in graph_data["nodes"]
                                   if entity_name.lower() in n["label"].lower()), None)

                if central_node:
                    entities_found.append(central_node)

                    # Find all connected entities
                    connected_ids = set()
                    for edge in graph_data["edges"]:
                        if edge["source"] == central_node["id"]:
                            connected_ids.add(edge["target"])
                            relationships_found.append(edge)
                        elif edge["target"] == central_node["id"]:
                            connected_ids.add(edge["source"])
                            relationships_found.append(edge)

                    # Get connected nodes
                    for node in graph_data["nodes"]:
                        if node["id"] in connected_ids:
                            entities_found.append(node)

                    insights.append(f"Found {len(connected_ids)} entities connected to {central_node['label']}")

        elif parsed.query_type == QueryType.FILTER_BY_TYPE:
            # Filter entities by type
            if parsed.entity_types:
                entity_type = parsed.entity_types[0]
                entities_found = [n for n in graph_data["nodes"]
                                if n["type"] == entity_type]

                insights.append(f"Found {len(entities_found)} entities of type '{entity_type}'")

        elif parsed.query_type == QueryType.ANALYZE_ENTITY:
            # Analyze specific entity
            if parsed.entities:
                entity_name = parsed.entities[0]
                node = next((n for n in graph_data["nodes"]
                           if entity_name.lower() in n["label"].lower()), None)

                if node:
                    entities_found = [node]

                    # Count connections
                    connection_count = sum(1 for e in graph_data["edges"]
                                         if e["source"] == node["id"] or e["target"] == node["id"])

                    insights.append(f"{node['label']} is a {node['type']} with {connection_count} connections")
                    if node.get("metadata"):
                        insights.append(f"Additional info: {node['metadata']}")

        # Prepare visualization data if we have results
        if entities_found or relationships_found:
            # Get all relevant node IDs
            relevant_ids = set([n["id"] for n in entities_found])
            for rel in relationships_found:
                relevant_ids.add(rel["source"])
                relevant_ids.add(rel["target"])

            # Get all relevant nodes
            vis_nodes = [n for n in graph_data["nodes"] if n["id"] in relevant_ids]

            visualization_data = {
                "nodes": vis_nodes,
                "edges": relationships_found
            }

        return NaturalLanguageQueryResponse(
            query_type=parsed.query_type.value,
            entities_found=entities_found[:request.max_results],
            relationships_found=relationships_found[:request.max_results],
            insights=insights,
            visualization_data=visualization_data
        )

    except Exception as e:
        logger.error(f"Natural language query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/examples")
async def get_query_examples(
    _: str = Depends(verify_token)
):
    """Get example natural language queries"""
    parser = GraphQueryParser()
    return parser.get_query_examples()


@router.post("/query/suggest")
async def suggest_queries(
    partial_query: str = Query(..., description="Partial query for suggestions"),
    _: str = Depends(verify_token)
):
    """Get query suggestions based on partial input"""
    parser = GraphQueryParser()
    suggestions = parser.suggest_query(partial_query)
    return {"suggestions": suggestions}
