"""
Main analytics engine that coordinates all insight generation components
"""

import asyncio
from datetime import datetime
from typing import Any

from .cluster_analyzer import ClusterAnalyzer
from .gap_detector import KnowledgeGapDetector
from .insight_generator import InsightGenerator
from .models import (
    ClusteringRequest,
    ClusterResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
    InsightRequest,
    InsightResponse,
    LearningProgress,
    PatternDetectionRequest,
    PatternResponse,
    TimeFrame,
)
from .pattern_detector import PatternDetector
from typing import Any
from datetime import datetime
from datetime import timedelta


class AnalyticsEngine:
    """
    Orchestrates all analytics and insight generation components
    """

    def __init__(self, database):
        self.db = database
        self.pattern_detector = PatternDetector(database)
        self.cluster_analyzer = ClusterAnalyzer(database)
        self.gap_detector = KnowledgeGapDetector(database)
        self.insight_generator = InsightGenerator(database)

    async def generate_insights(
        self,
        request: InsightRequest
    ) -> InsightResponse:
        """Generate comprehensive insights"""
        insights, statistics = await self.insight_generator.generate_insights(request)

        return InsightResponse(
            insights=insights,
            total=len(insights),
            time_frame=request.time_frame,
            generated_at=datetime.utcnow(),
            statistics=statistics
        )

    async def detect_patterns(
        self,
        request: PatternDetectionRequest
    ) -> PatternResponse:
        """Detect patterns in memory usage and content"""
        patterns = await self.pattern_detector.detect_patterns(request)

        return PatternResponse(
            patterns=patterns,
            total=len(patterns),
            time_frame=request.time_frame,
            detected_at=datetime.utcnow()
        )

    async def analyze_clusters(
        self,
        request: ClusteringRequest
    ) -> ClusterResponse:
        """Perform memory clustering analysis"""
        clusters, quality_score = await self.cluster_analyzer.analyze_clusters(request)

        # Calculate clustering statistics
        total_clustered = sum(cluster.size for cluster in clusters)
        total_memories = await self._get_total_memory_count()
        unclustered = total_memories - total_clustered

        return ClusterResponse(
            clusters=clusters,
            total_clusters=len(clusters),
            total_memories_clustered=total_clustered,
            unclustered_memories=unclustered,
            clustering_quality_score=quality_score
        )

    async def analyze_knowledge_gaps(
        self,
        request: GapAnalysisRequest
    ) -> GapAnalysisResponse:
        """Analyze knowledge gaps and suggest improvements"""
        gaps = await self.gap_detector.analyze_gaps(request)

        # Calculate coverage score
        coverage_score = await self._calculate_knowledge_coverage()

        # Generate learning paths
        learning_paths = self._generate_learning_paths(gaps)

        return GapAnalysisResponse(
            gaps=gaps,
            total=len(gaps),
            coverage_score=coverage_score,
            suggested_learning_paths=learning_paths,
            analyzed_at=datetime.utcnow()
        )

    async def get_learning_progress(
        self,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> LearningProgress:
        """Calculate learning progress metrics"""
        # Get memories for timeframe
        memories = await self._get_memories_for_timeframe(time_frame)

        # Calculate metrics
        topics = set()
        topic_memories = {}

        for memory in memories:
            for tag in memory.get('tags', []):
                topics.add(tag)
                if tag not in topic_memories:
                    topic_memories[tag] = []
                topic_memories[tag].append(memory)

        # Calculate mastery levels
        mastery_levels = {}
        for topic, topic_mems in topic_memories.items():
            # Simple mastery calculation based on count and importance
            count_factor = min(len(topic_mems) / 10, 1.0)
            avg_importance = sum(m.get('importance', 0) for m in topic_mems) / len(topic_mems)
            importance_factor = avg_importance / 10.0

            mastery_levels[topic] = (count_factor + importance_factor) / 2

        # Calculate retention score (simplified)
        if memories:
            accessed_memories = await self._get_accessed_memory_count(time_frame)
            retention_score = min(accessed_memories / len(memories), 1.0)
        else:
            retention_score = 0.0

        # Calculate learning velocity
        period_days = self._get_period_days(time_frame)
        learning_velocity = len(memories) / period_days if period_days > 0 else 0.0

        # Identify improvement areas
        improvement_areas = [
            topic for topic, mastery in mastery_levels.items()
            if mastery < 0.5
        ]

        # Generate achievements
        achievements = []
        if len(memories) > 50:
            achievements.append("Knowledge Builder: 50+ memories created")
        if len(topics) > 20:
            achievements.append("Diverse Learner: 20+ topics explored")
        if any(mastery > 0.8 for mastery in mastery_levels.values()):
            achievements.append("Subject Expert: High mastery achieved")

        return LearningProgress(
            time_frame=time_frame,
            topics_covered=len(topics),
            memories_created=len(memories),
            knowledge_retention_score=retention_score,
            learning_velocity=learning_velocity,
            mastery_levels=mastery_levels,
            improvement_areas=improvement_areas[:10],
            achievements=achievements
        )

    async def get_comprehensive_analytics(
        self,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> dict[str, Any]:
        """Get all analytics in one call"""
        # Run all analytics concurrently
        results = await asyncio.gather(
            self.generate_insights(InsightRequest(time_frame=time_frame)),
            self.detect_patterns(PatternDetectionRequest(time_frame=time_frame)),
            self.analyze_clusters(ClusteringRequest()),
            self.analyze_knowledge_gaps(GapAnalysisRequest()),
            self.get_learning_progress(time_frame),
            return_exceptions=True
        )

        # Handle results
        analytics = {
            'timestamp': datetime.utcnow().isoformat(),
            'time_frame': time_frame.value,
            'insights': None,
            'patterns': None,
            'clusters': None,
            'knowledge_gaps': None,
            'learning_progress': None,
            'errors': []
        }

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                analytics['errors'].append({
                    'component': ['insights', 'patterns', 'clusters', 'gaps', 'progress'][i],
                    'error': str(result)
                })
            else:
                if i == 0:
                    analytics['insights'] = result.dict()
                elif i == 1:
                    analytics['patterns'] = result.dict()
                elif i == 2:
                    analytics['clusters'] = result.dict()
                elif i == 3:
                    analytics['knowledge_gaps'] = result.dict()
                elif i == 4:
                    analytics['learning_progress'] = result.dict()

        return analytics

    async def _get_total_memory_count(self) -> int:
        """Get total number of memories with embeddings"""
        query = "SELECT COUNT(*) as count FROM memories WHERE content_vector IS NOT NULL"
        result = await self.db.fetch_one(query)
        return result['count'] if result else 0

    async def _calculate_knowledge_coverage(self) -> float:
        """Calculate overall knowledge coverage score"""
        # Get domain coverage
        query = """
        SELECT COUNT(DISTINCT tags) as unique_tags,
               COUNT(*) as total_memories,
               AVG(importance) as avg_importance
        FROM memories, unnest(tags) as tags
        """

        result = await self.db.fetch_one(query)

        if not result or result['total_memories'] == 0:
            return 0.0

        # Simple coverage calculation
        tag_factor = min(result['unique_tags'] / 50, 1.0)  # 50 tags = good coverage
        memory_factor = min(result['total_memories'] / 500, 1.0)  # 500 memories = good
        importance_factor = result['avg_importance'] / 10.0

        coverage_score = (tag_factor + memory_factor + importance_factor) / 3

        return coverage_score

    def _generate_learning_paths(
        self,
        gaps: list[Any]
    ) -> list[dict[str, Any]]:
        """Generate suggested learning paths based on gaps"""
        learning_paths = []

        # Group gaps by area type
        domain_gaps = [g for g in gaps if "Domain:" in g.area]
        topic_gaps = [g for g in gaps if "Topic:" in g.area]

        # Create learning paths
        if domain_gaps:
            # Domain-focused path
            path = {
                'name': 'Domain Mastery Path',
                'description': 'Focus on building foundational knowledge in key domains',
                'duration_weeks': len(domain_gaps) * 2,
                'steps': []
            }

            for gap in domain_gaps[:5]:
                domain = gap.area.replace('Domain: ', '')
                path['steps'].append({
                    'week': len(path['steps']) + 1,
                    'focus': domain,
                    'goals': gap.suggested_topics[:3],
                    'target_memories': 10
                })

            learning_paths.append(path)

        if topic_gaps:
            # Topic depth path
            path = {
                'name': 'Topic Deep Dive Path',
                'description': 'Deepen understanding of specific topics',
                'duration_weeks': len(topic_gaps),
                'steps': []
            }

            for gap in topic_gaps[:5]:
                topic = gap.area.replace('Shallow Coverage: ', '').replace('Isolated Topic: ', '')
                path['steps'].append({
                    'week': len(path['steps']) + 1,
                    'focus': topic,
                    'goals': ['Research advanced concepts', 'Find practical applications', 'Connect with other topics'],
                    'target_memories': 5
                })

            learning_paths.append(path)

        # Balanced learning path
        if learning_paths:
            balanced_path = {
                'name': 'Balanced Learning Path',
                'description': 'Mix of breadth and depth across multiple areas',
                'duration_weeks': 8,
                'steps': []
            }

            # Alternate between domain and topic focuses
            week = 1
            for i in range(4):
                if i < len(domain_gaps):
                    domain = domain_gaps[i].area.replace('Domain: ', '')
                    balanced_path['steps'].append({
                        'week': week,
                        'focus': f'Foundation: {domain}',
                        'goals': ['Learn basics', 'Understand core concepts'],
                        'target_memories': 8
                    })
                    week += 1

                if i < len(topic_gaps):
                    topic = topic_gaps[i].area.split(': ')[-1]
                    balanced_path['steps'].append({
                        'week': week,
                        'focus': f'Deep Dive: {topic}',
                        'goals': ['Advanced study', 'Practical application'],
                        'target_memories': 6
                    })
                    week += 1

            if balanced_path['steps']:
                learning_paths.append(balanced_path)

        return learning_paths

    async def _get_memories_for_timeframe(
        self,
        time_frame: TimeFrame
    ) -> list[dict[str, Any]]:
        """Get memories for specified timeframe"""
        from datetime import timedelta

        now = datetime.utcnow()

        if time_frame == TimeFrame.DAILY:
            start_date = now - timedelta(days=1)
        elif time_frame == TimeFrame.WEEKLY:
            start_date = now - timedelta(weeks=1)
        elif time_frame == TimeFrame.MONTHLY:
            start_date = now - timedelta(days=30)
        elif time_frame == TimeFrame.QUARTERLY:
            start_date = now - timedelta(days=90)
        elif time_frame == TimeFrame.YEARLY:
            start_date = now - timedelta(days=365)
        else:  # ALL_TIME
            start_date = datetime.min

        query = """
        SELECT * FROM memories
        WHERE created_at >= $1
        ORDER BY created_at DESC
        """

        return await self.db.fetch_all(query, start_date)

    async def _get_accessed_memory_count(
        self,
        time_frame: TimeFrame
    ) -> int:
        """Get count of accessed memories in timeframe"""
        from datetime import timedelta

        now = datetime.utcnow()

        if time_frame == TimeFrame.DAILY:
            start_date = now - timedelta(days=1)
        elif time_frame == TimeFrame.WEEKLY:
            start_date = now - timedelta(weeks=1)
        elif time_frame == TimeFrame.MONTHLY:
            start_date = now - timedelta(days=30)
        elif time_frame == TimeFrame.QUARTERLY:
            start_date = now - timedelta(days=90)
        elif time_frame == TimeFrame.YEARLY:
            start_date = now - timedelta(days=365)
        else:  # ALL_TIME
            start_date = datetime.min

        query = """
        SELECT COUNT(DISTINCT memory_id) as count
        FROM access_logs
        WHERE accessed_at >= $1
        """

        result = await self.db.fetch_one(query, start_date)
        return result['count'] if result else 0

    def _get_period_days(self, time_frame: TimeFrame) -> int:
        """Get number of days in time frame"""
        mapping = {
            TimeFrame.DAILY: 1,
            TimeFrame.WEEKLY: 7,
            TimeFrame.MONTHLY: 30,
            TimeFrame.QUARTERLY: 90,
            TimeFrame.YEARLY: 365,
            TimeFrame.ALL_TIME: 3650  # 10 years
        }
        return mapping.get(time_frame, 30)
