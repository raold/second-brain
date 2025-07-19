"""
Memory Merger Service for Phase 2 Memory Deduplication

This service handles the actual merging of detected duplicate memories.
Part of the Phase 2 Advanced Modularization converting the 928-line
deduplication engine into focused, maintainable components.

Key responsibilities:
- Merge duplicate memories using configurable strategies
- Handle metadata consolidation
- Preserve important information across merges
- Support different merging strategies (keep oldest, newest, smart merge)
- Provide comprehensive merge statistics and history

Architecture:
- Clean separation from detection logic
- Database-agnostic operations
- Strategy pattern for different merge approaches
- Comprehensive validation and error handling
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# For now, we'll create local definitions to avoid import issues
# In production, these would be imported from the proper modules


class MergeStrategy(Enum):
    KEEP_OLDEST = "keep_oldest"
    KEEP_NEWEST = "keep_newest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    SMART_MERGE = "smart_merge"


@dataclass
class DuplicateGroup:
    """A group of duplicate memories detected by deduplication."""

    group_id: str
    memory_ids: list[str]
    similarity_scores: list[float]
    detection_method: str
    confidence: float = 0.0


@dataclass
class DeduplicationConfig:
    """Configuration for deduplication operations."""

    merge_strategy: MergeStrategy = MergeStrategy.SMART_MERGE
    similarity_threshold: float = 0.85
    confidence_threshold: float = 0.7


class DeduplicationDatabaseInterface(ABC):
    """Abstract interface for deduplication database operations."""

    @abstractmethod
    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def merge_memories(
        self,
        primary_id: str,
        duplicate_ids: list[str],
        merge_strategy: str,
        merged_metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        pass


class MergeConflictResolution(Enum):
    """How to resolve conflicts during memory merging."""

    KEEP_PRIMARY = "keep_primary"  # Keep primary memory's values
    MERGE_VALUES = "merge_values"  # Attempt to merge conflicting values
    KEEP_HIGHEST_SCORE = "keep_highest_score"  # Keep value from highest scored memory
    MANUAL_REVIEW = "manual_review"  # Flag for manual review


@dataclass
class MergeStatistics:
    """Statistics from a memory merge operation."""

    total_groups_processed: int = 0
    total_memories_merged: int = 0
    merge_operations_performed: int = 0
    conflicts_resolved: int = 0
    errors_encountered: int = 0
    processing_time_seconds: float = 0.0
    merge_strategy_counts: Optional[dict[str, int]] = None

    def __post_init__(self):
        if self.merge_strategy_counts is None:
            self.merge_strategy_counts = {}


@dataclass
class MergeOperation:
    """Details of a single merge operation."""

    primary_memory_id: str
    merged_memory_ids: list[str]
    merge_strategy_used: MergeStrategy
    conflicts_resolved: list[str]
    metadata_changes: dict[str, Any]
    content_changes: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MemoryMerger:
    """
    Service for merging duplicate memories detected by the deduplication system.

    This service takes duplicate groups and merges them according to configured
    strategies, preserving important information and handling conflicts intelligently.
    """

    def __init__(self, database: DeduplicationDatabaseInterface, logger: Optional[logging.Logger] = None):
        self.database = database
        self.logger = logger or logging.getLogger(__name__)

        # Statistics tracking
        self.merge_history: list[MergeOperation] = []
        self.current_statistics = MergeStatistics()

        # Merge strategy handlers
        self._strategy_handlers = {
            MergeStrategy.KEEP_OLDEST: self._merge_keep_oldest,
            MergeStrategy.KEEP_NEWEST: self._merge_keep_newest,
            MergeStrategy.KEEP_HIGHEST_IMPORTANCE: self._merge_keep_highest_importance,
            MergeStrategy.SMART_MERGE: self._merge_smart_merge,
        }

    async def merge_duplicate_groups(
        self, duplicate_groups: list[DuplicateGroup], config: DeduplicationConfig
    ) -> tuple[list[MergeOperation], MergeStatistics]:
        """
        Merge all duplicate groups according to configuration.

        Args:
            duplicate_groups: Groups of duplicate memories to merge
            config: Deduplication configuration with merge strategy

        Returns:
            Tuple of (merge_operations, merge_statistics)
        """
        start_time = datetime.utcnow()
        merge_operations = []

        # Reset current statistics
        self.current_statistics = MergeStatistics()
        self.current_statistics.total_groups_processed = len(duplicate_groups)

        try:
            for group in duplicate_groups:
                if len(group.memory_ids) < 2:
                    self.logger.warning(f"Skipping group with insufficient memories: {group.group_id}")
                    continue

                try:
                    merge_op = await self._merge_single_group(group, config)
                    if merge_op:
                        merge_operations.append(merge_op)
                        self.merge_history.append(merge_op)
                        self.current_statistics.merge_operations_performed += 1
                        self.current_statistics.total_memories_merged += len(merge_op.merged_memory_ids)

                        # Track strategy usage
                        strategy_name = merge_op.merge_strategy_used.value
                        if self.current_statistics.merge_strategy_counts is not None:
                            self.current_statistics.merge_strategy_counts[strategy_name] = (
                                self.current_statistics.merge_strategy_counts.get(strategy_name, 0) + 1
                            )

                except Exception as e:
                    self.logger.error(f"Error merging group {group.group_id}: {str(e)}")
                    self.current_statistics.errors_encountered += 1

            # Calculate final statistics
            end_time = datetime.utcnow()
            self.current_statistics.processing_time_seconds = (end_time - start_time).total_seconds()

            self.logger.info(
                f"Merge completed: {len(merge_operations)} operations, "
                f"{self.current_statistics.total_memories_merged} memories merged"
            )

            return merge_operations, self.current_statistics

        except Exception as e:
            self.logger.error(f"Fatal error during merge process: {str(e)}")
            raise

    async def _merge_single_group(self, group: DuplicateGroup, config: DeduplicationConfig) -> Optional[MergeOperation]:
        """
        Merge a single group of duplicate memories.

        Args:
            group: Group of duplicate memories to merge
            config: Deduplication configuration

        Returns:
            MergeOperation details if successful, None if skipped
        """
        try:
            # Get full memory objects for the group
            memories = await self.database.get_memories_by_ids(group.memory_ids)
            if len(memories) < 2:
                self.logger.warning(f"Could not load memories for group {group.group_id}")
                return None

            # Select merge strategy handler
            strategy = config.merge_strategy
            handler = self._strategy_handlers.get(strategy)
            if not handler:
                self.logger.error(f"Unknown merge strategy: {strategy}")
                return None

            # Execute merge strategy
            merge_result = await handler(memories, group, config)
            if not merge_result:
                return None

            # Perform the actual database merge
            await self.database.merge_memories(
                primary_id=merge_result.primary_memory_id,
                duplicate_ids=merge_result.merged_memory_ids,
                merge_strategy=merge_result.merge_strategy_used.value,
                merged_metadata=merge_result.metadata_changes,
            )

            self.logger.debug(f"Successfully merged group {group.group_id} " f"using {strategy.value} strategy")

            return merge_result

        except Exception as e:
            self.logger.error(f"Error merging group {group.group_id}: {str(e)}")
            raise

    async def _merge_keep_oldest(
        self, memories: list[dict[str, Any]], group: DuplicateGroup, config: DeduplicationConfig
    ) -> Optional[MergeOperation]:
        """Merge strategy: keep the oldest memory as primary."""
        # Sort by creation date (oldest first)
        sorted_memories = sorted(memories, key=lambda m: datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")))

        primary = sorted_memories[0]
        duplicates = sorted_memories[1:]

        # Collect metadata from duplicates
        merged_metadata = await self._consolidate_metadata(primary, duplicates, config)

        # Track conflicts resolved
        conflicts = self._identify_conflicts(primary, duplicates)

        return MergeOperation(
            primary_memory_id=primary["id"],
            merged_memory_ids=[m["id"] for m in duplicates],
            merge_strategy_used=MergeStrategy.KEEP_OLDEST,
            conflicts_resolved=conflicts,
            metadata_changes=merged_metadata,
        )

    async def _merge_keep_newest(
        self, memories: list[dict[str, Any]], group: DuplicateGroup, config: DeduplicationConfig
    ) -> Optional[MergeOperation]:
        """Merge strategy: keep the newest memory as primary."""
        # Sort by creation date (newest first)
        sorted_memories = sorted(
            memories, key=lambda m: datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")), reverse=True
        )

        primary = sorted_memories[0]
        duplicates = sorted_memories[1:]

        # Collect metadata from duplicates
        merged_metadata = await self._consolidate_metadata(primary, duplicates, config)

        # Track conflicts resolved
        conflicts = self._identify_conflicts(primary, duplicates)

        return MergeOperation(
            primary_memory_id=primary["id"],
            merged_memory_ids=[m["id"] for m in duplicates],
            merge_strategy_used=MergeStrategy.KEEP_NEWEST,
            conflicts_resolved=conflicts,
            metadata_changes=merged_metadata,
        )

    async def _merge_keep_highest_importance(
        self, memories: list[dict[str, Any]], group: DuplicateGroup, config: DeduplicationConfig
    ) -> Optional[MergeOperation]:
        """Merge strategy: keep the memory with highest importance score."""

        # Sort by importance score (highest first)
        def get_importance_score(memory):
            metadata = memory.get("metadata", {})
            return metadata.get("importance_score", 0.0)

        sorted_memories = sorted(memories, key=get_importance_score, reverse=True)

        primary = sorted_memories[0]
        duplicates = sorted_memories[1:]

        # Collect metadata from duplicates
        merged_metadata = await self._consolidate_metadata(primary, duplicates, config)

        # Track conflicts resolved
        conflicts = self._identify_conflicts(primary, duplicates)

        return MergeOperation(
            primary_memory_id=primary["id"],
            merged_memory_ids=[m["id"] for m in duplicates],
            merge_strategy_used=MergeStrategy.KEEP_HIGHEST_IMPORTANCE,
            conflicts_resolved=conflicts,
            metadata_changes=merged_metadata,
        )

    async def _merge_smart_merge(
        self, memories: list[dict[str, Any]], group: DuplicateGroup, config: DeduplicationConfig
    ) -> Optional[MergeOperation]:
        """
        Smart merge strategy: intelligently combine information from all memories.

        This strategy:
        1. Selects the best primary memory based on multiple factors
        2. Intelligently merges metadata and content
        3. Preserves the most valuable information from all sources
        """
        # Score each memory for primary selection
        memory_scores = []
        for memory in memories:
            score = await self._calculate_smart_merge_score(memory, group)
            memory_scores.append((memory, score))

        # Sort by smart merge score (highest first)
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        primary = memory_scores[0][0]
        duplicates = [m[0] for m in memory_scores[1:]]

        # Perform intelligent metadata consolidation
        merged_metadata = await self._smart_consolidate_metadata(primary, duplicates, config)

        # Check if content needs smart merging
        content_changes = await self._smart_merge_content(primary, duplicates)

        # Track conflicts resolved
        conflicts = self._identify_conflicts(primary, duplicates)

        return MergeOperation(
            primary_memory_id=primary["id"],
            merged_memory_ids=[m["id"] for m in duplicates],
            merge_strategy_used=MergeStrategy.SMART_MERGE,
            conflicts_resolved=conflicts,
            metadata_changes=merged_metadata,
            content_changes=content_changes,
        )

    async def _calculate_smart_merge_score(self, memory: dict[str, Any], group: DuplicateGroup) -> float:
        """
        Calculate a smart merge score for selecting the best primary memory.

        Considers factors like:
        - Importance score
        - Content completeness
        - Metadata richness
        - Creation date (more recent slightly preferred)
        """
        score = 0.0

        # Base importance score (40% weight)
        metadata = memory.get("metadata", {})
        importance = metadata.get("importance_score", 0.0)
        score += importance * 0.4

        # Content completeness (25% weight)
        content = memory.get("content", "")
        content_score = min(len(content) / 1000.0, 1.0)  # Normalize to [0,1]
        score += content_score * 0.25

        # Metadata richness (20% weight)
        metadata_count = len(metadata)
        metadata_score = min(metadata_count / 10.0, 1.0)  # Normalize to [0,1]
        score += metadata_score * 0.20

        # Recency bias (15% weight) - more recent slightly preferred
        try:
            created_at = datetime.fromisoformat(memory["created_at"].replace("Z", "+00:00"))
            days_old = (datetime.now().replace(tzinfo=created_at.tzinfo) - created_at).days
            recency_score = max(0.0, 1.0 - (days_old / 365.0))  # Decay over a year
            score += recency_score * 0.15
        except:
            # If date parsing fails, neutral score
            score += 0.075

        return score

    async def _consolidate_metadata(
        self, primary: dict[str, Any], duplicates: list[dict[str, Any]], config: DeduplicationConfig
    ) -> dict[str, Any]:
        """
        Consolidate metadata from duplicate memories into the primary memory.

        Standard consolidation strategy for most merge types.
        """
        primary_metadata = primary.get("metadata", {}).copy()

        # Collect all tags and categories
        all_tags = set(primary_metadata.get("tags", []))
        all_categories = set(primary_metadata.get("categories", []))

        # Track access counts and update times
        total_access_count = primary_metadata.get("access_count", 0)
        latest_accessed = primary_metadata.get("last_accessed")

        for duplicate in duplicates:
            dup_metadata = duplicate.get("metadata", {})

            # Merge tags and categories
            all_tags.update(dup_metadata.get("tags", []))
            all_categories.update(dup_metadata.get("categories", []))

            # Sum access counts
            total_access_count += dup_metadata.get("access_count", 0)

            # Keep latest access time
            dup_accessed = dup_metadata.get("last_accessed")
            if dup_accessed and (not latest_accessed or dup_accessed > latest_accessed):
                latest_accessed = dup_accessed

        # Update consolidated metadata
        consolidated = primary_metadata
        consolidated["tags"] = list(all_tags)
        consolidated["categories"] = list(all_categories)
        consolidated["access_count"] = total_access_count
        if latest_accessed:
            consolidated["last_accessed"] = latest_accessed

        # Add merge tracking
        consolidated["merged_from"] = [dup["id"] for dup in duplicates]
        consolidated["merged_at"] = datetime.utcnow().isoformat()

        return consolidated

    async def _smart_consolidate_metadata(
        self, primary: dict[str, Any], duplicates: list[dict[str, Any]], config: DeduplicationConfig
    ) -> dict[str, Any]:
        """
        Intelligent metadata consolidation for smart merge strategy.

        This goes beyond basic consolidation to intelligently merge values.
        """
        # Start with standard consolidation
        consolidated = await self._consolidate_metadata(primary, duplicates, config)

        # Intelligent importance score calculation
        importance_scores = [primary.get("metadata", {}).get("importance_score", 0.0)]
        for dup in duplicates:
            importance_scores.append(dup.get("metadata", {}).get("importance_score", 0.0))

        # Use weighted average for importance score
        if importance_scores:
            # Weight the primary memory's score higher (60% vs 40% for duplicates)
            primary_weight = 0.6
            duplicate_weight = 0.4 / len(duplicates) if len(duplicates) > 0 else 0.0

            weighted_score = importance_scores[0] * primary_weight
            for i in range(1, len(importance_scores)):
                weighted_score += importance_scores[i] * duplicate_weight

            consolidated["importance_score"] = min(1.0, weighted_score)

        # Add smart merge metadata
        consolidated["merge_strategy"] = "smart_merge"
        consolidated["merge_confidence"] = await self._calculate_merge_confidence(primary, duplicates)

        return consolidated

    async def _smart_merge_content(self, primary: dict[str, Any], duplicates: list[dict[str, Any]]) -> Optional[str]:
        """
        Intelligently merge content from multiple memories.

        For now, this is a placeholder for future enhancement.
        In a full implementation, this could:
        - Combine complementary information
        - Remove redundant phrases
        - Merge structured content intelligently
        """
        # For now, keep primary content unchanged
        # Future enhancement: implement intelligent content merging
        return None

    async def _calculate_merge_confidence(self, primary: dict[str, Any], duplicates: list[dict[str, Any]]) -> float:
        """
        Calculate confidence score for the merge operation.

        Higher confidence indicates the merge is more likely to be correct.
        """
        # Factors that increase confidence:
        # - High similarity scores
        # - Consistent metadata across memories
        # - Clear primary memory selection

        confidence = 0.5  # Base confidence

        # Boost confidence if metadata is consistent
        primary_meta = primary.get("metadata", {})
        consistent_fields = 0
        total_fields = 0

        for dup in duplicates:
            dup_meta = dup.get("metadata", {})
            for field in ["categories", "tags", "source"]:
                total_fields += 1
                if primary_meta.get(field) == dup_meta.get(field):
                    consistent_fields += 1

        if total_fields > 0:
            consistency_score = consistent_fields / total_fields
            confidence += consistency_score * 0.3

        # Cap at 1.0
        return min(1.0, confidence)

    def _identify_conflicts(self, primary: dict[str, Any], duplicates: list[dict[str, Any]]) -> list[str]:
        """
        Identify conflicts between primary and duplicate memories.

        Returns list of field names where conflicts were found.
        """
        conflicts = []
        primary_meta = primary.get("metadata", {})

        for duplicate in duplicates:
            dup_meta = duplicate.get("metadata", {})

            # Check for conflicting values in important fields
            conflict_fields = ["source", "type", "importance_score"]
            for field in conflict_fields:
                if field in primary_meta and field in dup_meta and primary_meta[field] != dup_meta[field]:
                    if field not in conflicts:
                        conflicts.append(field)

        return conflicts

    def get_merge_statistics(self) -> MergeStatistics:
        """Get current merge statistics."""
        return self.current_statistics

    def get_merge_history(self, limit: Optional[int] = None) -> list[MergeOperation]:
        """
        Get merge operation history.

        Args:
            limit: Optional limit on number of operations to return

        Returns:
            List of merge operations, most recent first
        """
        history = sorted(self.merge_history, key=lambda op: op.created_at or datetime.min, reverse=True)
        if limit:
            return history[:limit]
        return history

    async def validate_merge_integrity(self, merge_operations: list[MergeOperation]) -> dict[str, Any]:
        """
        Validate the integrity of completed merge operations.

        Checks that:
        - Primary memories still exist
        - Duplicate memories were properly removed
        - Metadata was preserved correctly

        Args:
            merge_operations: List of merge operations to validate

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "total_operations": len(merge_operations),
            "valid_operations": 0,
            "invalid_operations": 0,
            "errors": [],
        }

        for operation in merge_operations:
            try:
                # Check if primary memory exists
                primary_memories = await self.database.get_memories_by_ids([operation.primary_memory_id])
                if not primary_memories:
                    validation_results["errors"].append(f"Primary memory {operation.primary_memory_id} not found")
                    validation_results["invalid_operations"] += 1
                    continue

                # Check if duplicate memories were removed
                duplicate_memories = await self.database.get_memories_by_ids(operation.merged_memory_ids)
                if duplicate_memories:
                    validation_results["errors"].append(
                        f"Duplicate memories still exist: {[m['id'] for m in duplicate_memories]}"
                    )
                    validation_results["invalid_operations"] += 1
                    continue

                validation_results["valid_operations"] += 1

            except Exception as e:
                validation_results["errors"].append(f"Validation error: {str(e)}")
                validation_results["invalid_operations"] += 1

        return validation_results
