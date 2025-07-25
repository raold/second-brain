"""
Knowledge graph visualization service for v2.8.2 Week 4.

This service generates interactive knowledge graphs with various
layout algorithms and filtering capabilities.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

import networkx as nx
import numpy as np

from app.database import Database
from app.models.memory import Memory
from app.models.synthesis.advanced_models import (
    GraphLayout,
    GraphVisualizationRequest,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
)
from app.services.memory_relationship_analyzer import MemoryRelationshipAnalyzer as RelationshipAnalyzer
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class GraphVisualizationService:
    """Service for generating knowledge graph visualizations."""

    def __init__(
        self,
        database: Database,
        memory_service: MemoryService,
        relationship_analyzer: RelationshipAnalyzer
    ):
        self.db = database
        self.memory_service = memory_service
        self.relationship_analyzer = relationship_analyzer

        # Layout algorithms
        self.layout_algorithms = {
            GraphLayout.FORCE_DIRECTED: self._force_directed_layout,
            GraphLayout.HIERARCHICAL: self._hierarchical_layout,
            GraphLayout.CIRCULAR: self._circular_layout,
            GraphLayout.RADIAL: self._radial_layout,
            GraphLayout.TIMELINE: self._timeline_layout,
            GraphLayout.CLUSTERED: self._clustered_layout
        }

        # Color schemes
        self.color_schemes = {
            "default": self._default_colors,
            "importance": self._importance_colors,
            "type": self._type_colors,
            "age": self._age_colors,
            "cluster": self._cluster_colors
        }

    async def generate_knowledge_graph(
        self,
        request: GraphVisualizationRequest
    ) -> KnowledgeGraph:
        """Generate knowledge graph visualization."""
        # Fetch memories and relationships
        memories, relationships = await self._fetch_graph_data(request)

        # Build NetworkX graph
        nx_graph = self._build_networkx_graph(memories, relationships)

        # Apply clustering if requested
        if request.cluster_by:
            clusters = self._apply_clustering(
                nx_graph, memories, request.cluster_by
            )
        else:
            clusters = None

        # Create nodes and edges
        nodes = self._create_graph_nodes(
            memories, nx_graph, request, clusters
        )
        edges = self._create_graph_edges(
            relationships, nx_graph, request
        )

        # Apply layout algorithm
        layout_func = self.layout_algorithms[request.layout]
        nodes = layout_func(nodes, edges, nx_graph, request)

        # Apply color scheme
        color_func = self.color_schemes.get(
            request.color_scheme, self._default_colors
        )
        nodes = color_func(nodes, memories, clusters)

        # Create knowledge graph
        graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            metadata={
                "layout": request.layout.value,
                "color_scheme": request.color_scheme,
                "filters": request.filters,
                "cluster_by": request.cluster_by
            },
            clusters=clusters
        )

        # Calculate statistics
        graph.calculate_stats()

        return graph

    async def _fetch_graph_data(
        self,
        request: GraphVisualizationRequest
    ) -> tuple[list[Memory], list[Any]]:
        """Fetch memories and relationships for graph."""
        # Fetch memories based on filters
        memories = await self._fetch_filtered_memories(request)

        # Limit number of nodes
        if len(memories) > request.max_nodes:
            # Prioritize by importance or connections
            memories = self._prioritize_memories(
                memories, request.max_nodes
            )

        # Fetch relationships
        relationships = []
        memory_ids = {m.id for m in memories}

        for memory in memories:
            rels = await self.relationship_analyzer.find_related_memories(
                memory.id, request.user_id, limit=100
            )

            # Filter to include only relationships within our memory set
            for rel in rels:
                if rel.target_memory_id in memory_ids:
                    relationships.append(rel)

        return memories, relationships

    async def _fetch_filtered_memories(
        self,
        request: GraphVisualizationRequest
    ) -> list[Memory]:
        """Fetch memories based on filters."""
        # In production, this would use database queries
        # For now, fetch all and filter
        all_memories = await self.memory_service.search_memories(
            query="",
            user_id=request.user_id,
            limit=10000
        )

        memories = all_memories.memories if all_memories else []

        # Apply filters
        if request.filters:
            if 'tags' in request.filters:
                tags = set(request.filters['tags'])
                memories = [
                    m for m in memories
                    if m.tags and tags.intersection(m.tags)
                ]

            if 'types' in request.filters:
                types = request.filters['types']
                memories = [
                    m for m in memories
                    if m.memory_type.value in types
                ]

            if 'min_importance' in request.filters:
                min_imp = request.filters['min_importance']
                memories = [
                    m for m in memories
                    if m.importance >= min_imp
                ]

        # Apply time range
        if request.time_range:
            start = request.time_range.get('start')
            end = request.time_range.get('end')

            if start:
                memories = [m for m in memories if m.created_at >= start]
            if end:
                memories = [m for m in memories if m.created_at <= end]

        return memories

    def _prioritize_memories(
        self,
        memories: list[Memory],
        max_nodes: int
    ) -> list[Memory]:
        """Prioritize memories for visualization."""
        # Score each memory
        scores = []
        for memory in memories:
            score = 0

            # Importance factor
            score += memory.importance * 10

            # Recency factor
            age_days = (datetime.utcnow() - memory.created_at).days
            recency_score = max(0, 100 - age_days)
            score += recency_score * 0.5

            # Tag factor (memories with more tags are often more connected)
            if memory.tags:
                score += len(memory.tags) * 5

            scores.append((score, memory))

        # Sort by score and take top N
        scores.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scores[:max_nodes]]

    def _build_networkx_graph(
        self,
        memories: list[Memory],
        relationships: list[Any]
    ) -> nx.Graph:
        """Build NetworkX graph from memories and relationships."""
        graph = nx.Graph()

        # Add nodes
        for memory in memories:
            graph.add_node(
                str(memory.id),
                memory=memory,
                type='memory',
                importance=memory.importance
            )

        # Add edges
        for rel in relationships:
            graph.add_edge(
                str(rel.source_memory_id),
                str(rel.target_memory_id),
                relationship=rel,
                weight=rel.strength,
                type=rel.relationship_type
            )

        return graph

    def _apply_clustering(
        self,
        graph: nx.Graph,
        memories: list[Memory],
        cluster_by: str
    ) -> list[list[str]]:
        """Apply clustering to graph nodes."""
        if cluster_by == "community":
            # Use Louvain community detection
            import community as community_louvain
            partition = community_louvain.best_partition(graph)

            # Convert to cluster list
            clusters = defaultdict(list)
            for node, cluster_id in partition.items():
                clusters[cluster_id].append(node)

            return list(clusters.values())

        elif cluster_by == "tag":
            # Cluster by shared tags
            tag_clusters = defaultdict(list)
            memory_map = {str(m.id): m for m in memories}

            for node_id in graph.nodes():
                memory = memory_map.get(node_id)
                if memory and memory.tags:
                    # Use first tag as cluster
                    tag_clusters[memory.tags[0]].append(node_id)
                else:
                    tag_clusters["untagged"].append(node_id)

            return list(tag_clusters.values())

        elif cluster_by == "type":
            # Cluster by memory type
            type_clusters = defaultdict(list)
            memory_map = {str(m.id): m for m in memories}

            for node_id in graph.nodes():
                memory = memory_map.get(node_id)
                if memory:
                    type_clusters[memory.memory_type.value].append(node_id)

            return list(type_clusters.values())

        return []

    def _create_graph_nodes(
        self,
        memories: list[Memory],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest,
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Create visualization nodes."""
        nodes = []
        memory_map = {str(m.id): m for m in memories}

        # Calculate node sizes
        if request.node_size_by == "importance":
            sizes = self._calculate_importance_sizes(memories)
        elif request.node_size_by == "connections":
            sizes = self._calculate_connection_sizes(nx_graph)
        else:
            sizes = {str(m.id): 1.0 for m in memories}

        for memory in memories:
            node_id = str(memory.id)

            # Include orphans check
            if not request.include_orphans and nx_graph.degree(node_id) == 0:
                continue

            # Determine icon based on memory type
            icon_map = {
                "episodic": "📅",
                "semantic": "🧠",
                "procedural": "⚙️",
                "question": "❓",
                "reflection": "💭"
            }

            node = KnowledgeGraphNode(
                id=node_id,
                label=memory.title[:50],  # Truncate long titles
                type="memory",
                properties={
                    "full_title": memory.title,
                    "importance": memory.importance,
                    "created_at": memory.created_at.isoformat(),
                    "memory_type": memory.memory_type.value,
                    "tags": memory.tags or []
                },
                size=sizes.get(node_id, 1.0),
                icon=icon_map.get(memory.memory_type.value, "📄")
            )

            nodes.append(node)

        return nodes

    def _create_graph_edges(
        self,
        relationships: list[Any],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphEdge]:
        """Create visualization edges."""
        edges = []

        # Calculate edge weights
        if request.edge_weight_by == "strength":
            weights = {
                (str(r.source_memory_id), str(r.target_memory_id)): r.strength
                for r in relationships
            }
        else:
            weights = {}

        for rel in relationships:
            source = str(rel.source_memory_id)
            target = str(rel.target_memory_id)

            # Style based on relationship type
            style_map = {
                "causal": "solid",
                "temporal": "dashed",
                "semantic": "dotted",
                "reference": "solid"
            }

            edge = KnowledgeGraphEdge(
                source=source,
                target=target,
                type=rel.relationship_type,
                weight=weights.get((source, target), 1.0),
                properties={
                    "created_at": rel.created_at.isoformat() if hasattr(rel, 'created_at') else None,
                    "strength": rel.strength
                },
                style=style_map.get(rel.relationship_type, "solid")
            )

            edges.append(edge)

        return edges

    def _calculate_importance_sizes(
        self,
        memories: list[Memory]
    ) -> dict[str, float]:
        """Calculate node sizes based on importance."""
        sizes = {}
        max_importance = max(m.importance for m in memories) if memories else 10

        for memory in memories:
            # Normalize to 0.5-2.0 range
            normalized = (memory.importance / max_importance) * 1.5 + 0.5
            sizes[str(memory.id)] = normalized

        return sizes

    def _calculate_connection_sizes(
        self,
        graph: nx.Graph
    ) -> dict[str, float]:
        """Calculate node sizes based on connections."""
        sizes = {}
        degrees = dict(graph.degree())
        max_degree = max(degrees.values()) if degrees else 1

        for node, degree in degrees.items():
            # Normalize to 0.5-2.0 range
            normalized = (degree / max_degree) * 1.5 + 0.5
            sizes[node] = normalized

        return sizes

    # Layout Algorithms

    def _force_directed_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply force-directed layout."""
        # Use NetworkX spring layout
        pos = nx.spring_layout(
            nx_graph,
            k=1/np.sqrt(len(nodes)) if nodes else 1,
            iterations=50,
            scale=1000
        )

        # Update node positions
        for node in nodes:
            if node.id in pos:
                node.x = float(pos[node.id][0])
                node.y = float(pos[node.id][1])

        return nodes

    def _hierarchical_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply hierarchical layout."""
        # Create directed graph for hierarchy
        di_graph = nx.DiGraph()
        for edge in edges:
            di_graph.add_edge(edge.source, edge.target)

        # Find root nodes (no incoming edges)
        roots = [n for n in di_graph.nodes() if di_graph.in_degree(n) == 0]

        if not roots:
            # Fall back to force-directed if no clear hierarchy
            return self._force_directed_layout(nodes, edges, nx_graph, request)

        # Use graphviz-style hierarchical layout
        # Simple level-based layout
        levels = {}
        for root in roots:
            levels[root] = 0

        # BFS to assign levels
        queue = list(roots)
        while queue:
            node = queue.pop(0)
            current_level = levels.get(node, 0)

            for successor in di_graph.successors(node):
                if successor not in levels:
                    levels[successor] = current_level + 1
                    queue.append(successor)

        # Position nodes by level
        level_counts = defaultdict(int)
        for node in nodes:
            level = levels.get(node.id, 0)
            level_counts[level] += 1

        level_positions = defaultdict(int)
        for node in nodes:
            level = levels.get(node.id, 0)
            count = level_counts[level]
            pos = level_positions[level]

            # Calculate position
            node.y = -level * 200  # Vertical spacing
            node.x = (pos - count/2) * 150  # Horizontal spacing

            level_positions[level] += 1

        return nodes

    def _circular_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply circular layout."""
        # Use NetworkX circular layout
        pos = nx.circular_layout(nx_graph, scale=500)

        # Update node positions
        for node in nodes:
            if node.id in pos:
                node.x = float(pos[node.id][0])
                node.y = float(pos[node.id][1])

        return nodes

    def _radial_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply radial layout with central nodes."""
        # Find most connected nodes as centers
        degrees = dict(nx_graph.degree())
        if not degrees:
            return self._circular_layout(nodes, edges, nx_graph, request)

        center_node = max(degrees, key=degrees.get)

        # Use shell layout with center
        shells = [
            [center_node],
            [n for n in nx_graph.neighbors(center_node)],
            [n for n in nx_graph.nodes()
             if n != center_node and n not in nx_graph.neighbors(center_node)]
        ]

        # Remove empty shells
        shells = [s for s in shells if s]

        pos = nx.shell_layout(nx_graph, shells, scale=500)

        # Update node positions
        for node in nodes:
            if node.id in pos:
                node.x = float(pos[node.id][0])
                node.y = float(pos[node.id][1])

        return nodes

    def _timeline_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply timeline layout based on creation dates."""
        # Sort nodes by creation date
        node_dates = []
        for node in nodes:
            date_str = node.properties.get('created_at')
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                node_dates.append((node, date))

        if not node_dates:
            return self._force_directed_layout(nodes, edges, nx_graph, request)

        # Sort by date
        node_dates.sort(key=lambda x: x[1])

        # Calculate time range
        min_date = node_dates[0][1]
        max_date = node_dates[-1][1]
        time_range = (max_date - min_date).total_seconds()

        if time_range == 0:
            time_range = 1  # Avoid division by zero

        # Position nodes along timeline
        for i, (node, date) in enumerate(node_dates):
            # X position based on time
            time_offset = (date - min_date).total_seconds()
            node.x = (time_offset / time_range) * 1000 - 500

            # Y position with some variation to avoid overlap
            node.y = (i % 5) * 50 - 100

        return nodes

    def _clustered_layout(
        self,
        nodes: list[KnowledgeGraphNode],
        edges: list[KnowledgeGraphEdge],
        nx_graph: nx.Graph,
        request: GraphVisualizationRequest
    ) -> list[KnowledgeGraphNode]:
        """Apply clustered layout."""
        # Detect communities
        import community as community_louvain
        partition = community_louvain.best_partition(nx_graph)

        # Group nodes by cluster
        clusters = defaultdict(list)
        for node_id, cluster_id in partition.items():
            clusters[cluster_id].append(node_id)

        # Position clusters in a grid
        n_clusters = len(clusters)
        grid_size = int(np.ceil(np.sqrt(n_clusters)))

        all_pos = {}
        for i, (cluster_id, cluster_nodes) in enumerate(clusters.items()):
            # Calculate cluster center
            row = i // grid_size
            col = i % grid_size
            center_x = col * 300 - (grid_size - 1) * 150
            center_y = row * 300 - (grid_size - 1) * 150

            # Create subgraph for cluster
            subgraph = nx_graph.subgraph(cluster_nodes)

            # Layout cluster nodes
            if len(cluster_nodes) > 1:
                sub_pos = nx.spring_layout(subgraph, scale=100)

                # Offset by cluster center
                for node_id, pos in sub_pos.items():
                    all_pos[node_id] = (
                        pos[0] + center_x,
                        pos[1] + center_y
                    )
            else:
                all_pos[cluster_nodes[0]] = (center_x, center_y)

        # Update node positions
        for node in nodes:
            if node.id in all_pos:
                node.x = float(all_pos[node.id][0])
                node.y = float(all_pos[node.id][1])

        return nodes

    # Color Schemes

    def _default_colors(
        self,
        nodes: list[KnowledgeGraphNode],
        memories: list[Memory],
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Apply default color scheme."""
        type_colors = {
            "episodic": "#FF6B6B",
            "semantic": "#4ECDC4",
            "procedural": "#45B7D1",
            "question": "#FFA07A",
            "reflection": "#98D8C8"
        }

        for node in nodes:
            memory_type = node.properties.get('memory_type', 'semantic')
            node.color = type_colors.get(memory_type, "#95A5A6")

        return nodes

    def _importance_colors(
        self,
        nodes: list[KnowledgeGraphNode],
        memories: list[Memory],
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Color nodes by importance."""
        for node in nodes:
            importance = node.properties.get('importance', 5)

            # Gradient from blue (low) to red (high)
            normalized = importance / 10.0
            red = int(255 * normalized)
            blue = int(255 * (1 - normalized))
            node.color = f"#{red:02x}00{blue:02x}"

        return nodes

    def _type_colors(
        self,
        nodes: list[KnowledgeGraphNode],
        memories: list[Memory],
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Color nodes by type."""
        # Same as default for now
        return self._default_colors(nodes, memories, clusters)

    def _age_colors(
        self,
        nodes: list[KnowledgeGraphNode],
        memories: list[Memory],
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Color nodes by age."""
        # Find date range
        dates = []
        for node in nodes:
            date_str = node.properties.get('created_at')
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                dates.append(date)

        if not dates:
            return nodes

        min_date = min(dates)
        max_date = max(dates)
        date_range = (max_date - min_date).total_seconds()

        if date_range == 0:
            date_range = 1

        for node in nodes:
            date_str = node.properties.get('created_at')
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                age_normalized = (date - min_date).total_seconds() / date_range

                # Gradient from green (new) to gray (old)
                green = int(255 * (1 - age_normalized))
                gray = int(128 + 127 * age_normalized)
                node.color = f"#{gray:02x}{green:02x}{gray:02x}"

        return nodes

    def _cluster_colors(
        self,
        nodes: list[KnowledgeGraphNode],
        memories: list[Memory],
        clusters: Optional[list[list[str]]]
    ) -> list[KnowledgeGraphNode]:
        """Color nodes by cluster."""
        if not clusters:
            return self._default_colors(nodes, memories, clusters)

        # Create color palette
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
            "#98D8C8", "#FFEAA7", "#DDA0DD", "#98FB98",
            "#F0E68C", "#87CEEB"
        ]

        # Map nodes to clusters
        node_cluster_map = {}
        for i, cluster in enumerate(clusters):
            color = colors[i % len(colors)]
            for node_id in cluster:
                node_cluster_map[node_id] = color

        # Apply colors
        for node in nodes:
            node.color = node_cluster_map.get(node.id, "#95A5A6")

        return nodes
