"""
Prometheus metrics collection.

Provides custom metrics for monitoring application performance.
"""

import time
from typing import Any, Callable, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Application info
app_info = Info(
    "secondbrain_app",
    "Application information",
)

# Request metrics
request_count = Counter(
    "secondbrain_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)

request_duration = Histogram(
    "secondbrain_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

# Memory metrics
memory_count = Gauge(
    "secondbrain_memories_total",
    "Total number of memories",
    ["user_id", "memory_type"],
)

memory_operations = Counter(
    "secondbrain_memory_operations_total",
    "Total number of memory operations",
    ["operation", "status"],
)

memory_operation_duration = Histogram(
    "secondbrain_memory_operation_duration_seconds",
    "Memory operation duration in seconds",
    ["operation"],
)

# Search metrics
search_requests = Counter(
    "secondbrain_search_requests_total",
    "Total number of search requests",
    ["search_type"],
)

search_duration = Histogram(
    "secondbrain_search_duration_seconds",
    "Search duration in seconds",
    ["search_type"],
)

search_results = Summary(
    "secondbrain_search_results_count",
    "Number of search results returned",
    ["search_type"],
)

# Event metrics
events_published = Counter(
    "secondbrain_events_published_total",
    "Total number of events published",
    ["event_type"],
)

events_processed = Counter(
    "secondbrain_events_processed_total",
    "Total number of events processed",
    ["event_type", "status"],
)

event_processing_duration = Histogram(
    "secondbrain_event_processing_duration_seconds",
    "Event processing duration in seconds",
    ["event_type"],
)

# Cache metrics
cache_hits = Counter(
    "secondbrain_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],
)

cache_misses = Counter(
    "secondbrain_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
)

# Database metrics
db_connections = Gauge(
    "secondbrain_db_connections_active",
    "Number of active database connections",
)

db_queries = Counter(
    "secondbrain_db_queries_total",
    "Total number of database queries",
    ["query_type"],
)

db_query_duration = Histogram(
    "secondbrain_db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
)


class MetricsCollector:
    """Collects and exposes Prometheus metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        # Set application info
        app_info.info({
            "version": "3.0.0",
            "environment": "production",
        })
    
    def track_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
    ) -> None:
        """Track HTTP request metrics."""
        request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def track_memory_operation(
        self,
        operation: str,
        status: str,
        duration: float,
    ) -> None:
        """Track memory operation metrics."""
        memory_operations.labels(operation=operation, status=status).inc()
        memory_operation_duration.labels(operation=operation).observe(duration)
    
    def track_search(
        self,
        search_type: str,
        duration: float,
        result_count: int,
    ) -> None:
        """Track search metrics."""
        search_requests.labels(search_type=search_type).inc()
        search_duration.labels(search_type=search_type).observe(duration)
        search_results.labels(search_type=search_type).observe(result_count)
    
    def track_event(
        self,
        event_type: str,
        operation: str,
        status: str = "success",
        duration: Optional[float] = None,
    ) -> None:
        """Track event metrics."""
        if operation == "published":
            events_published.labels(event_type=event_type).inc()
        elif operation == "processed":
            events_processed.labels(event_type=event_type, status=status).inc()
            if duration:
                event_processing_duration.labels(event_type=event_type).observe(duration)
    
    def track_cache(
        self,
        cache_type: str,
        hit: bool,
    ) -> None:
        """Track cache metrics."""
        if hit:
            cache_hits.labels(cache_type=cache_type).inc()
        else:
            cache_misses.labels(cache_type=cache_type).inc()
    
    def track_database(
        self,
        query_type: str,
        duration: float,
    ) -> None:
        """Track database metrics."""
        db_queries.labels(query_type=query_type).inc()
        db_query_duration.labels(query_type=query_type).observe(duration)
    
    def set_memory_count(
        self,
        user_id: str,
        memory_type: str,
        count: int,
    ) -> None:
        """Set memory count gauge."""
        memory_count.labels(user_id=user_id, memory_type=memory_type).set(count)
    
    def set_db_connections(self, count: int) -> None:
        """Set database connection count."""
        db_connections.set(count)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest()


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector instance."""
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    
    return _metrics_collector


def timed_operation(
    operation_type: str,
    metric_func: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to time operations and record metrics.
    
    Args:
        operation_type: Type of operation
        metric_func: Function to call with duration
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if metric_func:
                    metric_func(operation_type, "success", duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                if metric_func:
                    metric_func(operation_type, "error", duration)
                
                raise
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if metric_func:
                    metric_func(operation_type, "success", duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                if metric_func:
                    metric_func(operation_type, "error", duration)
                
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator