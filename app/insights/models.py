"""Models for insights and analytics"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
    user_id: Optional[str] = None
    memory_ids: Optional[List[str]] = None
    time_frame: TimeFrame = TimeFrame.MONTH
    insight_types: List[InsightType] = []
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
    data: Dict[str, Any] = {}
    recommendations: List[str] = []
    related_memories: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)


class InsightResponse(BaseModel):
    """Response containing insights"""
    request_id: str = Field(default_factory=lambda: f"req_{datetime.now().timestamp()}")
    insights: List[Insight] = []
    time_frame: TimeFrame
    total_memories_analyzed: int = 0
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)