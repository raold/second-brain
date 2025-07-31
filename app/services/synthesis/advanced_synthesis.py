"""Advanced Synthesis Engine Service

Real implementation of memory synthesis using hierarchical processing,
theme extraction, and LLM-powered consolidation.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.models.synthesis.advanced_models import SynthesisRequest, SynthesisResult, SynthesisStrategy
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ThemeCluster:
    """Represents a thematic cluster of memories"""

    def __init__(self, theme: str, memories: list[dict[str, Any]]):
        self.theme = theme
        self.memories = memories
        self.sub_themes: list[ThemeCluster] = []
        self.importance_score = self._calculate_importance()

    def _calculate_importance(self) -> float:
        """Calculate cluster importance based on memory metrics"""
        if not self.memories:
            return 0.0

        # Average importance of memories in cluster
        avg_importance = sum(m.get('importance', 5) for m in self.memories) / len(self.memories)

        # Size factor (more memories = more important)
        size_factor = min(len(self.memories) / 10, 1.0)

        # Recency factor
        latest_date = max(m.get('created_at', datetime.min) for m in self.memories)
        days_old = (datetime.utcnow() - latest_date).days
        recency_factor = max(0, 1 - (days_old / 365))  # Linear decay over a year

        # Combined score
        return (avg_importance / 10) * 0.5 + size_factor * 0.3 + recency_factor * 0.2

    def add_sub_theme(self, sub_cluster: 'ThemeCluster'):
        """Add a sub-theme cluster"""
        self.sub_themes.append(sub_cluster)


class AdvancedSynthesisEngine:
    """Advanced synthesis engine for memory processing with real implementation"""

    def __init__(self, db, memory_service, relationship_analyzer, openai_client):
        self.db = db
        self.memory_service = memory_service
        self.relationship_analyzer = relationship_analyzer
        self.openai_client = openai_client

        # Synthesis templates for different strategies
        self.synthesis_templates = {
            SynthesisStrategy.SUMMARY: """
You are an expert knowledge synthesizer. Analyze these memories and create a comprehensive summary that:
1. Identifies the main themes and concepts
2. Highlights key insights and patterns
3. Preserves important details while removing redundancy
4. Creates a coherent narrative flow

Memories to synthesize:
{memories}

Create a well-structured summary that captures the essence of these memories.
""",
            SynthesisStrategy.ANALYSIS: """
You are an analytical AI assistant. Perform a deep analysis of these memories to:
1. Identify patterns, trends, and correlations
2. Extract causal relationships and dependencies
3. Highlight contradictions or gaps in knowledge
4. Provide actionable insights and recommendations

Memories to analyze:
{memories}

Provide a thorough analytical report with clear sections and insights.
""",
            SynthesisStrategy.REPORT: """
You are a professional report writer. Create a structured report from these memories that:
1. Has clear sections with headings
2. Includes an executive summary
3. Presents information in a logical flow
4. Adds context and connections between ideas
5. Concludes with key takeaways

Memories for report:
{memories}

Generate a professional report suitable for knowledge management.
""",
            SynthesisStrategy.TIMELINE: """
You are a temporal analyst. Create a chronological synthesis that:
1. Orders events and ideas by time
2. Identifies cause-and-effect relationships
3. Highlights evolution of concepts over time
4. Marks important milestones and turning points

Memories for timeline:
{memories}

Create a narrative that shows the temporal progression of ideas and events.
"""
        }

    async def synthesize_memories(self, request: SynthesisRequest) -> list[SynthesisResult]:
        """Synthesize memories using advanced hierarchical processing"""
        try:
            # Fetch memories
            memories = await self._fetch_memories(request.memory_ids)
            if not memories:
                logger.warning("No memories found for synthesis")
                return []

            # Extract themes and create clusters
            theme_clusters = await self._extract_themes_and_cluster(memories)

            # Build hierarchical structure
            hierarchy = await self._build_hierarchy(theme_clusters)

            # Generate synthesis based on strategy
            if request.strategy == SynthesisStrategy.TIMELINE:
                synthesis_results = await self._synthesize_timeline(memories, hierarchy, request)
            else:
                synthesis_results = await self._synthesize_hierarchical(hierarchy, request)

            return synthesis_results

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Return a basic synthesis as fallback
            return [await self._create_fallback_synthesis(request)]

    async def _fetch_memories(self, memory_ids: list[UUID]) -> list[dict[str, Any]]:
        """Fetch memories with their content and metadata"""
        memories = []

        for memory_id in memory_ids:
            try:
                memory = await self.memory_service.get_memory(str(memory_id))
                if memory:
                    memories.append({
                        'id': memory_id,
                        'content': memory.content,
                        'importance': memory.importance_score,
                        'created_at': memory.created_at,
                        'tags': getattr(memory, 'tags', []),
                        'metadata': getattr(memory, 'metadata', {})
                    })
            except Exception as e:
                logger.error(f"Failed to fetch memory {memory_id}: {e}")

        return memories

    async def _extract_themes_and_cluster(self, memories: list[dict[str, Any]]) -> list[ThemeCluster]:
        """Extract themes and cluster memories"""
        # Group by explicit tags first
        tag_groups = defaultdict(list)
        untagged = []

        for memory in memories:
            tags = memory.get('tags', [])
            if tags:
                for tag in tags:
                    tag_groups[tag].append(memory)
            else:
                untagged.append(memory)

        # Create clusters from tag groups
        clusters = []
        for tag, tag_memories in tag_groups.items():
            clusters.append(ThemeCluster(tag, tag_memories))

        # Use LLM to find themes in untagged memories
        if untagged:
            implicit_themes = await self._extract_implicit_themes(untagged)
            clusters.extend(implicit_themes)

        return clusters

    async def _extract_implicit_themes(self, memories: list[dict[str, Any]]) -> list[ThemeCluster]:
        """Use LLM to extract themes from untagged memories"""
        # Prepare content for theme extraction
        memory_texts = [f"- {m['content'][:200]}..." for m in memories[:20]]  # Limit to prevent token overflow

        prompt = f"""
Analyze these memory excerpts and identify 3-5 main themes or topics:

{chr(10).join(memory_texts)}

Return themes as a JSON array of strings. Be specific but not too granular.
Example: ["Machine Learning Fundamentals", "Python Best Practices", "Database Design"]
"""

        try:
            response = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )

            # Parse themes
            themes = json.loads(response.strip())

            # Assign memories to themes based on content similarity
            theme_clusters = []
            for theme in themes:
                theme_memories = await self._find_memories_for_theme(theme, memories)
                if theme_memories:
                    theme_clusters.append(ThemeCluster(theme, theme_memories))

            # Handle any remaining memories
            assigned_ids = set()
            for cluster in theme_clusters:
                assigned_ids.update(m['id'] for m in cluster.memories)

            unassigned = [m for m in memories if m['id'] not in assigned_ids]
            if unassigned:
                theme_clusters.append(ThemeCluster("Miscellaneous", unassigned))

            return theme_clusters

        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            # Fallback: create a single cluster
            return [ThemeCluster("General", memories)]

    async def _find_memories_for_theme(self, theme: str, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find memories that match a theme using semantic similarity"""
        # Simple keyword matching for now
        # In production, use embeddings for semantic similarity
        theme_lower = theme.lower()
        theme_words = set(theme_lower.split())

        matched_memories = []
        for memory in memories:
            content_lower = memory['content'].lower()
            content_words = set(content_lower.split())

            # Check for word overlap
            overlap = theme_words.intersection(content_words)
            if overlap or theme_lower in content_lower:
                matched_memories.append(memory)

        return matched_memories

    async def _build_hierarchy(self, clusters: list[ThemeCluster]) -> ThemeCluster:
        """Build hierarchical structure from clusters"""
        # Sort clusters by importance
        sorted_clusters = sorted(clusters, key=lambda c: c.importance_score, reverse=True)

        # For now, create a simple two-level hierarchy
        # Top-level: most important cluster or a meta-cluster
        if len(sorted_clusters) == 1:
            return sorted_clusters[0]

        # Create meta-cluster
        all_memories = []
        for cluster in clusters:
            all_memories.extend(cluster.memories)

        root = ThemeCluster("Knowledge Synthesis", all_memories)

        # Add original clusters as sub-themes
        for cluster in sorted_clusters:
            root.add_sub_theme(cluster)

        return root

    async def _synthesize_hierarchical(
        self,
        hierarchy: ThemeCluster,
        request: SynthesisRequest
    ) -> list[SynthesisResult]:
        """Generate synthesis from hierarchical structure"""
        results = []

        # Synthesize root level
        root_synthesis = await self._synthesize_cluster(hierarchy, request)
        results.append(root_synthesis)

        # Optionally synthesize sub-themes
        if request.options.get('include_sub_themes', True) and hierarchy.sub_themes:
            for sub_theme in hierarchy.sub_themes[:3]:  # Limit to top 3 sub-themes
                sub_synthesis = await self._synthesize_cluster(sub_theme, request, is_sub_theme=True)
                results.append(sub_synthesis)

        return results

    async def _synthesize_cluster(
        self,
        cluster: ThemeCluster,
        request: SynthesisRequest,
        is_sub_theme: bool = False
    ) -> SynthesisResult:
        """Synthesize a single cluster"""
        # Prepare memory content
        memory_texts = []
        for i, memory in enumerate(cluster.memories[:20]):  # Limit to prevent token overflow
            memory_texts.append(f"{i+1}. {memory['content']}")

        memories_formatted = "\n\n".join(memory_texts)

        # Get appropriate template
        template = self.synthesis_templates.get(
            request.strategy,
            self.synthesis_templates[SynthesisStrategy.SUMMARY]
        )

        # Add context for sub-themes
        if is_sub_theme:
            template = f"This is a sub-theme analysis for '{cluster.theme}'.\n\n" + template

        # Generate synthesis
        prompt = template.format(memories=memories_formatted)

        try:
            synthesis_content = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            # Add references if requested
            if request.include_references:
                references = self._format_references(cluster.memories)
                synthesis_content += f"\n\n**References:**\n{references}"

            return SynthesisResult(
                id=uuid4(),
                synthesis_type=request.strategy.value,
                content=synthesis_content,
                source_memory_ids=[m['id'] for m in cluster.memories],
                confidence_score=cluster.importance_score,
                metadata={
                    "theme": cluster.theme,
                    "is_sub_theme": is_sub_theme,
                    "memory_count": len(cluster.memories),
                    "strategy": request.strategy.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Cluster synthesis failed: {e}")
            return await self._create_fallback_synthesis(request, cluster.memories)

    async def _synthesize_timeline(
        self,
        memories: list[dict[str, Any]],
        hierarchy: ThemeCluster,
        request: SynthesisRequest
    ) -> list[SynthesisResult]:
        """Create timeline-based synthesis"""
        # Sort memories by date
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get('created_at', datetime.min)
        )

        # Group by time periods
        time_groups = self._group_by_time_period(sorted_memories)

        # Generate timeline synthesis
        timeline_parts = []
        for period, period_memories in time_groups.items():
            period_summary = await self._synthesize_time_period(period, period_memories)
            timeline_parts.append(period_summary)

        # Combine into final timeline
        timeline_content = "\n\n".join(timeline_parts)

        # Add overall narrative
        narrative_prompt = f"""
Based on this timeline of events and ideas, create a narrative that shows the evolution and connections over time:

{timeline_content}

Focus on cause-and-effect relationships and the progression of concepts.
"""

        try:
            narrative = await self.openai_client.generate(
                prompt=narrative_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            final_content = f"# Timeline Synthesis\n\n{narrative}\n\n## Detailed Timeline\n\n{timeline_content}"

            return [SynthesisResult(
                id=uuid4(),
                synthesis_type=SynthesisStrategy.TIMELINE.value,
                content=final_content,
                source_memory_ids=[m['id'] for m in memories],
                confidence_score=0.85,
                metadata={
                    "periods": len(time_groups),
                    "span_days": (sorted_memories[-1]['created_at'] - sorted_memories[0]['created_at']).days,
                    "strategy": SynthesisStrategy.TIMELINE.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )]

        except Exception as e:
            logger.error(f"Timeline synthesis failed: {e}")
            return [await self._create_fallback_synthesis(request, memories)]

    def _group_by_time_period(self, memories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group memories by time period"""
        from collections import OrderedDict

        groups = OrderedDict()

        for memory in memories:
            date = memory.get('created_at', datetime.utcnow())
            # Group by month
            date.strftime("%Y-%m")
            period_label = date.strftime("%B %Y")

            if period_label not in groups:
                groups[period_label] = []
            groups[period_label].append(memory)

        return groups

    async def _synthesize_time_period(
        self,
        period: str,
        memories: list[dict[str, Any]]
    ) -> str:
        """Synthesize memories from a specific time period"""
        memory_summaries = []
        for memory in memories[:10]:  # Limit per period
            date_str = memory['created_at'].strftime("%Y-%m-%d")
            summary = f"[{date_str}] {memory['content'][:100]}..."
            memory_summaries.append(summary)

        return f"### {period}\n\n" + "\n".join(memory_summaries)

    def _format_references(self, memories: list[dict[str, Any]]) -> str:
        """Format memory references"""
        references = []
        for i, memory in enumerate(memories[:10]):  # Limit references
            ref = f"{i+1}. Memory {memory['id']} - Created: {memory['created_at'].strftime('%Y-%m-%d')}"
            references.append(ref)

        if len(memories) > 10:
            references.append(f"... and {len(memories) - 10} more memories")

        return "\n".join(references)

    async def _create_fallback_synthesis(
        self,
        request: SynthesisRequest,
        memories: list[dict[str, Any]] | None = None
    ) -> SynthesisResult:
        """Create a basic fallback synthesis"""
        if memories:
            content = f"Synthesis of {len(memories)} memories:\n\n"
            for i, memory in enumerate(memories[:5]):
                content += f"{i+1}. {memory['content'][:100]}...\n"
            if len(memories) > 5:
                content += f"\n... and {len(memories) - 5} more memories."
        else:
            content = "Unable to generate detailed synthesis. Please try again."

        return SynthesisResult(
            id=uuid4(),
            synthesis_type=request.strategy.value,
            content=content,
            source_memory_ids=request.memory_ids,
            confidence_score=0.5,
            metadata={
                "fallback": True,
                "strategy": request.strategy.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
