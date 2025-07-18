"""
Tests for bulk performance optimizer module.
Simple tests focusing on import, instantiation, and basic functionality.
"""

import pytest
from datetime import datetime
from app.bulk_performance_optimizer import (
    OptimizationLevel,
    ResourceType,
    PerformanceMetrics,
    OptimizationConfig,
    ConnectionPoolManager,
    ParallelWorkerManager,
    MemoryManager,
    CacheManager,
    PerformanceMonitor,
    BulkPerformanceOptimizer,
)


class TestEnums:
    """Test enum classes."""

    def test_optimization_level_enum(self):
        assert OptimizationLevel.CONSERVATIVE.value == "conservative"
        assert OptimizationLevel.BALANCED.value == "balanced"
        assert OptimizationLevel.AGGRESSIVE.value == "aggressive"
        assert OptimizationLevel.ADAPTIVE.value == "adaptive"

    def test_resource_type_enum(self):
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.DISK_IO.value == "disk_io"
        assert ResourceType.NETWORK_IO.value == "network_io"
        assert ResourceType.DATABASE_CONNECTIONS.value == "database_connections"


class TestPerformanceMetrics:
    """Test PerformanceMetrics data class."""

    def test_performance_metrics_creation(self):
        now = datetime.now()
        metrics = PerformanceMetrics(
            operation_id="test_op",
            start_time=now,
            total_items=100,
            processed_items=50
        )
        
        assert metrics.operation_id == "test_op"
        assert metrics.start_time == now
        assert metrics.total_items == 100
        assert metrics.processed_items == 50
        assert metrics.batch_processing_time == []

    def test_performance_metrics_with_end_time(self):
        start = datetime.now()
        end = datetime.now()
        
        metrics = PerformanceMetrics(
            operation_id="test_op",
            start_time=start,
            end_time=end,
            items_per_second=10.5,
            cpu_usage_percent=25.0
        )
        
        assert metrics.end_time == end
        assert metrics.items_per_second == 10.5
        assert metrics.cpu_usage_percent == 25.0


class TestOptimizationConfig:
    """Test OptimizationConfig data class."""

    def test_default_config(self):
        config = OptimizationConfig()
        
        assert config.optimization_level == OptimizationLevel.BALANCED
        assert config.min_connections == 5
        assert config.max_connections == 50
        assert config.min_workers == 2
        assert config.max_workers == 16
        assert config.enable_caching is True

    def test_custom_config(self):
        config = OptimizationConfig(
            optimization_level=OptimizationLevel.AGGRESSIVE,
            max_connections=100,
            max_workers=32
        )
        
        assert config.optimization_level == OptimizationLevel.AGGRESSIVE
        assert config.max_connections == 100
        assert config.max_workers == 32


class TestConnectionPoolManager:
    """Test ConnectionPoolManager class."""

    def test_initialization(self):
        config = OptimizationConfig()
        manager = ConnectionPoolManager(config, "postgresql://test")
        
        assert manager.config == config
        assert manager.database_url == "postgresql://test"
        assert manager.pool is None

    def test_initialization_with_custom_config(self):
        config = OptimizationConfig(max_connections=20)
        manager = ConnectionPoolManager(config, "postgresql://test")
        
        assert manager.config.max_connections == 20


class TestParallelWorkerManager:
    """Test ParallelWorkerManager class."""

    def test_initialization(self):
        config = OptimizationConfig()
        manager = ParallelWorkerManager(config)
        
        assert manager.config == config

    def test_initialization_with_custom_workers(self):
        config = OptimizationConfig(max_workers=8)
        manager = ParallelWorkerManager(config)
        
        assert manager.config.max_workers == 8


class TestMemoryManager:
    """Test MemoryManager class."""

    def test_initialization(self):
        config = OptimizationConfig()
        manager = MemoryManager(config)
        
        assert manager.config == config

    def test_initialization_with_memory_limit(self):
        config = OptimizationConfig(max_memory_usage_mb=4096)
        manager = MemoryManager(config)
        
        assert manager.config.max_memory_usage_mb == 4096


class TestCacheManager:
    """Test CacheManager class."""

    def test_initialization(self):
        config = OptimizationConfig()
        manager = CacheManager(config)
        
        assert manager.config == config

    def test_initialization_with_caching_disabled(self):
        config = OptimizationConfig(enable_caching=False)
        manager = CacheManager(config)
        
        assert manager.config.enable_caching is False


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""

    def test_initialization(self):
        config = OptimizationConfig()
        monitor = PerformanceMonitor(config)
        
        assert monitor.config == config


class TestBulkPerformanceOptimizer:
    """Test BulkPerformanceOptimizer class."""

    def test_initialization_default(self):
        optimizer = BulkPerformanceOptimizer()
        
        assert optimizer.config is not None
        assert optimizer.connection_manager is not None
        assert optimizer.worker_manager is not None
        assert optimizer.memory_manager is not None
        assert optimizer.cache_manager is not None
        assert optimizer.performance_monitor is not None

    def test_initialization_with_config(self):
        config = OptimizationConfig(optimization_level=OptimizationLevel.AGGRESSIVE)
        optimizer = BulkPerformanceOptimizer(config)
        
        assert optimizer.config.optimization_level == OptimizationLevel.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_get_optimization_recommendations(self):
        optimizer = BulkPerformanceOptimizer()
        
        # Create dummy metrics
        metrics = PerformanceMetrics(
            operation_id="test",
            start_time=datetime.now(),
            total_items=100
        )
        
        recommendations = await optimizer.get_optimization_recommendations(metrics)
        
        assert isinstance(recommendations, list)
