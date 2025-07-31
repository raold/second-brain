from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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
    related_memory_ids: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningPathSuggestion(BaseModel):
    """Suggested learning path"""
    path_name: str
    description: str
    steps: List[str]
    estimated_duration_days: int
    difficulty_level: str  # "beginner", "intermediate", "advanced"
    prerequisites: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    resources: List[Dict[str, str]] = Field(default_factory=list)


class ContentSuggestion(BaseModel):
    """Suggested content to create"""
    content_type: str  # "synthesis", "deep_dive", "reflection"
    topic: str
    rationale: str
    prompts: List[str]
    estimated_value: float = Field(ge=0, le=1)
    related_memories: List[UUID] = Field(default_factory=list)


class OrganizationSuggestion(BaseModel):
    """Suggestion for better organization"""
    organization_type: str  # "tagging", "structure", "maintenance"
    title: str
    description: str
    impact_areas: List[str]
    implementation_steps: List[str]
    estimated_effort: str  # "low", "medium", "high"


class SuggestionRequest(BaseModel):
    """Request for suggestions"""
    user_id: str
    context_memory_ids: Optional[List[UUID]] = Field(default_factory=list)
    suggestion_types: Optional[List[SuggestionType]] = None
    limit: Optional[int] = Field(default=10, gt=0)
    time_window_days: Optional[int] = None
    include_learning_paths: bool = Field(default=True)
    include_content_suggestions: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)
    
    # Legacy fields
    suggestion_type: Optional[str] = None
    max_suggestions: Optional[int] = None


class SuggestionResponse(BaseModel):
    """Response containing suggestions"""
    suggestions: List[Suggestion]
    learning_paths: List[LearningPathSuggestion] = Field(default_factory=list)
    content_suggestions: List[ContentSuggestion] = Field(default_factory=list)
    organization_suggestions: List[OrganizationSuggestion] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)