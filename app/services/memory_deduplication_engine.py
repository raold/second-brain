import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.database import get_database
from app.events.domain_events import DuplicatesDetectedEvent


#!/usr/bin/env python3
"""
Advanced Memory Deduplication Engine
Intelligent duplicate detection with similarity analysis and smart merging
"""

from collections import defaultdict
from enum import Enum


class SimilarityMethod(str, Enum):
    """Methods for similarity detection"""

    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    STRUCTURAL_SIMILARITY = "structural_similarity"
    HYBRID = "hybrid"


class DuplicateAction(str, Enum):
    """Actions to take with duplicates"""

    MERGE = "merge"
    DELETE_DUPLICATE = "delete_duplicate"
    MARK_DUPLICATE = "mark_duplicate"
    NO_ACTION = "no_action"
    MANUAL_REVIEW = "manual_review"


class MergeStrategy(str, Enum):
    """Strategies for merging duplicate memories"""

    KEEP_OLDEST = "keep_oldest"
    KEEP_NEWEST = "keep_newest"
    KEEP_LONGEST = "keep_longest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    SMART_MERGE = "smart_merge"
    MANUAL_MERGE = "manual_merge"


@dataclass
class SimilarityScore:
    """Similarity score between two memories"""

    memory_id_1: str
    memory_id_2: str
    content_similarity: float
    metadata_similarity: float
    structural_similarity: float
    overall_similarity: float
    method_used: SimilarityMethod
    confidence: float
    reasoning: str


@dataclass
class DuplicateGroup:
    """Group of duplicate memories"""

    group_id: str
    memory_ids: list[str]
    primary_memory_id: str
    similarity_scores: list[SimilarityScore]
    merge_strategy: MergeStrategy
    action_taken: DuplicateAction | None = None
    merged_content: str | None = None
    merged_metadata: dict[str, Any] | None = None


@dataclass
class DeduplicationResult:
    """Result of deduplication operation"""

    total_memories: int
    duplicate_groups_found: int
    total_duplicates: int
    memories_merged: int
    memories_deleted: int
    memories_marked: int
    processing_time: float
    duplicate_groups: list[DuplicateGroup]
    performance_metrics: dict[str, Any]
    errors: list[str]
    warnings: list[str]


class DeduplicationConfig(BaseModel):
    """Configuration for deduplication process"""

    similarity_method: SimilarityMethod = Field(
        SimilarityMethod.HYBRID, description="Method for similarity detection"
    )
    similarity_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Minimum similarity for duplicates"
    )
    content_weight: float = Field(0.6, ge=0.0, le=1.0, description="Weight for content similarity")
    metadata_weight: float = Field(
        0.3, ge=0.0, le=1.0, description="Weight for metadata similarity"
    )
    structural_weight: float = Field(
        0.1, ge=0.0, le=1.0, description="Weight for structural similarity"
    )
    merge_strategy: MergeStrategy = Field(
        MergeStrategy.SMART_MERGE, description="Strategy for merging duplicates"
    )
    duplicate_action: DuplicateAction = Field(
        DuplicateAction.MARK_DUPLICATE, description="Action for duplicates"
    )
    batch_size: int = Field(100, description="Batch size for processing")
    enable_fuzzy_matching: bool = Field(True, description="Enable fuzzy string matching")
    fuzzy_threshold: float = Field(0.85, description="Threshold for fuzzy matching")
    preserve_metadata: bool = Field(True, description="Preserve metadata from all duplicates")
    create_backup: bool = Field(True, description="Create backup before deduplication")
    dry_run: bool = Field(False, description="Perform dry run without making changes")


class ExactMatchDetector:
    """Detector for exact content matches"""

    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """Find exact duplicate memories"""
        content_hash_map = defaultdict(list)

        # Group memories by content hash
        for memory in memories:
            content = memory.get("content", "").strip()
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
            content_hash_map[content_hash].append(memory)

        duplicate_groups = []

        for content_hash, memory_group in content_hash_map.items():
            if len(memory_group) > 1:
                # Create duplicate group
                group_id = f"exact_{content_hash[:8]}_{len(memory_group)}"
                memory_ids = [m.get("id", f"mem_{i}") for i, m in enumerate(memory_group)]

                # Determine primary memory based on strategy
                primary_memory_id = self._select_primary_memory(memory_group, config.merge_strategy)

                # Create similarity scores (1.0 for exact matches)
                similarity_scores = []
                for i in range(len(memory_group)):
                    for j in range(i + 1, len(memory_group)):
                        similarity_scores.append(
                            SimilarityScore(
                                memory_id_1=memory_ids[i],
                                memory_id_2=memory_ids[j],
                                content_similarity=1.0,
                                metadata_similarity=self._calculate_metadata_similarity(
                                    memory_group[i], memory_group[j]
                                ),
                                structural_similarity=1.0,
                                overall_similarity=1.0,
                                method_used=SimilarityMethod.EXACT_MATCH,
                                confidence=1.0,
                                reasoning="Exact content match",
                            )
                        )

                duplicate_groups.append(
                    DuplicateGroup(
                        group_id=group_id,
                        memory_ids=memory_ids,
                        primary_memory_id=primary_memory_id,
                        similarity_scores=similarity_scores,
                        merge_strategy=config.merge_strategy,
                    )
                )

        return duplicate_groups

    def _select_primary_memory(
        self, memories: list[dict[str, Any]], strategy: MergeStrategy
    ) -> str:
        """Select primary memory based on strategy"""
        if strategy == MergeStrategy.KEEP_OLDEST:
            oldest = min(memories, key=lambda m: m.get("created_at", ""))
            return oldest.get("id", "unknown")
        elif strategy == MergeStrategy.KEEP_NEWEST:
            newest = max(memories, key=lambda m: m.get("created_at", ""))
            return newest.get("id", "unknown")
        elif strategy == MergeStrategy.KEEP_LONGEST:
            longest = max(memories, key=lambda m: len(m.get("content", "")))
            return longest.get("id", "unknown")
        elif strategy == MergeStrategy.KEEP_HIGHEST_IMPORTANCE:
            highest = max(
                memories, key=lambda m: m.get("metadata", {}).get("importance_score", 0.5)
            )
            return highest.get("id", "unknown")
        else:
            # Default to first memory
            return memories[0].get("id", "unknown")

    def _calculate_metadata_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any]
    ) -> float:
        """Calculate metadata similarity between two memories"""
        metadata1 = memory1.get("metadata", {})
        metadata2 = memory2.get("metadata", {})

        # Compare key metadata fields
        common_keys = set(metadata1.keys()) & set(metadata2.keys())
        if not common_keys:
            return 0.0

        matches = 0
        for key in common_keys:
            if metadata1[key] == metadata2[key]:
                matches += 1

        return matches / len(common_keys) if common_keys else 0.0


class FuzzyMatchDetector:
    """Detector for fuzzy content matches"""

    def __init__(self):
        self.text_processors = [
            self._normalize_whitespace,
            self._remove_punctuation,
            self._lowercase,
            self._remove_common_words,
        ]

    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """Find fuzzy duplicate memories"""
        if not config.enable_fuzzy_matching:
            return []

        # Preprocess content for comparison
        processed_memories = []
        for memory in memories:
            processed_content = await self._preprocess_content(memory.get("content", ""))
            processed_memories.append(
                {
                    "original": memory,
                    "processed_content": processed_content,
                    "content_tokens": set(processed_content.split()),
                }
            )

        duplicate_groups = []
        processed_pairs = set()

        # Compare all pairs of memories
        for i in range(len(processed_memories)):
            for j in range(i + 1, len(processed_memories)):
                pair_key = tuple(sorted([i, j]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                memory1 = processed_memories[i]
                memory2 = processed_memories[j]

                # Calculate similarity
                similarity = await self._calculate_fuzzy_similarity(memory1, memory2, config)

                if similarity.overall_similarity >= config.fuzzy_threshold:
                    # Check if memories are already in existing groups
                    existing_group = self._find_existing_group(
                        duplicate_groups,
                        [memory1["original"].get("id"), memory2["original"].get("id")],
                    )

                    if existing_group:
                        # Add to existing group
                        if memory1["original"].get("id") not in existing_group.memory_ids:
                            existing_group.memory_ids.append(memory1["original"].get("id"))
                        if memory2["original"].get("id") not in existing_group.memory_ids:
                            existing_group.memory_ids.append(memory2["original"].get("id"))
                        existing_group.similarity_scores.append(similarity)
                    else:
                        # Create new group
                        group_id = f"fuzzy_{hashlib.md5(f'{i}_{j}'.encode()).hexdigest()[:8]}"
                        memory_ids = [
                            memory1["original"].get("id", f"mem_{i}"),
                            memory2["original"].get("id", f"mem_{j}"),
                        ]

                        primary_memory_id = self._select_primary_memory(
                            [memory1["original"], memory2["original"]], config.merge_strategy
                        )

                        duplicate_groups.append(
                            DuplicateGroup(
                                group_id=group_id,
                                memory_ids=memory_ids,
                                primary_memory_id=primary_memory_id,
                                similarity_scores=[similarity],
                                merge_strategy=config.merge_strategy,
                            )
                        )

        return duplicate_groups

    async def _preprocess_content(self, content: str) -> str:
        """Preprocess content for fuzzy matching"""
        processed = content
        for processor in self.text_processors:
            processed = processor(processed)
        return processed

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        return re.sub(r"\s+", " ", text).strip()

    def _remove_punctuation(self, text: str) -> str:
        """Remove punctuation from text"""
        return re.sub(r"[^\w\s]", "", text)

    def _lowercase(self, text: str) -> str:
        """Convert text to lowercase"""
        return text.lower()

    def _remove_common_words(self, text: str) -> str:
        """Remove common words from text"""
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in common_words]
        return " ".join(filtered_words)

    async def _calculate_fuzzy_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any], config: DeduplicationConfig
    ) -> SimilarityScore:
        """Calculate fuzzy similarity between two memories"""
        # Jaccard similarity for content
        tokens1 = memory1["content_tokens"]
        tokens2 = memory2["content_tokens"]

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        content_similarity = intersection / union if union > 0 else 0.0

        # Levenshtein-like similarity for processed content
        content1 = memory1["processed_content"]
        content2 = memory2["processed_content"]

        if len(content1) == 0 and len(content2) == 0:
            string_similarity = 1.0
        elif len(content1) == 0 or len(content2) == 0:
            string_similarity = 0.0
        else:
            string_similarity = self._calculate_string_similarity(content1, content2)

        # Average content similarities
        final_content_similarity = (content_similarity + string_similarity) / 2

        # Metadata similarity
        metadata_similarity = self._calculate_metadata_similarity(
            memory1["original"], memory2["original"]
        )

        # Structural similarity (length, word count, etc.)
        structural_similarity = self._calculate_structural_similarity(
            memory1["original"], memory2["original"]
        )

        # Overall similarity
        overall_similarity = (
            final_content_similarity * config.content_weight
            + metadata_similarity * config.metadata_weight
            + structural_similarity * config.structural_weight
        )

        return SimilarityScore(
            memory_id_1=memory1["original"].get("id", "unknown"),
            memory_id_2=memory2["original"].get("id", "unknown"),
            content_similarity=final_content_similarity,
            metadata_similarity=metadata_similarity,
            structural_similarity=structural_similarity,
            overall_similarity=overall_similarity,
            method_used=SimilarityMethod.FUZZY_MATCH,
            confidence=0.8,
            reasoning=f"Fuzzy match with {intersection} common tokens, string similarity: {string_similarity:.2f}",
        )

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple algorithm"""
        # Simple character-based similarity
        if len(str1) == 0 and len(str2) == 0:
            return 1.0

        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0

        # Count matching characters in similar positions
        matches = 0
        for i in range(min(len(str1), len(str2))):
            if str1[i] == str2[i]:
                matches += 1

        # Add bonus for similar length
        length_similarity = 1 - abs(len(str1) - len(str2)) / max_len

        return (matches / max_len + length_similarity) / 2

    def _calculate_metadata_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any]
    ) -> float:
        """Calculate metadata similarity"""
        metadata1 = memory1.get("metadata", {})
        metadata2 = memory2.get("metadata", {})

        if not metadata1 and not metadata2:
            return 1.0

        all_keys = set(metadata1.keys()) | set(metadata2.keys())
        if not all_keys:
            return 1.0

        matches = 0
        for key in all_keys:
            val1 = metadata1.get(key)
            val2 = metadata2.get(key)

            if val1 == val2:
                matches += 1
            elif isinstance(val1, int | float) and isinstance(val2, int | float):
                # Numeric similarity
                if val1 != 0 or val2 != 0:
                    similarity = 1 - abs(val1 - val2) / max(abs(val1), abs(val2))
                    if similarity > 0.8:
                        matches += similarity

        return matches / len(all_keys)

    def _calculate_structural_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any]
    ) -> float:
        """Calculate structural similarity"""
        content1 = memory1.get("content", "")
        content2 = memory2.get("content", "")

        # Length similarity
        len1, len2 = len(content1), len(content2)
        if len1 == 0 and len2 == 0:
            length_similarity = 1.0
        else:
            max_len = max(len1, len2)
            length_similarity = 1 - abs(len1 - len2) / max_len if max_len > 0 else 1.0

        # Word count similarity
        words1 = len(content1.split())
        words2 = len(content2.split())
        if words1 == 0 and words2 == 0:
            word_similarity = 1.0
        else:
            max_words = max(words1, words2)
            word_similarity = 1 - abs(words1 - words2) / max_words if max_words > 0 else 1.0

        return (length_similarity + word_similarity) / 2

    def _find_existing_group(
        self, groups: list[DuplicateGroup], memory_ids: list[str]
    ) -> DuplicateGroup | None:
        """Find existing group containing any of the memory IDs"""
        for group in groups:
            if any(memory_id in group.memory_ids for memory_id in memory_ids):
                return group
        return None

    def _select_primary_memory(
        self, memories: list[dict[str, Any]], strategy: MergeStrategy
    ) -> str:
        """Select primary memory based on strategy"""
        if strategy == MergeStrategy.KEEP_LONGEST:
            longest = max(memories, key=lambda m: len(m.get("content", "")))
            return longest.get("id", "unknown")
        else:
            return memories[0].get("id", "unknown")


class SemanticSimilarityDetector:
    """Detector for semantic similarity"""

    async def find_duplicates(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """Find semantically similar memories"""
        # Simplified semantic similarity using keyword overlap
        # In a real implementation, this would use embeddings

        duplicate_groups = []

        # Extract keywords from each memory
        memory_keywords = []
        for memory in memories:
            keywords = await self._extract_keywords(memory.get("content", ""))
            memory_keywords.append({"memory": memory, "keywords": keywords})

        # Compare memories for semantic similarity
        processed_pairs = set()

        for i in range(len(memory_keywords)):
            for j in range(i + 1, len(memory_keywords)):
                pair_key = tuple(sorted([i, j]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                memory1_data = memory_keywords[i]
                memory2_data = memory_keywords[j]

                similarity = await self._calculate_semantic_similarity(
                    memory1_data, memory2_data, config
                )

                if similarity.overall_similarity >= config.similarity_threshold:
                    group_id = f"semantic_{hashlib.md5(f'{i}_{j}'.encode()).hexdigest()[:8]}"
                    memory_ids = [
                        memory1_data["memory"].get("id", f"mem_{i}"),
                        memory2_data["memory"].get("id", f"mem_{j}"),
                    ]

                    primary_memory_id = self._select_primary_memory(
                        [memory1_data["memory"], memory2_data["memory"]], config.merge_strategy
                    )

                    duplicate_groups.append(
                        DuplicateGroup(
                            group_id=group_id,
                            memory_ids=memory_ids,
                            primary_memory_id=primary_memory_id,
                            similarity_scores=[similarity],
                            merge_strategy=config.merge_strategy,
                        )
                    )

        return duplicate_groups

    async def _extract_keywords(self, content: str) -> set[str]:
        """Extract keywords from content"""
        # Simple keyword extraction
        words = re.findall(r"\b\w+\b", content.lower())

        # Filter common words and short words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        keywords = {word for word in words if len(word) > 3 and word not in stop_words}

        return keywords

    async def _calculate_semantic_similarity(
        self,
        memory1_data: dict[str, Any],
        memory2_data: dict[str, Any],
        config: DeduplicationConfig,
    ) -> SimilarityScore:
        """Calculate semantic similarity between memories"""
        keywords1 = memory1_data["keywords"]
        keywords2 = memory2_data["keywords"]

        # Jaccard similarity for keywords
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        content_similarity = intersection / union if union > 0 else 0.0

        # Metadata similarity
        metadata_similarity = self._calculate_metadata_similarity(
            memory1_data["memory"], memory2_data["memory"]
        )

        # Structural similarity
        structural_similarity = self._calculate_structural_similarity(
            memory1_data["memory"], memory2_data["memory"]
        )

        # Overall similarity
        overall_similarity = (
            content_similarity * config.content_weight
            + metadata_similarity * config.metadata_weight
            + structural_similarity * config.structural_weight
        )

        return SimilarityScore(
            memory_id_1=memory1_data["memory"].get("id", "unknown"),
            memory_id_2=memory2_data["memory"].get("id", "unknown"),
            content_similarity=content_similarity,
            metadata_similarity=metadata_similarity,
            structural_similarity=structural_similarity,
            overall_similarity=overall_similarity,
            method_used=SimilarityMethod.SEMANTIC_SIMILARITY,
            confidence=0.7,
            reasoning=f"Semantic similarity with {intersection} common keywords out of {union} total",
        )

    def _calculate_metadata_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any]
    ) -> float:
        """Calculate metadata similarity"""
        metadata1 = memory1.get("metadata", {})
        metadata2 = memory2.get("metadata", {})

        common_keys = set(metadata1.keys()) & set(metadata2.keys())
        if not common_keys:
            return 0.0

        matches = sum(1 for key in common_keys if metadata1[key] == metadata2[key])
        return matches / len(common_keys)

    def _calculate_structural_similarity(
        self, memory1: dict[str, Any], memory2: dict[str, Any]
    ) -> float:
        """Calculate structural similarity"""
        content1 = memory1.get("content", "")
        content2 = memory2.get("content", "")

        len1, len2 = len(content1), len(content2)
        max_len = max(len1, len2)

        if max_len == 0:
            return 1.0

        return 1 - abs(len1 - len2) / max_len

    def _select_primary_memory(
        self, memories: list[dict[str, Any]], strategy: MergeStrategy
    ) -> str:
        """Select primary memory based on strategy"""
        return memories[0].get("id", "unknown")


class MemoryDeduplicationEngine:
    """Advanced memory deduplication engine"""

    def __init__(self):
        self.detectors = {
            SimilarityMethod.EXACT_MATCH: ExactMatchDetector(),
            SimilarityMethod.FUZZY_MATCH: FuzzyMatchDetector(),
            SimilarityMethod.SEMANTIC_SIMILARITY: SemanticSimilarityDetector(),
        }
        self.deduplication_history = []

    async def deduplicate_memories(
        self, config: DeduplicationConfig, memory_filter: dict[str, Any] | None = None
    ) -> DeduplicationResult:
        """Perform memory deduplication"""
        start_time = time.time()

        result = DeduplicationResult(
            total_memories=0,
            duplicate_groups_found=0,
            total_duplicates=0,
            memories_merged=0,
            memories_deleted=0,
            memories_marked=0,
            processing_time=0.0,
            duplicate_groups=[],
            performance_metrics={},
            errors=[],
            warnings=[],
        )

        try:
            # Get memories to process
            db = await get_database()
            memories = await self._get_memories_for_deduplication(db, memory_filter)
            result.total_memories = len(memories)

            if result.total_memories == 0:
                result.warnings.append("No memories found for deduplication")
                return result

            # Find duplicate groups
            duplicate_groups = await self._find_duplicate_groups(memories, config)
            result.duplicate_groups = duplicate_groups
            result.duplicate_groups_found = len(duplicate_groups)

            # Count total duplicates
            result.total_duplicates = sum(len(group.memory_ids) - 1 for group in duplicate_groups)

            # Process duplicates if not dry run
            if not config.dry_run:
                processing_result = await self._process_duplicate_groups(
                    duplicate_groups, config, db
                )
                result.memories_merged = processing_result["merged"]
                result.memories_deleted = processing_result["deleted"]
                result.memories_marked = processing_result["marked"]
                result.errors.extend(processing_result["errors"])

            await db.close()

        except Exception as e:
            result.errors.append(f"Deduplication failed: {str(e)}")

        result.processing_time = time.time() - start_time
        result.performance_metrics = self._calculate_performance_metrics(result)

        # Save to history
        self.deduplication_history.append(result)

        return result

    async def _get_memories_for_deduplication(
        self, db, memory_filter: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Get memories for deduplication based on filter"""
        all_memories = await db.get_all_memories(limit=10000)

        if not memory_filter:
            return all_memories

        filtered_memories = []
        for memory in all_memories:
            if self._matches_filter(memory, memory_filter):
                filtered_memories.append(memory)

        return filtered_memories

    def _matches_filter(self, memory: dict[str, Any], filter_criteria: dict[str, Any]) -> bool:
        """Check if memory matches filter criteria"""
        for key, value in filter_criteria.items():
            if key == "memory_type" and memory.get("metadata", {}).get("memory_type") != value:
                return False
            elif key == "created_after" and memory.get("created_at", "") < value:
                return False
            elif key == "created_before" and memory.get("created_at", "") > value:
                return False
            elif key == "min_length" and len(memory.get("content", "")) < value:
                return False
            elif key == "max_length" and len(memory.get("content", "")) > value:
                return False
        return True

    async def _find_duplicate_groups(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """Find duplicate groups using specified method"""
        if config.similarity_method == SimilarityMethod.HYBRID:
            return await self._find_duplicates_hybrid(memories, config)
        else:
            detector = self.detectors.get(config.similarity_method)
            if not detector:
                raise ValueError(f"Unknown similarity method: {config.similarity_method}")

            return await detector.find_duplicates(memories, config)

    async def _find_duplicates_hybrid(
        self, memories: list[dict[str, Any]], config: DeduplicationConfig
    ) -> list[DuplicateGroup]:
        """Find duplicates using hybrid approach"""
        all_groups = []

        # Run all detection methods
        for method in [
            SimilarityMethod.EXACT_MATCH,
            SimilarityMethod.FUZZY_MATCH,
            SimilarityMethod.SEMANTIC_SIMILARITY,
        ]:
            detector = self.detectors[method]
            groups = await detector.find_duplicates(memories, config)
            all_groups.extend(groups)

        # Merge overlapping groups
        merged_groups = self._merge_overlapping_groups(all_groups)

        return merged_groups

    def _merge_overlapping_groups(self, groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
        """Merge overlapping duplicate groups"""
        if not groups:
            return []

        merged_groups = []
        processed_memory_ids = set()

        for group in groups:
            # Check if any memory in this group is already processed
            if any(memory_id in processed_memory_ids for memory_id in group.memory_ids):
                # Find existing group to merge with
                for merged_group in merged_groups:
                    if any(memory_id in merged_group.memory_ids for memory_id in group.memory_ids):
                        # Merge groups
                        for memory_id in group.memory_ids:
                            if memory_id not in merged_group.memory_ids:
                                merged_group.memory_ids.append(memory_id)
                        merged_group.similarity_scores.extend(group.similarity_scores)
                        break
            else:
                # Add as new group
                merged_groups.append(group)
                processed_memory_ids.update(group.memory_ids)

        return merged_groups

    async def _process_duplicate_groups(
        self, duplicate_groups: list[DuplicateGroup], config: DeduplicationConfig, db
    ) -> dict[str, Any]:
        """Process duplicate groups according to configuration"""
        result = {"merged": 0, "deleted": 0, "marked": 0, "errors": []}

        for group in duplicate_groups:
            try:
                if config.duplicate_action == DuplicateAction.MERGE:
                    await self._merge_memories(group, config, db)
                    result["merged"] += len(group.memory_ids) - 1
                elif config.duplicate_action == DuplicateAction.DELETE_DUPLICATE:
                    await self._delete_duplicates(group, config, db)
                    result["deleted"] += len(group.memory_ids) - 1
                elif config.duplicate_action == DuplicateAction.MARK_DUPLICATE:
                    await self._mark_duplicates(group, config, db)
                    result["marked"] += len(group.memory_ids) - 1

                group.action_taken = config.duplicate_action

            except Exception as e:
                result["errors"].append(f"Failed to process group {group.group_id}: {str(e)}")

        return result

    async def _merge_memories(self, group: DuplicateGroup, config: DeduplicationConfig, db):
        """Merge duplicate memories"""
        # Get all memories in the group
        memories = []
        for memory_id in group.memory_ids:
            memory = await db.get_memory(memory_id)
            if memory:
                memories.append(memory)

        if not memories:
            return

        # Create merged content and metadata
        merged_content, merged_metadata = await self._create_merged_memory(
            memories, group.merge_strategy, config
        )

        group.merged_content = merged_content
        group.merged_metadata = merged_metadata

        # In a real implementation, this would:
        # 1. Update the primary memory with merged content
        # 2. Delete the duplicate memories
        # 3. Update references to point to the primary memory

    async def _delete_duplicates(self, group: DuplicateGroup, config: DeduplicationConfig, db):
        """Delete duplicate memories, keeping primary"""
        for memory_id in group.memory_ids:
            if memory_id != group.primary_memory_id:
                # In a real implementation, this would delete the memory
                pass

    async def _mark_duplicates(self, group: DuplicateGroup, config: DeduplicationConfig, db):
        """Mark memories as duplicates without deleting"""
        for memory_id in group.memory_ids:
            if memory_id != group.primary_memory_id:
                # In a real implementation, this would update metadata to mark as duplicate
                pass

    async def _create_merged_memory(
        self, memories: list[dict[str, Any]], strategy: MergeStrategy, config: DeduplicationConfig
    ) -> tuple[str, dict[str, Any]]:
        """Create merged content and metadata from duplicate memories"""
        if strategy == MergeStrategy.SMART_MERGE:
            # Smart merge: combine the best parts of each memory
            longest_content = max(memories, key=lambda m: len(m.get("content", "")))["content"]

            # Merge metadata
            merged_metadata = {}
            for memory in memories:
                metadata = memory.get("metadata", {})
                for key, value in metadata.items():
                    if key not in merged_metadata:
                        merged_metadata[key] = value
                    elif key == "tags" and isinstance(value, list):
                        if isinstance(merged_metadata[key], list):
                            merged_metadata[key] = list(set(merged_metadata[key] + value))

            # Add deduplication metadata
            merged_metadata["deduplication_info"] = {
                "merged_from": [m.get("id") for m in memories],
                "merge_strategy": strategy.value,
                "merged_at": datetime.now().isoformat(),
            }

            return longest_content, merged_metadata

        else:
            # Use primary memory based on strategy
            primary_memory = memories[0]  # Simplified
            return primary_memory.get("content", ""), primary_memory.get("metadata", {})

    def _calculate_performance_metrics(self, result: DeduplicationResult) -> dict[str, Any]:
        """Calculate performance metrics"""
        if result.total_memories == 0:
            return {}

        duplicate_rate = result.total_duplicates / result.total_memories
        processing_rate = (
            result.total_memories / result.processing_time if result.processing_time > 0 else 0
        )

        return {
            "duplicate_rate": duplicate_rate,
            "processing_rate_per_second": processing_rate,
            "groups_per_second": (
                result.duplicate_groups_found / result.processing_time
                if result.processing_time > 0
                else 0
            ),
            "efficiency_score": 1 - len(result.errors) / max(1, result.total_memories),
        }

    def get_deduplication_statistics(self) -> dict[str, Any]:
        """Get deduplication engine statistics"""
        if not self.deduplication_history:
            return {"total_runs": 0}

        total_runs = len(self.deduplication_history)
        total_memories_processed = sum(r.total_memories for r in self.deduplication_history)
        total_duplicates_found = sum(r.total_duplicates for r in self.deduplication_history)

        avg_duplicate_rate = (
            total_duplicates_found / total_memories_processed if total_memories_processed > 0 else 0
        )

        return {
            "total_runs": total_runs,
            "total_memories_processed": total_memories_processed,
            "total_duplicates_found": total_duplicates_found,
            "average_duplicate_rate": avg_duplicate_rate,
            "available_methods": list(self.detectors.keys()),
        }


# Global deduplication engine
memory_deduplication_engine = MemoryDeduplicationEngine()


async def get_memory_deduplication_engine() -> MemoryDeduplicationEngine:
    """Get memory deduplication engine instance"""
    return memory_deduplication_engine
