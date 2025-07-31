"""
Fuzzy Match Detector

Detects similar content using fuzzy string matching algorithms.
Handles minor variations, typos, and formatting differences.
"""

import difflib
from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class FuzzyMatchDetector(BaseDuplicateDetector):
    """Detector for fuzzy content matches using various string similarity algorithms."""

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize fuzzy match detector.

        Args:
            cache_enabled: Whether to enable similarity score caching
        """
        super().__init__(cache_enabled)
        self.text_normalizer = TextNormalizer()
        self.similarity_calculator = FuzzyStringCalculator()

    def get_detector_name(self) -> str:
        """Get detector name."""
        return "Fuzzy Match Detector"

    def get_similarity_method(self) -> SimilarityMethod:
        """Get similarity method."""
        return SimilarityMethod.FUZZY_MATCH

    def get_optimal_batch_size(self) -> int:
        """Fuzzy matching is more computationally intensive."""
        return 200

    def get_required_memory_fields(self) -> list[str]:
        """Required fields for fuzzy matching."""
        return ["id", "content", "created_at"]

    async def _find_duplicates_impl(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Find fuzzy duplicate memories using string similarity algorithms.

        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration

        Returns:
            List of duplicate groups found
        """
        if not memories or not config.enable_fuzzy_matching:
            return []

        logger.debug(f"Starting fuzzy match detection on {len(memories)} memories")

        # Normalize content for comparison
        normalized_memories = []
        for memory in memories:
            normalized_content = self.text_normalizer.normalize(memory.get("content", ""))
            if normalized_content:  # Skip empty content
                normalized_memories.append(
                    {
                        "original": memory,
                        "normalized_content": normalized_content,
                        "tokens": self.text_normalizer.tokenize(normalized_content),
                        "fingerprint": self._create_fingerprint(normalized_content),
                    }
                )

        if len(normalized_memories) < 2:
            return []

        # Find potential duplicate pairs using similarity threshold
        duplicate_pairs = await self._find_similar_pairs(normalized_memories, config.fuzzy_threshold)

        if not duplicate_pairs:
            return []

        # Group pairs into duplicate groups
        duplicate_groups = self._group_similar_pairs(duplicate_pairs, config)

        logger.info(f"Fuzzy match detection completed: {len(duplicate_groups)} groups found")
        return duplicate_groups

    async def _find_similar_pairs(
        self, normalized_memories: list[dict[str, Any]], threshold: float
    ) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
        """
        Find pairs of memories with similarity above threshold.

        Args:
            normalized_memories: List of memories with normalized content
            threshold: Minimum similarity threshold

        Returns:
            List of (memory1, memory2, similarity_score) tuples
        """
        similar_pairs = []
        total_comparisons = len(normalized_memories) * (len(normalized_memories) - 1) // 2

        logger.debug(f"Performing {total_comparisons} fuzzy comparisons")

        for i in range(len(normalized_memories)):
            for j in range(i + 1, len(normalized_memories)):
                mem1, mem2 = normalized_memories[i], normalized_memories[j]

                # Check cache first
                mem1_id = mem1["original"].get("id")
                mem2_id = mem2["original"].get("id")
                cached_similarity = self._get_cached_similarity(mem1_id, mem2_id)

                if cached_similarity is not None:
                    similarity = cached_similarity
                    self._record_comparison(similarity, from_cache=True)
                else:
                    # Calculate fuzzy similarity
                    similarity = self.similarity_calculator.calculate_similarity(
                        mem1["normalized_content"],
                        mem2["normalized_content"],
                        mem1["tokens"],
                        mem2["tokens"],
                        mem1["fingerprint"],
                        mem2["fingerprint"],
                    )

                    # Cache the result
                    self._cache_similarity(mem1_id, mem2_id, similarity)
                    self._record_comparison(similarity, from_cache=False)

                # Add to pairs if above threshold
                if similarity >= threshold:
                    similar_pairs.append((mem1, mem2, similarity))
                    logger.debug(f"Found fuzzy match: {mem1_id} <-> {mem2_id} (similarity: {similarity:.3f})")

        return similar_pairs

    def _group_similar_pairs(
        self, pairs: list[tuple[dict[str, Any], dict[str, Any], float]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Group similar pairs into duplicate groups.

        Args:
            pairs: List of similar memory pairs with scores
            config: Deduplication configuration

        Returns:
            List of duplicate groups
        """
        # Build adjacency map
        adjacency_map = defaultdict(set)
        pair_similarities = {}

        for mem1, mem2, similarity in pairs:
            mem1_id = mem1["original"].get("id")
            mem2_id = mem2["original"].get("id")

            adjacency_map[mem1_id].add(mem2_id)
            adjacency_map[mem2_id].add(mem1_id)
            pair_similarities[(mem1_id, mem2_id)] = similarity
            pair_similarities[(mem2_id, mem1_id)] = similarity

        # Find connected components (groups of similar memories)
        visited = set()
        duplicate_groups = []

        for mem1, mem2, _ in pairs:
            mem1_id = mem1["original"].get("id")

            if mem1_id in visited:
                continue

            # Find all connected memories using DFS
            group_memory_ids = set()
            stack = [mem1_id]

            while stack:
                current_id = stack.pop()
                if current_id in visited:
                    continue

                visited.add(current_id)
                group_memory_ids.add(current_id)

                # Add all connected memories
                for connected_id in adjacency_map[current_id]:
                    if connected_id not in visited:
                        stack.append(connected_id)

            if len(group_memory_ids) >= 2:
                # Create duplicate group
                group = self._create_duplicate_group(group_memory_ids, pair_similarities, pairs, config)
                if group:
                    duplicate_groups.append(group)
                    self._record_duplicate_found()

        return duplicate_groups

    def _create_duplicate_group(
        self,
        memory_ids: set[str],
        pair_similarities: dict[tuple[str, str], float],
        original_pairs: list[tuple[dict[str, Any], dict[str, Any], float]],
        config: DeduplicationConfig,
    ) -> DuplicateGroup:
        """
        Create a duplicate group from a set of connected memory IDs.

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
            id_to_memory[mem1["original"].get("id")] = mem1["original"]
            id_to_memory[mem2["original"].get("id")] = mem2["original"]

        group_memories = [id_to_memory[mid] for mid in memory_ids if mid in id_to_memory]

        if len(group_memories) < 2:
            return None

        # Select primary memory
        primary_memory_id = self._select_primary_memory(group_memories, config.merge_strategy.value)

        # Create similarity scores for all pairs in the group
        similarity_scores = []
        memory_ids_list = list(memory_ids)

        for i in range(len(memory_ids_list)):
            for j in range(i + 1, len(memory_ids_list)):
                id1, id2 = memory_ids_list[i], memory_ids_list[j]
                similarity = pair_similarities.get((id1, id2), 0.0)

                if similarity > 0:
                    # Get memory objects for metadata calculation
                    mem1 = id_to_memory.get(id1, {})
                    mem2 = id_to_memory.get(id2, {})

                    metadata_similarity = self._calculate_metadata_similarity(mem1, mem2)

                    # Calculate composite similarity
                    content_weight = config.content_weight
                    metadata_weight = config.metadata_weight
                    overall_similarity = content_weight * similarity + metadata_weight * metadata_similarity

                    similarity_score = SimilarityScore(
                        memory_id_1=id1,
                        memory_id_2=id2,
                        content_similarity=similarity,
                        metadata_similarity=metadata_similarity,
                        structural_similarity=similarity,  # Use content similarity as proxy
                        overall_similarity=overall_similarity,
                        method_used=SimilarityMethod.FUZZY_MATCH,
                        confidence=min(similarity, 0.95),  # Fuzzy matches have slightly lower confidence
                        reasoning=f"Fuzzy string match (similarity: {similarity:.3f})",
                    )

                    similarity_scores.append(similarity_score)

        # Calculate average confidence for the group
        average_similarity = (
            sum(score.overall_similarity for score in similarity_scores) / len(similarity_scores)
            if similarity_scores
            else 0.0
        )

        # Create duplicate group
        group_id = f"fuzzy_{hash(''.join(sorted(memory_ids)))}"[-12:]

        duplicate_group = DuplicateGroup(
            group_id=f"fuzzy_{group_id}_{len(memory_ids)}",
            memory_ids=list(memory_ids),
            primary_memory_id=primary_memory_id,
            similarity_scores=similarity_scores,
            merge_strategy=config.merge_strategy,
            confidence_score=average_similarity,
            detected_by=self.get_detector_name(),
        )

        return duplicate_group

    def _create_fingerprint(self, text: str) -> str:
        """
        Create a fingerprint for quick similarity pre-filtering.

        Args:
            text: Normalized text

        Returns:
            Text fingerprint for quick comparison
        """
        # Create a simple fingerprint using sorted unique words
        words = set(text.lower().split())
        # Take most common patterns and first few characters
        sorted_words = sorted(words)[:10]  # Limit to avoid very long fingerprints
        return "".join(sorted_words)[:50]


class TextNormalizer:
    """Utility class for text normalization and preprocessing."""

    def __init__(self):
        """Initialize text normalizer with common patterns."""
        self.whitespace_pattern = re.compile(r"\s+")
        self.punctuation_pattern = re.compile(r"[^\w\s]")
        self.number_pattern = re.compile(r"\d+")

    def normalize(self, text: str) -> str:
        """
        Normalize text for fuzzy comparison.

        Args:
            text: Raw text to normalize

        Returns:
            Normalized text
        """
        if not isinstance(text, str):
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Replace numbers with placeholder
        normalized = self.number_pattern.sub("NUM", normalized)

        # Remove extra whitespace
        normalized = self.whitespace_pattern.sub(" ", normalized)

        # Remove leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize normalized text into words.

        Args:
            text: Normalized text

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Remove punctuation and split
        clean_text = self.punctuation_pattern.sub(" ", text)
        tokens = clean_text.split()

        # Filter out very short tokens
        return [token for token in tokens if len(token) > 1]


class FuzzyStringCalculator:
    """Utility class for calculating fuzzy string similarities."""

    def calculate_similarity(
        self, text1: str, text2: str, tokens1: list[str], tokens2: list[str], fingerprint1: str, fingerprint2: str
    ) -> float:
        """
        Calculate fuzzy similarity between two texts using multiple methods.

        Args:
            text1, text2: Normalized text strings
            tokens1, tokens2: Tokenized words
            fingerprint1, fingerprint2: Text fingerprints

        Returns:
            Fuzzy similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        if text1 == text2:
            return 1.0

        # Quick fingerprint pre-filter
        if len(fingerprint1) > 10 and len(fingerprint2) > 10:
            fingerprint_similarity = difflib.SequenceMatcher(None, fingerprint1, fingerprint2).ratio()

            # Skip expensive calculations if fingerprints are too different
            if fingerprint_similarity < 0.3:
                return 0.0

        # Calculate multiple similarity metrics
        similarities = []

        # 1. Sequence matcher (character-level)
        sequence_similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        similarities.append(sequence_similarity)

        # 2. Token-based Jaccard similarity
        if tokens1 and tokens2:
            set1, set2 = set(tokens1), set(tokens2)
            jaccard_similarity = len(set1 & set2) / len(set1 | set2) if set1 | set2 else 0.0
            similarities.append(jaccard_similarity)

        # 3. Longest common subsequence similarity
        lcs_similarity = self._lcs_similarity(text1, text2)
        similarities.append(lcs_similarity)

        # 4. Word order similarity
        if tokens1 and tokens2:
            word_order_similarity = self._word_order_similarity(tokens1, tokens2)
            similarities.append(word_order_similarity)

        # Return weighted average of similarities
        if similarities:
            weights = [0.4, 0.3, 0.2, 0.1][: len(similarities)]  # Prefer sequence matcher
            weights = weights[: len(similarities)]
            weight_sum = sum(weights)
            weighted_sum = sum(sim * weight for sim, weight in zip(similarities, weights, strict=False))
            return weighted_sum / weight_sum if weight_sum > 0 else 0.0

        return 0.0

    def _lcs_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity based on longest common subsequence.

        Args:
            text1, text2: Text strings to compare

        Returns:
            LCS-based similarity score
        """
        if not text1 or not text2:
            return 0.0

        # Use difflib to find longest common subsequence
        matcher = difflib.SequenceMatcher(None, text1, text2)
        lcs_length = sum(triple.size for triple in matcher.get_matching_blocks())

        max_length = max(len(text1), len(text2))
        return lcs_length / max_length if max_length > 0 else 0.0

    def _word_order_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        """
        Calculate similarity based on word order preservation.

        Args:
            tokens1, tokens2: Token lists to compare

        Returns:
            Word order similarity score
        """
        if not tokens1 or not tokens2:
            return 0.0

        # Find common tokens
        common_tokens = set(tokens1) & set(tokens2)
        if not common_tokens:
            return 0.0

        # Get positions of common tokens in both sequences
        pos1 = {token: i for i, token in enumerate(tokens1) if token in common_tokens}
        pos2 = {token: i for i, token in enumerate(tokens2) if token in common_tokens}

        # Calculate order preservation score
        order_preservation = 0
        total_comparisons = 0

        for token1 in common_tokens:
            for token2 in common_tokens:
                if token1 != token2:
                    # Check if relative order is preserved
                    order1 = pos1[token1] < pos1[token2]
                    order2 = pos2[token1] < pos2[token2]

                    if order1 == order2:
                        order_preservation += 1
                    total_comparisons += 1

        return order_preservation / total_comparisons if total_comparisons > 0 else 1.0
