"""
Deduplication Orchestrator Service for Phase 2 Memory Deduplication

This is the main orchestration service that coordinates all aspects of
the deduplication process. Part of the Phase 2 Advanced Modularization
converting the 928-line deduplication engine into focused components.

Key responsibilities:
- Orchestrate the complete deduplication workflow
- Coordinate detector services and memory merger
- Manage batch processing and performance optimization
- Provide comprehensive progress tracking and statistics
- Handle error recovery and retry logic
- Support different deduplication strategies and configurations

Architecture:
- Clean separation of concerns with dependency injection
- Support for multiple detection methods
- Configurable batch processing for scalability
- Comprehensive error handling and recovery
- Rich statistics and progress reporting
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


# Local type definitions (in production these would be proper imports)
class MergeStrategy(Enum):
    KEEP_OLDEST = "keep_oldest"
    KEEP_NEWEST = "keep_newest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    SMART_MERGE = "smart_merge"


class DetectionMethod(Enum):
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID = "hybrid"


@dataclass
class DeduplicationConfig:
    """Configuration for the complete deduplication process."""

    # Detection configuration
    detection_methods: list[DetectionMethod] = field(default_factory=lambda: [DetectionMethod.HYBRID])
    similarity_threshold: float = 0.85
    confidence_threshold: float = 0.7

    # Merge configuration
    merge_strategy: MergeStrategy = MergeStrategy.SMART_MERGE
    auto_merge: bool = False  # If False, only detect and report

    # Batch processing configuration
    batch_size: int = 100
    max_concurrent_batches: int = 3

    # Performance configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Weights for hybrid detection (must sum to 1.0)
    exact_weight: float = 0.4
    fuzzy_weight: float = 0.3
    semantic_weight: float = 0.3

    def __post_init__(self):
        # Validate weights
        total_weight = self.exact_weight + self.fuzzy_weight + self.semantic_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Detection weights must sum to 1.0, got {total_weight}")


@dataclass
class DuplicateGroup:
    """A group of duplicate memories."""

    group_id: str
    memory_ids: list[str]
    similarity_scores: list[float]
    detection_method: str
    confidence: float = 0.0


@dataclass
class DeduplicationProgress:
    """Progress tracking for deduplication operations."""

    total_memories: int = 0
    memories_processed: int = 0
    batches_completed: int = 0
    total_batches: int = 0
    duplicate_groups_found: int = 0
    memories_to_merge: int = 0
    memories_merged: int = 0
    errors_encountered: int = 0
    current_stage: str = "initializing"
    started_at: datetime | None = None
    estimated_completion: datetime | None = None

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_memories == 0:
            return 0.0
        return min(100.0, (self.memories_processed / self.total_memories) * 100.0)

    @property
    def elapsed_time(self) -> timedelta | None:
        """Calculate elapsed time since start."""
        if not self.started_at:
            return None
        return datetime.utcnow() - self.started_at


@dataclass
class OrchestrationResult:
    """Results from a complete deduplication orchestration."""

    duplicate_groups: list[DuplicateGroup]
    merge_operations: list[dict[str, Any]] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    progress: DeduplicationProgress = field(default_factory=DeduplicationProgress)
    errors: list[str] = field(default_factory=list)
    config_used: DeduplicationConfig | None = None
    total_time_seconds: float = 0.0
    success: bool = True


# Abstract interfaces (in production these would be proper imports)
class DeduplicationDatabaseInterface(ABC):
    """Abstract database interface."""

    @abstractmethod
    async def get_memories_for_deduplication(
        self, filter_criteria: dict[str, Any] | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def merge_memories(
        self,
        primary_id: str,
        duplicate_ids: list[str],
        merge_strategy: str,
        merged_metadata: dict[str, Any] | None = None,
    ) -> bool:
        pass


class BaseDuplicateDetector(ABC):
    """Abstract base class for duplicate detectors."""

    @abstractmethod
    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        pass


class MemoryMerger:
    """Memory merger service."""

    def __init__(self, database: DeduplicationDatabaseInterface):
        self.database = database

    async def merge_duplicate_groups(
        self, duplicate_groups: list[DuplicateGroup], config: DeduplicationConfig
    ) -> tuple[list[dict], dict[str, Any]]:
        # Mock implementation
        return [], {"merged": len(duplicate_groups)}


class DeduplicationOrchestrator:
    """
    Main orchestrator for the deduplication process.

    This service coordinates all components of the deduplication system:
    - Detector services (exact, fuzzy, semantic, hybrid)
    - Memory merger service
    - Progress tracking and statistics
    - Error handling and recovery
    - Batch processing and performance optimization
    """

    def __init__(
        self,
        database: DeduplicationDatabaseInterface,
        detectors: dict[DetectionMethod, BaseDuplicateDetector],
        memory_merger: MemoryMerger,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            database: Database interface for memory operations
            detectors: Dictionary mapping detection methods to detector instances
            memory_merger: Memory merger service instance
            logger: Optional logger instance
        """
        self.database = database
        self.detectors = detectors
        self.memory_merger = memory_merger
        self.logger = logger or logging.getLogger(__name__)

        # Progress tracking
        self.current_progress = DeduplicationProgress()
        self.operation_history: list[OrchestrationResult] = []

        # Performance tracking
        self.performance_metrics = {
            "total_operations": 0,
            "average_operation_time": 0.0,
            "total_memories_processed": 0,
            "total_duplicates_found": 0,
            "cache_hit_rate": 0.0,
        }

    async def deduplicate_memories(
        self, config: DeduplicationConfig | None = None, filter_criteria: dict[str, Any] | None = None
    ) -> OrchestrationResult:
        """
        Execute the complete deduplication process.

        Args:
            config: Deduplication configuration (uses default if None)
            filter_criteria: Optional filtering criteria for memories

        Returns:
            OrchestrationResult with complete results and statistics
        """
        # Use default config if none provided
        if config is None:
            config = DeduplicationConfig()

        # Initialize result object
        result = OrchestrationResult(duplicate_groups=[], config_used=config)

        start_time = datetime.utcnow()

        try:
            # Initialize progress tracking
            self.current_progress = DeduplicationProgress()
            self.current_progress.started_at = start_time
            self.current_progress.current_stage = "loading_memories"

            # Step 1: Load memories for deduplication
            self.logger.info("Loading memories for deduplication...")
            memories = await self._load_memories_for_deduplication(filter_criteria, config)

            if not memories:
                self.logger.warning("No memories found for deduplication")
                result.success = True
                return result

            self.current_progress.total_memories = len(memories)
            self.current_progress.total_batches = (len(memories) + config.batch_size - 1) // config.batch_size

            self.logger.info(f"Loaded {len(memories)} memories for deduplication")

            # Step 2: Detect duplicates using configured methods
            self.current_progress.current_stage = "detecting_duplicates"
            duplicate_groups = await self._detect_duplicates(memories, config)

            result.duplicate_groups = duplicate_groups
            self.current_progress.duplicate_groups_found = len(duplicate_groups)

            # Count total memories that would be merged
            memories_to_merge = sum(len(group.memory_ids) - 1 for group in duplicate_groups)  # -1 because primary stays
            self.current_progress.memories_to_merge = memories_to_merge

            self.logger.info(
                f"Found {len(duplicate_groups)} duplicate groups " f"containing {memories_to_merge} memories to merge"
            )

            # Step 3: Merge duplicates if auto-merge is enabled
            if config.auto_merge and duplicate_groups:
                self.current_progress.current_stage = "merging_duplicates"

                merge_operations, merge_stats = await self.memory_merger.merge_duplicate_groups(
                    duplicate_groups, config
                )

                result.merge_operations = merge_operations
                self.current_progress.memories_merged = merge_stats.get("total_memories_merged", 0)

                self.logger.info(f"Merged {len(merge_operations)} duplicate groups")

            # Step 4: Generate comprehensive statistics
            self.current_progress.current_stage = "generating_statistics"
            result.statistics = await self._generate_statistics(memories, duplicate_groups, config)

            # Mark as completed
            self.current_progress.current_stage = "completed"
            result.progress = self.current_progress
            result.success = True

            # Calculate total time
            end_time = datetime.utcnow()
            result.total_time_seconds = (end_time - start_time).total_seconds()

            # Update performance metrics
            await self._update_performance_metrics(result)

            # Store in operation history
            self.operation_history.append(result)

            self.logger.info(f"Deduplication completed in {result.total_time_seconds:.2f} seconds")

            return result

        except Exception as e:
            self.logger.error(f"Deduplication orchestration failed: {str(e)}")

            result.success = False
            result.errors.append(str(e))
            result.progress = self.current_progress

            end_time = datetime.utcnow()
            result.total_time_seconds = (end_time - start_time).total_seconds()

            return result

    async def _load_memories_for_deduplication(
        self, filter_criteria: dict[str, Any] | None, config: DeduplicationConfig
    ) -> list[dict[str, Any]]:
        """
        Load memories from the database for deduplication analysis.

        Args:
            filter_criteria: Optional filtering criteria
            config: Deduplication configuration

        Returns:
            List of memory dictionaries
        """
        try:
            # Load memories in batches to handle large datasets
            all_memories = []
            batch_size = config.batch_size * 5  # Larger batches for loading
            offset = 0

            while True:
                # Create filter criteria with pagination
                paginated_filter = (filter_criteria or {}).copy()
                paginated_filter["offset"] = offset
                paginated_filter["limit"] = batch_size

                batch = await self.database.get_memories_for_deduplication(filter_criteria=paginated_filter)

                if not batch:
                    break

                all_memories.extend(batch)
                offset += len(batch)

                # Update progress
                self.current_progress.memories_processed = len(all_memories)

                # Break if we got less than expected (end of data)
                if len(batch) < batch_size:
                    break

            return all_memories

        except Exception as e:
            self.logger.error(f"Failed to load memories: {str(e)}")
            raise

    async def _detect_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Detect duplicates using configured detection methods.

        Args:
            memories: List of memories to analyze
            config: Deduplication configuration

        Returns:
            List of duplicate groups found
        """
        all_duplicate_groups = []

        # Process each configured detection method
        for detection_method in config.detection_methods:
            if detection_method not in self.detectors:
                self.logger.warning(f"Detector not available: {detection_method.value}")
                continue

            detector = self.detectors[detection_method]

            try:
                self.logger.info(f"Running {detection_method.value} detection...")

                # Process in batches for performance
                method_groups = await self._process_detection_in_batches(detector, memories, config)

                if method_groups:
                    all_duplicate_groups.extend(method_groups)
                    self.logger.info(f"{detection_method.value} found {len(method_groups)} duplicate groups")

            except Exception as e:
                self.logger.error(f"Error in {detection_method.value} detection: {str(e)}")
                self.current_progress.errors_encountered += 1

        # If using multiple detection methods, we may need to consolidate overlapping groups
        if len(config.detection_methods) > 1:
            all_duplicate_groups = await self._consolidate_duplicate_groups(all_duplicate_groups)

        return all_duplicate_groups

    async def _process_detection_in_batches(
        self, detector: BaseDuplicateDetector, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """
        Process duplicate detection in batches for better performance.

        Args:
            detector: Detector instance to use
            memories: Memories to process
            config: Configuration

        Returns:
            List of duplicate groups found
        """
        all_groups = []

        # Split memories into batches
        total_batches = (len(memories) + config.batch_size - 1) // config.batch_size

        # Process batches with controlled concurrency
        semaphore = asyncio.Semaphore(config.max_concurrent_batches)

        async def process_batch(batch_memories: list[dict[str, Any]], batch_idx: int):
            async with semaphore:
                try:
                    batch_groups = await detector.find_duplicates(batch_memories, config)

                    # Update progress
                    self.current_progress.batches_completed += 1
                    self.current_progress.memories_processed += len(batch_memories)

                    if batch_groups:
                        self.logger.debug(f"Batch {batch_idx + 1}/{total_batches} found {len(batch_groups)} groups")

                    return batch_groups

                except Exception as e:
                    self.logger.error(f"Error processing batch {batch_idx + 1}: {str(e)}")
                    self.current_progress.errors_encountered += 1
                    return []

        # Create batch tasks
        tasks = []
        for i in range(0, len(memories), config.batch_size):
            batch = memories[i : i + config.batch_size]
            task = process_batch(batch, i // config.batch_size)
            tasks.append(task)

        # Execute all batch tasks
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        for result in batch_results:
            if isinstance(result, list):
                all_groups.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Batch processing error: {result}")

        return all_groups

    async def _consolidate_duplicate_groups(self, groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
        """
        Consolidate overlapping duplicate groups from multiple detection methods.

        This handles cases where different detection methods find overlapping
        duplicates and merges them into coherent groups.

        Args:
            groups: List of duplicate groups potentially with overlaps

        Returns:
            Consolidated list of duplicate groups
        """
        if not groups:
            return groups

        # Build a mapping of memory_id -> groups containing that memory
        memory_to_groups = {}
        for group in groups:
            for memory_id in group.memory_ids:
                if memory_id not in memory_to_groups:
                    memory_to_groups[memory_id] = []
                memory_to_groups[memory_id].append(group)

        # Find connected components (groups that share memories)
        visited = set()
        consolidated_groups = []

        for group in groups:
            if group.group_id in visited:
                continue

            # Find all groups connected to this one
            connected_groups = []
            stack = [group]

            while stack:
                current_group = stack.pop()
                if current_group.group_id in visited:
                    continue

                visited.add(current_group.group_id)
                connected_groups.append(current_group)

                # Find other groups sharing memories with this group
                for memory_id in current_group.memory_ids:
                    for related_group in memory_to_groups[memory_id]:
                        if related_group.group_id not in visited:
                            stack.append(related_group)

            # Merge connected groups into one consolidated group
            if len(connected_groups) == 1:
                # Single group, no merging needed
                consolidated_groups.append(connected_groups[0])
            else:
                # Multiple groups need consolidation
                merged_group = await self._merge_overlapping_groups(connected_groups)
                consolidated_groups.append(merged_group)

        self.logger.info(f"Consolidated {len(groups)} groups into {len(consolidated_groups)} groups")
        return consolidated_groups

    async def _merge_overlapping_groups(self, groups: list[DuplicateGroup]) -> DuplicateGroup:
        """
        Merge multiple overlapping groups into a single consolidated group.

        Args:
            groups: List of overlapping groups to merge

        Returns:
            Single consolidated duplicate group
        """
        # Collect all unique memory IDs
        all_memory_ids = set()
        all_scores = []
        detection_methods = []

        for group in groups:
            all_memory_ids.update(group.memory_ids)
            all_scores.extend(group.similarity_scores)
            detection_methods.append(group.detection_method)

        # Calculate consolidated metrics
        avg_confidence = sum(group.confidence for group in groups) / len(groups)
        avg_similarity = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Create consolidated group
        consolidated = DuplicateGroup(
            group_id=f"merged_{'_'.join(g.group_id for g in groups[:3])}",  # Limit ID length
            memory_ids=list(all_memory_ids),
            similarity_scores=[avg_similarity] * len(all_memory_ids),
            detection_method=f"combined_{'+'.join(set(detection_methods))}",
            confidence=avg_confidence,
        )

        return consolidated

    async def _generate_statistics(
        self, memories: list[dict[str, Any]], duplicate_groups: list[DuplicateGroup], config: DeduplicationConfig
    ) -> dict[str, Any]:
        """
        Generate comprehensive statistics about the deduplication process.

        Args:
            memories: Original memories analyzed
            duplicate_groups: Duplicate groups found
            config: Configuration used

        Returns:
            Dictionary with detailed statistics
        """
        stats = {
            # Basic counts
            "total_memories_analyzed": len(memories),
            "duplicate_groups_found": len(duplicate_groups),
            "memories_in_duplicates": sum(len(group.memory_ids) for group in duplicate_groups),
            "unique_memories": len(memories) - sum(len(group.memory_ids) - 1 for group in duplicate_groups),
            # Duplicate group statistics
            "average_group_size": 0.0,
            "largest_group_size": 0,
            "smallest_group_size": 0,
            # Detection method breakdown
            "detection_methods_used": [method.value for method in config.detection_methods],
            "groups_by_detection_method": {},
            # Confidence and similarity statistics
            "average_confidence": 0.0,
            "average_similarity": 0.0,
            "high_confidence_groups": 0,  # confidence > 0.8
            "low_confidence_groups": 0,  # confidence < 0.5
            # Performance metrics
            "processing_time": self.current_progress.elapsed_time.total_seconds()
            if self.current_progress.elapsed_time
            else 0.0,
            "memories_per_second": 0.0,
            "batches_processed": self.current_progress.batches_completed,
            "errors_encountered": self.current_progress.errors_encountered,
            # Configuration used
            "config": {
                "similarity_threshold": config.similarity_threshold,
                "confidence_threshold": config.confidence_threshold,
                "merge_strategy": config.merge_strategy.value,
                "auto_merge": config.auto_merge,
                "batch_size": config.batch_size,
            },
        }

        if duplicate_groups:
            # Calculate group size statistics
            group_sizes = [len(group.memory_ids) for group in duplicate_groups]
            stats["average_group_size"] = sum(group_sizes) / len(group_sizes)
            stats["largest_group_size"] = max(group_sizes)
            stats["smallest_group_size"] = min(group_sizes)

            # Calculate confidence and similarity statistics
            confidences = [group.confidence for group in duplicate_groups]
            stats["average_confidence"] = sum(confidences) / len(confidences)
            stats["high_confidence_groups"] = sum(1 for c in confidences if c > 0.8)
            stats["low_confidence_groups"] = sum(1 for c in confidences if c < 0.5)

            # Calculate average similarity
            all_similarities = []
            for group in duplicate_groups:
                all_similarities.extend(group.similarity_scores)
            if all_similarities:
                stats["average_similarity"] = sum(all_similarities) / len(all_similarities)

            # Group by detection method
            for group in duplicate_groups:
                method = group.detection_method
                stats["groups_by_detection_method"][method] = stats["groups_by_detection_method"].get(method, 0) + 1

        # Performance calculations
        if stats["processing_time"] > 0:
            stats["memories_per_second"] = len(memories) / stats["processing_time"]

        return stats

    async def _update_performance_metrics(self, result: OrchestrationResult):
        """Update overall performance metrics."""
        self.performance_metrics["total_operations"] += 1

        # Update average operation time
        total_time = (
            self.performance_metrics["average_operation_time"] * (self.performance_metrics["total_operations"] - 1)
            + result.total_time_seconds
        ) / self.performance_metrics["total_operations"]
        self.performance_metrics["average_operation_time"] = total_time

        # Update other metrics
        memories_processed = result.statistics.get("total_memories_analyzed", 0)
        self.performance_metrics["total_memories_processed"] += memories_processed
        self.performance_metrics["total_duplicates_found"] += len(result.duplicate_groups)

    def get_progress(self) -> DeduplicationProgress:
        """Get current deduplication progress."""
        return self.current_progress

    def get_operation_history(self, limit: int | None = None) -> list[OrchestrationResult]:
        """
        Get history of deduplication operations.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of orchestration results, most recent first
        """
        history = sorted(self.operation_history, key=lambda x: x.progress.started_at or datetime.min, reverse=True)

        if limit:
            return history[:limit]
        return history

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get overall performance metrics."""
        return self.performance_metrics.copy()

    async def validate_system_health(self) -> dict[str, Any]:
        """
        Validate that all components of the deduplication system are healthy.

        Returns:
            Dictionary with health check results
        """
        health_status = {"overall_status": "healthy", "components": {}, "issues": []}

        try:
            # Test database connectivity
            test_memories = await self.database.get_memories_for_deduplication(limit=1)
            health_status["components"]["database"] = {
                "status": "healthy",
                "test_result": f"Retrieved {len(test_memories)} test memories",
            }
        except Exception as e:
            health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["issues"].append(f"Database connectivity issue: {str(e)}")

        # Test each detector
        test_config = DeduplicationConfig()
        test_memories = [
            {"id": "test_1", "content": "Test memory content", "created_at": "2024-01-01T10:00:00Z", "metadata": {}}
        ]

        for method, detector in self.detectors.items():
            try:
                await detector.find_duplicates(test_memories, test_config)
                health_status["components"][f"detector_{method.value}"] = {
                    "status": "healthy",
                    "test_result": "Successfully processed test memories",
                }
            except Exception as e:
                health_status["components"][f"detector_{method.value}"] = {"status": "unhealthy", "error": str(e)}
                health_status["issues"].append(f"Detector {method.value} issue: {str(e)}")

        # Set overall status based on issues
        if health_status["issues"]:
            health_status["overall_status"] = "degraded" if len(health_status["issues"]) < 3 else "unhealthy"

        return health_status

    async def estimate_processing_time(
        self, memory_count: int, config: DeduplicationConfig | None = None
    ) -> dict[str, Any]:
        """
        Estimate processing time for a given number of memories.

        Args:
            memory_count: Number of memories to process
            config: Configuration to use (affects processing time)

        Returns:
            Dictionary with time estimates
        """
        if config is None:
            config = DeduplicationConfig()

        # Base estimates in seconds per memory (these would be calibrated from real usage)
        base_times = {
            DetectionMethod.EXACT_MATCH: 0.001,  # Very fast
            DetectionMethod.FUZZY_MATCH: 0.01,  # Medium
            DetectionMethod.SEMANTIC_SIMILARITY: 0.05,  # Slower due to embeddings
            DetectionMethod.HYBRID: 0.06,  # Combines multiple methods
        }

        estimates = {}
        total_time = 0.0

        for method in config.detection_methods:
            method_time = base_times.get(method, 0.02) * memory_count

            # Batch processing reduces overhead
            batch_factor = min(1.0, config.batch_size / 50.0)  # Efficiency improves with larger batches
            method_time *= 1.0 - batch_factor * 0.2  # Up to 20% improvement

            estimates[f"{method.value}_seconds"] = method_time
            total_time += method_time

        # Add merge time if auto-merge is enabled
        if config.auto_merge:
            # Estimate 5% of memories will be duplicates, merge takes ~0.1s per group
            estimated_groups = memory_count * 0.05 / 2  # Average 2 memories per group
            merge_time = estimated_groups * 0.1
            estimates["merge_seconds"] = merge_time
            total_time += merge_time

        return {
            "total_estimated_seconds": total_time,
            "total_estimated_minutes": total_time / 60.0,
            "method_breakdown": estimates,
            "assumptions": {
                "memory_count": memory_count,
                "detection_methods": [m.value for m in config.detection_methods],
                "batch_size": config.batch_size,
                "auto_merge": config.auto_merge,
            },
        }
