"""
Bulk Operations Performance Optimizer

Provides advanced performance optimization for bulk memory operations:
- Intelligent connection pooling and management
- Parallel processing with dynamic worker scaling
- Memory-efficient streaming and batching
- Advanced caching and prefetching
- Performance monitoring and auto-tuning
- Resource utilization optimization
"""

import asyncio
import logging
import time
import psutil
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import asyncpg
from concurrent.futures import ThreadPoolExecutor
import weakref
import gc

from .bulk_memory_operations import BulkMemoryItem, BulkOperationConfig

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Performance optimization levels."""
    CONSERVATIVE = "conservative"   # Safe, minimal optimizations
    BALANCED = "balanced"          # Balanced performance and stability
    AGGRESSIVE = "aggressive"      # Maximum performance
    ADAPTIVE = "adaptive"          # Auto-adapting based on load


class ResourceType(Enum):
    """System resource types to monitor."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_CONNECTIONS = "database_connections"


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    operation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    items_per_second: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    database_connections_used: int = 0
    cache_hit_rate: float = 0.0
    batch_processing_time: List[float] = None
    parallel_worker_efficiency: float = 0.0
    network_throughput_mbps: float = 0.0
    
    def __post_init__(self):
        if self.batch_processing_time is None:
            self.batch_processing_time = []


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED
    
    # Connection pooling
    min_connections: int = 5
    max_connections: int = 50
    connection_timeout: float = 30.0
    connection_idle_timeout: float = 600.0
    
    # Parallel processing
    min_workers: int = 2
    max_workers: int = 16
    worker_scaling_factor: float = 1.5
    worker_idle_timeout: float = 120.0
    
    # Memory management
    max_memory_usage_mb: int = 2048
    batch_size_auto_adjust: bool = True
    memory_pressure_threshold: float = 0.8
    gc_threshold: int = 1000
    
    # Caching
    enable_caching: bool = True
    cache_size_mb: int = 256
    cache_ttl_seconds: int = 3600
    prefetch_enabled: bool = True
    
    # Monitoring
    metrics_collection_interval: float = 1.0
    performance_logging: bool = True
    auto_tuning_enabled: bool = True
    
    # Resource limits
    cpu_usage_limit: float = 80.0
    memory_usage_limit: float = 85.0
    disk_io_limit_mbps: float = 500.0


class ConnectionPoolManager:
    """
    Advanced database connection pool management.
    
    Features:
    - Dynamic pool sizing
    - Connection health monitoring
    - Load balancing across connections
    - Connection warmup and keepalive
    """
    
    def __init__(self, config: OptimizationConfig, database_url: str):
        self.config = config
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_metrics = {}
        self.pool_created_at = None
        self.active_connections = 0
        self.peak_connections = 0
        
    async def initialize_pool(self):
        """Initialize the connection pool with optimization."""
        try:
            # Calculate optimal pool size based on system resources
            cpu_count = psutil.cpu_count()
            optimal_connections = min(
                max(self.config.min_connections, cpu_count * 2),
                self.config.max_connections
            )
            
            logger.info(f"Initializing connection pool: {optimal_connections} connections")
            
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.config.min_connections,
                max_size=optimal_connections,
                command_timeout=self.config.connection_timeout,
                max_inactive_connection_lifetime=self.config.connection_idle_timeout,
                setup=self._setup_connection,
                init=self._init_connection
            )
            
            self.pool_created_at = datetime.now()
            logger.info("Connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    async def _setup_connection(self, connection):
        """Setup individual connection with optimizations."""
        # Set connection-level optimizations
        await connection.execute("SET synchronous_commit = off")
        await connection.execute("SET wal_writer_delay = 200ms")
        await connection.execute("SET checkpoint_completion_target = 0.9")
    
    async def _init_connection(self, connection):
        """Initialize connection with prepared statements."""
        # Prepare commonly used statements for better performance
        await connection.prepare("""
            INSERT INTO memories (content, memory_type, embedding, importance_score,
                                semantic_metadata, episodic_metadata, procedural_metadata, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
        """)
    
    async def acquire_connection(self):
        """Acquire connection with monitoring."""
        if not self.pool:
            await self.initialize_pool()
        
        connection = await self.pool.acquire()
        self.active_connections += 1
        self.peak_connections = max(self.peak_connections, self.active_connections)
        
        # Track connection metrics
        conn_id = id(connection)
        self.connection_metrics[conn_id] = {
            "acquired_at": time.time(),
            "queries_executed": 0
        }
        
        return connection
    
    async def release_connection(self, connection):
        """Release connection with cleanup."""
        conn_id = id(connection)
        if conn_id in self.connection_metrics:
            del self.connection_metrics[conn_id]
        
        await self.pool.release(connection)
        self.active_connections -= 1
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self.pool:
            return {}
        
        return {
            "pool_size": self.pool.get_size(),
            "active_connections": self.active_connections,
            "peak_connections": self.peak_connections,
            "idle_connections": self.pool.get_idle_size(),
            "pool_uptime_seconds": (datetime.now() - self.pool_created_at).total_seconds() if self.pool_created_at else 0
        }


class ParallelWorkerManager:
    """
    Dynamic parallel worker management system.
    
    Features:
    - Auto-scaling based on load and performance
    - Worker health monitoring
    - Load balancing across workers
    - Efficient task distribution
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.workers = []
        self.worker_pool = None
        self.task_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.worker_metrics = {}
        self.scaling_history = deque(maxlen=100)
        self.last_scale_time = 0
        
    async def initialize_workers(self):
        """Initialize worker pool with optimal sizing."""
        initial_workers = self._calculate_optimal_workers()
        
        self.worker_pool = ThreadPoolExecutor(
            max_workers=initial_workers,
            thread_name_prefix="bulk_worker"
        )
        
        logger.info(f"Initialized {initial_workers} parallel workers")
    
    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on system resources."""
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Base calculation on CPU cores and available memory
        if self.config.optimization_level == OptimizationLevel.CONSERVATIVE:
            optimal = min(cpu_count, self.config.max_workers // 2)
        elif self.config.optimization_level == OptimizationLevel.AGGRESSIVE:
            optimal = min(cpu_count * 2, self.config.max_workers)
        else:  # BALANCED or ADAPTIVE
            optimal = min(cpu_count + 2, self.config.max_workers)
        
        # Adjust based on memory constraints
        memory_per_worker = 128  # MB per worker estimate
        max_workers_by_memory = int(memory_gb * 1024 / memory_per_worker)
        optimal = min(optimal, max_workers_by_memory)
        
        return max(self.config.min_workers, optimal)
    
    async def auto_scale_workers(self, current_load: float, performance_metrics: PerformanceMetrics):
        """Automatically scale workers based on load and performance."""
        if not self.config.auto_tuning_enabled:
            return
        
        current_time = time.time()
        if current_time - self.last_scale_time < 30:  # Minimum 30 seconds between scaling
            return
        
        current_workers = len(self.workers)
        cpu_usage = performance_metrics.cpu_usage_percent
        memory_usage = performance_metrics.memory_usage_mb
        
        should_scale_up = (
            current_load > 0.8 and
            cpu_usage < self.config.cpu_usage_limit * 0.8 and
            memory_usage < self.config.memory_usage_limit * 0.8 and
            current_workers < self.config.max_workers
        )
        
        should_scale_down = (
            current_load < 0.3 and
            current_workers > self.config.min_workers
        )
        
        if should_scale_up:
            new_workers = min(
                current_workers + 2,
                self.config.max_workers
            )
            await self._scale_to_workers(new_workers)
            logger.info(f"Scaled up workers: {current_workers} -> {new_workers}")
            
        elif should_scale_down:
            new_workers = max(
                current_workers - 1,
                self.config.min_workers
            )
            await self._scale_to_workers(new_workers)
            logger.info(f"Scaled down workers: {current_workers} -> {new_workers}")
        
        self.last_scale_time = current_time
    
    async def _scale_to_workers(self, target_workers: int):
        """Scale worker pool to target size."""
        current_workers = len(self.workers)
        
        if target_workers > current_workers:
            # Scale up
            for _ in range(target_workers - current_workers):
                worker_id = f"worker_{len(self.workers)}"
                self.workers.append(worker_id)
                self.worker_metrics[worker_id] = {
                    "created_at": time.time(),
                    "tasks_completed": 0,
                    "total_processing_time": 0.0
                }
        
        elif target_workers < current_workers:
            # Scale down
            workers_to_remove = current_workers - target_workers
            for _ in range(workers_to_remove):
                if self.workers:
                    worker_id = self.workers.pop()
                    if worker_id in self.worker_metrics:
                        del self.worker_metrics[worker_id]
        
        self.scaling_history.append({
            "timestamp": time.time(),
            "from_workers": current_workers,
            "to_workers": target_workers,
            "reason": "auto_scale"
        })


class MemoryManager:
    """
    Memory-efficient processing manager.
    
    Features:
    - Dynamic batch size adjustment
    - Memory pressure monitoring
    - Garbage collection optimization
    - Streaming processing for large datasets
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.current_batch_size = 1000
        self.memory_samples = deque(maxlen=50)
        self.gc_stats = {"collections": 0, "freed_objects": 0}
        
    async def optimize_batch_size(self, current_memory_mb: float, processing_rate: float) -> int:
        """Dynamically optimize batch size based on memory usage and performance."""
        if not self.config.batch_size_auto_adjust:
            return self.current_batch_size
        
        self.memory_samples.append(current_memory_mb)
        
        # Calculate memory trend
        if len(self.memory_samples) >= 10:
            recent_avg = sum(list(self.memory_samples)[-5:]) / 5
            overall_avg = sum(self.memory_samples) / len(self.memory_samples)
            memory_trend = (recent_avg - overall_avg) / overall_avg
        else:
            memory_trend = 0
        
        # Adjust batch size based on memory pressure and performance
        memory_ratio = current_memory_mb / self.config.max_memory_usage_mb
        
        if memory_ratio > self.config.memory_pressure_threshold:
            # Reduce batch size to lower memory pressure
            self.current_batch_size = max(100, int(self.current_batch_size * 0.8))
        elif memory_ratio < 0.5 and processing_rate > 500:  # Low memory usage, good performance
            # Increase batch size for better throughput
            self.current_batch_size = min(5000, int(self.current_batch_size * 1.2))
        
        return self.current_batch_size
    
    async def stream_process_items(
        self, 
        items: List[BulkMemoryItem], 
        processor: Callable,
        chunk_size: Optional[int] = None
    ) -> AsyncGenerator[Any, None]:
        """Stream process items in memory-efficient chunks."""
        chunk_size = chunk_size or self.current_batch_size
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            
            # Process chunk
            result = await processor(chunk)
            yield result
            
            # Memory management
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            if current_memory > self.config.max_memory_usage_mb * 0.9:
                await self._force_garbage_collection()
    
    async def _force_garbage_collection(self):
        """Force garbage collection to free memory."""
        before_objects = len(gc.get_objects())
        collected = gc.collect()
        after_objects = len(gc.get_objects())
        
        self.gc_stats["collections"] += 1
        self.gc_stats["freed_objects"] += (before_objects - after_objects)
        
        logger.debug(f"Forced GC: collected {collected} objects, freed {before_objects - after_objects} objects")


class CacheManager:
    """
    Advanced caching system for bulk operations.
    
    Features:
    - LRU cache with TTL
    - Prefetching based on access patterns
    - Cache warming strategies
    - Memory-efficient cache storage
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.cache = {}
        self.access_times = {}
        self.access_counts = defaultdict(int)
        self.cache_stats = {"hits": 0, "misses": 0}
        self.prefetch_queue = asyncio.Queue()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache with LRU and TTL."""
        if not self.config.enable_caching:
            return None
        
        if key in self.cache:
            # Check TTL
            cache_entry = self.cache[key]
            if time.time() - cache_entry["timestamp"] < self.config.cache_ttl_seconds:
                # Update access time for LRU
                self.access_times[key] = time.time()
                self.access_counts[key] += 1
                self.cache_stats["hits"] += 1
                return cache_entry["value"]
            else:
                # Expired, remove from cache
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any):
        """Set item in cache with size management."""
        if not self.config.enable_caching:
            return
        
        # Check cache size and evict if necessary
        await self._evict_if_needed()
        
        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "size": self._estimate_size(value)
        }
        self.access_times[key] = time.time()
    
    async def _evict_if_needed(self):
        """Evict least recently used items if cache is full."""
        current_size = sum(entry["size"] for entry in self.cache.values())
        max_size = self.config.cache_size_mb * 1024 * 1024
        
        if current_size > max_size:
            # Sort by access time (LRU)
            sorted_keys = sorted(self.access_times.keys(), key=lambda k: self.access_times[k])
            
            # Evict oldest 25% of entries
            evict_count = max(1, len(sorted_keys) // 4)
            for i in range(evict_count):
                key_to_evict = sorted_keys[i]
                if key_to_evict in self.cache:
                    del self.cache[key_to_evict]
                if key_to_evict in self.access_times:
                    del self.access_times[key_to_evict]
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of cached value."""
        if isinstance(value, str):
            return len(value.encode('utf-8'))
        elif isinstance(value, (list, tuple)):
            return sum(self._estimate_size(item) for item in value)
        elif isinstance(value, dict):
            return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items())
        else:
            return 1000  # Default estimate


class PerformanceMonitor:
    """
    Real-time performance monitoring and metrics collection.
    
    Features:
    - System resource monitoring
    - Performance trend analysis
    - Bottleneck detection
    - Automated alerts
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.metrics_history = deque(maxlen=1000)
        self.current_metrics = None
        self.monitoring_task = None
        self.alert_thresholds = {
            "cpu_usage": 90.0,
            "memory_usage": 95.0,
            "disk_io": 80.0,
            "response_time": 5.0
        }
    
    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                metrics = await self._collect_metrics()
                self.current_metrics = metrics
                self.metrics_history.append(metrics)
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                await asyncio.sleep(self.config.metrics_collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect current system metrics."""
        process = psutil.Process()
        
        return {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": process.memory_info().rss / 1024 / 1024,
            "disk_io_read_mbps": psutil.disk_io_counters().read_bytes / 1024 / 1024 if psutil.disk_io_counters() else 0,
            "disk_io_write_mbps": psutil.disk_io_counters().write_bytes / 1024 / 1024 if psutil.disk_io_counters() else 0,
            "network_sent_mbps": psutil.net_io_counters().bytes_sent / 1024 / 1024 if psutil.net_io_counters() else 0,
            "network_recv_mbps": psutil.net_io_counters().bytes_recv / 1024 / 1024 if psutil.net_io_counters() else 0,
            "open_files": len(process.open_files()),
            "threads": process.num_threads()
        }
    
    async def _check_alerts(self, metrics: Dict[str, float]):
        """Check metrics against alert thresholds."""
        alerts = []
        
        if metrics["cpu_percent"] > self.alert_thresholds["cpu_usage"]:
            alerts.append(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
        
        if metrics["memory_percent"] > self.alert_thresholds["memory_usage"]:
            alerts.append(f"High memory usage: {metrics['memory_percent']:.1f}%")
        
        if alerts and self.config.performance_logging:
            logger.warning(f"Performance alerts: {'; '.join(alerts)}")
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and trends."""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-10:]
        
        return {
            "current": self.current_metrics,
            "averages": {
                "cpu_percent": sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics),
                "memory_percent": sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics),
                "memory_used_mb": sum(m["memory_used_mb"] for m in recent_metrics) / len(recent_metrics)
            },
            "peaks": {
                "cpu_percent": max(m["cpu_percent"] for m in self.metrics_history),
                "memory_percent": max(m["memory_percent"] for m in self.metrics_history),
                "memory_used_mb": max(m["memory_used_mb"] for m in self.metrics_history)
            },
            "monitoring_duration": len(self.metrics_history) * self.config.metrics_collection_interval
        }


class BulkPerformanceOptimizer:
    """
    Master performance optimizer orchestrating all optimization components.
    
    Provides unified interface for all performance optimization features.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None, database_url: str = None):
        self.config = config or OptimizationConfig()
        self.database_url = database_url or "postgresql://user:password@localhost/secondbrain"
        
        # Initialize components
        self.connection_manager = ConnectionPoolManager(self.config, self.database_url)
        self.worker_manager = ParallelWorkerManager(self.config)
        self.memory_manager = MemoryManager(self.config)
        self.cache_manager = CacheManager(self.config)
        self.performance_monitor = PerformanceMonitor(self.config)
        
        self.optimization_stats = {
            "optimizations_applied": 0,
            "performance_improvements": [],
            "resource_savings": {}
        }
    
    async def initialize(self):
        """Initialize all optimization components."""
        logger.info("Initializing bulk performance optimizer")
        
        await self.connection_manager.initialize_pool()
        await self.worker_manager.initialize_workers()
        await self.performance_monitor.start_monitoring()
        
        logger.info("Bulk performance optimizer initialized")
    
    async def optimize_operation(
        self, 
        operation_type: str, 
        item_count: int,
        current_performance: Optional[PerformanceMetrics] = None
    ) -> Dict[str, Any]:
        """Apply optimizations for a specific operation."""
        optimizations = {}
        
        # Get current system state
        system_metrics = await self.performance_monitor._collect_metrics()
        
        # Optimize batch size
        if current_performance:
            optimal_batch_size = await self.memory_manager.optimize_batch_size(
                system_metrics["memory_used_mb"],
                current_performance.items_per_second
            )
            optimizations["batch_size"] = optimal_batch_size
        
        # Auto-scale workers
        if current_performance:
            current_load = min(1.0, item_count / 10000)  # Normalize load
            await self.worker_manager.auto_scale_workers(current_load, current_performance)
            optimizations["worker_count"] = len(self.worker_manager.workers)
        
        # Connection pool optimization
        pool_stats = await self.connection_manager.get_pool_stats()
        if pool_stats.get("active_connections", 0) > pool_stats.get("pool_size", 0) * 0.8:
            optimizations["connection_pool"] = "high_utilization_detected"
        
        self.optimization_stats["optimizations_applied"] += 1
        
        return optimizations
    
    async def get_optimization_recommendations(self, operation_metrics: PerformanceMetrics) -> List[str]:
        """Get optimization recommendations based on performance data."""
        recommendations = []
        
        # CPU optimization
        if operation_metrics.cpu_usage_percent > 80:
            recommendations.append("Consider reducing parallel workers or batch size")
        elif operation_metrics.cpu_usage_percent < 30:
            recommendations.append("Consider increasing parallel workers for better CPU utilization")
        
        # Memory optimization
        if operation_metrics.memory_usage_mb > self.config.max_memory_usage_mb * 0.8:
            recommendations.append("Reduce batch size to lower memory usage")
        
        # Performance optimization
        if operation_metrics.items_per_second < 100:
            recommendations.append("Consider optimizing database queries or increasing batch size")
        
        # Cache optimization
        if operation_metrics.cache_hit_rate < 0.5:
            recommendations.append("Enable or tune caching for better performance")
        
        return recommendations
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        performance_summary = await self.performance_monitor.get_performance_summary()
        pool_stats = await self.connection_manager.get_pool_stats()
        
        return {
            "optimization_config": asdict(self.config),
            "system_performance": performance_summary,
            "connection_pool": pool_stats,
            "worker_management": {
                "current_workers": len(self.worker_manager.workers),
                "scaling_history": list(self.worker_manager.scaling_history)
            },
            "memory_management": {
                "current_batch_size": self.memory_manager.current_batch_size,
                "gc_stats": self.memory_manager.gc_stats
            },
            "cache_performance": {
                "hit_rate": self.cache_manager.cache_stats["hits"] / 
                           max(1, self.cache_manager.cache_stats["hits"] + self.cache_manager.cache_stats["misses"]),
                "cache_size": len(self.cache_manager.cache),
                "stats": self.cache_manager.cache_stats
            },
            "optimization_stats": self.optimization_stats,
            "recommendations": await self.get_optimization_recommendations(
                PerformanceMetrics(
                    operation_id="current",
                    start_time=datetime.now(),
                    cpu_usage_percent=performance_summary.get("current", {}).get("cpu_percent", 0),
                    memory_usage_mb=performance_summary.get("current", {}).get("memory_used_mb", 0),
                    cache_hit_rate=self.cache_manager.cache_stats["hits"] / 
                                  max(1, self.cache_manager.cache_stats["hits"] + self.cache_manager.cache_stats["misses"])
                )
            )
        }
    
    async def shutdown(self):
        """Gracefully shutdown optimizer components."""
        logger.info("Shutting down bulk performance optimizer")
        
        await self.performance_monitor.stop_monitoring()
        
        if self.worker_manager.worker_pool:
            self.worker_manager.worker_pool.shutdown(wait=True)
        
        if self.connection_manager.pool:
            await self.connection_manager.pool.close()
        
        logger.info("Bulk performance optimizer shutdown complete")


# Global instance
_performance_optimizer_instance: Optional[BulkPerformanceOptimizer] = None


async def get_performance_optimizer(
    config: Optional[OptimizationConfig] = None,
    database_url: Optional[str] = None
) -> BulkPerformanceOptimizer:
    """Get or create the global performance optimizer instance."""
    global _performance_optimizer_instance
    
    if _performance_optimizer_instance is None:
        _performance_optimizer_instance = BulkPerformanceOptimizer(config, database_url)
        await _performance_optimizer_instance.initialize()
    
    return _performance_optimizer_instance 