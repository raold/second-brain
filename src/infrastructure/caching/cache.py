"""
Redis cache implementation.

Provides high-performance caching with Redis.
"""

import json
import pickle
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio.lock import Lock

from src.infrastructure.logging import get_logger
from src.infrastructure.observability import get_metrics_collector

logger = get_logger(__name__)


class CacheKey:
    """Cache key builder for consistent key generation."""
    
    def __init__(self, namespace: str):
        """
        Initialize cache key builder.
        
        Args:
            namespace: Cache namespace
        """
        self.namespace = namespace
    
    def build(self, *parts: Any) -> str:
        """
        Build cache key from parts.
        
        Args:
            *parts: Key components
            
        Returns:
            Cache key string
        """
        key_parts = [self.namespace]
        for part in parts:
            if isinstance(part, (list, tuple)):
                key_parts.append(":".join(str(p) for p in part))
            else:
                key_parts.append(str(part))
        return ":".join(key_parts)
    
    def pattern(self, *parts: Any) -> str:
        """
        Build cache key pattern for matching.
        
        Args:
            *parts: Key components (use * for wildcards)
            
        Returns:
            Cache key pattern
        """
        return self.build(*parts)


class Cache:
    """Redis cache with async support."""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_ttl: int = 3600,
        key_prefix: str = "secondbrain",
    ):
        """
        Initialize cache.
        
        Args:
            redis_client: Redis client instance
            default_ttl: Default TTL in seconds
            key_prefix: Global key prefix
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.metrics = get_metrics_collector()
    
    def _make_key(self, key: str) -> str:
        """Make full cache key with prefix."""
        return f"{self.key_prefix}:{key}"
    
    async def get(
        self,
        key: str,
        deserialize: bool = True,
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            deserialize: Whether to deserialize the value
            
        Returns:
            Cached value or None
        """
        full_key = self._make_key(key)
        
        try:
            value = await self.redis.get(full_key)
            
            if value is None:
                self.metrics.track_cache("redis", hit=False)
                return None
            
            self.metrics.track_cache("redis", hit=True)
            
            if deserialize:
                # Try JSON first, fall back to pickle
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return pickle.loads(value)
            
            return value
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics.track_cache("redis", hit=False)
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            serialize: Whether to serialize the value
            
        Returns:
            Success boolean
        """
        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            if serialize:
                # Try JSON first for better interop
                try:
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    serialized = pickle.dumps(value)
            else:
                serialized = value
            
            await self.redis.set(
                full_key,
                serialized,
                ex=ttl,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success boolean
        """
        full_key = self._make_key(key)
        
        try:
            result = await self.redis.delete(full_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*:memories")
            
        Returns:
            Number of keys deleted
        """
        full_pattern = self._make_key(pattern)
        
        try:
            # Use SCAN to avoid blocking
            deleted = 0
            async for key in self.redis.scan_iter(match=full_pattern, count=100):
                if await self.redis.delete(key):
                    deleted += 1
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            Existence boolean
        """
        full_key = self._make_key(key)
        
        try:
            return await self.redis.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        ttl: Optional[int] = None,
    ) -> Optional[int]:
        """
        Increment counter in cache.
        
        Args:
            key: Cache key
            amount: Increment amount
            ttl: TTL in seconds
            
        Returns:
            New value or None on error
        """
        full_key = self._make_key(key)
        
        try:
            value = await self.redis.incrby(full_key, amount)
            
            if ttl is not None:
                await self.redis.expire(full_key, ttl)
            
            return value
            
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None
    
    async def get_lock(
        self,
        key: str,
        timeout: float = 10.0,
        blocking_timeout: Optional[float] = None,
    ) -> Lock:
        """
        Get distributed lock.
        
        Args:
            key: Lock key
            timeout: Lock timeout in seconds
            blocking_timeout: Max time to wait for lock
            
        Returns:
            Redis lock instance
        """
        full_key = self._make_key(f"lock:{key}")
        
        return self.redis.lock(
            full_key,
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )
    
    async def mget(self, keys: list[str]) -> dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict of key -> value
        """
        if not keys:
            return {}
        
        full_keys = [self._make_key(k) for k in keys]
        
        try:
            values = await self.redis.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = pickle.loads(value)
                    self.metrics.track_cache("redis", hit=True)
                else:
                    self.metrics.track_cache("redis", hit=False)
            
            return result
            
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            return {}
    
    async def mset(
        self,
        mapping: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            mapping: Dict of key -> value
            ttl: TTL in seconds
            
        Returns:
            Success boolean
        """
        if not mapping:
            return True
        
        try:
            # Serialize values
            serialized = {}
            for key, value in mapping.items():
                full_key = self._make_key(key)
                try:
                    serialized[full_key] = json.dumps(value)
                except (TypeError, ValueError):
                    serialized[full_key] = pickle.dumps(value)
            
            # Use pipeline for atomic operation
            async with self.redis.pipeline() as pipe:
                pipe.mset(serialized)
                
                if ttl is not None:
                    for key in serialized:
                        pipe.expire(key, ttl)
                
                await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.
        
        Args:
            namespace: Cache namespace
            
        Returns:
            Number of keys deleted
        """
        pattern = f"{namespace}:*"
        return await self.delete_pattern(pattern)
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()


# Singleton instance
_cache: Optional[Cache] = None


async def get_cache(url: Optional[str] = None) -> Cache:
    """
    Get or create cache instance.
    
    Args:
        url: Redis URL (uses env var if not provided)
        
    Returns:
        Cache instance
    """
    global _cache
    
    if _cache is None:
        import os
        redis_url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        client = redis.from_url(
            redis_url,
            decode_responses=False,  # We handle serialization
            max_connections=50,
        )
        
        _cache = Cache(client)
        
        # Test connection
        try:
            await client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    return _cache