"""
Knowledge Summarization Service for v2.8.2
Generate intelligent summaries using GPT-4 and graph context
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import numpy as np

from app.interfaces.memory_database_interface import MemoryDatabaseInterface
from app.models.synthesis.summary_models import (
    ExecutiveSummary,
    PeriodSummary,
    TopicSummary,
)
from app.services.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)


class KnowledgeSummarizer:
    """Service for generating various types of knowledge summaries"""

    def __init__(
        self,
        db: MemoryDatabaseInterface,
        graph_builder: KnowledgeGraphBuilder,
        topic_analyzer: Optional[Any] = None
    ):
        self.db = db
        self.graph_builder = graph_builder
        self.topic_analyzer = topic_analyzer
        self.openai = get_openai_client()

    async def summarize_topic(
        self,
        topic: str,
        time_range: Optional[dict[str, datetime]] = None,
        max_memories: int = 50,
        include_related: bool = True
    ) -> TopicSummary:
        """Generate comprehensive summary for a specific topic"""

        start_time = datetime.utcnow()

        # Search for memories related to the topic
        memories = await self._get_topic_memories(topic, time_range, max_memories)

        if not memories:
            return self._create_empty_topic_summary(topic)

        # Extract entities and subtopics
        entities, subtopics = await self._extract_topic_elements(memories)

        # Build context from graph relationships
        graph_context = await self._build_graph_context(memories[:10])  # Limit for performance

        # Generate summary using GPT-4
        summary_text = await self._generate_topic_summary(
            topic,
            memories,
            entities,
            subtopics,
            graph_context
        )

        # Extract key insights
        insights = await self._extract_key_insights(summary_text, topic)

        # Calculate confidence based on memory quality and quantity
        confidence = self._calculate_summary_confidence(memories, len(insights))

        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return TopicSummary(
            topic=topic,
            summary=summary_text,
            key_insights=insights,
            related_entities=[{"name": e, "count": c} for e, c in entities.most_common(10)],
            related_topics=list(subtopics)[:10],
            memory_count=len(memories),
            time_range=time_range,
            confidence_score=confidence,
            word_count=len(summary_text.split()),
            generated_at=datetime.utcnow(),
            metadata={
                "generation_time_ms": generation_time,
                "included_related": include_related,
                "graph_context_used": bool(graph_context)
            }
        )

    async def summarize_time_period(
        self,
        start_date: datetime,
        end_date: datetime,
        focus_areas: Optional[list[str]] = None,
        max_memories: int = 100
    ) -> PeriodSummary:
        """Summarize knowledge from a specific time period"""

        # Get memories from time period
        memories = await self.db.search_memories_by_date_range(
            start_date=start_date,
            end_date=end_date,
            limit=max_memories
        )

        if not memories:
            return self._create_empty_period_summary(start_date, end_date)

        # Filter by focus areas if specified
        if focus_areas:
            memories = self._filter_by_focus_areas(memories, focus_areas)

        # Analyze period content
        period_analysis = await self._analyze_period_content(memories)

        # Generate period summary
        summary_text = await self._generate_period_summary(
            memories,
            start_date,
            end_date,
            period_analysis
        )

        # Extract highlights
        highlights = await self._extract_period_highlights(memories, period_analysis)

        # Identify trends
        trends = self._identify_period_trends(memories, period_analysis)

        # Get top memories by importance
        top_memories = sorted(memories, key=lambda m: m.importance, reverse=True)[:10]

        period_type = self._determine_period_type(start_date, end_date)

        return PeriodSummary(
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            summary=summary_text,
            highlights=highlights,
            new_topics=period_analysis["new_topics"],
            new_entities=period_analysis["new_entities"],
            top_memories=[self._memory_to_dict(m) for m in top_memories],
            statistics=period_analysis["statistics"],
            trends=trends,
            generated_at=datetime.utcnow()
        )

    async def generate_executive_summary(
        self,
        memory_ids: list[UUID],
        include_graph: bool = True,
        style: str = "professional"
    ) -> ExecutiveSummary:
        """Generate executive summary with actionable insights"""

        start_time = datetime.utcnow()

        # Fetch memories
        memories = await self.db.get_memories_by_ids(memory_ids)

        if not memories:
            raise ValueError("No memories found for provided IDs")

        # Build comprehensive context
        context = await self._build_executive_context(memories)

        # Generate graph visualization data if requested
        graph_data = None
        if include_graph:
            graph_data = await self._generate_graph_visualization(memories)

        # Generate executive summary using GPT-4
        summary_components = await self._generate_executive_components(
            memories,
            context,
            style
        )

        # Extract actionable elements
        action_items = await self._extract_action_items(memories, context)
        questions = await self._extract_questions(memories, context)
        opportunities = await self._identify_opportunities(memories, context)
        risks = await self._identify_risks(memories, context)

        # Calculate metrics
        metrics = self._calculate_executive_metrics(memories, context)

        # Assess confidence
        confidence = self._calculate_executive_confidence(
            memories,
            len(action_items),
            len(questions)
        )

        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecutiveSummary(
            title=summary_components["title"],
            summary=summary_components["summary"],
            key_points=summary_components["key_points"],
            action_items=action_items,
            questions_raised=questions,
            opportunities=opportunities,
            risks=risks,
            memory_ids=memory_ids,
            graph_visualization=graph_data,
            metrics=metrics,
            confidence_score=confidence,
            generated_at=datetime.utcnow(),
            generation_time_ms=generation_time
        )

    # Helper methods

    async def _get_topic_memories(
        self,
        topic: str,
        time_range: Optional[dict[str, datetime]],
        max_memories: int
    ) -> list[Any]:
        """Get memories related to a topic"""

        # Search by topic in content and metadata
        query = f"{topic} OR tags:{topic} OR metadata.topics:{topic}"

        memories = await self.db.search_memories(
            query=query,
            limit=max_memories
        )

        # Filter by time range if specified
        if time_range:
            memories = [
                m for m in memories
                if time_range.get("start", datetime.min) <= m.created_at <= time_range.get("end", datetime.max)
            ]

        return memories

    async def _extract_topic_elements(
        self,
        memories: list[Any]
    ) -> tuple[Counter, set]:
        """Extract entities and subtopics from memories"""

        entities = Counter()
        subtopics = set()

        for memory in memories:
            # Extract from metadata
            memory_entities = memory.metadata.get("entities", [])
            memory_topics = memory.metadata.get("topics", [])

            entities.update(memory_entities)
            subtopics.update(memory_topics)

            # Extract from tags
            subtopics.update(memory.tags)

        return entities, subtopics

    async def _build_graph_context(self, memories: list[Any]) -> dict[str, Any]:
        """Build context from knowledge graph"""

        if not memories:
            return {}

        try:
            # Build mini graph from these memories
            memory_ids = [m.id for m in memories]
            graph_data = await self.graph_builder.build_graph_from_memories(
                memory_ids=memory_ids,
                include_relationships=True
            )

            # Extract key patterns
            context = {
                "central_entities": self._get_central_entities(graph_data),
                "key_relationships": self._get_key_relationships(graph_data),
                "clusters": self._identify_clusters(graph_data)
            }

            return context

        except Exception as e:
            logger.error(f"Error building graph context: {e}")
            return {}

    def _get_central_entities(self, graph_data: dict[str, Any]) -> list[str]:
        """Get most central entities from graph"""
        nodes = graph_data.get("nodes", [])
        # Sort by degree (number of connections)
        sorted_nodes = sorted(nodes, key=lambda n: len(n.get("connections", [])), reverse=True)
        return [n["name"] for n in sorted_nodes[:5]]

    def _get_key_relationships(self, graph_data: dict[str, Any]) -> list[dict[str, str]]:
        """Get most important relationships"""
        edges = graph_data.get("edges", [])
        # Sort by weight/importance
        sorted_edges = sorted(edges, key=lambda e: e.get("weight", 1.0), reverse=True)
        return [
            {
                "source": e["source"],
                "target": e["target"],
                "type": e.get("type", "related_to")
            }
            for e in sorted_edges[:10]
        ]

    def _identify_clusters(self, graph_data: dict[str, Any]) -> list[list[str]]:
        """Identify clusters in the graph"""
        # Simple clustering based on connected components
        # In a real implementation, this would use proper graph algorithms
        return []

    async def _generate_topic_summary(
        self,
        topic: str,
        memories: list[Any],
        entities: Counter,
        subtopics: set,
        graph_context: dict[str, Any]
    ) -> str:
        """Generate topic summary using GPT-4"""

        # Prepare memory content
        memory_texts = []
        for i, m in enumerate(memories[:20]):  # Limit to prevent token overflow
            memory_texts.append(f"{i+1}. {m.content[:200]}...")

        # Build context string
        context_parts = []

        if entities:
            top_entities = ", ".join([e for e, _ in entities.most_common(5)])
            context_parts.append(f"Key entities: {top_entities}")

        if subtopics:
            top_subtopics = ", ".join(list(subtopics)[:5])
            context_parts.append(f"Related topics: {top_subtopics}")

        if graph_context.get("central_entities"):
            central = ", ".join(graph_context["central_entities"])
            context_parts.append(f"Central concepts: {central}")

        context_string = "\n".join(context_parts)

        # Generate summary
        prompt = f"""Create a comprehensive summary about "{topic}" based on the following memories and context.

Context:
{context_string}

Memories:
{chr(10).join(memory_texts)}

Create a well-structured summary that:
1. Explains the main concepts and ideas about {topic}
2. Highlights important relationships and connections
3. Identifies patterns or trends
4. Provides a coherent narrative

Keep the summary between 200-500 words."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at synthesizing information and creating insightful summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating topic summary: {e}")
            return self._fallback_topic_summary(topic, memories)

    def _fallback_topic_summary(self, topic: str, memories: list[Any]) -> str:
        """Fallback summary generation"""
        summary = f"Summary of {topic}:\n\n"
        summary += f"Based on {len(memories)} memories:\n\n"

        # Group by date
        by_date = defaultdict(list)
        for m in memories[:10]:
            date_key = m.created_at.strftime("%Y-%m-%d")
            by_date[date_key].append(m.content[:100])

        for date, contents in sorted(by_date.items()):
            summary += f"\n{date}:\n"
            for content in contents:
                summary += f"- {content}...\n"

        return summary

    async def _extract_key_insights(self, summary: str, topic: str) -> list[str]:
        """Extract key insights from summary"""

        prompt = f"""Extract 3-5 key insights from this summary about {topic}.

Summary:
{summary}

Format each insight as a clear, actionable statement. Focus on:
- Important discoveries or patterns
- Practical applications
- Future implications
- Surprising connections

Return only the insights, one per line."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying key insights and takeaways."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )

            insights_text = response.choices[0].message.content.strip()
            insights = [line.strip() for line in insights_text.split('\n') if line.strip()]

            return insights[:5]  # Limit to 5

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return [f"Key finding about {topic}", "Further investigation recommended"]

    def _calculate_summary_confidence(self, memories: list[Any], insight_count: int) -> float:
        """Calculate confidence score for summary"""

        base_score = 0.5

        # More memories increase confidence
        memory_score = min(0.3, len(memories) * 0.01)

        # Higher quality memories increase confidence
        if memories:
            avg_importance = np.mean([m.importance for m in memories])
            quality_score = avg_importance / 10.0 * 0.2
        else:
            quality_score = 0.0

        # More insights indicate better understanding
        insight_score = min(0.1, insight_count * 0.02)

        return min(1.0, base_score + memory_score + quality_score + insight_score)

    def _create_empty_topic_summary(self, topic: str) -> TopicSummary:
        """Create empty summary when no memories found"""
        return TopicSummary(
            topic=topic,
            summary=f"No memories found related to '{topic}'.",
            key_insights=["No insights available - start adding memories about this topic"],
            related_entities=[],
            related_topics=[],
            memory_count=0,
            confidence_score=0.0,
            word_count=0,
            generated_at=datetime.utcnow()
        )

    def _create_empty_period_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> PeriodSummary:
        """Create empty period summary"""
        period_type = self._determine_period_type(start_date, end_date)

        return PeriodSummary(
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            summary="No memories found in this time period.",
            highlights=["No activity during this period"],
            new_topics=[],
            new_entities=[],
            top_memories=[],
            statistics={"total_memories": 0},
            trends=[],
            generated_at=datetime.utcnow()
        )

    def _filter_by_focus_areas(
        self,
        memories: list[Any],
        focus_areas: list[str]
    ) -> list[Any]:
        """Filter memories by focus areas"""
        filtered = []

        for memory in memories:
            # Check content
            content_lower = memory.content.lower()
            if any(area.lower() in content_lower for area in focus_areas):
                filtered.append(memory)
                continue

            # Check tags
            if any(area.lower() in tag.lower() for area in focus_areas for tag in memory.tags):
                filtered.append(memory)
                continue

            # Check metadata topics
            topics = memory.metadata.get("topics", [])
            if any(area.lower() in topic.lower() for area in focus_areas for topic in topics):
                filtered.append(memory)

        return filtered

    async def _analyze_period_content(self, memories: list[Any]) -> dict[str, Any]:
        """Analyze content from a time period"""

        # Track what's new in this period
        all_topics = []
        all_entities = []

        for memory in memories:
            all_topics.extend(memory.metadata.get("topics", []))
            all_entities.extend(memory.metadata.get("entities", []))

        # Count occurrences
        topic_counts = Counter(all_topics)
        entity_counts = Counter(all_entities)

        # Identify new (first appearances)
        # In a real implementation, this would compare with previous periods
        new_topics = list(topic_counts.keys())[:5]
        new_entities = list(entity_counts.keys())[:5]

        # Calculate statistics
        statistics = {
            "total_memories": len(memories),
            "unique_topics": len(set(all_topics)),
            "unique_entities": len(set(all_entities)),
            "avg_importance": np.mean([m.importance for m in memories]) if memories else 0,
            "total_tags": sum(len(m.tags) for m in memories)
        }

        return {
            "topic_counts": topic_counts,
            "entity_counts": entity_counts,
            "new_topics": new_topics,
            "new_entities": new_entities,
            "statistics": statistics
        }

    async def _generate_period_summary(
        self,
        memories: list[Any],
        start_date: datetime,
        end_date: datetime,
        analysis: dict[str, Any]
    ) -> str:
        """Generate summary for time period"""

        # Prepare top content
        top_topics = ", ".join([t for t, _ in analysis["topic_counts"].most_common(5)])
        top_entities = ", ".join([e for e, _ in analysis["entity_counts"].most_common(5)])

        # Sample memory content
        memory_samples = []
        for m in memories[:10]:
            date_str = m.created_at.strftime("%b %d")
            memory_samples.append(f"[{date_str}] {m.content[:100]}...")

        prompt = f"""Create a summary of knowledge captured between {start_date.strftime('%B %d, %Y')} and {end_date.strftime('%B %d, %Y')}.

Statistics:
- Total memories: {analysis['statistics']['total_memories']}
- Key topics: {top_topics}
- Key entities: {top_entities}
- Average importance: {analysis['statistics']['avg_importance']:.1f}

Sample memories:
{chr(10).join(memory_samples)}

Create a narrative summary that:
1. Describes the main themes and activities during this period
2. Highlights significant developments or changes
3. Identifies patterns or trends
4. Suggests areas of focus or growth

Keep the summary between 150-300 words."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating insightful period summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=800
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating period summary: {e}")
            return self._fallback_period_summary(start_date, end_date, memories, analysis)

    def _fallback_period_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        memories: list[Any],
        analysis: dict[str, Any]
    ) -> str:
        """Fallback period summary"""
        period_str = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        summary = f"Summary for {period_str}:\n\n"
        summary += f"Captured {len(memories)} memories during this period.\n\n"

        if analysis["topic_counts"]:
            summary += "Main topics: " + ", ".join([t for t, _ in analysis["topic_counts"].most_common(5)]) + "\n\n"

        summary += "This period showed consistent knowledge acquisition across various areas."

        return summary

    async def _extract_period_highlights(
        self,
        memories: list[Any],
        analysis: dict[str, Any]
    ) -> list[str]:
        """Extract highlights from period"""

        highlights = []

        # Most important memory
        if memories:
            top_memory = max(memories, key=lambda m: m.importance)
            highlights.append(f"Key insight: {top_memory.content[:100]}...")

        # Most discussed topic
        if analysis["topic_counts"]:
            top_topic = analysis["topic_counts"].most_common(1)[0]
            highlights.append(f"Focus area: {top_topic[0]} (mentioned {top_topic[1]} times)")

        # New discoveries
        if analysis["new_entities"]:
            highlights.append(f"New concepts: {', '.join(analysis['new_entities'][:3])}")

        # Activity level
        daily_avg = len(memories) / max(1, (memories[-1].created_at - memories[0].created_at).days) if memories else 0
        highlights.append(f"Activity: {daily_avg:.1f} memories per day")

        return highlights[:10]  # Limit to 10 highlights

    def _identify_period_trends(
        self,
        memories: list[Any],
        analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify trends in the period"""

        trends = []

        # Topic trends
        if analysis["topic_counts"]:
            top_topics = analysis["topic_counts"].most_common(3)
            for topic, count in top_topics:
                trends.append({
                    "type": "topic_trend",
                    "name": topic,
                    "direction": "increasing",  # Would need historical data for real trends
                    "strength": min(1.0, count / 10.0),
                    "description": f"{topic} gaining focus"
                })

        # Importance trends
        if memories:
            importances = [m.importance for m in memories]
            avg_importance = np.mean(importances)

            trends.append({
                "type": "importance_trend",
                "name": "Memory importance",
                "value": avg_importance,
                "direction": "stable",
                "description": f"Average importance: {avg_importance:.1f}/10"
            })

        return trends

    def _memory_to_dict(self, memory: Any) -> dict[str, Any]:
        """Convert memory to dictionary for API response"""
        return {
            "id": str(memory.id),
            "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
            "importance": memory.importance,
            "created_at": memory.created_at.isoformat(),
            "tags": memory.tags,
            "topic": memory.metadata.get("topics", [])[0] if memory.metadata.get("topics") else "General"
        }

    def _determine_period_type(self, start_date: datetime, end_date: datetime) -> str:
        """Determine the type of period"""
        days = (end_date - start_date).days

        if days <= 1:
            return "daily"
        elif days <= 7:
            return "weekly"
        elif days <= 31:
            return "monthly"
        else:
            return "custom"

    async def _build_executive_context(self, memories: list[Any]) -> dict[str, Any]:
        """Build comprehensive context for executive summary"""

        context = {
            "total_memories": len(memories),
            "date_range": {
                "start": min(m.created_at for m in memories),
                "end": max(m.created_at for m in memories)
            },
            "importance_distribution": Counter([int(m.importance) for m in memories]),
            "all_topics": [],
            "all_entities": [],
            "all_tags": []
        }

        for memory in memories:
            context["all_topics"].extend(memory.metadata.get("topics", []))
            context["all_entities"].extend(memory.metadata.get("entities", []))
            context["all_tags"].extend(memory.tags)

        # Count occurrences
        context["topic_counts"] = Counter(context["all_topics"])
        context["entity_counts"] = Counter(context["all_entities"])
        context["tag_counts"] = Counter(context["all_tags"])

        return context

    async def _generate_graph_visualization(self, memories: list[Any]) -> dict[str, Any]:
        """Generate D3.js compatible graph data"""

        try:
            # Build graph from memories
            memory_ids = [m.id for m in memories]
            graph_data = await self.graph_builder.build_graph_from_memories(
                memory_ids=memory_ids,
                include_relationships=True,
                max_entities=50  # Limit for visualization
            )

            # Convert to D3.js format
            d3_data = {
                "nodes": [
                    {
                        "id": node["id"],
                        "name": node["name"],
                        "type": node.get("type", "concept"),
                        "size": node.get("importance", 1) * 10
                    }
                    for node in graph_data.get("nodes", [])
                ],
                "links": [
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "type": edge.get("type", "related_to"),
                        "weight": edge.get("weight", 1.0)
                    }
                    for edge in graph_data.get("edges", [])
                ]
            }

            return d3_data

        except Exception as e:
            logger.error(f"Error generating graph visualization: {e}")
            return None

    async def _generate_executive_components(
        self,
        memories: list[Any],
        context: dict[str, Any],
        style: str
    ) -> dict[str, Any]:
        """Generate executive summary components"""

        # Prepare context summary
        date_range = f"{context['date_range']['start'].strftime('%B %d')} - {context['date_range']['end'].strftime('%B %d, %Y')}"
        top_topics = ", ".join([t for t, _ in context["topic_counts"].most_common(5)])
        top_entities = ", ".join([e for e, _ in context["entity_counts"].most_common(5)])

        # Sample important memories
        important_memories = sorted(memories, key=lambda m: m.importance, reverse=True)[:5]
        memory_samples = []
        for m in important_memories:
            memory_samples.append(f"- {m.content[:150]}...")

        style_instructions = {
            "professional": "Use formal business language, focus on actionable insights and strategic implications.",
            "casual": "Use conversational tone, make it engaging and easy to understand.",
            "technical": "Include technical details, metrics, and precise terminology.",
            "academic": "Use scholarly language, include analysis and theoretical connections."
        }

        prompt = f"""Create an executive summary for {context['total_memories']} memories from {date_range}.

Key Information:
- Main topics: {top_topics}
- Key entities: {top_entities}
- Average importance: {np.mean([m.importance for m in memories]):.1f}/10

Important memories:
{chr(10).join(memory_samples)}

Style: {style_instructions.get(style, style_instructions['professional'])}

Generate:
1. A compelling title (10-15 words)
2. An executive summary (200-300 words) that synthesizes the key information
3. 5-7 key points that capture the most important insights

Format the response as:
TITLE: [title here]

SUMMARY:
[summary here]

KEY POINTS:
1. [point 1]
2. [point 2]
... etc"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert executive summary writer who creates clear, insightful, and actionable summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract components
            lines = content.split('\n')
            title = ""
            summary = ""
            key_points = []

            current_section = None

            for line in lines:
                line = line.strip()

                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                elif line == "SUMMARY:":
                    current_section = "summary"
                elif line == "KEY POINTS:":
                    current_section = "key_points"
                elif current_section == "summary" and line:
                    summary += line + " "
                elif current_section == "key_points" and line and line[0].isdigit():
                    point = line.split('.', 1)[1].strip() if '.' in line else line
                    key_points.append(point)

            return {
                "title": title or f"Executive Summary: {date_range}",
                "summary": summary.strip() or "Summary of key findings and insights.",
                "key_points": key_points[:7] if key_points else ["Key findings from the analyzed period"]
            }

        except Exception as e:
            logger.error(f"Error generating executive components: {e}")
            return self._fallback_executive_components(memories, context)

    def _fallback_executive_components(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Fallback executive summary components"""

        date_range = f"{context['date_range']['start'].strftime('%B %d')} - {context['date_range']['end'].strftime('%B %d, %Y')}"

        return {
            "title": f"Knowledge Summary: {date_range}",
            "summary": f"Analysis of {len(memories)} memories reveals key insights across multiple topics and domains. The knowledge base shows consistent growth and deepening understanding in core areas.",
            "key_points": [
                f"Analyzed {len(memories)} memories with average importance {np.mean([m.importance for m in memories]):.1f}/10",
                f"Key topics include: {', '.join([t for t, _ in context['topic_counts'].most_common(3)])}",
                f"Notable entities: {', '.join([e for e, _ in context['entity_counts'].most_common(3)])}",
                "Knowledge base shows consistent growth",
                "Multiple interconnected themes identified"
            ]
        }

    async def _extract_action_items(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> list[str]:
        """Extract actionable items from memories"""

        # Look for memories with action-oriented content
        action_memories = []
        action_keywords = ["todo", "task", "need to", "should", "must", "will", "plan to", "action:", "next step"]

        for memory in memories:
            content_lower = memory.content.lower()
            if any(keyword in content_lower for keyword in action_keywords):
                action_memories.append(memory)

        if not action_memories:
            return []

        # Extract actions using GPT
        memory_texts = [m.content[:200] for m in action_memories[:10]]

        prompt = f"""Extract specific action items from these memories:

{chr(10).join(f'{i+1}. {text}' for i, text in enumerate(memory_texts))}

Return up to 5 clear, specific action items that should be taken based on these memories.
Format: One action per line, starting with a verb."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying and extracting actionable tasks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            actions_text = response.choices[0].message.content.strip()
            actions = [line.strip() for line in actions_text.split('\n') if line.strip()]

            return actions[:5]

        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return []

    async def _extract_questions(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> list[str]:
        """Extract questions raised by the memories"""

        # Look for explicit questions
        question_memories = []
        for memory in memories:
            if '?' in memory.content:
                question_memories.append(memory)

        # Also generate implicit questions
        prompt = f"""Based on these topics and gaps in knowledge, what questions should be explored?

Topics covered: {', '.join([t for t, _ in context['topic_counts'].most_common(5)])}
Entities mentioned: {', '.join([e for e, _ in context['entity_counts'].most_common(5)])}

Generate 3-5 thought-provoking questions that would deepen understanding of these areas."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying knowledge gaps and generating insightful questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=500
            )

            questions_text = response.choices[0].message.content.strip()
            questions = [line.strip() for line in questions_text.split('\n') if line.strip() and '?' in line]

            return questions[:5]

        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return ["What are the key learnings from this period?"]

    async def _identify_opportunities(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> list[str]:
        """Identify opportunities from the knowledge base"""

        # Analyze for opportunity indicators
        opportunity_keywords = ["potential", "opportunity", "could", "possibility", "explore", "investigate", "develop", "expand"]

        relevant_memories = []
        for memory in memories:
            if any(keyword in memory.content.lower() for keyword in opportunity_keywords):
                relevant_memories.append(memory)

        # Focus on high-importance topics
        important_topics = [t for t, c in context["topic_counts"].most_common(10) if c >= 3]

        prompt = f"""Identify 3-5 opportunities based on this knowledge:

Key topics with multiple mentions: {', '.join(important_topics)}
Total knowledge items: {len(memories)}

What opportunities exist for:
1. Deeper exploration
2. Practical application
3. Knowledge synthesis
4. New connections

Be specific and actionable."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying opportunities for growth and development."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )

            opportunities_text = response.choices[0].message.content.strip()
            opportunities = [line.strip() for line in opportunities_text.split('\n') if line.strip() and not line[0].isdigit()]

            return opportunities[:5]

        except Exception as e:
            logger.error(f"Error identifying opportunities: {e}")
            return []

    async def _identify_risks(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> list[str]:
        """Identify potential risks or concerns"""

        # Look for risk indicators
        risk_keywords = ["risk", "concern", "problem", "issue", "challenge", "difficult", "warning", "caution", "danger"]

        risk_memories = []
        for memory in memories:
            if any(keyword in memory.content.lower() for keyword in risk_keywords):
                risk_memories.append(memory)

        if not risk_memories:
            return []

        # Analyze for knowledge gaps
        all_topics = set(context["all_topics"])
        mentioned_once = [t for t, c in context["topic_counts"].items() if c == 1]

        risks = []

        # Knowledge gaps
        if len(mentioned_once) > len(all_topics) * 0.3:
            risks.append("Many topics have limited coverage - knowledge gaps may exist")

        # Low importance areas
        low_importance = [m for m in memories if m.importance < 3]
        if len(low_importance) > len(memories) * 0.3:
            risks.append("Significant portion of knowledge marked as low importance")

        # Extract specific risks from content
        if risk_memories:
            prompt = f"""Extract 2-3 specific risks or concerns from these memories:

{chr(10).join(m.content[:150] + '...' for m in risk_memories[:5])}

Focus on actual risks mentioned, not hypothetical ones."""

            try:
                response = await self.openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert at risk identification and analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=300
                )

                risks_text = response.choices[0].message.content.strip()
                extracted_risks = [line.strip() for line in risks_text.split('\n') if line.strip()]

                risks.extend(extracted_risks[:3])

            except Exception as e:
                logger.error(f"Error extracting risks: {e}")

        return risks[:5]

    def _calculate_executive_metrics(
        self,
        memories: list[Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate metrics for executive summary"""

        return {
            "total_memories": len(memories),
            "date_range_days": (context["date_range"]["end"] - context["date_range"]["start"]).days,
            "unique_topics": len(set(context["all_topics"])),
            "unique_entities": len(set(context["all_entities"])),
            "avg_importance": float(np.mean([m.importance for m in memories])),
            "importance_std": float(np.std([m.importance for m in memories])),
            "memories_per_day": len(memories) / max(1, (context["date_range"]["end"] - context["date_range"]["start"]).days),
            "top_topic_coverage": context["topic_counts"].most_common(1)[0][1] if context["topic_counts"] else 0,
            "connectivity": len([m for m in memories if len(m.metadata.get("entities", [])) > 2]) / len(memories) if memories else 0
        }

    def _calculate_executive_confidence(
        self,
        memories: list[Any],
        action_count: int,
        question_count: int
    ) -> float:
        """Calculate confidence score for executive summary"""

        base_score = 0.4

        # Memory quantity and quality
        memory_score = min(0.3, len(memories) * 0.005)
        quality_score = np.mean([m.importance for m in memories]) / 10.0 * 0.2 if memories else 0

        # Insights generated
        insight_score = min(0.1, (action_count + question_count) * 0.01)

        return min(1.0, base_score + memory_score + quality_score + insight_score)
