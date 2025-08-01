import logging
import time

from app.services.monitoring.metrics_collector import MetricsCollector

"""
Monitoring services for Second Brain.

Provides real-time monitoring, alerting, and analytics capabilities
based on structured logging.
"""

from .log_analytics import (
    Alert,
    AlertLevel,
    LogAnalyticsService,
    PerformanceMetrics,
    get_analytics_service,
    start_log_monitoring,
    stop_log_monitoring,
)
from .metrics_collector import MetricsCollector, MetricType, get_metrics_collector

__all__ = [
    "LogAnalyticsService",
    "Alert",
    "AlertLevel",
    "PerformanceMetrics",
    "get_analytics_service",
    "start_log_monitoring",
    "stop_log_monitoring",
    "MetricsCollector",
    "MetricType",
    "get_metrics_collector",
]
