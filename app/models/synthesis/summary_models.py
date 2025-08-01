from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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

    memory_ids: list[UUID] = Field(default_factory=list)
    summary_type: SummaryType = Field(default=SummaryType.DETAILED)
    max_length: int | None = Field(default=500, gt=0)
    format_type: FormatType = Field(default=FormatType.STRUCTURED)
    include_insights: bool = Field(default=True)
    include_references: bool = Field(default=False)
    user_id: str | None = None
    time_range: dict[str, datetime] | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class SummarySegment(BaseModel):
    """A segment of the summary"""

    title: str
    content: str
    importance: float = Field(ge=0, le=1)
    memory_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    """Response containing the generated summary"""

    id: UUID = Field(default_factory=uuid4)
    summary_type: SummaryType
    segments: list[SummarySegment] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    domains: list[Any] = Field(default_factory=list)  # KnowledgeDomain objects
    total_memories_processed: int = Field(default=0, ge=0)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryResult(BaseModel):
    """Legacy summary result for compatibility"""

    id: UUID
    summary: str
    key_points: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicSummary(BaseModel):
    """Summary of a specific topic"""

    topic_name: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    memory_count: int = Field(ge=0)
    importance_score: float = Field(ge=0, le=1)
    related_topics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DomainOverview(BaseModel):
    """Overview of a knowledge domain"""

    domain_name: str
    description: str
    topic_summaries: list[TopicSummary] = Field(default_factory=list)
    total_memories: int = Field(ge=0)
    coverage_score: float = Field(ge=0, le=1)
    key_insights: list[str] = Field(default_factory=list)
    growth_metrics: dict[str, float] = Field(default_factory=dict)


class KeyInsight(BaseModel):
    """Represents a key insight from summarization"""

    insight: str
    confidence: float = Field(ge=0, le=1)
    supporting_memories: list[UUID] = Field(default_factory=list)
    impact_score: float = Field(ge=0, le=1)
    related_insights: list[str] = Field(default_factory=list)
