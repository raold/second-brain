from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NodeMetrics(BaseModel):
    node_id: UUID
    degree: int = Field(default=0, ge=0)
    betweenness_centrality: float = Field(default=0.0, ge=0, le=1)
    closeness_centrality: float = Field(default=0.0, ge=0, le=1)
    pagerank: float = Field(default=0.0, ge=0, le=1)


class ConnectivityMetrics(BaseModel):
    """Connectivity metrics for the graph"""
    is_connected: bool = Field(default=False)
    num_connected_components: int = Field(default=0, ge=0)
    largest_component_size: int = Field(default=0, ge=0)
    average_path_length: float = Field(default=0.0, ge=0)
    diameter: int = Field(default=0, ge=0)
    edge_connectivity: int = Field(default=0, ge=0)
    node_connectivity: int = Field(default=0, ge=0)
    num_bridges: int = Field(default=0, ge=0)
    num_articulation_points: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemporalMetrics(BaseModel):
    """Temporal metrics for memory creation patterns"""
    growth_rate: float = Field(default=0.0)  # memories per day
    recent_activity_score: float = Field(default=0.0, ge=0, le=1)
    temporal_clusters: List[Dict[str, Any]] = Field(default_factory=list)
    activity_periods: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeCluster(BaseModel):
    """Represents a cluster of related knowledge"""
    cluster_id: str
    cluster_theme: str
    size: int = Field(ge=1)
    density: float = Field(ge=0, le=1)
    central_nodes: List[UUID]
    member_nodes: List[UUID]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClusterMetrics(BaseModel):
    """Metrics for knowledge clusters"""
    clusters: List[KnowledgeCluster] = Field(default_factory=list)
    modularity: float = Field(default=0.0, ge=-1, le=1)
    num_clusters: int = Field(default=0, ge=0)
    largest_cluster_size: int = Field(default=0, ge=0)
    avg_cluster_size: float = Field(default=0.0, ge=0)
    inter_cluster_connections: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphMetrics(BaseModel):
    """Extended graph metrics with all fields"""
    total_nodes: int = Field(default=0, ge=0)
    total_edges: int = Field(default=0, ge=0)
    graph_density: float = Field(default=0.0, ge=0, le=1)
    average_degree: float = Field(default=0.0, ge=0)
    clustering_coefficient: float = Field(default=0.0, ge=0, le=1)
    node_metrics: Dict[str, NodeMetrics] = Field(default_factory=dict)
    connectivity_metrics: Optional[ConnectivityMetrics] = None
    temporal_metrics: Optional[TemporalMetrics] = None
    health_score: float = Field(default=0.0, ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


class MetricsRequest(BaseModel):
    """Request for graph metrics calculation"""
    memory_ids: Optional[List[UUID]] = None
    include_relationships: bool = Field(default=True)
    include_temporal: bool = Field(default=True)
    time_window_days: Optional[int] = None
    user_id: Optional[str] = None