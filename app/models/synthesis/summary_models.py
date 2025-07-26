from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    memory_ids: List[UUID] = Field(default_factory=list)
    summary_type: str = Field(default="concise")
    max_length: Optional[int] = Field(default=500, gt=0)
    user_id: Optional[str] = None
    time_range: Optional[Dict[str, datetime]] = None


class SummaryResult(BaseModel):
    id: UUID
    summary: str
    key_points: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryOptions(BaseModel):
    include_keywords: bool = Field(default=True)
    include_entities: bool = Field(default=True)
    hierarchical: bool = Field(default=False)


class ExecutiveSummary(BaseModel):
    """High-level executive summary of knowledge base"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    title: str
    overview: str
    key_insights: List[str]
    trends: List[Dict[str, Any]]
    recommendations: List[str]
    time_period: Dict[str, datetime]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TopicSummary(BaseModel):
    """Summary for a specific topic"""
    topic: str
    summary: str
    memory_count: int = Field(ge=0)
    key_points: List[str] = Field(default_factory=list)
    related_topics: List[str] = Field(default_factory=list)
    importance_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PeriodSummary(BaseModel):
    """Summary for a specific time period"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    start_date: datetime
    end_date: datetime
    summary: str
    memory_count: int = Field(ge=0)
    topics: List[TopicSummary] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)