from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConsolidationRequest(BaseModel):
    memory_ids: List[UUID]
    consolidation_type: str = Field(default="merge")
    preserve_originals: bool = Field(default=True)


class ConsolidationResult(BaseModel):
    id: UUID
    consolidated_content: str
    original_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationStatus(BaseModel):
    status: str
    progress: float = Field(default=0.0, ge=0, le=1)
    message: Optional[str] = None