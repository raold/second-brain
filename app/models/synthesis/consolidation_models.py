from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


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
    memory_ids: Optional[List[UUID]] = None
    similarity_threshold: float = Field(default=0.85, ge=0, le=1)
    auto_merge: bool = Field(default=False)
    merge_strategy: Optional[MergeStrategy] = None
    include_metadata: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)


class ConsolidationResult(BaseModel):
    kept_memory_id: Optional[UUID] = None
    removed_memory_ids: List[UUID] = Field(default_factory=list)
    new_content: Optional[str] = None
    merge_metadata: Dict[str, Any] = Field(default_factory=dict)
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


class DuplicateGroup(BaseModel):
    """Group of duplicate or similar memories"""
    memory_ids: List[UUID]
    similarity_score: float = Field(ge=0, le=1)
    duplicate_type: str  # "exact", "near_duplicate", "similar"
    group_summary: Optional[str] = None
    suggested_action: Optional[MergeStrategy] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)