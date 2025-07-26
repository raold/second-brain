"""
Report Generation Models - v2.8.2

Data models for automated report generation including configurations,
templates, and scheduling options.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class KnowledgeMapReport(BaseModel):
    """Report containing knowledge map visualization data"""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    clusters: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportType(str, Enum):
    """Types of reports that can be generated."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    INSIGHTS = "insights"
    PROGRESS = "progress"
    KNOWLEDGE_MAP = "knowledge_map"
    LEARNING_PATH = "learning_path"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Supported report output formats."""

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    EMAIL = "email"
    DOCX = "docx"
    CSV = "csv"


class ReportSection(BaseModel):
    """Individual section within a report."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    order: int = Field(1, description="Display order")
    include_visualization: bool = Field(False, description="Include charts/graphs")
    visualization_type: Optional[str] = Field(None, description="Type of visualization")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportTemplate(BaseModel):
    """Reusable report template."""

    id: Optional[str] = Field(None, description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    report_type: ReportType = Field(..., description="Type of report")
    sections: list[str] = Field(..., description="Section identifiers to include")
    default_format: ReportFormat = Field(ReportFormat.PDF)
    custom_css: Optional[str] = Field(None, description="Custom styling for HTML/PDF")
    include_summary: bool = Field(True, description="Include AI-generated summary")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportConfig(BaseModel):
    """Configuration for report generation."""

    report_type: ReportType = Field(..., description="Type of report to generate")
    format: ReportFormat = Field(ReportFormat.PDF, description="Output format")
    template_id: Optional[str] = Field(None, description="Template to use")

    # Time range configuration
    start_date: Optional[datetime] = Field(None, description="Report start date")
    end_date: Optional[datetime] = Field(None, description="Report end date")
    relative_timeframe: Optional[str] = Field(
        None,
        description="Relative timeframe (e.g., 'last_7_days', 'last_month')"
    )

    # Content configuration
    include_memories: bool = Field(True, description="Include memory statistics")
    include_insights: bool = Field(True, description="Include AI insights")
    include_graphs: bool = Field(True, description="Include visualizations")
    include_recommendations: bool = Field(True, description="Include recommendations")

    # AI configuration
    use_gpt4_summary: bool = Field(True, description="Use GPT-4 for executive summary")
    summary_length: int = Field(500, description="Target summary length in words")
    analysis_depth: str = Field("standard", description="Analysis depth: basic, standard, deep")

    # Delivery configuration
    email_recipients: list[str] = Field(default_factory=list, description="Email recipients")
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook for delivery")

    @field_validator('relative_timeframe')
    def validate_timeframe(cls, v):
        """Validate relative timeframe format."""
        valid_timeframes = [
            "last_24_hours", "last_7_days", "last_30_days",
            "last_month", "last_quarter", "last_year",
            "this_week", "this_month", "this_quarter", "this_year"
        ]
        if v and v not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")
        return v


class ReportSchedule(BaseModel):
    """Schedule configuration for automated reports."""

    id: Optional[str] = Field(None, description="Schedule ID")
    name: str = Field(..., description="Schedule name")
    config: ReportConfig = Field(..., description="Report configuration")

    # Scheduling
    enabled: bool = Field(True, description="Whether schedule is active")
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    timezone: str = Field("UTC", description="Timezone for schedule")

    # Delivery
    auto_deliver: bool = Field(True, description="Automatically deliver reports")
    delivery_format: ReportFormat = Field(..., description="Delivery format")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = Field(None, description="Last execution time")
    next_run: Optional[datetime] = Field(None, description="Next scheduled run")

    @field_validator('cron_expression')
    def validate_cron(cls, v):
        """Validate cron expression format."""
        # Basic validation - in production, use croniter
        parts = v.split()
        if len(parts) not in [5, 6]:  # Standard cron or with seconds
            raise ValueError("Invalid cron expression format")
        return v


class ReportRequest(BaseModel):
    """Request to generate a report."""

    config: ReportConfig = Field(..., description="Report configuration")
    immediate: bool = Field(True, description="Generate immediately")
    priority: str = Field("normal", description="Priority: low, normal, high")
    callback_url: Optional[HttpUrl] = Field(
        None,
        description="URL to call when report is ready"
    )


class ReportMetrics(BaseModel):
    """Metrics included in a report."""

    total_memories: int = Field(0, description="Total memories in period")
    new_memories: int = Field(0, description="New memories added")
    memories_reviewed: int = Field(0, description="Memories reviewed")

    # Activity metrics
    active_days: int = Field(0, description="Days with activity")
    peak_activity_time: Optional[str] = Field(None, description="Most active time")
    average_daily_memories: float = Field(0.0, description="Average memories per day")

    # Knowledge metrics
    topics_covered: list[str] = Field(default_factory=list, description="Topics covered")
    knowledge_growth_rate: float = Field(0.0, description="Knowledge growth percentage")
    retention_rate: float = Field(0.0, description="Memory retention rate")

    # Insights
    top_insights: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top insights discovered"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for improvement"
    )


class ReportResponse(BaseModel):
    """Response containing generated report."""

    id: str = Field(..., description="Report ID")
    config: ReportConfig = Field(..., description="Configuration used")

    # Report content
    title: str = Field(..., description="Report title")
    summary: Optional[str] = Field(None, description="Executive summary")
    sections: list[ReportSection] = Field(..., description="Report sections")
    metrics: ReportMetrics = Field(..., description="Report metrics")

    # Generation metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_time_ms: int = Field(..., description="Generation time in milliseconds")
    format: ReportFormat = Field(..., description="Report format")

    # Output
    content: Optional[str] = Field(None, description="Report content (for text formats)")
    file_url: Optional[HttpUrl] = Field(None, description="Download URL (for file formats)")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")

    # Delivery status
    delivered: bool = Field(False, description="Whether report was delivered")
    delivery_status: Optional[str] = Field(None, description="Delivery status message")


class ReportFilter(BaseModel):
    """Filters for querying reports."""

    report_type: Optional[ReportType] = Field(None, description="Filter by type")
    format: Optional[ReportFormat] = Field(None, description="Filter by format")
    start_date: Optional[datetime] = Field(None, description="Reports after this date")
    end_date: Optional[datetime] = Field(None, description="Reports before this date")
    delivered: Optional[bool] = Field(None, description="Filter by delivery status")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


# Additional report types expected by tests
class LearningPathReport(BaseModel):
    """Report for learning progress and recommendations"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    title: str
    current_progress: Dict[str, Any]
    completed_topics: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    learning_velocity: float = Field(ge=0)
    estimated_completion: Optional[datetime] = None
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressReport(BaseModel):
    """Report tracking progress over time"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    title: str
    time_period: Dict[str, datetime]
    metrics: Dict[str, Any]
    achievements: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    comparisons: Dict[str, Any] = Field(default_factory=dict)
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# Legacy alias - must be after ReportResponse
GeneratedReport = ReportResponse
