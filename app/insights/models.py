"""
Data models for AI insights and pattern discovery
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class InsightType(str, Enum):
    """Types of insights that can be generated"""
    USAGE_PATTERN = "usage_pattern"
    KNOWLEDGE_GROWTH = "knowledge_growth"
    MEMORY_CLUSTER = "memory_cluster"
    LEARNING_TREND = "learning_trend"
    ACCESS_PATTERN = "access_pattern"
    TAG_EVOLUTION = "tag_evolution"
    IMPORTANCE_SHIFT = "importance_shift"
    CONTENT_GAP = "content_gap"
    RELATIONSHIP_DISCOVERY = "relationship_discovery"
    TEMPORAL_PATTERN = "temporal_pattern"


class PatternType(str, Enum):
    """Types of patterns that can be detected"""
    TEMPORAL = "temporal"  # Time-based patterns
    SEMANTIC = "semantic"  # Content similarity patterns
    BEHAVIORAL = "behavioral"  # Usage behavior patterns
    STRUCTURAL = "structural"  # Memory organization patterns
    EVOLUTIONARY = "evolutionary"  # Knowledge evolution patterns


class TimeFrame(str, Enum):
    """Time frames for analysis"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


class Insight(BaseModel):
    """Individual insight generated from memory analysis"""
    id: UUID
    type: InsightType
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    impact_score: float = Field(ge=0.0, le=10.0)
    data: dict[str, Any]
    recommendations: list[str] = []
    created_at: datetime
    time_frame: TimeFrame
    affected_memories: list[UUID] = []

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class Pattern(BaseModel):
    """Detected pattern in memory usage or content"""
    id: UUID
    type: PatternType
    name: str
    description: str
    strength: float = Field(ge=0.0, le=1.0)
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    examples: list[dict[str, Any]]
    metadata: dict[str, Any] = {}

    @field_validator('strength')
    @classmethod
    def validate_strength(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class MemoryCluster(BaseModel):
    """Cluster of related memories"""
    id: UUID
    name: str
    description: str
    size: int
    centroid_memory_id: UUID | None = None
    memory_ids: list[UUID]
    common_tags: list[str]
    average_importance: float
    coherence_score: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    keywords: list[str] = []

    @field_validator('coherence_score')
    @classmethod
    def validate_coherence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class KnowledgeGap(BaseModel):
    """Identified gap in knowledge"""
    id: UUID
    area: str
    description: str
    severity: float = Field(ge=0.0, le=1.0)
    related_memories: list[UUID]
    suggested_topics: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime

    @field_validator('severity', 'confidence')
    @classmethod
    def validate_scores(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class UsageStatistics(BaseModel):
    """Memory usage statistics"""
    time_frame: TimeFrame
    total_memories: int
    total_accesses: int
    unique_accessed: int
    average_importance: float
    most_accessed_memories: list[UUID]
    access_frequency: dict[str, int]  # hour/day -> count
    peak_usage_times: list[str]
    growth_rate: float  # percentage


class LearningProgress(BaseModel):
    """Learning progress tracking"""
    time_frame: TimeFrame
    topics_covered: int
    memories_created: int
    knowledge_retention_score: float = Field(ge=0.0, le=1.0)
    learning_velocity: float  # memories per day
    mastery_levels: dict[str, float]  # topic -> mastery score
    improvement_areas: list[str]
    achievements: list[str]


class InsightRequest(BaseModel):
    """Request for generating insights"""
    time_frame: TimeFrame = TimeFrame.WEEKLY
    insight_types: list[InsightType] | None = None
    limit: int = Field(default=10, ge=1, le=50)
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    include_recommendations: bool = True


class PatternDetectionRequest(BaseModel):
    """Request for pattern detection"""
    pattern_types: list[PatternType] | None = None
    time_frame: TimeFrame = TimeFrame.MONTHLY
    min_occurrences: int = Field(default=3, ge=1)
    min_strength: float = Field(default=0.5, ge=0.0, le=1.0)


class ClusteringRequest(BaseModel):
    """Request for memory clustering"""
    algorithm: Literal["kmeans", "dbscan", "hierarchical"] = "kmeans"
    num_clusters: int | None = Field(None, ge=2, le=50)
    min_cluster_size: int = Field(default=3, ge=2)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class GapAnalysisRequest(BaseModel):
    """Request for knowledge gap analysis"""
    domains: list[str] | None = None
    min_severity: float = Field(default=0.5, ge=0.0, le=1.0)
    include_suggestions: bool = True
    limit: int = Field(default=10, ge=1, le=50)


# Response models
class InsightResponse(BaseModel):
    """Response containing insights"""
    insights: list[Insight]
    total: int
    time_frame: TimeFrame
    generated_at: datetime
    statistics: UsageStatistics


class PatternResponse(BaseModel):
    """Response containing detected patterns"""
    patterns: list[Pattern]
    total: int
    time_frame: TimeFrame
    detected_at: datetime


class ClusterResponse(BaseModel):
    """Response containing memory clusters"""
    clusters: list[MemoryCluster]
    total_clusters: int
    total_memories_clustered: int
    unclustered_memories: int
    clustering_quality_score: float = Field(ge=0.0, le=1.0)


class GapAnalysisResponse(BaseModel):
    """Response containing knowledge gaps"""
    gaps: list[KnowledgeGap]
    total: int
    coverage_score: float = Field(ge=0.0, le=1.0)
    suggested_learning_paths: list[dict[str, Any]]
    analyzed_at: datetime


class TrendAnalysis(BaseModel):
    """Trend analysis results"""
    trend_type: str
    trend_direction: Literal["increasing", "decreasing", "stable"]
    confidence: float = Field(ge=0.0, le=1.0)
    data_points: list[dict[str, Any]]
    forecast: dict[str, Any] | None = None
    insights: list[str]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class PatternDetection(BaseModel):
    """Pattern detection results"""
    pattern_type: PatternType
    pattern_name: str
    occurrences: int
    confidence: float = Field(ge=0.0, le=1.0)
    examples: list[dict[str, Any]]
    description: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
