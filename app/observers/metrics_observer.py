"""
Metrics observer implementation for performance monitoring.

Observes system changes and collects performance metrics
for monitoring and analytics purposes.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import Any, Deque, Optional

from .observable import ChangeNotification, ChangeType, Observer

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'timestamp': self.timestamp,
            'value': self.value,
            'tags': self.tags,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    name: str
    count: int
    sum_value: float
    min_value: float
    max_value: float
    avg_value: float
    median_value: float
    last_value: float
    last_updated: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'count': self.count,
            'sum': self.sum_value,
            'min': self.min_value,
            'max': self.max_value,
            'avg': self.avg_value,
            'median': self.median_value,
            'last_value': self.last_value,
            'last_updated': self.last_updated,
            'last_updated_datetime': datetime.fromtimestamp(self.last_updated).isoformat()
        }


class MetricsCollector:
    """
    Collects and aggregates metrics data.

    Provides time-series data collection with configurable retention
    and automatic aggregation of statistics.
    """

    def __init__(self, retention_hours: int = 24, max_points_per_metric: int = 10000):
        self.retention_hours = retention_hours
        self.max_points_per_metric = max_points_per_metric

        # Storage for metrics
        self._metrics: dict[str, Deque[MetricPoint]] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self._metric_summaries: dict[str, MetricSummary] = {}

        # Configuration
        self._aggregation_window = 60  # seconds
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 1 hour

        # Stats
        self._stats = {
            'total_points_collected': 0,
            'metrics_count': 0,
            'last_cleanup': self._last_cleanup
        }

    def record_metric(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        """
        Record a single metric point.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        timestamp = time.time()
        point = MetricPoint(
            timestamp=timestamp,
            value=value,
            tags=tags or {}
        )

        # Add to time series
        self._metrics[name].append(point)

        # Update summary
        self._update_summary(name, point)

        # Update stats
        self._stats['total_points_collected'] += 1
        self._stats['metrics_count'] = len(self._metrics)

        # Periodic cleanup
        if timestamp - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_data()

    def _update_summary(self, name: str, point: MetricPoint) -> None:
        """Update summary statistics for a metric."""
        if name not in self._metric_summaries:
            self._metric_summaries[name] = MetricSummary(
                name=name,
                count=1,
                sum_value=point.value,
                min_value=point.value,
                max_value=point.value,
                avg_value=point.value,
                median_value=point.value,
                last_value=point.value,
                last_updated=point.timestamp
            )
        else:
            summary = self._metric_summaries[name]
            summary.count += 1
            summary.sum_value += point.value
            summary.min_value = min(summary.min_value, point.value)
            summary.max_value = max(summary.max_value, point.value)
            summary.avg_value = summary.sum_value / summary.count
            summary.last_value = point.value
            summary.last_updated = point.timestamp

            # Calculate median from recent data (performance optimization)
            recent_points = list(self._metrics[name])[-100:]  # Last 100 points
            if recent_points:
                summary.median_value = median([p.value for p in recent_points])

    def get_metric_points(self, name: str, since: Optional[float] = None) -> list[MetricPoint]:
        """
        Get metric points for a specific metric.

        Args:
            name: Metric name
            since: Optional timestamp to filter points from

        Returns:
            List of metric points
        """
        points = list(self._metrics.get(name, []))

        if since is not None:
            points = [p for p in points if p.timestamp >= since]

        return points

    def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """Get summary statistics for a metric."""
        return self._metric_summaries.get(name)

    def get_all_summaries(self) -> dict[str, MetricSummary]:
        """Get summary statistics for all metrics."""
        return self._metric_summaries.copy()

    def get_metric_names(self) -> list[str]:
        """Get all metric names."""
        return list(self._metrics.keys())

    def _cleanup_old_data(self) -> None:
        """Remove old metric data based on retention policy."""
        cutoff_time = time.time() - (self.retention_hours * 3600)
        cleaned_metrics = 0
        cleaned_points = 0

        for metric_name, points in list(self._metrics.items()):
            original_count = len(points)

            # Remove old points
            while points and points[0].timestamp < cutoff_time:
                points.popleft()
                cleaned_points += 1

            # Remove empty metrics
            if not points:
                del self._metrics[metric_name]
                if metric_name in self._metric_summaries:
                    del self._metric_summaries[metric_name]
                cleaned_metrics += 1

        self._last_cleanup = time.time()
        self._stats['last_cleanup'] = self._last_cleanup
        self._stats['metrics_count'] = len(self._metrics)

        if cleaned_points > 0:
            logger.debug(f"Cleaned up {cleaned_points} old metric points from {cleaned_metrics} metrics")

    def get_stats(self) -> dict[str, Any]:
        """Get collector statistics."""
        return {
            'total_points_collected': self._stats['total_points_collected'],
            'metrics_count': self._stats['metrics_count'],
            'last_cleanup': self._stats['last_cleanup'],
            'retention_hours': self.retention_hours,
            'max_points_per_metric': self.max_points_per_metric
        }


class MetricsObserver(Observer):
    """
    Observer that collects metrics from change notifications.

    Automatically tracks various performance and usage metrics
    based on system changes and events.
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or MetricsCollector()
        self._start_time = time.time()

        # Metric names
        self.CHANGE_COUNT_METRIC = "system.changes.count"
        self.CHANGE_LATENCY_METRIC = "system.changes.latency"
        self.ENTITY_COUNT_METRIC = "system.entities.count"
        self.OPERATION_DURATION_METRIC = "system.operation.duration"

        # Counters for different change types
        self._change_counters: dict[ChangeType, int] = defaultdict(int)
        self._entity_counters: dict[str, int] = defaultdict(int)

    async def on_change(self, notification: ChangeNotification) -> None:
        """Collect metrics from change notifications."""
        current_time = time.time()

        # Calculate latency (time since notification was created)
        latency = current_time - notification.timestamp

        # Common tags
        base_tags = {
            'change_type': notification.change_type.value,
            'entity_type': notification.entity_type
        }

        # Record change count metric
        self.metrics_collector.record_metric(
            self.CHANGE_COUNT_METRIC,
            1.0,
            base_tags
        )

        # Record latency metric
        self.metrics_collector.record_metric(
            self.CHANGE_LATENCY_METRIC,
            latency * 1000,  # Convert to milliseconds
            base_tags
        )

        # Update counters
        self._change_counters[notification.change_type] += 1
        self._entity_counters[notification.entity_type] += 1

        # Record entity count changes
        if notification.change_type == ChangeType.CREATED:
            self.metrics_collector.record_metric(
                self.ENTITY_COUNT_METRIC,
                1.0,
                {**base_tags, 'operation': 'increment'}
            )
        elif notification.change_type == ChangeType.DELETED:
            self.metrics_collector.record_metric(
                self.ENTITY_COUNT_METRIC,
                -1.0,
                {**base_tags, 'operation': 'decrement'}
            )

        # Record operation duration if available in metadata
        if 'duration_ms' in notification.metadata:
            duration = notification.metadata['duration_ms']
            self.metrics_collector.record_metric(
                self.OPERATION_DURATION_METRIC,
                duration,
                {**base_tags, 'operation': notification.metadata.get('operation', 'unknown')}
            )

        # Record custom metrics from metadata
        await self._record_custom_metrics(notification, base_tags)

    async def _record_custom_metrics(self, notification: ChangeNotification, base_tags: dict[str, str]) -> None:
        """Record custom metrics from notification metadata."""
        metadata = notification.metadata

        # Record any numeric values in metadata as metrics
        for key, value in metadata.items():
            if isinstance(value, (int, float)) and key.endswith('_metric'):
                metric_name = f"custom.{key[:-7]}"  # Remove '_metric' suffix
                self.metrics_collector.record_metric(
                    metric_name,
                    float(value),
                    base_tags
                )

        # Record specific domain metrics
        if notification.entity_type == 'memory':
            await self._record_memory_metrics(notification, base_tags)
        elif notification.entity_type == 'session':
            await self._record_session_metrics(notification, base_tags)

    async def _record_memory_metrics(self, notification: ChangeNotification, base_tags: dict[str, str]) -> None:
        """Record memory-specific metrics."""
        metadata = notification.metadata

        # Memory importance score
        if 'importance_score' in metadata:
            self.metrics_collector.record_metric(
                "memory.importance_score",
                metadata['importance_score'],
                base_tags
            )

        # Memory content length
        if 'content_length' in metadata:
            self.metrics_collector.record_metric(
                "memory.content_length",
                metadata['content_length'],
                base_tags
            )

        # Memory access count
        if 'access_count' in metadata:
            self.metrics_collector.record_metric(
                "memory.access_count",
                metadata['access_count'],
                base_tags
            )

    async def _record_session_metrics(self, notification: ChangeNotification, base_tags: dict[str, str]) -> None:
        """Record session-specific metrics."""
        metadata = notification.metadata

        # Session duration
        if 'duration_minutes' in metadata:
            self.metrics_collector.record_metric(
                "session.duration_minutes",
                metadata['duration_minutes'],
                base_tags
            )

        # Active session count
        if notification.change_type == ChangeType.CREATED:
            self.metrics_collector.record_metric(
                "session.active_count",
                1.0,
                {**base_tags, 'operation': 'increment'}
            )
        elif notification.change_type == ChangeType.DELETED:
            self.metrics_collector.record_metric(
                "session.active_count",
                -1.0,
                {**base_tags, 'operation': 'decrement'}
            )

    def get_change_summary(self) -> dict[str, Any]:
        """Get summary of change counts by type."""
        return {
            'change_counts': dict(self._change_counters),
            'entity_counts': dict(self._entity_counters),
            'uptime_seconds': time.time() - self._start_time
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all collected metrics."""
        return {
            'summaries': {name: summary.to_dict() for name, summary in self.metrics_collector.get_all_summaries().items()},
            'collector_stats': self.metrics_collector.get_stats(),
            'change_summary': self.get_change_summary()
        }


class PerformanceMetricsCollector:
    """
    Specialized metrics collector for performance monitoring.

    Focuses on performance-related metrics like response times,
    throughput, error rates, and resource usage.
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or MetricsCollector()
        self._operation_timers: dict[str, float] = {}

        # Performance metric names
        self.RESPONSE_TIME_METRIC = "performance.response_time"
        self.THROUGHPUT_METRIC = "performance.throughput"
        self.ERROR_RATE_METRIC = "performance.error_rate"
        self.CONCURRENCY_METRIC = "performance.concurrency"

        # Counters
        self._operation_counts: dict[str, int] = defaultdict(int)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._active_operations: dict[str, int] = defaultdict(int)

    def start_operation(self, operation_id: str, operation_type: str) -> None:
        """Start timing an operation."""
        self._operation_timers[operation_id] = time.time()
        self._active_operations[operation_type] += 1

        # Record concurrency metric
        self.metrics_collector.record_metric(
            self.CONCURRENCY_METRIC,
            self._active_operations[operation_type],
            {'operation_type': operation_type}
        )

    def end_operation(self, operation_id: str, operation_type: str, success: bool = True) -> float:
        """
        End timing an operation and record metrics.

        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation
            success: Whether operation was successful

        Returns:
            Operation duration in seconds
        """
        if operation_id not in self._operation_timers:
            logger.warning(f"Operation {operation_id} was not started or already ended")
            return 0.0

        start_time = self._operation_timers.pop(operation_id)
        duration = time.time() - start_time

        # Update counters
        self._operation_counts[operation_type] += 1
        if not success:
            self._error_counts[operation_type] += 1

        self._active_operations[operation_type] = max(0, self._active_operations[operation_type] - 1)

        # Record metrics
        tags = {'operation_type': operation_type, 'success': str(success)}

        # Response time
        self.metrics_collector.record_metric(
            self.RESPONSE_TIME_METRIC,
            duration * 1000,  # Convert to milliseconds
            tags
        )

        # Throughput (operations per second)
        self.metrics_collector.record_metric(
            self.THROUGHPUT_METRIC,
            1.0,  # One operation completed
            tags
        )

        # Error rate
        if not success:
            self.metrics_collector.record_metric(
                self.ERROR_RATE_METRIC,
                1.0,
                tags
            )

        # Concurrency
        self.metrics_collector.record_metric(
            self.CONCURRENCY_METRIC,
            self._active_operations[operation_type],
            {'operation_type': operation_type}
        )

        return duration

    def record_error(self, operation_type: str, error_type: str) -> None:
        """Record an error occurrence."""
        self._error_counts[operation_type] += 1

        self.metrics_collector.record_metric(
            self.ERROR_RATE_METRIC,
            1.0,
            {'operation_type': operation_type, 'error_type': error_type}
        )

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance metrics summary."""
        total_operations = sum(self._operation_counts.values())
        total_errors = sum(self._error_counts.values())

        return {
            'total_operations': total_operations,
            'total_errors': total_errors,
            'overall_error_rate': total_errors / max(1, total_operations),
            'operation_counts': dict(self._operation_counts),
            'error_counts': dict(self._error_counts),
            'active_operations': dict(self._active_operations),
            'metrics_summaries': {
                name: summary.to_dict()
                for name, summary in self.metrics_collector.get_all_summaries().items()
                if name.startswith('performance.')
            }
        }


# Global metrics instances
_global_metrics_collector: Optional[MetricsCollector] = None
_global_performance_collector: Optional[PerformanceMetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector


def get_performance_collector() -> PerformanceMetricsCollector:
    """Get the global performance metrics collector instance."""
    global _global_performance_collector
    if _global_performance_collector is None:
        _global_performance_collector = PerformanceMetricsCollector(get_metrics_collector())
    return _global_performance_collector


def create_metrics_observer() -> MetricsObserver:
    """Create a metrics observer with the global collector."""
    return MetricsObserver(get_metrics_collector())
