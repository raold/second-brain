"""
API Request/Response Models
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    """Base memory request model."""
    content: str = Field(..., min_length=1, max_length=10000)
    importance_score: float = Field(default=0.5, ge=0, le=1)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class EpisodicMemoryRequest(MemoryRequest):
    """Episodic memory request."""
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    emotional_valence: Optional[float] = None


class SemanticMemoryRequest(MemoryRequest):
    """Semantic memory request."""
    category: Optional[str] = None
    related_concepts: Optional[List[str]] = None


class ProceduralMemoryRequest(MemoryRequest):
    """Procedural memory request."""
    steps: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filters: Optional[Dict[str, Any]] = None


class ContextualSearchRequest(SearchRequest):
    """Contextual search request."""
    context: Optional[str] = None
    time_range: Optional[Dict[str, datetime]] = None


class MemoryResponse(BaseModel):
    """Memory response model."""
    id: str
    user_id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[MemoryResponse]
    total: int
    limit: int
    offset: int