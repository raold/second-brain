"""
Memory Consolidation Engine for v2.8.2
Intelligently merge and consolidate related memories
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.interfaces.memory_database_interface import MemoryDatabaseInterface
from app.models.synthesis.consolidation_models import (
    ConsolidatedMemory,
    ConsolidationCandidate,
    ConsolidationPreview,
    ConsolidationRequest,
    ConsolidationStrategy,
)
from app.services.knowledge_graph_builder import KnowledgeGraphBuilder
from app.services.reasoning_engine import ReasoningEngine

logger = logging.getLogger(__name__)


class MemoryConsolidationEngine:
    """Engine for finding and consolidating related memories"""

    def __init__(
        self,
        db: MemoryDatabaseInterface,
        graph_builder: KnowledgeGraphBuilder,
        reasoning_engine: ReasoningEngine
    ):
        self.db = db
        self.graph_builder = graph_builder
        self.reasoning_engine = reasoning_engine
        self.openai = get_openai_client()

    async def find_consolidation_candidates(
        self,
        similarity_threshold: float = 0.85,
        time_window_days: int = 30,
        max_candidates: int = 10,
        min_group_size: int = 2,
        max_group_size: int = 10
    ) -> list[ConsolidationCandidate]:
        """Find groups of memories that could be consolidated"""

        # Get recent memories
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        recent_memories = await self.db.search_memories_by_date_range(
            start_date=cutoff_date,
            end_date=datetime.utcnow()
        )

        if len(recent_memories) < min_group_size:
            return []

        # Build similarity matrix
        memory_ids = [m.id for m in recent_memories]
        embeddings = [m.content_vector for m in recent_memories if m.content_vector]

        if len(embeddings) < len(recent_memories):
            # Some memories missing embeddings
            logger.warning(f"Only {len(embeddings)}/{len(recent_memories)} memories have embeddings")

        similarity_matrix = self._calculate_similarity_matrix(embeddings)

        # Find clusters of similar memories
        clusters = self._find_similarity_clusters(
            similarity_matrix,
            memory_ids,
            similarity_threshold,
            min_group_size,
            max_group_size
        )

        # Analyze each cluster to create candidates
        candidates = []
        for cluster_ids in clusters[:max_candidates]:
            cluster_memories = [m for m in recent_memories if m.id in cluster_ids]

            # Extract common elements
            common_entities = self._find_common_elements([m.metadata.get("entities", []) for m in cluster_memories])
            common_topics = self._find_common_elements([m.metadata.get("topics", []) for m in cluster_memories])
            common_tags = self._find_common_elements([m.tags for m in cluster_memories])

            # Get reasoning paths between memories
            reasoning_paths = await self._get_reasoning_paths(cluster_ids[:3])  # Limit for performance

            # Determine best strategy
            strategy = self._suggest_consolidation_strategy(
                cluster_memories,
                common_entities,
                common_topics,
                common_tags
            )

            # Calculate quality score
            quality = self._estimate_consolidation_quality(
                cluster_memories,
                len(common_entities),
                len(common_topics),
                len(reasoning_paths)
            )

            candidates.append(ConsolidationCandidate(
                memory_ids=cluster_ids,
                similarity_score=self._calculate_cluster_similarity(cluster_ids, similarity_matrix, memory_ids),
                common_entities=common_entities,
                common_topics=common_topics,
                common_tags=common_tags,
                reasoning_paths=reasoning_paths,
                suggested_strategy=strategy,
                estimated_quality=quality,
                explanation=self._generate_consolidation_explanation(
                    len(cluster_ids),
                    strategy,
                    common_topics[:3]
                )
            ))

        return sorted(candidates, key=lambda x: x.estimated_quality, reverse=True)

    async def preview_consolidation(
        self,
        request: ConsolidationRequest
    ) -> ConsolidationPreview:
        """Preview what a consolidation would produce without executing it"""

        # Fetch memories
        memories = await self.db.get_memories_by_ids(request.memory_ids)

        if len(memories) != len(request.memory_ids):
            raise ValueError("Could not find all requested memories")

        # Generate consolidated content based on strategy
        consolidated_content = await self._generate_consolidated_content(
            memories,
            request.strategy,
            request.additional_context
        )

        # Generate title
        consolidated_title = request.custom_title or await self._generate_consolidated_title(
            memories,
            request.strategy
        )

        # Merge metadata
        merged_entities = self._merge_unique_elements([m.metadata.get("entities", []) for m in memories])
        merged_topics = self._merge_unique_elements([m.metadata.get("topics", []) for m in memories])
        merged_tags = self._merge_unique_elements([m.tags for m in memories])

        # Calculate importance
        base_importance = np.mean([m.importance for m in memories])
        importance = min(10.0, base_importance + request.importance_boost)

        # Quality assessment
        quality = await self._assess_consolidation_quality(
            memories,
            consolidated_content,
            request.strategy
        )

        # Check for warnings
        warnings = self._check_consolidation_warnings(memories, consolidated_content)

        # Estimate token reduction
        original_tokens = sum(len(m.content.split()) for m in memories) * 1.3  # Rough estimate
        consolidated_tokens = len(consolidated_content.split()) * 1.3
        token_reduction = int(original_tokens - consolidated_tokens)

        return ConsolidationPreview(
            original_memories=[m.dict() for m in memories],
            consolidated_content=consolidated_content,
            consolidated_title=consolidated_title,
            merged_entities=merged_entities,
            merged_topics=merged_topics,
            merged_tags=merged_tags,
            importance_score=importance,
            quality_assessment=quality,
            warnings=warnings,
            estimated_token_reduction=token_reduction
        )

    async def consolidate_memories(
        self,
        request: ConsolidationRequest
    ) -> ConsolidatedMemory:
        """Execute memory consolidation"""

        # Get preview first
        preview = await self.preview_consolidation(request)

        # Create new consolidated memory
        new_memory_data = {
            "content": preview.consolidated_content,
            "importance": preview.importance_score,
            "tags": preview.merged_tags,
            "metadata": {
                "title": preview.consolidated_title,
                "entities": preview.merged_entities,
                "topics": preview.merged_topics,
                "consolidation": {
                    "strategy": request.strategy.value,
                    "original_ids": [str(id) for id in request.memory_ids],
                    "quality_score": preview.quality_assessment.get("overall", 0.0),
                    "token_reduction": preview.estimated_token_reduction
                }
            }
        }

        # Store consolidated memory
        new_memory = await self.db.store_memory(**new_memory_data)

        # Update lineage tracking
        await self._update_memory_lineage(
            new_memory.id,
            request.memory_ids,
            request.strategy
        )

        # Archive originals if requested
        if not request.preserve_originals:
            await self._archive_original_memories(request.memory_ids)

        # Create result
        return ConsolidatedMemory(
            id=new_memory.id,
            content=new_memory.content,
            title=preview.consolidated_title,
            original_memory_ids=request.memory_ids,
            consolidation_strategy=request.strategy,
            entities=preview.merged_entities,
            topics=preview.merged_topics,
            tags=preview.merged_tags,
            importance=new_memory.importance,
            metadata=new_memory.metadata,
            lineage={
                "parent_ids": [str(id) for id in request.memory_ids],
                "strategy": request.strategy.value,
                "consolidated_at": datetime.utcnow().isoformat()
            },
            created_at=new_memory.created_at,
            token_count=len(new_memory.content.split()),
            quality_score=preview.quality_assessment.get("overall", 0.0)
        )

    # Helper methods

    def _calculate_similarity_matrix(self, embeddings: list[np.ndarray]) -> np.ndarray:
        """Calculate pairwise similarity matrix"""
        if not embeddings:
            return np.array([])
        embeddings_array = np.array(embeddings)
        return cosine_similarity(embeddings_array)

    def _find_similarity_clusters(
        self,
        similarity_matrix: np.ndarray,
        memory_ids: list[UUID],
        threshold: float,
        min_size: int,
        max_size: int
    ) -> list[list[UUID]]:
        """Find clusters of similar memories"""
        n = len(memory_ids)
        visited = set()
        clusters = []

        for i in range(n):
            if i in visited:
                continue

            # Find all memories similar to this one
            cluster_indices = {i}
            queue = [i]

            while queue and len(cluster_indices) < max_size:
                current = queue.pop(0)

                for j in range(n):
                    if j not in cluster_indices and similarity_matrix[current][j] >= threshold:
                        cluster_indices.add(j)
                        queue.append(j)

            if len(cluster_indices) >= min_size:
                clusters.append([memory_ids[idx] for idx in cluster_indices])
                visited.update(cluster_indices)

        return clusters

    def _find_common_elements(self, element_lists: list[list[str]]) -> list[str]:
        """Find elements common to multiple lists"""
        if not element_lists:
            return []

        # Count occurrences
        element_counts = {}
        for elements in element_lists:
            for element in elements:
                element_counts[element] = element_counts.get(element, 0) + 1

        # Return elements that appear in at least half the lists
        min_count = len(element_lists) / 2
        return [e for e, count in element_counts.items() if count >= min_count]

    def _merge_unique_elements(self, element_lists: list[list[str]]) -> list[str]:
        """Merge and deduplicate elements from multiple lists"""
        all_elements = set()
        for elements in element_lists:
            all_elements.update(elements)
        return sorted(list(all_elements))

    async def _get_reasoning_paths(self, memory_ids: list[UUID]) -> list[str]:
        """Get reasoning paths between memories"""
        paths = []

        # Get paths between pairs
        for i in range(len(memory_ids)):
            for j in range(i + 1, min(i + 2, len(memory_ids))):  # Limit for performance
                try:
                    result = await self.reasoning_engine.find_reasoning_path(
                        start_id=memory_ids[i],
                        end_id=memory_ids[j],
                        max_hops=3
                    )
                    if result and result.path:
                        paths.append(f"{memory_ids[i]} -> {memory_ids[j]}")
                except Exception as e:
                    logger.error(f"Error finding reasoning path: {e}")

        return paths

    def _suggest_consolidation_strategy(
        self,
        memories: list[Any],
        common_entities: list[str],
        common_topics: list[str],
        common_tags: list[str]
    ) -> ConsolidationStrategy:
        """Suggest the best consolidation strategy"""

        # Check for chronological sequence
        dates = [m.created_at for m in memories]
        if self._is_chronological_sequence(dates):
            return ConsolidationStrategy.CHRONOLOGICAL

        # Check for entity focus
        if len(common_entities) >= 3:
            return ConsolidationStrategy.ENTITY_FOCUSED

        # Check for topic coherence
        if len(common_topics) >= 2:
            return ConsolidationStrategy.TOPIC_BASED

        # Default to merge similar
        return ConsolidationStrategy.MERGE_SIMILAR

    def _is_chronological_sequence(self, dates: list[datetime]) -> bool:
        """Check if dates form a chronological sequence"""
        if len(dates) < 2:
            return False

        sorted_dates = sorted(dates)
        gaps = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]

        # Check if gaps are relatively uniform and small
        if max(gaps) <= 7 and np.std(gaps) < 2:
            return True

        return False

    def _estimate_consolidation_quality(
        self,
        memories: list[Any],
        common_entities: int,
        common_topics: int,
        reasoning_paths: int
    ) -> float:
        """Estimate the quality of a potential consolidation"""

        # Base score on content overlap
        base_score = 0.5

        # Boost for common elements
        if common_entities > 0:
            base_score += min(0.2, common_entities * 0.05)
        if common_topics > 0:
            base_score += min(0.2, common_topics * 0.1)
        if reasoning_paths > 0:
            base_score += min(0.1, reasoning_paths * 0.05)

        # Penalty for too many memories
        if len(memories) > 5:
            base_score -= (len(memories) - 5) * 0.05

        return max(0.0, min(1.0, base_score))

    def _calculate_cluster_similarity(
        self,
        cluster_ids: list[UUID],
        similarity_matrix: np.ndarray,
        all_ids: list[UUID]
    ) -> float:
        """Calculate average similarity within a cluster"""
        indices = [all_ids.index(id) for id in cluster_ids if id in all_ids]

        if len(indices) < 2:
            return 0.0

        similarities = []
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                similarities.append(similarity_matrix[indices[i]][indices[j]])

        return np.mean(similarities) if similarities else 0.0

    def _generate_consolidation_explanation(
        self,
        memory_count: int,
        strategy: ConsolidationStrategy,
        top_topics: list[str]
    ) -> str:
        """Generate human-readable explanation for consolidation suggestion"""

        strategy_explanations = {
            ConsolidationStrategy.MERGE_SIMILAR: "have very similar content",
            ConsolidationStrategy.CHRONOLOGICAL: "form a chronological sequence",
            ConsolidationStrategy.TOPIC_BASED: f"share common topics: {', '.join(top_topics)}",
            ConsolidationStrategy.ENTITY_FOCUSED: "refer to the same entities",
            ConsolidationStrategy.HIERARCHICAL: "can be organized hierarchically"
        }

        explanation = strategy_explanations.get(strategy, "are related")
        return f"Found {memory_count} memories that {explanation} and could be consolidated."

    async def _generate_consolidated_content(
        self,
        memories: list[Any],
        strategy: ConsolidationStrategy,
        additional_context: Optional[str] = None
    ) -> str:
        """Generate consolidated content using GPT-4"""

        # Prepare content based on strategy
        if strategy == ConsolidationStrategy.CHRONOLOGICAL:
            sorted_memories = sorted(memories, key=lambda m: m.created_at)
            prompt = self._build_chronological_prompt(sorted_memories, additional_context)
        elif strategy == ConsolidationStrategy.ENTITY_FOCUSED:
            prompt = self._build_entity_focused_prompt(memories, additional_context)
        elif strategy == ConsolidationStrategy.TOPIC_BASED:
            prompt = self._build_topic_based_prompt(memories, additional_context)
        else:  # MERGE_SIMILAR
            prompt = self._build_merge_similar_prompt(memories, additional_context)

        # Generate with GPT-4
        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at consolidating and summarizing information while preserving key details."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating consolidated content: {e}")
            # Fallback to simple concatenation
            return self._fallback_consolidation(memories)

    def _build_chronological_prompt(self, memories: list[Any], context: Optional[str]) -> str:
        """Build prompt for chronological consolidation"""
        memory_texts = []
        for m in memories:
            date_str = m.created_at.strftime("%Y-%m-%d")
            memory_texts.append(f"[{date_str}] {m.content}")

        prompt = f"""Consolidate these chronologically ordered memories into a coherent narrative:

{chr(10).join(memory_texts)}

Create a unified summary that preserves the temporal flow and key information from each memory.
"""
        if context:
            prompt += f"\nAdditional context: {context}"

        return prompt

    def _build_entity_focused_prompt(self, memories: list[Any], context: Optional[str]) -> str:
        """Build prompt for entity-focused consolidation"""
        # Extract common entities
        all_entities = []
        for m in memories:
            all_entities.extend(m.metadata.get("entities", []))

        entity_counts = {}
        for e in all_entities:
            entity_counts[e] = entity_counts.get(e, 0) + 1

        key_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        memory_texts = [m.content for m in memories]

        prompt = f"""Consolidate these memories that all relate to these key entities: {', '.join([e[0] for e in key_entities])}

Memories:
{chr(10).join(f'- {text}' for text in memory_texts)}

Create a comprehensive summary organized around these entities, preserving all important relationships and facts.
"""
        if context:
            prompt += f"\nAdditional context: {context}"

        return prompt

    def _build_topic_based_prompt(self, memories: list[Any], context: Optional[str]) -> str:
        """Build prompt for topic-based consolidation"""
        # Extract common topics
        all_topics = []
        for m in memories:
            all_topics.extend(m.metadata.get("topics", []))

        topic_counts = {}
        for t in all_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1

        key_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        memory_texts = [m.content for m in memories]

        prompt = f"""Consolidate these memories that share common topics: {', '.join([t[0] for t in key_topics])}

Memories:
{chr(10).join(f'- {text}' for text in memory_texts)}

Create a well-organized summary that groups information by topic while maintaining coherence.
"""
        if context:
            prompt += f"\nAdditional context: {context}"

        return prompt

    def _build_merge_similar_prompt(self, memories: list[Any], context: Optional[str]) -> str:
        """Build prompt for merging similar memories"""
        memory_texts = [m.content for m in memories]

        prompt = f"""Merge these similar memories into a single, comprehensive memory:

{chr(10).join(f'Memory {i+1}: {text}' for i, text in enumerate(memory_texts))}

Combine the information, remove redundancies, and create a unified memory that captures all unique details.
"""
        if context:
            prompt += f"\nAdditional context: {context}"

        return prompt

    def _fallback_consolidation(self, memories: list[Any]) -> str:
        """Simple fallback consolidation method"""
        consolidated = "Consolidated Memory:\n\n"

        for i, m in enumerate(memories):
            consolidated += f"Part {i+1} (from {m.created_at.strftime('%Y-%m-%d')}):\n"
            consolidated += f"{m.content}\n\n"

        return consolidated.strip()

    async def _generate_consolidated_title(
        self,
        memories: list[Any],
        strategy: ConsolidationStrategy
    ) -> str:
        """Generate a title for the consolidated memory"""

        # Extract key elements
        all_topics = []
        all_entities = []

        for m in memories:
            all_topics.extend(m.metadata.get("topics", []))
            all_entities.extend(m.metadata.get("entities", []))

        # Get most common
        if all_topics:
            main_topic = max(set(all_topics), key=all_topics.count)
        else:
            main_topic = "Consolidated Memory"

        if all_entities:
            main_entity = max(set(all_entities), key=all_entities.count)
        else:
            main_entity = None

        # Build title based on strategy
        if strategy == ConsolidationStrategy.CHRONOLOGICAL:
            date_range = f"{memories[0].created_at.strftime('%b %d')} - {memories[-1].created_at.strftime('%b %d, %Y')}"
            title = f"{main_topic}: {date_range}"
        elif strategy == ConsolidationStrategy.ENTITY_FOCUSED and main_entity:
            title = f"{main_entity}: {main_topic}"
        else:
            title = f"{main_topic} (Consolidated)"

        return title

    async def _assess_consolidation_quality(
        self,
        original_memories: list[Any],
        consolidated_content: str,
        strategy: ConsolidationStrategy
    ) -> dict[str, float]:
        """Assess the quality of a consolidation"""

        quality_metrics = {
            "information_preservation": 0.0,
            "coherence": 0.0,
            "conciseness": 0.0,
            "readability": 0.0,
            "overall": 0.0
        }

        # Information preservation - check if key entities/topics are preserved
        original_entities = set()
        original_topics = set()

        for m in original_memories:
            original_entities.update(m.metadata.get("entities", []))
            original_topics.update(m.metadata.get("topics", []))

        preserved_entities = sum(1 for e in original_entities if e.lower() in consolidated_content.lower())
        preserved_topics = sum(1 for t in original_topics if t.lower() in consolidated_content.lower())

        if original_entities:
            quality_metrics["information_preservation"] = preserved_entities / len(original_entities)
        else:
            quality_metrics["information_preservation"] = 0.8  # Default if no entities

        # Coherence - based on strategy appropriateness
        strategy_coherence = {
            ConsolidationStrategy.CHRONOLOGICAL: 0.9,
            ConsolidationStrategy.ENTITY_FOCUSED: 0.85,
            ConsolidationStrategy.TOPIC_BASED: 0.85,
            ConsolidationStrategy.MERGE_SIMILAR: 0.8,
            ConsolidationStrategy.HIERARCHICAL: 0.75
        }
        quality_metrics["coherence"] = strategy_coherence.get(strategy, 0.8)

        # Conciseness - ratio of consolidated to original length
        original_length = sum(len(m.content) for m in original_memories)
        consolidated_length = len(consolidated_content)

        if original_length > 0:
            compression_ratio = consolidated_length / original_length
            # Ideal compression between 0.3 and 0.7
            if 0.3 <= compression_ratio <= 0.7:
                quality_metrics["conciseness"] = 1.0
            elif compression_ratio < 0.3:
                quality_metrics["conciseness"] = compression_ratio / 0.3
            else:
                quality_metrics["conciseness"] = max(0.5, 1.0 - (compression_ratio - 0.7))
        else:
            quality_metrics["conciseness"] = 0.8

        # Readability - simple heuristic based on sentence length
        sentences = consolidated_content.split('.')
        avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()])

        if 10 <= avg_sentence_length <= 20:
            quality_metrics["readability"] = 1.0
        elif avg_sentence_length < 10:
            quality_metrics["readability"] = avg_sentence_length / 10
        else:
            quality_metrics["readability"] = max(0.5, 1.0 - (avg_sentence_length - 20) / 20)

        # Overall score
        quality_metrics["overall"] = np.mean([
            quality_metrics["information_preservation"],
            quality_metrics["coherence"],
            quality_metrics["conciseness"],
            quality_metrics["readability"]
        ])

        return quality_metrics

    def _check_consolidation_warnings(
        self,
        memories: list[Any],
        consolidated_content: str
    ) -> list[str]:
        """Check for potential issues with consolidation"""
        warnings = []

        # Check for significant information loss
        original_length = sum(len(m.content) for m in memories)
        if len(consolidated_content) < original_length * 0.2:
            warnings.append("Significant compression detected - some details may be lost")

        # Check for conflicting information
        dates = set()
        for m in memories:
            # Extract dates mentioned in content (simple heuristic)
            import re
            date_pattern = r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}'
            found_dates = re.findall(date_pattern, m.content)
            dates.update(found_dates)

        if len(dates) > 5:
            warnings.append("Multiple dates detected - verify temporal consistency")

        # Check for different importance levels
        importance_values = [m.importance for m in memories]
        if max(importance_values) - min(importance_values) > 5:
            warnings.append("Memories have significantly different importance levels")

        # Check for special content types
        for m in memories:
            if "code" in m.tags or "```" in m.content:
                warnings.append("Contains code snippets - verify formatting is preserved")
                break

        return warnings

    async def _update_memory_lineage(
        self,
        new_memory_id: UUID,
        original_ids: list[UUID],
        strategy: ConsolidationStrategy
    ) -> None:
        """Update memory lineage tracking"""
        # This would be implemented with actual database operations
        # For now, it's a placeholder
        logger.info(f"Updated lineage for {new_memory_id} from {len(original_ids)} parents")

    async def _archive_original_memories(self, memory_ids: list[UUID]) -> None:
        """Archive original memories after consolidation"""
        # This would mark memories as archived in the database
        # For now, it's a placeholder
        logger.info(f"Archived {len(memory_ids)} original memories")
