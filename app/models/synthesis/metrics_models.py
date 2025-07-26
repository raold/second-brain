from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GraphMetrics(BaseModel):
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    average_degree: float = Field(default=0.0, ge=0)
    avg_degree: float = Field(default=0.0, ge=0)  # Alias for compatibility
    density: float = Field(default=0.0, ge=0, le=1)
    connected_components: int = Field(default=0, ge=0)
    components: int = Field(default=0, ge=0)  # Alias for compatibility
    clustering_coefficient: float = Field(default=0.0, ge=0, le=1)
    diameter: Optional[int] = Field(default=None, ge=0)
    centrality_scores: Dict[str, float] = Field(default_factory=dict)
    community_count: int = Field(default=0, ge=0)
    modularity: float = Field(default=0.0, ge=-1, le=1)


class NodeMetrics(BaseModel):
    node_id: UUID
    degree: int = Field(default=0, ge=0)
    betweenness_centrality: float = Field(default=0.0, ge=0, le=1)
    closeness_centrality: float = Field(default=0.0, ge=0, le=1)
    pagerank: float = Field(default=0.0, ge=0, le=1)


class MetricsReport(BaseModel):
    graph_metrics: GraphMetrics
    top_nodes: List[NodeMetrics] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MetricsAlert(BaseModel):
    """Alert for significant metric changes"""
    id: UUID = Field(default_factory=uuid4)
    metric_name: str
    alert_type: str = Field(default="threshold")  # "threshold", "anomaly", "trend"
    severity: str = Field(default="info")  # "low", "medium", "high"
    current_value: float
    actual_value: float = Field(default=0.0)  # Alias for compatibility
    previous_value: Optional[float] = None
    change_percentage: Optional[float] = None
    threshold: Optional[float] = None
    threshold_value: Optional[float] = None  # Alias for compatibility
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Alias
    resolved_at: Optional[datetime] = None


class MetricsTrend(BaseModel):
    """Trend data for a metric over time"""
    metric_name: str
    time_points: List[datetime]
    values: List[float]
    trend_direction: str = Field(default="stable")  # "increasing", "decreasing", "stable"
    change_rate: float = Field(default=0.0)
    forecast: Optional[List[float]] = None


class MetricsSnapshot(BaseModel):
    """Snapshot of all metrics at a point in time"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    graph_metrics: GraphMetrics
    memory_metrics: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    usage_metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsDashboard(BaseModel):
    """Dashboard configuration and data"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    name: str
    description: Optional[str] = None
    widgets: List[Dict[str, Any]] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval: int = Field(default=60, gt=0)  # seconds
    snapshots: List[MetricsSnapshot] = Field(default_factory=list)
    alerts: List[MetricsAlert] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)