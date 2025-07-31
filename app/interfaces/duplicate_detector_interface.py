"""
Duplicate Detector Interface

Abstract interface for all duplicate detection algorithms,
enabling modular, testable, and extensible detection methods.
"""

from app.utils.logging_config import get_logger
from typing import Optional
from typing import List
from typing import Any
logger = get_logger(__name__)


class DuplicateDetectorInterface(ABC):
    """Abstract interface for duplicate detection algorithms."""

    @abstractmethod
    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Find duplicate groups in the given memories.

        Args:
            memories: List of memory dictionaries to analyze
            config: Deduplication configuration

        Returns:
            List of duplicate groups found
        """
        pass

    @abstractmethod
    def get_detector_name(self) -> str:
        """
        Get the name of this detector.

        Returns:
            Human-readable detector name
        """
        pass

    @abstractmethod
    def get_similarity_method(self) -> SimilarityMethod:
        """
        Get the similarity method this detector implements.

        Returns:
            SimilarityMethod enum value
        """
        pass

    def supports_incremental_detection(self) -> bool:
        """
        Check if this detector supports incremental detection.

        Returns:
            True if incremental detection is supported
        """
        return False

    def get_required_memory_fields(self) -> list[str]:
        """
        Get list of required memory fields for this detector.

        Returns:
            List of required field names
        """
        return ["id", "content"]

    def get_optimal_batch_size(self) -> Optional[int]:
        """
        Get optimal batch size for this detector.

        Returns:
            Optimal batch size, or None for no preference
        """
        return None

    async def validate_memories(self, memories: list[dict[str, Any]]) -> list[str]:
        """
        Validate that memories have required fields for this detector.

        Args:
            memories: List of memories to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        required_fields = self.get_required_memory_fields()

        for i, memory in enumerate(memories):
            for field in required_fields:
                if field not in memory or memory[field] is None:
                    errors.append(f"Memory {i} missing required field: {field}")
                elif field == "content" and not isinstance(memory[field], str):
                    errors.append(f"Memory {i} field '{field}' must be string, got {type(memory[field])}")
                elif field == "id" and not memory[field]:
                    errors.append(f"Memory {i} has empty ID")

        return errors


class BaseDuplicateDetector(DuplicateDetectorInterface):
    """Base implementation with common functionality."""

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize base detector.

        Args:
            cache_enabled: Whether to enable similarity score caching
        """
        self.cache_enabled = cache_enabled
        self.similarity_cache: dict[str, float] = {}
        self.stats = None

    def _get_cache_key(self, memory_id_1: str, memory_id_2: str) -> str:
        """
        Generate cache key for memory pair.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID

        Returns:
            Cache key string
        """
        # Ensure consistent ordering for cache key
        ids = sorted([memory_id_1, memory_id_2])
        return f"{ids[0]}:{ids[1]}:{self.get_similarity_method().value}"

    def _get_cached_similarity(self, memory_id_1: str, memory_id_2: str) -> Optional[float]:
        """
        Get cached similarity score.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID

        Returns:
            Cached similarity score or None if not cached
        """
        if not self.cache_enabled:
            return None

        cache_key = self._get_cache_key(memory_id_1, memory_id_2)
        return self.similarity_cache.get(cache_key)

    def _cache_similarity(self, memory_id_1: str, memory_id_2: str, similarity: float) -> None:
        """
        Cache similarity score.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID
            similarity: Similarity score to cache
        """
        if not self.cache_enabled:
            return

        cache_key = self._get_cache_key(memory_id_1, memory_id_2)
        self.similarity_cache[cache_key] = similarity

    def _start_detection_stats(self) -> None:
        """Initialize detection statistics tracking."""
        self.stats = {
            "start_time": time.time(),
            "comparisons": 0,
            "duplicates_found": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "confidences": [],
        }

    def _record_comparison(self, similarity: float, from_cache: bool = False) -> None:
        """
        Record a comparison for statistics.

        Args:
            similarity: Similarity score calculated
            from_cache: Whether result came from cache
        """
        if self.stats is None:
            return

        self.stats["comparisons"] += 1
        self.stats["confidences"].append(similarity)

        if from_cache:
            self.stats["cache_hits"] += 1
        else:
            self.stats["cache_misses"] += 1

    def _record_duplicate_found(self) -> None:
        """Record that a duplicate was found."""
        if self.stats is not None:
            self.stats["duplicates_found"] += 1

    def _get_detection_stats(self) -> DetectionStats:
        """
        Get detection statistics.

        Returns:
            DetectionStats object with performance metrics
        """
        if self.stats is None:
            return DetectionStats(
                method=self.get_similarity_method(),
                comparisons_made=0,
                duplicates_found=0,
                average_confidence=0.0,
                processing_time=0.0,
            )

        processing_time = time.time() - self.stats["start_time"]
        average_confidence = (
            sum(self.stats["confidences"]) / len(self.stats["confidences"]) if self.stats["confidences"] else 0.0
        )

        return DetectionStats(
            method=self.get_similarity_method(),
            comparisons_made=self.stats["comparisons"],
            duplicates_found=self.stats["duplicates_found"],
            average_confidence=average_confidence,
            processing_time=processing_time,
            cache_hits=self.stats["cache_hits"],
            cache_misses=self.stats["cache_misses"],
        )

    def _select_primary_memory(self, memories: list[dict[str, Any]], strategy: str) -> str:
        """
        Select primary memory from a group based on merge strategy.

        Args:
            memories: List of memory dictionaries
            strategy: Merge strategy to use

        Returns:
            ID of selected primary memory
        """
        if not memories:
            raise ValueError("Cannot select primary from empty memory list")

        try:
            if strategy == "keep_oldest":
                primary = min(memories, key=lambda m: m.get("created_at", ""))
            elif strategy == "keep_newest":
                primary = max(memories, key=lambda m: m.get("created_at", ""))
            elif strategy == "keep_longest":
                primary = max(memories, key=lambda m: len(m.get("content", "")))
            elif strategy == "keep_highest_importance":
                primary = max(memories, key=lambda m: m.get("metadata", {}).get("importance_score", 0.5))
            else:
                # Default to first memory for unknown strategies
                primary = memories[0]

            return primary.get("id", f"unknown_{hash(str(primary))}")

        except Exception as e:
            logger.warning(f"Error selecting primary memory with strategy {strategy}: {e}")
            return memories[0].get("id", f"fallback_{hash(str(memories[0]))}")

    def _calculate_metadata_similarity(self, memory1: dict[str, Any], memory2: dict[str, Any]) -> float:
        """
        Calculate similarity between memory metadata.

        Args:
            memory1: First memory dictionary
            memory2: Second memory dictionary

        Returns:
            Metadata similarity score (0.0 to 1.0)
        """
        metadata1 = memory1.get("metadata", {})
        metadata2 = memory2.get("metadata", {})

        if not metadata1 and not metadata2:
            return 1.0  # Both empty, considered identical
        if not metadata1 or not metadata2:
            return 0.0  # One empty, one not

        # Compare common fields
        common_keys = set(metadata1.keys()) & set(metadata2.keys())
        if not common_keys:
            return 0.0

        similarities = []

        for key in common_keys:
            val1, val2 = metadata1[key], metadata2[key]

            if val1 == val2:
                similarities.append(1.0)
            elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numeric similarity
                max_val = max(abs(val1), abs(val2))
                if max_val == 0:
                    similarities.append(1.0)
                else:
                    diff = abs(val1 - val2)
                    similarities.append(max(0.0, 1.0 - (diff / max_val)))
            elif isinstance(val1, str) and isinstance(val2, str):
                # String similarity (simple approach)
                if val1.lower() == val2.lower():
                    similarities.append(1.0)
                else:
                    similarities.append(0.0)
            else:
                similarities.append(0.0)

        return sum(similarities) / len(similarities) if similarities else 0.0

    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Base implementation that handles common setup and validation.

        Subclasses should override _find_duplicates_impl for specific logic.
        """
        # Validate memories
        errors = await self.validate_memories(memories)
        if errors:
            logger.error(f"Memory validation failed for {self.get_detector_name()}: {errors}")
            return []

        # Start statistics tracking
        self._start_detection_stats()

        try:
            # Call implementation-specific logic
            groups = await self._find_duplicates_impl(memories, config)

            logger.info(f"{self.get_detector_name()} found {len(groups)} duplicate groups")
            return groups

        except Exception as e:
            logger.error(f"Error in {self.get_detector_name()}: {e}")
            return []

    async def _find_duplicates_impl(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Implementation-specific duplicate finding logic.

        Subclasses must override this method.
        """
        raise NotImplementedError("Subclasses must implement _find_duplicates_impl")
