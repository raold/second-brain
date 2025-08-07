"""Report models for generating analytical reports"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    """Report output formats"""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


class ReportType(str, Enum):
    """Types of reports"""
    SUMMARY = "summary"
    ANALYTICAL = "analytical"
    PROGRESS = "progress"
    INSIGHTS = "insights"
    COMPREHENSIVE = "comprehensive"


class ReportSection(BaseModel):
    """A section of a report"""
    title: str
    content: str
    section_type: str = "text"
    data: Optional[Dict[str, Any]] = None
    charts: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class ReportSchedule(BaseModel):
    """Schedule for automated report generation"""
    schedule_id: str = Field(default_factory=lambda: f"sch_{datetime.now().timestamp()}")
    report_type: ReportType
    frequency: str  # daily, weekly, monthly
    recipients: List[str] = []
    format: ReportFormat = ReportFormat.MARKDOWN
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class ReportRequest(BaseModel):
    """Request for report generation"""
    user_id: Optional[str] = None
    report_type: ReportType = ReportType.SUMMARY
    format: ReportFormat = ReportFormat.MARKDOWN
    time_range_days: Optional[int] = None
    memory_ids: Optional[List[str]] = None
    include_charts: bool = False
    include_recommendations: bool = True
    custom_sections: List[str] = []


class ReportResponse(BaseModel):
    """Generated report response"""
    report_id: str = Field(default_factory=lambda: f"rep_{datetime.now().timestamp()}")
    report_type: ReportType
    format: ReportFormat
    title: str
    sections: List[ReportSection] = []
    summary: Optional[str] = None
    total_memories_analyzed: int = 0
    insights_count: int = 0
    recommendations: List[str] = []
    generation_time_ms: float = 0.0
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)