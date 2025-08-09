"""Summary models for knowledge summarization"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SummaryType(str, Enum):
    """Types of summaries"""

    BRIEF = "brief"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    NARRATIVE = "narrative"


class FormatType(str, Enum):
    """Output format types"""

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PDF = "pdf"


class SummaryRequest(BaseModel):
    """Request for memory summarization"""

    memory_ids: Optional[List[str]] = None
    user_id: Optional[str] = None
    summary_type: SummaryType = SummaryType.BRIEF
    max_length: Optional[int] = None
    include_insights: bool = True
    include_themes: bool = True
    time_range_days: Optional[int] = None


class SummaryResponse(BaseModel):
    """Response from summarization"""

    summary_id: str = Field(default_factory=lambda: f"sum_{datetime.now().timestamp()}")
    summary_type: SummaryType
    content: str
    memories_processed: int = 0
    key_insights: List[str] = []
    main_themes: List[str] = []
    important_dates: List[datetime] = []
    word_count: int = 0
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
