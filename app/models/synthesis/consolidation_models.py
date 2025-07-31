from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConsolidationStrategy(str, Enum):
    """Consolidation strategies"""
    MERGE = "merge"
    SUMMARIZE = "summarize"
    HIERARCHICAL = "hierarchical"
    TEMPORAL = "temporal"


class MergeStrategy(str, Enum):
    """Memory merge strategies"""
    KEEP_NEWEST = "keep_newest"
    KEEP_OLDEST = "keep_oldest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    MERGE_CONTENT = "merge_content"
    CREATE_SUMMARY = "create_summary"
    HIERARCHICAL = "hierarchical"


class ConsolidationRequest(BaseModel):
    memory_ids: list[UUID] | None = None
    similarity_threshold: float = Field(default=0.85, ge=0, le=1)
    auto_merge: bool = Field(default=False)
    merge_strategy: MergeStrategy | None = None
    include_metadata: bool = Field(default=True)
    options: dict[str, Any] = Field(default_factory=dict)


class ConsolidationResult(BaseModel):
    kept_memory_id: UUID | None = None
    removed_memory_ids: list[UUID] = Field(default_factory=list)
    new_content: str | None = None
    merge_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationStatus(BaseModel):
    status: str
    progress: float = Field(default=0.0, ge=0, le=1)
    message: str | None = None


class ConsolidatedMemory(BaseModel):
    """Represents a consolidated memory"""
    id: UUID
    title: str
    content: str
    original_memory_ids: list[UUID]
    consolidation_strategy: ConsolidationStrategy
    importance_score: float = Field(ge=0, le=1)
    quality_score: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationCandidate(BaseModel):
    """Candidate memories for consolidation"""
    memory_ids: list[UUID]
    similarity_score: float = Field(ge=0, le=1)
    reason: str
    suggested_strategy: ConsolidationStrategy
    estimated_quality: float = Field(ge=0, le=1)


class ConsolidationPreview(BaseModel):
    """Preview of consolidation result"""
    candidate: ConsolidationCandidate
    preview_content: str
    estimated_reduction: float = Field(ge=0, le=1)
    quality_assessment: dict[str, Any]


class QualityAssessment(BaseModel):
    """Quality assessment for consolidation"""
    coherence_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    accuracy_score: float = Field(ge=0, le=1)
    overall_score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DuplicateGroup(BaseModel):
    """Group of duplicate or similar memories"""
    memory_ids: list[UUID]
    similarity_score: float = Field(ge=0, le=1)
    duplicate_type: str  # "exact", "near_duplicate", "similar"
    group_summary: str | None = None
    suggested_action: MergeStrategy | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
