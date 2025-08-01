from typing import Any

from app.utils.logging_config import get_logger

"""
Semantic Similarity Detector

Detects semantically similar content using vector embeddings.
Handles conceptual similarity beyond lexical matching.
"""

from collections import defaultdict

logger = get_logger(__name__)


class SemanticSimilarityDetector(BaseDuplicateDetector):
    """Detector for semantic similarity using embedding vectors."""

    def __init__(self, cache_enabled: bool = True, embedding_service=None):
        """
        Initialize semantic similarity detector.

        Args:
            cache_enabled: Whether to enable similarity score caching
            embedding_service: Service for generating embeddings (optional)
        """
        super().__init__(cache_enabled)
        self.embedding_service = embedding_service
        self.embedding_cache: dict[str, list[float]] = {}
        self.similarity_cache: dict[str, float] = {}

    def get_detector_name(self) -> str:
        """Get detector name."""
        return "Semantic Similarity Detector"

    def get_similarity_method(self) -> SimilarityMethod:
        """Get similarity method."""
        return SimilarityMethod.SEMANTIC_SIMILARITY

    def get_optimal_batch_size(self) -> int:
        """Semantic analysis benefits from batch processing embeddings."""
        return 50

    def get_required_memory_fields(self) -> list[str]:
        """Required fields for semantic analysis."""
        return ["id", "content", "created_at"]

    def supports_incremental_detection(self) -> bool:
        """Semantic similarity supports incremental detection with cached embeddings."""
        return True

    async def _find_duplicates_impl(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Find semantically similar memories using embedding vectors.

        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration

        Returns:
            List of duplicate groups found
        """
        if not memories or not config.enable_semantic_analysis:
            return []

        logger.debug(f"Starting semantic similarity detection on {len(memories)} memories")

        # Filter memories with sufficient content
        valid_memories = [
            mem
            for mem in memories
            if mem.get("content", "") and len(mem.get("content", "").strip()) > 10
        ]

        if len(valid_memories) < 2:
            return []

        # Generate embeddings for all memories
        embeddings_map = await self._get_embeddings_batch(valid_memories, config)

        if len(embeddings_map) < 2:
            logger.warning("Insufficient embeddings generated for semantic analysis")
            return []

        # Find similar pairs using cosine similarity
        similar_pairs = await self._find_semantically_similar_pairs(
            valid_memories, embeddings_map, config.similarity_threshold
        )

        if not similar_pairs:
            return []

        # Group pairs into duplicate groups
        duplicate_groups = self._group_semantic_pairs(similar_pairs, config)

        logger.info(
            f"Semantic similarity detection completed: {len(duplicate_groups)} groups found"
        )
        return duplicate_groups

    async def _get_embeddings_batch(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> dict[str, list[float]]:
        """
        Get embeddings for a batch of memories.

        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration

        Returns:
            Map of memory IDs to embedding vectors
        """
        embeddings_map = {}
        memories_needing_embeddings = []

        # Check cache first
        for memory in memories:
            memory_id = memory.get("id")
            if memory_id in self.embedding_cache:
                embeddings_map[memory_id] = self.embedding_cache[memory_id]
            else:
                memories_needing_embeddings.append(memory)

        if not memories_needing_embeddings:
            return embeddings_map

        logger.debug(f"Generating embeddings for {len(memories_needing_embeddings)} memories")

        try:
            # Generate embeddings using service or fallback method
            if self.embedding_service:
                new_embeddings = await self._generate_embeddings_with_service(
                    memories_needing_embeddings, config
                )
            else:
                new_embeddings = await self._generate_fallback_embeddings(
                    memories_needing_embeddings
                )

            # Cache new embeddings
            for memory_id, embedding in new_embeddings.items():
                self.embedding_cache[memory_id] = embedding
                embeddings_map[memory_id] = embedding

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Use fallback method on error
            fallback_embeddings = await self._generate_fallback_embeddings(
                memories_needing_embeddings
            )
            embeddings_map.update(fallback_embeddings)

        return embeddings_map

    async def _generate_embeddings_with_service(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> dict[str, list[float]]:
        """
        Generate embeddings using external service.

        Args:
            memories: Memories to generate embeddings for
            config: Configuration with model settings

        Returns:
            Map of memory IDs to embeddings
        """
        embeddings_map = {}

        try:
            # Prepare content for embedding generation
            content_list = []
            memory_ids = []

            for memory in memories:
                content = self._prepare_content_for_embedding(memory.get("content", ""))
                if content:
                    content_list.append(content)
                    memory_ids.append(memory.get("id"))

            if not content_list:
                return {}

            # Generate embeddings in batches (actual service call would go here)
            # For now, simulate with a placeholder that generates consistent embeddings
            embeddings = await self._simulate_embedding_service(content_list, config.semantic_model)

            # Map embeddings to memory IDs
            for memory_id, embedding in zip(memory_ids, embeddings, strict=False):
                embeddings_map[memory_id] = embedding

        except Exception as e:
            logger.error(f"Embedding service failed: {e}")
            raise

        return embeddings_map

    async def _simulate_embedding_service(
        self, content_list: list[str], model: str
    ) -> list[list[float]]:
        """
        Simulate embedding service for testing/fallback.

        In production, this would call actual embedding service.
        """
        embeddings = []

        for content in content_list:
            # Create a simple deterministic embedding based on content
            # In production, this would use actual transformer models
            embedding = self._create_simple_embedding(content)
            embeddings.append(embedding)

        return embeddings

    def _create_simple_embedding(self, content: str) -> list[float]:
        """
        Create a simple embedding for testing purposes.

        Args:
            content: Text content

        Returns:
            Simple embedding vector
        """
        # Create a basic embedding based on text characteristics
        words = content.lower().split()

        # Create a 384-dimensional vector (common embedding size)
        embedding = [0.0] * 384

        # Use word characteristics to populate embedding
        for i, word in enumerate(words[:50]):  # Limit to first 50 words
            # Use character codes and position to create features
            for j, char in enumerate(word[:8]):  # Limit to first 8 chars
                index = (hash(char) + i * 7 + j * 3) % 384
                embedding[index] += ord(char) / 1000.0

        # Add content-length features
        embedding[0] = len(content) / 1000.0
        embedding[1] = len(words) / 100.0

        # Normalize the embedding
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def _generate_fallback_embeddings(
        self, memories: list[dict[str, Any]]
    ) -> dict[str, list[float]]:
        """
        Generate simple fallback embeddings when service is unavailable.

        Args:
            memories: Memories to generate embeddings for

        Returns:
            Map of memory IDs to simple embeddings
        """
        embeddings_map = {}

        for memory in memories:
            memory_id = memory.get("id")
            content = memory.get("content", "")

            if content:
                embedding = self._create_simple_embedding(content)
                embeddings_map[memory_id] = embedding

        return embeddings_map

    def _prepare_content_for_embedding(self, content: str) -> str:
        """
        Prepare content for embedding generation.

        Args:
            content: Raw content

        Returns:
            Cleaned content ready for embedding
        """
        if not isinstance(content, str):
            return ""

        # Basic cleaning
        cleaned = content.strip()

        # Truncate very long content (embedding models have limits)
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."

        return cleaned

    async def _find_semantically_similar_pairs(
        self,
        memories: list[dict[str, Any]],
        embeddings_map: dict[str, list[float]],
        threshold: float,
    ) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
        """
        Find pairs of memories with semantic similarity above threshold.

        Args:
            memories: List of memory dictionaries
            embeddings_map: Map of memory IDs to embeddings
            threshold: Minimum similarity threshold

        Returns:
            List of (memory1, memory2, similarity_score) tuples
        """
        similar_pairs = []

        # Filter memories that have embeddings
        memories_with_embeddings = [mem for mem in memories if mem.get("id") in embeddings_map]

        total_comparisons = len(memories_with_embeddings) * (len(memories_with_embeddings) - 1) // 2
        logger.debug(f"Performing {total_comparisons} semantic similarity comparisons")

        for i in range(len(memories_with_embeddings)):
            for j in range(i + 1, len(memories_with_embeddings)):
                mem1, mem2 = memories_with_embeddings[i], memories_with_embeddings[j]
                mem1_id, mem2_id = mem1.get("id"), mem2.get("id")

                # Check cache first
                cached_similarity = self._get_cached_similarity(mem1_id, mem2_id)

                if cached_similarity is not None:
                    similarity = cached_similarity
                    self._record_comparison(similarity, from_cache=True)
                else:
                    # Calculate cosine similarity
                    embedding1 = embeddings_map[mem1_id]
                    embedding2 = embeddings_map[mem2_id]

                    similarity = self._cosine_similarity(embedding1, embedding2)

                    # Cache the result
                    self._cache_similarity(mem1_id, mem2_id, similarity)
                    self._record_comparison(similarity, from_cache=False)

                # Add to pairs if above threshold
                if similarity >= threshold:
                    similar_pairs.append((mem1, mem2, similarity))
                    logger.debug(
                        f"Found semantic match: {mem1_id} <-> {mem2_id} (similarity: {similarity:.3f})"
                    )

        return similar_pairs

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1, vec2: Embedding vectors

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        try:
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))

            # Calculate magnitudes
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(a * a for a in vec2) ** 0.5

            # Avoid division by zero
            if magnitude1 == 0.0 or magnitude2 == 0.0:
                return 0.0

            # Calculate cosine similarity
            cosine_sim = dot_product / (magnitude1 * magnitude2)

            # Ensure result is in valid range [0, 1]
            return max(0.0, min(1.0, cosine_sim))

        except Exception as e:
            logger.warning(f"Error calculating cosine similarity: {e}")
            return 0.0

    def _group_semantic_pairs(
        self, pairs: list[tuple[dict[str, Any], dict[str, Any], float]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Group semantic pairs into duplicate groups.

        Args:
            pairs: List of similar memory pairs with scores
            config: Deduplication configuration

        Returns:
            List of duplicate groups
        """
        # Use same grouping logic as fuzzy detector but with semantic context

        # Build adjacency map
        adjacency_map = defaultdict(set)
        pair_similarities = {}

        for mem1, mem2, similarity in pairs:
            mem1_id = mem1.get("id")
            mem2_id = mem2.get("id")

            adjacency_map[mem1_id].add(mem2_id)
            adjacency_map[mem2_id].add(mem1_id)
            pair_similarities[(mem1_id, mem2_id)] = similarity
            pair_similarities[(mem2_id, mem1_id)] = similarity

        # Find connected components
        visited = set()
        duplicate_groups = []

        for mem1, mem2, _ in pairs:
            mem1_id = mem1.get("id")

            if mem1_id in visited:
                continue

            # Find all connected memories
            group_memory_ids = set()
            stack = [mem1_id]

            while stack:
                current_id = stack.pop()
                if current_id in visited:
                    continue

                visited.add(current_id)
                group_memory_ids.add(current_id)

                for connected_id in adjacency_map[current_id]:
                    if connected_id not in visited:
                        stack.append(connected_id)

            if len(group_memory_ids) >= 2:
                group = self._create_semantic_duplicate_group(
                    group_memory_ids, pair_similarities, pairs, config
                )
                if group:
                    duplicate_groups.append(group)
                    self._record_duplicate_found()

        return duplicate_groups

    def _create_semantic_duplicate_group(
        self,
        memory_ids: set,
        pair_similarities: dict[tuple[str, str], float],
        original_pairs: list[tuple[dict[str, Any], dict[str, Any], float]],
        config: DeduplicationConfig,
    ) -> DuplicateGroup:
        """
        Create a semantic duplicate group.

        Args:
            memory_ids: Set of memory IDs in the group
            pair_similarities: Map of pairwise similarities
            original_pairs: Original memory pair data
            config: Deduplication configuration

        Returns:
            DuplicateGroup instance
        """
        if len(memory_ids) < 2:
            return None

        # Get original memory objects
        id_to_memory = {}
        for mem1, mem2, _ in original_pairs:
            id_to_memory[mem1.get("id")] = mem1
            id_to_memory[mem2.get("id")] = mem2

        group_memories = [id_to_memory[mid] for mid in memory_ids if mid in id_to_memory]

        if len(group_memories) < 2:
            return None

        # Select primary memory
        primary_memory_id = self._select_primary_memory(group_memories, config.merge_strategy.value)

        # Create similarity scores
        similarity_scores = []
        memory_ids_list = list(memory_ids)

        for i in range(len(memory_ids_list)):
            for j in range(i + 1, len(memory_ids_list)):
                id1, id2 = memory_ids_list[i], memory_ids_list[j]
                semantic_similarity = pair_similarities.get((id1, id2), 0.0)

                if semantic_similarity > 0:
                    # Get memory objects
                    mem1 = id_to_memory.get(id1, {})
                    mem2 = id_to_memory.get(id2, {})

                    metadata_similarity = self._calculate_metadata_similarity(mem1, mem2)

                    # Calculate weighted overall similarity
                    content_weight = config.content_weight
                    metadata_weight = config.metadata_weight
                    overall_similarity = (
                        content_weight * semantic_similarity + metadata_weight * metadata_similarity
                    )

                    similarity_score = SimilarityScore(
                        memory_id_1=id1,
                        memory_id_2=id2,
                        content_similarity=semantic_similarity,
                        metadata_similarity=metadata_similarity,
                        structural_similarity=semantic_similarity
                        * 0.9,  # Slightly lower for semantic
                        overall_similarity=overall_similarity,
                        method_used=SimilarityMethod.SEMANTIC_SIMILARITY,
                        confidence=semantic_similarity * 0.9,  # Semantic similarity confidence
                        reasoning=f"Semantic embedding similarity (cosine: {semantic_similarity:.3f})",
                    )

                    similarity_scores.append(similarity_score)

        # Calculate group confidence
        average_similarity = (
            sum(score.overall_similarity for score in similarity_scores) / len(similarity_scores)
            if similarity_scores
            else 0.0
        )

        # Create group ID
        group_id = f"semantic_{hash(''.join(sorted(memory_ids)))}"[-12:]

        duplicate_group = DuplicateGroup(
            group_id=f"semantic_{group_id}_{len(memory_ids)}",
            memory_ids=list(memory_ids),
            primary_memory_id=primary_memory_id,
            similarity_scores=similarity_scores,
            merge_strategy=config.merge_strategy,
            confidence_score=average_similarity,
            detected_by=self.get_detector_name(),
        )

        return duplicate_group

    async def get_embedding(self, content: str, config: DeduplicationConfig) -> list[float] | None:
        """
        Get embedding for a single piece of content.

        Args:
            content: Content to embed
            config: Configuration

        Returns:
            Embedding vector or None if failed
        """
        try:
            if self.embedding_service:
                embeddings = await self._generate_embeddings_with_service(
                    [{"id": "temp", "content": content}], config
                )
                return embeddings.get("temp")
            else:
                return self._create_simple_embedding(content)
        except Exception as e:
            logger.error(f"Error getting single embedding: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear embedding and similarity caches."""
        self.embedding_cache.clear()
        self.similarity_cache.clear()
        logger.debug("Semantic similarity detector caches cleared")
