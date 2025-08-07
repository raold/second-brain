"""Advanced synthesis models"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
    memory_ids: Optional[List[str]] = None
    user_id: Optional[str] = None
    strategy: SynthesisStrategy = SynthesisStrategy.HYBRID
    filters: Dict[str, Any] = {}
    max_results: int = 10
    include_metadata: bool = True


class SynthesisResult(BaseModel):
    """Result of memory synthesis"""
    synthesis_id: str = Field(default_factory=lambda: f"syn_{datetime.now().timestamp()}")
    strategy_used: SynthesisStrategy
    memories_processed: int = 0
    themes_identified: List[str] = []
    summary: Optional[str] = None
    insights: List[Dict[str, Any]] = []
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)