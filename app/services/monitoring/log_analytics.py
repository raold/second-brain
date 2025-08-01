import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.utils.logging_config import get_logger

"""
Log Analytics Service - Real-time monitoring using structured logs.

This service processes structured logs to provide real-time monitoring,
alerting, and performance analytics.
"""

from collections import defaultdict, deque
from collections.abc import Callable
from enum import Enum

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogMetric:
    """Structured log metric."""

    timestamp: datetime
    level: str
    operation: str
    duration_ms: float | None = None
    memory_mb: float | None = None
    user_id: str | None = None
    request_id: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """System alert based on log analysis."""

    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source_operation: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics aggregated from logs."""

    operation: str
    avg_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    total_calls: int
    error_rate: float
    avg_memory_mb: float
    last_updated: datetime


class LogAnalyticsService:
    """Service for real-time log analytics and monitoring."""

    def __init__(self):
        self.metrics_buffer: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.alerts: list[Alert] = []
        self.performance_cache: dict[str, PerformanceMetrics] = {}
        self.alert_handlers: list[Callable[[Alert], None]] = []

        # Real-time counters
        self.error_counts = defaultdict(int)
        self.operation_counts = defaultdict(int)
        self.user_activity = defaultdict(int)

        # Performance thresholds
        self.performance_thresholds = {
            "memory_synthesis": {"duration_ms": 5000, "memory_mb": 500},
            "graph_generation": {"duration_ms": 3000, "memory_mb": 300},
            "memory_search": {"duration_ms": 1000, "memory_mb": 100},
            "memory_creation": {"duration_ms": 500, "memory_mb": 50},
        }

        # Background processing
        self._processing = False
        self._processor_task: asyncio.Task | None = None

    async def start_monitoring(self):
        """Start real-time log monitoring."""
        if self._processing:
            return

        logger.info("Starting log analytics monitoring")
        self._processing = True
        self._processor_task = asyncio.create_task(self._process_metrics_loop())

        # Set up log handler to capture structured logs
        self._setup_log_handler()

    async def stop_monitoring(self):
        """Stop log monitoring."""
        if not self._processing:
            return

        logger.info("Stopping log analytics monitoring")
        self._processing = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

    def _setup_log_handler(self):
        """Set up custom log handler to capture structured logs."""
        handler = StructuredLogHandler(self)

        # Add to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        logger.info("Structured log handler installed for monitoring")

    async def process_log_metric(self, metric: LogMetric):
        """Process a single log metric."""
        # Add to buffer
        self.metrics_buffer.append(metric)

        # Update counters
        self.operation_counts[metric.operation] += 1
        if metric.level in ["ERROR", "CRITICAL"]:
            self.error_counts[metric.operation] += 1
        if metric.user_id:
            self.user_activity[metric.user_id] += 1

        # Check for alerts
        await self._check_alerts(metric)

        # Update performance metrics
        await self._update_performance_metrics(metric)

    async def _check_alerts(self, metric: LogMetric):
        """Check if metric triggers any alerts."""
        alerts = []

        # Performance threshold alerts
        if metric.duration_ms and metric.operation in self.performance_thresholds:
            threshold = self.performance_thresholds[metric.operation]["duration_ms"]
            if metric.duration_ms > threshold:
                alerts.append(
                    Alert(
                        id=f"perf_{metric.operation}_{int(time.time())}",
                        level=AlertLevel.WARNING,
                        title=f"Slow {metric.operation}",
                        message=f"Operation took {metric.duration_ms:.1f}ms (threshold: {threshold}ms)",
                        timestamp=metric.timestamp,
                        source_operation=metric.operation,
                        context={
                            "duration_ms": metric.duration_ms,
                            "threshold_ms": threshold,
                            "user_id": metric.user_id,
                            "request_id": metric.request_id,
                        },
                    )
                )

        # Memory usage alerts
        if metric.memory_mb and metric.operation in self.performance_thresholds:
            threshold = self.performance_thresholds[metric.operation]["memory_mb"]
            if metric.memory_mb > threshold:
                alerts.append(
                    Alert(
                        id=f"mem_{metric.operation}_{int(time.time())}",
                        level=AlertLevel.WARNING,
                        title=f"High memory usage in {metric.operation}",
                        message=f"Operation used {metric.memory_mb:.1f}MB (threshold: {threshold}MB)",
                        timestamp=metric.timestamp,
                        source_operation=metric.operation,
                        context={
                            "memory_mb": metric.memory_mb,
                            "threshold_mb": threshold,
                            "user_id": metric.user_id,
                            "request_id": metric.request_id,
                        },
                    )
                )

        # Error rate alerts
        error_rate = self._calculate_error_rate(metric.operation)
        if error_rate > 0.1:  # 10% error rate
            alerts.append(
                Alert(
                    id=f"error_{metric.operation}_{int(time.time())}",
                    level=AlertLevel.ERROR,
                    title=f"High error rate in {metric.operation}",
                    message=f"Error rate: {error_rate:.1%}",
                    timestamp=metric.timestamp,
                    source_operation=metric.operation,
                    context={"error_rate": error_rate},
                )
            )

        # Process alerts
        for alert in alerts:
            await self._handle_alert(alert)

    async def _update_performance_metrics(self, metric: LogMetric):
        """Update performance metrics for operation."""
        if not metric.duration_ms:
            return

        operation = metric.operation

        # Get recent metrics for this operation
        recent_metrics = [
            m
            for m in self.metrics_buffer
            if m.operation == operation
            and m.duration_ms is not None
            and (datetime.utcnow() - m.timestamp) < timedelta(minutes=5)
        ]

        if len(recent_metrics) < 2:
            return

        # Calculate performance metrics
        durations = [m.duration_ms for m in recent_metrics]
        durations.sort()

        avg_duration = sum(durations) / len(durations)
        p95_duration = durations[int(len(durations) * 0.95)]
        p99_duration = durations[int(len(durations) * 0.99)]

        error_count = sum(1 for m in recent_metrics if m.level in ["ERROR", "CRITICAL"])
        error_rate = error_count / len(recent_metrics)

        memory_values = [m.memory_mb for m in recent_metrics if m.memory_mb is not None]
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0

        # Update cache
        self.performance_cache[operation] = PerformanceMetrics(
            operation=operation,
            avg_duration_ms=avg_duration,
            p95_duration_ms=p95_duration,
            p99_duration_ms=p99_duration,
            total_calls=len(recent_metrics),
            error_rate=error_rate,
            avg_memory_mb=avg_memory,
            last_updated=datetime.utcnow(),
        )

    def _calculate_error_rate(self, operation: str) -> float:
        """Calculate recent error rate for operation."""
        total = self.operation_counts[operation]
        errors = self.error_counts[operation]
        return errors / total if total > 0 else 0

    async def _handle_alert(self, alert: Alert):
        """Handle generated alert."""
        self.alerts.append(alert)

        # Keep only recent alerts (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]

        # Log the alert
        logger.warning(
            "System alert generated",
            extra={
                "alert_id": alert.id,
                "alert_level": alert.level,
                "alert_title": alert.title,
                "alert_message": alert.message,
                "source_operation": alert.source_operation,
                "alert_context": alert.context,
            },
        )

        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(
                    "Alert handler failed",
                    extra={"handler": str(handler), "error": str(e), "alert_id": alert.id},
                )

    async def _process_metrics_loop(self):
        """Background loop for processing metrics."""
        while self._processing:
            try:
                # Clean old metrics
                cutoff = datetime.utcnow() - timedelta(hours=1)
                old_count = len(self.metrics_buffer)
                self.metrics_buffer = deque(
                    [m for m in self.metrics_buffer if m.timestamp > cutoff], maxlen=10000
                )
                new_count = len(self.metrics_buffer)

                if old_count != new_count:
                    logger.debug(
                        "Cleaned old metrics",
                        extra={
                            "removed_count": old_count - new_count,
                            "remaining_count": new_count,
                        },
                    )

                # Sleep before next iteration
                await asyncio.sleep(60)  # Process every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    "Error in metrics processing loop", extra={"error_type": type(e).__name__}
                )
                await asyncio.sleep(10)  # Short sleep on error

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add custom alert handler."""
        self.alert_handlers.append(handler)
        logger.info("Alert handler added", extra={"handler_count": len(self.alert_handlers)})

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get current dashboard data."""
        now = datetime.utcnow()

        # Recent activity (last 5 minutes)
        recent_cutoff = now - timedelta(minutes=5)
        recent_metrics = [m for m in self.metrics_buffer if m.timestamp > recent_cutoff]

        # Operation breakdown
        operation_stats = defaultdict(lambda: {"count": 0, "errors": 0, "avg_duration": 0})
        for metric in recent_metrics:
            stats = operation_stats[metric.operation]
            stats["count"] += 1
            if metric.level in ["ERROR", "CRITICAL"]:
                stats["errors"] += 1
            if metric.duration_ms:
                current_avg = stats["avg_duration"]
                stats["avg_duration"] = (
                    current_avg * (stats["count"] - 1) + metric.duration_ms
                ) / stats["count"]

        # Active alerts
        active_alerts = [a for a in self.alerts if (now - a.timestamp) < timedelta(minutes=30)]

        return {
            "timestamp": now.isoformat(),
            "metrics_count": len(self.metrics_buffer),
            "recent_activity": {
                "total_operations": len(recent_metrics),
                "unique_operations": len(operation_stats),
                "error_count": sum(stats["errors"] for stats in operation_stats.values()),
                "active_users": len(set(m.user_id for m in recent_metrics if m.user_id)),
            },
            "operation_stats": dict(operation_stats),
            "performance_metrics": {
                op: {
                    "avg_duration_ms": metrics.avg_duration_ms,
                    "p95_duration_ms": metrics.p95_duration_ms,
                    "error_rate": metrics.error_rate,
                    "total_calls": metrics.total_calls,
                }
                for op, metrics in self.performance_cache.items()
            },
            "active_alerts": [
                {
                    "id": alert.id,
                    "level": alert.level,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "operation": alert.source_operation,
                }
                for alert in active_alerts
            ],
        }


class StructuredLogHandler(logging.Handler):
    """Custom log handler to extract structured data from logs."""

    def __init__(self, analytics_service: LogAnalyticsService):
        super().__init__()
        self.analytics_service = analytics_service

    def emit(self, record: logging.LogRecord):
        """Process log record for analytics."""
        try:
            # Only process logs with structured data
            if not hasattr(record, "extra_data"):
                return

            # Extract structured data
            extra_data = getattr(record, "extra_data", {})

            metric = LogMetric(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                operation=extra_data.get("operation", "unknown"),
                duration_ms=extra_data.get("duration_ms"),
                memory_mb=extra_data.get("memory_mb"),
                user_id=extra_data.get("user_id"),
                request_id=extra_data.get("request_id"),
                extra_data=extra_data,
            )

            # Process asynchronously
            asyncio.create_task(self.analytics_service.process_log_metric(metric))

        except Exception:
            # Silently ignore errors in log processing to avoid log loops
            pass


# Global analytics service instance
_analytics_service: LogAnalyticsService | None = None


def get_analytics_service() -> LogAnalyticsService:
    """Get global analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = LogAnalyticsService()
    return _analytics_service


async def start_log_monitoring():
    """Start global log monitoring."""
    service = get_analytics_service()
    await service.start_monitoring()


async def stop_log_monitoring():
    """Stop global log monitoring."""
    service = get_analytics_service()
    await service.stop_monitoring()
