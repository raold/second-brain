"""
Data models for smart suggestion feature
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Types of suggestions the system can make"""
    RELATED_MEMORY = "related_memory"
    MISSING_CONNECTION = "missing_connection"
    FOLLOW_UP_QUESTION = "follow_up_question"
    KNOWLEDGE_GAP = "knowledge_gap"
    REVIEW_REMINDER = "review_reminder"
    CONSOLIDATION_OPPORTUNITY = "consolidation_opportunity"
    TOPIC_EXPLORATION = "topic_exploration"
    ENTITY_INVESTIGATION = "entity_investigation"
    PATTERN_DISCOVERY = "pattern_discovery"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"


class Suggestion(BaseModel):
    """Base model for all suggestions"""
    id: UUID = Field(default_factory=UUID)
    type: SuggestionType
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=1000)
    reason: str = Field(..., min_length=10, max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority: float = Field(..., ge=0.0, le=1.0)
    action_url: Optional[str] = None
    action_text: str = Field(default="View")
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemorySuggestion(Suggestion):
    """Suggestion to explore a specific memory"""
    memory_id: UUID
    memory_title: str
    memory_preview: str = Field(..., max_length=200)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    connection_paths: list[str] = Field(default_factory=list)
    common_entities: list[str] = Field(default_factory=list)
    common_topics: list[str] = Field(default_factory=list)


class ConnectionSuggestion(Suggestion):
    """Suggestion to create a connection between memories"""
    source_memory_id: UUID
    target_memory_id: UUID
    source_title: str
    target_title: str
    suggested_relationship: str
    supporting_evidence: list[str] = Field(..., min_items=1, max_items=5)
    potential_insights: list[str] = Field(default_factory=list)


class QuestionSuggestion(Suggestion):
    """Follow-up question to explore"""
    question: str
    context_memory_ids: list[UUID] = Field(default_factory=list)
    expected_answer_type: str  # 'factual', 'exploratory', 'analytical', 'creative'
    related_topics: list[str] = Field(default_factory=list)
    exploration_paths: list[dict[str, str]] = Field(default_factory=list)


class GapSuggestion(Suggestion):
    """Knowledge gap that could be filled"""
    gap_type: str  # 'missing_topic', 'incomplete_entity', 'time_gap', 'detail_gap'
    current_coverage: dict[str, Any]
    suggested_coverage: dict[str, Any]
    filling_strategies: list[str] = Field(..., min_items=1)
    related_memories: list[UUID] = Field(default_factory=list)
    external_resources: list[dict[str, str]] = Field(default_factory=list)


class ReviewSuggestion(Suggestion):
    """Memory that should be reviewed"""
    memory_id: UUID
    memory_title: str
    last_accessed: datetime
    review_reason: str  # 'forgetting_curve', 'importance_decay', 'update_needed', 'quality_check'
    suggested_actions: list[str] = Field(..., min_items=1)
    review_interval_days: int = Field(..., ge=1)
    importance_change: Optional[float] = None


class SuggestionContext(BaseModel):
    """Context used to generate suggestions"""
    current_memory_id: Optional[UUID] = None
    recent_memory_ids: list[UUID] = Field(default_factory=list)
    current_topics: list[str] = Field(default_factory=list)
    current_entities: list[str] = Field(default_factory=list)
    user_goals: list[str] = Field(default_factory=list)
    time_of_day: str  # 'morning', 'afternoon', 'evening', 'night'
    activity_level: str  # 'low', 'medium', 'high'
    suggestion_history: list[UUID] = Field(default_factory=list)  # Recently shown suggestions


class SuggestionBatch(BaseModel):
    """Batch of suggestions with metadata"""
    suggestions: list[Suggestion]
    context: SuggestionContext
    total_available: int
    generation_time_ms: int
    algorithm_version: str
    filtering_applied: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
