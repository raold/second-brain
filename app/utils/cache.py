"""
Advanced caching utilities for Second Brain performance optimization.
Provides LRU caching with TTL, metrics, and distributed caching interface.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

from cachetools import LRUCache, TTLCache
from cachetools.keys import hashkey

from app.utils.logger import get_logger

logger = get_logger()

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Gauge, Histogram
    cache_hits = Counter('cache_hits_total', 'Cache hits by type', ['cache_type'])
    cache_misses = Counter('cache_misses_total', 'Cache misses by type', ['cache_type'])
    cache_operations = Histogram('cache_operation_duration_seconds', 'Cache operation duration', ['operation', 'cache_type'])
    cache_size = Gauge('cache_size_current', 'Current cache size', ['cache_type'])
    cache_evictions = Counter('cache_evictions_total', 'Cache evictions by type', ['cache_type'])
except ImportError:
    cache_hits = cache_misses = cache_operations = cache_size = cache_evictions = None

@dataclass
class CacheConfig:
    """Configuration for cache instances."""
    max_size: int = 1000
    ttl_seconds: Optional[int] = None
    enable_metrics: bool = True
    compress_keys: bool = False
    async_refresh: bool = False

class AdvancedCache:
    """
    Advanced caching wrapper with metrics, TTL, and async support.
    """
    
    def __init__(self, name: str, config: CacheConfig):
        self.name = name
        self.config = config
        
        # Choose cache type based on TTL requirement
        if config.ttl_seconds:
            self._cache = TTLCache(maxsize=config.max_size, ttl=config.ttl_seconds)
        else:
            self._cache = LRUCache(maxsize=config.max_size)
        
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._last_eviction_time = None
        
        logger.info(f"Initialized {name} cache: max_size={config.max_size}, ttl={config.ttl_seconds}s")
    
    def _generate_key(self, func_args: tuple, func_kwargs: dict) -> str:
        """Generate cache key from function arguments."""
        if self.config.compress_keys:
            # Create hash for large arguments
            key_data = json.dumps([func_args, func_kwargs], sort_keys=True, default=str)
            return hashlib.md5(key_data.encode()).hexdigest()
        else:
            return hashkey(*func_args, **func_kwargs)
    
    def _record_hit(self):
        """Record cache hit metrics."""
        self._hit_count += 1
        if cache_hits and self.config.enable_metrics:
            cache_hits.labels(cache_type=self.name).inc()
    
    def _record_miss(self):
        """Record cache miss metrics."""
        self._miss_count += 1
        if cache_misses and self.config.enable_metrics:
            cache_misses.labels(cache_type=self.name).inc()
    
    def _record_eviction(self):
        """Record cache eviction."""
        self._eviction_count += 1
        self._last_eviction_time = datetime.now(timezone.utc)
        if cache_evictions and self.config.enable_metrics:
            cache_evictions.labels(cache_type=self.name).inc()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self._cache[key]
            self._record_hit()
            return value
        except KeyError:
            self._record_miss()
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        old_size = len(self._cache)
        self._cache[key] = value
        new_size = len(self._cache)
        
        # Check if eviction occurred
        if new_size <= old_size and old_size == self.config.max_size:
            self._record_eviction()
        
        # Update size metric
        if cache_size and self.config.enable_metrics:
            cache_size.labels(cache_type=self.name).set(new_size)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            del self._cache[key]
            if cache_size and self.config.enable_metrics:
                cache_size.labels(cache_type=self.name).set(len(self._cache))
            return True
        except KeyError:
            return False
    
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        if cache_size and self.config.enable_metrics:
            cache_size.labels(cache_type=self.name).set(0)
        logger.info(f"Cleared {self.name} cache")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "name": self.name,
            "size": len(self._cache),
            "max_size": self.config.max_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "eviction_count": self._eviction_count,
            "last_eviction": self._last_eviction_time.isoformat() if self._last_eviction_time else None,
            "ttl_seconds": self.config.ttl_seconds,
            "total_requests": total_requests
        }

# Global cache registry
_cache_registry: Dict[str, AdvancedCache] = {}

def get_cache(name: str, config: Optional[CacheConfig] = None) -> AdvancedCache:
    """Get or create a named cache instance."""
    if name not in _cache_registry:
        if config is None:
            config = CacheConfig()  # Use defaults
        _cache_registry[name] = AdvancedCache(name, config)
    return _cache_registry[name]

def cached_function(
    cache_name: str,
    config: Optional[CacheConfig] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching function results with advanced features.
    
    Args:
        cache_name: Name of the cache to use
        config: Cache configuration (created if not exists)
        key_func: Custom key generation function
    """
    def decorator(func):
        cache = get_cache(cache_name, config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache._generate_key(args, kwargs)
            
            # Check cache first
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            start_time = time.time()
            result = func(*args, **kwargs)
            
            # Record operation metrics
            if cache_operations and cache.config.enable_metrics:
                cache_operations.labels(
                    operation='compute',
                    cache_type=cache_name
                ).observe(time.time() - start_time)
            
            # Store in cache
            cache.set(key, result)
            return result
        
        return wrapper
    return decorator

def async_cached_function(
    cache_name: str,
    config: Optional[CacheConfig] = None,
    key_func: Optional[Callable] = None
):
    """
    Async decorator for caching function results.
    """
    def decorator(func):
        cache = get_cache(cache_name, config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache._generate_key(args, kwargs)
            
            # Check cache first
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute async function and cache result
            start_time = time.time()
            result = await func(*args, **kwargs)
            
            # Record operation metrics
            if cache_operations and cache.config.enable_metrics:
                cache_operations.labels(
                    operation='compute',
                    cache_type=cache_name
                ).observe(time.time() - start_time)
            
            # Store in cache
            cache.set(key, result)
            return result
        
        return wrapper
    return decorator

# Pre-configured cache instances for common use cases
EMBEDDING_CACHE_CONFIG = CacheConfig(
    max_size=2000,  # Larger for embeddings
    ttl_seconds=3600,  # 1 hour TTL
    enable_metrics=True,
    compress_keys=True  # Embeddings can have long text
)

SEARCH_CACHE_CONFIG = CacheConfig(
    max_size=1000,
    ttl_seconds=300,  # 5 minutes TTL for search results
    enable_metrics=True,
    compress_keys=False
)

ANALYTICS_CACHE_CONFIG = CacheConfig(
    max_size=100,
    ttl_seconds=60,  # 1 minute TTL for analytics
    enable_metrics=True,
    compress_keys=False
)

MEMORY_ACCESS_CACHE_CONFIG = CacheConfig(
    max_size=5000,  # Large cache for memory access patterns
    ttl_seconds=1800,  # 30 minutes TTL
    enable_metrics=True,
    compress_keys=False
)

def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics for all registered caches."""
    stats = {}
    total_hits = 0
    total_misses = 0
    total_size = 0
    
    for name, cache in _cache_registry.items():
        cache_stats = cache.stats()
        stats[name] = cache_stats
        total_hits += cache_stats["hit_count"]
        total_misses += cache_stats["miss_count"]
        total_size += cache_stats["size"]
    
    total_requests = total_hits + total_misses
    overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
    
    stats["_summary"] = {
        "total_caches": len(_cache_registry),
        "total_size": total_size,
        "total_hits": total_hits,
        "total_misses": total_misses,
        "overall_hit_rate_percent": round(overall_hit_rate, 2),
        "total_requests": total_requests
    }
    
    return stats

def clear_all_caches():
    """Clear all registered caches."""
    for cache in _cache_registry.values():
        cache.clear()
    logger.info("Cleared all caches")

# Smart eviction based on access patterns
class SmartEvictionCache(AdvancedCache):
    """
    Cache with smart eviction based on access patterns and usage frequency.
    """
    
    def __init__(self, name: str, config: CacheConfig):
        super().__init__(name, config)
        self._access_times: Dict[str, datetime] = {}
        self._access_counts: Dict[str, int] = {}
        self._last_cleanup = datetime.now(timezone.utc)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value and update access patterns."""
        result = super().get(key)
        if result is not None:
            # Update access tracking
            self._access_times[key] = datetime.now(timezone.utc)
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
        return result
    
    def set(self, key: str, value: Any) -> None:
        """Set value and initialize access tracking."""
        super().set(key, value)
        self._access_times[key] = datetime.now(timezone.utc)
        self._access_counts[key] = self._access_counts.get(key, 0)
        
        # Periodic cleanup of tracking data
        if (datetime.now(timezone.utc) - self._last_cleanup).total_seconds() > 300:  # 5 minutes
            self._cleanup_tracking_data()
    
    def _cleanup_tracking_data(self):
        """Clean up tracking data for evicted keys."""
        active_keys = set(self._cache.keys())
        
        # Remove tracking data for evicted keys
        for key in list(self._access_times.keys()):
            if key not in active_keys:
                del self._access_times[key]
                if key in self._access_counts:
                    del self._access_counts[key]
        
        self._last_cleanup = datetime.now(timezone.utc)
    
    def get_access_stats(self, key: str) -> Dict[str, Any]:
        """Get access statistics for a specific key."""
        return {
            "last_access": self._access_times.get(key),
            "access_count": self._access_counts.get(key, 0),
            "in_cache": key in self._cache
        }

def get_smart_cache(name: str, config: Optional[CacheConfig] = None) -> SmartEvictionCache:
    """Get or create a smart eviction cache instance."""
    cache_key = f"smart_{name}"
    if cache_key not in _cache_registry:
        if config is None:
            config = CacheConfig()
        _cache_registry[cache_key] = SmartEvictionCache(cache_key, config)
    return _cache_registry[cache_key] 