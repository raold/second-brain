"""Advanced synthesis models"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SynthesisStrategy(str, Enum):
    """Synthesis strategy types"""

    CHRONOLOGICAL = "chronological"
    THEMATIC = "thematic"
    IMPORTANCE_BASED = "importance_based"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SynthesisRequest(BaseModel):
    """Request for memory synthesis"""

    memory_ids: list[str] | None = None
    user_id: str | None = None
    strategy: SynthesisStrategy = SynthesisStrategy.HYBRID
    filters: dict[str, Any] = {}
    max_results: int = 10
    include_metadata: bool = True


class SynthesisResult(BaseModel):
    """Result of memory synthesis"""

    synthesis_id: str = Field(default_factory=lambda: f"syn_{datetime.now().timestamp()}")
    strategy_used: SynthesisStrategy
    memories_processed: int = 0
    themes_identified: list[str] = []
    summary: str | None = None
    insights: list[dict[str, Any]] = []
    confidence_score: float = 0.0
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
