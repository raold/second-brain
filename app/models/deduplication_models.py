from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

"""
Deduplication Data Models

Comprehensive data models for memory deduplication operations,
including enums, configurations, and result structures.
"""

from enum import Enum

from pydantic import ConfigDict


class SimilarityMethod(str, Enum):
    """Methods for similarity detection."""

    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    STRUCTURAL_SIMILARITY = "structural_similarity"
    HYBRID = "hybrid"


class DuplicateAction(str, Enum):
    """Actions to take with duplicates."""

    MERGE = "merge"
    DELETE_DUPLICATE = "delete_duplicate"
    MARK_DUPLICATE = "mark_duplicate"
    NO_ACTION = "no_action"
    MANUAL_REVIEW = "manual_review"


class MergeStrategy(str, Enum):
    """Strategies for merging duplicate memories."""

    KEEP_OLDEST = "keep_oldest"
    KEEP_NEWEST = "keep_newest"
    KEEP_LONGEST = "keep_longest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    SMART_MERGE = "smart_merge"
    MANUAL_MERGE = "manual_merge"


@dataclass
class SimilarityScore:
    """Similarity score between two memories."""

    memory_id_1: str
    memory_id_2: str
    content_similarity: float
    metadata_similarity: float
    structural_similarity: float
    overall_similarity: float
    method_used: SimilarityMethod
    confidence: float
    reasoning: str
    calculation_time: float | None = None

    def __post_init__(self):
        """Validate similarity scores are within valid range."""
        for score_name, score_value in [
            ("content_similarity", self.content_similarity),
            ("metadata_similarity", self.metadata_similarity),
            ("structural_similarity", self.structural_similarity),
            ("overall_similarity", self.overall_similarity),
            ("confidence", self.confidence),
        ]:
            if not 0.0 <= score_value <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0, got {score_value}")


@dataclass
class DuplicateGroup:
    """Group of duplicate memories."""

    group_id: str
    memory_ids: list[str]
    primary_memory_id: str
    similarity_scores: list[SimilarityScore]
    merge_strategy: MergeStrategy
    confidence_score: float | None = None
    detected_by: str | None = None
    detection_time: datetime | None = None

    def __post_init__(self):
        """Validate duplicate group consistency."""
        if self.primary_memory_id not in self.memory_ids:
            raise ValueError("Primary memory ID must be in memory_ids list")
        if len(self.memory_ids) < 2:
            raise ValueError("Duplicate group must contain at least 2 memories")

    @property
    def duplicate_count(self) -> int:
        """Number of duplicates (excluding primary)."""
        return len(self.memory_ids) - 1

    @property
    def average_similarity(self) -> float:
        """Average similarity score for the group."""
        if not self.similarity_scores:
            return 0.0
        return sum(score.overall_similarity for score in self.similarity_scores) / len(
            self.similarity_scores
        )


@dataclass
class MergeResult:
    """Result of a memory merge operation."""

    success: bool
    primary_memory_id: str
    merged_memory_ids: list[str]
    merge_strategy: MergeStrategy
    merged_metadata: dict[str, Any] | None = None
    merge_time: datetime | None = None
    error_message: str | None = None
    backup_id: str | None = None


@dataclass
class DeduplicationResult:
    """Result of a deduplication operation."""

    total_memories: int
    duplicate_groups_found: int
    total_duplicates: int
    memories_merged: int
    memories_deleted: int
    memories_marked: int
    processing_time: float
    duplicate_groups: list[DuplicateGroup]
    merge_results: list[MergeResult] = None
    performance_metrics: dict[str, Any] = None
    errors: list[str] = None
    warnings: list[str] = None
    backup_created: str | None = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.merge_results is None:
            self.merge_results = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    @property
    def success_rate(self) -> float:
        """Success rate of merge operations."""
        if not self.merge_results:
            return 1.0
        successful = sum(1 for result in self.merge_results if result.success)
        return successful / len(self.merge_results)

    @property
    def deduplication_efficiency(self) -> float:
        """Percentage of memories processed for deduplication."""
        if self.total_memories == 0:
            return 0.0
        processed = self.memories_merged + self.memories_deleted + self.memories_marked
        return processed / self.total_memories


class DeduplicationConfig(BaseModel):
    """Configuration for deduplication operations."""

    # Similarity detection settings
    similarity_method: SimilarityMethod = Field(
        default=SimilarityMethod.HYBRID, description="Method for similarity detection"
    )
    similarity_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Minimum similarity for duplicates"
    )

    # Similarity weights (must sum to approximately 1.0)
    content_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Weight for content similarity"
    )
    metadata_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for metadata similarity"
    )
    structural_weight: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Weight for structural similarity"
    )

    # Merge and action settings
    merge_strategy: MergeStrategy = Field(
        default=MergeStrategy.SMART_MERGE, description="Strategy for merging duplicates"
    )
    duplicate_action: DuplicateAction = Field(
        default=DuplicateAction.MARK_DUPLICATE, description="Action for duplicates"
    )

    # Processing settings
    batch_size: int = Field(default=100, gt=0, description="Batch size for processing")
    max_comparisons: int | None = Field(
        default=10000, gt=0, description="Maximum number of pairwise comparisons"
    )

    # Fuzzy matching settings
    enable_fuzzy_matching: bool = Field(default=True, description="Enable fuzzy string matching")
    fuzzy_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Threshold for fuzzy matching"
    )

    # Semantic similarity settings
    enable_semantic_analysis: bool = Field(
        default=True, description="Enable semantic similarity analysis"
    )
    semantic_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Model for semantic embeddings",
    )

    # Safety and backup settings
    preserve_metadata: bool = Field(
        default=True, description="Preserve metadata from all duplicates"
    )
    create_backup: bool = Field(default=True, description="Create backup before deduplication")
    dry_run: bool = Field(default=False, description="Perform dry run without making changes")

    # Performance settings
    enable_caching: bool = Field(default=True, description="Enable similarity score caching")
    parallel_processing: bool = Field(
        default=True, description="Enable parallel processing where possible"
    )
    max_workers: int = Field(
        default=4, gt=0, description="Maximum worker threads for parallel processing"
    )

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    def validate_weights(self) -> bool:
        """Validate that similarity weights sum to approximately 1.0."""
        total_weight = self.content_weight + self.metadata_weight + self.structural_weight
        return 0.95 <= total_weight <= 1.05

    def get_detection_methods(self) -> list[SimilarityMethod]:
        """Get list of detection methods to use based on configuration."""
        if self.similarity_method == SimilarityMethod.HYBRID:
            methods = [SimilarityMethod.EXACT_MATCH]
            if self.enable_fuzzy_matching:
                methods.append(SimilarityMethod.FUZZY_MATCH)
            if self.enable_semantic_analysis:
                methods.append(SimilarityMethod.SEMANTIC_SIMILARITY)
            return methods
        else:
            return [self.similarity_method]


@dataclass
class DetectionStats:
    """Statistics for a detection method."""

    method: SimilarityMethod
    comparisons_made: int
    duplicates_found: int
    average_confidence: float
    processing_time: float
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate percentage."""
        total_cache_attempts = self.cache_hits + self.cache_misses
        if total_cache_attempts == 0:
            return 0.0
        return self.cache_hits / total_cache_attempts


@dataclass
class PerformanceMetrics:
    """Performance metrics for deduplication operation."""

    total_processing_time: float
    detection_stats: list[DetectionStats]
    memory_usage_mb: float | None = None
    comparisons_per_second: float | None = None
    duplicates_per_second: float | None = None

    @property
    def total_comparisons(self) -> int:
        """Total comparisons across all detection methods."""
        return sum(stat.comparisons_made for stat in self.detection_stats)

    @property
    def total_duplicates_found(self) -> int:
        """Total duplicates found across all detection methods."""
        return sum(stat.duplicates_found for stat in self.detection_stats)

    @property
    def overall_cache_hit_rate(self) -> float:
        """Overall cache hit rate across all methods."""
        total_hits = sum(stat.cache_hits for stat in self.detection_stats)
        total_attempts = sum(stat.cache_hits + stat.cache_misses for stat in self.detection_stats)
        if total_attempts == 0:
            return 0.0
        return total_hits / total_attempts
