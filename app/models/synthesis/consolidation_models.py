from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConsolidationStrategy(str, Enum):
    """Consolidation strategies"""
    MERGE = "merge"
    SUMMARIZE = "summarize"
    HIERARCHICAL = "hierarchical"
    TEMPORAL = "temporal"


class ConsolidationRequest(BaseModel):
    memory_ids: List[UUID]
    consolidation_type: str = Field(default="merge")
    preserve_originals: bool = Field(default=True)
    strategy: ConsolidationStrategy = Field(default=ConsolidationStrategy.MERGE)
    options: Dict[str, Any] = Field(default_factory=dict)


class ConsolidationResult(BaseModel):
    id: UUID
    consolidated_content: str
    original_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationStatus(BaseModel):
    status: str
    progress: float = Field(default=0.0, ge=0, le=1)
    message: Optional[str] = None


class ConsolidatedMemory(BaseModel):
    """Represents a consolidated memory"""
    id: UUID
    title: str
    content: str
    original_memory_ids: List[UUID]
    consolidation_strategy: ConsolidationStrategy
    importance_score: float = Field(ge=0, le=1)
    quality_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationCandidate(BaseModel):
    """Candidate memories for consolidation"""
    memory_ids: List[UUID]
    similarity_score: float = Field(ge=0, le=1)
    reason: str
    suggested_strategy: ConsolidationStrategy
    estimated_quality: float = Field(ge=0, le=1)


class ConsolidationPreview(BaseModel):
    """Preview of consolidation result"""
    candidate: ConsolidationCandidate
    preview_content: str
    estimated_reduction: float = Field(ge=0, le=1)
    quality_assessment: Dict[str, Any]


class QualityAssessment(BaseModel):
    """Quality assessment for consolidation"""
    coherence_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    accuracy_score: float = Field(ge=0, le=1)
    overall_score: float = Field(ge=0, le=1)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)