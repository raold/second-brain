from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

"""
Analytics models for v2.8.3 Intelligence features.

This module defines data models for advanced analytics, including
dashboard metrics, trend analysis, and performance tracking.
"""

from enum import Enum

from pydantic import ConfigDict, validator


class MetricType(str, Enum):
    """Types of metrics tracked in analytics."""

    MEMORY_COUNT = "memory_count"
    MEMORY_GROWTH = "memory_growth"
    QUERY_PERFORMANCE = "query_performance"
    EMBEDDING_QUALITY = "embedding_quality"
    RELATIONSHIP_DENSITY = "relationship_density"
    KNOWLEDGE_COVERAGE = "knowledge_coverage"
    REVIEW_COMPLETION = "review_completion"
    RETENTION_RATE = "retention_rate"
    API_USAGE = "api_usage"
    SYSTEM_HEALTH = "system_health"


class TimeGranularity(str, Enum):
    """Time granularity for analytics aggregation."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class TrendDirection(str, Enum):
    """Direction of metric trends."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnomalyType(str, Enum):
    """Types of anomalies detected."""

    SPIKE = "spike"
    DROP = "drop"
    PATTERN_BREAK = "pattern_break"
    THRESHOLD_BREACH = "threshold_breach"
    UNUSUAL_FREQUENCY = "unusual_frequency"


class InsightCategory(str, Enum):
    """Categories of predictive insights."""

    PERFORMANCE = "performance"
    KNOWLEDGE = "knowledge"
    BEHAVIOR = "behavior"
    SYSTEM = "system"
    OPPORTUNITY = "opportunity"
    WARNING = "warning"


class MetricPoint(BaseModel):
    """Single data point for a metric."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    value: float
    metadata: dict[str, Any] | None = Field(default_factory=dict)

    @validator("value")
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Metric value cannot be negative")
        return v


class MetricSeries(BaseModel):
    """Time series data for a metric."""

    model_config = ConfigDict(from_attributes=True)

    metric_type: MetricType
    data_points: list[MetricPoint]
    granularity: TimeGranularity
    start_time: datetime
    end_time: datetime

    @property
    def average(self) -> float:
        """Calculate average value."""
        if not self.data_points:
            return 0.0
        return sum(p.value for p in self.data_points) / len(self.data_points)

    @property
    def trend(self) -> TrendDirection:
        """Determine trend direction."""
        if len(self.data_points) < 2:
            return TrendDirection.STABLE

        # Simple linear regression slope
        n = len(self.data_points)
        x_mean = n / 2
        y_mean = self.average

        numerator = sum((i - x_mean) * (p.value - y_mean) for i, p in enumerate(self.data_points))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.STABLE

        slope = numerator / denominator

        # Determine trend based on slope and variance
        variance = sum((p.value - y_mean) ** 2 for p in self.data_points) / n
        cv = (variance**0.5) / y_mean if y_mean > 0 else 0

        if cv > 0.5:  # High coefficient of variation
            return TrendDirection.VOLATILE
        elif abs(slope) < 0.01:
            return TrendDirection.STABLE
        elif slope > 0:
            return TrendDirection.INCREASING
        else:
            return TrendDirection.DECREASING


class Anomaly(BaseModel):
    """Detected anomaly in metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_type: MetricType
    anomaly_type: AnomalyType
    timestamp: datetime
    severity: float = Field(ge=0.0, le=1.0)
    expected_value: float
    actual_value: float
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class PredictiveInsight(BaseModel):
    """Predictive insight generated from analytics."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: InsightCategory
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    impact_score: float = Field(ge=0.0, le=1.0)
    timeframe: str  # e.g., "next 7 days", "within 24 hours"
    recommendations: list[str]
    supporting_metrics: list[MetricType]
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeGap(BaseModel):
    """Identified gap in knowledge base."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic: str
    related_concepts: list[str]
    gap_score: float = Field(ge=0.0, le=1.0)
    importance_score: float = Field(ge=0.0, le=1.0)
    suggested_queries: list[str]
    potential_sources: list[str]
    identified_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard data."""

    model_config = ConfigDict(from_attributes=True)

    # Core metrics
    metrics: dict[MetricType, MetricSeries]

    # Advanced analytics
    anomalies: list[Anomaly]
    insights: list[PredictiveInsight]
    knowledge_gaps: list[KnowledgeGap]

    # Summary statistics
    total_memories: int
    active_users: int
    system_health_score: float = Field(ge=0.0, le=1.0)

    # Time information
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    time_range: TimeGranularity

    def get_critical_insights(self) -> list[PredictiveInsight]:
        """Get high-impact insights."""
        return sorted(
            [i for i in self.insights if i.impact_score > 0.7],
            key=lambda x: x.impact_score,
            reverse=True,
        )

    def get_recent_anomalies(self, hours: int = 24) -> list[Anomaly]:
        """Get anomalies from recent hours."""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        return [a for a in self.anomalies if a.timestamp.timestamp() > cutoff]


class AnalyticsQuery(BaseModel):
    """Query parameters for analytics data."""

    model_config = ConfigDict(from_attributes=True)

    metrics: list[MetricType] | None = None
    granularity: TimeGranularity = TimeGranularity.DAY
    start_date: datetime | None = None
    end_date: datetime | None = None
    include_anomalies: bool = True
    include_insights: bool = True
    include_knowledge_gaps: bool = True
    user_id: str | None = None

    @validator("end_date")
    def validate_date_range(cls, v, values):
        if v and "start_date" in values and values["start_date"]:
            if v < values["start_date"]:
                raise ValueError("End date must be after start date")
        return v


class MetricThreshold(BaseModel):
    """Threshold configuration for metric monitoring."""

    model_config = ConfigDict(from_attributes=True)

    metric_type: MetricType
    min_value: float | None = None
    max_value: float | None = None
    alert_on_breach: bool = True
    breach_duration_minutes: int = 5

    def is_breached(self, value: float) -> bool:
        """Check if value breaches threshold."""
        if self.min_value is not None and value < self.min_value:
            return True
        if self.max_value is not None and value > self.max_value:
            return True
        return False


class PerformanceBenchmark(BaseModel):
    """Performance benchmark for system metrics."""

    model_config = ConfigDict(from_attributes=True)

    operation: str  # e.g., "memory_search", "embedding_generation"
    p50_ms: float  # 50th percentile
    p90_ms: float  # 90th percentile
    p99_ms: float  # 99th percentile
    throughput_per_second: float
    error_rate: float = Field(ge=0.0, le=1.0)
    measured_at: datetime = Field(default_factory=datetime.utcnow)
