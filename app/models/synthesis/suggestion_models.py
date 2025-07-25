from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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