"""
API routes for advanced relationship graph functionality
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.memory_service import MemoryService
from app.ingestion.entity_extractor import EntityExtractor
from app.ingestion.relationship_detector import RelationshipDetector
from app.visualization.relationship_graph import RelationshipGraph
from app.ingestion.models import Entity, Relationship
from app.auth.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graph",
    tags=["graph"],
    responses={404: {"description": "Not found"}}
)


class GraphRequest(BaseModel):
    """Request model for graph building"""
    memory_ids: Optional[List[str]] = Field(None, description="Memory IDs to include")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    min_confidence: float = Field(0.5, description="Minimum confidence threshold")
    max_entities: int = Field(100, description="Maximum entities to include")
    enable_clustering: bool = Field(True, description="Enable community detection")


class PathRequest(BaseModel):
    """Request model for path finding"""
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    max_paths: int = Field(5, description="Maximum number of paths")
    max_length: int = Field(5, description="Maximum path length")


class NeighborhoodRequest(BaseModel):
    """Request model for entity neighborhood"""
    entity_id: str = Field(..., description="Entity ID")
    depth: int = Field(2, description="Neighborhood depth")
    min_confidence: float = Field(0.5, description="Minimum confidence")


@router.post("/build")
async def build_relationship_graph(
    request: GraphRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Build a relationship graph from memories
    """
    try:
        memory_service = MemoryService(db)
        
        # Get memories based on filters
        if request.memory_ids:
            memories = []
            for memory_id in request.memory_ids:
                memory = await memory_service.get_memory(memory_id, current_user.id)
                if memory:
                    memories.append(memory)
        else:
            # Get all memories with optional tag filter
            memories = await memory_service.search_memories(
                user_id=current_user.id,
                tags=request.tags,
                limit=50
            )
        
        if not memories:
            return {
                "status": "no_data",
                "message": "No memories found with specified filters"
            }
        
        # Extract entities and relationships from memories
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories[:request.max_entities]:
            # Extract entities
            entities = entity_extractor.extract_entities(memory.content)
            
            # Extract relationships
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities,
                    min_confidence=request.min_confidence
                )
                
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph
        graph = RelationshipGraph(
            enable_clustering=request.enable_clustering
        )
        
        graph_data = graph.build_graph(
            entities=all_entities,
            relationships=all_relationships,
            min_confidence=request.min_confidence
        )
        
        # Add layout
        layout = graph.compute_layout()
        
        # Export graph data
        export_data = graph.export_to_format("json")
        
        return {
            "status": "success",
            "statistics": graph_data,
            "graph": export_data,
            "layout": {node: list(pos) for node, pos in layout.items()},
            "metadata": {
                "num_memories": len(memories),
                "num_entities": len(all_entities),
                "num_relationships": len(all_relationships)
            }
        }
        
    except Exception as e:
        logger.error(f"Error building relationship graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paths")
async def find_relationship_paths(
    request: PathRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find paths between two entities in the relationship graph
    """
    try:
        # Build graph first (in production, this might be cached)
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=100
        )
        
        # Extract entities and relationships
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories:
            entities = entity_extractor.extract_entities(memory.content)
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph
        graph = RelationshipGraph(enable_pathfinding=True)
        graph.build_graph(entities=all_entities, relationships=all_relationships)
        
        # Find paths
        paths = graph.find_paths(
            source_id=request.source_entity_id,
            target_id=request.target_entity_id,
            max_paths=request.max_paths,
            max_length=request.max_length
        )
        
        return {
            "status": "success",
            "paths": paths,
            "metadata": {
                "source": request.source_entity_id,
                "target": request.target_entity_id,
                "num_paths_found": len(paths)
            }
        }
        
    except Exception as e:
        logger.error(f"Error finding paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neighborhood")
async def get_entity_neighborhood(
    request: NeighborhoodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the neighborhood of an entity
    """
    try:
        # Build graph (in production, this might be cached)
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=100
        )
        
        # Extract entities and relationships
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories:
            entities = entity_extractor.extract_entities(memory.content)
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph
        graph = RelationshipGraph()
        graph.build_graph(entities=all_entities, relationships=all_relationships)
        
        # Get neighborhood
        neighborhood = graph.get_entity_neighborhood(
            entity_id=request.entity_id,
            depth=request.depth,
            min_confidence=request.min_confidence
        )
        
        return {
            "status": "success",
            "neighborhood": neighborhood
        }
        
    except Exception as e:
        logger.error(f"Error getting neighborhood: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centrality")
async def get_central_entities(
    top_n: int = Query(10, description="Number of top entities"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the most central entities in the knowledge graph
    """
    try:
        # Build graph
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=100
        )
        
        # Extract entities and relationships
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories:
            entities = entity_extractor.extract_entities(memory.content)
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph with centrality analysis
        graph = RelationshipGraph(enable_centrality=True)
        graph.build_graph(entities=all_entities, relationships=all_relationships)
        
        # Get centrality metrics
        centrality = graph.compute_centrality_metrics(top_n=top_n)
        
        return {
            "status": "success",
            "centrality_metrics": centrality,
            "metadata": {
                "total_entities": len(all_entities),
                "total_relationships": len(all_relationships)
            }
        }
        
    except Exception as e:
        logger.error(f"Error computing centrality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities")
async def detect_communities(
    algorithm: str = Query("spectral", description="Community detection algorithm"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect communities in the knowledge graph
    """
    try:
        # Build graph
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=100
        )
        
        # Extract entities and relationships
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories:
            entities = entity_extractor.extract_entities(memory.content)
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph with clustering
        graph = RelationshipGraph(enable_clustering=True)
        graph.build_graph(entities=all_entities, relationships=all_relationships)
        
        # Detect communities
        communities = graph.detect_communities(algorithm=algorithm)
        
        return {
            "status": "success",
            "communities": communities,
            "metadata": {
                "algorithm": algorithm,
                "total_entities": len(all_entities),
                "total_relationships": len(all_relationships)
            }
        }
        
    except Exception as e:
        logger.error(f"Error detecting communities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{format}")
async def export_graph(
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the knowledge graph in various formats
    """
    if format not in ["json", "graphml", "gexf"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Use json, graphml, or gexf")
    
    try:
        # Build graph
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=100
        )
        
        # Extract entities and relationships
        entity_extractor = EntityExtractor()
        relationship_detector = RelationshipDetector()
        
        all_entities = []
        all_relationships = []
        
        for memory in memories:
            entities = entity_extractor.extract_entities(memory.content)
            if len(entities) >= 2:
                relationships = relationship_detector.detect_relationships(
                    memory.content,
                    entities
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
        
        # Build graph
        graph = RelationshipGraph()
        graph.build_graph(entities=all_entities, relationships=all_relationships)
        
        # Export
        export_data = graph.export_to_format(format)
        
        return {
            "status": "success",
            "format": format,
            "data": export_data
        }
        
    except Exception as e:
        logger.error(f"Error exporting graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))