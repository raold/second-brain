"""
Smart suggestion engine for memory recommendations
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.memory import Memory
from app.models.synthesis.suggestion_models import (
    ConnectionSuggestion,
    GapSuggestion,
    MemorySuggestion,
    QuestionSuggestion,
    ReviewSuggestion,
    Suggestion,
    SuggestionBatch,
    SuggestionContext,
    SuggestionType,
)
from app.services.memory_service import MemoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SmartSuggestionEngine:
    """Engine for generating intelligent memory suggestions"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
        self.openai_client = get_openai_client()

    async def generate_suggestions(
        self,
        user_id: str,
        context: SuggestionContext,
        max_suggestions: int = 10,
        suggestion_types: Optional[list[SuggestionType]] = None
    ) -> SuggestionBatch:
        """Generate a batch of smart suggestions based on context"""
        start_time = datetime.utcnow()

        try:
            # Generate suggestions of each type
            all_suggestions = []

            if not suggestion_types:
                suggestion_types = list(SuggestionType)

            # Generate suggestions in parallel
            suggestion_tasks = []

            if SuggestionType.RELATED_MEMORY in suggestion_types:
                suggestion_tasks.append(
                    self._generate_related_memory_suggestions(user_id, context)
                )

            if SuggestionType.MISSING_CONNECTION in suggestion_types:
                suggestion_tasks.append(
                    self._generate_connection_suggestions(user_id, context)
                )

            if SuggestionType.FOLLOW_UP_QUESTION in suggestion_types:
                suggestion_tasks.append(
                    self._generate_question_suggestions(user_id, context)
                )

            if SuggestionType.KNOWLEDGE_GAP in suggestion_types:
                suggestion_tasks.append(
                    self._generate_gap_suggestions(user_id, context)
                )

            if SuggestionType.REVIEW_REMINDER in suggestion_types:
                suggestion_tasks.append(
                    self._generate_review_suggestions(user_id, context)
                )

            # Wait for all suggestion generations
            suggestion_results = await asyncio.gather(*suggestion_tasks, return_exceptions=True)

            # Combine all suggestions
            for result in suggestion_results:
                if isinstance(result, list):
                    all_suggestions.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error generating suggestions: {result}")

            # Rank and filter suggestions
            ranked_suggestions = await self._rank_suggestions(
                all_suggestions, context, max_suggestions
            )

            # Calculate generation time
            generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return SuggestionBatch(
                suggestions=ranked_suggestions,
                context=context,
                total_available=len(all_suggestions),
                generation_time_ms=generation_time_ms,
                algorithm_version="1.0.0",
                filtering_applied=[
                    "relevance_ranking",
                    "diversity_filtering",
                    "context_matching"
                ]
            )

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            raise

    async def _generate_related_memory_suggestions(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[MemorySuggestion]:
        """Generate suggestions for related memories"""
        suggestions = []

        try:
            # Get similar memories based on current context
            if context.current_memory_id:
                # Find similar memories using embedding similarity
                query = text("""
                    SELECT
                        m2.id,
                        m2.title,
                        m2.content,
                        m2.importance,
                        1 - (m1.embedding <=> m2.embedding) as similarity
                    FROM memories m1
                    JOIN memories m2 ON m1.user_id = m2.user_id
                    WHERE
                        m1.id = :current_id
                        AND m2.id != :current_id
                        AND m2.deleted_at IS NULL
                        AND 1 - (m1.embedding <=> m2.embedding) > 0.7
                    ORDER BY similarity DESC
                    LIMIT 5
                """)

                result = await self.db.execute(
                    query,
                    {"current_id": str(context.current_memory_id)}
                )
                similar_memories = result.fetchall()

                for memory in similar_memories:
                    # Extract common entities and topics
                    common_entities = await self._find_common_entities(
                        context.current_memory_id, memory.id
                    )
                    common_topics = await self._find_common_topics(
                        context.current_memory_id, memory.id
                    )

                    suggestion = MemorySuggestion(
                        type=SuggestionType.RELATED_MEMORY,
                        title=f"Related: {memory.title}",
                        description="This memory shares similar concepts and themes",
                        reason=f"Similarity score: {memory.similarity:.2f}",
                        confidence=memory.similarity,
                        priority=memory.importance * memory.similarity,
                        memory_id=memory.id,
                        memory_title=memory.title,
                        memory_preview=memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                        relevance_score=memory.similarity,
                        common_entities=common_entities,
                        common_topics=common_topics
                    )
                    suggestions.append(suggestion)

            # Also suggest based on recent topics
            if context.current_topics:
                for topic in context.current_topics[:3]:  # Top 3 topics
                    topic_memories = await self._find_memories_by_topic(
                        user_id, topic, exclude_ids=context.recent_memory_ids
                    )

                    for memory in topic_memories[:2]:  # Top 2 per topic
                        suggestion = MemorySuggestion(
                            type=SuggestionType.RELATED_MEMORY,
                            title=f"Topic '{topic}': {memory['title']}",
                            description=f"Explore more about {topic}",
                            reason=f"Contains relevant information about {topic}",
                            confidence=0.8,
                            priority=memory['importance'] * 0.8,
                            memory_id=memory['id'],
                            memory_title=memory['title'],
                            memory_preview=memory['content'][:200] + "..." if len(memory['content']) > 200 else memory['content'],
                            relevance_score=0.8,
                            common_topics=[topic]
                        )
                        suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.error(f"Error generating related memory suggestions: {e}")
            return []

    async def _generate_connection_suggestions(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[ConnectionSuggestion]:
        """Generate suggestions for missing connections"""
        suggestions = []

        try:
            if not context.current_memory_id:
                return []

            # Find memories that should be connected but aren't
            query = text("""
                WITH current_connections AS (
                    SELECT target_id FROM memory_relationships
                    WHERE source_id = :current_id
                    UNION
                    SELECT source_id FROM memory_relationships
                    WHERE target_id = :current_id
                ),
                potential_connections AS (
                    SELECT
                        m.id,
                        m.title,
                        m.content,
                        1 - (cm.embedding <=> m.embedding) as similarity
                    FROM memories cm
                    JOIN memories m ON cm.user_id = m.user_id
                    WHERE
                        cm.id = :current_id
                        AND m.id != :current_id
                        AND m.id NOT IN (SELECT * FROM current_connections)
                        AND m.deleted_at IS NULL
                        AND 1 - (cm.embedding <=> m.embedding) > 0.75
                    ORDER BY similarity DESC
                    LIMIT 10
                )
                SELECT * FROM potential_connections
            """)

            result = await self.db.execute(
                query,
                {"current_id": str(context.current_memory_id)}
            )
            potential_connections = result.fetchall()

            # Analyze each potential connection
            current_memory = await self.memory_service.get_memory(
                user_id, context.current_memory_id
            )

            for candidate in potential_connections:
                # Use AI to determine relationship type and evidence
                relationship_info = await self._analyze_relationship(
                    current_memory,
                    {"id": candidate.id, "title": candidate.title, "content": candidate.content}
                )

                if relationship_info['should_connect']:
                    suggestion = ConnectionSuggestion(
                        type=SuggestionType.MISSING_CONNECTION,
                        title=f"Connect: {current_memory.title} ↔ {candidate.title}",
                        description=relationship_info['description'],
                        reason=f"High similarity ({candidate.similarity:.2f}) suggests a relationship",
                        confidence=relationship_info['confidence'],
                        priority=candidate.similarity * relationship_info['confidence'],
                        source_memory_id=context.current_memory_id,
                        target_memory_id=candidate.id,
                        source_title=current_memory.title,
                        target_title=candidate.title,
                        suggested_relationship=relationship_info['relationship_type'],
                        supporting_evidence=relationship_info['evidence'],
                        potential_insights=relationship_info['insights']
                    )
                    suggestions.append(suggestion)

            return suggestions[:5]  # Top 5 connection suggestions

        except Exception as e:
            logger.error(f"Error generating connection suggestions: {e}")
            return []

    async def _generate_question_suggestions(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[QuestionSuggestion]:
        """Generate follow-up questions"""
        suggestions = []

        try:
            # Generate questions based on current memory or recent activities
            if context.current_memory_id:
                memory = await self.memory_service.get_memory(user_id, context.current_memory_id)
                questions = await self._generate_followup_questions(memory)

                for q in questions:
                    suggestion = QuestionSuggestion(
                        type=SuggestionType.FOLLOW_UP_QUESTION,
                        title="Follow-up Question",
                        description=q['question'],
                        reason=q['reason'],
                        confidence=q['confidence'],
                        priority=q['priority'],
                        question=q['question'],
                        context_memory_ids=[context.current_memory_id],
                        expected_answer_type=q['answer_type'],
                        related_topics=q['topics'],
                        exploration_paths=q['paths']
                    )
                    suggestions.append(suggestion)

            # Generate questions based on knowledge gaps
            gaps = await self._identify_knowledge_gaps(user_id, context)
            for gap in gaps[:3]:  # Top 3 gaps
                question = await self._generate_gap_question(gap)
                if question:
                    suggestion = QuestionSuggestion(
                        type=SuggestionType.FOLLOW_UP_QUESTION,
                        title="Knowledge Gap Question",
                        description=question['question'],
                        reason=f"Fill knowledge gap in {gap['area']}",
                        confidence=0.7,
                        priority=0.7,
                        question=question['question'],
                        expected_answer_type="exploratory",
                        related_topics=[gap['area']]
                    )
                    suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.error(f"Error generating question suggestions: {e}")
            return []

    async def _generate_gap_suggestions(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[GapSuggestion]:
        """Generate knowledge gap suggestions"""
        suggestions = []

        try:
            # Identify gaps in different dimensions
            gaps = await self._identify_knowledge_gaps(user_id, context)

            for gap in gaps[:5]:  # Top 5 gaps
                suggestion = GapSuggestion(
                    type=SuggestionType.KNOWLEDGE_GAP,
                    title=f"Knowledge Gap: {gap['title']}",
                    description=gap['description'],
                    reason=gap['reason'],
                    confidence=gap['confidence'],
                    priority=gap['priority'],
                    gap_type=gap['type'],
                    current_coverage=gap['current_coverage'],
                    suggested_coverage=gap['suggested_coverage'],
                    filling_strategies=gap['strategies'],
                    related_memories=gap['related_memories']
                )
                suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.error(f"Error generating gap suggestions: {e}")
            return []

    async def _generate_review_suggestions(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[ReviewSuggestion]:
        """Generate review reminder suggestions"""
        suggestions = []

        try:
            # Find memories that need review based on spaced repetition
            query = text("""
                SELECT
                    id,
                    title,
                    content,
                    importance,
                    created_at,
                    updated_at,
                    last_accessed,
                    access_count,
                    EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed, created_at))) / 86400 as days_since_access
                FROM memories
                WHERE
                    user_id = :user_id
                    AND deleted_at IS NULL
                    AND (
                        -- High importance memories not accessed recently
                        (importance > 0.7 AND last_accessed < NOW() - INTERVAL '7 days')
                        OR
                        -- Memories with forgetting curve risk
                        (EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed, created_at))) / 86400 >
                         POWER(2, LEAST(access_count, 10)) * 7)
                        OR
                        -- Old memories that might need updating
                        (created_at < NOW() - INTERVAL '90 days' AND updated_at = created_at)
                    )
                ORDER BY
                    importance DESC,
                    days_since_access DESC
                LIMIT 10
            """)

            result = await self.db.execute(query, {"user_id": user_id})
            review_candidates = result.fetchall()

            for memory in review_candidates:
                # Determine review reason and actions
                review_info = self._determine_review_needs(memory)

                suggestion = ReviewSuggestion(
                    type=SuggestionType.REVIEW_REMINDER,
                    title=f"Review: {memory.title}",
                    description=review_info['description'],
                    reason=review_info['reason'],
                    confidence=review_info['confidence'],
                    priority=memory.importance * review_info['urgency'],
                    memory_id=memory.id,
                    memory_title=memory.title,
                    last_accessed=memory.last_accessed or memory.created_at,
                    review_reason=review_info['review_type'],
                    suggested_actions=review_info['actions'],
                    review_interval_days=review_info['interval'],
                    importance_change=review_info.get('importance_change')
                )
                suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.error(f"Error generating review suggestions: {e}")
            return []

    async def _rank_suggestions(
        self,
        suggestions: list[Suggestion],
        context: SuggestionContext,
        max_count: int
    ) -> list[Suggestion]:
        """Rank and filter suggestions"""
        if not suggestions:
            return []

        # Calculate combined scores
        for suggestion in suggestions:
            # Base score from confidence and priority
            base_score = suggestion.confidence * 0.4 + suggestion.priority * 0.6

            # Context relevance bonus
            context_score = 0.0
            if hasattr(suggestion, 'common_topics'):
                matching_topics = set(suggestion.common_topics) & set(context.current_topics)
                context_score += len(matching_topics) * 0.1

            if hasattr(suggestion, 'common_entities'):
                matching_entities = set(suggestion.common_entities) & set(context.current_entities)
                context_score += len(matching_entities) * 0.1

            # Time-based adjustments
            time_multiplier = self._get_time_multiplier(context.time_of_day)

            # Activity level adjustments
            activity_multiplier = 1.0
            if context.activity_level == "low":
                # Prefer lighter suggestions
                if suggestion.type in [SuggestionType.REVIEW_REMINDER, SuggestionType.RELATED_MEMORY]:
                    activity_multiplier = 1.2
            elif context.activity_level == "high":
                # Prefer deeper suggestions
                if suggestion.type in [SuggestionType.KNOWLEDGE_GAP, SuggestionType.MISSING_CONNECTION]:
                    activity_multiplier = 1.2

            # Calculate final score
            suggestion.metadata['ranking_score'] = (
                base_score + context_score
            ) * time_multiplier * activity_multiplier

        # Sort by ranking score
        suggestions.sort(
            key=lambda s: s.metadata.get('ranking_score', 0),
            reverse=True
        )

        # Ensure diversity (no more than 2 of same type)
        selected = []
        type_counts = {}

        for suggestion in suggestions:
            type_count = type_counts.get(suggestion.type, 0)
            if type_count < 2:
                selected.append(suggestion)
                type_counts[suggestion.type] = type_count + 1

                if len(selected) >= max_count:
                    break

        return selected

    def _get_time_multiplier(self, time_of_day: str) -> float:
        """Get suggestion multiplier based on time of day"""
        multipliers = {
            "morning": 1.0,    # Balanced suggestions
            "afternoon": 0.9,  # Slightly reduced complexity
            "evening": 0.8,    # More relaxed suggestions
            "night": 0.7       # Light suggestions
        }
        return multipliers.get(time_of_day, 1.0)

    async def _find_common_entities(
        self,
        memory1_id: UUID,
        memory2_id: UUID
    ) -> list[str]:
        """Find common entities between two memories"""
        # This is a simplified implementation
        # In production, you'd extract entities from memories
        return []

    async def _find_common_topics(
        self,
        memory1_id: UUID,
        memory2_id: UUID
    ) -> list[str]:
        """Find common topics between two memories"""
        # This is a simplified implementation
        # In production, you'd use topic modeling
        return []

    async def _find_memories_by_topic(
        self,
        user_id: str,
        topic: str,
        exclude_ids: list[UUID]
    ) -> list[dict[str, Any]]:
        """Find memories related to a topic"""
        # This is a simplified implementation
        # In production, you'd use topic search
        return []

    async def _analyze_relationship(
        self,
        memory1: Memory,
        memory2: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze potential relationship between memories"""
        try:
            prompt = f"""
            Analyze the relationship between these two memories:

            Memory 1: {memory1.title}
            {memory1.content[:500]}

            Memory 2: {memory2['title']}
            {memory2['content'][:500]}

            Determine:
            1. Should these be connected? (true/false)
            2. What type of relationship? (related_to, follows_from, contradicts, supports, etc.)
            3. Evidence supporting the connection (2-3 points)
            4. Potential insights from this connection (1-2 points)
            5. Confidence level (0-1)

            Format as JSON.
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=500
            )

            result = eval(response.choices[0].message.content)

            return {
                'should_connect': result.get('should_connect', False),
                'relationship_type': result.get('relationship_type', 'related_to'),
                'evidence': result.get('evidence', []),
                'insights': result.get('insights', []),
                'confidence': result.get('confidence', 0.5),
                'description': result.get('description', 'These memories appear to be related')
            }

        except Exception as e:
            logger.error(f"Error analyzing relationship: {e}")
            return {
                'should_connect': False,
                'relationship_type': 'unknown',
                'evidence': [],
                'insights': [],
                'confidence': 0.0,
                'description': 'Unable to analyze relationship'
            }

    async def _generate_followup_questions(
        self,
        memory: Memory
    ) -> list[dict[str, Any]]:
        """Generate follow-up questions for a memory"""
        try:
            prompt = f"""
            Based on this memory, generate 2-3 thought-provoking follow-up questions:

            Title: {memory.title}
            Content: {memory.content[:1000]}

            For each question provide:
            - question: The question text
            - reason: Why this question is valuable
            - answer_type: factual/exploratory/analytical/creative
            - topics: Related topics (1-3)
            - paths: Exploration paths (1-2 suggestions)
            - confidence: 0-1
            - priority: 0-1

            Format as JSON array.
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8,
                max_tokens=800
            )

            result = eval(response.choices[0].message.content)
            return result.get('questions', [])

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return []

    async def _identify_knowledge_gaps(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[dict[str, Any]]:
        """Identify knowledge gaps in user's memory system"""
        gaps = []

        try:
            # Time-based gaps
            time_gaps = await self._find_time_gaps(user_id)
            gaps.extend(time_gaps)

            # Topic coverage gaps
            topic_gaps = await self._find_topic_gaps(user_id, context)
            gaps.extend(topic_gaps)

            # Entity detail gaps
            entity_gaps = await self._find_entity_gaps(user_id, context)
            gaps.extend(entity_gaps)

            return sorted(gaps, key=lambda g: g['priority'], reverse=True)

        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {e}")
            return []

    async def _find_time_gaps(self, user_id: str) -> list[dict[str, Any]]:
        """Find temporal gaps in memory coverage"""
        # Simplified implementation
        return []

    async def _find_topic_gaps(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[dict[str, Any]]:
        """Find gaps in topic coverage"""
        # Simplified implementation
        return []

    async def _find_entity_gaps(
        self,
        user_id: str,
        context: SuggestionContext
    ) -> list[dict[str, Any]]:
        """Find gaps in entity information"""
        # Simplified implementation
        return []

    async def _generate_gap_question(
        self,
        gap: dict[str, Any]
    ) -> Optional[dict[str, str]]:
        """Generate a question to fill a knowledge gap"""
        questions = {
            'missing_topic': f"What do you know about {gap['area']}?",
            'incomplete_entity': f"Can you provide more details about {gap['area']}?",
            'time_gap': f"What happened during {gap['area']}?",
            'detail_gap': f"Can you elaborate on {gap['area']}?"
        }

        question = questions.get(gap['type'], f"Tell me more about {gap['area']}")

        return {
            'question': question,
            'type': gap['type'],
            'area': gap['area']
        }

    def _determine_review_needs(
        self,
        memory: Any
    ) -> dict[str, Any]:
        """Determine why and how a memory should be reviewed"""
        days_since_access = memory.days_since_access
        access_count = memory.access_count or 0

        # Calculate forgetting curve position
        expected_interval = pow(2, min(access_count, 10)) * 7
        overdue_factor = days_since_access / expected_interval if expected_interval > 0 else 1

        review_info = {
            'description': '',
            'reason': '',
            'review_type': '',
            'actions': [],
            'interval': 7,
            'urgency': 0.5,
            'confidence': 0.8
        }

        if overdue_factor > 1.5:
            review_info.update({
                'description': 'This memory is overdue for review based on spaced repetition',
                'reason': f'Last accessed {int(days_since_access)} days ago',
                'review_type': 'forgetting_curve',
                'actions': ['Review content', 'Test recall', 'Update if needed'],
                'interval': int(expected_interval),
                'urgency': min(overdue_factor / 2, 1.0)
            })
        elif memory.importance > 0.7 and days_since_access > 7:
            review_info.update({
                'description': 'High importance memory needs regular review',
                'reason': 'Maintaining important knowledge',
                'review_type': 'importance_decay',
                'actions': ['Refresh understanding', 'Check relevance'],
                'interval': 7,
                'urgency': 0.7
            })
        elif memory.created_at < datetime.utcnow() - timedelta(days=90) and memory.updated_at == memory.created_at:
            review_info.update({
                'description': 'Old memory may need updating',
                'reason': 'Not updated in over 90 days',
                'review_type': 'update_needed',
                'actions': ['Check accuracy', 'Add new information', 'Update relevance'],
                'interval': 30,
                'urgency': 0.6
            })
        else:
            review_info.update({
                'description': 'Regular quality check',
                'reason': 'Maintain memory quality',
                'review_type': 'quality_check',
                'actions': ['Verify accuracy', 'Improve clarity'],
                'interval': 60,
                'urgency': 0.3
            })

        return review_info
