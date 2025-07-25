from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GraphMetrics(BaseModel):
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    average_degree: float = Field(default=0.0, ge=0)
    density: float = Field(default=0.0, ge=0, le=1)
    connected_components: int = Field(default=0, ge=0)


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
    metric_name: str
    current_value: float
    previous_value: float
    change_percentage: float
    threshold: float
    severity: str = Field(default="info")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)