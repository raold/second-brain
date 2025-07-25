"""
Caching decorators for easy cache integration.

Provides decorators for common caching patterns.
"""

import functools
import hashlib
import json
from typing import Any, Callable, Optional, Union

from src.infrastructure.caching import Cache, CacheKey, CacheStrategy, TTLStrategy
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def _make_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: Optional[str] = None,
) -> str:
    """
    Generate cache key from function and arguments.
    
    Args:
        func: Function being cached
        args: Function arguments
        kwargs: Function keyword arguments
        key_prefix: Optional key prefix
        
    Returns:
        Cache key string
    """
    # Build key components
    components = [
        key_prefix or func.__module__,
        func.__name__,
    ]
    
    # Add args
    for arg in args:
        if hasattr(arg, "id"):  # Domain objects
            components.append(str(arg.id))
        elif isinstance(arg, (str, int, float, bool)):
            components.append(str(arg))
        else:
            # Hash complex objects
            components.append(
                hashlib.md5(
                    json.dumps(arg, sort_keys=True, default=str).encode()
                ).hexdigest()[:8]
            )
    
    # Add kwargs
    if kwargs:
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        components.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
    
    return ":".join(components)


def cache_aside(
    cache: Optional[Cache] = None,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    strategy: Optional[CacheStrategy] = None,
    namespace: Optional[str] = None,
) -> Callable:
    """
    Cache-aside decorator for functions.
    
    Args:
        cache: Cache instance (uses default if None)
        ttl: TTL in seconds
        key_prefix: Cache key prefix
        strategy: Caching strategy
        namespace: Cache namespace
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get cache instance
            cache_instance = cache
            if cache_instance is None:
                from src.infrastructure.caching import get_cache
                cache_instance = await get_cache()
            
            # Generate cache key
            if namespace:
                key_builder = CacheKey(namespace)
                cache_key = key_builder.build(func.__name__, *args)
            else:
                cache_key = _make_cache_key(func, args, kwargs, key_prefix)
            
            # Try to get from cache
            cached_value = await cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Determine if we should cache
            if strategy:
                should_cache = strategy.should_cache(cache_key, result)
                cache_ttl = strategy.get_ttl(cache_key, result) if should_cache else None
            else:
                should_cache = result is not None
                cache_ttl = ttl
            
            # Cache the result
            if should_cache:
                await cache_instance.set(
                    cache_key,
                    result,
                    ttl=cache_ttl,
                )
                logger.debug(f"Cached result for {cache_key}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For sync functions, we can't use async cache
            # Just execute the function
            logger.warning(
                f"Cache-aside decorator used on sync function {func.__name__}, "
                "caching disabled"
            )
            return func(*args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_invalidate(
    cache: Optional[Cache] = None,
    patterns: Optional[list[str]] = None,
    namespace: Optional[str] = None,
) -> Callable:
    """
    Cache invalidation decorator.
    
    Invalidates cache entries after function execution.
    
    Args:
        cache: Cache instance
        patterns: Key patterns to invalidate
        namespace: Cache namespace
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Get cache instance
            cache_instance = cache
            if cache_instance is None:
                from src.infrastructure.caching import get_cache
                cache_instance = await get_cache()
            
            # Invalidate cache
            if namespace:
                # Clear entire namespace
                deleted = await cache_instance.clear_namespace(namespace)
                logger.debug(f"Cleared {deleted} keys from namespace {namespace}")
            elif patterns:
                # Clear specific patterns
                for pattern in patterns:
                    deleted = await cache_instance.delete_pattern(pattern)
                    logger.debug(f"Deleted {deleted} keys matching {pattern}")
            else:
                # Clear based on function name
                pattern = f"*{func.__name__}*"
                deleted = await cache_instance.delete_pattern(pattern)
                logger.debug(f"Deleted {deleted} keys matching {pattern}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For sync functions, just execute
            return func(*args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cached_property(
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
) -> Callable:
    """
    Cached property decorator.
    
    Caches property values for the specified TTL.
    
    Args:
        ttl: TTL in seconds
        key_prefix: Cache key prefix
        
    Returns:
        Property decorator
    """
    def decorator(func: Callable) -> property:
        cache_attr = f"_cached_{func.__name__}"
        cache_time_attr = f"_cache_time_{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(self: Any) -> Any:
            import time
            
            # Check if cached value exists and is still valid
            if hasattr(self, cache_attr):
                cache_time = getattr(self, cache_time_attr, 0)
                if time.time() - cache_time < ttl:
                    return getattr(self, cache_attr)
            
            # Compute value
            value = func(self)
            
            # Cache it
            setattr(self, cache_attr, value)
            setattr(self, cache_time_attr, time.time())
            
            return value
        
        return property(wrapper)
    
    return decorator