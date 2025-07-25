"""
Observability infrastructure for monitoring and tracing.

Provides OpenTelemetry, Prometheus metrics, and structured logging.
"""

from .metrics import MetricsCollector, get_metrics_collector
from .tracing import setup_tracing, trace

__all__ = [
    "MetricsCollector",
    "get_metrics_collector",
    "setup_tracing",
    "trace",
]