"""Metrics models for graph and knowledge analysis"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeMetrics(BaseModel):
    """Metrics for a single node in the knowledge graph"""
    node_id: str
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0
    betweenness_centrality: float = 0.0
    closeness_centrality: float = 0.0
    page_rank: float = 0.0
    clustering_coefficient: float = 0.0


class KnowledgeCluster(BaseModel):
    """A cluster of related knowledge nodes"""
    cluster_id: str
    node_ids: List[str]
    size: int
    density: float = 0.0
    coherence_score: float = 0.0
    central_theme: Optional[str] = None
    keywords: List[str] = []


class ClusterMetrics(BaseModel):
    """Metrics for knowledge clusters"""
    total_clusters: int = 0
    average_cluster_size: float = 0.0
    largest_cluster_size: int = 0
    clusters: List[KnowledgeCluster] = []
    modularity_score: float = 0.0


class ConnectivityMetrics(BaseModel):
    """Graph connectivity metrics"""
    is_connected: bool = False
    number_of_components: int = 0
    largest_component_size: int = 0
    average_path_length: float = 0.0
    diameter: int = 0
    density: float = 0.0


class TemporalMetrics(BaseModel):
    """Temporal analysis metrics"""
    time_range_days: int = 0
    memories_per_day: float = 0.0
    peak_activity_date: Optional[datetime] = None
    growth_rate: float = 0.0
    activity_patterns: Dict[str, Any] = {}


class GraphMetrics(BaseModel):
    """Complete graph metrics"""
    total_nodes: int = 0
    total_edges: int = 0
    average_degree: float = 0.0
    node_metrics: List[NodeMetrics] = []
    cluster_metrics: ClusterMetrics = Field(default_factory=ClusterMetrics)
    connectivity_metrics: ConnectivityMetrics = Field(default_factory=ConnectivityMetrics)
    temporal_metrics: TemporalMetrics = Field(default_factory=TemporalMetrics)
    metadata: Dict[str, Any] = {}
    computed_at: datetime = Field(default_factory=datetime.now)


class MetricsRequest(BaseModel):
    """Request for graph metrics computation"""
    user_id: Optional[str] = None
    memory_ids: Optional[List[str]] = None
    include_node_metrics: bool = True
    include_clusters: bool = True
    include_temporal: bool = True
    time_range_days: Optional[int] = None