"""
Advanced Memory Relationship System.
Analyzes and manages complex relationships between memories including semantic similarity,
temporal connections, causal relationships, and conceptual hierarchies.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemoryRelationshipAnalyzer:
    """Advanced analyzer for detecting and quantifying relationships between memories."""

    def __init__(self, database=None):
        self.database = database
        self.relationship_types = {
            "semantic_similarity": self._calculate_semantic_similarity,
            "temporal_proximity": self._calculate_temporal_proximity,
            "content_overlap": self._calculate_content_overlap,
            "conceptual_hierarchy": self._calculate_conceptual_hierarchy,
            "causal_relationship": self._detect_causal_relationship,
            "contextual_association": self._calculate_contextual_association,
        }
        self.similarity_threshold = 0.3
        self.temporal_window_hours = 24

    async def analyze_memory_relationships(
        self, memory_id: str, relationship_types: list[str] | None = None, depth: int = 2, max_connections: int = 50
    ) -> dict[str, Any]:
        """
        Perform comprehensive relationship analysis for a specific memory.

        Args:
            memory_id: Target memory UUID
            relationship_types: Types of relationships to analyze
            depth: Depth of relationship traversal (1-3)
            max_connections: Maximum connections to analyze

        Returns:
            Comprehensive relationship analysis results
        """
        db = self.database or await get_database()

        # Get target memory
        async with db.pool.acquire() as conn:
            target_memory = await conn.fetchrow(
                """
                SELECT id, content, embedding, memory_type, importance_score,
                       semantic_metadata, episodic_metadata, procedural_metadata,
                       created_at, updated_at
                FROM memories
                WHERE id = $1
            """,
                memory_id,
            )

            if not target_memory:
                raise ValueError(f"Memory {memory_id} not found")

            # Get candidate memories for relationship analysis
            candidate_memories = await conn.fetch(
                """
                SELECT id, content, embedding, memory_type, importance_score,
                       semantic_metadata, episodic_metadata, procedural_metadata,
                       created_at, updated_at
                FROM memories
                WHERE id != $1 AND embedding IS NOT NULL
                ORDER BY importance_score DESC, created_at DESC
                LIMIT $2
            """,
                memory_id,
                max_connections * 3,
            )  # Get more candidates for filtering

        if not candidate_memories:
            return self._empty_relationship_analysis(memory_id)

        # Analyze relationships
        relationships = await self._analyze_relationships_batch(
            target_memory, candidate_memories, relationship_types or list(self.relationship_types.keys())
        )

        # Filter and rank relationships
        significant_relationships = self._filter_significant_relationships(relationships, max_connections)

        # Perform multi-level analysis if depth > 1
        extended_network = {}
        if depth > 1:
            extended_network = await self._analyze_extended_network(
                significant_relationships, depth - 1, max_connections // 2
            )

        # Generate relationship insights
        insights = self._generate_relationship_insights(significant_relationships, extended_network)

        # Calculate network metrics
        network_metrics = self._calculate_network_metrics(significant_relationships, extended_network)

        return {
            "target_memory": {
                "id": str(target_memory["id"]),
                "content_preview": target_memory["content"][:100],
                "memory_type": target_memory["memory_type"],
                "importance_score": float(target_memory["importance_score"]),
            },
            "direct_relationships": significant_relationships,
            "extended_network": extended_network,
            "insights": insights,
            "network_metrics": network_metrics,
            "metadata": {
                "analysis_depth": depth,
                "total_relationships": len(significant_relationships),
                "network_size": len(extended_network),
                "analyzed_at": datetime.now().isoformat(),
                "relationship_types_analyzed": relationship_types or list(self.relationship_types.keys()),
            },
        }

    async def discover_memory_clusters(
        self,
        memory_types: list[str] | None = None,
        clustering_method: str = "hierarchical",
        min_cluster_size: int = 3,
        max_clusters: int = 20,
    ) -> dict[str, Any]:
        """
        Discover natural clusters in the memory space using relationship analysis.

        Args:
            memory_types: Filter by memory types
            clustering_method: 'hierarchical', 'community', or 'semantic'
            min_cluster_size: Minimum memories per cluster
            max_clusters: Maximum number of clusters

        Returns:
            Cluster analysis with relationship patterns
        """
        db = self.database or await get_database()

        # Build query filters
        query_filters = ["embedding IS NOT NULL"]
        params = []

        if memory_types:
            params.append(memory_types)
            query_filters.append(f"memory_type = ANY(${len(params)})")

        where_clause = " AND ".join(query_filters)

        # Get memories for clustering
        query = f"""
            SELECT id, content, embedding, memory_type, importance_score,
                   semantic_metadata, episodic_metadata, procedural_metadata,
                   created_at
            FROM memories
            WHERE {where_clause}
            ORDER BY importance_score DESC
            LIMIT 200
        """

        async with db.pool.acquire() as conn:
            memories = await conn.fetch(query, *params)

        if len(memories) < min_cluster_size * 2:
            return self._empty_cluster_analysis()

        # Perform clustering based on method
        if clustering_method == "hierarchical":
            clusters = await self._hierarchical_clustering(memories, min_cluster_size, max_clusters)
        elif clustering_method == "community":
            clusters = await self._community_detection_clustering(memories, min_cluster_size)
        else:  # semantic
            clusters = await self._semantic_clustering(memories, min_cluster_size, max_clusters)

        # Analyze intra-cluster relationships
        cluster_relationships = await self._analyze_cluster_relationships(clusters, memories)

        # Generate cluster insights
        cluster_insights = self._generate_cluster_insights(clusters, cluster_relationships)

        return {
            "clusters": clusters,
            "cluster_relationships": cluster_relationships,
            "insights": cluster_insights,
            "metadata": {
                "clustering_method": clustering_method,
                "total_memories": len(memories),
                "cluster_count": len(clusters),
                "min_cluster_size": min_cluster_size,
                "analyzed_at": datetime.now().isoformat(),
            },
        }

    async def trace_concept_evolution(
        self, concept_keywords: list[str], time_range_days: int = 90, min_relevance: float = 0.5
    ) -> dict[str, Any]:
        """
        Trace how concepts evolve and relate over time in the memory space.

        Args:
            concept_keywords: Keywords defining the concept
            time_range_days: Time range for analysis
            min_relevance: Minimum relevance threshold

        Returns:
            Temporal evolution analysis of concept relationships
        """
        db = self.database or await get_database()

        # Build concept search query
        concept_pattern = "|".join(concept_keywords)
        cutoff_date = datetime.now() - timedelta(days=time_range_days)

        async with db.pool.acquire() as conn:
            concept_memories = await conn.fetch(
                """
                SELECT id, content, embedding, memory_type, importance_score,
                       created_at, updated_at
                FROM memories
                WHERE (content ~* $1 OR
                       semantic_metadata::text ~* $1 OR
                       episodic_metadata::text ~* $1 OR
                       procedural_metadata::text ~* $1)
                AND created_at >= $2
                AND embedding IS NOT NULL
                ORDER BY created_at ASC
            """,
                concept_pattern,
                cutoff_date,
            )

        if len(concept_memories) < 3:
            return self._empty_evolution_analysis(concept_keywords)

        # Group memories by time periods
        time_periods = self._group_memories_by_time(concept_memories, time_range_days // 7)  # Weekly periods

        # Analyze relationships within and between time periods
        temporal_relationships = await self._analyze_temporal_relationships(time_periods)

        # Calculate concept drift and evolution metrics
        evolution_metrics = self._calculate_evolution_metrics(time_periods, temporal_relationships)

        # Identify key transition points
        transition_points = self._identify_transition_points(time_periods, evolution_metrics)

        # Generate evolution insights
        evolution_insights = self._generate_evolution_insights(
            concept_keywords, time_periods, evolution_metrics, transition_points
        )

        return {
            "concept_keywords": concept_keywords,
            "time_periods": time_periods,
            "temporal_relationships": temporal_relationships,
            "evolution_metrics": evolution_metrics,
            "transition_points": transition_points,
            "insights": evolution_insights,
            "metadata": {
                "time_range_days": time_range_days,
                "total_memories": len(concept_memories),
                "analysis_periods": len(time_periods),
                "analyzed_at": datetime.now().isoformat(),
            },
        }

    async def _analyze_relationships_batch(
        self, target_memory: dict, candidate_memories: list[dict], relationship_types: list[str]
    ) -> list[dict[str, Any]]:
        """Analyze relationships between target memory and candidates."""
        relationships = []

        target_embedding = self._parse_embedding(target_memory["embedding"])
        if not target_embedding:
            return relationships

        for candidate in candidate_memories:
            candidate_embedding = self._parse_embedding(candidate["embedding"])
            if not candidate_embedding:
                continue

            relationship_scores = {}

            # Calculate each requested relationship type
            for rel_type in relationship_types:
                if rel_type in self.relationship_types:
                    score = await self.relationship_types[rel_type](
                        target_memory, candidate, target_embedding, candidate_embedding
                    )
                    relationship_scores[rel_type] = score

            # Calculate composite relationship strength
            composite_score = self._calculate_composite_score(relationship_scores)

            if composite_score > self.similarity_threshold:
                relationship = {
                    "target_id": str(target_memory["id"]),
                    "related_id": str(candidate["id"]),
                    "related_memory": {
                        "content_preview": candidate["content"][:100],
                        "memory_type": candidate["memory_type"],
                        "importance_score": float(candidate["importance_score"]),
                        "created_at": candidate["created_at"].isoformat(),
                    },
                    "relationship_scores": relationship_scores,
                    "composite_score": composite_score,
                    "primary_relationship_type": max(relationship_scores.keys(), key=relationship_scores.get),
                    "strength": self._categorize_strength(composite_score),
                }
                relationships.append(relationship)

        return sorted(relationships, key=lambda x: x["composite_score"], reverse=True)

    async def _calculate_semantic_similarity(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate semantic similarity using embeddings."""
        if not embedding1 or not embedding2:
            return 0.0

        # Cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return max(0.0, similarity)  # Ensure non-negative

    async def _calculate_temporal_proximity(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate temporal proximity score."""
        time1 = memory1["created_at"]
        time2 = memory2["created_at"]

        time_diff = abs((time1 - time2).total_seconds()) / 3600  # Hours

        # Exponential decay with configurable window
        proximity = math.exp(-time_diff / self.temporal_window_hours)
        return proximity

    async def _calculate_content_overlap(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate content overlap using text analysis."""
        content1 = memory1["content"].lower()
        content2 = memory2["content"].lower()

        # Tokenize and find overlap
        words1 = set(content1.split())
        words2 = set(content2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        jaccard_similarity = intersection / union if union > 0 else 0.0
        return jaccard_similarity

    async def _calculate_conceptual_hierarchy(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Detect hierarchical relationships (parent-child, general-specific)."""
        content1 = memory1["content"].lower()
        content2 = memory2["content"].lower()

        # Simple heuristic: check for containment patterns
        hierarchy_indicators = [
            ("definition", "example"),
            ("concept", "instance"),
            ("general", "specific"),
            ("category", "item"),
            ("overview", "detail"),
            ("summary", "elaboration"),
        ]

        hierarchy_score = 0.0

        for parent_word, child_word in hierarchy_indicators:
            if parent_word in content1 and child_word in content2:
                hierarchy_score += 0.3
            elif child_word in content1 and parent_word in content2:
                hierarchy_score += 0.3

        # Check for length-based hierarchy (shorter content might be more general)
        length_ratio = min(len(content1), len(content2)) / max(len(content1), len(content2))
        if length_ratio < 0.5:  # Significant length difference
            hierarchy_score += 0.2

        return min(hierarchy_score, 1.0)

    async def _detect_causal_relationship(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Detect potential causal relationships."""
        content1 = memory1["content"].lower()
        content2 = memory2["content"].lower()

        # Causal indicators
        causal_words = [
            "because",
            "due to",
            "caused by",
            "results in",
            "leads to",
            "triggers",
            "enables",
            "prevents",
            "influences",
            "affects",
            "therefore",
            "consequently",
            "as a result",
            "thus",
        ]

        causal_score = 0.0

        for word in causal_words:
            if word in content1 or word in content2:
                causal_score += 0.2

        # Temporal ordering can indicate causality
        if memory1["created_at"] < memory2["created_at"]:
            causal_score += 0.1  # memory1 might be cause of memory2

        return min(causal_score, 1.0)

    async def _calculate_contextual_association(
        self, memory1: dict, memory2: dict, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate contextual association based on metadata."""
        association_score = 0.0

        # Check metadata overlap
        metadata_fields = ["semantic_metadata", "episodic_metadata", "procedural_metadata"]

        for field in metadata_fields:
            meta1 = memory1.get(field, {}) or {}
            meta2 = memory2.get(field, {}) or {}

            if isinstance(meta1, dict) and isinstance(meta2, dict):
                common_keys = set(meta1.keys()) & set(meta2.keys())
                if common_keys:
                    association_score += 0.3 * len(common_keys) / max(len(meta1), len(meta2), 1)

        # Memory type similarity
        if memory1["memory_type"] == memory2["memory_type"]:
            association_score += 0.2

        # Importance correlation
        importance_diff = abs(memory1["importance_score"] - memory2["importance_score"])
        importance_similarity = 1.0 - importance_diff  # Assumes scores 0-1
        association_score += 0.2 * importance_similarity

        return min(association_score, 1.0)

    def _calculate_composite_score(self, relationship_scores: dict[str, float]) -> float:
        """Calculate weighted composite relationship score."""
        if not relationship_scores:
            return 0.0

        # Weights for different relationship types
        weights = {
            "semantic_similarity": 0.3,
            "temporal_proximity": 0.15,
            "content_overlap": 0.2,
            "conceptual_hierarchy": 0.15,
            "causal_relationship": 0.1,
            "contextual_association": 0.1,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for rel_type, score in relationship_scores.items():
            weight = weights.get(rel_type, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _categorize_strength(self, score: float) -> str:
        """Categorize relationship strength."""
        if score >= 0.8:
            return "very_strong"
        elif score >= 0.6:
            return "strong"
        elif score >= 0.4:
            return "moderate"
        elif score >= 0.2:
            return "weak"
        else:
            return "very_weak"

    def _filter_significant_relationships(self, relationships: list[dict], max_connections: int) -> list[dict]:
        """Filter and rank relationships by significance."""
        # Remove very weak relationships
        filtered = [r for r in relationships if r["composite_score"] > self.similarity_threshold]

        # Sort by composite score and limit
        filtered.sort(key=lambda x: x["composite_score"], reverse=True)

        return filtered[:max_connections]

    async def _analyze_extended_network(
        self, direct_relationships: list[dict], remaining_depth: int, max_connections: int
    ) -> dict[str, Any]:
        """Analyze extended network relationships."""
        if remaining_depth <= 0 or not direct_relationships:
            return {}

        extended_network = {}

        # For each direct relationship, find its relationships
        for relationship in direct_relationships[:10]:  # Limit to prevent explosion
            related_id = relationship["related_id"]

            try:
                sub_analysis = await self.analyze_memory_relationships(
                    related_id, depth=1, max_connections=max_connections // 2
                )

                extended_network[related_id] = {
                    "memory_preview": relationship["related_memory"],
                    "secondary_relationships": sub_analysis["direct_relationships"][:5],  # Limit depth
                    "relationship_count": len(sub_analysis["direct_relationships"]),
                }

            except Exception as e:
                logger.warning(f"Failed to analyze extended network for {related_id}: {e}")
                continue

        return extended_network

    def _generate_relationship_insights(self, relationships: list[dict], extended_network: dict) -> dict[str, Any]:
        """Generate insights from relationship analysis."""
        if not relationships:
            return {}

        # Relationship type distribution
        primary_types = [r["primary_relationship_type"] for r in relationships]
        type_distribution = dict(Counter(primary_types))

        # Strength distribution
        strength_categories = [r["strength"] for r in relationships]
        strength_distribution = dict(Counter(strength_categories))

        # Average scores by type
        type_scores = defaultdict(list)
        for r in relationships:
            for rel_type, score in r["relationship_scores"].items():
                type_scores[rel_type].append(score)

        avg_scores_by_type = {rel_type: np.mean(scores) for rel_type, scores in type_scores.items()}

        # Network insights
        network_size = len(relationships) + len(extended_network)
        avg_composite_score = np.mean([r["composite_score"] for r in relationships])

        return {
            "summary": {
                "total_direct_relationships": len(relationships),
                "network_size": network_size,
                "avg_relationship_strength": avg_composite_score,
                "strongest_relationship_type": max(avg_scores_by_type.keys(), key=avg_scores_by_type.get)
                if avg_scores_by_type
                else None,
            },
            "distributions": {
                "relationship_types": type_distribution,
                "strength_categories": strength_distribution,
                "avg_scores_by_type": avg_scores_by_type,
            },
            "network_characteristics": {
                "density": len(relationships) / max(network_size * (network_size - 1) / 2, 1),
                "has_extended_network": len(extended_network) > 0,
                "max_secondary_connections": max(
                    [node["relationship_count"] for node in extended_network.values()], default=0
                ),
            },
        }

    def _calculate_network_metrics(self, relationships: list[dict], extended_network: dict) -> dict[str, Any]:
        """Calculate network topology metrics."""
        if not relationships:
            return {}

        # Create adjacency structure
        nodes = set()
        edges = []

        for rel in relationships:
            nodes.add(rel["target_id"])
            nodes.add(rel["related_id"])
            edges.append((rel["target_id"], rel["related_id"], rel["composite_score"]))

        # Add extended network nodes
        for node_id, node_data in extended_network.items():
            nodes.add(node_id)
            for sec_rel in node_data["secondary_relationships"]:
                nodes.add(sec_rel["related_id"])
                edges.append((node_id, sec_rel["related_id"], sec_rel["composite_score"]))

        # Calculate basic metrics
        node_count = len(nodes)
        edge_count = len(edges)
        density = edge_count / max(node_count * (node_count - 1) / 2, 1)

        # Calculate degree distribution
        degree_count = defaultdict(int)
        for edge in edges:
            degree_count[edge[0]] += 1
            degree_count[edge[1]] += 1

        avg_degree = np.mean(list(degree_count.values())) if degree_count else 0
        max_degree = max(degree_count.values()) if degree_count else 0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
            "average_degree": avg_degree,
            "max_degree": max_degree,
            "clustering_coefficient": self._estimate_clustering_coefficient(edges),
            "avg_edge_weight": np.mean([e[2] for e in edges]) if edges else 0,
        }

    def _estimate_clustering_coefficient(self, edges: list[tuple]) -> float:
        """Estimate clustering coefficient for the network."""
        if len(edges) < 3:
            return 0.0

        # Build adjacency list
        adj_list = defaultdict(set)
        for edge in edges:
            adj_list[edge[0]].add(edge[1])
            adj_list[edge[1]].add(edge[0])

        total_coefficient = 0.0
        node_count = 0

        for _node, neighbors in adj_list.items():
            if len(neighbors) < 2:
                continue

            # Count triangles
            triangle_count = 0
            possible_triangles = len(neighbors) * (len(neighbors) - 1) / 2

            for neighbor1 in neighbors:
                for neighbor2 in neighbors:
                    if neighbor1 < neighbor2 and neighbor2 in adj_list[neighbor1]:
                        triangle_count += 1

            if possible_triangles > 0:
                total_coefficient += triangle_count / possible_triangles
                node_count += 1

        return total_coefficient / node_count if node_count > 0 else 0.0

    async def _hierarchical_clustering(
        self, memories: list[dict], min_cluster_size: int, max_clusters: int
    ) -> list[dict]:
        """Perform hierarchical clustering on memories."""
        # Extract embeddings
        embeddings = []
        valid_memories = []

        for memory in memories:
            embedding = self._parse_embedding(memory["embedding"])
            if embedding:
                embeddings.append(embedding)
                valid_memories.append(memory)

        if len(embeddings) < min_cluster_size:
            return []

        # Perform hierarchical clustering
        n_clusters = min(max_clusters, len(embeddings) // min_cluster_size)
        clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")

        cluster_labels = clustering.fit_predict(embeddings)

        # Group memories by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(valid_memories[i])

        # Convert to result format
        result_clusters = []
        for cluster_id, cluster_memories in clusters.items():
            if len(cluster_memories) >= min_cluster_size:
                cluster = await self._build_cluster_result(cluster_id, cluster_memories)
                result_clusters.append(cluster)

        return result_clusters

    async def _build_cluster_result(self, cluster_id: int, memories: list[dict]) -> dict:
        """Build cluster result structure."""
        # Calculate cluster centroid
        embeddings = [self._parse_embedding(m["embedding"]) for m in memories]
        valid_embeddings = [e for e in embeddings if e]

        if valid_embeddings:
            centroid = np.mean(valid_embeddings, axis=0)
        else:
            centroid = None

        # Find representative memory (closest to centroid)
        representative = memories[0]
        if centroid is not None:
            min_distance = float("inf")
            for memory in memories:
                embedding = self._parse_embedding(memory["embedding"])
                if embedding:
                    distance = np.linalg.norm(np.array(embedding) - centroid)
                    if distance < min_distance:
                        min_distance = distance
                        representative = memory

        # Extract common themes
        all_content = " ".join([m["content"] for m in memories])
        themes = self._extract_themes(all_content)

        # Calculate cluster statistics
        importance_scores = [m["importance_score"] for m in memories]
        memory_types = [m["memory_type"] for m in memories]

        return {
            "cluster_id": f"cluster_{cluster_id}",
            "size": len(memories),
            "representative": {
                "id": str(representative["id"]),
                "content_preview": representative["content"][:100],
                "memory_type": representative["memory_type"],
            },
            "members": [
                {
                    "id": str(m["id"]),
                    "content_preview": m["content"][:50],
                    "memory_type": m["memory_type"],
                    "importance_score": float(m["importance_score"]),
                }
                for m in memories
            ],
            "themes": themes[:5],  # Top 5 themes
            "statistics": {
                "avg_importance": float(np.mean(importance_scores)),
                "memory_type_distribution": dict(Counter(memory_types)),
                "date_range": {
                    "earliest": min([m["created_at"] for m in memories]).isoformat(),
                    "latest": max([m["created_at"] for m in memories]).isoformat(),
                },
            },
            "coherence_score": self._calculate_cluster_coherence(valid_embeddings),
        }

    def _extract_themes(self, text: str) -> list[str]:
        """Extract key themes from text using TF-IDF."""
        if not text:
            return []

        try:
            # Simple TF-IDF extraction
            vectorizer = TfidfVectorizer(max_features=20, stop_words="english", ngram_range=(1, 2))

            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]

            # Get top themes
            theme_scores = list(zip(feature_names, tfidf_scores, strict=False))
            theme_scores.sort(key=lambda x: x[1], reverse=True)

            return [theme for theme, score in theme_scores if score > 0.1]

        except Exception as e:
            logger.warning(f"Theme extraction failed: {e}")
            return []

    def _calculate_cluster_coherence(self, embeddings: list[list[float]]) -> float:
        """Calculate cluster coherence based on internal similarity."""
        if len(embeddings) < 2:
            return 1.0

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                similarities.append(sim)

        return float(np.mean(similarities)) if similarities else 0.0

    def _parse_embedding(self, embedding_data: Any) -> list[float] | None:
        """Parse embedding from database format."""
        if not embedding_data:
            return None

        try:
            if isinstance(embedding_data, str):
                # Remove brackets and parse
                embedding_str = embedding_data.strip("[]")
                return [float(x.strip()) for x in embedding_str.split(",")]
            elif isinstance(embedding_data, list):
                return [float(x) for x in embedding_data]
            else:
                return None
        except (ValueError, TypeError):
            return None

    # Empty result helpers
    def _empty_relationship_analysis(self, memory_id: str) -> dict[str, Any]:
        """Return empty relationship analysis."""
        return {
            "target_memory": {"id": memory_id},
            "direct_relationships": [],
            "extended_network": {},
            "insights": {},
            "network_metrics": {},
            "metadata": {
                "analysis_depth": 0,
                "total_relationships": 0,
                "network_size": 0,
                "analyzed_at": datetime.now().isoformat(),
            },
        }

    def _empty_cluster_analysis(self) -> dict[str, Any]:
        """Return empty cluster analysis."""
        return {
            "clusters": [],
            "cluster_relationships": {},
            "insights": {},
            "metadata": {"total_memories": 0, "cluster_count": 0, "analyzed_at": datetime.now().isoformat()},
        }

    def _empty_evolution_analysis(self, concept_keywords: list[str]) -> dict[str, Any]:
        """Return empty evolution analysis."""
        return {
            "concept_keywords": concept_keywords,
            "time_periods": [],
            "temporal_relationships": {},
            "evolution_metrics": {},
            "transition_points": [],
            "insights": {},
            "metadata": {"total_memories": 0, "analysis_periods": 0, "analyzed_at": datetime.now().isoformat()},
        }


# Additional helper functions would continue here...
# (Implementation continues with temporal analysis, community detection, etc.)
