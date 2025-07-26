from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Types of suggestions"""
    CONNECTION = "connection"
    GAP = "gap"
    QUESTION = "question"
    REVIEW = "review"
    MEMORY = "memory"


class Suggestion(BaseModel):
    id: UUID
    title: str
    description: str
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    related_memory_ids: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SuggestionRequest(BaseModel):
    context_memory_ids: List[UUID] = Field(default_factory=list)
    suggestion_type: str = Field(default="related")
    max_suggestions: int = Field(default=10, gt=0)


class SuggestionResult(BaseModel):
    suggestions: List[Suggestion] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectionSuggestion(BaseModel):
    """Suggestion to connect related memories"""
    id: UUID = Field(default_factory=uuid4)
    memory_id_1: UUID
    memory_id_2: UUID
    connection_type: str
    confidence_score: float = Field(ge=0, le=1)
    reason: str
    suggested_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GapSuggestion(BaseModel):
    """Suggestion for knowledge gaps"""
    id: UUID = Field(default_factory=uuid4)
    topic: str
    gap_description: str
    related_memories: List[UUID] = Field(default_factory=list)
    importance_score: float = Field(ge=0, le=1)
    suggested_resources: List[str] = Field(default_factory=list)
    learning_path: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuestionSuggestion(BaseModel):
    """Suggested questions for deeper exploration"""
    id: UUID = Field(default_factory=uuid4)
    question: str
    context: str
    related_memories: List[UUID] = Field(default_factory=list)
    question_type: str  # "clarification", "exploration", "synthesis"
    priority: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewSuggestion(BaseModel):
    """Suggestion to review specific memories"""
    id: UUID = Field(default_factory=uuid4)
    memory_id: UUID
    reason: str
    urgency: float = Field(ge=0, le=1)
    last_reviewed: Optional[datetime] = None
    suggested_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemorySuggestion(BaseModel):
    """Suggestion for new memory creation"""
    id: UUID = Field(default_factory=uuid4)
    title: str
    content_template: str
    memory_type: str
    related_memories: List[UUID] = Field(default_factory=list)
    suggested_tags: List[str] = Field(default_factory=list)
    importance_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SuggestionContext(BaseModel):
    """Context for generating suggestions"""
    user_id: str
    current_memory_ids: List[UUID] = Field(default_factory=list)
    recent_activity: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    time_context: Optional[datetime] = None


class SuggestionBatch(BaseModel):
    """Batch of various suggestions"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    context: SuggestionContext
    connections: List[ConnectionSuggestion] = Field(default_factory=list)
    gaps: List[GapSuggestion] = Field(default_factory=list)
    questions: List[QuestionSuggestion] = Field(default_factory=list)
    reviews: List[ReviewSuggestion] = Field(default_factory=list)
    memories: List[MemorySuggestion] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None