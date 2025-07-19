"""
Cross-Memory Relationship API Routes
Provides endpoints for analyzing relationships between different memory types
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.cross_memory_relationships import CrossMemoryRelationshipEngine
from app.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


class RelationshipAnalysisRequest(BaseModel):
    """Request for relationship analysis"""

    memory_ids: Optional[list[str]] = Field(None, description="Specific memory IDs to analyze")
    memory_types: Optional[list[str]] = Field(None, description="Memory types to include")
    min_strength: float = Field(0.3, description="Minimum relationship strength", ge=0.0, le=1.0)
    include_clusters: bool = Field(True, description="Include knowledge cluster analysis")


class RelationshipResponse(BaseModel):
    """Response containing relationship analysis"""

    total_memories: int
    total_relationships: int
    cross_type_patterns: list[dict[str, Any]]
    knowledge_clusters: list[dict[str, Any]]
    network_metrics: dict[str, Any]
    memory_roles: dict[str, list[str]]
    insights: list[str]


@router.post("/analyze")
async def analyze_cross_memory_relationships(request: Optional[RelationshipAnalysisRequest] = None):
    """
    Comprehensive analysis of cross-memory-type relationships
    Identifies patterns, clusters, and network structure in knowledge base
    """
    try:
        database = await get_database()

        # Get memories for analysis
        if request and request.memory_ids:
            # Analyze specific memories
            memories = []
            for memory_id in request.memory_ids:
                memory = await database.get_memory(memory_id)
                if memory:
                    memories.append(memory)
        else:
            # Get all memories or filtered by type
            if hasattr(database, "get_all_memories"):
                memories = await database.get_all_memories()
            else:
                # Fallback for mock database
                memories = []

        if not memories:
            return {
                "status": "no_data",
                "message": "No memories available for relationship analysis",
                "note": "Add memories to see cross-type relationship patterns",
            }

        # Initialize relationship engine
        engine = CrossMemoryRelationshipEngine(database)

        # Perform comprehensive analysis
        analysis = await engine.analyze_memory_relationships(memories)

        return {
            "status": "success",
            "analysis": analysis,
            "summary": {
                "total_memories": analysis.get("total_memories", 0),
                "total_relationships": analysis.get("total_relationships", 0),
                "cross_type_ratio": analysis.get("network_metrics", {}).get("cross_type_ratio", 0),
                "clusters_found": len(analysis.get("knowledge_clusters", [])),
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing cross-memory relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/memory/{memory_id}")
async def get_memory_relationships(memory_id: str):
    """
    Get all relationships for a specific memory
    Shows how this memory connects to others across types
    """
    try:
        database = await get_database()

        # Check if memory exists
        memory = await database.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Get all memories for relationship analysis
        if hasattr(database, "get_all_memories"):
            all_memories = await database.get_all_memories()
        else:
            all_memories = [memory]  # Fallback for limited analysis

        # Initialize relationship engine and analyze
        engine = CrossMemoryRelationshipEngine(database)
        await engine.analyze_memory_relationships(all_memories)

        # Get specific memory relationships
        relationships = await engine.get_memory_relationships(memory_id)

        return {
            "status": "success",
            "memory_relationships": relationships,
            "cross_type_summary": {
                "total_relationships": relationships.get("total_relationships", 0),
                "cross_type_count": relationships.get("cross_type_count", 0),
                "memory_type": relationships.get("memory_type", "unknown"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory relationships for {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Relationship query failed: {str(e)}")


@router.get("/patterns")
async def get_cross_type_patterns():
    """
    Get patterns in cross-memory-type relationships
    Identifies common relationship patterns between memory types
    """
    try:
        database = await get_database()

        # Get all memories for pattern analysis
        if hasattr(database, "get_all_memories"):
            memories = await database.get_all_memories()
        else:
            memories = []

        if not memories:
            return {
                "status": "insufficient_data",
                "message": "Need more memories to detect cross-type patterns",
                "patterns": [],
            }

        # Analyze patterns
        engine = CrossMemoryRelationshipEngine(database)
        analysis = await engine.analyze_memory_relationships(memories)

        patterns = analysis.get("cross_type_patterns", [])

        return {
            "status": "success",
            "patterns": patterns,
            "insights": analysis.get("insights", []),
            "pattern_summary": {
                "total_patterns": len(patterns),
                "most_common": patterns[0] if patterns else None,
                "total_memories_analyzed": len(memories),
            },
        }

    except Exception as e:
        logger.error(f"Error getting cross-type patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@router.get("/clusters")
async def get_knowledge_clusters():
    """
    Get knowledge clusters from relationship analysis
    Identifies groups of related memories across types
    """
    try:
        database = await get_database()

        # Get memories for clustering
        if hasattr(database, "get_all_memories"):
            memories = await database.get_all_memories()
        else:
            memories = []

        if len(memories) < 3:
            return {
                "status": "insufficient_data",
                "message": "Need at least 3 memories for cluster analysis",
                "clusters": [],
            }

        # Perform clustering analysis
        engine = CrossMemoryRelationshipEngine(database)
        analysis = await engine.analyze_memory_relationships(memories)

        clusters = analysis.get("knowledge_clusters", [])

        return {
            "status": "success",
            "clusters": clusters,
            "cluster_summary": {
                "total_clusters": len(clusters),
                "largest_cluster": max(clusters, key=lambda x: x["memory_count"])["memory_count"] if clusters else 0,
                "average_coherence": sum(c["coherence_score"] for c in clusters) / len(clusters) if clusters else 0,
            },
        }

    except Exception as e:
        logger.error(f"Error getting knowledge clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster analysis failed: {str(e)}")


@router.get("/network-metrics")
async def get_network_metrics():
    """
    Get network analysis metrics for the memory relationship graph
    Provides insights into knowledge network structure
    """
    try:
        database = await get_database()

        # Get all memories
        if hasattr(database, "get_all_memories"):
            memories = await database.get_all_memories()
        else:
            memories = []

        if not memories:
            return {"status": "no_data", "message": "No memories available for network analysis", "metrics": {}}

        # Calculate network metrics
        engine = CrossMemoryRelationshipEngine(database)
        analysis = await engine.analyze_memory_relationships(memories)

        metrics = analysis.get("network_metrics", {})

        # Enhanced metrics with interpretations
        enhanced_metrics = {
            **metrics,
            "interpretations": {
                "density": _interpret_density(metrics.get("network_density", 0)),
                "cross_type_ratio": _interpret_cross_type_ratio(metrics.get("cross_type_ratio", 0)),
                "connectivity": _interpret_connectivity(metrics.get("average_degree", 0)),
            },
        }

        return {
            "status": "success",
            "metrics": enhanced_metrics,
            "recommendations": _generate_network_recommendations(metrics),
        }

    except Exception as e:
        logger.error(f"Error getting network metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Network analysis failed: {str(e)}")


@router.get("/memory-roles")
async def get_memory_roles():
    """
    Classify memories by their roles in the relationship network
    Identifies hubs, bridges, specialists, and isolated memories
    """
    try:
        database = await get_database()

        # Get memories for role analysis
        if hasattr(database, "get_all_memories"):
            memories = await database.get_all_memories()
        else:
            memories = []

        if not memories:
            return {"status": "no_data", "message": "No memories available for role analysis", "roles": {}}

        # Analyze memory roles
        engine = CrossMemoryRelationshipEngine(database)
        analysis = await engine.analyze_memory_relationships(memories)

        roles = analysis.get("memory_roles", {})

        # Enhanced role information
        enhanced_roles = {}
        for role, memory_ids in roles.items():
            enhanced_roles[role] = {
                "count": len(memory_ids),
                "memory_ids": memory_ids[:10],  # Top 10 for each role
                "description": _get_role_description(role),
            }

        return {
            "status": "success",
            "roles": enhanced_roles,
            "summary": {
                "total_memories": sum(len(ids) for ids in roles.values()),
                "hub_memories": len(roles.get("hubs", [])),
                "bridge_memories": len(roles.get("bridges", [])),
                "isolated_memories": len(roles.get("isolates", [])),
            },
        }

    except Exception as e:
        logger.error(f"Error getting memory roles: {e}")
        raise HTTPException(status_code=500, detail=f"Role analysis failed: {str(e)}")


@router.post("/find-bridges")
async def find_knowledge_bridges(
    source_type: str = Query(..., description="Source memory type"),
    target_type: str = Query(..., description="Target memory type"),
):
    """
    Find memories that bridge between specific memory types
    Useful for discovering knowledge connections across domains
    """
    try:
        valid_types = ["semantic", "episodic", "procedural"]
        if source_type not in valid_types or target_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Memory types must be one of: {', '.join(valid_types)}")

        database = await get_database()

        # Get all memories
        if hasattr(database, "get_all_memories"):
            memories = await database.get_all_memories()
        else:
            memories = []

        if not memories:
            return {"status": "no_data", "message": "No memories available for bridge analysis", "bridges": []}

        # Find bridge memories
        engine = CrossMemoryRelationshipEngine(database)
        analysis = await engine.analyze_memory_relationships(memories)

        # Filter for bridge relationships between specified types
        bridges = []
        for rel in engine.relationships:
            source_memory = engine.memory_nodes.get(rel.source_id)
            target_memory = engine.memory_nodes.get(rel.target_id)

            if (
                source_memory
                and target_memory
                and source_memory.memory_type == source_type
                and target_memory.memory_type == target_type
                and rel.strength >= 0.4
            ):  # Only strong bridges
                bridges.append(
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "relationship_type": rel.relationship_type.value,
                        "strength": rel.strength,
                        "source_content": source_memory.content[:100] + "...",
                        "target_content": target_memory.content[:100] + "...",
                    }
                )

        # Sort by strength
        bridges.sort(key=lambda x: x["strength"], reverse=True)

        return {
            "status": "success",
            "bridges": bridges[:20],  # Top 20 bridges
            "bridge_summary": {
                "source_type": source_type,
                "target_type": target_type,
                "total_bridges": len(bridges),
                "strongest_bridge": bridges[0] if bridges else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding knowledge bridges: {e}")
        raise HTTPException(status_code=500, detail=f"Bridge analysis failed: {str(e)}")


def _interpret_density(density: float) -> str:
    """Interpret network density value"""
    if density > 0.7:
        return "Very dense - highly interconnected knowledge"
    elif density > 0.4:
        return "Moderately dense - good knowledge connectivity"
    elif density > 0.1:
        return "Sparse - some knowledge gaps exist"
    else:
        return "Very sparse - significant knowledge silos"


def _interpret_cross_type_ratio(ratio: float) -> str:
    """Interpret cross-type relationship ratio"""
    if ratio > 0.5:
        return "High cross-type integration - knowledge domains well connected"
    elif ratio > 0.3:
        return "Moderate cross-type integration - some domain bridging"
    elif ratio > 0.1:
        return "Low cross-type integration - mostly siloed knowledge"
    else:
        return "Very low cross-type integration - isolated knowledge domains"


def _interpret_connectivity(avg_degree: float) -> str:
    """Interpret average connectivity"""
    if avg_degree > 10:
        return "Highly connected - memories have many relationships"
    elif avg_degree > 5:
        return "Well connected - good relationship density"
    elif avg_degree > 2:
        return "Moderately connected - some relationship gaps"
    else:
        return "Poorly connected - many isolated memories"


def _generate_network_recommendations(metrics: dict[str, Any]) -> list[str]:
    """Generate recommendations based on network metrics"""
    recommendations = []

    density = metrics.get("network_density", 0)
    cross_type_ratio = metrics.get("cross_type_ratio", 0)

    if density < 0.2:
        recommendations.append("Consider creating more connections between related memories")

    if cross_type_ratio < 0.2:
        recommendations.append("Add more cross-type relationships to bridge knowledge domains")

    strong_rels = metrics.get("strong_relationships", 0)
    weak_rels = metrics.get("weak_relationships", 0)

    if weak_rels > strong_rels * 2:
        recommendations.append("Focus on strengthening existing weak relationships")

    if not recommendations:
        recommendations.append("Knowledge network is well-structured and connected")

    return recommendations


def _get_role_description(role: str) -> str:
    """Get description for memory role"""
    descriptions = {
        "hubs": "Central memories with many connections - key knowledge nodes",
        "bridges": "Memories connecting different domains - knowledge integrators",
        "specialists": "Focused memories within specific domains - domain experts",
        "isolates": "Disconnected memories - potential integration opportunities",
    }
    return descriptions.get(role, "Unknown role")
