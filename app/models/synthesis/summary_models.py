from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


class SummaryType(str, Enum):
    """Types of summaries available"""
    EXECUTIVE = "executive"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    LEARNING = "learning"


class FormatType(str, Enum):
    """Output format types"""
    PLAIN_TEXT = "plain_text"
    STRUCTURED = "structured"
    BULLET_POINTS = "bullet_points"
    NARRATIVE = "narrative"


class SummaryRequest(BaseModel):
    """Request for summary generation"""
    memory_ids: List[UUID] = Field(default_factory=list)
    summary_type: SummaryType = Field(default=SummaryType.DETAILED)
    max_length: Optional[int] = Field(default=500, gt=0)
    format_type: FormatType = Field(default=FormatType.STRUCTURED)
    include_insights: bool = Field(default=True)
    include_references: bool = Field(default=False)
    user_id: Optional[str] = None
    time_range: Optional[Dict[str, datetime]] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class SummarySegment(BaseModel):
    """A segment of the summary"""
    title: str
    content: str
    importance: float = Field(ge=0, le=1)
    memory_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    """Response containing the generated summary"""
    id: UUID = Field(default_factory=uuid4)
    summary_type: SummaryType
    segments: List[SummarySegment] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    domains: List[Any] = Field(default_factory=list)  # KnowledgeDomain objects
    total_memories_processed: int = Field(default=0, ge=0)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryResult(BaseModel):
    """Legacy summary result for compatibility"""
    id: UUID
    summary: str
    key_points: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TopicSummary(BaseModel):
    """Summary of a specific topic"""
    topic_name: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    memory_count: int = Field(ge=0)
    importance_score: float = Field(ge=0, le=1)
    related_topics: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DomainOverview(BaseModel):
    """Overview of a knowledge domain"""
    domain_name: str
    description: str
    topic_summaries: List[TopicSummary] = Field(default_factory=list)
    total_memories: int = Field(ge=0)
    coverage_score: float = Field(ge=0, le=1)
    key_insights: List[str] = Field(default_factory=list)
    growth_metrics: Dict[str, float] = Field(default_factory=dict)


class KeyInsight(BaseModel):
    """Represents a key insight from summarization"""
    insight: str
    confidence: float = Field(ge=0, le=1)
    supporting_memories: List[UUID] = Field(default_factory=list)
    impact_score: float = Field(ge=0, le=1)
    related_insights: List[str] = Field(default_factory=list)