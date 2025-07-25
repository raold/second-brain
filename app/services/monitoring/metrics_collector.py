"""
Metrics Collector - Prometheus-style metrics from structured logs.

This service converts structured log data into time-series metrics
compatible with Prometheus, Grafana, and other monitoring systems.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Individual metric data point."""
    name: str
    type: MetricType
    value: float
    labels: dict[str, str]
    timestamp: float
    help: str = ""


@dataclass
class HistogramBucket:
    """Histogram bucket for latency metrics."""
    le: float  # Less than or equal to
    count: int


class MetricsCollector:
    """Collects and exports Prometheus-style metrics from logs."""

    def __init__(self):
        # Counters
        self.operation_total = defaultdict(int)
        self.operation_errors = defaultdict(int)
        self.http_requests_total = defaultdict(int)
        self.memory_operations_total = defaultdict(int)

        # Gauges
        self.active_users = set()
        self.active_requests = defaultdict(int)
        self.memory_usage_mb = {}

        # Histograms (duration tracking)
        self.operation_duration_buckets = {
            # Buckets in milliseconds
            "buckets": [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, float('inf')],
            "counts": defaultdict(lambda: defaultdict(int)),
            "sums": defaultdict(float),
            "totals": defaultdict(int)
        }

        # Memory histogram
        self.memory_usage_buckets = {
            "buckets": [1, 5, 10, 25, 50, 100, 250, 500, 1000, float('inf')],
            "counts": defaultdict(lambda: defaultdict(int)),
            "sums": defaultdict(float),
            "totals": defaultdict(int)
        }

        # Time series storage (last hour)
        self.time_series = defaultdict(list)
        self.cleanup_interval = 3600  # 1 hour

    async def record_operation(
        self,
        operation: str,
        duration_ms: Optional[float] = None,
        memory_mb: Optional[float] = None,
        user_id: Optional[str] = None,
        success: bool = True,
        labels: Optional[dict[str, str]] = None
    ):
        """Record an operation metric."""
        base_labels = {"operation": operation}
        if labels:
            base_labels.update(labels)

        # Update counters
        self.operation_total[self._labels_key(base_labels)] += 1

        if not success:
            error_labels = {**base_labels, "type": "error"}
            self.operation_errors[self._labels_key(error_labels)] += 1

        # Track active users
        if user_id:
            self.active_users.add(user_id)

        # Record duration histogram
        if duration_ms is not None:
            self._record_histogram(
                self.operation_duration_buckets,
                base_labels,
                duration_ms
            )

        # Record memory histogram
        if memory_mb is not None:
            self._record_histogram(
                self.memory_usage_buckets,
                base_labels,
                memory_mb
            )

            # Update memory gauge
            self.memory_usage_mb[operation] = memory_mb

        # Add to time series
        timestamp = time.time()
        self.time_series[operation].append({
            "timestamp": timestamp,
            "duration_ms": duration_ms,
            "memory_mb": memory_mb,
            "success": success,
            "user_id": user_id
        })

        # Cleanup old time series data
        await self._cleanup_time_series()

    async def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None
    ):
        """Record HTTP request metrics."""
        labels = {
            "method": method,
            "path": path,
            "status": str(status_code),
            "status_class": f"{status_code // 100}xx"
        }

        key = self._labels_key(labels)
        self.http_requests_total[key] += 1

        # Record duration
        await self.record_operation(
            operation="http_request",
            duration_ms=duration_ms,
            user_id=user_id,
            success=status_code < 400,
            labels=labels
        )

    async def record_memory_operation(
        self,
        operation_type: str,
        memory_type: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None
    ):
        """Record memory-specific operations."""
        labels = {
            "operation_type": operation_type,
            "memory_type": memory_type
        }

        key = self._labels_key(labels)
        self.memory_operations_total[key] += 1

        await self.record_operation(
            operation=f"memory_{operation_type}",
            duration_ms=duration_ms,
            user_id=user_id,
            success=success,
            labels=labels
        )

    def _record_histogram(
        self,
        histogram: dict[str, Any],
        labels: dict[str, str],
        value: float
    ):
        """Record value in histogram buckets."""
        labels_key = self._labels_key(labels)

        # Update buckets
        for bucket in histogram["buckets"]:
            if value <= bucket:
                histogram["counts"][labels_key][bucket] += 1

        # Update sum and count
        histogram["sums"][labels_key] += value
        histogram["totals"][labels_key] += 1

    def _labels_key(self, labels: dict[str, str]) -> str:
        """Create consistent key from labels."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    async def _cleanup_time_series(self):
        """Remove old time series data."""
        cutoff = time.time() - self.cleanup_interval

        for operation in list(self.time_series.keys()):
            series = self.time_series[operation]
            # Keep only recent data
            self.time_series[operation] = [
                point for point in series
                if point["timestamp"] > cutoff
            ]

            # Remove empty series
            if not self.time_series[operation]:
                del self.time_series[operation]

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Operation counters
        lines.append("# HELP second_brain_operations_total Total operations performed")
        lines.append("# TYPE second_brain_operations_total counter")
        for labels_key, count in self.operation_total.items():
            lines.append(f"second_brain_operations_total{{{labels_key}}} {count}")

        # Error counters
        lines.append("# HELP second_brain_operation_errors_total Total operation errors")
        lines.append("# TYPE second_brain_operation_errors_total counter")
        for labels_key, count in self.operation_errors.items():
            lines.append(f"second_brain_operation_errors_total{{{labels_key}}} {count}")

        # HTTP request counters
        lines.append("# HELP second_brain_http_requests_total Total HTTP requests")
        lines.append("# TYPE second_brain_http_requests_total counter")
        for labels_key, count in self.http_requests_total.items():
            lines.append(f"second_brain_http_requests_total{{{labels_key}}} {count}")

        # Active users gauge
        lines.append("# HELP second_brain_active_users Number of active users")
        lines.append("# TYPE second_brain_active_users gauge")
        lines.append(f"second_brain_active_users {len(self.active_users)}")

        # Memory usage gauge
        lines.append("# HELP second_brain_memory_usage_mb Current memory usage by operation")
        lines.append("# TYPE second_brain_memory_usage_mb gauge")
        for operation, memory_mb in self.memory_usage_mb.items():
            lines.append(f"second_brain_memory_usage_mb{{operation=\"{operation}\"}} {memory_mb}")

        # Duration histograms
        lines.append("# HELP second_brain_operation_duration_ms Operation duration in milliseconds")
        lines.append("# TYPE second_brain_operation_duration_ms histogram")
        self._add_histogram_metrics(lines, "second_brain_operation_duration_ms", self.operation_duration_buckets)

        # Memory histograms
        lines.append("# HELP second_brain_memory_allocation_mb Memory allocation in MB")
        lines.append("# TYPE second_brain_memory_allocation_mb histogram")
        self._add_histogram_metrics(lines, "second_brain_memory_allocation_mb", self.memory_usage_buckets)

        return "\n".join(lines)

    def _add_histogram_metrics(self, lines: list[str], metric_name: str, histogram: dict[str, Any]):
        """Add histogram metrics to Prometheus output."""
        # Buckets
        for labels_key, bucket_counts in histogram["counts"].items():
            for bucket, count in bucket_counts.items():
                le_value = "+Inf" if bucket == float('inf') else str(bucket)
                lines.append(f"{metric_name}_bucket{{{labels_key},le=\"{le_value}\"}} {count}")

        # Sums
        for labels_key, sum_value in histogram["sums"].items():
            lines.append(f"{metric_name}_sum{{{labels_key}}} {sum_value}")

        # Counts
        for labels_key, total in histogram["totals"].items():
            lines.append(f"{metric_name}_count{{{labels_key}}} {total}")

    def get_json_metrics(self) -> dict[str, Any]:
        """Export metrics in JSON format for internal dashboards."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "counters": {
                "operations_total": dict(self.operation_total),
                "operation_errors": dict(self.operation_errors),
                "http_requests_total": dict(self.http_requests_total),
                "memory_operations_total": dict(self.memory_operations_total)
            },
            "gauges": {
                "active_users": len(self.active_users),
                "memory_usage_mb": dict(self.memory_usage_mb)
            },
            "histograms": {
                "operation_duration": {
                    "buckets": self.operation_duration_buckets["buckets"],
                    "counts": dict(self.operation_duration_buckets["counts"]),
                    "sums": dict(self.operation_duration_buckets["sums"]),
                    "totals": dict(self.operation_duration_buckets["totals"])
                },
                "memory_allocation": {
                    "buckets": self.memory_usage_buckets["buckets"],
                    "counts": dict(self.memory_usage_buckets["counts"]),
                    "sums": dict(self.memory_usage_buckets["sums"]),
                    "totals": dict(self.memory_usage_buckets["totals"])
                }
            },
            "time_series": dict(self.time_series)
        }

    def get_summary_stats(self) -> dict[str, Any]:
        """Get high-level summary statistics."""
        total_operations = sum(self.operation_total.values())
        total_errors = sum(self.operation_errors.values())
        error_rate = total_errors / total_operations if total_operations > 0 else 0

        # Calculate average durations
        avg_durations = {}
        for labels_key, total_time in self.operation_duration_buckets["sums"].items():
            count = self.operation_duration_buckets["totals"][labels_key]
            if count > 0:
                avg_durations[labels_key] = total_time / count

        return {
            "total_operations": total_operations,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "active_users": len(self.active_users),
            "tracked_operations": len(self.time_series),
            "avg_durations": avg_durations,
            "current_memory_usage": dict(self.memory_usage_mb)
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
