"""
AI-powered insight generation from memory patterns and statistics
"""

import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import numpy as np

from .models import Insight, InsightRequest, InsightType, TimeFrame, UsageStatistics
from typing import Any
from datetime import datetime
from datetime import timedelta
from collections import Counter
from collections import defaultdict


class InsightGenerator:
    """Generates actionable insights from memory analysis"""

    def __init__(self, database):
        self.db = database

    async def generate_insights(
        self,
        request: InsightRequest
    ) -> tuple[list[Insight], UsageStatistics]:
        """Generate insights based on request parameters"""
        # Get memories and usage data
        memories, access_logs = await self._get_data_for_timeframe(request.time_frame)

        if not memories:
            return [], self._empty_statistics(request.time_frame)

        # Calculate usage statistics
        statistics = await self._calculate_usage_statistics(
            memories,
            access_logs,
            request.time_frame
        )

        # Generate insights based on requested types
        insight_types = request.insight_types or list(InsightType)
        insights = []

        generation_tasks = []
        for insight_type in insight_types:
            if insight_type == InsightType.USAGE_PATTERN:
                generation_tasks.append(
                    self._generate_usage_pattern_insights(memories, access_logs, statistics)
                )
            elif insight_type == InsightType.KNOWLEDGE_GROWTH:
                generation_tasks.append(
                    self._generate_knowledge_growth_insights(memories, statistics)
                )
            elif insight_type == InsightType.MEMORY_CLUSTER:
                generation_tasks.append(
                    self._generate_cluster_insights(memories)
                )
            elif insight_type == InsightType.LEARNING_TREND:
                generation_tasks.append(
                    self._generate_learning_trend_insights(memories, statistics)
                )
            elif insight_type == InsightType.ACCESS_PATTERN:
                generation_tasks.append(
                    self._generate_access_pattern_insights(access_logs, memories)
                )
            elif insight_type == InsightType.TAG_EVOLUTION:
                generation_tasks.append(
                    self._generate_tag_evolution_insights(memories)
                )
            elif insight_type == InsightType.IMPORTANCE_SHIFT:
                generation_tasks.append(
                    self._generate_importance_shift_insights(memories)
                )

        # Run all generation tasks concurrently
        insight_results = await asyncio.gather(*generation_tasks)

        # Flatten and filter results
        for insight_list in insight_results:
            for insight in insight_list:
                if insight.confidence >= request.min_confidence:
                    insights.append(insight)

        # Sort by impact score and limit
        insights.sort(key=lambda i: i.impact_score, reverse=True)
        insights = insights[:request.limit]

        # Add recommendations if requested
        if request.include_recommendations:
            for insight in insights:
                insight.recommendations = self._generate_recommendations(insight)

        return insights, statistics

    async def _get_data_for_timeframe(
        self,
        time_frame: TimeFrame
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Get memories and access logs for specified timeframe"""
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

        # Get memories
        memories_query = """
        SELECT * FROM memories
        WHERE created_at >= $1
        ORDER BY created_at DESC
        """
        memories = await self.db.fetch_all(memories_query, start_date)

        # Get access logs
        access_query = """
        SELECT * FROM access_logs
        WHERE accessed_at >= $1
        ORDER BY accessed_at DESC
        """
        access_logs = await self.db.fetch_all(access_query, start_date)

        return memories, access_logs

    async def _calculate_usage_statistics(
        self,
        memories: list[dict[str, Any]],
        access_logs: list[dict[str, Any]],
        time_frame: TimeFrame
    ) -> UsageStatistics:
        """Calculate comprehensive usage statistics"""
        # Basic counts
        total_memories = len(memories)
        total_accesses = len(access_logs)

        # Unique accessed memories
        accessed_memory_ids = set(log['memory_id'] for log in access_logs)
        unique_accessed = len(accessed_memory_ids)

        # Most accessed memories
        access_counts = Counter(log['memory_id'] for log in access_logs)
        most_accessed = [
            memory_id for memory_id, _ in access_counts.most_common(10)
        ]

        # Access frequency by hour/day
        access_frequency = defaultdict(int)
        for log in access_logs:
            if time_frame in [TimeFrame.DAILY, TimeFrame.WEEKLY]:
                key = str(log['accessed_at'].hour)
            else:
                key = log['accessed_at'].strftime('%Y-%m-%d')
            access_frequency[key] += 1

        # Peak usage times
        peak_times = sorted(
            access_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        peak_usage_times = [time for time, _ in peak_times]

        # Average importance
        avg_importance = np.mean([
            m.get('importance', 0) for m in memories
        ]) if memories else 0.0

        # Growth rate
        if time_frame != TimeFrame.ALL_TIME and memories:
            # Compare to previous period
            period_days = self._get_period_days(time_frame)
            prev_start = memories[0]['created_at'] - timedelta(days=period_days * 2)
            prev_end = memories[0]['created_at'] - timedelta(days=period_days)

            prev_query = """
            SELECT COUNT(*) as count FROM memories
            WHERE created_at >= $1 AND created_at < $2
            """
            prev_result = await self.db.fetch_one(prev_query, prev_start, prev_end)
            prev_count = prev_result['count'] if prev_result else 0

            if prev_count > 0:
                growth_rate = ((total_memories - prev_count) / prev_count) * 100
            else:
                growth_rate = 100.0 if total_memories > 0 else 0.0
        else:
            growth_rate = 0.0

        return UsageStatistics(
            time_frame=time_frame,
            total_memories=total_memories,
            total_accesses=total_accesses,
            unique_accessed=unique_accessed,
            average_importance=avg_importance,
            most_accessed_memories=most_accessed,
            access_frequency=dict(access_frequency),
            peak_usage_times=peak_usage_times,
            growth_rate=growth_rate
        )

    async def _generate_usage_pattern_insights(
        self,
        memories: list[dict[str, Any]],
        access_logs: list[dict[str, Any]],
        statistics: UsageStatistics
    ) -> list[Insight]:
        """Generate insights about usage patterns"""
        insights = []

        # Insight: Memory access concentration
        if statistics.unique_accessed > 0:
            access_ratio = statistics.unique_accessed / statistics.total_memories

            if access_ratio < 0.3:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.USAGE_PATTERN,
                    title="Low Memory Utilization",
                    description=f"Only {access_ratio*100:.1f}% of memories are being accessed",
                    confidence=0.9,
                    impact_score=7.5,
                    data={
                        'accessed_ratio': access_ratio,
                        'total_memories': statistics.total_memories,
                        'accessed_memories': statistics.unique_accessed
                    },
                    created_at=datetime.utcnow(),
                    time_frame=statistics.time_frame,
                    affected_memories=[]
                )
                insights.append(insight)

        # Insight: Access time patterns
        if statistics.peak_usage_times:
            peak_hour = statistics.peak_usage_times[0]
            peak_accesses = statistics.access_frequency[peak_hour]

            if statistics.total_accesses > 0:
                peak_concentration = peak_accesses / statistics.total_accesses

                if peak_concentration > 0.3:
                    insight = Insight(
                        id=uuid4(),
                        type=InsightType.USAGE_PATTERN,
                        title="Concentrated Usage Pattern",
                        description=f"Peak usage at {peak_hour} accounts for {peak_concentration*100:.1f}% of activity",
                        confidence=0.8,
                        impact_score=6.0,
                        data={
                            'peak_time': peak_hour,
                            'peak_percentage': peak_concentration,
                            'distribution': dict(list(statistics.access_frequency.items())[:24])
                        },
                        created_at=datetime.utcnow(),
                        time_frame=statistics.time_frame,
                        affected_memories=[]
                    )
                    insights.append(insight)

        return insights

    async def _generate_knowledge_growth_insights(
        self,
        memories: list[dict[str, Any]],
        statistics: UsageStatistics
    ) -> list[Insight]:
        """Generate insights about knowledge growth"""
        insights = []

        # Insight: Growth acceleration/deceleration
        if statistics.growth_rate != 0:
            if statistics.growth_rate > 50:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.KNOWLEDGE_GROWTH,
                    title="Rapid Knowledge Expansion",
                    description=f"Knowledge base growing at {statistics.growth_rate:.1f}% rate",
                    confidence=0.9,
                    impact_score=8.0,
                    data={
                        'growth_rate': statistics.growth_rate,
                        'new_memories': statistics.total_memories,
                        'time_frame': statistics.time_frame.value
                    },
                    created_at=datetime.utcnow(),
                    time_frame=statistics.time_frame,
                    affected_memories=[m['id'] for m in memories[:5]]
                )
                insights.append(insight)

            elif statistics.growth_rate < -20:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.KNOWLEDGE_GROWTH,
                    title="Knowledge Addition Slowdown",
                    description=f"Memory creation decreased by {abs(statistics.growth_rate):.1f}%",
                    confidence=0.8,
                    impact_score=6.5,
                    data={
                        'growth_rate': statistics.growth_rate,
                        'total_memories': statistics.total_memories
                    },
                    created_at=datetime.utcnow(),
                    time_frame=statistics.time_frame,
                    affected_memories=[]
                )
                insights.append(insight)

        # Insight: Knowledge diversity
        if memories:
            unique_tags = set()
            for memory in memories:
                unique_tags.update(memory.get('tags', []))

            diversity_score = len(unique_tags) / len(memories)

            if diversity_score > 0.7:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.KNOWLEDGE_GROWTH,
                    title="High Knowledge Diversity",
                    description=f"Covering {len(unique_tags)} different topics across {len(memories)} memories",
                    confidence=0.85,
                    impact_score=7.0,
                    data={
                        'unique_topics': len(unique_tags),
                        'diversity_score': diversity_score,
                        'top_topics': list(unique_tags)[:10]
                    },
                    created_at=datetime.utcnow(),
                    time_frame=statistics.time_frame,
                    affected_memories=[]
                )
                insights.append(insight)

        return insights

    async def _generate_cluster_insights(
        self,
        memories: list[dict[str, Any]]
    ) -> list[Insight]:
        """Generate insights about memory clusters"""
        insights = []

        # Simple clustering by tags
        tag_clusters = defaultdict(list)
        for memory in memories:
            for tag in memory.get('tags', []):
                tag_clusters[tag].append(memory)

        # Find significant clusters
        significant_clusters = [
            (tag, mems) for tag, mems in tag_clusters.items()
            if len(mems) >= 5
        ]

        if significant_clusters:
            # Sort by size
            significant_clusters.sort(key=lambda x: len(x[1]), reverse=True)

            top_cluster = significant_clusters[0]
            insight = Insight(
                id=uuid4(),
                type=InsightType.MEMORY_CLUSTER,
                title=f"Major Knowledge Cluster: {top_cluster[0]}",
                description=f"Strong focus on '{top_cluster[0]}' with {len(top_cluster[1])} related memories",
                confidence=0.9,
                impact_score=7.5,
                data={
                    'cluster_topic': top_cluster[0],
                    'cluster_size': len(top_cluster[1]),
                    'other_clusters': [
                        {'topic': tag, 'size': len(mems)}
                        for tag, mems in significant_clusters[1:6]
                    ]
                },
                created_at=datetime.utcnow(),
                time_frame=TimeFrame.ALL_TIME,
                affected_memories=[m['id'] for m in top_cluster[1][:10]]
            )
            insights.append(insight)

        return insights

    async def _generate_learning_trend_insights(
        self,
        memories: list[dict[str, Any]],
        statistics: UsageStatistics
    ) -> list[Insight]:
        """Generate insights about learning trends"""
        insights = []

        # Analyze importance trends
        if len(memories) >= 10:
            # Split into time buckets
            sorted_memories = sorted(memories, key=lambda m: m['created_at'])

            # Compare first half vs second half
            mid_point = len(sorted_memories) // 2
            first_half = sorted_memories[:mid_point]
            second_half = sorted_memories[mid_point:]

            first_avg_importance = np.mean([m.get('importance', 0) for m in first_half])
            second_avg_importance = np.mean([m.get('importance', 0) for m in second_half])

            importance_change = second_avg_importance - first_avg_importance

            if abs(importance_change) > 1.0:
                trend = "increasing" if importance_change > 0 else "decreasing"
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.LEARNING_TREND,
                    title=f"Memory Importance {trend.capitalize()}",
                    description=f"Average importance {trend} by {abs(importance_change):.1f} points",
                    confidence=0.75,
                    impact_score=6.0,
                    data={
                        'first_period_avg': first_avg_importance,
                        'second_period_avg': second_avg_importance,
                        'change': importance_change
                    },
                    created_at=datetime.utcnow(),
                    time_frame=statistics.time_frame,
                    affected_memories=[]
                )
                insights.append(insight)

        return insights

    async def _generate_access_pattern_insights(
        self,
        access_logs: list[dict[str, Any]],
        memories: list[dict[str, Any]]
    ) -> list[Insight]:
        """Generate insights about memory access patterns"""
        insights = []

        if not access_logs:
            return insights

        # Analyze recency bias
        memory_dict = {m['id']: m for m in memories}
        accessed_memories = []

        for log in access_logs:
            if log['memory_id'] in memory_dict:
                accessed_memories.append(memory_dict[log['memory_id']])

        if accessed_memories:
            # Calculate average age of accessed memories
            now = datetime.utcnow()
            ages = [(now - m['created_at']).days for m in accessed_memories]
            avg_age = np.mean(ages)

            # Compare to overall average
            all_ages = [(now - m['created_at']).days for m in memories]
            overall_avg_age = np.mean(all_ages)

            if avg_age < overall_avg_age * 0.5:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.ACCESS_PATTERN,
                    title="Recency Bias in Access Pattern",
                    description=f"Accessing newer memories {(overall_avg_age/avg_age):.1f}x more than older ones",
                    confidence=0.8,
                    impact_score=6.5,
                    data={
                        'accessed_avg_age_days': avg_age,
                        'overall_avg_age_days': overall_avg_age,
                        'bias_factor': overall_avg_age / avg_age
                    },
                    created_at=datetime.utcnow(),
                    time_frame=TimeFrame.ALL_TIME,
                    affected_memories=[]
                )
                insights.append(insight)

        return insights

    async def _generate_tag_evolution_insights(
        self,
        memories: list[dict[str, Any]]
    ) -> list[Insight]:
        """Generate insights about tag evolution"""
        insights = []

        # Group memories by time period
        time_buckets = defaultdict(list)

        for memory in memories:
            month_key = memory['created_at'].strftime('%Y-%m')
            time_buckets[month_key].append(memory)

        if len(time_buckets) >= 3:
            # Analyze tag changes over time
            monthly_tags = {}
            for month, month_memories in sorted(time_buckets.items()):
                tags = []
                for mem in month_memories:
                    tags.extend(mem.get('tags', []))
                monthly_tags[month] = Counter(tags)

            # Find emerging tags
            recent_months = sorted(monthly_tags.keys())[-3:]
            older_months = sorted(monthly_tags.keys())[:-3]

            recent_tags = set()
            for month in recent_months:
                recent_tags.update(monthly_tags[month].keys())

            older_tags = set()
            for month in older_months:
                older_tags.update(monthly_tags[month].keys())

            new_tags = recent_tags - older_tags

            if new_tags:
                insight = Insight(
                    id=uuid4(),
                    type=InsightType.TAG_EVOLUTION,
                    title="Emerging Topics",
                    description=f"New topics appearing: {', '.join(list(new_tags)[:5])}",
                    confidence=0.85,
                    impact_score=7.0,
                    data={
                        'new_tags': list(new_tags),
                        'timeline': {
                            month: list(tags.keys())[:10]
                            for month, tags in list(monthly_tags.items())[-6:]
                        }
                    },
                    created_at=datetime.utcnow(),
                    time_frame=TimeFrame.QUARTERLY,
                    affected_memories=[]
                )
                insights.append(insight)

        return insights

    async def _generate_importance_shift_insights(
        self,
        memories: list[dict[str, Any]]
    ) -> list[Insight]:
        """Generate insights about importance shifts"""
        insights = []

        # Group by tags and analyze importance changes
        tag_importance = defaultdict(list)

        for memory in memories:
            importance = memory.get('importance', 0)
            for tag in memory.get('tags', []):
                tag_importance[tag].append((memory['created_at'], importance))

        # Find tags with significant importance shifts
        for tag, importance_list in tag_importance.items():
            if len(importance_list) >= 5:
                # Sort by date
                importance_list.sort(key=lambda x: x[0])

                # Compare early vs late importance
                early_imp = [imp for _, imp in importance_list[:len(importance_list)//2]]
                late_imp = [imp for _, imp in importance_list[len(importance_list)//2:]]

                early_avg = np.mean(early_imp)
                late_avg = np.mean(late_imp)

                change = late_avg - early_avg

                if abs(change) > 2.0:
                    direction = "increased" if change > 0 else "decreased"
                    insight = Insight(
                        id=uuid4(),
                        type=InsightType.IMPORTANCE_SHIFT,
                        title=f"Importance Shift: {tag}",
                        description=f"'{tag}' importance {direction} by {abs(change):.1f} points",
                        confidence=0.7,
                        impact_score=5.5,
                        data={
                            'tag': tag,
                            'early_importance': early_avg,
                            'late_importance': late_avg,
                            'change': change,
                            'memory_count': len(importance_list)
                        },
                        created_at=datetime.utcnow(),
                        time_frame=TimeFrame.ALL_TIME,
                        affected_memories=[]
                    )
                    insights.append(insight)

        return insights

    def _generate_recommendations(self, insight: Insight) -> list[str]:
        """Generate recommendations based on insight type"""
        recommendations = []

        if insight.type == InsightType.USAGE_PATTERN:
            if "Low Memory Utilization" in insight.title:
                recommendations.extend([
                    "Review and organize older memories for better discoverability",
                    "Consider adding tags to improve searchability",
                    "Set up regular review sessions for forgotten content"
                ])
            elif "Concentrated Usage" in insight.title:
                recommendations.extend([
                    "Explore memories from different time periods",
                    "Diversify your learning schedule",
                    "Set reminders for off-peak learning times"
                ])

        elif insight.type == InsightType.KNOWLEDGE_GROWTH:
            if "Rapid Knowledge Expansion" in insight.title:
                recommendations.extend([
                    "Maintain momentum with consistent learning",
                    "Consider organizing recent memories into themes",
                    "Review and consolidate related information"
                ])
            elif "Slowdown" in insight.title:
                recommendations.extend([
                    "Set learning goals to maintain consistency",
                    "Explore new topics to reignite interest",
                    "Schedule dedicated learning time"
                ])

        elif insight.type == InsightType.MEMORY_CLUSTER:
            recommendations.extend([
                f"Deepen knowledge in '{insight.data.get('cluster_topic', 'this area')}'",
                "Connect this cluster with other knowledge areas",
                "Create summary memories for this topic"
            ])

        elif insight.type == InsightType.TAG_EVOLUTION:
            if "Emerging Topics" in insight.title:
                recommendations.extend([
                    "Continue exploring these new areas",
                    "Connect new topics with existing knowledge",
                    "Create foundational memories for new topics"
                ])

        # Default recommendations
        if not recommendations:
            recommendations = [
                "Continue current learning patterns",
                "Review insights regularly",
                "Adjust based on your goals"
            ]

        return recommendations[:3]

    def _empty_statistics(self, time_frame: TimeFrame) -> UsageStatistics:
        """Return empty statistics object"""
        return UsageStatistics(
            time_frame=time_frame,
            total_memories=0,
            total_accesses=0,
            unique_accessed=0,
            average_importance=0.0,
            most_accessed_memories=[],
            access_frequency={},
            peak_usage_times=[],
            growth_rate=0.0
        )

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
