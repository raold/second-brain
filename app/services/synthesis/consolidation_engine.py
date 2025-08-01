from datetime import datetime
from typing import Any
from uuid import UUID
import numpy as np
from app.models.synthesis.consolidation_models import ConsolidationResult
from app.utils.logging_config import get_logger
from app.events.domain_events import MemoryConsolidatedEvent, ConsolidationEvent
from collections import defaultdict
from app.models.synthesis.consolidation_models import (

"""Consolidation Engine for Memory Deduplication and Merging

Real implementation that detects duplicate/similar memories and consolidates
them intelligently while preserving important information.
"""

    ConsolidationRequest,
    DuplicateGroup,
    MergeStrategy,
)

logger = get_logger(__name__)

class MemorySimilarity:
    """Represents similarity between two memories"""

    def __init__(
        self, memory1_id: UUID, memory2_id: UUID, similarity_score: float, similarity_type: str
    ):
        self.memory1_id = memory1_id
        self.memory2_id = memory2_id
        self.similarity_score = similarity_score
        self.similarity_type = similarity_type  # 'exact', 'semantic', 'partial'

class ConsolidationEngine:
    """Engine for detecting and consolidating duplicate or similar memories"""

    def __init__(self, db, memory_service, openai_client):
        self.db = db
        self.memory_service = memory_service
        self.openai_client = openai_client

        # Similarity thresholds
        self.exact_threshold = 0.95
        self.high_similarity_threshold = 0.85
        self.moderate_similarity_threshold = 0.70

        # Merge strategy templates
        self.merge_templates = {
            MergeStrategy.KEEP_NEWEST: "Keep the most recent version",
            MergeStrategy.KEEP_OLDEST: "Keep the original version",
            MergeStrategy.MERGE_CONTENT: """
Merge these similar memories into a single comprehensive memory that:
1. Combines unique information from both
2. Resolves any contradictions
3. Maintains chronological context
4. Preserves important metadata

Memory 1: {memory1}
Memory 2: {memory2}

Create a merged version that captures all valuable information.
""",
            MergeStrategy.CREATE_SUMMARY: """
These memories are related. Create a summary that:
1. Captures the essence of all memories
2. Notes the evolution of ideas if applicable
3. Highlights the most important points
4. Maintains context

Memories:
{memories}

Create a concise summary that preserves key information.
""",
        }

    async def analyze_duplicates(self, request: ConsolidationRequest) -> list[DuplicateGroup]:
        """Analyze memories for duplicates and similarities"""
        try:
            # Fetch memories with embeddings
            memories = await self._fetch_memories_with_embeddings(request.memory_ids)
            if len(memories) < 2:
                logger.info("Not enough memories for duplicate analysis")
                return []

            # Find similarities
            similarities = await self._find_similarities(memories, request)

            # Group similar memories
            duplicate_groups = self._create_duplicate_groups(memories, similarities)

            # Add consolidation suggestions
            for group in duplicate_groups:
                group.suggested_action = await self._suggest_consolidation_action(group)

            return duplicate_groups

        except Exception as e:
            logger.error(f"Duplicate analysis failed: {e}")
            return []

    async def consolidate_memories(
        self, duplicate_group: DuplicateGroup, strategy: MergeStrategy | None = None
    ) -> ConsolidationResult:
        """Consolidate a group of duplicate memories"""
        try:
            # Use suggested strategy if none provided
            if not strategy:
                strategy = duplicate_group.suggested_action or MergeStrategy.KEEP_NEWEST

            # Fetch full memory data
            memories = await self._fetch_full_memories(duplicate_group.memory_ids)

            # Apply consolidation strategy
            if strategy == MergeStrategy.KEEP_NEWEST:
                result = await self._keep_newest_strategy(memories)
            elif strategy == MergeStrategy.KEEP_OLDEST:
                result = await self._keep_oldest_strategy(memories)
            elif strategy == MergeStrategy.MERGE_CONTENT:
                result = await self._merge_content_strategy(memories)
            elif strategy == MergeStrategy.CREATE_SUMMARY:
                result = await self._create_summary_strategy(memories)
            else:
                raise ValueError(f"Unknown merge strategy: {strategy}")

            return result

        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            raise

    async def _fetch_memories_with_embeddings(
        self, memory_ids: list[UUID] | None
    ) -> list[dict[str, Any]]:
        """Fetch memories with their embeddings"""
        if memory_ids:
            # Fetch specific memories
            placeholders = ",".join(f"${i+1}" for i in range(len(memory_ids)))
            query = f"""
            SELECT id, content, content_vector, importance, created_at, updated_at, tags
            FROM memories
            WHERE id IN ({placeholders})
            AND content_vector IS NOT NULL
            """
            memories = await self.db.fetch_all(query, *memory_ids)
        else:
            # Fetch all memories with embeddings (limited for performance)
            query = """
            SELECT id, content, content_vector, importance, created_at, updated_at, tags
            FROM memories
            WHERE content_vector IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1000
            """
            memories = await self.db.fetch_all(query)

        # Convert to dict format
        return [
            {
                "id": m["id"],
                "content": m["content"],
                "embedding": np.array(m["content_vector"]) if m["content_vector"] else None,
                "importance": m["importance"],
                "created_at": m["created_at"],
                "updated_at": m["updated_at"],
                "tags": m.get("tags", []),
            }
            for m in memories
        ]

    async def _find_similarities(
        self, memories: list[dict[str, Any]], request: ConsolidationRequest
    ) -> list[MemorySimilarity]:
        """Find similarities between memories"""
        similarities = []

        # Extract embeddings
        embeddings = np.array([m["embedding"] for m in memories if m["embedding"] is not None])
        memory_ids = [m["id"] for m in memories if m["embedding"] is not None]

        if len(embeddings) < 2:
            return similarities

        # Calculate cosine similarities
        similarity_matrix = cosine_similarity(embeddings)

        # Find similar pairs
        for i in range(len(memory_ids)):
            for j in range(i + 1, len(memory_ids)):
                sim_score = similarity_matrix[i][j]

                # Check exact match
                if sim_score >= self.exact_threshold:
                    similarity_type = "exact"
                elif sim_score >= self.high_similarity_threshold:
                    similarity_type = "semantic"
                elif sim_score >= self.moderate_similarity_threshold:
                    similarity_type = "partial"
                else:
                    continue  # Skip low similarities

                # Additional content-based checking for exact matches
                if similarity_type == "exact":
                    content1 = memories[i]["content"].strip().lower()
                    content2 = memories[j]["content"].strip().lower()
                    if content1 != content2:
                        similarity_type = "semantic"  # Downgrade if content differs

                similarities.append(
                    MemorySimilarity(
                        memory_ids[i], memory_ids[j], float(sim_score), similarity_type
                    )
                )

        # Apply threshold filter
        if request.similarity_threshold:
            similarities = [
                s for s in similarities if s.similarity_score >= request.similarity_threshold
            ]

        return similarities

    def _create_duplicate_groups(
        self, memories: list[dict[str, Any]], similarities: list[MemorySimilarity]
    ) -> list[DuplicateGroup]:
        """Group memories into duplicate clusters"""
        # Create adjacency list
        adjacency = defaultdict(set)
        for sim in similarities:
            adjacency[sim.memory1_id].add(sim.memory2_id)
            adjacency[sim.memory2_id].add(sim.memory1_id)

        # Find connected components (duplicate groups)
        visited = set()
        groups = []

        def dfs(memory_id: UUID, current_group: Set[UUID]):
            """Depth-first search to find connected components"""
            if memory_id in visited:
                return
            visited.add(memory_id)
            current_group.add(memory_id)
            for neighbor in adjacency[memory_id]:
                dfs(neighbor, current_group)

        # Create groups
        for memory in memories:
            memory_id = memory["id"]
            if memory_id not in visited and memory_id in adjacency:
                current_group = set()
                dfs(memory_id, current_group)

                if len(current_group) > 1:  # Only groups with 2+ memories
                    # Calculate group similarity score
                    group_sims = []
                    group_ids = list(current_group)
                    for i in range(len(group_ids)):
                        for j in range(i + 1, len(group_ids)):
                            for sim in similarities:
                                if (
                                    sim.memory1_id == group_ids[i]
                                    and sim.memory2_id == group_ids[j]
                                ) or (
                                    sim.memory1_id == group_ids[j]
                                    and sim.memory2_id == group_ids[i]
                                ):
                                    group_sims.append(sim.similarity_score)

                    avg_similarity = sum(group_sims) / len(group_sims) if group_sims else 0.0

                    # Determine duplicate type
                    if avg_similarity >= self.exact_threshold:
                        duplicate_type = "exact"
                    elif avg_similarity >= self.high_similarity_threshold:
                        duplicate_type = "near_duplicate"
                    else:
                        duplicate_type = "similar"

                    groups.append(
                        DuplicateGroup(
                            memory_ids=list(current_group),
                            similarity_score=avg_similarity,
                            duplicate_type=duplicate_type,
                            group_summary=f"Group of {len(current_group)} {duplicate_type} memories",
                        )
                    )

        # Sort by similarity score
        groups.sort(key=lambda g: g.similarity_score, reverse=True)

        return groups

    async def _suggest_consolidation_action(self, group: DuplicateGroup) -> MergeStrategy:
        """Suggest the best consolidation action for a duplicate group"""
        # For exact duplicates, keep the newest
        if group.duplicate_type == "exact":
            return MergeStrategy.KEEP_NEWEST

        # For near duplicates, analyze content differences
        memories = await self._fetch_full_memories(group.memory_ids[:2])  # Sample first two

        if not memories:
            return MergeStrategy.KEEP_NEWEST

        # Check content length differences
        content_lengths = [len(m["content"]) for m in memories]
        length_variance = np.var(content_lengths)

        # If one is significantly longer, merge content
        if length_variance > 10000:  # Significant length difference
            return MergeStrategy.MERGE_CONTENT

        # For similar memories with moderate overlap, create summary
        if group.duplicate_type == "similar":
            return MergeStrategy.CREATE_SUMMARY

        # Default to merging content for near duplicates
        return MergeStrategy.MERGE_CONTENT

    async def _fetch_full_memories(self, memory_ids: list[UUID]) -> list[dict[str, Any]]:
        """Fetch complete memory data"""
        memories = []
        for memory_id in memory_ids:
            try:
                memory = await self.memory_service.get_memory(str(memory_id))
                if memory:
                    memories.append(
                        {
                            "id": memory_id,
                            "content": memory.content,
                            "importance": memory.importance_score,
                            "created_at": memory.created_at,
                            "updated_at": getattr(memory, "updated_at", memory.created_at),
                            "tags": getattr(memory, "tags", []),
                            "metadata": getattr(memory, "metadata", {}),
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to fetch memory {memory_id}: {e}")

        return memories

    async def _keep_newest_strategy(self, memories: list[dict[str, Any]]) -> ConsolidationResult:
        """Keep only the newest memory"""
        # Sort by updated_at or created_at
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get("updated_at", m.get("created_at", datetime.min)),
            reverse=True,
        )

        kept_memory = sorted_memories[0]
        removed_ids = [m["id"] for m in sorted_memories[1:]]

        return ConsolidationResult(
            kept_memory_id=kept_memory["id"],
            removed_memory_ids=removed_ids,
            new_content=None,
            merge_metadata={
                "strategy": "keep_newest",
                "kept_date": kept_memory.get(
                    "updated_at", kept_memory.get("created_at")
                ).isoformat(),
                "removed_count": len(removed_ids),
            },
        )

    async def _keep_oldest_strategy(self, memories: list[dict[str, Any]]) -> ConsolidationResult:
        """Keep only the oldest memory"""
        # Sort by created_at
        sorted_memories = sorted(memories, key=lambda m: m.get("created_at", datetime.max))

        kept_memory = sorted_memories[0]
        removed_ids = [m["id"] for m in sorted_memories[1:]]

        return ConsolidationResult(
            kept_memory_id=kept_memory["id"],
            removed_memory_ids=removed_ids,
            new_content=None,
            merge_metadata={
                "strategy": "keep_oldest",
                "kept_date": kept_memory.get("created_at").isoformat(),
                "removed_count": len(removed_ids),
            },
        )

    async def _merge_content_strategy(self, memories: list[dict[str, Any]]) -> ConsolidationResult:
        """Merge content from multiple memories"""
        if len(memories) < 2:
            return await self._keep_newest_strategy(memories)

        # Prepare content for merging
        memory1 = memories[0]
        memory2 = memories[1]

        prompt = self.merge_templates[MergeStrategy.MERGE_CONTENT].format(
            memory1=memory1["content"], memory2=memory2["content"]
        )

        try:
            # Use LLM to merge content
            merged_content = await self.openai_client.generate(
                prompt=prompt, max_tokens=1000, temperature=0.3
            )

            # Merge metadata
            merged_tags = list(set(memory1.get("tags", []) + memory2.get("tags", [])))

            # Keep the oldest memory ID, update its content
            oldest_memory = min(memories, key=lambda m: m.get("created_at", datetime.max))
            removed_ids = [m["id"] for m in memories if m["id"] != oldest_memory["id"]]

            return ConsolidationResult(
                kept_memory_id=oldest_memory["id"],
                removed_memory_ids=removed_ids,
                new_content=merged_content,
                merge_metadata={
                    "strategy": "merge_content",
                    "merged_from": len(memories),
                    "merged_tags": merged_tags,
                    "original_lengths": [len(m["content"]) for m in memories],
                    "merged_length": len(merged_content),
                },
            )

        except Exception as e:
            logger.error(f"Content merge failed: {e}")
            # Fallback to keeping newest
            return await self._keep_newest_strategy(memories)

    async def _create_summary_strategy(self, memories: list[dict[str, Any]]) -> ConsolidationResult:
        """Create a summary of related memories"""
        # Format memories for summarization
        memory_texts = []
        for i, memory in enumerate(memories[:10]):  # Limit to prevent token overflow
            memory_texts.append(f"{i+1}. {memory['content']}")

        memories_formatted = "\n\n".join(memory_texts)

        prompt = self.merge_templates[MergeStrategy.CREATE_SUMMARY].format(
            memories=memories_formatted
        )

        try:
            # Generate summary
            summary_content = await self.openai_client.generate(
                prompt=prompt, max_tokens=800, temperature=0.5
            )

            # Add metadata about summarized memories
            summary_content += f"\n\n[Summary of {len(memories)} related memories]"

            # Create new summary memory, keep originals
            return ConsolidationResult(
                kept_memory_id=None,  # New memory will be created
                removed_memory_ids=[],  # Keep all originals
                new_content=summary_content,
                merge_metadata={
                    "strategy": "create_summary",
                    "summarized_count": len(memories),
                    "source_memory_ids": [str(m["id"]) for m in memories],
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Summary creation failed: {e}")
            # Fallback: don't remove anything
            return ConsolidationResult(
                kept_memory_id=memories[0]["id"],
                removed_memory_ids=[],
                new_content=None,
                merge_metadata={"strategy": "failed", "error": str(e)},
            )

    async def bulk_consolidate(self, request: ConsolidationRequest) -> dict[str, Any]:
        """Perform bulk consolidation on all similar memories"""
        try:
            # Find all duplicate groups
            duplicate_groups = await self.analyze_duplicates(request)

            if not duplicate_groups:
                return {
                    "status": "complete",
                    "groups_found": 0,
                    "memories_consolidated": 0,
                    "memories_removed": 0,
                }

            # Auto-consolidate based on thresholds
            consolidation_results = []
            total_removed = 0

            for group in duplicate_groups:
                # Auto-consolidate exact duplicates
                if group.duplicate_type == "exact" or (
                    request.auto_merge and group.similarity_score >= 0.9
                ):

                    result = await self.consolidate_memories(group)
                    consolidation_results.append(result)
                    total_removed += len(result.removed_memory_ids)

            return {
                "status": "complete",
                "groups_found": len(duplicate_groups),
                "groups_consolidated": len(consolidation_results),
                "memories_removed": total_removed,
                "duplicate_groups": duplicate_groups,
                "consolidation_results": consolidation_results,
            }

        except Exception as e:
            logger.error(f"Bulk consolidation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "groups_found": 0,
                "memories_consolidated": 0,
            }
