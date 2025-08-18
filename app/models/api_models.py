"""
API Request/Response Models
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    """Base memory request model."""

    content: str = Field(..., min_length=1, max_length=10000)
    importance_score: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class EpisodicMemoryRequest(MemoryRequest):
    """Episodic memory request."""

    location: str | None = None
    participants: list[str] | None = None
    emotional_valence: float | None = None


class SemanticMemoryRequest(MemoryRequest):
    """Semantic memory request."""

    category: str | None = None
    related_concepts: list[str] | None = None


class ProceduralMemoryRequest(MemoryRequest):
    """Procedural memory request."""

    steps: list[str] | None = None
    prerequisites: list[str] | None = None


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filters: dict[str, Any] | None = None


class ContextualSearchRequest(SearchRequest):
    """Contextual search request."""

    context: str | None = None
    time_range: dict[str, datetime] | None = None


class MemoryResponse(BaseModel):
    """Memory response model."""

    id: str
    user_id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: datetime
    updated_at: datetime
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    """Search response model."""

    results: list[MemoryResponse]
    total: int
    limit: int
    offset: int
