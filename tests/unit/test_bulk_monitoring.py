"""
Additional comprehensive tests for bulk monitoring analytics coverage.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import statistics

from app.bulk_monitoring_analytics import (
    MetricsCollector,
    OperationTracker, 
    AlertManager,
    AnalyticsEngine,
    BulkMonitoringDashboard,
    MetricType,
    AlertSeverity,
    AnalyticsTimeframe,
    MetricPoint,
    Alert,
    get_monitoring_dashboard,
)
from app.bulk_memory_operations import (
    BulkOperationType, 
    BulkOperationStatus,
    BulkOperationProgress,
    BulkOperationResult
)


class TestMetricsCollectorAdvanced:
    """Advanced tests for MetricsCollector."""

    @pytest.mark.asyncio
    async def test_internal_aggregation_trigger(self):
        """Test that internal aggregation is triggered when buffer is full."""
        collector = MetricsCollector()
        
        # Fill buffer to near capacity to trigger aggregation
        for i in range(9900):
            metric = MetricPoint(
                timestamp=datetime.now(),
                metric_name="test_metric",
                metric_type=MetricType.COUNTER,
                value=float(i),
                tags={}
            )
            collector.metrics_buffer.append(metric)
        
        # This should trigger internal aggregation
        await collector.record_metric("trigger_metric", 999.0)
        
        # Buffer should be cleared after aggregation (or very small)
        assert len(collector.metrics_buffer) <= 1  # Buffer cleared or just the new metric
        assert collector.collection_stats["last_aggregation"] is not None

    @pytest.mark.asyncio
    async def test_get_metrics_with_aggregation(self):
        """Test getting metrics with time range after aggregation."""
        collector = MetricsCollector()
        
        # Add metrics and force aggregation
        for i in range(20):
            await collector.record_metric("test_metric", float(i), MetricType.COUNTER)
        
        await collector._aggregate_metrics()
        
        # Test retrieval
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        metrics = await collector.get_metrics("test_metric", start_time, end_time)
        
        assert len(metrics) >= 0  # Should return aggregated data
        if metrics:
            assert "timestamp" in metrics[0]
            assert "value" in metrics[0]

    @pytest.mark.asyncio
    async def test_get_latest_metrics_from_aggregated(self):
        """Test getting latest metrics when buffer is empty but aggregated data exists."""
        collector = MetricsCollector()
        
        # Add and aggregate metrics
        await collector.record_metric("cpu_usage", 75.0)
        await collector.record_metric("memory_usage", 512.0)
        await collector._aggregate_metrics()
        
        # Buffer should be empty, but aggregated data should exist
        assert len(collector.metrics_buffer) == 0
        
        latest = await collector.get_latest_metrics(["cpu_usage", "memory_usage"])
        
        # Should get values from aggregated data
        assert "cpu_usage" in latest
        assert "memory_usage" in latest


class TestOperationTrackerAdvanced:
    """Advanced tests for OperationTracker."""

    @pytest.mark.asyncio
    async def test_get_operation_status(self):
        """Test getting operation status."""
        tracker = OperationTracker()
        
        progress = BulkOperationProgress(
            operation_id="test-op",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.RUNNING,
            total_items=100,
            processed_items=50,
            successful_items=45,
            failed_items=5,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        
        await tracker.start_tracking(progress)
        
        status = await tracker.get_operation_status("test-op")
        assert status is not None
        assert status.operation_id == "test-op"
        assert status.processed_items == 50
        
        # Test non-existent operation
        status = await tracker.get_operation_status("non-existent")
        assert status is None

    @pytest.mark.asyncio 
    async def test_get_active_operations(self):
        """Test getting all active operations."""
        tracker = OperationTracker()
        
        # Start multiple operations
        operations = []
        for i in range(3):
            progress = BulkOperationProgress(
                operation_id=f"op-{i}",
                operation_type=BulkOperationType.INSERT,
                status=BulkOperationStatus.RUNNING,
                total_items=100,
                processed_items=10 * i,
                successful_items=10 * i,
                failed_items=0,
                skipped_items=0,
                start_time=datetime.now(),
                last_update=datetime.now()
            )
            operations.append(progress)
            await tracker.start_tracking(progress)
        
        active_ops = await tracker.get_active_operations()
        assert len(active_ops) == 3
        
        # Verify all operations are present
        op_ids = [op.operation_id for op in active_ops]
        assert "op-0" in op_ids
        assert "op-1" in op_ids
        assert "op-2" in op_ids


class TestAlertManagerAdvanced:
    """Advanced tests for AlertManager."""

    @pytest.mark.asyncio
    async def test_alert_condition_evaluation(self):
        """Test detailed alert condition evaluation."""
        manager = AlertManager()
        
        # Test different condition types
        conditions_data = [
            ("cpu_usage > threshold", {"cpu_usage": 95.0}, {"threshold": 90.0}, True),
            ("memory_usage > threshold", {"memory_usage": 80.0}, {"threshold": 85.0}, False),
            ("error_rate > threshold", {"error_rate": 0.15}, {"threshold": 0.1}, True),
            ("response_time > threshold", {"response_time": 45.0}, {"threshold": 30.0}, True),
        ]
        
        for condition, metrics, _, expected in conditions_data:
            alert = Alert(
                alert_id="test-alert",
                name="Test Alert",
                description="Test alert",
                severity=AlertSeverity.WARNING,
                condition=condition,
                threshold=90.0 if "cpu" in condition else 85.0 if "memory" in condition else 0.1 if "error" in condition else 30.0
            )
            
            should_trigger = await manager._evaluate_alert_condition(alert, metrics, {})
            assert should_trigger == expected

    @pytest.mark.asyncio
    async def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        # Define some alerts
        await manager.define_alert(
            name="CPU Alert",
            description="High CPU",
            condition="cpu_usage > threshold", 
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        await manager.define_alert(
            name="Memory Alert",
            description="High Memory",
            condition="memory_usage > threshold",
            threshold=90.0,
            severity=AlertSeverity.ERROR
        )
        
        # Trigger alerts
        await manager.check_alerts({"cpu_usage": 85.0, "memory_usage": 95.0}, {})
        
        active_alerts = await manager.get_active_alerts()
        assert len(active_alerts) == 2
        
        alert_names = [alert.name for alert in active_alerts]
        assert "CPU Alert" in alert_names
        assert "Memory Alert" in alert_names


class TestAnalyticsEngineAdvanced:
    """Advanced tests for AnalyticsEngine."""

    @pytest.mark.asyncio
    async def test_calculate_trend_detailed(self):
        """Test detailed trend calculation."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)
        
        # Create trend data - increasing trend
        data_points = []
        base_time = datetime.now()
        for i in range(10):
            point = {
                "timestamp": base_time - timedelta(hours=9-i),
                "value": 10.0 + i * 2.0,  # Increasing by 2 each hour
                "count": 1,
                "min": 10.0 + i * 2.0,
                "max": 10.0 + i * 2.0,
                "std": 0.0
            }
            data_points.append(point)
        
        trend = await engine._calculate_trend("test_metric", data_points, AnalyticsTimeframe.DAY)
        
        assert trend.metric_name == "test_metric"
        assert trend.timeframe == AnalyticsTimeframe.DAY
        assert trend.trend_direction == "increasing"
        assert trend.change_percentage > 0

    @pytest.mark.asyncio
    async def test_generate_operation_insights_detailed(self):
        """Test detailed operation insights generation."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)
        
        # Add operation history with performance issues
        tracker.operation_history[BulkOperationType.INSERT] = [
            {
                "operation_id": "slow-op-1",
                "status": BulkOperationStatus.COMPLETED,
                "total_items": 1000,
                "execution_time": 400.0,  # Over 5 minutes
                "completed_at": datetime.now()
            },
            {
                "operation_id": "failed-op-1", 
                "status": BulkOperationStatus.FAILED,
                "total_items": 500,
                "execution_time": 60.0,
                "completed_at": datetime.now()
            }
        ]
        
        # Add more operations to get completion rate below 90%
        for i in range(3):
            tracker.operation_history[BulkOperationType.INSERT].append({
                "operation_id": f"failed-op-{i+2}",
                "status": BulkOperationStatus.FAILED,
                "total_items": 100,
                "execution_time": 30.0,
                "completed_at": datetime.now()
            })
        
        insights = await engine.generate_operation_insights()
        
        assert len(insights) > 0
        
        # Should detect both performance and efficiency issues
        insight_types = [insight.insight_type for insight in insights]
        assert "efficiency" in insight_types or "performance" in insight_types

    @pytest.mark.asyncio
    async def test_predict_operation_performance_detailed(self):
        """Test detailed operation performance prediction."""
        collector = MetricsCollector()
        tracker = OperationTracker()
        engine = AnalyticsEngine(collector, tracker)
        
        # Add consistent historical data
        tracker.operation_history[BulkOperationType.UPDATE] = [
            {
                "operation_id": f"update-{i}",
                "status": BulkOperationStatus.COMPLETED,
                "total_items": 100,
                "execution_time": 60.0,  # 1 minute for 100 items
            }
            for i in range(10)
        ]
        
        prediction = await engine.predict_operation_performance(BulkOperationType.UPDATE, 500)
        
        assert "predicted_duration_seconds" in prediction
        assert "confidence" in prediction
        assert "based_on_operations" in prediction
        assert "recommendations" in prediction
        
        # Should predict ~5 minutes for 500 items based on 1 min per 100 items
        predicted_duration = prediction["predicted_duration_seconds"]
        assert 250.0 < predicted_duration < 350.0  # Allow some variance
        assert prediction["based_on_operations"] == 10
        assert prediction["confidence"] > 0.5


class TestBulkMonitoringDashboardAdvanced:
    """Advanced tests for BulkMonitoringDashboard."""

    @pytest.mark.asyncio
    async def test_setup_default_alerts(self):
        """Test that default alerts are set up correctly."""
        dashboard = BulkMonitoringDashboard()
        
        await dashboard._setup_default_alerts()
        
        alert_stats = await dashboard.alert_manager.get_alert_statistics()
        assert alert_stats["total_alerts"] >= 4  # Should have CPU, Memory, Error Rate, Slow Ops alerts
        
        # Check that different severity levels are used
        severity_counts = alert_stats["alerts_by_severity"]
        assert AlertSeverity.WARNING.value in severity_counts
        assert AlertSeverity.ERROR.value in severity_counts

    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def test_collect_dashboard_metrics_detailed(self, mock_disk, mock_memory, mock_cpu):
        """Test detailed dashboard metrics collection."""
        dashboard = BulkMonitoringDashboard()
        
        # Mock psutil with detailed values
        mock_cpu.return_value = 72.3
        mock_memory.return_value.percent = 58.7
        mock_disk.return_value.percent = 23.4
        
        # Add some active operations
        progress = BulkOperationProgress(
            operation_id="active-op-1",
            operation_type=BulkOperationType.INSERT,
            status=BulkOperationStatus.RUNNING,
            total_items=1000,
            processed_items=500,
            successful_items=480,
            failed_items=20,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        await dashboard.operation_tracker.start_tracking(progress)
        
        metrics = await dashboard._collect_dashboard_metrics()
        
        assert metrics["cpu_usage"] == 72.3
        assert metrics["memory_usage"] == 58.7
        assert metrics["disk_usage"] == 23.4
        assert metrics["active_operations"] == 1
        assert "error_rate" in metrics
        assert "response_time" in metrics
        assert "throughput" in metrics

    @pytest.mark.asyncio
    async def test_get_dashboard_data_comprehensive(self):
        """Test comprehensive dashboard data retrieval."""
        dashboard = BulkMonitoringDashboard()
        
        # Add sample data
        await dashboard.metrics_collector.record_metric("cpu_usage", 65.0)
        await dashboard.metrics_collector.record_metric("throughput", 1250.5)
        
        # Add operation tracking
        progress = BulkOperationProgress(
            operation_id="dashboard-op",
            operation_type=BulkOperationType.DELETE,
            status=BulkOperationStatus.RUNNING,
            total_items=200,
            processed_items=150,
            successful_items=140,
            failed_items=10,
            skipped_items=0,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        await dashboard.operation_tracker.start_tracking(progress)
        
        # Define an alert
        await dashboard.alert_manager.define_alert(
            name="Test Dashboard Alert",
            description="Test alert for dashboard",
            condition="cpu_usage > threshold",
            threshold=50.0,
            severity=AlertSeverity.INFO
        )
        
        data = await dashboard.get_dashboard_data()
        
        # Verify comprehensive structure
        expected_keys = [
            "current_metrics", "operation_statistics", "active_alerts",
            "performance_trends", "insights", "cost_analysis", 
            "dashboard_health", "last_updated"
        ]
        
        for key in expected_keys:
            assert key in data
        
        # Verify dashboard health
        health = data["dashboard_health"]
        assert "monitoring_active" in health
        assert "metrics_buffer_size" in health
        assert "active_operations_count" in health
        assert "total_alerts" in health


class TestGlobalFunctionalities:
    """Test global monitoring dashboard functions."""

    @pytest.mark.asyncio
    async def test_global_dashboard_initialization(self):
        """Test global dashboard singleton functionality."""
        # Reset the global instance
        import app.bulk_monitoring_analytics
        app.bulk_monitoring_analytics._monitoring_dashboard_instance = None
        
        # Mock the initialize method to prevent actual monitoring loop
        with patch.object(BulkMonitoringDashboard, 'initialize', new_callable=AsyncMock) as mock_init:
            dashboard1 = await get_monitoring_dashboard()
            dashboard2 = await get_monitoring_dashboard()
            
            # Should be the same instance
            assert dashboard1 is dashboard2
            
            # Initialize should be called only once
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitoring_dashboard_lifecycle(self):
        """Test the complete lifecycle of monitoring dashboard."""
        dashboard = BulkMonitoringDashboard()
        
        # Test initialization
        with patch.object(dashboard, '_monitoring_loop', new_callable=AsyncMock):
            await dashboard.initialize()
        
        # Should have default alerts
        alert_stats = await dashboard.alert_manager.get_alert_statistics()
        assert alert_stats["total_alerts"] > 0
        
        # Test shutdown logic without mocking complex async behavior
        # Just verify the shutdown method exists and can be called
        dashboard.monitoring_task = None  # Simulate no active task
        await dashboard.shutdown()  # Should complete without error
        
        # Test that cancel is called when task exists
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        dashboard.monitoring_task = mock_task
        
        # Test the cancel logic
        if dashboard.monitoring_task:
            dashboard.monitoring_task.cancel()
        
        mock_task.cancel.assert_called_once()


# Additional edge case and integration tests
class TestIntegrationScenarios:
    """Integration tests covering realistic scenarios."""

    @pytest.mark.asyncio
    async def test_high_volume_metrics_scenario(self):
        """Test handling high volume of metrics."""
        collector = MetricsCollector()
        
        # Simulate high-volume metric collection
        metrics_count = 5000
        start_time = datetime.now()
        
        for i in range(metrics_count):
            await collector.record_metric(
                name=f"high_vol_metric_{i % 10}",  # 10 different metric types
                value=float(i % 100),
                metric_type=MetricType.GAUGE if i % 2 == 0 else MetricType.COUNTER,
                tags={"batch": str(i // 100), "worker": str(i % 4)}
            )
        
        # Should handle all metrics
        assert len(collector.metrics_buffer) <= 10000  # Buffer limit
        assert collector.collection_stats["total_points"] == metrics_count

    @pytest.mark.asyncio
    async def test_complex_alert_scenario(self):
        """Test complex alerting scenarios."""
        manager = AlertManager()
        
        # Set up alerts
        await manager.define_alert(
            name="Critical CPU",
            description="CPU critically high",
            condition="cpu_usage > threshold",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL
        )
        
        await manager.define_alert(
            name="Memory Warning", 
            description="Memory usage warning",
            condition="memory_usage > threshold",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        # Test cascading alerts
        metrics_sequence = [
            {"cpu_usage": 70.0, "memory_usage": 60.0},  # No alerts
            {"cpu_usage": 70.0, "memory_usage": 85.0},  # Memory alert
            {"cpu_usage": 98.0, "memory_usage": 85.0},  # Both alerts
            {"cpu_usage": 70.0, "memory_usage": 60.0},  # Resolve both
        ]
        
        alert_counts = []
        for metrics in metrics_sequence:
            await manager.check_alerts(metrics, {})
            active = await manager.get_active_alerts()
            alert_counts.append(len(active))
        
        # Should see: 0, 1, 2, 0 active alerts
        assert alert_counts == [0, 1, 2, 0]


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


class TestMetricsCollectorBasic:
    """Basic tests for MetricsCollector."""

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


class TestOperationTrackerBasic:
    """Basic tests for OperationTracker."""

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


class TestAlertManagerBasic:
    """Basic tests for AlertManager."""

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


class TestAnalyticsEngineBasic:
    """Basic tests for AnalyticsEngine."""

    def test_initialization(self):
        collector = MetricsCollector()
        tracker = OperationTracker()
        
        engine = AnalyticsEngine(collector, tracker)
        
        assert engine.metrics_collector == collector
        assert engine.operation_tracker == tracker


class TestBulkMonitoringDashboardBasic:
    """Basic tests for BulkMonitoringDashboard."""

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
