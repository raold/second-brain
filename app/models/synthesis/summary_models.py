from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    memory_ids: List[UUID]
    summary_type: str = Field(default="concise")
    max_length: Optional[int] = Field(default=500, gt=0)


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