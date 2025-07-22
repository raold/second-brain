"""
API routes for multi-hop reasoning engine
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import Database, get_database
from app.security import verify_token
from app.services.reasoning_engine import ReasoningEngine, ReasoningType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class ReasoningQueryRequest(BaseModel):
    """Request model for reasoning queries"""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language reasoning query")
    max_hops: int = Field(3, ge=1, le=5, description="Maximum reasoning hops")
    reasoning_type: str | None = Field(None, description="Type of reasoning: causal, temporal, semantic, evolutionary, comparative")
    min_relevance: float = Field(0.5, ge=0.0, le=1.0, description="Minimum relevance threshold")
    beam_width: int | None = Field(None, ge=1, le=20, description="Beam search width")

    class Config:
        schema_extra = {
            "example": {
                "query": "What led to my career change?",
                "max_hops": 3,
                "reasoning_type": "causal",
                "min_relevance": 0.6
            }
        }


class ReasoningNodeResponse(BaseModel):
    """Response model for reasoning nodes"""
    memory_id: str
    content: str
    relevance_score: float
    hop_number: int
    relationship_type: str
    metadata: dict


class ReasoningPathResponse(BaseModel):
    """Response model for reasoning paths"""
    query: str
    nodes: list[ReasoningNodeResponse]
    total_score: float
    reasoning_type: str
    insights: list[str]
    execution_time_ms: float


class PathTraceRequest(BaseModel):
    """Request model for path tracing"""
    start_memory_id: str = Field(..., description="Starting memory ID")
    end_memory_id: str = Field(..., description="Target memory ID")
    max_hops: int = Field(5, ge=1, le=10, description="Maximum hops to explore")


class CausalChainRequest(BaseModel):
    """Request model for causal chain analysis"""
    memory_id: str = Field(..., description="Event memory ID to analyze")
    direction: str = Field("backward", description="Direction: 'backward' for causes, 'forward' for effects")
    max_depth: int = Field(3, ge=1, le=5, description="Maximum causal depth")


@router.post("/query", response_model=list[ReasoningPathResponse])
async def multi_hop_reasoning(
    request: ReasoningQueryRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Execute a multi-hop reasoning query to find connections and insights across memories
    
    This endpoint enables complex questions like:
    - "How did my understanding of Python evolve over time?"
    - "What caused me to change careers?"
    - "What connections exist between my work projects and personal goals?"
    """
    try:
        # Initialize reasoning engine
        engine = ReasoningEngine(db)

        # Convert string reasoning type to enum if provided
        reasoning_type = None
        if request.reasoning_type:
            try:
                reasoning_type = ReasoningType(request.reasoning_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid reasoning type: {request.reasoning_type}"
                )

        # Execute multi-hop query
        paths = await engine.multi_hop_query(
            query=request.query,
            max_hops=request.max_hops,
            reasoning_type=reasoning_type
        )

        # Convert to response format
        response_paths = []
        for path in paths:
            response_paths.append(ReasoningPathResponse(
                query=path.query,
                nodes=[
                    ReasoningNodeResponse(
                        memory_id=node.memory_id,
                        content=node.content,
                        relevance_score=node.relevance_score,
                        hop_number=node.hop_number,
                        relationship_type=node.relationship_type,
                        metadata=node.metadata
                    )
                    for node in path.nodes
                ],
                total_score=path.total_score,
                reasoning_type=path.reasoning_type.value,
                insights=path.insights,
                execution_time_ms=path.execution_time_ms
            ))

        logger.info(f"Reasoning query completed: {request.query} - Found {len(response_paths)} paths")
        return response_paths

    except ValueError as e:
        logger.error(f"Invalid reasoning query parameters: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_REQUEST",
                "message": "Invalid query parameters",
                "details": str(e)
            }
        )
    except TimeoutError:
        logger.error(f"Reasoning query timed out: {request.query}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "TIMEOUT",
                "message": "Query execution timed out",
                "suggestion": "Try reducing max_hops or simplifying the query"
            }
        )
    except Exception as e:
        logger.error(f"Reasoning query failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REASONING_ERROR",
                "message": "Internal reasoning engine error",
                "details": str(e)
            }
        )


@router.post("/trace", response_model=Optional[ReasoningPathResponse])
async def trace_path(
    request: PathTraceRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Trace the reasoning path between two specific memories
    
    Useful for understanding how two seemingly unrelated memories connect
    """
    try:
        engine = ReasoningEngine(db)

        path = await engine.trace_reasoning_path(
            start_memory_id=request.start_memory_id,
            end_memory_id=request.end_memory_id,
            max_hops=request.max_hops
        )

        if not path:
            return None

        return ReasoningPathResponse(
            query=path.query,
            nodes=[
                ReasoningNodeResponse(
                    memory_id=node.memory_id,
                    content=node.content,
                    relevance_score=node.relevance_score,
                    hop_number=node.hop_number,
                    relationship_type=node.relationship_type,
                    metadata=node.metadata
                )
                for node in path.nodes
            ],
            total_score=path.total_score,
            reasoning_type=path.reasoning_type.value,
            insights=path.insights,
            execution_time_ms=path.execution_time_ms
        )

    except Exception as e:
        logger.error(f"Path trace failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/causal", response_model=list[ReasoningPathResponse])
async def find_causal_chains(
    request: CausalChainRequest,
    _: str = Depends(verify_token),
    db: Database = Depends(get_database)
):
    """
    Find causal chains leading to or resulting from a specific event/memory
    
    Helps answer questions like:
    - "What led to this decision?"
    - "What were the consequences of this action?"
    """
    try:
        engine = ReasoningEngine(db)

        paths = await engine.find_causal_chains(
            event_memory_id=request.memory_id,
            direction=request.direction,
            max_depth=request.max_depth
        )

        # Convert to response format
        response_paths = []
        for path in paths:
            response_paths.append(ReasoningPathResponse(
                query=path.query,
                nodes=[
                    ReasoningNodeResponse(
                        memory_id=node.memory_id,
                        content=node.content,
                        relevance_score=node.relevance_score,
                        hop_number=node.hop_number,
                        relationship_type=node.relationship_type,
                        metadata=node.metadata
                    )
                    for node in path.nodes
                ],
                total_score=path.total_score,
                reasoning_type=path.reasoning_type.value,
                insights=path.insights,
                execution_time_ms=path.execution_time_ms
            ))

        return response_paths

    except Exception as e:
        logger.error(f"Causal chain analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_reasoning_types(
    _: str = Depends(verify_token)
):
    """Get available reasoning types and their descriptions"""
    return {
        "types": [
            {
                "value": "causal",
                "name": "Causal Reasoning",
                "description": "Find what caused something or what it led to",
                "example_queries": [
                    "What caused me to change careers?",
                    "What led to this decision?"
                ]
            },
            {
                "value": "temporal",
                "name": "Temporal Reasoning",
                "description": "Understand sequences and time-based relationships",
                "example_queries": [
                    "What happened before/after this event?",
                    "Show me the timeline of this project"
                ]
            },
            {
                "value": "semantic",
                "name": "Semantic Reasoning",
                "description": "Find conceptually related memories",
                "example_queries": [
                    "What else relates to machine learning?",
                    "Find connections to this topic"
                ]
            },
            {
                "value": "evolutionary",
                "name": "Evolutionary Reasoning",
                "description": "Track how concepts evolved over time",
                "example_queries": [
                    "How did my understanding of Python evolve?",
                    "Show me how this idea developed"
                ]
            },
            {
                "value": "comparative",
                "name": "Comparative Reasoning",
                "description": "Compare and contrast different memories",
                "example_queries": [
                    "How does project A compare to project B?",
                    "What's different between these approaches?"
                ]
            }
        ]
    }


@router.get("/examples")
async def get_example_queries(
    _: str = Depends(verify_token)
):
    """Get example reasoning queries to help users get started"""
    return {
        "examples": [
            {
                "category": "Career & Learning",
                "queries": [
                    "How did my programming skills evolve from beginner to now?",
                    "What experiences led me to my current career path?",
                    "Show me connections between my learning goals and actual progress"
                ]
            },
            {
                "category": "Project Analysis",
                "queries": [
                    "What patterns exist across my successful projects?",
                    "Find connections between technical challenges and their solutions",
                    "How do my side projects relate to my main work?"
                ]
            },
            {
                "category": "Personal Growth",
                "queries": [
                    "What events shaped my current perspectives?",
                    "Trace the evolution of my interests over time",
                    "Find patterns in my decision-making process"
                ]
            },
            {
                "category": "Knowledge Connections",
                "queries": [
                    "How do different concepts I've learned connect to each other?",
                    "What unexpected connections exist in my knowledge base?",
                    "Find the path between two seemingly unrelated topics"
                ]
            }
        ]
    }
