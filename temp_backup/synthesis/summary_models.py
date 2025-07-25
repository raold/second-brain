"""
Data models for knowledge summarization feature
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TopicSummary(BaseModel):
    """Summary of knowledge about a specific topic"""
    topic: str
    summary: str = Field(..., min_length=50, max_length=5000)
    key_insights: list[str] = Field(..., min_items=1, max_items=10)
    related_entities: list[dict[str, Any]] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    memory_count: int = Field(..., ge=0)
    time_range: Optional[dict[str, datetime]] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    word_count: int = Field(..., ge=0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PeriodSummary(BaseModel):
    """Summary of knowledge from a time period"""
    start_date: datetime
    end_date: datetime
    period_type: str  # 'daily', 'weekly', 'monthly', 'custom'
    summary: str = Field(..., min_length=50)
    highlights: list[str] = Field(..., min_items=1, max_items=20)
    new_topics: list[str] = Field(default_factory=list)
    new_entities: list[str] = Field(default_factory=list)
    top_memories: list[dict[str, Any]] = Field(default_factory=list, max_items=10)
    statistics: dict[str, int] = Field(default_factory=dict)
    trends: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutiveSummary(BaseModel):
    """High-level executive summary with actionable insights"""
    title: str = Field(..., min_length=5, max_length=200)
    summary: str = Field(..., min_length=100, max_length=5000)
    key_points: list[str] = Field(..., min_items=3, max_items=10)
    action_items: list[str] = Field(default_factory=list, max_items=10)
    questions_raised: list[str] = Field(default_factory=list, max_items=10)
    opportunities: list[str] = Field(default_factory=list, max_items=5)
    risks: list[str] = Field(default_factory=list, max_items=5)
    memory_ids: list[UUID] = Field(..., min_items=1)
    graph_visualization: Optional[dict[str, Any]] = None  # D3.js compatible data
    metrics: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_time_ms: int = Field(..., ge=0)


class SummaryRequest(BaseModel):
    """Request for generating a summary"""
    summary_type: str = Field(..., pattern="^(topic|period|executive|custom)$")
    target: Optional[str] = None  # Topic name for topic summaries
    memory_ids: Optional[list[UUID]] = None  # For executive summaries
    start_date: Optional[datetime] = None  # For period summaries
    end_date: Optional[datetime] = None
    max_memories: int = Field(default=50, ge=1, le=500)
    include_graph: bool = True
    include_metrics: bool = True
    focus_areas: Optional[list[str]] = None
    language: str = Field(default="en", pattern="^[a-z]{2}$")
    style: str = Field(default="professional", pattern="^(professional|casual|technical|academic)$")


class SummaryMetrics(BaseModel):
    """Metrics about a generated summary"""
    summary_id: UUID
    input_memory_count: int
    input_token_count: int
    output_token_count: int
    compression_ratio: float
    generation_time_ms: int
    quality_scores: dict[str, float]  # coherence, completeness, accuracy, etc.
    user_feedback: Optional[dict[str, Any]] = None
