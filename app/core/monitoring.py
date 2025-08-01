import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.monitoring.metrics_collector import MetricsCollector

"""
Monitoring and metrics collection for Second Brain v3.0.0

This module provides:
- Application metrics collection
- Performance monitoring
- Health checks
- Resource usage tracking
- Custom metrics
"""

from collections import defaultdict, deque
from collections.abc import Callable
from enum import Enum

import psutil
from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
)
import redis.asyncio as redis

# Optional Redis dependency
try:

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None


class MetricType(str, Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """A single metric data point"""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """Definition of a metric"""

    name: str
    type: MetricType
    description: str
    labels: list[str] = field(default_factory=list)
    buckets: list[float] | None = None  # For histograms


class MetricsCollector:
    """Collects and manages application metrics"""

    _instance = None
    _initialized = False

    def __new__(cls, app_name: str = "second_brain"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_name: str = "second_brain"):
        if not self._initialized:
            self.app_name = app_name
            self.metrics: dict[str, Any] = {}
            self._timeseries_data: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
            self._setup_default_metrics()
            self.__class__._initialized = True

    def _setup_default_metrics(self):
        """Set up default metrics"""
        # Request metrics
        self.request_count = Counter(
            f"{self.app_name}_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
        )

        self.request_duration = Histogram(
            f"{self.app_name}_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Memory metrics
        self.memory_count = Gauge(
            f"{self.app_name}_memories_total", "Total number of memories", ["type"]
        )

        self.memory_operations = Counter(
            f"{self.app_name}_memory_operations_total",
            "Total number of memory operations",
            ["operation", "status"],
        )

        # Database metrics
        self.db_connections = Gauge(
            f"{self.app_name}_database_connections", "Number of database connections", ["state"]
        )

        self.db_query_duration = Histogram(
            f"{self.app_name}_database_query_duration_seconds",
            "Database query duration",
            ["query_type"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )

        # System metrics
        self.cpu_usage = Gauge(f"{self.app_name}_cpu_usage_percent", "CPU usage percentage")

        self.memory_usage = Gauge(f"{self.app_name}_memory_usage_bytes", "Memory usage in bytes")

        # Error metrics
        self.error_count = Counter(
            f"{self.app_name}_errors_total", "Total number of errors", ["error_type", "endpoint"]
        )

        # Custom metrics registry
        self.custom_metrics: dict[str, Any] = {}

    def register_custom_metric(self, definition: MetricDefinition):
        """Register a custom metric"""
        if definition.type == MetricType.COUNTER:
            metric = Counter(
                f"{self.app_name}_{definition.name}", definition.description, definition.labels
            )
        elif definition.type == MetricType.GAUGE:
            metric = Gauge(
                f"{self.app_name}_{definition.name}", definition.description, definition.labels
            )
        elif definition.type == MetricType.HISTOGRAM:
            metric = Histogram(
                f"{self.app_name}_{definition.name}",
                definition.description,
                definition.labels,
                buckets=definition.buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            )
        elif definition.type == MetricType.SUMMARY:
            metric = Summary(
                f"{self.app_name}_{definition.name}", definition.description, definition.labels
            )
        else:
            raise ValueError(f"Unknown metric type: {definition.type}")

        self.custom_metrics[definition.name] = metric
        return metric

    def increment_counter(self, name: str, value: float = 1, **labels):
        """Increment a counter metric"""
        if name in self.custom_metrics:
            self.custom_metrics[name].labels(**labels).inc(value)

    def set_gauge(self, name: str, value: float, **labels):
        """Set a gauge metric"""
        if name in self.custom_metrics:
            self.custom_metrics[name].labels(**labels).set(value)

    def observe_histogram(self, name: str, value: float, **labels):
        """Observe a histogram metric"""
        if name in self.custom_metrics:
            self.custom_metrics[name].labels(**labels).observe(value)

    def record_timeseries(self, name: str, value: float, **labels):
        """Record a timeseries data point"""
        key = f"{name}:{json.dumps(labels, sort_keys=True)}"
        self._timeseries_data[key].append(
            MetricPoint(timestamp=time.time(), value=value, labels=labels)
        )

    async def collect_system_metrics(self):
        """Collect system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_usage.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        self.memory_usage.set(memory.used)

        # Record timeseries
        self.record_timeseries("cpu_usage", cpu_percent)
        self.record_timeseries("memory_usage", memory.used)
        self.record_timeseries("memory_percent", memory.percent)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics"""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "memory_usage_mb": psutil.virtual_memory().used / 1024 / 1024,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
            },
            "application": {
                "uptime_seconds": time.time() - getattr(self, "_start_time", time.time())
            },
            "timeseries": {},
        }

        # Add recent timeseries data
        for key, points in self._timeseries_data.items():
            if points:
                recent = list(points)[-10:]  # Last 10 points
                summary["timeseries"][key] = [
                    {"timestamp": p.timestamp, "value": p.value} for p in recent
                ]

        return summary


class HealthChecker:
    """Performs health checks on various components"""

    def __init__(self):
        self.checks: dict[str, Callable] = {}
        self.check_results: dict[str, dict[str, Any]] = {}

    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func

    async def run_checks(self) -> dict[str, Any]:
        """Run all registered health checks"""
        results = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "checks": {}}

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                duration = time.time() - start_time

                results["checks"][name] = {
                    "status": "healthy" if result.get("healthy", True) else "unhealthy",
                    "duration_ms": duration * 1000,
                    **result,
                }

                if not result.get("healthy", True):
                    results["status"] = "unhealthy"

            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                results["status"] = "unhealthy"

        self.check_results = results
        return results

    async def check_database(self, db) -> dict[str, Any]:
        """Check database health"""
        try:
            # Simple query to check connection
            result = await db.pool.fetchval("SELECT 1")
            pool_size = db.pool.get_size()

            return {
                "healthy": result == 1,
                "pool_size": pool_size,
                "message": "Database connection is healthy",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "message": "Database connection failed"}

    async def check_redis(self, redis_url: str) -> dict[str, Any]:
        """Check Redis health"""
        if not HAS_REDIS:
            return {
                "healthy": False,
                "error": "redis not installed",
                "message": "Redis monitoring unavailable",
            }

        try:
            client = redis.from_url(redis_url)
            await client.ping()
            info = await client.info()
            await client.close()

            return {
                "healthy": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": info.get("used_memory", 0) / 1024 / 1024,
                "message": "Redis connection is healthy",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "message": "Redis connection failed"}

    async def check_disk_space(self, min_free_gb: float = 1.0) -> dict[str, Any]:
        """Check disk space"""
        try:
            disk = psutil.disk_usage("/")
            free_gb = disk.free / 1024 / 1024 / 1024

            return {
                "healthy": free_gb >= min_free_gb,
                "free_gb": round(free_gb, 2),
                "used_percent": disk.percent,
                "message": f"Disk space: {free_gb:.2f}GB free",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "message": "Disk space check failed"}


class RequestTracker:
    """Tracks request metrics and performance"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.active_requests = 0
        self.request_history = deque(maxlen=1000)

    async def track_request(self, request, call_next):
        """Middleware to track requests"""
        # Increment active requests
        self.active_requests += 1

        # Start timing
        start_time = time.time()

        # Get request details
        method = request.method
        path = request.url.path

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            status = response.status_code

            # Update metrics
            self.metrics.request_count.labels(
                method=method, endpoint=path, status=str(status)
            ).inc()

            self.metrics.request_duration.labels(method=method, endpoint=path).observe(duration)

            # Record in history
            self.request_history.append(
                {
                    "timestamp": start_time,
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": duration * 1000,
                }
            )

            # Add metrics headers
            response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

            return response

        except Exception as e:
            # Record error
            duration = time.time() - start_time
            self.metrics.error_count.labels(error_type=type(e).__name__, endpoint=path).inc()

            raise

        finally:
            # Decrement active requests
            self.active_requests -= 1


# Global instances
_metrics_collector: MetricsCollector | None = None
_health_checker: HealthChecker | None = None
_request_tracker: RequestTracker | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_checker() -> HealthChecker:
    """Get the global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def get_request_tracker() -> RequestTracker:
    """Get the global request tracker"""
    global _request_tracker
    if _request_tracker is None:
        _request_tracker = RequestTracker(get_metrics_collector())
    return _request_tracker


async def export_metrics() -> Response:
    """Export metrics in Prometheus format"""
    metrics_output = generate_latest()
    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


# Monitoring decorators
def monitor_performance(operation: str):
    """Decorator to monitor function performance"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = get_metrics_collector()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Record success
                metrics.observe_histogram(
                    "operation_duration", duration, operation=operation, status="success"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Record failure
                metrics.observe_histogram(
                    "operation_duration", duration, operation=operation, status="failure"
                )

                metrics.increment_counter(
                    "operation_errors", operation=operation, error_type=type(e).__name__
                )

                raise

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = get_metrics_collector()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Record success
                metrics.observe_histogram(
                    "operation_duration", duration, operation=operation, status="success"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Record failure
                metrics.observe_histogram(
                    "operation_duration", duration, operation=operation, status="failure"
                )

                metrics.increment_counter(
                    "operation_errors", operation=operation, error_type=type(e).__name__
                )

                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
