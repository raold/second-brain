"""
Tests for bulk monitoring analytics module.
Simple tests focusing on import, instantiation, and basic functionality.
"""

from datetime import datetime, timedelta

import pytest

from app.bulk_memory_operations import BulkOperationProgress, BulkOperationStatus, BulkOperationType
from app.bulk_monitoring_analytics import (
    AlertManager,
    AlertSeverity,
    AnalyticsEngine,
    AnalyticsTimeframe,
    BulkMonitoringDashboard,
    MetricPoint,
    MetricsCollector,
    MetricType,
    OperationTracker,
)


class TestMetricTypes:
    """Test metric type enums."""

    def test_metric_type_enum(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"

    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_analytics_timeframe_enum(self):
        assert AnalyticsTimeframe.HOUR.value == "hour"


class TestMetricPoint:
    """Test metric point data class."""

    def test_metric_point_creation(self):
        now = datetime.now()
        point = MetricPoint(
            timestamp=now,
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=42.0,
            tags={"env": "test"},
            operation_id="op123"
        )

        assert point.timestamp == now
        assert point.metric_name == "test_metric"
        assert point.metric_type == MetricType.GAUGE
        assert point.value == 42.0
        assert point.tags == {"env": "test"}
        assert point.operation_id == "op123"


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_initialization(self):
        collector = MetricsCollector()
        assert collector.retention_days == 30
        assert len(collector.metrics_buffer) == 0
        assert collector.collection_stats["total_points"] == 0

    def test_initialization_with_custom_retention(self):
        collector = MetricsCollector(retention_days=60)
        assert collector.retention_days == 60

    @pytest.mark.asyncio
    async def test_record_metric_basic(self):
        collector = MetricsCollector()

        await collector.record_metric("test_metric", 100.0)

        assert len(collector.metrics_buffer) == 1
        assert collector.collection_stats["total_points"] == 1

        metric = collector.metrics_buffer[0]
        assert metric.metric_name == "test_metric"
        assert metric.value == 100.0
        assert metric.metric_type == MetricType.GAUGE

    @pytest.mark.asyncio
    async def test_record_metric_with_options(self):
        collector = MetricsCollector()

        await collector.record_metric(
            "counter_metric",
            1.0,
            MetricType.COUNTER,
            tags={"service": "test"},
            operation_id="op456"
        )

        metric = collector.metrics_buffer[0]
        assert metric.metric_type == MetricType.COUNTER
        assert metric.tags == {"service": "test"}
        assert metric.operation_id == "op456"


class TestOperationTracker:
    """Test OperationTracker class."""

    def test_initialization(self):
        tracker = OperationTracker()
        assert len(tracker.active_operations) == 0
        assert tracker.tracking_stats["total_operations"] == 0
        assert tracker.tracking_stats["active_count"] == 0

    @pytest.mark.asyncio
    async def test_start_tracking(self):
        tracker = OperationTracker()

        now = datetime.now()
        operation = BulkOperationProgress(
            operation_id="test_op",
            operation_type=BulkOperationType.INSERT,
            total_items=100,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            status=BulkOperationStatus.RUNNING,
            start_time=now,
            last_update=now
        )

        await tracker.start_tracking(operation)

        assert len(tracker.active_operations) == 1
        assert "test_op" in tracker.active_operations
        assert tracker.tracking_stats["total_operations"] == 1
        assert tracker.tracking_stats["active_count"] == 1

    @pytest.mark.asyncio
    async def test_update_progress(self):
        tracker = OperationTracker()

        # Use a time that's not exactly now to avoid division by zero
        start_time = datetime.now() - timedelta(seconds=1)
        operation = BulkOperationProgress(
            operation_id="test_op",
            operation_type=BulkOperationType.INSERT,
            total_items=100,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            status=BulkOperationStatus.RUNNING,
            start_time=start_time,
            last_update=start_time
        )

        await tracker.start_tracking(operation)
        await tracker.update_progress("test_op", {"processed_items": 50})

        updated_op = tracker.active_operations["test_op"]
        assert updated_op.processed_items == 50


class TestAlertManager:
    """Test AlertManager class."""

    def test_initialization(self):
        manager = AlertManager()
        assert len(manager.alerts) == 0
        assert len(manager.alert_history) == 0
        assert len(manager.notification_channels) == 0

    @pytest.mark.asyncio
    async def test_define_alert(self):
        manager = AlertManager()

        alert_id = await manager.define_alert(
            name="test_alert",
            description="Test alert",
            condition="cpu > 80",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )

        assert alert_id is not None
        assert len(manager.alerts) == 1
        assert alert_id in manager.alerts

        alert = manager.alerts[alert_id]
        assert alert.name == "test_alert"
        assert alert.threshold == 80.0
        assert alert.severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_check_alerts_no_alerts(self):
        manager = AlertManager()

        # Should not raise any errors
        await manager.check_alerts({}, {})


class TestAnalyticsEngine:
    """Test AnalyticsEngine class."""

    def test_initialization(self):
        collector = MetricsCollector()
        tracker = OperationTracker()

        engine = AnalyticsEngine(collector, tracker)

        assert engine.metrics_collector == collector
        assert engine.operation_tracker == tracker


class TestBulkMonitoringDashboard:
    """Test BulkMonitoringDashboard class."""

    def test_initialization(self):
        dashboard = BulkMonitoringDashboard()

        assert dashboard.metrics_collector is not None
        assert dashboard.operation_tracker is not None
        assert dashboard.alert_manager is not None
        assert dashboard.analytics_engine is not None

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self):
        dashboard = BulkMonitoringDashboard()

        data = await dashboard.get_dashboard_data()

        # Should return a dictionary with expected keys
        assert isinstance(data, dict)
        assert "current_metrics" in data
        assert "dashboard_health" in data  # Use the actual key from the dashboard
        assert "active_alerts" in data
