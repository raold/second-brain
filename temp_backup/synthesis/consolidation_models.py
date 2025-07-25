"""
Data models for memory consolidation feature
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConsolidationStrategy(str, Enum):
    """Strategies for consolidating memories"""
    MERGE_SIMILAR = "merge_similar"          # Merge highly similar content
    CHRONOLOGICAL = "chronological"          # Combine time-ordered sequences
    TOPIC_BASED = "topic_based"              # Group by common topics
    ENTITY_FOCUSED = "entity_focused"        # Consolidate around key entities
    HIERARCHICAL = "hierarchical"            # Create parent-child relationships


class ConsolidationCandidate(BaseModel):
    """A group of memories that could be consolidated"""
    memory_ids: list[UUID] = Field(..., min_items=2)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    common_entities: list[str] = Field(default_factory=list)
    common_topics: list[str] = Field(default_factory=list)
    common_tags: list[str] = Field(default_factory=list)
    reasoning_paths: list[str] = Field(default_factory=list)
    suggested_strategy: ConsolidationStrategy
    estimated_quality: float = Field(..., ge=0.0, le=1.0)
    explanation: str


class ConsolidationRequest(BaseModel):
    """Request to consolidate memories"""
    memory_ids: list[UUID] = Field(..., min_items=2, max_items=50)
    strategy: ConsolidationStrategy = ConsolidationStrategy.MERGE_SIMILAR
    preserve_originals: bool = True
    custom_title: Optional[str] = None
    additional_context: Optional[str] = None
    importance_boost: float = Field(default=0.0, ge=0.0, le=5.0)


class ConsolidationPreview(BaseModel):
    """Preview of what consolidation would produce"""
    original_memories: list[dict[str, Any]]
    consolidated_content: str
    consolidated_title: str
    merged_entities: list[str]
    merged_topics: list[str]
    merged_tags: list[str]
    importance_score: float
    quality_assessment: dict[str, float]
    warnings: list[str] = Field(default_factory=list)
    estimated_token_reduction: int


class ConsolidatedMemory(BaseModel):
    """Result of memory consolidation"""
    id: UUID
    content: str
    title: str
    original_memory_ids: list[UUID]
    consolidation_strategy: ConsolidationStrategy
    entities: list[str]
    topics: list[str]
    tags: list[str]
    importance: float
    metadata: dict[str, Any]
    lineage: dict[str, Any]  # Track how this memory was created
    created_at: datetime
    token_count: int
    quality_score: float
