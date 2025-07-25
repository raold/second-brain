from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdvancedSynthesisRequest(BaseModel):
    memory_ids: List[UUID]
    synthesis_type: str = Field(default="default")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AdvancedSynthesisResult(BaseModel):
    id: UUID
    synthesis: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisOptions(BaseModel):
    max_tokens: int = Field(default=1000, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    include_references: bool = Field(default=True)