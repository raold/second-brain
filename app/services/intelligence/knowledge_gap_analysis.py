"""
Knowledge gap analysis service for v2.8.3 Intelligence features.

This service analyzes the knowledge base to identify missing information,
under-represented topics, and potential areas for expansion.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Optional
from uuid import uuid4

import networkx as nx
import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer

from app.database import Database
from app.models.intelligence.analytics_models import KnowledgeGap
from app.models.memory import Memory, MemoryType
from app.services.memory_relationship_analyzer import MemoryRelationshipAnalyzer as RelationshipAnalyzer
from app.services.memory_service import MemoryService
from app.utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class KnowledgeGapAnalyzer:
    """Service for analyzing knowledge gaps in the memory base."""

    def __init__(
        self,
        database: Database,
        memory_service: MemoryService,
        relationship_analyzer: RelationshipAnalyzer,
        openai_client: OpenAIClient
    ):
        self.db = database
        self.memory_service = memory_service
        self.relationship_analyzer = relationship_analyzer
        self.openai = openai_client

        # Analysis parameters
        self.min_topic_size = 5
        self.gap_threshold = 0.3
        self.importance_weight = 0.7

    async def analyze_knowledge_gaps(
        self,
        user_id: str,
        limit: int = 20,
        focus_areas: Optional[list[str]] = None
    ) -> list[KnowledgeGap]:
        """Analyze and identify knowledge gaps."""
        # Get all memories for analysis
        memories = await self._get_user_memories(user_id)

        if len(memories) < 10:
            logger.info(f"Insufficient memories for gap analysis: {len(memories)}")
            return []

        # Run multiple gap detection methods in parallel
        gap_tasks = [
            self._analyze_topic_coverage(memories, focus_areas),
            self._analyze_relationship_gaps(memories, user_id),
            self._analyze_temporal_gaps(memories),
            self._analyze_conceptual_completeness(memories),
            self._analyze_question_gaps(memories)
        ]

        gap_results = await asyncio.gather(*gap_tasks, return_exceptions=True)

        all_gaps = []
        for result in gap_results:
            if isinstance(result, Exception):
                logger.error(f"Error in gap analysis: {result}")
                continue
            all_gaps.extend(result)

        # Merge and rank gaps
        merged_gaps = self._merge_knowledge_gaps(all_gaps)

        # Sort by importance score
        merged_gaps.sort(key=lambda g: g.importance_score, reverse=True)

        return merged_gaps[:limit]

    async def _get_user_memories(self, user_id: str) -> list[Memory]:
        """Get all memories for a user."""
        # This would typically query the database
        # For now, using memory service search
        results = await self.memory_service.search_memories(
            query="",  # Empty query to get all
            user_id=user_id,
            limit=10000  # High limit to get all memories
        )
        return results.memories if results else []

    async def _analyze_topic_coverage(
        self,
        memories: list[Memory],
        focus_areas: Optional[list[str]] = None
    ) -> list[KnowledgeGap]:
        """Analyze topic coverage using LDA and TF-IDF."""
        gaps = []

        # Prepare text data
        texts = [f"{m.title} {m.content}" for m in memories]

        if len(texts) < self.min_topic_size:
            return gaps

        try:
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            doc_term_matrix = vectorizer.fit_transform(texts)

            # Topic modeling with LDA
            n_topics = min(10, len(texts) // 5)
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=10
            )
            lda.fit(doc_term_matrix)

            # Get feature names
            feature_names = vectorizer.get_feature_names_out()

            # Analyze topic distribution
            doc_topics = lda.transform(doc_term_matrix)
            topic_coverage = np.mean(doc_topics, axis=0)

            # Identify under-represented topics
            for topic_idx, coverage in enumerate(topic_coverage):
                if coverage < self.gap_threshold:
                    # Get top words for this topic
                    topic_words = self._get_topic_words(
                        lda, feature_names, topic_idx, n_words=5
                    )

                    gap = KnowledgeGap(
                        id=uuid4(),
                        topic=f"Topic: {' '.join(topic_words[:3])}",
                        related_concepts=topic_words,
                        gap_score=1.0 - coverage,
                        importance_score=self._calculate_topic_importance(
                            topic_idx, doc_topics, memories
                        ),
                        suggested_queries=[
                            f"What is {word}?" for word in topic_words[:3]
                        ],
                        potential_sources=[
                            "Wikipedia",
                            "Academic papers",
                            "Documentation",
                            "Expert interviews"
                        ]
                    )
                    gaps.append(gap)

            # Check focus areas if provided
            if focus_areas:
                gaps.extend(await self._check_focus_area_coverage(
                    focus_areas, texts, vectorizer
                ))

        except Exception as e:
            logger.error(f"Error in topic coverage analysis: {e}")

        return gaps

    async def _analyze_relationship_gaps(
        self,
        memories: list[Memory],
        user_id: str
    ) -> list[KnowledgeGap]:
        """Analyze gaps in memory relationships."""
        gaps = []

        try:
            # Build knowledge graph
            graph = nx.Graph()

            # Add memories as nodes
            for memory in memories:
                graph.add_node(memory.id, memory=memory)

            # Add relationships as edges
            for memory in memories:
                relationships = await self.relationship_analyzer.find_related_memories(
                    memory.id, user_id, limit=10
                )
                for rel in relationships:
                    if rel.target_memory_id in [m.id for m in memories]:
                        graph.add_edge(
                            memory.id,
                            rel.target_memory_id,
                            weight=rel.strength
                        )

            # Analyze graph structure
            if len(graph) > 0:
                # Find isolated components
                components = list(nx.connected_components(graph))

                # Identify isolated knowledge islands
                for component in components:
                    if len(component) < 3:  # Small isolated group
                        component_memories = [
                            graph.nodes[node]['memory']
                            for node in component
                        ]

                        gap = KnowledgeGap(
                            id=uuid4(),
                            topic=f"Isolated concept: {component_memories[0].title}",
                            related_concepts=[m.title for m in component_memories],
                            gap_score=0.8,
                            importance_score=0.6,
                            suggested_queries=[
                                f"How does {component_memories[0].title} relate to other topics?",
                                f"What connects {component_memories[0].title} to the broader knowledge base?"
                            ],
                            potential_sources=[
                                "Cross-references",
                                "Conceptual frameworks",
                                "Integration guides"
                            ]
                        )
                        gaps.append(gap)

                # Find weakly connected nodes
                for node in graph.nodes():
                    degree = graph.degree(node)
                    if degree < 2:  # Weakly connected
                        memory = graph.nodes[node]['memory']

                        gap = KnowledgeGap(
                            id=uuid4(),
                            topic=f"Under-connected: {memory.title}",
                            related_concepts=[memory.title],
                            gap_score=0.6,
                            importance_score=0.5,
                            suggested_queries=[
                                f"What concepts relate to {memory.title}?",
                                f"How can {memory.title} be better integrated?"
                            ],
                            potential_sources=[
                                "Related concepts",
                                "Contextual information",
                                "Examples and applications"
                            ]
                        )
                        gaps.append(gap)

        except Exception as e:
            logger.error(f"Error in relationship gap analysis: {e}")

        return gaps

    async def _analyze_temporal_gaps(
        self,
        memories: list[Memory]
    ) -> list[KnowledgeGap]:
        """Analyze temporal gaps in knowledge acquisition."""
        gaps = []

        # Sort memories by creation date
        sorted_memories = sorted(memories, key=lambda m: m.created_at)

        if len(sorted_memories) < 2:
            return gaps

        # Find time periods with no memories
        gap_threshold_days = 7  # Week without new memories

        for i in range(1, len(sorted_memories)):
            time_diff = sorted_memories[i].created_at - sorted_memories[i-1].created_at

            if time_diff.days > gap_threshold_days:
                # Analyze what might be missing
                before_topics = self._extract_topics(sorted_memories[:i])
                after_topics = self._extract_topics(sorted_memories[i:])

                missing_topics = before_topics - after_topics

                if missing_topics:
                    gap = KnowledgeGap(
                        id=uuid4(),
                        topic=f"Temporal gap: {time_diff.days} days",
                        related_concepts=list(missing_topics)[:5],
                        gap_score=min(time_diff.days / 30, 1.0),  # Normalize to 30 days
                        importance_score=0.4,
                        suggested_queries=[
                            f"What happened with {topic} during this period?"
                            for topic in list(missing_topics)[:3]
                        ],
                        potential_sources=[
                            "Historical records",
                            "Activity logs",
                            "External events"
                        ]
                    )
                    gaps.append(gap)

        return gaps

    async def _analyze_conceptual_completeness(
        self,
        memories: list[Memory]
    ) -> list[KnowledgeGap]:
        """Analyze conceptual completeness using GPT."""
        gaps = []

        # Group memories by topic
        topic_groups = self._group_by_topics(memories)

        # Analyze each topic group for completeness
        for topic, topic_memories in list(topic_groups.items())[:5]:  # Limit API calls
            if len(topic_memories) < 3:
                continue

            try:
                # Ask GPT to identify missing concepts
                prompt = f"""
                Analyze the following knowledge items about "{topic}" and identify what key concepts or information might be missing:

                {chr(10).join([f"- {m.title}: {m.content[:100]}..." for m in topic_memories[:10]])}

                List 3-5 specific missing concepts or gaps in JSON format:
                {{
                    "missing_concepts": ["concept1", "concept2", ...],
                    "importance": 0.0-1.0,
                    "suggested_questions": ["question1", "question2", ...]
                }}
                """

                response = await self.openai.generate_completion(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.7
                )

                # Parse response
                import json
                try:
                    gap_data = json.loads(response)

                    gap = KnowledgeGap(
                        id=uuid4(),
                        topic=f"Incomplete: {topic}",
                        related_concepts=gap_data.get("missing_concepts", []),
                        gap_score=0.7,
                        importance_score=gap_data.get("importance", 0.5),
                        suggested_queries=gap_data.get("suggested_questions", []),
                        potential_sources=[
                            "Domain experts",
                            "Textbooks",
                            "Research papers",
                            "Online courses"
                        ]
                    )
                    gaps.append(gap)

                except json.JSONDecodeError:
                    logger.error(f"Failed to parse GPT response for topic: {topic}")

            except Exception as e:
                logger.error(f"Error analyzing conceptual completeness: {e}")

        return gaps

    async def _analyze_question_gaps(
        self,
        memories: list[Memory]
    ) -> list[KnowledgeGap]:
        """Identify unanswered questions in memories."""
        gaps = []

        # Find memories with questions
        question_memories = [
            m for m in memories
            if '?' in m.content or m.memory_type == MemoryType.QUESTION
        ]

        # Check if questions have answers
        for q_memory in question_memories:
            # Look for potential answer memories
            potential_answers = [
                m for m in memories
                if m.id != q_memory.id and self._might_answer(q_memory, m)
            ]

            if not potential_answers:
                gap = KnowledgeGap(
                    id=uuid4(),
                    topic=f"Unanswered: {q_memory.title}",
                    related_concepts=self._extract_concepts(q_memory.content),
                    gap_score=0.9,
                    importance_score=0.7,
                    suggested_queries=[q_memory.content[:200]],
                    potential_sources=[
                        "Q&A platforms",
                        "Expert consultation",
                        "Research literature",
                        "Experimentation"
                    ]
                )
                gaps.append(gap)

        return gaps

    async def _check_focus_area_coverage(
        self,
        focus_areas: list[str],
        texts: list[str],
        vectorizer: TfidfVectorizer
    ) -> list[KnowledgeGap]:
        """Check coverage of specific focus areas."""
        gaps = []

        for area in focus_areas:
            # Check how well the area is covered
            area_coverage = sum(1 for text in texts if area.lower() in text.lower())
            coverage_ratio = area_coverage / len(texts)

            if coverage_ratio < 0.1:  # Less than 10% coverage
                gap = KnowledgeGap(
                    id=uuid4(),
                    topic=f"Focus area: {area}",
                    related_concepts=[area],
                    gap_score=1.0 - coverage_ratio,
                    importance_score=0.9,  # High importance for focus areas
                    suggested_queries=[
                        f"What is {area}?",
                        f"How does {area} work?",
                        f"Why is {area} important?",
                        f"Examples of {area}"
                    ],
                    potential_sources=[
                        f"{area} documentation",
                        f"{area} tutorials",
                        "Domain experts",
                        "Case studies"
                    ]
                )
                gaps.append(gap)

        return gaps

    def _get_topic_words(
        self,
        lda_model,
        feature_names: np.ndarray,
        topic_idx: int,
        n_words: int = 10
    ) -> list[str]:
        """Get top words for a topic."""
        topic = lda_model.components_[topic_idx]
        top_indices = topic.argsort()[-n_words:][::-1]
        return [feature_names[i] for i in top_indices]

    def _calculate_topic_importance(
        self,
        topic_idx: int,
        doc_topics: np.ndarray,
        memories: list[Memory]
    ) -> float:
        """Calculate importance score for a topic."""
        # Base importance on memory importance scores
        topic_memories_idx = np.where(doc_topics[:, topic_idx] > 0.3)[0]

        if len(topic_memories_idx) == 0:
            return 0.5

        importance_scores = [
            memories[idx].importance / 10.0  # Normalize to 0-1
            for idx in topic_memories_idx
            if idx < len(memories)
        ]

        return np.mean(importance_scores) if importance_scores else 0.5

    def _extract_topics(self, memories: list[Memory]) -> set[str]:
        """Extract topics from memories."""
        topics = set()

        for memory in memories:
            # Simple topic extraction based on title and tags
            words = memory.title.lower().split()
            topics.update(w for w in words if len(w) > 3)

            if memory.tags:
                topics.update(tag.lower() for tag in memory.tags)

        return topics

    def _group_by_topics(self, memories: list[Memory]) -> dict[str, list[Memory]]:
        """Group memories by common topics."""
        topic_groups = defaultdict(list)

        for memory in memories:
            # Extract main topic from title
            main_topic = memory.title.split()[0] if memory.title else "unknown"
            topic_groups[main_topic].append(memory)

            # Also group by tags
            if memory.tags:
                for tag in memory.tags:
                    topic_groups[tag].append(memory)

        return dict(topic_groups)

    def _extract_concepts(self, text: str) -> list[str]:
        """Extract key concepts from text."""
        # Simple noun phrase extraction
        words = text.split()
        concepts = []

        for i, word in enumerate(words):
            if word[0].isupper() and i > 0:  # Likely proper noun
                concepts.append(word)
            elif len(word) > 6 and word.isalpha():  # Longer words
                concepts.append(word)

        return concepts[:5]

    def _might_answer(self, question: Memory, candidate: Memory) -> bool:
        """Check if a memory might answer a question."""
        # Simple heuristic: check for keyword overlap
        q_words = set(question.content.lower().split())
        c_words = set(candidate.content.lower().split())

        overlap = len(q_words & c_words)
        return overlap > min(len(q_words), len(c_words)) * 0.3

    def _merge_knowledge_gaps(self, gaps: list[KnowledgeGap]) -> list[KnowledgeGap]:
        """Merge similar knowledge gaps."""
        if not gaps:
            return []

        merged = []
        seen_topics = set()

        for gap in gaps:
            # Simple deduplication by topic similarity
            topic_key = gap.topic.lower()[:20]  # First 20 chars

            if topic_key not in seen_topics:
                seen_topics.add(topic_key)
                merged.append(gap)
            else:
                # Find and update existing gap
                for existing in merged:
                    if existing.topic.lower()[:20] == topic_key:
                        # Merge information
                        existing.related_concepts.extend(gap.related_concepts)
                        existing.related_concepts = list(set(existing.related_concepts))
                        existing.suggested_queries.extend(gap.suggested_queries)
                        existing.gap_score = max(existing.gap_score, gap.gap_score)
                        existing.importance_score = max(
                            existing.importance_score,
                            gap.importance_score
                        )
                        break

        return merged
