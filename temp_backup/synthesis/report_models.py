"""
Data models for automated report generation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports that can be generated"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"
    INSIGHTS = "insights"
    PROGRESS = "progress"
    KNOWLEDGE_MAP = "knowledge_map"
    LEARNING_PATH = "learning_path"


class ReportFormat(str, Enum):
    """Output formats for reports"""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    DOCX = "docx"
    EMAIL = "email"


class ReportSection(BaseModel):
    """Individual section of a report"""
    id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (markdown)")
    order: int = Field(..., description="Display order")
    data: Optional[dict[str, Any]] = Field(default=None, description="Supporting data")
    visualizations: Optional[list[dict[str, Any]]] = Field(default=None, description="Charts/graphs data")
    subsections: Optional[list["ReportSection"]] = Field(default=None, description="Nested sections")


class ReportTemplate(BaseModel):
    """Template for generating reports"""
    id: UUID = Field(default_factory=UUID)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: ReportType
    sections: list[str] = Field(..., description="Section identifiers to include")
    include_visualizations: bool = Field(default=True)
    include_metrics: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)
    custom_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSchedule(BaseModel):
    """Schedule for automated report generation"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    template_id: UUID
    report_type: ReportType
    format: ReportFormat
    schedule_type: str = Field(..., pattern="^(daily|weekly|monthly|cron)$")
    schedule_config: dict[str, Any] = Field(..., description="Schedule configuration")
    recipients: list[str] = Field(default_factory=list, description="Email addresses")
    enabled: bool = Field(default=True)
    last_generated: Optional[datetime] = None
    next_scheduled: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedReport(BaseModel):
    """A generated report instance"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    template_id: Optional[UUID] = None
    report_type: ReportType
    title: str
    subtitle: Optional[str] = None
    executive_summary: str
    sections: list[ReportSection]
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    format: ReportFormat
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    generation_time_ms: int
    period_start: datetime
    period_end: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportRequest(BaseModel):
    """Request to generate a report"""
    report_type: ReportType
    format: ReportFormat = Field(default=ReportFormat.HTML)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    template_id: Optional[UUID] = None
    include_sections: Optional[list[str]] = None
    exclude_sections: Optional[list[str]] = None
    custom_title: Optional[str] = None
    recipients: Optional[list[str]] = None
    options: dict[str, Any] = Field(default_factory=dict)


class InsightsReport(BaseModel):
    """Specialized insights report"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    period: str  # "last_7_days", "last_30_days", etc.

    # Key insights
    top_insights: list[str] = Field(..., min_items=3, max_items=10)
    key_patterns: list[dict[str, Any]] = Field(default_factory=list)
    emerging_topics: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_gaps: list[dict[str, Any]] = Field(default_factory=list)

    # Growth metrics
    memory_growth: dict[str, Any]
    connection_growth: dict[str, Any]
    topic_evolution: dict[str, Any]

    # Recommendations
    action_items: list[str] = Field(..., min_items=1, max_items=10)
    learning_suggestions: list[str] = Field(default_factory=list)
    consolidation_opportunities: list[dict[str, Any]] = Field(default_factory=list)

    # Visualizations
    knowledge_heatmap: Optional[dict[str, Any]] = None
    growth_chart: Optional[dict[str, Any]] = None
    topic_network: Optional[dict[str, Any]] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressReport(BaseModel):
    """Learning progress report"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    period: str

    # Progress metrics
    memories_created: int
    memories_reviewed: int
    connections_made: int
    topics_explored: int

    # Learning metrics
    knowledge_retention_score: float = Field(..., ge=0.0, le=1.0)
    learning_velocity: float = Field(..., description="Memories per day")
    topic_mastery: dict[str, float] = Field(default_factory=dict)

    # Achievements
    milestones_reached: list[str] = Field(default_factory=list)
    streaks: dict[str, int] = Field(default_factory=dict)

    # Comparisons
    vs_previous_period: dict[str, float] = Field(default_factory=dict)
    vs_average: dict[str, float] = Field(default_factory=dict)

    # Recommendations
    focus_areas: list[str] = Field(default_factory=list)
    suggested_reviews: list[UUID] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeMapReport(BaseModel):
    """Visual knowledge map report"""
    id: UUID = Field(default_factory=UUID)
    user_id: str

    # Map structure
    domains: list[dict[str, Any]] = Field(..., description="Knowledge domains")
    clusters: list[dict[str, Any]] = Field(..., description="Topic clusters")
    bridges: list[dict[str, Any]] = Field(..., description="Cross-domain connections")

    # Metrics
    domain_coverage: dict[str, float] = Field(default_factory=dict)
    cluster_density: dict[str, float] = Field(default_factory=dict)
    connectivity_score: float = Field(..., ge=0.0, le=1.0)

    # Insights
    strongest_domains: list[str] = Field(..., max_items=5)
    weakest_domains: list[str] = Field(..., max_items=5)
    isolated_clusters: list[str] = Field(default_factory=list)
    bridge_opportunities: list[dict[str, Any]] = Field(default_factory=list)

    # Visualization data
    graph_data: dict[str, Any] = Field(..., description="D3.js compatible graph data")
    heatmap_data: Optional[dict[str, Any]] = None
    treemap_data: Optional[dict[str, Any]] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningPathReport(BaseModel):
    """Personalized learning path report"""
    id: UUID = Field(default_factory=UUID)
    user_id: str
    goal: str = Field(..., description="Learning goal")

    # Current state
    current_knowledge: list[str] = Field(..., description="What you know")
    knowledge_gaps: list[str] = Field(..., description="What you need to learn")

    # Learning path
    recommended_path: list[dict[str, Any]] = Field(..., description="Step-by-step path")
    estimated_duration: str = Field(..., description="Estimated time to complete")
    difficulty_level: str = Field(..., pattern="^(beginner|intermediate|advanced|expert)$")

    # Resources
    suggested_topics: list[str] = Field(default_factory=list)
    related_memories: list[UUID] = Field(default_factory=list)
    external_resources: list[dict[str, str]] = Field(default_factory=list)

    # Milestones
    milestones: list[dict[str, Any]] = Field(..., min_items=3)
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)

    # Progress tracking
    completion_criteria: list[str] = Field(..., min_items=1)
    assessment_methods: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportDelivery(BaseModel):
    """Report delivery configuration"""
    id: UUID = Field(default_factory=UUID)
    report_id: UUID
    delivery_method: str = Field(..., pattern="^(email|webhook|storage|api)$")
    destination: str = Field(..., description="Email, URL, or path")
    status: str = Field(default="pending", pattern="^(pending|sending|delivered|failed)$")
    attempts: int = Field(default=0)
    last_attempt: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
