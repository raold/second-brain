"""
Comprehensive tests for bulk monitoring analytics system.

Tests analytics, monitoring, and business intelligence functionality
for bulk memory operations with metrics collection and reporting.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.bulk_memory_operations import (
    BulkOperationProgress,
    BulkOperationResult,
    BulkOperationStatus,
    BulkOperationType,
)
from app.bulk_monitoring_analytics import (
    AlertManager,
    AlertSeverity,
    AnalyticsEngine,
    AnalyticsTimeframe,
    BulkMonitoringDashboard,
    CostAnalysis,
    MetricPoint,
    MetricsCollector,
    MetricType,
    OperationInsight,
    OperationTracker,
    get_monitoring_dashboard,
)


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_init_default_settings(self):
        """Test metrics collector initialization with defaults."""
        collector = MetricsCollector()

        assert collector.retention_days == 30
        assert len(collector.metrics_buffer) == 0
        assert collector.aggregated_metrics == defaultdict(list)
        assert collector.collection_stats["total_points"] == 0

    def test_init_custom_settings(self):
        """Test metrics collector initialization with custom settings."""
        collector = MetricsCollector(retention_days=60)

        assert collector.retention_days == 60
        assert collector.metrics_buffer.maxlen == 10000

    @pytest.mark.asyncio
    async def test_record_metric_basic(self):
        """Test basic metric recording functionality."""
        collector = MetricsCollector()

        await collector.record_metric(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            tags={"operation": "insert"},
            operation_id="test-op-123"
        )

        assert len(collector.metrics_buffer) == 1
        metric = collector.metrics_buffer[0]

        assert metric.metric_name == "test_metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.tags["operation"] == "insert"
        assert metric.operation_id == "test-op-123"
        assert isinstance(metric.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_record_metric_no_tags(self):
        """Test metric recording without tags."""
        collector = MetricsCollector()

        await collector.record_metric(
            name="simple_metric",
            value=100.0
        )

        assert len(collector.metrics_buffer) == 1
        metric = collector.metrics_buffer[0]

        assert metric.metric_name == "simple_metric"
        assert metric.value == 100.0
        assert metric.metric_type == MetricType.GAUGE  # Default
        assert metric.tags == {}
        assert metric.operation_id is None

    @pytest.mark.asyncio
    async def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        collector = MetricsCollector()

        metrics_data = [
            ("cpu_usage", 75.5, MetricType.GAUGE),
            ("operations_count", 1, MetricType.COUNTER),
            ("response_time", 125.3, MetricType.TIMER),
        ]

        for name, value, metric_type in metrics_data:
            await collector.record_metric(name, value, metric_type)

        assert len(collector.metrics_buffer) == 3

        # Verify each metric
        for i, (name, value, metric_type) in enumerate(metrics_data):
            metric = collector.metrics_buffer[i]
            assert metric.metric_name == name
            assert metric.value == value
            assert metric.metric_type == metric_type

    @pytest.mark.asyncio
    async def test_get_metrics_timerange(self):
        """Test retrieving metrics for a time range."""
        collector = MetricsCollector()

        # Add some test metrics with timestamps
        base_time = datetime.now()
        for i in range(5):
            metric = MetricPoint(
                timestamp=base_time - timedelta(hours=i),
                metric_name="test_metric",
                metric_type=MetricType.GAUGE,
                value=float(i * 10),
                tags={}
            )
            collector.metrics_buffer.append(metric)

        # Force aggregation
        await collector._aggregate_metrics()

        # Test retrieval
        start_time = base_time - timedelta(hours=3)
        end_time = base_time

        metrics = await collector.get_metrics("test_metric", start_time, end_time)

        assert len(metrics) > 0
        # Should have aggregated data
        for metric in metrics:
            assert "timestamp" in metric
            assert "value" in metric

    @pytest.mark.asyncio
    async def test_get_latest_metrics(self):
        """Test retrieving latest metric values."""
        collector = MetricsCollector()

        # Add some metrics
        await collector.record_metric("cpu_usage", 75.0)
        await collector.record_metric("memory_usage", 512.0)
        await collector.record_metric("cpu_usage", 80.0)  # Update CPU

        latest = await collector.get_latest_metrics(["cpu_usage", "memory_usage", "disk_usage"])

        assert latest["cpu_usage"] == 80.0  # Latest value
        assert latest["memory_usage"] == 512.0
        assert latest["disk_usage"] is None  # Not recorded


class TestOperationTracker:
    """Test the OperationTracker class."""

    def test_init_default_settings(self):
        """Test operation tracker initialization."""
        tracker = OperationTracker()

        assert len(tracker.active_operations) == 0
        assert len(tracker.completed_operations) == 0
        assert tracker.operation_history == defaultdict(list)
        assert tracker.tracking_stats["total_operations"] == 0

    @pytest.mark.asyncio
    async def test_start_tracking_operation(self):
        """Test starting operation tracking."""
        tracker = OperationTracker()

        # Create mock operation progress
        progress = BulkOperationProgress(
            operation_id="test-op-123",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.RUNNING,
            total_items=1000,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )

        await tracker.start_tracking(progress)

        assert len(tracker.active_operations) == 1
        assert tracker.active_operations["test-op-123"] == progress
        assert tracker.tracking_stats["total_operations"] == 1
        assert tracker.tracking_stats["active_count"] == 1

    @pytest.mark.asyncio
    async def test_update_operation_progress(self):
        """Test updating operation progress."""
        tracker = OperationTracker()

        # Start tracking
        progress = BulkOperationProgress(
            operation_id="test-op-123",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.RUNNING,
            total_items=1000,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )

        await tracker.start_tracking(progress)

        # Update progress
        await tracker.update_progress("test-op-123", {
            "processed_items": 500,
            "failed_items": 10
        })

        updated = tracker.active_operations["test-op-123"]
        assert updated.processed_items == 500
        assert updated.failed_items == 10
        assert updated.last_update is not None

    @pytest.mark.asyncio
    async def test_complete_operation(self):
        """Test completing operation tracking."""
        tracker = OperationTracker()

        # Start tracking
        progress = BulkOperationProgress(
            operation_id="test-op-123",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.RUNNING,
            total_items=1000,
            processed_items=1000,
            successful_items=950,
            failed_items=50,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )

        await tracker.start_tracking(progress)

        # Complete the operation
        result = BulkOperationResult(
            operation_id="test-op-123",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.COMPLETED,
            total_items=1000,
            successful_items=950,
            failed_items=50,
            skipped_items=0,
            execution_time=120.0,
            memory_ids=["mem-1", "mem-2"],
            error_summary={},
            performance_metrics={}
        )

        await tracker.complete_operation("test-op-123", result)

        assert len(tracker.active_operations) == 0
        assert len(tracker.completed_operations) == 1
        assert tracker.tracking_stats["active_count"] == 0
        assert len(tracker.operation_history[BulkOperationType.INSERT]) == 1

    @pytest.mark.asyncio
    async def test_get_operation_statistics(self):
        """Test getting operation statistics."""
        tracker = OperationTracker()

        # Add some completed operations
        for i in range(5):
            operation_id = f"op-{i}"

            progress = BulkOperationProgress(
                operation_id=operation_id,
                operation_type=BulkOperationType.INSERT,
                status=BulkOperationStatus.RUNNING,
                total_items=100,
                processed_items=100,
                successful_items=95,
                failed_items=5,
                skipped_items=0,
                start_time=datetime.now() - timedelta(seconds=30),
                last_update=datetime.now()
            )

            await tracker.start_tracking(progress)

            result = BulkOperationResult(
                operation_id=operation_id,
                operation_type=BulkOperationType.INSERT,
                status=BulkOperationStatus.COMPLETED,
                total_items=100,
                successful_items=95,
                failed_items=5,
                skipped_items=0,
                execution_time=30.0,
                memory_ids=[f"mem-{i}"],
                error_summary={},
                performance_metrics={}
            )

            await tracker.complete_operation(operation_id, result)

        stats = await tracker.get_operation_statistics()

        assert stats["tracking_stats"]["total_operations"] == 5
        assert stats["completed_operations"] == 5
        assert BulkOperationType.INSERT.value in stats["completion_rates"]
        assert BulkOperationType.INSERT.value in stats["average_execution_times"]


class TestAlertManager:
    """Test the AlertManager class."""

    def test_init_default_settings(self):
        """Test alert manager initialization."""
        manager = AlertManager()

        assert len(manager.alerts) == 0
        assert len(manager.alert_history) == 0
        assert manager.notification_channels == []
        assert manager.alert_rules == {}

    @pytest.mark.asyncio
    async def test_define_alert(self):
        """Test defining alert rules."""
        manager = AlertManager()

        alert_id = await manager.define_alert(
            name="High CPU Usage",
            description="CPU usage exceeded 90%",
            condition="cpu_usage > threshold",
            threshold=90.0,
            severity=AlertSeverity.WARNING
        )

        assert alert_id is not None
        assert len(manager.alerts) == 1
        assert manager.alerts[alert_id].name == "High CPU Usage"
        assert manager.alerts[alert_id].severity == AlertSeverity.WARNING
        assert manager.alerts[alert_id].threshold == 90.0

    @pytest.mark.asyncio
    async def test_check_alerts_trigger(self):
        """Test alert triggering."""
        manager = AlertManager()

        # Define an alert
        await manager.define_alert(
            name="High Memory Usage",
            description="Memory usage too high",
            condition="memory_usage > threshold",
            threshold=80.0,
            severity=AlertSeverity.ERROR
        )

        # Check with high memory
        metrics = {"memory_usage": 90.0, "cpu_usage": 50.0}
        operation_data = {"failed_operations": 0}

        await manager.check_alerts(metrics, operation_data)

        active_alerts = await manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].is_active
        assert active_alerts[0].triggered_at is not None

    @pytest.mark.asyncio
    async def test_check_alerts_resolve(self):
        """Test alert resolution."""
        manager = AlertManager()

        # Define and trigger an alert
        await manager.define_alert(
            name="High CPU Usage",
            description="CPU too high",
            condition="cpu_usage > threshold",
            threshold=85.0,
            severity=AlertSeverity.WARNING
        )

        # Trigger alert
        await manager.check_alerts({"cpu_usage": 90.0}, {})

        # Resolve alert
        await manager.check_alerts({"cpu_usage": 70.0}, {})

        active_alerts = await manager.get_active_alerts()
        assert len(active_alerts) == 0  # Should be resolved

    @pytest.mark.asyncio
    async def test_get_alert_statistics(self):
        """Test getting alert statistics."""
        manager = AlertManager()

        # Add some alerts
        for i in range(3):
            await manager.define_alert(
                name=f"Test Alert {i}",
                description=f"Test alert {i}",
                condition="test > threshold",
                threshold=10.0,
                severity=AlertSeverity.INFO
            )

        stats = await manager.get_alert_statistics()

        assert stats["total_alerts"] == 3
        assert stats["active_alerts"] >= 0
        assert AlertSeverity.INFO.value in stats["alerts_by_severity"]


class TestAnalyticsEngine:
    """Test the AnalyticsEngine class."""

    def test_init_with_dependencies(self):
        """Test analytics engine initialization."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)

        assert engine.metrics_collector == collector
        assert engine.operation_tracker == tracker
        assert engine.insights_cache == {}

    @pytest.mark.asyncio
    async def test_analyze_performance_trends(self):
        """Test performance trend analysis."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)

        # Add some metric data with trends
        base_time = datetime.now()
        for i in range(10):
            metric = MetricPoint(
                timestamp=base_time - timedelta(hours=i),
                metric_name="items_per_second",
                metric_type=MetricType.GAUGE,
                value=100.0 + i * 5.0,  # Increasing trend
                tags={}
            )
            collector.metrics_buffer.append(metric)

        trends = await engine.analyze_performance_trends(AnalyticsTimeframe.DAY)

        assert isinstance(trends, list)
        # Should have trends for metrics that have data
        trend_names = [t.metric_name for t in trends]
        assert "items_per_second" in trend_names

    @pytest.mark.asyncio
    async def test_generate_operation_insights(self):
        """Test generating operation insights."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)

        # Add operation history with low success rate
        for i in range(5):
            operation_id = f"op-{i}"

            # Simulate some failed operations
            status = BulkOperationStatus.COMPLETED if i < 2 else BulkOperationStatus.FAILED

            tracker.operation_history[BulkOperationType.INSERT].append({
                "operation_id": operation_id,
                "status": status,
                "total_items": 100,
                "execution_time": 60.0,
                "completed_at": datetime.now()
            })

        insights = await engine.generate_operation_insights()

        assert isinstance(insights, list)
        # Should detect low success rate
        if insights:
            assert isinstance(insights[0], OperationInsight)
            assert insights[0].operation_type == BulkOperationType.INSERT

    @pytest.mark.asyncio
    async def test_analyze_cost_efficiency(self):
        """Test cost efficiency analysis."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)

        # Add operation history
        tracker.operation_history[BulkOperationType.INSERT] = [
            {
                "operation_id": "op-1",
                "status": BulkOperationStatus.COMPLETED,
                "total_items": 1000,
                "execution_time": 120.0,
                "completed_at": datetime.now()
            },
            {
                "operation_id": "op-2",
                "status": BulkOperationStatus.COMPLETED,
                "total_items": 500,
                "execution_time": 60.0,
                "completed_at": datetime.now()
            }
        ]

        cost_analysis = await engine.analyze_cost_efficiency()

        assert isinstance(cost_analysis, dict)
        assert BulkOperationType.INSERT in cost_analysis

        analysis = cost_analysis[BulkOperationType.INSERT]
        assert isinstance(analysis, CostAnalysis)
        assert analysis.total_operations == 2
        assert analysis.total_items_processed == 1500

    @pytest.mark.asyncio
    async def test_predict_operation_performance(self):
        """Test operation performance prediction."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)

        # Add historical data
        tracker.operation_history[BulkOperationType.INSERT] = [
            {
                "operation_id": "op-1",
                "total_items": 1000,
                "execution_time": 60.0,
                "status": BulkOperationStatus.COMPLETED
            },
            {
                "operation_id": "op-2",
                "total_items": 500,
                "execution_time": 30.0,
                "status": BulkOperationStatus.COMPLETED
            }
        ]

        prediction = await engine.predict_operation_performance(BulkOperationType.INSERT, 2000)

        assert "predicted_duration_seconds" in prediction
        assert "confidence" in prediction
        assert "recommendations" in prediction
        assert isinstance(prediction["recommendations"], list)


class TestBulkMonitoringDashboard:
    """Test the BulkMonitoringDashboard class."""

    def test_init_default_settings(self):
        """Test dashboard initialization."""
        dashboard = BulkMonitoringDashboard()

        assert isinstance(dashboard.metrics_collector, MetricsCollector)
        assert isinstance(dashboard.operation_tracker, OperationTracker)
        assert isinstance(dashboard.alert_manager, AlertManager)
        assert isinstance(dashboard.analytics_engine, AnalyticsEngine)
        assert dashboard.dashboard_config["refresh_interval"] == 5.0

    @pytest.mark.asyncio
    async def test_initialize_dashboard(self):
        """Test dashboard initialization."""
        dashboard = BulkMonitoringDashboard()

        # Mock the monitoring loop to avoid it running
        with patch.object(dashboard, '_monitoring_loop', new_callable=AsyncMock):
            await dashboard.initialize()

        # Should have created default alerts
        alert_stats = await dashboard.alert_manager.get_alert_statistics()
        assert alert_stats["total_alerts"] > 0

    @pytest.mark.asyncio
    @patch('app.bulk_monitoring_analytics.psutil')
    async def test_collect_dashboard_metrics(self, mock_psutil):
        """Test collecting dashboard metrics."""
        dashboard = BulkMonitoringDashboard()

        # Mock psutil
        mock_psutil.cpu_percent.return_value = 75.5
        mock_psutil.virtual_memory.return_value.percent = 60.2
        mock_psutil.disk_usage.return_value.percent = 45.8

        metrics = await dashboard._collect_dashboard_metrics()

        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_usage" in metrics
        assert "active_operations" in metrics
        assert metrics["cpu_usage"] == 75.5

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self):
        """Test getting complete dashboard data."""
        dashboard = BulkMonitoringDashboard()

        # Add some test data
        await dashboard.metrics_collector.record_metric("cpu_usage", 70.0)
        await dashboard.metrics_collector.record_metric("memory_usage", 50.0)

        data = await dashboard.get_dashboard_data()

        assert "current_metrics" in data
        assert "operation_statistics" in data
        assert "active_alerts" in data
        assert "performance_trends" in data
        assert "insights" in data
        assert "cost_analysis" in data
        assert "dashboard_health" in data
        assert "last_updated" in data

    @pytest.mark.asyncio
    async def test_shutdown_dashboard(self):
        """Test graceful dashboard shutdown."""
        dashboard = BulkMonitoringDashboard()

        # Mock the monitoring task
        mock_task = AsyncMock()
        dashboard.monitoring_task = mock_task

        await dashboard.shutdown()

        mock_task.cancel.assert_called_once()


class TestGlobalFunctions:
    """Test global utility functions."""

    @pytest.mark.asyncio
    async def test_get_monitoring_dashboard_singleton(self):
        """Test the global monitoring dashboard singleton."""
        # Reset global instance
        import app.bulk_monitoring_analytics
        app.bulk_monitoring_analytics._monitoring_dashboard_instance = None

        # Mock initialization to prevent actual monitoring loop
        with patch('app.bulk_monitoring_analytics.BulkMonitoringDashboard.initialize', new_callable=AsyncMock):
            dashboard1 = await get_monitoring_dashboard()
            dashboard2 = await get_monitoring_dashboard()

        # Should return the same instance
        assert dashboard1 is dashboard2
        assert isinstance(dashboard1, BulkMonitoringDashboard)
