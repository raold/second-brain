from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import networkx as nx
import numpy as np

from app.utils.logging_config import get_logger

"""Graph Metrics Service for Knowledge Graph Analysis

Real implementation that analyzes the structure and properties of the
knowledge graph formed by memories and their relationships.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

# Optional dependencies
try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Type checking imports
if TYPE_CHECKING and NETWORKX_AVAILABLE:
    from networkx import Graph
else:
    Graph = Any

from app.models.synthesis.metrics_models import (
    ClusterMetrics,
    ConnectivityMetrics,
    GraphMetrics,
    KnowledgeCluster,
    MetricsRequest,
    NodeMetrics,
    TemporalMetrics,
)

logger = get_logger(__name__)


class GraphNode:
    """Represents a node in the knowledge graph"""

    def __init__(self, memory_id: UUID, content: str, importance: float, created_at: datetime):
        self.id = memory_id
        self.content = content
        self.importance = importance
        self.created_at = created_at
        self.connections: set[UUID] = set()
        self.tags: set[str] = set()
        self.metadata: dict[str, Any] = {}


class GraphMetricsService:
    """Service for analyzing knowledge graph structure and metrics"""

    def __init__(self, db, memory_service, relationship_analyzer):
        if not NETWORKX_AVAILABLE:
            raise ImportError(
                "NetworkX is required for graph metrics. Install with: pip install networkx"
            )
        if not NUMPY_AVAILABLE:
            raise ImportError(
                "NumPy is required for graph metrics. Install with: pip install numpy"
            )

        self.db = db
        self.memory_service = memory_service
        self.relationship_analyzer = relationship_analyzer

        # Graph cache
        self._graph_cache: Graph | None = None
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = timedelta(minutes=15)

    async def calculate_metrics(self, request: MetricsRequest) -> GraphMetrics:
        """Calculate comprehensive graph metrics"""
        try:
            # Build or get cached graph
            graph = await self._build_knowledge_graph(request.memory_ids)

            if graph.number_of_nodes() == 0:
                return self._empty_metrics()

            # Calculate different metric categories
            node_metrics = await self._calculate_node_metrics(graph)
            cluster_metrics = await self._calculate_cluster_metrics(graph)
            connectivity_metrics = await self._calculate_connectivity_metrics(graph)
            temporal_metrics = await self._calculate_temporal_metrics(graph)

            # Calculate overall graph health score
            health_score = self._calculate_graph_health(
                node_metrics, cluster_metrics, connectivity_metrics
            )

            # Convert node_metrics to proper format
            node_metrics_dict = {}
            if isinstance(node_metrics, dict) and "top_pagerank_nodes" in node_metrics:
                for node_info in node_metrics.get("top_pagerank_nodes", []):
                    if isinstance(node_info, dict) and "node" in node_info:
                        node_id = node_info["node"]
                        node_metrics_dict[str(node_id)] = NodeMetrics(
                            node_id=node_id,
                            degree=graph.degree(node_id) if node_id in graph else 0,
                            betweenness_centrality=0.0,
                            closeness_centrality=0.0,
                            pagerank=node_info.get("score", 0.0),
                        )

            return GraphMetrics(
                total_nodes=graph.number_of_nodes(),
                total_edges=graph.number_of_edges(),
                graph_density=nx.density(graph),
                average_degree=(
                    sum(dict(graph.degree()).values()) / graph.number_of_nodes()
                    if graph.number_of_nodes() > 0
                    else 0
                ),
                clustering_coefficient=nx.average_clustering(graph),
                node_metrics=node_metrics_dict,
                connectivity_metrics=connectivity_metrics,
                temporal_metrics=temporal_metrics,
                health_score=health_score,
                metadata={
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "graph_type": "knowledge_graph",
                    "includes_relationships": request.include_relationships,
                    "raw_node_metrics": node_metrics,  # Keep raw metrics in metadata
                },
            )

        except Exception as e:
            logger.error(f"Metrics calculation failed: {e}")
            return self._empty_metrics()

    async def analyze_node_importance(self, memory_id: UUID) -> NodeMetrics:
        """Analyze importance of a specific node in the graph"""
        try:
            graph = await self._build_knowledge_graph()

            if memory_id not in graph:
                raise ValueError(f"Memory {memory_id} not found in graph")

            # Calculate various centrality measures
            nx.degree_centrality(graph)[memory_id]

            # Betweenness centrality (how often node appears on shortest paths)
            between_cent = nx.betweenness_centrality(graph)[memory_id]

            # Closeness centrality (average distance to all other nodes)
            if graph.number_of_nodes() > 1:
                closeness_cent = nx.closeness_centrality(graph)[memory_id]
            else:
                closeness_cent = 0.0

            # PageRank (importance based on connections to important nodes)
            pagerank = nx.pagerank(graph)[memory_id]

            # Local clustering (how connected are node's neighbors)
            nx.clustering(graph, memory_id)

            # Get node data
            graph.nodes[memory_id]

            return NodeMetrics(
                node_id=memory_id,
                degree=graph.degree(memory_id),
                betweenness_centrality=between_cent,
                closeness_centrality=closeness_cent,
                pagerank=pagerank,
            )

        except Exception as e:
            logger.error(f"Node importance analysis failed: {e}")
            raise

    async def find_knowledge_clusters(self, min_cluster_size: int = 3) -> list[ClusterMetrics]:
        """Find and analyze knowledge clusters in the graph"""
        try:
            graph = await self._build_knowledge_graph()

            # Find connected components (natural clusters)
            components = list(nx.connected_components(graph.to_undirected()))

            # Filter by minimum size
            significant_components = [c for c in components if len(c) >= min_cluster_size]

            # Analyze each cluster
            clusters = []
            for i, component in enumerate(significant_components):
                subgraph = graph.subgraph(component)

                # Find most central node (cluster representative)
                pagerank_scores = nx.pagerank(subgraph)
                central_node = max(pagerank_scores, key=pagerank_scores.get)

                # Extract cluster theme from tags and content
                cluster_tags = set()
                for node in component:
                    node_data = graph.nodes[node]
                    cluster_tags.update(node_data.get("tags", []))

                # Calculate cluster metrics
                cluster = KnowledgeCluster(
                    cluster_id=f"cluster_{i}",
                    cluster_theme=self._infer_cluster_theme(cluster_tags, subgraph),
                    size=len(component),
                    density=nx.density(subgraph),
                    central_nodes=[central_node],
                    member_nodes=list(component),
                    metadata={
                        "avg_importance": np.mean(
                            [graph.nodes[n].get("importance", 0.5) for n in component]
                        ),
                        "tags": list(cluster_tags)[:10],  # Top 10 tags
                        "modularity": self._calculate_cluster_modularity(graph, component),
                        "cohesion": nx.average_clustering(subgraph.to_undirected()),
                    },
                )
                clusters.append(cluster)

            # Sort by size and importance
            clusters.sort(key=lambda c: (c.size, c.metadata.get("avg_importance", 0)), reverse=True)

            return clusters

        except Exception as e:
            logger.error(f"Cluster finding failed: {e}")
            return []

    async def _build_knowledge_graph(self, memory_ids: list[UUID] | None = None) -> Graph:
        """Build or retrieve the knowledge graph"""
        # Check cache
        if (
            self._graph_cache is not None
            and self._cache_timestamp
            and datetime.utcnow() - self._cache_timestamp < self._cache_ttl
            and memory_ids is None
        ):  # Only use cache for full graph
            return self._graph_cache

        # Build new graph
        graph = nx.Graph()

        # Fetch memories
        memories = await self._fetch_graph_memories(memory_ids)

        # Add nodes
        for memory in memories:
            graph.add_node(
                memory["id"],
                content=memory["content"],
                importance=memory["importance"],
                created_at=memory["created_at"],
                tags=memory.get("tags", []),
                metadata=memory.get("metadata", {}),
            )

        # Fetch and add relationships
        relationships = await self._fetch_relationships(memory_ids)

        for rel in relationships:
            # Add edge with relationship data
            graph.add_edge(
                rel["source_id"],
                rel["target_id"],
                relationship_type=rel["relationship_type"],
                strength=rel.get("strength", 0.5),
                created_at=rel.get("created_at"),
            )

        # Cache if full graph
        if memory_ids is None:
            self._graph_cache = graph
            self._cache_timestamp = datetime.utcnow()

        return graph

    async def _fetch_graph_memories(self, memory_ids: list[UUID] | None) -> list[dict[str, Any]]:
        """Fetch memories for graph construction"""
        if memory_ids:
            # Fetch specific memories
            placeholders = ",".join(f"${i+1}" for i in range(len(memory_ids)))
            query = f"""
            SELECT id, content, importance, created_at, tags, metadata
            FROM memories
            WHERE id IN ({placeholders})
            """
            memories = await self.db.fetch_all(query, *memory_ids)
        else:
            # Fetch all memories (with limit for performance)
            query = """
            SELECT id, content, importance, created_at, tags, metadata
            FROM memories
            ORDER BY importance DESC, created_at DESC
            LIMIT 5000
            """
            memories = await self.db.fetch_all(query)

        return [dict(m) for m in memories]

    async def _fetch_relationships(self, memory_ids: list[UUID] | None) -> list[dict[str, Any]]:
        """Fetch relationships between memories"""
        if memory_ids:
            # Fetch relationships involving specific memories
            placeholders = ",".join(f"${i+1}" for i in range(len(memory_ids)))
            query = f"""
            SELECT source_id, target_id, relationship_type, strength, created_at
            FROM memory_relationships
            WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
            """
            relationships = await self.db.fetch_all(query, *memory_ids, *memory_ids)
        else:
            # Fetch all relationships
            query = """
            SELECT source_id, target_id, relationship_type, strength, created_at
            FROM memory_relationships
            LIMIT 10000
            """
            relationships = await self.db.fetch_all(query)

        return [dict(r) for r in relationships]

    async def _calculate_node_metrics(self, graph: Graph) -> dict[str, Any]:
        """Calculate node-level metrics"""
        # Degree distribution
        degrees = [d for n, d in graph.degree()]
        degree_dist = {
            "mean": np.mean(degrees),
            "std": np.std(degrees),
            "min": min(degrees) if degrees else 0,
            "max": max(degrees) if degrees else 0,
            "median": np.median(degrees) if degrees else 0,
        }

        # Find hubs (highly connected nodes)
        degree_threshold = degree_dist["mean"] + 2 * degree_dist["std"]
        hubs = [n for n, d in graph.degree() if d > degree_threshold]

        # Find isolated nodes
        isolated = list(nx.isolates(graph))

        # Calculate centrality statistics
        pagerank_scores = nx.pagerank(graph)
        top_pagerank = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "degree_distribution": degree_dist,
            "hub_nodes": hubs[:20],  # Top 20 hubs
            "isolated_nodes": isolated[:20],  # Sample of isolated nodes
            "top_pagerank_nodes": [{"node": n, "score": s} for n, s in top_pagerank],
            "avg_clustering": nx.average_clustering(graph),
            "node_connectivity": nx.node_connectivity(graph) if graph.number_of_nodes() > 1 else 0,
        }

    async def _calculate_cluster_metrics(self, graph: Graph) -> dict[str, Any]:
        """Calculate cluster-level metrics"""
        # Find communities using different algorithms
        try:
            # Louvain community detection
            import community

            partition = community.best_partition(graph.to_undirected())
            modularity = community.modularity(partition, graph.to_undirected())

            # Count communities
            communities = defaultdict(list)
            for node, comm_id in partition.items():
                communities[comm_id].append(node)

            # Analyze community sizes
            comm_sizes = [len(nodes) for nodes in communities.values()]

            cluster_metrics = {
                "num_communities": len(communities),
                "modularity": modularity,
                "community_sizes": {
                    "mean": np.mean(comm_sizes),
                    "std": np.std(comm_sizes),
                    "min": min(comm_sizes),
                    "max": max(comm_sizes),
                },
                "largest_communities": sorted(
                    [(cid, len(nodes)) for cid, nodes in communities.items()],
                    key=lambda x: x[1],
                    reverse=True,
                )[:5],
            }
        except ImportError:
            # Fallback to connected components
            components = list(nx.connected_components(graph.to_undirected()))
            comp_sizes = [len(c) for c in components]

            cluster_metrics = {
                "num_components": len(components),
                "component_sizes": {
                    "mean": np.mean(comp_sizes) if comp_sizes else 0,
                    "std": np.std(comp_sizes) if comp_sizes else 0,
                    "min": min(comp_sizes) if comp_sizes else 0,
                    "max": max(comp_sizes) if comp_sizes else 0,
                },
            }

        return cluster_metrics

    async def _calculate_connectivity_metrics(self, graph: Graph) -> ConnectivityMetrics:
        """Calculate connectivity metrics"""
        # Basic connectivity
        is_connected = nx.is_connected(graph.to_undirected())
        num_components = nx.number_connected_components(graph.to_undirected())

        # Path statistics
        if graph.number_of_nodes() > 1 and is_connected:
            avg_path_length = nx.average_shortest_path_length(graph.to_undirected())
            diameter = nx.diameter(graph.to_undirected())
        else:
            avg_path_length = 0.0
            diameter = 0

        # Find bridges (edges whose removal disconnects the graph)
        bridges = list(nx.bridges(graph.to_undirected())) if graph.number_of_edges() > 0 else []

        # Find articulation points (nodes whose removal increases components)
        articulation_points = list(nx.articulation_points(graph.to_undirected()))

        return ConnectivityMetrics(
            is_connected=is_connected,
            num_connected_components=num_components,
            largest_component_size=(
                max([len(c) for c in nx.connected_components(graph.to_undirected())])
                if num_components > 0
                else 0
            ),
            average_path_length=avg_path_length,
            diameter=diameter,
            edge_connectivity=nx.edge_connectivity(graph) if graph.number_of_nodes() > 1 else 0,
            node_connectivity=nx.node_connectivity(graph) if graph.number_of_nodes() > 1 else 0,
            num_bridges=len(bridges),
            num_articulation_points=len(articulation_points),
            metadata={
                "bridges_sample": bridges[:10],  # Sample of bridges
                "articulation_points_sample": articulation_points[:10],
            },
        )

    async def _calculate_temporal_metrics(self, graph: Graph) -> TemporalMetrics:
        """Calculate temporal metrics"""
        # Extract creation times
        creation_times = []
        for node in graph.nodes():
            created_at = graph.nodes[node].get("created_at")
            if created_at:
                creation_times.append(created_at)

        if not creation_times:
            return TemporalMetrics(
                growth_rate=0.0,
                recent_activity_score=0.0,
                temporal_clusters=[],
                activity_periods=[],
                metadata={},
            )

        # Sort times
        creation_times.sort()

        # Calculate growth rate (memories per day)
        time_span = (creation_times[-1] - creation_times[0]).days
        growth_rate = len(creation_times) / max(time_span, 1)

        # Recent activity score (based on last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_nodes = sum(1 for t in creation_times if t > thirty_days_ago)
        recent_activity_score = recent_nodes / max(len(creation_times), 1)

        # Find temporal clusters (periods of high activity)
        temporal_clusters = self._find_temporal_clusters(creation_times)

        # Identify activity periods
        activity_periods = self._identify_activity_periods(creation_times)

        return TemporalMetrics(
            growth_rate=growth_rate,
            recent_activity_score=recent_activity_score,
            temporal_clusters=temporal_clusters,
            activity_periods=activity_periods,
            metadata={
                "total_time_span_days": time_span,
                "first_memory": creation_times[0].isoformat(),
                "last_memory": creation_times[-1].isoformat(),
                "memories_last_7_days": sum(
                    1 for t in creation_times if t > datetime.utcnow() - timedelta(days=7)
                ),
                "memories_last_30_days": recent_nodes,
            },
        )

    def _find_temporal_clusters(self, times: list[datetime]) -> list[dict[str, Any]]:
        """Find clusters of activity in time"""
        if len(times) < 2:
            return []

        # Sort times to ensure chronological order
        sorted_times = sorted(times)

        # Calculate time differences
        time_diffs = [
            (sorted_times[i + 1] - sorted_times[i]).total_seconds() / 3600
            for i in range(len(sorted_times) - 1)
        ]

        # Find clusters using a threshold based on median
        # Use median instead of mean to handle outliers better
        median_diff = np.median(time_diffs)
        # Threshold: gaps larger than 3x median indicate cluster boundaries
        threshold = median_diff * 3

        # If all times are very close, use a fixed threshold of 6 hours
        if threshold < 6:
            threshold = 6

        clusters = []
        current_cluster_start = 0

        for i, diff in enumerate(time_diffs):
            if diff > threshold:
                # End of cluster
                cluster_size = i - current_cluster_start + 1
                if cluster_size >= 3:  # Minimum cluster size
                    clusters.append(
                        {
                            "start_time": sorted_times[current_cluster_start].isoformat(),
                            "end_time": sorted_times[i].isoformat(),
                            "size": cluster_size,
                            "duration_hours": (
                                sorted_times[i] - sorted_times[current_cluster_start]
                            ).total_seconds()
                            / 3600,
                        }
                    )
                current_cluster_start = i + 1

        # Handle last cluster
        if len(sorted_times) - current_cluster_start >= 3:
            clusters.append(
                {
                    "start_time": sorted_times[current_cluster_start].isoformat(),
                    "end_time": sorted_times[-1].isoformat(),
                    "size": len(sorted_times) - current_cluster_start,
                    "duration_hours": (
                        sorted_times[-1] - sorted_times[current_cluster_start]
                    ).total_seconds()
                    / 3600,
                }
            )

        return clusters

    def _identify_activity_periods(self, times: list[datetime]) -> list[str]:
        """Identify characteristic activity periods"""
        periods = []

        # Check for daily patterns
        hours = [t.hour for t in times]
        hour_counts = defaultdict(int)
        for h in hours:
            hour_counts[h] += 1

        # Find peak hours
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        if peak_hours[0][1] > len(times) * 0.2:  # Significant concentration
            periods.append(f"Peak activity hours: {', '.join(f'{h[0]}:00' for h in peak_hours)}")

        # Check for weekly patterns
        weekdays = [t.weekday() for t in times]
        weekday_counts = defaultdict(int)
        for w in weekdays:
            weekday_counts[w] += 1

        # Find peak days
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        peak_days = sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        if peak_days[0][1] > len(times) * 0.25:  # Significant concentration
            periods.append(f"Most active days: {', '.join(day_names[d[0]] for d in peak_days)}")

        return periods

    def _infer_cluster_theme(self, tags: set[str], subgraph: Graph) -> str:
        """Infer theme of a cluster from tags and content"""
        if not tags:
            return "General Knowledge"

        # Sort tags by frequency in cluster
        tag_list = list(tags)
        if len(tag_list) <= 3:
            return ", ".join(tag_list)
        else:
            return f"{', '.join(tag_list[:3])} and {len(tag_list)-3} more"

    def _calculate_cluster_modularity(self, graph: Graph, cluster_nodes: set[UUID]) -> float:
        """Calculate modularity score for a specific cluster"""
        # Simplified modularity calculation
        internal_edges = 0
        external_edges = 0

        for node in cluster_nodes:
            for neighbor in graph.neighbors(node):
                if neighbor in cluster_nodes:
                    internal_edges += 1
                else:
                    external_edges += 1

        if internal_edges + external_edges == 0:
            return 0.0

        # Modularity score (higher means better clustering)
        return internal_edges / (internal_edges + external_edges)

    def _calculate_graph_health(
        self,
        node_metrics: dict[str, Any],
        cluster_metrics: dict[str, Any],
        connectivity_metrics: ConnectivityMetrics,
    ) -> float:
        """Calculate overall graph health score"""
        scores = []

        # Connectivity score (prefer connected graphs)
        conn_score = 1.0 if connectivity_metrics.is_connected else 0.5
        scores.append(conn_score * 0.3)

        # Clustering score (good clustering coefficient)
        clustering = node_metrics.get("avg_clustering", 0)
        cluster_score = min(clustering * 2, 1.0)  # Normalize
        scores.append(cluster_score * 0.2)

        # Modularity score (clear community structure)
        modularity = cluster_metrics.get("modularity", 0)
        mod_score = min(modularity * 1.5, 1.0)  # Normalize
        scores.append(mod_score * 0.2)

        # Balance score (not too many isolated nodes)
        total_nodes = node_metrics.get("degree_distribution", {}).get("mean", 1) * 100  # Estimate
        isolated_ratio = len(node_metrics.get("isolated_nodes", [])) / max(total_nodes, 1)
        balance_score = 1.0 - min(isolated_ratio * 5, 1.0)  # Penalize high isolation
        scores.append(balance_score * 0.3)

        return sum(scores)

    def _empty_metrics(self) -> GraphMetrics:
        """Return empty metrics structure"""
        return GraphMetrics(
            total_nodes=0,
            total_edges=0,
            graph_density=0.0,
            average_degree=0.0,
            clustering_coefficient=0.0,
            node_metrics={},
            cluster_metrics={},
            connectivity_metrics=ConnectivityMetrics(
                is_connected=False,
                num_connected_components=0,
                largest_component_size=0,
                average_path_length=0.0,
                diameter=0,
                edge_connectivity=0,
                node_connectivity=0,
                num_bridges=0,
                num_articulation_points=0,
                metadata={},
            ),
            temporal_metrics=TemporalMetrics(
                growth_rate=0.0,
                recent_activity_score=0.0,
                temporal_clusters=[],
                activity_periods=[],
                metadata={},
            ),
            health_score=0.0,
            metadata={"empty": True},
        )
