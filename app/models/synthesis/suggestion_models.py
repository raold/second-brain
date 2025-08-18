"""Suggestion models for intelligent recommendations"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Types of suggestions"""

    CONTENT = "content"
    ORGANIZATION = "organization"
    LEARNING_PATH = "learning_path"
    CONNECTION = "connection"
    REVIEW = "review"
    CLEANUP = "cleanup"


class ActionType(str, Enum):
    """Types of suggested actions"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    TAG = "tag"
    LINK = "link"
    REVIEW = "review"


class Suggestion(BaseModel):
    """Base suggestion model"""

    suggestion_id: str = Field(default_factory=lambda: f"sug_{datetime.now().timestamp()}")
    type: SuggestionType
    action: ActionType
    title: str
    description: str
    priority: float = 0.5
    confidence: float = 0.0
    reason: str | None = None
    metadata: dict[str, Any] = {}


class ContentSuggestion(Suggestion):
    """Suggestion for content creation or modification"""

    type: SuggestionType = SuggestionType.CONTENT
    related_memories: list[str] = []
    suggested_content: str | None = None
    suggested_tags: list[str] = []
    knowledge_gaps: list[str] = []


class OrganizationSuggestion(Suggestion):
    """Suggestion for memory organization"""

    type: SuggestionType = SuggestionType.ORGANIZATION
    affected_memories: list[str] = []
    suggested_structure: dict[str, Any] | None = None
    current_issues: list[str] = []


class LearningPathSuggestion(Suggestion):
    """Suggestion for learning paths"""

    type: SuggestionType = SuggestionType.LEARNING_PATH
    topics: list[str] = []
    recommended_order: list[str] = []
    estimated_time_hours: float = 0.0
    prerequisites: list[str] = []
    learning_objectives: list[str] = []


class SuggestionRequest(BaseModel):
    """Request for suggestions"""

    user_id: str | None = None
    memory_ids: list[str] | None = None
    suggestion_types: list[SuggestionType] = []
    max_suggestions: int = 10
    min_confidence: float = 0.5
    include_reasons: bool = True


class SuggestionResponse(BaseModel):
    """Response with suggestions"""

    request_id: str = Field(default_factory=lambda: f"req_{datetime.now().timestamp()}")
    suggestions: list[Suggestion] = []
    total_analyzed: int = 0
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
