"""
Memory Visualization Engine for Interactive Memory Exploration.
Provides graph data generation, relationship extraction, and semantic clustering.
"""

import json
from app.utils.logging_config import get_logger
from typing import Any
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
logger = get_logger(__name__)


class MemoryVisualizationEngine:
    """Advanced memory visualization engine with graph generation and relationship analysis."""

    def __init__(self, database=None):
        self.database = database
        self.similarity_threshold = 0.7  # Threshold for creating edges between memories
        self.max_nodes = 500  # Maximum nodes to include in visualization
        self.cluster_algorithms = {
            "kmeans": self._cluster_kmeans,
            "dbscan": self._cluster_dbscan,
            "semantic": self._cluster_semantic,
        }

    async def generate_memory_graph(
        self,
        memory_types: list[str] | None = None,
        importance_threshold: float = 0.3,
        time_range_days: int | None = None,
        max_nodes: int | None = None,
        include_relationships: bool = True,
        cluster_method: str = "semantic",
    ) -> dict[str, Any]:
        """
        Generate interactive memory graph data with nodes, edges, and clusters.

        Args:
            memory_types: Filter by memory types ['semantic', 'episodic', 'procedural']
            importance_threshold: Minimum importance score for inclusion
            time_range_days: Include memories from last N days only
            max_nodes: Maximum number of nodes (default: self.max_nodes)
            include_relationships: Whether to compute similarity relationships
            cluster_method: Clustering algorithm ('kmeans', 'dbscan', 'semantic')

        Returns:
            Graph data structure with nodes, edges, clusters, and metadata
        """
        db = self.database or await get_database()
        max_nodes = max_nodes or self.max_nodes

        # Build query filters
        query_filters = ["embedding IS NOT NULL"]
        params = []

        if memory_types:
            params.append(memory_types)
            query_filters.append(f"memory_type = ANY(${len(params)})")

        if importance_threshold is not None:
            params.append(importance_threshold)
            query_filters.append(f"importance_score >= ${len(params)}")

        if time_range_days:
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
            params.append(cutoff_date)
            query_filters.append(f"created_at >= ${len(params)}")

        where_clause = " AND ".join(query_filters)

        # Fetch memories with embeddings
        query = f"""
            SELECT id, content, memory_type, importance_score,
                   semantic_metadata, episodic_metadata, procedural_metadata,
                   embedding, created_at, updated_at
            FROM memories
            WHERE {where_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ${len(params) + 1}
        """
        params.append(max_nodes)

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return self._empty_graph()

        # Convert to memory objects
        memories = []
        embeddings = []

        for row in rows:
            memory_data = {
                "id": str(row["id"]),
                "content": row["content"],
                "memory_type": row["memory_type"],
                "importance_score": float(row["importance_score"]),
                "semantic_metadata": row["semantic_metadata"] or {},
                "episodic_metadata": row["episodic_metadata"] or {},
                "procedural_metadata": row["procedural_metadata"] or {},
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            memories.append(memory_data)

            # Parse embedding vector
            if row["embedding"]:
                embedding_str = str(row["embedding"])
                # Remove brackets and split
                embedding_values = [float(x.strip()) for x in embedding_str.strip("[]").split(",")]
                embeddings.append(embedding_values)
            else:
                embeddings.append([0.0] * 1536)  # Default embedding size

        # Generate graph components
        nodes = await self._generate_nodes(memories, embeddings)
        edges = []
        clusters = []

        if include_relationships and len(embeddings) > 1:
            edges = await self._generate_edges(memories, embeddings)

        if len(memories) > 2:
            clusters = await self._generate_clusters(memories, embeddings, cluster_method)

        # Calculate graph statistics
        stats = self._calculate_graph_stats(nodes, edges, clusters)

        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "metadata": {
                "total_memories": len(memories),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "cluster_count": len(clusters),
                "generated_at": datetime.now().isoformat(),
                "filters": {
                    "memory_types": memory_types,
                    "importance_threshold": importance_threshold,
                    "time_range_days": time_range_days,
                    "cluster_method": cluster_method,
                },
                "statistics": stats,
            },
        }

    async def _generate_nodes(self, memories: list[dict], embeddings: list[list[float]]) -> list[dict[str, Any]]:
        """Generate node data for visualization."""
        if not embeddings:
            return []

        # Reduce dimensionality for 2D positioning
        positions = await self._calculate_2d_positions(embeddings)

        nodes = []
        for i, memory in enumerate(memories):
            # Calculate node size based on importance and content length
            base_size = 5
            importance_factor = memory["importance_score"] * 15
            content_factor = min(len(memory["content"]) / 100, 10)
            node_size = base_size + importance_factor + content_factor

            # Determine node color based on memory type
            color_map = {
                "semantic": "#3498db",  # Blue
                "episodic": "#e74c3c",  # Red
                "procedural": "#2ecc71",  # Green
            }
            node_color = color_map.get(memory["memory_type"], "#95a5a6")

            # Extract key topics from metadata
            topics = self._extract_topics(memory)

            node = {
                "id": memory["id"],
                "label": memory["content"][:50] + ("..." if len(memory["content"]) > 50 else ""),
                "full_content": memory["content"],
                "memory_type": memory["memory_type"],
                "importance_score": memory["importance_score"],
                "topics": topics,
                "created_at": memory["created_at"],
                "updated_at": memory["updated_at"],
                "position": {"x": float(positions[i][0]), "y": float(positions[i][1])},
                "style": {
                    "size": node_size,
                    "color": node_color,
                    "opacity": 0.8,
                    "border_width": 2,
                    "border_color": "#34495e",
                },
                "metadata": {
                    "semantic": memory["semantic_metadata"],
                    "episodic": memory["episodic_metadata"],
                    "procedural": memory["procedural_metadata"],
                },
            }
            nodes.append(node)

        return nodes

    async def _generate_edges(self, memories: list[dict], embeddings: list[list[float]]) -> list[dict[str, Any]]:
        """Generate edge data based on semantic similarity."""
        if len(embeddings) < 2:
            return []

        # Calculate cosine similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        edges = []

        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                similarity = similarity_matrix[i][j]

                # Only create edge if similarity exceeds threshold
                if similarity >= self.similarity_threshold:
                    # Edge weight and style based on similarity strength
                    edge_weight = float(similarity)
                    edge_width = 1 + (similarity - self.similarity_threshold) * 5
                    edge_opacity = 0.3 + (similarity - self.similarity_threshold) * 0.7

                    # Determine edge color based on relationship type
                    edge_color = self._determine_edge_color(memories[i], memories[j], similarity)

                    edge = {
                        "id": f"{memories[i]['id']}-{memories[j]['id']}",
                        "source": memories[i]["id"],
                        "target": memories[j]["id"],
                        "weight": edge_weight,
                        "similarity": similarity,
                        "relationship_type": self._classify_relationship(memories[i], memories[j]),
                        "style": {
                            "width": edge_width,
                            "color": edge_color,
                            "opacity": edge_opacity,
                            "curve": "straight",
                        },
                    }
                    edges.append(edge)

        return edges

    async def _generate_clusters(
        self, memories: list[dict], embeddings: list[list[float]], method: str
    ) -> list[dict[str, Any]]:
        """Generate clusters using specified clustering algorithm."""
        if len(embeddings) < 3:
            return []

        cluster_func = self.cluster_algorithms.get(method, self._cluster_semantic)
        cluster_labels = await cluster_func(embeddings, memories)

        # Group memories by cluster
        clusters_dict = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            if label != -1:  # -1 indicates noise in DBSCAN
                clusters_dict[label].append((i, memories[i]))

        clusters = []
        for cluster_id, cluster_memories in clusters_dict.items():
            if len(cluster_memories) < 2:
                continue

            # Calculate cluster center and properties
            indices = [idx for idx, _ in cluster_memories]
            cluster_embeddings = [embeddings[idx] for idx in indices]
            cluster_center = np.mean(cluster_embeddings, axis=0)

            # Find most representative memory (closest to center)
            distances = [np.linalg.norm(emb - cluster_center) for emb in cluster_embeddings]
            representative_idx = indices[np.argmin(distances)]
            representative = memories[representative_idx]

            # Extract common topics
            all_topics = []
            for _, memory in cluster_memories:
                all_topics.extend(self._extract_topics(memory))
            common_topics = self._find_common_topics(all_topics)

            # Calculate cluster importance (average of member importance)
            avg_importance = np.mean([mem["importance_score"] for _, mem in cluster_memories])

            cluster = {
                "id": f"cluster_{cluster_id}",
                "label": self._generate_cluster_label(common_topics, representative),
                "size": len(cluster_memories),
                "importance": float(avg_importance),
                "topics": common_topics[:5],  # Top 5 topics
                "representative": representative["id"],
                "members": [mem["id"] for _, mem in cluster_memories],
                "center": {
                    "x": float(
                        np.mean(
                            [pos[0] for pos in await self._calculate_2d_positions([embeddings[idx] for idx in indices])]
                        )
                    ),
                    "y": float(
                        np.mean(
                            [pos[1] for pos in await self._calculate_2d_positions([embeddings[idx] for idx in indices])]
                        )
                    ),
                },
                "style": {
                    "color": self._generate_cluster_color(cluster_id),
                    "opacity": 0.2,
                    "border_color": self._generate_cluster_color(cluster_id),
                    "border_width": 2,
                },
            }
            clusters.append(cluster)

        return clusters

    async def _calculate_2d_positions(self, embeddings: list[list[float]]) -> list[tuple[float, float]]:
        """Calculate 2D positions for nodes using PCA dimensionality reduction."""
        if len(embeddings) == 1:
            return [(0.0, 0.0)]

        # Use PCA to reduce to 2D
        pca = PCA(n_components=2, random_state=42)
        positions_2d = pca.fit_transform(embeddings)

        # Normalize to reasonable coordinate range
        min_val, max_val = positions_2d.min(), positions_2d.max()
        if max_val > min_val:
            positions_2d = (positions_2d - min_val) / (max_val - min_val) * 1000 - 500

        return [(float(pos[0]), float(pos[1])) for pos in positions_2d]

    async def _cluster_kmeans(self, embeddings: list[list[float]], memories: list[dict]) -> list[int]:
        """K-means clustering based on embeddings."""
        n_clusters = min(8, max(2, len(embeddings) // 10))  # Adaptive cluster count
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        return kmeans.fit_predict(embeddings).tolist()

    async def _cluster_dbscan(self, embeddings: list[list[float]], memories: list[dict]) -> list[int]:
        """DBSCAN clustering for density-based grouping."""
        # Adaptive eps based on embedding dimensionality
        eps = 0.5 if len(embeddings[0]) > 100 else 0.3
        min_samples = max(2, len(embeddings) // 20)

        dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
        return dbscan.fit_predict(embeddings).tolist()

    async def _cluster_semantic(self, embeddings: list[list[float]], memories: list[dict]) -> list[int]:
        """Semantic clustering based on content analysis and memory types."""
        # Combine embedding similarity with semantic features
        labels = []
        clusters = {}
        current_label = 0

        for _i, memory in enumerate(memories):
            assigned = False
            memory_topics = set(self._extract_topics(memory))
            memory_type = memory["memory_type"]

            # Check existing clusters
            for label, cluster_info in clusters.items():
                cluster_topics = cluster_info["topics"]
                cluster_type = cluster_info["type"]

                # Semantic similarity criteria
                topic_overlap = len(memory_topics & cluster_topics) / max(len(memory_topics | cluster_topics), 1)
                type_match = memory_type == cluster_type

                if topic_overlap > 0.3 and type_match:
                    labels.append(label)
                    clusters[label]["topics"].update(memory_topics)
                    assigned = True
                    break

            if not assigned:
                labels.append(current_label)
                clusters[current_label] = {"topics": memory_topics, "type": memory_type}
                current_label += 1

        return labels

    def _extract_topics(self, memory: dict) -> list[str]:
        """Extract topics/keywords from memory content and metadata."""
        topics = []

        # Extract from content (simple keyword extraction)
        content_words = memory["content"].lower().split()
        # Filter for meaningful words (length > 3, not common words)
        stopwords = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "new",
            "now",
            "old",
            "see",
            "two",
            "way",
            "who",
            "boy",
            "did",
            "man",
            "end",
            "few",
            "got",
            "lot",
            "may",
            "say",
            "she",
            "use",
            "own",
            "too",
            "any",
            "oil",
            "sit",
            "set",
            "run",
            "eat",
            "far",
            "sea",
            "eye",
            "ask",
            "try",
            "let",
        }
        meaningful_words = [word for word in content_words if len(word) > 3 and word not in stopwords]
        topics.extend(meaningful_words[:5])  # Top 5 content keywords

        # Extract from metadata
        for metadata_type in ["semantic_metadata", "episodic_metadata", "procedural_metadata"]:
            metadata = memory.get(metadata_type, {})
            if isinstance(metadata, dict):
                for _key, value in metadata.items():
                    if isinstance(value, str) and len(value) > 2:
                        topics.append(value.lower())
                    elif isinstance(value, list):
                        topics.extend([str(v).lower() for v in value if len(str(v)) > 2])

        return list(set(topics))  # Remove duplicates

    def _find_common_topics(self, all_topics: list[str]) -> list[str]:
        """Find most common topics across a collection."""
        topic_counts = defaultdict(int)
        for topic in all_topics:
            topic_counts[topic] += 1

        # Sort by frequency and return top topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics if count > 1]

    def _generate_cluster_label(self, topics: list[str], representative: dict) -> str:
        """Generate a descriptive label for a cluster."""
        if topics:
            return f"{topics[0].title()} Cluster"
        return f"{representative['memory_type'].title()} Memory Group"

    def _generate_cluster_color(self, cluster_id: int) -> str:
        """Generate a consistent color for a cluster."""
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF", "#5F27CD"]
        return colors[cluster_id % len(colors)]

    def _determine_edge_color(self, memory1: dict, memory2: dict, similarity: float) -> str:
        """Determine edge color based on relationship characteristics."""
        # Same memory type = blue, different = purple, high similarity = green
        if memory1["memory_type"] == memory2["memory_type"]:
            if similarity > 0.85:
                return "#2ecc71"  # Green for strong same-type connections
            return "#3498db"  # Blue for same-type connections
        return "#9b59b6"  # Purple for cross-type connections

    def _classify_relationship(self, memory1: dict, memory2: dict) -> str:
        """Classify the relationship type between two memories."""
        if memory1["memory_type"] == memory2["memory_type"]:
            return f"same_type_{memory1['memory_type']}"
        return f"cross_type_{memory1['memory_type']}_{memory2['memory_type']}"

    def _calculate_graph_stats(self, nodes: list[dict], edges: list[dict], clusters: list[dict]) -> dict[str, Any]:
        """Calculate graph statistics and metrics."""
        if not nodes:
            return {}

        # Node statistics
        importance_scores = [node["importance_score"] for node in nodes]
        memory_types = [node["memory_type"] for node in nodes]

        # Edge statistics
        similarities = [edge["similarity"] for edge in edges] if edges else []

        # Cluster statistics
        cluster_sizes = [cluster["size"] for cluster in clusters]

        return {
            "nodes": {
                "total": len(nodes),
                "avg_importance": np.mean(importance_scores) if importance_scores else 0,
                "memory_type_distribution": {t: memory_types.count(t) for t in set(memory_types)},
            },
            "edges": {
                "total": len(edges),
                "avg_similarity": np.mean(similarities) if similarities else 0,
                "max_similarity": max(similarities) if similarities else 0,
                "min_similarity": min(similarities) if similarities else 0,
            },
            "clusters": {
                "total": len(clusters),
                "avg_size": np.mean(cluster_sizes) if cluster_sizes else 0,
                "largest_cluster": max(cluster_sizes) if cluster_sizes else 0,
            },
        }

    def _empty_graph(self) -> dict[str, Any]:
        """Return empty graph structure."""
        return {
            "nodes": [],
            "edges": [],
            "clusters": [],
            "metadata": {
                "total_memories": 0,
                "node_count": 0,
                "edge_count": 0,
                "cluster_count": 0,
                "generated_at": datetime.now().isoformat(),
                "statistics": {},
            },
        }


class AdvancedSearchEngine:
    """Advanced search engine with multi-dimensional search capabilities."""

    def __init__(self, database=None):
        self.database = database

    async def advanced_search(
        self,
        query: str,
        search_type: str = "hybrid",  # semantic, temporal, importance, hybrid
        memory_types: list[str] | None = None,
        importance_range: tuple[float, float] | None = None,
        date_range: tuple[str, str] | None = None,
        topic_filters: list[str] | None = None,
        limit: int = 50,
        include_clusters: bool = True,
        include_relationships: bool = True,
    ) -> dict[str, Any]:
        """
        Perform advanced multi-dimensional search with clustering and relationships.

        Args:
            query: Search query text
            search_type: Type of search (semantic, temporal, importance, hybrid)
            memory_types: Filter by memory types
            importance_range: Min/max importance scores (0.0 - 1.0)
            date_range: ISO date strings (start, end)
            topic_filters: Filter by topics/keywords
            limit: Maximum results
            include_clusters: Include cluster analysis
            include_relationships: Include relationship analysis

        Returns:
            Advanced search results with clusters and relationships
        """
        db = self.database or await get_database()

        # Build search query based on type
        if search_type == "semantic":
            results = await self._semantic_search(db, query, memory_types, limit)
        elif search_type == "temporal":
            results = await self._temporal_search(db, query, date_range, limit)
        elif search_type == "importance":
            results = await self._importance_search(db, query, importance_range, limit)
        else:  # hybrid
            results = await self._hybrid_search(db, query, memory_types, importance_range, date_range, limit)

        # Apply additional filters
        if topic_filters:
            results = self._filter_by_topics(results, topic_filters)

        # Add cluster analysis
        clusters = []
        if include_clusters and len(results) > 2:
            viz_engine = MemoryVisualizationEngine(db)
            embeddings = [result.get("embedding", []) for result in results]
            valid_embeddings = [emb for emb in embeddings if emb]

            if valid_embeddings:
                cluster_labels = await viz_engine._cluster_semantic(valid_embeddings, results)
                clusters = self._build_result_clusters(results, cluster_labels)

        # Add relationship analysis
        relationships = []
        if include_relationships and len(results) > 1:
            relationships = await self._analyze_result_relationships(results)

        # Calculate search analytics
        analytics = self._calculate_search_analytics(query, results, clusters, relationships)

        return {
            "query": query,
            "search_type": search_type,
            "results": results,
            "clusters": clusters,
            "relationships": relationships,
            "metadata": {
                "total_results": len(results),
                "cluster_count": len(clusters),
                "relationship_count": len(relationships),
                "search_timestamp": datetime.now().isoformat(),
                "filters_applied": {
                    "memory_types": memory_types,
                    "importance_range": importance_range,
                    "date_range": date_range,
                    "topic_filters": topic_filters,
                },
                "analytics": analytics,
            },
        }

    async def _semantic_search(self, db, query: str, memory_types: list[str] | None, limit: int) -> list[dict]:
        """Semantic similarity search using embeddings."""
        return await db.contextual_search(query=query, limit=limit, memory_types=memory_types)

    async def _temporal_search(self, db, query: str, date_range: tuple[str, str] | None, limit: int) -> list[dict]:
        """Temporal search focusing on time-based patterns."""
        timeframe = None
        if date_range:
            start_date, end_date = date_range
            # Convert to days for timeframe parameter
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            timeframe = f"{start.isoformat()},{end.isoformat()}"

        return await db.contextual_search(query=query, limit=limit, timeframe=timeframe)

    async def _importance_search(
        self, db, query: str, importance_range: tuple[float, float] | None, limit: int
    ) -> list[dict]:
        """Search focusing on importance-weighted results."""
        importance_threshold = importance_range[0] if importance_range else 0.5

        return await db.contextual_search(query=query, limit=limit, importance_threshold=importance_threshold)

    async def _hybrid_search(
        self,
        db,
        query: str,
        memory_types: list[str] | None,
        importance_range: tuple[float, float] | None,
        date_range: tuple[str, str] | None,
        limit: int,
    ) -> list[dict]:
        """Hybrid search combining multiple dimensions."""
        importance_threshold = importance_range[0] if importance_range else None

        timeframe = None
        if date_range:
            start_date, end_date = date_range
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            timeframe = f"{start.isoformat()},{end.isoformat()}"

        return await db.contextual_search(
            query=query,
            limit=limit,
            memory_types=memory_types,
            importance_threshold=importance_threshold,
            timeframe=timeframe,
        )

    def _filter_by_topics(self, results: list[dict], topic_filters: list[str]) -> list[dict]:
        """Filter results by topic keywords."""
        filtered_results = []
        topic_filters_lower = [topic.lower() for topic in topic_filters]

        for result in results:
            content_lower = result.get("content", "").lower()
            metadata_str = json.dumps(result.get("metadata", {})).lower()

            # Check if any topic filter matches content or metadata
            if any(topic in content_lower or topic in metadata_str for topic in topic_filters_lower):
                filtered_results.append(result)

        return filtered_results

    def _build_result_clusters(self, results: list[dict], cluster_labels: list[int]) -> list[dict]:
        """Build clusters from search results."""
        clusters_dict = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            if label != -1 and i < len(results):
                clusters_dict[label].append(results[i])

        clusters = []
        for cluster_id, cluster_results in clusters_dict.items():
            if len(cluster_results) > 1:
                cluster = {
                    "id": f"search_cluster_{cluster_id}",
                    "size": len(cluster_results),
                    "results": cluster_results,
                    "common_themes": self._extract_common_themes(cluster_results),
                    "avg_importance": np.mean([r.get("importance_score", 0) for r in cluster_results]),
                }
                clusters.append(cluster)

        return clusters

    async def _analyze_result_relationships(self, results: list[dict]) -> list[dict]:
        """Analyze relationships between search results."""
        relationships = []

        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                relationship = self._calculate_relationship(results[i], results[j])
                if relationship["strength"] > 0.3:  # Only significant relationships
                    relationships.append(relationship)

        return sorted(relationships, key=lambda x: x["strength"], reverse=True)[:20]  # Top 20

    def _calculate_relationship(self, result1: dict, result2: dict) -> dict:
        """Calculate relationship strength between two results."""
        # Simple relationship calculation based on content similarity and metadata
        content1 = result1.get("content", "").lower()
        content2 = result2.get("content", "").lower()

        # Word overlap ratio
        words1 = set(content1.split())
        words2 = set(content2.split())
        overlap_ratio = len(words1 & words2) / max(len(words1 | words2), 1)

        # Memory type similarity
        type_similarity = 1.0 if result1.get("memory_type") == result2.get("memory_type") else 0.5

        # Combine factors
        strength = (overlap_ratio * 0.7) + (type_similarity * 0.3)

        return {
            "source_id": result1.get("id"),
            "target_id": result2.get("id"),
            "strength": strength,
            "type": "content_similarity",
            "overlap_ratio": overlap_ratio,
        }

    def _extract_common_themes(self, results: list[dict]) -> list[str]:
        """Extract common themes from a group of results."""
        all_words = []
        for result in results:
            content = result.get("content", "").lower()
            words = [word for word in content.split() if len(word) > 3]
            all_words.extend(words)

        # Count word frequency
        word_counts = defaultdict(int)
        for word in all_words:
            word_counts[word] += 1

        # Return most common words that appear in multiple results
        threshold = max(1, len(results) // 2)  # Must appear in at least half the results
        common_themes = [word for word, count in word_counts.items() if count >= threshold]

        return sorted(common_themes, key=lambda x: word_counts[x], reverse=True)[:5]

    def _calculate_search_analytics(
        self, query: str, results: list[dict], clusters: list[dict], relationships: list[dict]
    ) -> dict:
        """Calculate search performance analytics."""
        if not results:
            return {}

        # Result distribution by memory type
        memory_types = [result.get("memory_type", "unknown") for result in results]
        type_distribution = {t: memory_types.count(t) for t in set(memory_types)}

        # Importance score statistics
        importance_scores = [result.get("importance_score", 0) for result in results]

        # Similarity scores if available
        similarity_scores = [result.get("similarity", 0) for result in results if result.get("similarity")]

        return {
            "query_length": len(query),
            "result_distribution": type_distribution,
            "importance_stats": {
                "avg": np.mean(importance_scores) if importance_scores else 0,
                "max": max(importance_scores) if importance_scores else 0,
                "min": min(importance_scores) if importance_scores else 0,
            },
            "similarity_stats": {
                "avg": np.mean(similarity_scores) if similarity_scores else 0,
                "max": max(similarity_scores) if similarity_scores else 0,
                "min": min(similarity_scores) if similarity_scores else 0,
            }
            if similarity_scores
            else {},
            "clustering_efficiency": len(clusters) / max(len(results), 1),
            "relationship_density": len(relationships) / max((len(results) * (len(results) - 1)) // 2, 1),
        }
