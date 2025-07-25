"""
Unit tests for v2.8.3 Intelligence analytics features.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest

from app.models.intelligence.analytics_models import (
    AnalyticsDashboard,
    AnalyticsQuery,
    Anomaly,
    AnomalyType,
    InsightCategory,
    MetricPoint,
    MetricSeries,
    MetricType,
    PredictiveInsight,
    TimeGranularity,
    TrendDirection,
)
from app.services.intelligence.analytics_dashboard import AnalyticsDashboardService
from app.services.intelligence.anomaly_detection import (
    AnomalyDetectionService,
    MovingAverageDetector,
    PatternBreakDetector,
    StatisticalAnomalyDetector,
)
from app.services.intelligence.knowledge_gap_analysis import KnowledgeGapAnalyzer
from app.services.intelligence.predictive_insights import PredictiveInsightsService


class TestAnalyticsModels:
    """Test analytics data models."""

    @pytest.mark.parametrize("value,should_raise", [
        (42.5, False),
        (0.0, False),
        (100.0, False),
        (-1.0, True),
        (-0.1, True),
        (float('inf'), True),
        (float('nan'), True),
    ])
    def test_metric_point_validation(self, value, should_raise):
        """Test MetricPoint validation with various values."""
        timestamp = datetime.utcnow()
        metadata = {"source": "test"}

        if should_raise:
            with pytest.raises(ValueError):
                MetricPoint(timestamp=timestamp, value=value, metadata=metadata)
        else:
            point = MetricPoint(timestamp=timestamp, value=value, metadata=metadata)
            assert point.value == value

    def test_metric_series_calculations(self):
        """Test MetricSeries calculations."""
        points = [
            MetricPoint(timestamp=datetime.utcnow() + timedelta(hours=i), value=i * 10)
            for i in range(5)
        ]

        series = MetricSeries(
            metric_type=MetricType.QUERY_PERFORMANCE,
            data_points=points,
            granularity=TimeGranularity.HOUR,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        # Test average calculation
        assert series.average == 20.0  # (0 + 10 + 20 + 30 + 40) / 5

        # Test trend detection
        assert series.trend == TrendDirection.INCREASING

    def test_analytics_dashboard_filtering(self):
        """Test AnalyticsDashboard filtering methods."""
        # Create test data
        insights = [
            PredictiveInsight(
                id=uuid4(),
                category=InsightCategory.PERFORMANCE,
                title="Test Insight",
                description="Test",
                confidence=0.8,
                impact_score=0.9,
                timeframe="24 hours",
                recommendations=["Do something"],
                supporting_metrics=[MetricType.QUERY_PERFORMANCE]
            ),
            PredictiveInsight(
                id=uuid4(),
                category=InsightCategory.WARNING,
                title="Low Impact",
                description="Test",
                confidence=0.6,
                impact_score=0.3,
                timeframe="7 days",
                recommendations=["Check this"],
                supporting_metrics=[MetricType.SYSTEM_HEALTH]
            )
        ]

        anomalies = [
            Anomaly(
                id=uuid4(),
                metric_type=MetricType.API_USAGE,
                anomaly_type=AnomalyType.SPIKE,
                timestamp=datetime.utcnow() - timedelta(hours=1),
                severity=0.8,
                expected_value=100,
                actual_value=500,
                confidence=0.9,
                description="Usage spike"
            )
        ]

        dashboard = AnalyticsDashboard(
            metrics={},
            anomalies=anomalies,
            insights=insights,
            knowledge_gaps=[],
            total_memories=1000,
            active_users=10,
            system_health_score=0.85,
            time_range=TimeGranularity.DAY
        )

        # Test critical insights filtering
        critical = dashboard.get_critical_insights()
        assert len(critical) == 1
        assert critical[0].impact_score == 0.9

        # Test recent anomalies filtering
        recent = dashboard.get_recent_anomalies(hours=2)
        assert len(recent) == 1


class TestAnomalyDetection:
    """Test anomaly detection algorithms."""

    @pytest.mark.parametrize("z_threshold,expected_outliers", [
        (1.0, [50]),  # Strict threshold
        (2.0, [50]),  # Normal threshold
        (3.0, []),    # Lenient threshold
        (0.5, [50, 12, 10]),  # Very strict
    ])
    def test_statistical_anomaly_detector(self, z_threshold, expected_outliers):
        """Test statistical anomaly detection with different thresholds."""
        detector = StatisticalAnomalyDetector(z_threshold=z_threshold)

        # Create test data with outliers
        values = [10, 12, 11, 10, 11, 12, 10, 50, 11, 10]  # 50 is clear outlier
        points = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(hours=i),
                value=v
            )
            for i, v in enumerate(values)
        ]

        series = MetricSeries(
            metric_type=MetricType.API_USAGE,
            data_points=points,
            granularity=TimeGranularity.HOUR,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        anomalies = detector.detect(series)
        detected_values = [a.actual_value for a in anomalies]

        for expected in expected_outliers:
            assert expected in detected_values, f"Expected outlier {expected} not detected with threshold {z_threshold}"

    def test_moving_average_detector(self):
        """Test moving average anomaly detection."""
        detector = MovingAverageDetector(window_size=3, deviation_multiplier=2.0)

        # Create test data
        values = [10, 11, 10, 11, 10, 30, 10, 11]  # 30 is anomalous
        points = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(hours=i),
                value=v
            )
            for i, v in enumerate(values)
        ]

        series = MetricSeries(
            metric_type=MetricType.QUERY_PERFORMANCE,
            data_points=points,
            granularity=TimeGranularity.HOUR,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        anomalies = detector.detect(series)

        # Should detect anomaly around value 30
        assert len(anomalies) > 0
        assert any(a.actual_value == 30 for a in anomalies)

    def test_pattern_break_detector(self):
        """Test pattern break detection."""
        detector = PatternBreakDetector()

        # Create daily pattern data with a break
        points = []
        for day in range(7):
            for hour in range(24):
                # Normal pattern: high during day, low at night
                if 9 <= hour <= 17:
                    value = 100 + np.random.normal(0, 5)
                else:
                    value = 20 + np.random.normal(0, 5)

                # Inject pattern break on day 5, hour 14
                if day == 5 and hour == 14:
                    value = 10  # Abnormally low during peak hours

                timestamp = datetime.utcnow() + timedelta(days=day, hours=hour)
                points.append(MetricPoint(timestamp=timestamp, value=value))

        series = MetricSeries(
            metric_type=MetricType.API_USAGE,
            data_points=points,
            granularity=TimeGranularity.HOUR,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        anomalies = detector.detect(series)

        # Should detect pattern breaks
        pattern_breaks = [a for a in anomalies if a.anomaly_type == AnomalyType.PATTERN_BREAK]
        assert len(pattern_breaks) > 0

    @pytest.mark.asyncio
    async def test_anomaly_detection_service(self, mock_database):
        """Test complete anomaly detection service."""
        service = AnomalyDetectionService(mock_database)

        # Create test metrics
        metrics = {
            MetricType.API_USAGE: MetricSeries(
                metric_type=MetricType.API_USAGE,
                data_points=[
                    MetricPoint(
                        timestamp=datetime.utcnow() + timedelta(hours=i),
                        value=100 if i != 5 else 500  # Spike at hour 5
                    )
                    for i in range(10)
                ],
                granularity=TimeGranularity.HOUR,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=10)
            )
        }

        anomalies = await service.detect_anomalies(metrics)

        # Should detect anomalies from multiple detectors
        assert len(anomalies) > 0
        # Should be sorted by severity
        if len(anomalies) > 1:
            assert anomalies[0].severity >= anomalies[1].severity


class TestPredictiveInsights:
    """Test predictive insights generation."""

    @pytest.mark.asyncio
    async def test_performance_insights(self, mock_services):
        """Test performance-related insights."""
        service = PredictiveInsightsService(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['openai_client']
        )

        # Create degrading performance metrics
        metrics = {
            MetricType.QUERY_PERFORMANCE: MetricSeries(
                metric_type=MetricType.QUERY_PERFORMANCE,
                data_points=[
                    MetricPoint(
                        timestamp=datetime.utcnow() + timedelta(hours=i),
                        value=50 + i * 20  # Increasing response time
                    )
                    for i in range(10)
                ],
                granularity=TimeGranularity.HOUR,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=10)
            )
        }

        insights = await service.generate_insights(metrics)

        # Should generate performance degradation insight
        perf_insights = [i for i in insights if i.category == InsightCategory.PERFORMANCE]
        assert len(perf_insights) > 0
        assert any("degradation" in i.title.lower() for i in perf_insights)

    @pytest.mark.asyncio
    async def test_knowledge_insights(self, mock_services):
        """Test knowledge-related insights."""
        service = PredictiveInsightsService(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['openai_client']
        )

        # Create stagnant growth metrics
        metrics = {
            MetricType.MEMORY_GROWTH: MetricSeries(
                metric_type=MetricType.MEMORY_GROWTH,
                data_points=[
                    MetricPoint(
                        timestamp=datetime.utcnow() + timedelta(days=i),
                        value=0.001  # Very low growth
                    )
                    for i in range(10)
                ],
                granularity=TimeGranularity.DAY,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(days=10)
            )
        }

        insights = await service.generate_insights(metrics)

        # Should identify stagnation
        knowledge_insights = [i for i in insights if i.category == InsightCategory.KNOWLEDGE]
        assert any("stagnation" in i.title.lower() for i in knowledge_insights)


class TestKnowledgeGapAnalysis:
    """Test knowledge gap analysis."""

    @pytest.mark.asyncio
    async def test_topic_coverage_analysis(self, mock_services, sample_memories):
        """Test topic coverage gap analysis."""
        analyzer = KnowledgeGapAnalyzer(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['relationship_analyzer'],
            mock_services['openai_client']
        )

        # Mock memory retrieval
        async def mock_get_memories(user_id):
            return sample_memories

        analyzer._get_user_memories = mock_get_memories

        gaps = await analyzer.analyze_knowledge_gaps("test_user", limit=10)

        # Should identify some gaps
        assert isinstance(gaps, list)
        if gaps:
            gap = gaps[0]
            assert hasattr(gap, 'topic')
            assert hasattr(gap, 'gap_score')
            assert hasattr(gap, 'suggested_queries')

    @pytest.mark.asyncio
    async def test_focus_area_coverage(self, mock_services, sample_memories):
        """Test focus area gap detection."""
        analyzer = KnowledgeGapAnalyzer(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['relationship_analyzer'],
            mock_services['openai_client']
        )

        # Mock memory retrieval
        async def mock_get_memories(user_id):
            return sample_memories

        analyzer._get_user_memories = mock_get_memories

        # Analyze with focus areas that don't exist in memories
        gaps = await analyzer.analyze_knowledge_gaps(
            "test_user",
            limit=10,
            focus_areas=["quantum computing", "blockchain"]
        )

        # Should identify gaps in focus areas
        focus_gaps = [g for g in gaps if "focus area" in g.topic.lower()]
        assert len(focus_gaps) > 0


class TestAnalyticsDashboard:
    """Test analytics dashboard service."""

    @pytest.mark.asyncio
    async def test_dashboard_generation(self, mock_services):
        """Test complete dashboard generation."""
        # Create all required services
        insights_service = PredictiveInsightsService(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['openai_client']
        )

        anomaly_service = AnomalyDetectionService(mock_services['database'])

        gap_analyzer = KnowledgeGapAnalyzer(
            mock_services['database'],
            mock_services['memory_service'],
            mock_services['relationship_analyzer'],
            mock_services['openai_client']
        )

        dashboard_service = AnalyticsDashboardService(
            mock_services['database'],
            mock_services['memory_service'],
            insights_service,
            anomaly_service,
            gap_analyzer,
            mock_services['connection_pool']
        )

        # Generate dashboard
        query = AnalyticsQuery(
            metrics=[MetricType.API_USAGE, MetricType.QUERY_PERFORMANCE],
            granularity=TimeGranularity.HOUR,
            include_insights=True,
            include_anomalies=True,
            include_knowledge_gaps=False,
            user_id="test_user"
        )

        dashboard = await dashboard_service.generate_dashboard(query)

        # Verify dashboard structure
        assert isinstance(dashboard, AnalyticsDashboard)
        assert len(dashboard.metrics) > 0
        assert dashboard.total_memories >= 0
        assert 0 <= dashboard.system_health_score <= 1
        assert dashboard.generated_at is not None

    @pytest.mark.asyncio
    async def test_metric_collection(self, mock_services):
        """Test individual metric collection."""
        dashboard_service = AnalyticsDashboardService(
            mock_services['database'],
            mock_services['memory_service'],
            None, None, None,
            mock_services['connection_pool']
        )

        query = AnalyticsQuery(
            granularity=TimeGranularity.HOUR,
            user_id="test_user"
        )

        # Test API usage collection
        api_usage = await dashboard_service._collect_api_usage(query)
        assert api_usage.metric_type == MetricType.API_USAGE
        assert len(api_usage.data_points) > 0
        assert all(p.value >= 0 for p in api_usage.data_points)

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, mock_services):
        """Test performance benchmark generation."""
        dashboard_service = AnalyticsDashboardService(
            mock_services['database'],
            mock_services['memory_service'],
            None, None, None,
            mock_services['connection_pool']
        )

        benchmarks = await dashboard_service.get_performance_benchmarks()

        assert len(benchmarks) > 0
        for benchmark in benchmarks:
            assert benchmark.p50_ms <= benchmark.p90_ms <= benchmark.p99_ms
            assert benchmark.throughput_per_second > 0
            assert 0 <= benchmark.error_rate <= 1
