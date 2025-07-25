"""
Caching strategies for different use cases.

Provides various caching patterns and eviction strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheStrategy(ABC):
    """Base class for cache strategies."""
    
    @abstractmethod
    def should_cache(self, key: str, value: Any) -> bool:
        """
        Determine if value should be cached.
        
        Args:
            key: Cache key
            value: Value to potentially cache
            
        Returns:
            Whether to cache the value
        """
        pass
    
    @abstractmethod
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """
        Get TTL for cached value.
        
        Args:
            key: Cache key
            value: Value being cached
            
        Returns:
            TTL in seconds or None for default
        """
        pass


class TTLStrategy(CacheStrategy):
    """TTL-based caching strategy."""
    
    def __init__(
        self,
        default_ttl: int = 3600,
        ttl_map: Optional[dict[str, int]] = None,
    ):
        """
        Initialize TTL strategy.
        
        Args:
            default_ttl: Default TTL in seconds
            ttl_map: Map of key patterns to TTLs
        """
        self.default_ttl = default_ttl
        self.ttl_map = ttl_map or {}
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Always cache with TTL strategy."""
        return value is not None
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get TTL based on key pattern."""
        # Check for exact matches first
        if key in self.ttl_map:
            return self.ttl_map[key]
        
        # Check for pattern matches
        for pattern, ttl in self.ttl_map.items():
            if "*" in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split("*")
                if all(part in key for part in pattern_parts if part):
                    return ttl
        
        return self.default_ttl


class LRUStrategy(CacheStrategy):
    """LRU (Least Recently Used) caching strategy."""
    
    def __init__(
        self,
        max_items: int = 10000,
        ttl: int = 3600,
    ):
        """
        Initialize LRU strategy.
        
        Args:
            max_items: Maximum number of items to cache
            ttl: TTL for cached items
        """
        self.max_items = max_items
        self.ttl = ttl
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if value is not None."""
        return value is not None
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get fixed TTL."""
        return self.ttl


class SizeBasedStrategy(CacheStrategy):
    """Cache based on value size."""
    
    def __init__(
        self,
        max_size: int = 1024 * 1024,  # 1MB
        ttl: int = 3600,
    ):
        """
        Initialize size-based strategy.
        
        Args:
            max_size: Maximum size in bytes
            ttl: TTL for cached items
        """
        self.max_size = max_size
        self.ttl = ttl
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if value size is within limits."""
        if value is None:
            return False
        
        # Estimate size
        import sys
        size = sys.getsizeof(value)
        
        return size <= self.max_size
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get fixed TTL."""
        return self.ttl


class FrequencyBasedStrategy(CacheStrategy):
    """Cache frequently accessed items."""
    
    def __init__(
        self,
        min_frequency: int = 3,
        ttl: int = 3600,
    ):
        """
        Initialize frequency-based strategy.
        
        Args:
            min_frequency: Minimum access frequency to cache
            ttl: TTL for cached items
        """
        self.min_frequency = min_frequency
        self.ttl = ttl
        self.access_counts: dict[str, int] = {}
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if accessed frequently enough."""
        if value is None:
            return False
        
        # Increment access count
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        
        # Cache if threshold reached
        return self.access_counts[key] >= self.min_frequency
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get TTL based on access frequency."""
        # Higher frequency = longer TTL
        frequency = self.access_counts.get(key, 0)
        multiplier = min(frequency / self.min_frequency, 5)  # Cap at 5x
        
        return int(self.ttl * multiplier)