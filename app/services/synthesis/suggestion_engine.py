"""Suggestion Engine for Smart Recommendations

Real implementation that provides intelligent suggestions for memory organization,
knowledge exploration, and learning paths based on user behavior and content analysis.
"""

import asyncio
import json
from app.utils.logging_config import get_logger
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from datetime import datetime
from datetime import timedelta
from collections import Counter
from collections import defaultdict
logger = get_logger(__name__)


class UserBehaviorProfile:
    """Tracks user behavior patterns for personalized suggestions"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.access_patterns: Dict[str, int] = defaultdict(int)
        self.topic_interests: Dict[str, float] = defaultdict(float)
        self.creation_patterns: Dict[str, Any] = {
            'peak_hours': [],
            'active_days': [],
            'avg_content_length': 0,
            'preferred_tags': Counter()
        }
        self.learning_velocity: float = 0.0
        self.exploration_score: float = 0.0


class SuggestionEngine:
    """Engine for generating intelligent suggestions and recommendations"""
    
    def __init__(self, db, memory_service, openai_client, analytics_engine):
        self.db = db
        self.memory_service = memory_service
        self.openai_client = openai_client
        self.analytics_engine = analytics_engine
        
        # Suggestion generation prompts
        self.suggestion_prompts = {
            'exploration': """
Based on this user's knowledge profile, suggest 3 new topics or areas to explore:

Current interests: {interests}
Recent topics: {recent_topics}
Knowledge gaps: {gaps}

Provide suggestions as a JSON array with:
- "topic": The topic to explore
- "reason": Why this would be valuable
- "starting_point": Where to begin
""",
            'connection': """
Analyze these disconnected knowledge areas and suggest how to connect them:

Area 1: {area1}
Area 2: {area2}
Current knowledge: {context}

Suggest 2-3 ways to bridge these areas with specific actions.
""",
            'consolidation': """
These memories appear related but scattered. Suggest how to consolidate:

Memories:
{memories}

Provide consolidation suggestions focusing on organization and synthesis.
"""
        }
    
    async def generate_suggestions(self, request: SuggestionRequest) -> SuggestionResponse:
        """Generate personalized suggestions based on request"""
        try:
            # Build user behavior profile
            profile = await self._build_user_profile(request.user_id)
            
            # Analyze current knowledge state
            knowledge_state = await self._analyze_knowledge_state(request.user_id)
            
            # Generate different types of suggestions
            suggestions = []
            
            if request.suggestion_types is None or SuggestionType.EXPLORE in request.suggestion_types:
                exploration_suggestions = await self._generate_exploration_suggestions(profile, knowledge_state)
                suggestions.extend(exploration_suggestions)
            
            if request.suggestion_types is None or SuggestionType.CONNECT in request.suggestion_types:
                connection_suggestions = await self._generate_connection_suggestions(profile, knowledge_state)
                suggestions.extend(connection_suggestions)
            
            if request.suggestion_types is None or SuggestionType.REVIEW in request.suggestion_types:
                review_suggestions = await self._generate_review_suggestions(profile, knowledge_state)
                suggestions.extend(review_suggestions)
            
            if request.suggestion_types is None or SuggestionType.ORGANIZE in request.suggestion_types:
                organization_suggestions = await self._generate_organization_suggestions(profile, knowledge_state)
                suggestions.extend(organization_suggestions)
            
            # Generate specialized suggestions
            learning_paths = await self._generate_learning_paths(profile, knowledge_state, request)
            content_suggestions = await self._generate_content_suggestions(profile, knowledge_state)
            organization_tips = await self._generate_organization_tips(profile, knowledge_state)
            
            # Sort by priority
            suggestions.sort(key=lambda s: s.priority, reverse=True)
            
            # Apply limit
            if request.limit:
                suggestions = suggestions[:request.limit]
            
            return SuggestionResponse(
                suggestions=suggestions,
                learning_paths=learning_paths,
                content_suggestions=content_suggestions,
                organization_suggestions=organization_tips,
                metadata={
                    'profile_completeness': self._calculate_profile_completeness(profile),
                    'knowledge_coverage': knowledge_state.get('coverage_score', 0.0),
                    'suggestion_confidence': self._calculate_suggestion_confidence(suggestions),
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return SuggestionResponse(
                suggestions=[],
                learning_paths=[],
                content_suggestions=[],
                organization_suggestions=[],
                metadata={'error': str(e)}
            )
    
    async def _build_user_profile(self, user_id: str) -> UserBehaviorProfile:
        """Build comprehensive user behavior profile"""
        profile = UserBehaviorProfile(user_id)
        
        # Analyze access patterns
        access_query = """
        SELECT memory_id, COUNT(*) as access_count, MAX(accessed_at) as last_access
        FROM access_logs
        WHERE user_id = $1 AND accessed_at > $2
        GROUP BY memory_id
        ORDER BY access_count DESC
        LIMIT 100
        """
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        access_logs = await self.db.fetch_all(access_query, user_id, thirty_days_ago)
        
        # Analyze creation patterns
        creation_query = """
        SELECT id, content, tags, importance, created_at
        FROM memories
        WHERE user_id = $1 AND created_at > $2
        ORDER BY created_at DESC
        LIMIT 200
        """
        
        recent_memories = await self.db.fetch_all(creation_query, user_id, thirty_days_ago)
        
        # Process access patterns
        for log in access_logs:
            memory = await self.memory_service.get_memory(str(log['memory_id']))
            if memory and hasattr(memory, 'tags'):
                for tag in memory.tags:
                    profile.access_patterns[tag] += log['access_count']
        
        # Process creation patterns
        if recent_memories:
            # Extract patterns
            creation_times = [m['created_at'] for m in recent_memories]
            profile.creation_patterns['peak_hours'] = self._find_peak_hours(creation_times)
            profile.creation_patterns['active_days'] = self._find_active_days(creation_times)
            
            # Content analysis
            content_lengths = [len(m['content']) for m in recent_memories]
            profile.creation_patterns['avg_content_length'] = np.mean(content_lengths)
            
            # Tag preferences
            for memory in recent_memories:
                if memory.get('tags'):
                    profile.creation_patterns['preferred_tags'].update(memory['tags'])
            
            # Calculate learning velocity (memories per day)
            days_span = (creation_times[0] - creation_times[-1]).days + 1
            profile.learning_velocity = len(recent_memories) / days_span
        
        # Calculate topic interests based on importance and recency
        for memory in recent_memories:
            if memory.get('tags'):
                recency_factor = 1.0 - ((datetime.utcnow() - memory['created_at']).days / 30)
                importance_factor = memory['importance'] / 10.0
                
                for tag in memory['tags']:
                    profile.topic_interests[tag] += (recency_factor * importance_factor)
        
        # Calculate exploration score (diversity of topics)
        unique_tags = set()
        for memory in recent_memories:
            if memory.get('tags'):
                unique_tags.update(memory['tags'])
        
        profile.exploration_score = len(unique_tags) / max(len(recent_memories), 1)
        
        return profile
    
    async def _analyze_knowledge_state(self, user_id: str) -> Dict[str, Any]:
        """Analyze current state of user's knowledge base"""
        # Get comprehensive analytics
        from app.insights.models import TimeFrame, InsightRequest
        
        insights = await self.analytics_engine.generate_insights(
            InsightRequest(time_frame=TimeFrame.MONTHLY, user_id=user_id)
        )
        
        # Get knowledge clusters
        clusters = await self.analytics_engine.analyze_clusters(
            {'user_id': user_id}  # Simplified request
        )
        
        # Analyze gaps
        gap_analysis = await self.analytics_engine.analyze_knowledge_gaps(
            {'user_id': user_id}
        )
        
        # Get memory statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_memories,
            COUNT(DISTINCT tags) as unique_tags,
            AVG(importance) as avg_importance,
            MAX(created_at) as last_activity
        FROM memories, unnest(tags) as tags
        WHERE user_id = $1
        """
        
        stats = await self.db.fetch_one(stats_query, user_id)
        
        return {
            'total_memories': stats['total_memories'] if stats else 0,
            'unique_topics': stats['unique_tags'] if stats else 0,
            'avg_importance': stats['avg_importance'] if stats else 0,
            'last_activity': stats['last_activity'] if stats else None,
            'insights': insights.insights if insights else [],
            'clusters': clusters.clusters if clusters else [],
            'knowledge_gaps': gap_analysis.gaps if gap_analysis else [],
            'coverage_score': gap_analysis.coverage_score if gap_analysis else 0.0
        }
    
    async def _generate_exploration_suggestions(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate suggestions for new topics to explore"""
        suggestions = []
        
        # Get top interests and gaps
        top_interests = sorted(profile.topic_interests.items(), key=lambda x: x[1], reverse=True)[:5]
        knowledge_gaps = knowledge_state.get('knowledge_gaps', [])[:5]
        
        # Use LLM to generate exploration suggestions
        prompt = self.suggestion_prompts['exploration'].format(
            interests=', '.join([t[0] for t in top_interests]),
            recent_topics=', '.join(list(profile.creation_patterns['preferred_tags'])[:5]),
            gaps=', '.join([g.area for g in knowledge_gaps]) if knowledge_gaps else 'None identified'
        )
        
        try:
            response = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.8
            )
            
            exploration_ideas = json.loads(response)
            
            for i, idea in enumerate(exploration_ideas[:3]):
                suggestions.append(Suggestion(
                    id=f"explore_{i}",
                    type=SuggestionType.EXPLORE,
                    title=f"Explore: {idea['topic']}",
                    description=idea['reason'],
                    action=ActionType.CREATE,
                    priority=0.8 - (i * 0.1),
                    metadata={
                        'topic': idea['topic'],
                        'starting_point': idea.get('starting_point', ''),
                        'related_interests': [t[0] for t in top_interests[:3]]
                    }
                ))
                
        except Exception as e:
            logger.error(f"Exploration suggestion generation failed: {e}")
            
            # Fallback suggestions based on gaps
            for i, gap in enumerate(knowledge_gaps[:2]):
                suggestions.append(Suggestion(
                    id=f"explore_gap_{i}",
                    type=SuggestionType.EXPLORE,
                    title=f"Fill Gap: {gap.area}",
                    description=f"You have limited knowledge in {gap.area}. "
                               f"Consider exploring: {', '.join(gap.suggested_topics[:3])}",
                    action=ActionType.CREATE,
                    priority=0.7,
                    metadata={
                        'gap_area': gap.area,
                        'suggested_topics': gap.suggested_topics
                    }
                ))
        
        return suggestions
    
    async def _generate_connection_suggestions(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate suggestions for connecting disparate knowledge areas"""
        suggestions = []
        
        # Find disconnected clusters
        clusters = knowledge_state.get('clusters', [])
        
        if len(clusters) >= 2:
            # Find clusters with low interconnection
            for i in range(min(len(clusters), 3)):
                for j in range(i + 1, min(len(clusters), 4)):
                    cluster1 = clusters[i]
                    cluster2 = clusters[j]
                    
                    # Check if clusters are disconnected
                    if self._clusters_disconnected(cluster1, cluster2):
                        suggestion = await self._create_connection_suggestion(
                            cluster1, cluster2, profile
                        )
                        if suggestion:
                            suggestions.append(suggestion)
        
        # Find isolated high-importance memories
        isolated_query = """
        SELECT m.id, m.content, m.tags, m.importance
        FROM memories m
        LEFT JOIN memory_relationships r ON m.id = r.source_id OR m.id = r.target_id
        WHERE m.user_id = $1 AND r.id IS NULL AND m.importance >= 7
        ORDER BY m.importance DESC
        LIMIT 5
        """
        
        isolated_memories = await self.db.fetch_all(isolated_query, profile.user_id)
        
        for memory in isolated_memories[:2]:
            suggestions.append(Suggestion(
                id=f"connect_isolated_{memory['id']}",
                type=SuggestionType.CONNECT,
                title="Connect Isolated Knowledge",
                description=f"This important memory is not connected to others: "
                           f"{memory['content'][:100]}...",
                action=ActionType.LINK,
                priority=0.7,
                metadata={
                    'memory_id': str(memory['id']),
                    'tags': memory.get('tags', []),
                    'importance': memory['importance']
                }
            ))
        
        return suggestions
    
    async def _generate_review_suggestions(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate suggestions for reviewing and reinforcing knowledge"""
        suggestions = []
        
        # Find memories that haven't been accessed recently
        review_query = """
        SELECT m.id, m.content, m.importance, m.created_at,
               COALESCE(MAX(a.accessed_at), m.created_at) as last_accessed
        FROM memories m
        LEFT JOIN access_logs a ON m.id = a.memory_id
        WHERE m.user_id = $1 AND m.importance >= 6
        GROUP BY m.id, m.content, m.importance, m.created_at
        HAVING COALESCE(MAX(a.accessed_at), m.created_at) < $2
        ORDER BY m.importance DESC, last_accessed ASC
        LIMIT 10
        """
        
        review_cutoff = datetime.utcnow() - timedelta(days=14)
        memories_to_review = await self.db.fetch_all(review_query, profile.user_id, review_cutoff)
        
        for i, memory in enumerate(memories_to_review[:3]):
            days_since_access = (datetime.utcnow() - memory['last_accessed']).days
            
            suggestions.append(Suggestion(
                id=f"review_{memory['id']}",
                type=SuggestionType.REVIEW,
                title="Review Important Knowledge",
                description=f"Haven't reviewed in {days_since_access} days: "
                           f"{memory['content'][:100]}...",
                action=ActionType.REVIEW,
                priority=0.6 + (memory['importance'] / 20),  # Higher importance = higher priority
                metadata={
                    'memory_id': str(memory['id']),
                    'days_since_access': days_since_access,
                    'importance': memory['importance']
                }
            ))
        
        # Suggest review sessions for topics with many memories
        topic_review_query = """
        SELECT tags, COUNT(*) as memory_count, AVG(importance) as avg_importance
        FROM memories, unnest(tags) as tags
        WHERE user_id = $1
        GROUP BY tags
        HAVING COUNT(*) >= 5
        ORDER BY COUNT(*) DESC
        LIMIT 5
        """
        
        topic_reviews = await self.db.fetch_all(topic_review_query, profile.user_id)
        
        for topic in topic_reviews[:2]:
            suggestions.append(Suggestion(
                id=f"review_topic_{topic['tags']}",
                type=SuggestionType.REVIEW,
                title=f"Deep Review: {topic['tags']}",
                description=f"You have {topic['memory_count']} memories on {topic['tags']}. "
                           f"Consider a focused review session.",
                action=ActionType.REVIEW,
                priority=0.65,
                metadata={
                    'topic': topic['tags'],
                    'memory_count': topic['memory_count'],
                    'avg_importance': float(topic['avg_importance'])
                }
            ))
        
        return suggestions
    
    async def _generate_organization_suggestions(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[Suggestion]:
        """Generate suggestions for better organization"""
        suggestions = []
        
        # Find untagged memories
        untagged_query = """
        SELECT id, content, importance
        FROM memories
        WHERE user_id = $1 AND (tags IS NULL OR tags = '{}')
        ORDER BY importance DESC, created_at DESC
        LIMIT 10
        """
        
        untagged_memories = await self.db.fetch_all(untagged_query, profile.user_id)
        
        if len(untagged_memories) >= 3:
            suggestions.append(Suggestion(
                id="organize_untagged",
                type=SuggestionType.ORGANIZE,
                title="Tag Unorganized Memories",
                description=f"You have {len(untagged_memories)} untagged memories. "
                           f"Adding tags will improve organization and discovery.",
                action=ActionType.TAG,
                priority=0.75,
                metadata={
                    'memory_ids': [str(m['id']) for m in untagged_memories[:5]],
                    'suggested_tags': list(profile.creation_patterns['preferred_tags'])[:5]
                }
            ))
        
        # Suggest consolidation for similar memories
        if knowledge_state.get('total_memories', 0) > 50:
            suggestions.append(Suggestion(
                id="organize_consolidate",
                type=SuggestionType.ORGANIZE,
                title="Consolidate Similar Memories",
                description="Run duplicate detection to find and merge similar memories. "
                           "This will reduce clutter and improve clarity.",
                action=ActionType.CONSOLIDATE,
                priority=0.7,
                metadata={
                    'estimated_duplicates': int(knowledge_state['total_memories'] * 0.1),  # Estimate
                    'recommended_threshold': 0.85
                }
            ))
        
        # Suggest creating synthesis for large topics
        large_topics = [
            tag for tag, count in profile.creation_patterns['preferred_tags'].items()
            if count >= 10
        ]
        
        for topic in large_topics[:2]:
            suggestions.append(Suggestion(
                id=f"organize_synthesize_{topic}",
                type=SuggestionType.ORGANIZE,
                title=f"Synthesize: {topic}",
                description=f"You have many memories about {topic}. "
                           f"Create a synthesis to consolidate this knowledge.",
                action=ActionType.SYNTHESIZE,
                priority=0.72,
                metadata={
                    'topic': topic,
                    'memory_count': profile.creation_patterns['preferred_tags'][topic]
                }
            ))
        
        return suggestions
    
    async def _generate_learning_paths(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any],
        request: SuggestionRequest
    ) -> List[LearningPathSuggestion]:
        """Generate personalized learning path suggestions"""
        paths = []
        
        # Path 1: Deepen existing interests
        if profile.topic_interests:
            top_interest = max(profile.topic_interests.items(), key=lambda x: x[1])[0]
            
            deepening_path = LearningPathSuggestion(
                path_name=f"Master {top_interest}",
                description=f"Deepen your knowledge in {top_interest} with advanced concepts",
                steps=[
                    f"Review fundamentals of {top_interest}",
                    f"Explore advanced {top_interest} techniques",
                    f"Study real-world {top_interest} applications",
                    f"Create synthesis of {top_interest} knowledge",
                    f"Connect {top_interest} to related fields"
                ],
                estimated_duration_days=30,
                difficulty_level="intermediate",
                prerequisites=[f"Basic knowledge of {top_interest}"],
                learning_objectives=[
                    f"Master advanced {top_interest} concepts",
                    "Apply knowledge to practical problems",
                    "Identify connections to other domains"
                ]
            )
            paths.append(deepening_path)
        
        # Path 2: Bridge knowledge gaps
        if knowledge_state.get('knowledge_gaps'):
            gap = knowledge_state['knowledge_gaps'][0]
            
            gap_filling_path = LearningPathSuggestion(
                path_name=f"Explore {gap.area}",
                description=f"Fill knowledge gap in {gap.area}",
                steps=[
                    f"Introduction to {gap.area}",
                    f"Core concepts of {gap.area}",
                    f"Connect {gap.area} to existing knowledge",
                    f"Practical exercises in {gap.area}",
                    f"Integration with current interests"
                ],
                estimated_duration_days=21,
                difficulty_level="beginner",
                prerequisites=[],
                learning_objectives=gap.suggested_topics[:3]
            )
            paths.append(gap_filling_path)
        
        # Path 3: Interdisciplinary exploration
        if len(profile.topic_interests) >= 2:
            topics = list(profile.topic_interests.keys())[:2]
            
            interdisciplinary_path = LearningPathSuggestion(
                path_name=f"Connect {topics[0]} & {topics[1]}",
                description="Explore connections between your interests",
                steps=[
                    f"Identify overlaps between {topics[0]} and {topics[1]}",
                    "Research interdisciplinary applications",
                    "Create synthesis memories",
                    "Develop integrated mental models",
                    "Apply combined knowledge"
                ],
                estimated_duration_days=14,
                difficulty_level="advanced",
                prerequisites=[f"Knowledge of {topics[0]}", f"Knowledge of {topics[1]}"],
                learning_objectives=[
                    "Discover unexpected connections",
                    "Develop holistic understanding",
                    "Create innovative combinations"
                ]
            )
            paths.append(interdisciplinary_path)
        
        return paths
    
    async def _generate_content_suggestions(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[ContentSuggestion]:
        """Generate content creation suggestions"""
        suggestions = []
        
        # Suggest content based on learning velocity
        if profile.learning_velocity > 1.0:  # More than 1 memory per day
            suggestions.append(ContentSuggestion(
                content_type="synthesis",
                topic="Weekly Knowledge Review",
                rationale="Your high learning velocity suggests regular synthesis would be valuable",
                prompts=[
                    "What were the key insights from this week?",
                    "How do this week's learnings connect?",
                    "What questions emerged from your exploration?"
                ],
                estimated_value=0.9
            ))
        
        # Suggest content for incomplete topics
        for topic, interest in profile.topic_interests.items():
            if interest > 0.7:  # High interest topic
                suggestions.append(ContentSuggestion(
                    content_type="deep_dive",
                    topic=topic,
                    rationale=f"You show strong interest in {topic} - time for deeper exploration",
                    prompts=[
                        f"What advanced aspects of {topic} intrigue you?",
                        f"How does {topic} connect to your other interests?",
                        f"What practical applications of {topic} have you discovered?"
                    ],
                    estimated_value=interest
                ))
        
        # Suggest reflection content
        if knowledge_state.get('total_memories', 0) > 100:
            suggestions.append(ContentSuggestion(
                content_type="reflection",
                topic="Knowledge Journey Reflection",
                rationale="With 100+ memories, reflection can reveal patterns and growth",
                prompts=[
                    "How has your understanding evolved?",
                    "What surprising connections have you discovered?",
                    "What would you tell your past self?"
                ],
                estimated_value=0.8
            ))
        
        return suggestions[:5]  # Limit to top 5
    
    async def _generate_organization_tips(
        self,
        profile: UserBehaviorProfile,
        knowledge_state: Dict[str, Any]
    ) -> List[OrganizationSuggestion]:
        """Generate organization improvement suggestions"""
        tips = []
        
        # Tip 1: Consistent tagging
        tag_variance = len(profile.creation_patterns['preferred_tags'])
        if tag_variance > 20:
            tips.append(OrganizationSuggestion(
                organization_type="tagging",
                title="Standardize Your Tags",
                description=f"You use {tag_variance} different tags. Consider consolidating similar ones.",
                impact_areas=["searchability", "organization", "synthesis"],
                implementation_steps=[
                    "Review your current tags",
                    "Identify similar or redundant tags",
                    "Create a tag hierarchy",
                    "Bulk update memories with new schema"
                ],
                estimated_effort="medium"
            ))
        
        # Tip 2: Create collections
        if knowledge_state.get('total_memories', 0) > 50:
            tips.append(OrganizationSuggestion(
                organization_type="structure",
                title="Create Memory Collections",
                description="Group related memories into collections for easier navigation",
                impact_areas=["navigation", "context", "learning"],
                implementation_steps=[
                    "Identify major themes in your memories",
                    "Create collection categories",
                    "Assign memories to collections",
                    "Add collection summaries"
                ],
                estimated_effort="high"
            ))
        
        # Tip 3: Regular maintenance
        tips.append(OrganizationSuggestion(
            organization_type="maintenance",
            title="Weekly Knowledge Maintenance",
            description="Establish a routine for knowledge base maintenance",
            impact_areas=["quality", "relevance", "growth"],
            implementation_steps=[
                "Review and tag new memories weekly",
                "Update importance scores monthly",
                "Create synthesis quarterly",
                "Archive outdated content annually"
            ],
            estimated_effort="low"
        ))
        
        return tips
    
    async def _create_connection_suggestion(
        self,
        cluster1: Any,
        cluster2: Any,
        profile: UserBehaviorProfile
    ) -> Optional[Suggestion]:
        """Create suggestion for connecting two clusters"""
        try:
            prompt = self.suggestion_prompts['connection'].format(
                area1=cluster1.cluster_theme,
                area2=cluster2.cluster_theme,
                context=f"User interests: {', '.join(list(profile.topic_interests.keys())[:5])}"
            )
            
            response = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.7
            )
            
            return Suggestion(
                id=f"connect_{cluster1.cluster_id}_{cluster2.cluster_id}",
                type=SuggestionType.CONNECT,
                title=f"Bridge: {cluster1.cluster_theme} ↔ {cluster2.cluster_theme}",
                description=response.strip(),
                action=ActionType.CREATE,
                priority=0.75,
                metadata={
                    'cluster1_id': cluster1.cluster_id,
                    'cluster2_id': cluster2.cluster_id,
                    'cluster1_size': cluster1.size,
                    'cluster2_size': cluster2.size
                }
            )
            
        except Exception as e:
            logger.error(f"Connection suggestion creation failed: {e}")
            return None
    
    def _clusters_disconnected(self, cluster1: Any, cluster2: Any) -> bool:
        """Check if two clusters are disconnected"""
        # Simple check - in real implementation would check actual edges
        common_nodes = set(cluster1.member_nodes).intersection(set(cluster2.member_nodes))
        return len(common_nodes) == 0
    
    def _find_peak_hours(self, creation_times: List[datetime]) -> List[int]:
        """Find peak activity hours"""
        hours = [t.hour for t in creation_times]
        hour_counts = Counter(hours)
        
        # Get top 3 hours
        peak_hours = [h for h, _ in hour_counts.most_common(3)]
        return sorted(peak_hours)
    
    def _find_active_days(self, creation_times: List[datetime]) -> List[str]:
        """Find most active days of week"""
        weekdays = [t.strftime('%A') for t in creation_times]
        day_counts = Counter(weekdays)
        
        # Get top 2 days
        active_days = [d for d, _ in day_counts.most_common(2)]
        return active_days
    
    def _calculate_profile_completeness(self, profile: UserBehaviorProfile) -> float:
        """Calculate how complete the user profile is"""
        scores = []
        
        # Access patterns
        scores.append(min(len(profile.access_patterns) / 10, 1.0))
        
        # Topic interests
        scores.append(min(len(profile.topic_interests) / 5, 1.0))
        
        # Creation patterns
        scores.append(1.0 if profile.creation_patterns['peak_hours'] else 0.0)
        
        # Learning velocity
        scores.append(min(profile.learning_velocity / 0.5, 1.0))  # 0.5 memories/day is good
        
        return sum(scores) / len(scores)
    
    def _calculate_suggestion_confidence(self, suggestions: List[Suggestion]) -> float:
        """Calculate overall confidence in suggestions"""
        if not suggestions:
            return 0.0
        
        # Average priority as proxy for confidence
        avg_priority = sum(s.priority for s in suggestions) / len(suggestions)
        
        # Diversity bonus
        suggestion_types = set(s.type for s in suggestions)
        diversity_bonus = len(suggestion_types) / 4  # 4 types total
        
        return min((avg_priority + diversity_bonus * 0.2), 1.0)