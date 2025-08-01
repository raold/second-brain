from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.synthesis.suggestion_models import SuggestionType


class SuggestionType(str, Enum):
    """Types of suggestions"""

    EXPLORE = "explore"
    CONNECT = "connect"
    REVIEW = "review"
    ORGANIZE = "organize"
    CONSOLIDATE = "consolidate"
    SYNTHESIZE = "synthesize"

    # Legacy aliases
    CONNECTION = "connection"
    GAP = "gap"
    QUESTION = "question"
    MEMORY = "memory"


class ActionType(str, Enum):
    """Types of actions for suggestions"""

    CREATE = "create"
    LINK = "link"
    REVIEW = "review"
    TAG = "tag"
    CONSOLIDATE = "consolidate"
    SYNTHESIZE = "synthesize"


class Suggestion(BaseModel):
    """Individual suggestion"""

    id: str
    type: SuggestionType
    title: str
    description: str
    action: ActionType
    priority: float = Field(default=0.5, ge=0, le=1)
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    related_memory_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningPathSuggestion(BaseModel):
    """Suggested learning path"""

    path_name: str
    description: str
    steps: list[str]
    estimated_duration_days: int
    difficulty_level: str  # "beginner", "intermediate", "advanced"
    prerequisites: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    resources: list[dict[str, str]] = Field(default_factory=list)


class ContentSuggestion(BaseModel):
    """Suggested content to create"""

    content_type: str  # "synthesis", "deep_dive", "reflection"
    topic: str
    rationale: str
    prompts: list[str]
    estimated_value: float = Field(ge=0, le=1)
    related_memories: list[UUID] = Field(default_factory=list)


class OrganizationSuggestion(BaseModel):
    """Suggestion for better organization"""

    organization_type: str  # "tagging", "structure", "maintenance"
    title: str
    description: str
    impact_areas: list[str]
    implementation_steps: list[str]
    estimated_effort: str  # "low", "medium", "high"


class SuggestionRequest(BaseModel):
    """Request for suggestions"""

    user_id: str
    context_memory_ids: list[UUID] | None = Field(default_factory=list)
    suggestion_types: list[SuggestionType] | None = None
    limit: int | None = Field(default=10, gt=0)
    time_window_days: int | None = None
    include_learning_paths: bool = Field(default=True)
    include_content_suggestions: bool = Field(default=True)
    options: dict[str, Any] = Field(default_factory=dict)

    # Legacy fields
    suggestion_type: str | None = None
    max_suggestions: int | None = None


class SuggestionResponse(BaseModel):
    """Response containing suggestions"""

    suggestions: list[Suggestion]
    learning_paths: list[LearningPathSuggestion] = Field(default_factory=list)
    content_suggestions: list[ContentSuggestion] = Field(default_factory=list)
    organization_suggestions: list[OrganizationSuggestion] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
