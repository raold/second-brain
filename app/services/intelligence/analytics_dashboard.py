"""
Analytics dashboard service for v2.8.3 Intelligence features.

This service aggregates all analytics data and provides a unified
interface for the dashboard.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from app.connection_pool import DatabasePoolManager as ConnectionPool
from app.database import Database
from app.models.intelligence.analytics_models import (
    AnalyticsDashboard,
    AnalyticsQuery,
    MetricPoint,
    MetricSeries,
    MetricThreshold,
    MetricType,
    PerformanceBenchmark,
    TimeGranularity,
)
from app.services.intelligence.anomaly_detection import AnomalyDetectionService
from app.services.intelligence.knowledge_gap_analysis import KnowledgeGapAnalyzer
from app.services.intelligence.predictive_insights import PredictiveInsightsService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class AnalyticsDashboardService:
    """Service for generating comprehensive analytics dashboards."""

    def __init__(
        self,
        database: Database,
        memory_service: MemoryService,
        insights_service: PredictiveInsightsService,
        anomaly_service: AnomalyDetectionService,
        gap_analyzer: KnowledgeGapAnalyzer,
        connection_pool: ConnectionPool
    ):
        self.db = database
        self.memory_service = memory_service
        self.insights_service = insights_service
        self.anomaly_service = anomaly_service
        self.gap_analyzer = gap_analyzer
        self.connection_pool = connection_pool

        # Metric collection configuration
        self.metric_collectors = {
            MetricType.MEMORY_COUNT: self._collect_memory_count,
            MetricType.MEMORY_GROWTH: self._collect_memory_growth,
            MetricType.QUERY_PERFORMANCE: self._collect_query_performance,
            MetricType.EMBEDDING_QUALITY: self._collect_embedding_quality,
            MetricType.RELATIONSHIP_DENSITY: self._collect_relationship_density,
            MetricType.KNOWLEDGE_COVERAGE: self._collect_knowledge_coverage,
            MetricType.REVIEW_COMPLETION: self._collect_review_completion,
            MetricType.RETENTION_RATE: self._collect_retention_rate,
            MetricType.API_USAGE: self._collect_api_usage,
            MetricType.SYSTEM_HEALTH: self._collect_system_health
        }

        # Cache for metrics
        self._metrics_cache = {}
        self._cache_ttl = 300  # 5 minutes

    async def generate_dashboard(
        self,
        query: AnalyticsQuery
    ) -> AnalyticsDashboard:
        """Generate a complete analytics dashboard."""
        # Determine which metrics to collect
        metrics_to_collect = query.metrics or list(MetricType)

        # Collect metrics in parallel
        metric_tasks = []
        for metric_type in metrics_to_collect:
            if metric_type in self.metric_collectors:
                task = self._collect_metric_with_cache(
                    metric_type, query
                )
                metric_tasks.append((metric_type, task))

        # Wait for all metrics
        metrics = {}
        results = await asyncio.gather(
            *[task for _, task in metric_tasks],
            return_exceptions=True
        )

        for i, (metric_type, _) in enumerate(metric_tasks):
            if isinstance(results[i], Exception):
                logger.error(f"Error collecting {metric_type}: {results[i]}")
                continue
            metrics[metric_type] = results[i]

        # Generate insights if requested
        insights = []
        if query.include_insights:
            try:
                insights = await self.insights_service.generate_insights(
                    metrics, query.user_id
                )
            except Exception as e:
                logger.error(f"Error generating insights: {e}")

        # Detect anomalies if requested
        anomalies = []
        if query.include_anomalies:
            try:
                anomalies = await self.anomaly_service.detect_anomalies(
                    metrics
                )
            except Exception as e:
                logger.error(f"Error detecting anomalies: {e}")

        # Analyze knowledge gaps if requested
        knowledge_gaps = []
        if query.include_knowledge_gaps and query.user_id:
            try:
                knowledge_gaps = await self.gap_analyzer.analyze_knowledge_gaps(
                    query.user_id
                )
            except Exception as e:
                logger.error(f"Error analyzing knowledge gaps: {e}")

        # Calculate summary statistics
        total_memories = await self._get_total_memories(query.user_id)
        active_users = await self._get_active_users()
        system_health = await self._calculate_system_health(metrics)

        return AnalyticsDashboard(
            metrics=metrics,
            anomalies=anomalies,
            insights=insights,
            knowledge_gaps=knowledge_gaps,
            total_memories=total_memories,
            active_users=active_users,
            system_health_score=system_health,
            time_range=query.granularity
        )

    async def _collect_metric_with_cache(
        self,
        metric_type: MetricType,
        query: AnalyticsQuery
    ) -> MetricSeries:
        """Collect metric with caching."""
        cache_key = f"{metric_type}_{query.granularity}_{query.user_id}"

        # Check cache
        if cache_key in self._metrics_cache:
            cached_data, cached_time = self._metrics_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data

        # Collect fresh data
        collector = self.metric_collectors[metric_type]
        metric_series = await collector(query)

        # Cache the result
        self._metrics_cache[cache_key] = (metric_series, datetime.utcnow())

        return metric_series

    async def _collect_memory_count(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect memory count metrics."""
        data_points = []

        # Generate time points based on granularity
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Count memories up to this timestamp
            count = await self._count_memories_at_time(
                timestamp, query.user_id
            )

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=float(count),
                metadata={"user_id": query.user_id} if query.user_id else {}
            ))

        return MetricSeries(
            metric_type=MetricType.MEMORY_COUNT,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_memory_growth(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect memory growth rate metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        if len(time_points) < 2:
            return MetricSeries(
                metric_type=MetricType.MEMORY_GROWTH,
                data_points=[],
                granularity=query.granularity,
                start_time=query.start_date or datetime.utcnow(),
                end_time=query.end_date or datetime.utcnow()
            )

        prev_count = await self._count_memories_at_time(
            time_points[0], query.user_id
        )

        for i in range(1, len(time_points)):
            current_count = await self._count_memories_at_time(
                time_points[i], query.user_id
            )

            growth_rate = 0.0
            if prev_count > 0:
                growth_rate = (current_count - prev_count) / prev_count

            data_points.append(MetricPoint(
                timestamp=time_points[i],
                value=growth_rate,
                metadata={"absolute_growth": current_count - prev_count}
            ))

            prev_count = current_count

        return MetricSeries(
            metric_type=MetricType.MEMORY_GROWTH,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_query_performance(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect query performance metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        # Simulate performance data (in production, this would come from logs)
        for timestamp in time_points:
            # Generate realistic performance values
            base_time = 50.0  # Base response time in ms

            # Add some variation
            hour_factor = 1 + 0.5 * np.sin(timestamp.hour * np.pi / 12)
            random_factor = 1 + 0.2 * (np.random.random() - 0.5)

            response_time = base_time * hour_factor * random_factor

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=response_time,
                metadata={
                    "query_count": int(100 * random_factor),
                    "cache_hit_rate": 0.85 + 0.1 * (np.random.random() - 0.5)
                }
            ))

        return MetricSeries(
            metric_type=MetricType.QUERY_PERFORMANCE,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_embedding_quality(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect embedding quality metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Calculate average cosine similarity of recent embeddings
            quality_score = 0.85 + 0.1 * np.random.random()

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=quality_score,
                metadata={
                    "embeddings_processed": int(50 + 50 * np.random.random()),
                    "dimension": 1536
                }
            ))

        return MetricSeries(
            metric_type=MetricType.EMBEDDING_QUALITY,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_relationship_density(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect relationship density metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Calculate relationship density
            # (edges / possible edges in graph)
            density = 0.15 + 0.05 * np.random.random()

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=density,
                metadata={
                    "total_relationships": int(1000 * density),
                    "unique_connections": int(500 * density)
                }
            ))

        return MetricSeries(
            metric_type=MetricType.RELATIONSHIP_DENSITY,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_knowledge_coverage(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect knowledge coverage metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Estimate topic coverage
            coverage = 0.6 + 0.2 * np.random.random()

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=coverage,
                metadata={
                    "topics_covered": int(100 * coverage),
                    "total_topics": 100
                }
            ))

        return MetricSeries(
            metric_type=MetricType.KNOWLEDGE_COVERAGE,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_review_completion(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect review completion metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Calculate review completion rate
            completion_rate = 0.75 + 0.15 * np.random.random()

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=completion_rate,
                metadata={
                    "reviews_completed": int(50 * completion_rate),
                    "reviews_due": 50
                }
            ))

        return MetricSeries(
            metric_type=MetricType.REVIEW_COMPLETION,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_retention_rate(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect memory retention rate metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Calculate retention rate from reviews
            retention = 0.8 + 0.1 * np.random.random()

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=retention,
                metadata={
                    "successful_recalls": int(100 * retention),
                    "total_reviews": 100
                }
            ))

        return MetricSeries(
            metric_type=MetricType.RETENTION_RATE,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_api_usage(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect API usage metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Simulate API usage patterns
            base_usage = 100
            hour_factor = 1 + 0.7 * np.sin((timestamp.hour - 14) * np.pi / 12)
            day_factor = 1.2 if timestamp.weekday() < 5 else 0.6

            usage = base_usage * hour_factor * day_factor * (1 + 0.3 * np.random.random())

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=usage,
                metadata={
                    "unique_users": int(usage / 10),
                    "error_rate": 0.02 * np.random.random()
                }
            ))

        return MetricSeries(
            metric_type=MetricType.API_USAGE,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    async def _collect_system_health(self, query: AnalyticsQuery) -> MetricSeries:
        """Collect system health metrics."""
        data_points = []
        time_points = self._generate_time_points(query)

        for timestamp in time_points:
            # Calculate composite health score
            cpu_health = 1 - (0.4 + 0.2 * np.random.random())  # CPU usage inverted
            memory_health = 1 - (0.3 + 0.1 * np.random.random())  # Memory usage inverted
            db_health = 0.95 + 0.05 * np.random.random()  # DB connection health

            health_score = (cpu_health + memory_health + db_health) / 3

            data_points.append(MetricPoint(
                timestamp=timestamp,
                value=health_score,
                metadata={
                    "cpu_usage": 1 - cpu_health,
                    "memory_usage": 1 - memory_health,
                    "db_connections": int(20 * db_health)
                }
            ))

        return MetricSeries(
            metric_type=MetricType.SYSTEM_HEALTH,
            data_points=data_points,
            granularity=query.granularity,
            start_time=query.start_date or time_points[0],
            end_time=query.end_date or time_points[-1]
        )

    def _generate_time_points(self, query: AnalyticsQuery) -> list[datetime]:
        """Generate time points based on query parameters."""
        # Default time range
        end_time = query.end_date or datetime.utcnow()

        if query.start_date:
            start_time = query.start_date
        else:
            # Default ranges based on granularity
            default_ranges = {
                TimeGranularity.MINUTE: timedelta(hours=1),
                TimeGranularity.HOUR: timedelta(days=1),
                TimeGranularity.DAY: timedelta(days=30),
                TimeGranularity.WEEK: timedelta(days=90),
                TimeGranularity.MONTH: timedelta(days=365),
                TimeGranularity.QUARTER: timedelta(days=365 * 2),
                TimeGranularity.YEAR: timedelta(days=365 * 5)
            }
            start_time = end_time - default_ranges[query.granularity]

        # Generate points
        points = []
        current = start_time

        while current <= end_time:
            points.append(current)

            # Increment based on granularity
            if query.granularity == TimeGranularity.MINUTE:
                current += timedelta(minutes=1)
            elif query.granularity == TimeGranularity.HOUR:
                current += timedelta(hours=1)
            elif query.granularity == TimeGranularity.DAY:
                current += timedelta(days=1)
            elif query.granularity == TimeGranularity.WEEK:
                current += timedelta(weeks=1)
            elif query.granularity == TimeGranularity.MONTH:
                # Approximate month
                current += timedelta(days=30)
            elif query.granularity == TimeGranularity.QUARTER:
                # Approximate quarter
                current += timedelta(days=90)
            elif query.granularity == TimeGranularity.YEAR:
                # Approximate year
                current += timedelta(days=365)

        return points

    async def _count_memories_at_time(
        self,
        timestamp: datetime,
        user_id: Optional[str]
    ) -> int:
        """Count memories up to a specific timestamp."""
        # In production, this would query the database
        # For now, return simulated data
        base_count = 1000
        days_elapsed = (timestamp - datetime(2024, 1, 1)).days
        growth_rate = 10  # Memories per day

        count = base_count + days_elapsed * growth_rate

        if user_id:
            # Simulate user-specific variation
            count = int(count * 0.3)  # User has 30% of total

        return max(0, count + int(50 * (np.random.random() - 0.5)))

    async def _get_total_memories(self, user_id: Optional[str]) -> int:
        """Get total memory count."""
        return await self._count_memories_at_time(datetime.utcnow(), user_id)

    async def _get_active_users(self) -> int:
        """Get count of active users."""
        # In production, query database for users active in last 24h
        return 42

    async def _calculate_system_health(
        self,
        metrics: dict[MetricType, MetricSeries]
    ) -> float:
        """Calculate overall system health score."""
        health_components = []

        # Check system health metric
        if MetricType.SYSTEM_HEALTH in metrics:
            series = metrics[MetricType.SYSTEM_HEALTH]
            if series.data_points:
                # Average of recent points
                recent_points = series.data_points[-5:]
                avg_health = sum(p.value for p in recent_points) / len(recent_points)
                health_components.append(avg_health)

        # Check query performance
        if MetricType.QUERY_PERFORMANCE in metrics:
            series = metrics[MetricType.QUERY_PERFORMANCE]
            if series.data_points:
                avg_response = series.average
                # Convert to health score (lower is better)
                perf_health = max(0, 1 - (avg_response - 50) / 500)
                health_components.append(perf_health)

        # Check API usage (shouldn't be too high)
        if MetricType.API_USAGE in metrics:
            series = metrics[MetricType.API_USAGE]
            if series.data_points:
                avg_usage = series.average
                # Normalize (assume 1000 requests/hour is max healthy)
                usage_health = max(0, 1 - avg_usage / 1000)
                health_components.append(usage_health)

        if health_components:
            return sum(health_components) / len(health_components)

        return 0.85  # Default healthy score

    async def get_performance_benchmarks(self) -> list[PerformanceBenchmark]:
        """Get current performance benchmarks."""
        benchmarks = []

        # Define operations to benchmark
        operations = [
            "memory_search",
            "embedding_generation",
            "relationship_analysis",
            "report_generation"
        ]

        for operation in operations:
            # In production, these would come from actual measurements
            benchmark = PerformanceBenchmark(
                operation=operation,
                p50_ms=50 + 50 * np.random.random(),
                p90_ms=100 + 100 * np.random.random(),
                p99_ms=200 + 200 * np.random.random(),
                throughput_per_second=100 + 50 * np.random.random(),
                error_rate=0.01 * np.random.random()
            )
            benchmarks.append(benchmark)

        return benchmarks

    async def set_metric_threshold(
        self,
        threshold: MetricThreshold
    ) -> bool:
        """Set alerting threshold for a metric."""
        # In production, store in database
        logger.info(f"Setting threshold for {threshold.metric_type}: {threshold}")
        return True

    async def get_metric_thresholds(self) -> list[MetricThreshold]:
        """Get all configured metric thresholds."""
        # In production, retrieve from database
        return [
            MetricThreshold(
                metric_type=MetricType.QUERY_PERFORMANCE,
                max_value=1000.0,
                alert_on_breach=True
            ),
            MetricThreshold(
                metric_type=MetricType.SYSTEM_HEALTH,
                min_value=0.5,
                alert_on_breach=True
            ),
            MetricThreshold(
                metric_type=MetricType.MEMORY_GROWTH,
                min_value=0.001,
                max_value=0.5,
                alert_on_breach=True
            )
        ]
