"""
Memory clustering and semantic grouping analyzer
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from uuid import uuid4

import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.metrics import calinski_harabasz_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from .models import ClusteringRequest, MemoryCluster


class ClusterAnalyzer:
    """Analyzes and clusters memories based on semantic similarity"""

    def __init__(self, database):
        self.db = database
        self.min_cluster_size = 3
        self.max_clusters = 50

    async def analyze_clusters(
        self,
        request: ClusteringRequest
    ) -> tuple[list[MemoryCluster], float]:
        """Main method to perform clustering analysis"""
        # Get memories with embeddings
        memories = await self._get_memories_with_embeddings()

        if len(memories) < request.min_cluster_size * 2:
            return [], 0.0

        # Extract embeddings and prepare data
        embeddings, memory_data = self._prepare_clustering_data(memories)

        # Perform clustering based on algorithm
        if request.algorithm == "kmeans":
            labels, quality_score = await self._kmeans_clustering(
                embeddings, request, memory_data
            )
        elif request.algorithm == "dbscan":
            labels, quality_score = await self._dbscan_clustering(
                embeddings, request, memory_data
            )
        elif request.algorithm == "hierarchical":
            labels, quality_score = await self._hierarchical_clustering(
                embeddings, request, memory_data
            )
        else:
            raise ValueError(f"Unknown clustering algorithm: {request.algorithm}")

        # Create cluster objects
        clusters = self._create_clusters_from_labels(
            labels, memory_data, embeddings, request
        )

        return clusters, quality_score

    async def _get_memories_with_embeddings(self) -> list[dict[str, Any]]:
        """Get all memories that have embeddings"""
        query = """
        SELECT id, content, content_vector, tags, importance,
               created_at, updated_at, metadata
        FROM memories
        WHERE content_vector IS NOT NULL
        ORDER BY created_at DESC
        """

        return await self.db.fetch_all(query)

    def _prepare_clustering_data(
        self,
        memories: list[dict[str, Any]]
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """Prepare data for clustering"""
        embeddings = []
        memory_data = []

        for memory in memories:
            if memory.get('content_vector'):
                embeddings.append(memory['content_vector'])
                memory_data.append({
                    'id': memory['id'],
                    'content': memory['content'],
                    'tags': memory.get('tags', []),
                    'importance': memory.get('importance', 0),
                    'created_at': memory['created_at'],
                    'metadata': memory.get('metadata', {})
                })

        return np.array(embeddings), memory_data

    async def _kmeans_clustering(
        self,
        embeddings: np.ndarray,
        request: ClusteringRequest,
        memory_data: list[dict[str, Any]]
    ) -> tuple[np.ndarray, float]:
        """Perform K-means clustering"""
        # Determine optimal number of clusters if not specified
        if request.num_clusters is None:
            n_clusters = await self._find_optimal_clusters_elbow(
                embeddings, max_k=min(len(embeddings) // 3, self.max_clusters)
            )
        else:
            n_clusters = request.num_clusters

        # Perform clustering
        scaler = StandardScaler()
        scaled_embeddings = scaler.fit_transform(embeddings)

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )
        labels = kmeans.fit_predict(scaled_embeddings)

        # Calculate quality score
        if len(set(labels)) > 1:
            silhouette = silhouette_score(scaled_embeddings, labels)
            calinski = calinski_harabasz_score(scaled_embeddings, labels)
            quality_score = (silhouette + min(calinski / 1000, 1)) / 2
        else:
            quality_score = 0.0

        return labels, quality_score

    async def _dbscan_clustering(
        self,
        embeddings: np.ndarray,
        request: ClusteringRequest,
        memory_data: list[dict[str, Any]]
    ) -> tuple[np.ndarray, float]:
        """Perform DBSCAN clustering"""
        scaler = StandardScaler()
        scaled_embeddings = scaler.fit_transform(embeddings)

        # Use similarity threshold to determine eps
        eps = 1.0 - request.similarity_threshold

        dbscan = DBSCAN(
            eps=eps,
            min_samples=request.min_cluster_size,
            metric='cosine'
        )
        labels = dbscan.fit_predict(scaled_embeddings)

        # Calculate quality score
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        if n_clusters > 1:
            # Filter out noise points for quality calculation
            mask = labels != -1
            if np.sum(mask) > 0:
                silhouette = silhouette_score(
                    scaled_embeddings[mask],
                    labels[mask]
                )
                quality_score = silhouette * (1 - n_noise / len(labels))
            else:
                quality_score = 0.0
        else:
            quality_score = 0.0

        return labels, quality_score

    async def _hierarchical_clustering(
        self,
        embeddings: np.ndarray,
        request: ClusteringRequest,
        memory_data: list[dict[str, Any]]
    ) -> tuple[np.ndarray, float]:
        """Perform hierarchical clustering"""
        scaler = StandardScaler()
        scaled_embeddings = scaler.fit_transform(embeddings)

        # Determine number of clusters
        if request.num_clusters is None:
            n_clusters = min(len(embeddings) // 5, 20)
        else:
            n_clusters = request.num_clusters

        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage='ward'
        )
        labels = clustering.fit_predict(scaled_embeddings)

        # Calculate quality score
        if len(set(labels)) > 1:
            silhouette = silhouette_score(scaled_embeddings, labels)
            quality_score = silhouette
        else:
            quality_score = 0.0

        return labels, quality_score

    async def _find_optimal_clusters_elbow(
        self,
        embeddings: np.ndarray,
        max_k: int = 20
    ) -> int:
        """Find optimal number of clusters using elbow method"""
        scaler = StandardScaler()
        scaled_embeddings = scaler.fit_transform(embeddings)

        inertias = []
        K = range(2, min(max_k, len(embeddings) // 2))

        for k in K:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(scaled_embeddings)
            inertias.append(kmeans.inertia_)

        # Find elbow point (simplified)
        if len(inertias) > 2:
            # Calculate second derivative
            diffs = np.diff(inertias)
            diffs2 = np.diff(diffs)

            # Find elbow as maximum of second derivative
            elbow_idx = np.argmax(diffs2) + 2
            optimal_k = list(K)[elbow_idx]
        else:
            optimal_k = 5  # Default

        return optimal_k

    def _create_clusters_from_labels(
        self,
        labels: np.ndarray,
        memory_data: list[dict[str, Any]],
        embeddings: np.ndarray,
        request: ClusteringRequest
    ) -> list[MemoryCluster]:
        """Create MemoryCluster objects from clustering labels"""
        clusters = []

        # Group memories by cluster label
        cluster_groups = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise in DBSCAN
                cluster_groups[label].append((idx, memory_data[idx]))

        # Create cluster objects
        for cluster_id, members in cluster_groups.items():
            if len(members) < request.min_cluster_size:
                continue

            # Extract member data
            member_indices = [m[0] for m in members]
            member_memories = [m[1] for m in members]
            member_embeddings = embeddings[member_indices]

            # Find centroid (memory closest to cluster center)
            cluster_center = np.mean(member_embeddings, axis=0)
            distances = np.linalg.norm(
                member_embeddings - cluster_center,
                axis=1
            )
            centroid_idx = np.argmin(distances)
            centroid_memory = member_memories[centroid_idx]

            # Extract common tags
            all_tags = []
            for mem in member_memories:
                all_tags.extend(mem.get('tags', []))
            common_tags = [
                tag for tag, count in Counter(all_tags).most_common(10)
                if count >= len(member_memories) * 0.3  # Present in 30% of memories
            ]

            # Calculate average importance
            avg_importance = np.mean([
                mem.get('importance', 0) for mem in member_memories
            ])

            # Calculate coherence score
            coherence = self._calculate_cluster_coherence(
                member_embeddings,
                cluster_center
            )

            # Extract keywords from content
            keywords = self._extract_cluster_keywords(member_memories)

            cluster = MemoryCluster(
                id=uuid4(),
                name=self._generate_cluster_name(common_tags, keywords),
                description=self._generate_cluster_description(
                    member_memories,
                    common_tags
                ),
                size=len(members),
                centroid_memory_id=centroid_memory['id'],
                memory_ids=[mem['id'] for mem in member_memories],
                common_tags=common_tags,
                average_importance=avg_importance,
                coherence_score=coherence,
                created_at=datetime.utcnow(),
                keywords=keywords
            )

            clusters.append(cluster)

        return sorted(clusters, key=lambda c: c.size, reverse=True)

    def _calculate_cluster_coherence(
        self,
        member_embeddings: np.ndarray,
        center: np.ndarray
    ) -> float:
        """Calculate coherence of cluster members"""
        # Average cosine similarity to center
        similarities = []
        for embedding in member_embeddings:
            similarity = np.dot(embedding, center) / (
                np.linalg.norm(embedding) * np.linalg.norm(center)
            )
            similarities.append(similarity)

        return np.mean(similarities)

    def _extract_cluster_keywords(
        self,
        memories: list[dict[str, Any]],
        max_keywords: int = 10
    ) -> list[str]:
        """Extract representative keywords from cluster"""
        # Simple keyword extraction from content
        word_freq = defaultdict(int)

        for memory in memories:
            content = memory.get('content', '').lower()
            # Simple tokenization
            words = content.split()

            for word in words:
                if len(word) > 4:  # Skip short words
                    word_freq[word] += 1

        # Get most frequent words
        keywords = [
            word for word, _ in sorted(
                word_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_keywords]
        ]

        return keywords

    def _generate_cluster_name(
        self,
        tags: list[str],
        keywords: list[str]
    ) -> str:
        """Generate descriptive name for cluster"""
        if tags:
            return f"Cluster: {', '.join(tags[:3])}"
        elif keywords:
            return f"Topic: {', '.join(keywords[:3])}"
        else:
            return "Unnamed Cluster"

    def _generate_cluster_description(
        self,
        memories: list[dict[str, Any]],
        tags: list[str]
    ) -> str:
        """Generate description for cluster"""
        desc_parts = []

        desc_parts.append(f"Collection of {len(memories)} related memories")

        if tags:
            desc_parts.append(f"Common themes: {', '.join(tags[:5])}")

        # Add date range
        dates = [m['created_at'] for m in memories]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            desc_parts.append(
                f"Created between {min_date.date()} and {max_date.date()}"
            )

        return ". ".join(desc_parts)
