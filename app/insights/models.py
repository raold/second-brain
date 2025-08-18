"""Models for insights and analytics"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TimeFrame(str, Enum):
    """Time frame for analysis"""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


class InsightType(str, Enum):
    """Types of insights"""

    TREND = "trend"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"


class InsightRequest(BaseModel):
    """Request for generating insights"""

    user_id: str | None = None
    memory_ids: list[str] | None = None
    time_frame: TimeFrame = TimeFrame.MONTH
    insight_types: list[InsightType] = []
    min_confidence: float = 0.5
    max_results: int = 10


class Insight(BaseModel):
    """An insight generated from memory analysis"""

    insight_id: str = Field(default_factory=lambda: f"ins_{datetime.now().timestamp()}")
    type: InsightType
    title: str
    description: str
    confidence: float = 0.0
    importance: float = 0.0
    data: dict[str, Any] = {}
    recommendations: list[str] = []
    related_memories: list[str] = []
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)


class InsightResponse(BaseModel):
    """Response containing insights"""

    request_id: str = Field(default_factory=lambda: f"req_{datetime.now().timestamp()}")
    insights: list[Insight] = []
    time_frame: TimeFrame
    total_memories_analyzed: int = 0
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
