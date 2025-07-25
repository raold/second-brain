"""
Predictive insights service for v2.8.3 Intelligence features.

This service analyzes patterns in user behavior, system performance,
and knowledge base growth to generate actionable insights.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Optional
from uuid import uuid4

import numpy as np

from app.database import Database
from app.models.intelligence.analytics_models import (
    InsightCategory,
    MetricSeries,
    MetricType,
    PredictiveInsight,
    TrendDirection,
)
from app.services.memory_service import MemoryService
from app.utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class PredictiveInsightsService:
    """Service for generating predictive insights from analytics data."""

    def __init__(
        self,
        database: Database,
        memory_service: MemoryService,
        openai_client: OpenAIClient
    ):
        self.db = database
        self.memory_service = memory_service
        self.openai = openai_client

        # Insight generation rules
        self.insight_rules = {
            InsightCategory.PERFORMANCE: self._analyze_performance_trends,
            InsightCategory.KNOWLEDGE: self._analyze_knowledge_patterns,
            InsightCategory.BEHAVIOR: self._analyze_user_behavior,
            InsightCategory.SYSTEM: self._analyze_system_health,
            InsightCategory.OPPORTUNITY: self._identify_opportunities,
            InsightCategory.WARNING: self._detect_warnings
        }

    async def generate_insights(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str] = None
    ) -> list[PredictiveInsight]:
        """Generate predictive insights from metrics data."""
        insights = []

        # Run all insight generators in parallel
        tasks = []
        for category, analyzer in self.insight_rules.items():
            task = analyzer(metrics, user_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error generating insights: {result}")
                continue
            if result:
                insights.extend(result)

        # Sort by impact score
        insights.sort(key=lambda x: x.impact_score, reverse=True)

        return insights

    async def _analyze_performance_trends(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Analyze performance-related trends."""
        insights = []

        # Check query performance
        if MetricType.QUERY_PERFORMANCE in metrics:
            perf_series = metrics[MetricType.QUERY_PERFORMANCE]
            avg_response = perf_series.average
            trend = perf_series.trend

            if trend == TrendDirection.INCREASING and avg_response > 100:
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.PERFORMANCE,
                    title="Query Performance Degradation",
                    description=f"Query response times have increased by {self._calculate_change(perf_series):.1f}% over the past {len(perf_series.data_points)} data points.",
                    confidence=0.85,
                    impact_score=0.8,
                    timeframe="next 48 hours",
                    recommendations=[
                        "Consider optimizing database indexes",
                        "Review and optimize complex queries",
                        "Check for resource constraints",
                        "Enable query caching if not already active"
                    ],
                    supporting_metrics=[MetricType.QUERY_PERFORMANCE],
                    metadata={"avg_response_ms": avg_response}
                ))

        # Check API usage patterns
        if MetricType.API_USAGE in metrics:
            usage_series = metrics[MetricType.API_USAGE]
            if self._detect_usage_spike(usage_series):
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.PERFORMANCE,
                    title="API Usage Spike Detected",
                    description="API usage is 3x higher than normal patterns. System may need scaling.",
                    confidence=0.9,
                    impact_score=0.7,
                    timeframe="within 24 hours",
                    recommendations=[
                        "Monitor system resources closely",
                        "Consider enabling auto-scaling",
                        "Review rate limiting configuration",
                        "Prepare for increased load"
                    ],
                    supporting_metrics=[MetricType.API_USAGE],
                    metadata={"spike_factor": 3.0}
                ))

        return insights

    async def _analyze_knowledge_patterns(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Analyze knowledge base patterns."""
        insights = []

        # Check memory growth
        if MetricType.MEMORY_GROWTH in metrics:
            growth_series = metrics[MetricType.MEMORY_GROWTH]
            growth_rate = self._calculate_growth_rate(growth_series)

            if growth_rate < 0.01:  # Less than 1% growth
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.KNOWLEDGE,
                    title="Knowledge Base Stagnation",
                    description="Memory creation has slowed significantly. Consider diversifying information sources.",
                    confidence=0.75,
                    impact_score=0.6,
                    timeframe="ongoing",
                    recommendations=[
                        "Explore new topic areas",
                        "Import content from external sources",
                        "Review and expand existing memories",
                        "Set daily memory creation goals"
                    ],
                    supporting_metrics=[MetricType.MEMORY_GROWTH],
                    metadata={"growth_rate": growth_rate}
                ))

        # Check knowledge coverage
        if MetricType.KNOWLEDGE_COVERAGE in metrics:
            coverage_series = metrics[MetricType.KNOWLEDGE_COVERAGE]
            coverage = coverage_series.average

            if coverage < 0.5:  # Less than 50% coverage
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.KNOWLEDGE,
                    title="Knowledge Coverage Gaps",
                    description="Significant gaps identified in knowledge coverage across topics.",
                    confidence=0.8,
                    impact_score=0.7,
                    timeframe="next 7 days",
                    recommendations=[
                        "Run knowledge gap analysis",
                        "Focus on underrepresented topics",
                        "Create topic-specific learning plans",
                        "Import relevant documentation"
                    ],
                    supporting_metrics=[MetricType.KNOWLEDGE_COVERAGE],
                    metadata={"coverage_percentage": coverage * 100}
                ))

        return insights

    async def _analyze_user_behavior(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Analyze user behavior patterns."""
        insights = []

        # Check review completion
        if MetricType.REVIEW_COMPLETION in metrics:
            review_series = metrics[MetricType.REVIEW_COMPLETION]
            completion_rate = review_series.average
            trend = review_series.trend

            if completion_rate < 0.6 and trend == TrendDirection.DECREASING:
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.BEHAVIOR,
                    title="Declining Review Engagement",
                    description="Review completion rates are falling. Risk of knowledge retention loss.",
                    confidence=0.85,
                    impact_score=0.75,
                    timeframe="next 3 days",
                    recommendations=[
                        "Adjust review scheduling algorithm",
                        "Implement review reminders",
                        "Gamify the review process",
                        "Reduce daily review burden"
                    ],
                    supporting_metrics=[MetricType.REVIEW_COMPLETION],
                    metadata={"completion_rate": completion_rate}
                ))

        # Check retention rates
        if MetricType.RETENTION_RATE in metrics:
            retention_series = metrics[MetricType.RETENTION_RATE]
            if retention_series.average < 0.7:
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.BEHAVIOR,
                    title="Low Knowledge Retention",
                    description="Memory retention rates are below optimal levels.",
                    confidence=0.8,
                    impact_score=0.8,
                    timeframe="ongoing",
                    recommendations=[
                        "Increase review frequency for difficult items",
                        "Enhance memory connections",
                        "Add more context to memories",
                        "Use multimedia content for better retention"
                    ],
                    supporting_metrics=[MetricType.RETENTION_RATE],
                    metadata={"avg_retention": retention_series.average}
                ))

        return insights

    async def _analyze_system_health(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Analyze system health indicators."""
        insights = []

        if MetricType.SYSTEM_HEALTH in metrics:
            health_series = metrics[MetricType.SYSTEM_HEALTH]
            health_score = health_series.average

            # Predict system issues
            if health_score < 0.8:
                severity = "critical" if health_score < 0.5 else "moderate"
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.SYSTEM,
                    title=f"System Health {severity.title()} Alert",
                    description=f"System health score is {health_score:.2f}. Preventive action recommended.",
                    confidence=0.9,
                    impact_score=0.9 if severity == "critical" else 0.7,
                    timeframe="immediate",
                    recommendations=[
                        "Check system logs for errors",
                        "Review resource utilization",
                        "Verify database connections",
                        "Run system diagnostics"
                    ],
                    supporting_metrics=[MetricType.SYSTEM_HEALTH],
                    metadata={"health_score": health_score, "severity": severity}
                ))

        # Check embedding quality
        if MetricType.EMBEDDING_QUALITY in metrics:
            quality_series = metrics[MetricType.EMBEDDING_QUALITY]
            if quality_series.trend == TrendDirection.DECREASING:
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.SYSTEM,
                    title="Embedding Quality Degradation",
                    description="Vector embedding quality is declining, affecting search accuracy.",
                    confidence=0.75,
                    impact_score=0.65,
                    timeframe="next 7 days",
                    recommendations=[
                        "Review embedding model configuration",
                        "Check for data quality issues",
                        "Consider model retraining",
                        "Validate input preprocessing"
                    ],
                    supporting_metrics=[MetricType.EMBEDDING_QUALITY],
                    metadata={"quality_trend": quality_series.trend.value}
                ))

        return insights

    async def _identify_opportunities(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Identify growth and optimization opportunities."""
        insights = []

        # Check relationship density
        if MetricType.RELATIONSHIP_DENSITY in metrics:
            density_series = metrics[MetricType.RELATIONSHIP_DENSITY]
            density = density_series.average

            if density < 0.3:  # Low interconnection
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.OPPORTUNITY,
                    title="Knowledge Graph Enhancement Opportunity",
                    description="Low relationship density suggests opportunity for better knowledge connections.",
                    confidence=0.8,
                    impact_score=0.6,
                    timeframe="next 14 days",
                    recommendations=[
                        "Run automatic relationship discovery",
                        "Enable cross-memory linking",
                        "Create topic clusters",
                        "Implement entity extraction"
                    ],
                    supporting_metrics=[MetricType.RELATIONSHIP_DENSITY],
                    metadata={"current_density": density}
                ))

        # Identify peak usage times
        if MetricType.API_USAGE in metrics:
            usage_patterns = self._analyze_usage_patterns(metrics[MetricType.API_USAGE])
            if usage_patterns:
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.OPPORTUNITY,
                    title="Optimal Processing Window Identified",
                    description=f"Low activity period identified: {usage_patterns['quiet_period']}. Ideal for batch processing.",
                    confidence=0.85,
                    impact_score=0.5,
                    timeframe="recurring daily",
                    recommendations=[
                        "Schedule heavy processing during quiet periods",
                        "Run maintenance tasks off-peak",
                        "Perform batch imports during low usage",
                        "Schedule model retraining"
                    ],
                    supporting_metrics=[MetricType.API_USAGE],
                    metadata=usage_patterns
                ))

        return insights

    async def _detect_warnings(
        self,
        metrics: dict[MetricType, MetricSeries],
        user_id: Optional[str]
    ) -> list[PredictiveInsight]:
        """Detect potential issues requiring attention."""
        insights = []

        # Check for volatile patterns
        volatile_metrics = [
            (metric_type, series)
            for metric_type, series in metrics.items()
            if series.trend == TrendDirection.VOLATILE
        ]

        if volatile_metrics:
            insights.append(PredictiveInsight(
                id=uuid4(),
                category=InsightCategory.WARNING,
                title="System Instability Detected",
                description=f"Multiple metrics showing volatile patterns: {', '.join(m[0].value for m in volatile_metrics[:3])}",
                confidence=0.7,
                impact_score=0.8,
                timeframe="ongoing",
                recommendations=[
                    "Investigate root cause of instability",
                    "Enable detailed logging",
                    "Monitor system closely",
                    "Prepare rollback plan"
                ],
                supporting_metrics=[m[0] for m in volatile_metrics],
                metadata={"volatile_count": len(volatile_metrics)}
            ))

        # Check for threshold breaches
        for metric_type, series in metrics.items():
            if self._check_threshold_breach(metric_type, series):
                insights.append(PredictiveInsight(
                    id=uuid4(),
                    category=InsightCategory.WARNING,
                    title=f"{metric_type.value.replace('_', ' ').title()} Threshold Breach",
                    description="Metric has exceeded normal operating range.",
                    confidence=0.9,
                    impact_score=0.7,
                    timeframe="immediate",
                    recommendations=[
                        f"Review {metric_type.value} configuration",
                        "Check for abnormal activity",
                        "Implement corrective measures",
                        "Set up automated alerts"
                    ],
                    supporting_metrics=[metric_type],
                    metadata={"breach_value": series.data_points[-1].value if series.data_points else 0}
                ))

        return insights

    def _calculate_change(self, series: MetricSeries) -> float:
        """Calculate percentage change in metric."""
        if len(series.data_points) < 2:
            return 0.0

        first_value = series.data_points[0].value
        last_value = series.data_points[-1].value

        if first_value == 0:
            return 100.0 if last_value > 0 else 0.0

        return ((last_value - first_value) / first_value) * 100

    def _calculate_growth_rate(self, series: MetricSeries) -> float:
        """Calculate compound growth rate."""
        if len(series.data_points) < 2:
            return 0.0

        first_value = series.data_points[0].value
        last_value = series.data_points[-1].value
        periods = len(series.data_points) - 1

        if first_value <= 0 or periods == 0:
            return 0.0

        return ((last_value / first_value) ** (1 / periods)) - 1

    def _detect_usage_spike(self, series: MetricSeries) -> bool:
        """Detect if there's a usage spike."""
        if len(series.data_points) < 10:
            return False

        recent_values = [p.value for p in series.data_points[-5:]]
        historical_values = [p.value for p in series.data_points[:-5]]

        recent_avg = np.mean(recent_values)
        historical_avg = np.mean(historical_values)

        return recent_avg > historical_avg * 3

    def _analyze_usage_patterns(self, series: MetricSeries) -> Optional[dict[str, Any]]:
        """Analyze usage patterns to find quiet periods."""
        if len(series.data_points) < 24:  # Need at least 24 hours of data
            return None

        # Group by hour
        hourly_usage = defaultdict(list)
        for point in series.data_points:
            hour = point.timestamp.hour
            hourly_usage[hour].append(point.value)

        # Calculate average usage per hour
        hourly_avg = {
            hour: np.mean(values)
            for hour, values in hourly_usage.items()
        }

        if not hourly_avg:
            return None

        # Find quietest period
        min_hour = min(hourly_avg, key=hourly_avg.get)
        max_hour = max(hourly_avg, key=hourly_avg.get)

        return {
            "quiet_period": f"{min_hour:02d}:00 - {(min_hour + 1) % 24:02d}:00",
            "peak_period": f"{max_hour:02d}:00 - {(max_hour + 1) % 24:02d}:00",
            "quiet_usage": hourly_avg[min_hour],
            "peak_usage": hourly_avg[max_hour]
        }

    def _check_threshold_breach(self, metric_type: MetricType, series: MetricSeries) -> bool:
        """Check if metric breaches predefined thresholds."""
        if not series.data_points:
            return False

        # Define thresholds for each metric type
        thresholds = {
            MetricType.QUERY_PERFORMANCE: (0, 1000),  # Max 1 second
            MetricType.ERROR_RATE: (0, 0.05),  # Max 5% error rate
            MetricType.MEMORY_GROWTH: (0.001, 0.5),  # Min 0.1%, Max 50% growth
            MetricType.SYSTEM_HEALTH: (0.5, 1.0),  # Min 50% health
        }

        if metric_type not in thresholds:
            return False

        min_val, max_val = thresholds[metric_type]
        current_value = series.data_points[-1].value

        return current_value < min_val or current_value > max_val
