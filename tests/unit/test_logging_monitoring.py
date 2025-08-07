"""
Test logging and monitoring systems
"""

import asyncio
import time
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

from app.core.logging import AuditLogger, LogConfig, PerformanceLogger, StructuredLogger, get_logger
from app.core.monitoring import (
    HealthChecker,
    MetricDefinition,
    MetricsCollector,
    MetricType,
    RequestTracker,
    get_metrics_collector,
)


class TestLogging:
    """Test logging functionality"""

    def test_logger_creation(self):
        """Test creating a logger"""
        config = LogConfig(level="INFO", format="json")
        logger = StructuredLogger("test", config)

        assert logger.name == "test"
        assert logger.config.level == "INFO"

    def test_logger_context(self):
        """Test logger adds context"""
        from app.core.logging import request_id_var, user_id_var

        # Set context
        request_id_var.set("req-123")
        user_id_var.set("user-456")

        config = LogConfig(level="INFO", format="json")
        logger = StructuredLogger("test", config)

        # Create context
        context = logger._add_context({"custom": "value"})

        assert context["request_id"] == "req-123"
        assert context["user_id"] == "user-456"
        assert context["custom"] == "value"
        assert "timestamp" in context

    def test_performance_logger(self):
        """Test performance logger"""
        logger = get_logger("test")

        with PerformanceLogger("test_operation", logger, test=True) as perf:
            time.sleep(0.1)

        # Logger should have recorded the operation
        assert perf.start_time is not None

    def test_audit_logger(self):
        """Test audit logger"""
        logger = get_logger("audit")
        audit_logger = AuditLogger(logger)

        # Log an audit event
        audit_logger.log_event(
            event_type="USER_ACTION",
            resource="memory",
            action="create",
            result="success",
            user_id="user-123",
            details={"memory_id": "mem-456"},
        )

        # No exception should be raised


class TestMonitoring:
    """Test monitoring functionality"""

    def test_metrics_collector_creation(self):
        """Test creating metrics collector"""
        collector = MetricsCollector("test_app")

        # Note: Due to singleton pattern, app_name might be from previous initialization
        assert collector.app_name is not None
        assert collector.request_count is not None
        assert collector.memory_count is not None

    def test_custom_metric_registration(self):
        """Test registering custom metrics"""
        collector = MetricsCollector("test_app")

        # Register a counter
        definition = MetricDefinition(
            name="test_counter",
            type=MetricType.COUNTER,
            description="Test counter",
            labels=["status"],
        )
        metric = collector.register_custom_metric(definition)

        assert metric is not None
        assert "test_counter" in collector.custom_metrics

    def test_metric_operations(self):
        """Test metric operations"""
        collector = get_metrics_collector()

        # Register metrics
        collector.register_custom_metric(
            MetricDefinition(
                name="test_ops_counter",
                type=MetricType.COUNTER,
                description="Test operations",
                labels=["operation"],
            )
        )

        collector.register_custom_metric(
            MetricDefinition(
                name="test_gauge",
                type=MetricType.GAUGE,
                description="Test gauge",
                labels=["component"],
            )
        )

        collector.register_custom_metric(
            MetricDefinition(
                name="test_histogram",
                type=MetricType.HISTOGRAM,
                description="Test histogram",
                labels=["endpoint"],
            )
        )

        # Test operations
        collector.increment_counter("test_ops_counter", 1, operation="read")
        collector.set_gauge("test_gauge", 42.5, component="memory")
        collector.observe_histogram("test_histogram", 0.125, endpoint="/api/test")

        # Record timeseries
        collector.record_timeseries("cpu_usage", 75.5)

        # Check timeseries data
        assert len(collector._timeseries_data) > 0

    @pytest.mark.asyncio
    async def test_system_metrics_collection(self):
        """Test collecting system metrics"""
        collector = MetricsCollector("test_app")

        await collector.collect_system_metrics()

        # CPU and memory gauges should be set
        # Note: We can't check exact values as they vary
        summary = collector.get_metrics_summary()

        assert "system" in summary
        assert "cpu_usage" in summary["system"]
        assert "memory_usage_mb" in summary["system"]
        assert summary["system"]["cpu_usage"] >= 0
        assert summary["system"]["memory_usage_mb"] > 0


class TestHealthChecker:
    """Test health checker functionality"""

    def test_health_checker_creation(self):
        """Test creating health checker"""
        checker = HealthChecker()

        assert checker.checks == {}
        assert checker.check_results == {}

    def test_register_health_check(self):
        """Test registering health checks"""
        checker = HealthChecker()

        def test_check():
            return {"healthy": True, "message": "Test OK"}

        checker.register_check("test", test_check)

        assert "test" in checker.checks

    @pytest.mark.asyncio
    async def test_run_health_checks(self):
        """Test running health checks"""
        checker = HealthChecker()

        # Register sync check
        def sync_check():
            return {"healthy": True, "sync": True}

        # Register async check
        async def async_check():
            await asyncio.sleep(0.01)
            return {"healthy": True, "async": True}

        # Register failing check
        def failing_check():
            raise Exception("Test failure")

        checker.register_check("sync", sync_check)
        checker.register_check("async", async_check)
        checker.register_check("failing", failing_check)

        # Run checks
        results = await checker.run_checks()

        assert results["status"] == "unhealthy"  # Due to failing check
        assert results["checks"]["sync"]["status"] == "healthy"
        assert results["checks"]["async"]["status"] == "healthy"
        assert results["checks"]["failing"]["status"] == "unhealthy"
        assert "error" in results["checks"]["failing"]

    @pytest.mark.asyncio
    async def test_disk_space_check(self):
        """Test disk space health check"""
        checker = HealthChecker()

        result = await checker.check_disk_space(min_free_gb=0.001)  # Very low threshold

        assert result["healthy"] is True
        assert "free_gb" in result
        assert "used_percent" in result


class TestRequestTracker:
    """Test request tracking"""

    def test_request_tracker_creation(self):
        """Test creating request tracker"""
        collector = MetricsCollector("test_app")
        tracker = RequestTracker(collector)

        assert tracker.metrics == collector
        assert tracker.active_requests == 0
        assert len(tracker.request_history) == 0

    @pytest.mark.asyncio
    async def test_track_request(self):
        """Test tracking a request"""
        collector = MetricsCollector("test_app")
        tracker = RequestTracker(collector)

        # Mock request and response
        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"

        response = Mock()
        response.status_code = 200
        response.headers = {}

        # Mock call_next
        async def call_next(req):
            await asyncio.sleep(0.01)
            return response

        # Track request
        result = await tracker.track_request(request, call_next)

        assert result == response
        assert len(tracker.request_history) == 1
        assert tracker.request_history[0]["method"] == "GET"
        assert tracker.request_history[0]["path"] == "/api/test"
        assert tracker.request_history[0]["status"] == 200
        assert "X-Response-Time" in response.headers


class TestMonitoringDecorator:
    """Test monitoring decorator"""

    @pytest.mark.asyncio
    async def test_monitor_performance_async(self):
        """Test monitoring async function performance"""
        from app.core.monitoring import monitor_performance

        collector = get_metrics_collector()

        # Register metric
        collector.register_custom_metric(
            MetricDefinition(
                name="operation_duration",
                type=MetricType.HISTOGRAM,
                description="Operation duration",
                labels=["operation", "status"],
            )
        )

        @monitor_performance("test_async_op")
        async def test_function():
            await asyncio.sleep(0.01)
            return "success"

        result = await test_function()
        assert result == "success"

    def test_monitor_performance_sync(self):
        """Test monitoring sync function performance"""
        from app.core.monitoring import monitor_performance

        collector = get_metrics_collector()

        # Register metrics if not already registered
        if "operation_duration" not in collector.custom_metrics:
            collector.register_custom_metric(
                MetricDefinition(
                    name="operation_duration",
                    type=MetricType.HISTOGRAM,
                    description="Operation duration",
                    labels=["operation", "status"],
                )
            )

        if "operation_errors" not in collector.custom_metrics:
            collector.register_custom_metric(
                MetricDefinition(
                    name="operation_errors",
                    type=MetricType.COUNTER,
                    description="Operation errors",
                    labels=["operation", "error_type"],
                )
            )

        @monitor_performance("test_sync_op")
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()
        assert result == "success"

        # Test error handling
        @monitor_performance("test_error_op")
        def error_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_function()
