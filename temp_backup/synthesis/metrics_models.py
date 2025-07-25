"""
Data models for graph metrics feature
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GraphMetrics(BaseModel):
    """Real-time graph metrics"""
    graph_id: str = Field(default="main")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Basic metrics
    node_count: int = Field(..., ge=0)
    edge_count: int = Field(..., ge=0)
    density: float = Field(..., ge=0.0, le=1.0)
    average_degree: float = Field(..., ge=0.0)

    # Structural metrics
    clustering_coefficient: float = Field(..., ge=0.0, le=1.0)
    connected_components: int = Field(..., ge=1)
    largest_component_size: int = Field(..., ge=0)
    diameter: int = Field(..., ge=0)  # -1 if infinite (disconnected)
    average_path_length: float = Field(..., ge=0.0)

    # Centrality distributions
    degree_centrality: dict[str, float] = Field(default_factory=dict)
    betweenness_centrality: dict[str, float] = Field(default_factory=dict)
    closeness_centrality: dict[str, float] = Field(default_factory=dict)
    eigenvector_centrality: dict[str, float] = Field(default_factory=dict)

    # Growth metrics
    growth_rate_nodes_per_day: float = Field(..., ge=0.0)
    growth_rate_edges_per_day: float = Field(..., ge=0.0)
    new_nodes_last_hour: int = Field(default=0, ge=0)
    new_edges_last_hour: int = Field(default=0, ge=0)

    # Performance metrics
    calculation_time_ms: int = Field(..., ge=0)
    cache_hit: bool = False

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricsTrend(BaseModel):
    """Trend analysis for a specific metric"""
    metric_name: str
    time_series: list[dict[str, Any]]  # [{"timestamp": dt, "value": float}]
    trend_direction: str  # 'increasing', 'decreasing', 'stable', 'volatile'
    trend_strength: float = Field(..., ge=0.0, le=1.0)
    average_value: float
    min_value: float
    max_value: float
    standard_deviation: float
    forecast_next_value: Optional[float] = None
    confidence_interval: Optional[tuple[float, float]] = None


class Anomaly(BaseModel):
    """Detected anomaly in graph metrics"""
    id: UUID = Field(default_factory=UUID)
    metric_name: str
    detected_at: datetime
    anomaly_type: str  # 'spike', 'drop', 'pattern_break', 'unusual_value'
    severity: str  # 'low', 'medium', 'high', 'critical'
    current_value: float
    expected_value: float
    deviation_percentage: float
    description: str
    suggested_investigation: list[str] = Field(default_factory=list)
    related_events: list[dict[str, Any]] = Field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsDashboard(BaseModel):
    """Comprehensive metrics dashboard"""
    current_metrics: GraphMetrics
    historical_metrics: list[GraphMetrics] = Field(..., min_items=1)

    # Trends
    trends: dict[str, MetricsTrend] = Field(default_factory=dict)

    # Anomalies
    active_anomalies: list[Anomaly] = Field(default_factory=list)
    recent_anomalies: list[Anomaly] = Field(default_factory=list)

    # Insights
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Predictions
    predictions: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Summary statistics
    summary: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    time_range_days: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_time_ms: int = Field(..., ge=0)


class MetricsSnapshot(BaseModel):
    """Point-in-time snapshot of key metrics"""
    id: UUID = Field(default_factory=UUID)
    name: str
    description: Optional[str] = None
    metrics: GraphMetrics
    notable_nodes: list[dict[str, Any]] = Field(default_factory=list)  # Top central nodes
    notable_communities: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


class MetricsAlert(BaseModel):
    """Alert configuration for metrics"""
    id: UUID = Field(default_factory=UUID)
    name: str
    metric_name: str
    condition: str  # 'greater_than', 'less_than', 'equals', 'change_rate'
    threshold: float
    time_window_minutes: int = Field(default=60, ge=1)
    enabled: bool = True
    notification_channels: list[str] = Field(default_factory=list)
    last_triggered: Optional[datetime] = None
    trigger_count: int = Field(default=0, ge=0)
