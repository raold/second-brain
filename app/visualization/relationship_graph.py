"""
Advanced relationship graph visualization and analysis
"""

from app.utils.logging_config import get_logger
from typing import List
from typing import Any
from typing import Union
from collections import Counter
from collections import defaultdict
logger = get_logger(__name__)


class RelationshipGraph:
    """Advanced relationship graph for entity network analysis and visualization"""

    def __init__(self,
                 enable_clustering: bool = True,
                 enable_centrality: bool = True,
                 enable_pathfinding: bool = True,
                 layout_algorithm: str = "spring"):
        """
        Initialize relationship graph

        Args:
            enable_clustering: Enable community detection
            enable_centrality: Enable centrality analysis
            enable_pathfinding: Enable path finding algorithms
            layout_algorithm: Graph layout algorithm (spring, circular, hierarchical)
        """
        self.enable_clustering = enable_clustering and NETWORKX_AVAILABLE and SKLEARN_AVAILABLE
        self.enable_centrality = enable_centrality and NETWORKX_AVAILABLE
        self.enable_pathfinding = enable_pathfinding and NETWORKX_AVAILABLE
        self.layout_algorithm = layout_algorithm

        # Initialize graph
        if NETWORKX_AVAILABLE:
            self.graph = nx.MultiDiGraph()
        else:
            self.graph = None
            logger.warning("NetworkX not available. Graph features will be limited.")

        # Cache for computed metrics
        self._centrality_cache = {}
        self._community_cache = {}
        self._layout_cache = {}

    def build_graph(self,
                   entities: list[Entity],
                   relationships: list[Relationship],
                   min_confidence: float = 0.5) -> dict[str, Any]:
        """
        Build graph from entities and relationships

        Args:
            entities: List of entities
            relationships: List of relationships
            min_confidence: Minimum confidence threshold

        Returns:
            Graph statistics and metadata
        """
        if not self.graph:
            return {"error": "NetworkX not available"}

        # Clear existing graph
        self.graph.clear()
        self._clear_caches()

        # Add nodes (entities)
        for entity in entities:
            self.graph.add_node(
                entity.id,
                label=entity.text,
                type=entity.type.value,
                normalized=entity.normalized,
                confidence=entity.confidence,
                metadata=entity.metadata or {}
            )

        # Add edges (relationships)
        for rel in relationships:
            if rel.confidence >= min_confidence:
                self.graph.add_edge(
                    rel.source.id,
                    rel.target.id,
                    type=rel.type.value,
                    confidence=rel.confidence,
                    evidence=rel.evidence,
                    metadata=rel.metadata or {}
                )

        # Compute graph statistics
        stats = self._compute_graph_statistics()

        # Add advanced metrics if enabled
        if self.enable_centrality:
            stats["centrality_metrics"] = self.compute_centrality_metrics()

        if self.enable_clustering:
            stats["communities"] = self.detect_communities()

        return stats

    def _compute_graph_statistics(self) -> dict[str, Any]:
        """Compute basic graph statistics"""
        if not self.graph:
            return {}

        # Basic metrics
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()

        stats = {
            "num_entities": num_nodes,
            "num_relationships": num_edges,
            "density": nx.density(self.graph) if num_nodes > 0 else 0,
            "is_connected": nx.is_weakly_connected(self.graph) if num_nodes > 0 else False
        }

        # Degree distribution
        if num_nodes > 0:
            degrees = dict(self.graph.degree())
            stats["degree_distribution"] = {
                "mean": sum(degrees.values()) / len(degrees),
                "max": max(degrees.values()),
                "min": min(degrees.values())
            }

        # Relationship type distribution
        edge_types = [data["type"] for _, _, data in self.graph.edges(data=True)]
        stats["relationship_types"] = dict(Counter(edge_types))

        # Entity type distribution
        node_types = [data["type"] for _, data in self.graph.nodes(data=True)]
        stats["entity_types"] = dict(Counter(node_types))

        return stats

    def compute_centrality_metrics(self, top_n: int = 10) -> dict[str, Any]:
        """
        Compute various centrality metrics for nodes

        Args:
            top_n: Number of top central nodes to return

        Returns:
            Dictionary of centrality metrics
        """
        if not self.graph or self.graph.number_of_nodes() == 0:
            return {}

        metrics = {}

        try:
            # Degree centrality
            degree_centrality = nx.degree_centrality(self.graph)
            metrics["degree_centrality"] = self._get_top_nodes(degree_centrality, top_n)

            # Betweenness centrality (nodes that connect different parts)
            if self.graph.number_of_nodes() > 2:
                betweenness = nx.betweenness_centrality(self.graph)
                metrics["betweenness_centrality"] = self._get_top_nodes(betweenness, top_n)

            # Eigenvector centrality (importance based on neighbor importance)
            if nx.is_weakly_connected(self.graph):
                try:
                    eigenvector = nx.eigenvector_centrality(self.graph.to_undirected(), max_iter=100)
                    metrics["eigenvector_centrality"] = self._get_top_nodes(eigenvector, top_n)
                except:
                    logger.warning("Eigenvector centrality computation failed")

            # PageRank (Google's algorithm)
            pagerank = nx.pagerank(self.graph, max_iter=100)
            metrics["pagerank"] = self._get_top_nodes(pagerank, top_n)

            # Cache results
            self._centrality_cache = metrics

        except Exception as e:
            logger.error(f"Error computing centrality metrics: {e}")

        return metrics

    def detect_communities(self, algorithm: str = "spectral") -> dict[str, Any]:
        """
        Detect communities in the graph

        Args:
            algorithm: Community detection algorithm

        Returns:
            Community structure and statistics
        """
        if not self.graph or self.graph.number_of_nodes() < 3:
            return {}

        try:
            # Convert to undirected for community detection
            undirected = self.graph.to_undirected()

            communities = []

            if algorithm == "spectral" and SKLEARN_AVAILABLE:
                # Spectral clustering
                adj_matrix = nx.adjacency_matrix(undirected)
                clustering = SpectralClustering(
                    n_clusters=min(5, self.graph.number_of_nodes() // 3),
                    affinity='precomputed',
                    random_state=42
                )
                labels = clustering.fit_predict(adj_matrix)

                # Group nodes by community
                community_map = defaultdict(list)
                for node, label in zip(self.graph.nodes(), labels, strict=False):
                    community_map[label].append(node)

                communities = list(community_map.values())

            elif algorithm == "louvain":
                # Louvain method (if python-louvain is available)
                try:
                    import community as community_louvain
                    partition = community_louvain.best_partition(undirected)

                    community_map = defaultdict(list)
                    for node, comm_id in partition.items():
                        community_map[comm_id].append(node)

                    communities = list(community_map.values())
                except ImportError:
                    logger.warning("Louvain method not available, using connected components")
                    communities = list(nx.connected_components(undirected))
            else:
                # Fallback to connected components
                communities = list(nx.connected_components(undirected))

            # Analyze communities
            community_data = []
            for i, community in enumerate(communities):
                if len(community) > 1:  # Skip single-node communities
                    # Get subgraph for this community
                    subgraph = self.graph.subgraph(community)

                    # Find most central node in community
                    if len(community) > 2:
                        sub_centrality = nx.degree_centrality(subgraph)
                        central_node = max(sub_centrality, key=sub_centrality.get)
                    else:
                        central_node = list(community)[0]

                    # Get entity types in community
                    entity_types = [self.graph.nodes[n]["type"] for n in community]
                    type_distribution = dict(Counter(entity_types))

                    community_data.append({
                        "id": i,
                        "size": len(community),
                        "central_entity": {
                            "id": central_node,
                            "label": self.graph.nodes[central_node]["label"]
                        },
                        "entity_types": type_distribution,
                        "density": nx.density(subgraph)
                    })

            # Cache results
            self._community_cache = {
                "algorithm": algorithm,
                "num_communities": len(community_data),
                "communities": community_data,
                "modularity": self._calculate_modularity(communities, undirected)
            }

            return self._community_cache

        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            return {}

    def find_paths(self,
                  source_id: str,
                  target_id: str,
                  max_paths: int = 5,
                  max_length: int = 5) -> list[dict[str, Any]]:
        """
        Find paths between two entities

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_paths: Maximum number of paths to return
            max_length: Maximum path length

        Returns:
            List of paths with metadata
        """
        if not self.graph or not self.enable_pathfinding:
            return []

        if source_id not in self.graph or target_id not in self.graph:
            return []

        paths = []

        try:
            # Find all simple paths
            all_paths = nx.all_simple_paths(
                self.graph,
                source_id,
                target_id,
                cutoff=max_length
            )

            # Process paths
            for i, path in enumerate(all_paths):
                if i >= max_paths:
                    break

                # Build path information
                path_info = {
                    "path": path,
                    "length": len(path) - 1,
                    "entities": [],
                    "relationships": [],
                    "confidence": 1.0
                }

                # Add entity information
                for node_id in path:
                    node_data = self.graph.nodes[node_id]
                    path_info["entities"].append({
                        "id": node_id,
                        "label": node_data["label"],
                        "type": node_data["type"]
                    })

                # Add relationship information
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i+1])
                    if edge_data:
                        # Handle multiple edges
                        for edge in edge_data.values():
                            path_info["relationships"].append({
                                "type": edge["type"],
                                "confidence": edge["confidence"]
                            })
                            path_info["confidence"] *= edge["confidence"]

                paths.append(path_info)

            # Sort by confidence and length
            paths.sort(key=lambda p: (p["confidence"], -p["length"]), reverse=True)

        except Exception as e:
            logger.error(f"Error finding paths: {e}")

        return paths

    def get_entity_neighborhood(self,
                               entity_id: str,
                               depth: int = 2,
                               min_confidence: float = 0.5) -> dict[str, Any]:
        """
        Get the neighborhood of an entity up to specified depth

        Args:
            entity_id: Entity ID
            depth: How many hops to include
            min_confidence: Minimum relationship confidence

        Returns:
            Subgraph data for the neighborhood
        """
        if not self.graph or entity_id not in self.graph:
            return {}

        try:
            # Get all nodes within depth
            neighbors = nx.single_source_shortest_path_length(
                self.graph, entity_id, cutoff=depth
            )

            # Create subgraph
            subgraph = self.graph.subgraph(neighbors.keys())

            # Filter by confidence
            edges_to_keep = [
                (u, v, k) for u, v, k, data in subgraph.edges(keys=True, data=True)
                if data.get("confidence", 0) >= min_confidence
            ]

            filtered_subgraph = nx.MultiDiGraph()
            filtered_subgraph.add_nodes_from(subgraph.nodes(data=True))
            filtered_subgraph.add_edges_from([
                (u, v, subgraph.edges[u, v, k])
                for u, v, k in edges_to_keep
            ])

            # Prepare visualization data
            nodes = []
            edges = []

            for node_id, data in filtered_subgraph.nodes(data=True):
                nodes.append({
                    "id": node_id,
                    "label": data["label"],
                    "type": data["type"],
                    "distance": neighbors[node_id]
                })

            for u, v, data in filtered_subgraph.edges(data=True):
                edges.append({
                    "source": u,
                    "target": v,
                    "type": data["type"],
                    "confidence": data["confidence"]
                })

            return {
                "center": entity_id,
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "max_distance": max(neighbors.values()) if neighbors else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting entity neighborhood: {e}")
            return {}

    def compute_layout(self, algorithm: str | None = None) -> dict[str, tuple[float, float]]:
        """
        Compute graph layout for visualization

        Args:
            algorithm: Layout algorithm (spring, circular, hierarchical, kamada_kawai)

        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        if not self.graph or self.graph.number_of_nodes() == 0:
            return {}

        algorithm = algorithm or self.layout_algorithm

        # Check cache
        if algorithm in self._layout_cache:
            return self._layout_cache[algorithm]

        try:
            if algorithm == "spring":
                pos = nx.spring_layout(self.graph, k=1/math.sqrt(self.graph.number_of_nodes()))
            elif algorithm == "circular":
                pos = nx.circular_layout(self.graph)
            elif algorithm == "hierarchical":
                # Use topological sort for hierarchical layout
                try:
                    # Create DAG by removing cycles
                    dag = nx.DiGraph()
                    dag.add_nodes_from(self.graph.nodes(data=True))

                    # Add edges that don't create cycles
                    for u, v, data in self.graph.edges(data=True):
                        dag.add_edge(u, v, **data)
                        if not nx.is_directed_acyclic_graph(dag):
                            dag.remove_edge(u, v)

                    # Compute hierarchical positions
                    if dag.number_of_edges() > 0:
                        pos = nx.nx_agraph.graphviz_layout(dag, prog='dot')
                    else:
                        pos = nx.spring_layout(self.graph)
                except:
                    pos = nx.spring_layout(self.graph)
            elif algorithm == "kamada_kawai":
                pos = nx.kamada_kawai_layout(self.graph)
            else:
                pos = nx.spring_layout(self.graph)

            # Normalize positions to [0, 1] range
            if pos:
                x_values = [p[0] for p in pos.values()]
                y_values = [p[1] for p in pos.values()]

                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)

                x_range = x_max - x_min if x_max - x_min > 0 else 1
                y_range = y_max - y_min if y_max - y_min > 0 else 1

                normalized_pos = {
                    node: (
                        (x - x_min) / x_range,
                        (y - y_min) / y_range
                    )
                    for node, (x, y) in pos.items()
                }

                # Cache result
                self._layout_cache[algorithm] = normalized_pos

                return normalized_pos

        except Exception as e:
            logger.error(f"Error computing layout: {e}")

        return {}

    def export_to_format(self, format: str = "json") -> Union[str, dict]:
        """
        Export graph to various formats

        Args:
            format: Export format (json, graphml, gexf)

        Returns:
            Exported graph data
        """
        if not self.graph:
            return {} if format == "json" else ""

        try:
            if format == "json":
                # Custom JSON format with all metadata
                data = {
                    "nodes": [],
                    "edges": [],
                    "metadata": {
                        "num_nodes": self.graph.number_of_nodes(),
                        "num_edges": self.graph.number_of_edges()
                    }
                }

                # Add nodes
                for node_id, node_data in self.graph.nodes(data=True):
                    data["nodes"].append({
                        "id": node_id,
                        **node_data
                    })

                # Add edges
                for u, v, edge_data in self.graph.edges(data=True):
                    data["edges"].append({
                        "source": u,
                        "target": v,
                        **edge_data
                    })

                # Add layout if computed
                if self._layout_cache:
                    data["layouts"] = {
                        alg: {node: list(pos) for node, pos in layout.items()}
                        for alg, layout in self._layout_cache.items()
                    }

                # Add analysis results if available
                if self._centrality_cache:
                    data["centrality"] = self._centrality_cache

                if self._community_cache:
                    data["communities"] = self._community_cache

                return data

            elif format == "graphml":
                import io
                buffer = io.StringIO()
                nx.write_graphml(self.graph, buffer)
                return buffer.getvalue()

            elif format == "gexf":
                import io
                buffer = io.StringIO()
                nx.write_gexf(self.graph, buffer)
                return buffer.getvalue()

            else:
                logger.error(f"Unknown export format: {format}")
                return "" if format != "json" else {}

        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            return {} if format == "json" else ""

    def _get_top_nodes(self, scores: dict[str, float], top_n: int) -> list[dict[str, Any]]:
        """Get top N nodes by score"""
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        return [
            {
                "id": node_id,
                "label": self.graph.nodes[node_id]["label"],
                "type": self.graph.nodes[node_id]["type"],
                "score": score
            }
            for node_id, score in sorted_nodes
        ]

    def _calculate_modularity(self, communities: list[set], graph: nx.Graph) -> float:
        """Calculate modularity of community partition"""
        try:
            # Create partition dictionary
            partition = {}
            for i, community in enumerate(communities):
                for node in community:
                    partition[node] = i

            # Calculate modularity
            if len(partition) == len(graph):
                try:
                    import community as community_louvain
                    return community_louvain.modularity(partition, graph)
                except ImportError:
                    # Simple modularity calculation
                    m = graph.number_of_edges()
                    if m == 0:
                        return 0

                    q = 0
                    for u, v in graph.edges():
                        if partition.get(u) == partition.get(v):
                            q += 1 - (graph.degree(u) * graph.degree(v)) / (2 * m)

                    return q / (2 * m)

        except Exception as e:
            logger.error(f"Error calculating modularity: {e}")

        return 0.0

    def _clear_caches(self):
        """Clear all cached computations"""
        self._centrality_cache.clear()
        self._community_cache.clear()
        self._layout_cache.clear()
