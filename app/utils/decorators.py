"""
Elegant decorators for cross-cutting concerns in the Second Brain application.

This module provides sophisticated decorators that simplify complexity
rather than just showing off cleverness. Each decorator addresses real
architectural needs while maintaining readability and debuggability.
"""

import asyncio
import functools
import inspect
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Optional, ParamSpec, TypeVar, Union
from uuid import uuid4

# Type variables for generic decorators
F = TypeVar('F', bound=Callable[..., Any])
P = ParamSpec('P')
T = TypeVar('T')

logger = logging.getLogger(__name__)


# ============================================================================
# Performance and Monitoring Decorators
# ============================================================================

def measure_performance(
    operation_name: Optional[str] = None,
    log_slow_queries: bool = True,
    slow_threshold_ms: float = 1000.0,
    include_args: bool = False
):
    """
    Measure function execution time with intelligent logging.

    Args:
        operation_name: Custom name for the operation (defaults to function name)
        log_slow_queries: Whether to log slow operations
        slow_threshold_ms: Threshold in milliseconds for logging slow operations
        include_args: Whether to include function arguments in logs
    """
    def decorator(func: F) -> F:
        op_name = operation_name or f"{func.__module__}.{func.__qualname__}"

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start_time = time.perf_counter()
                operation_id = str(uuid4())[:8]

                logger.debug(f"Starting {op_name}", extra={
                    'operation_id': operation_id,
                    'operation_name': op_name
                })

                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    log_data = {
                        'operation_id': operation_id,
                        'operation_name': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'success'
                    }

                    if include_args and args:
                        log_data['args'] = str(args)[:200]  # Truncate long args

                    if log_slow_queries and duration_ms > slow_threshold_ms:
                        logger.warning(f"Slow operation: {op_name}", extra=log_data)
                    else:
                        logger.debug(f"Completed {op_name}", extra=log_data)

                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.error(f"Failed {op_name}: {e}", extra={
                        'operation_id': operation_id,
                        'operation_name': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'error',
                        'error_type': type(e).__name__
                    })
                    raise

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start_time = time.perf_counter()
                operation_id = str(uuid4())[:8]

                logger.debug(f"Starting {op_name}", extra={
                    'operation_id': operation_id,
                    'operation_name': op_name
                })

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    log_data = {
                        'operation_id': operation_id,
                        'operation_name': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'success'
                    }

                    if include_args and args:
                        log_data['args'] = str(args)[:200]

                    if log_slow_queries and duration_ms > slow_threshold_ms:
                        logger.warning(f"Slow operation: {op_name}", extra=log_data)
                    else:
                        logger.debug(f"Completed {op_name}", extra=log_data)

                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.error(f"Failed {op_name}: {e}", extra={
                        'operation_id': operation_id,
                        'operation_name': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'error',
                        'error_type': type(e).__name__
                    })
                    raise

            return sync_wrapper

    return decorator


class RateLimiter:
    """Thread-safe rate limiter for decorators."""

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
        self._lock = asyncio.Lock()

    async def can_proceed(self, identifier: str) -> bool:
        """Check if call can proceed based on rate limit."""
        async with self._lock:
            now = time.time()
            call_times = self.calls[identifier]

            # Remove calls outside the time window
            self.calls[identifier] = [t for t in call_times if now - t < self.time_window]

            if len(self.calls[identifier]) < self.max_calls:
                self.calls[identifier].append(now)
                return True

            return False


def rate_limit(max_calls: int, time_window: float, per: str = 'function'):
    """
    Rate limit function calls with sophisticated controls.

    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds
        per: Rate limiting scope ('function', 'instance', 'user')
    """
    limiter = RateLimiter(max_calls, time_window)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine rate limiting identifier
            if per == 'function':
                identifier = func.__qualname__
            elif per == 'instance' and args:
                identifier = f"{func.__qualname__}:{id(args[0])}"
            elif per == 'user':
                # Look for user_id in kwargs or first arg
                user_id = kwargs.get('user_id') or (args[0] if args else 'anonymous')
                identifier = f"{func.__qualname__}:user:{user_id}"
            else:
                identifier = func.__qualname__

            if not await limiter.can_proceed(identifier):
                raise RuntimeError(f"Rate limit exceeded for {func.__qualname__}")

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Error Handling and Resilience Decorators
# ============================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[type[Exception], tuple] = Exception,
    on_retry: Optional[Callable] = None
):
    """
    Retry decorator with exponential backoff and customizable behavior.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Exception types to retry on
        on_retry: Callback function called on each retry
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, don't retry
                        logger.error(f"Function {func.__qualname__} failed after {max_attempts} attempts: {e}")
                        raise

                    logger.warning(f"Attempt {attempt + 1} failed for {func.__qualname__}: {e}, retrying in {current_delay}s")

                    if on_retry:
                        try:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(attempt, e, *args, **kwargs)
                            else:
                                on_retry(attempt, e, *args, **kwargs)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached due to the raise in the loop
            raise last_exception

        return wrapper

    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: float = 60.0,
    expected_exception: type[Exception] = Exception
):
    """
    Circuit breaker pattern to prevent cascading failures.

    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Time to wait before attempting to close circuit
        expected_exception: Exception type that triggers circuit breaker
    """
    class CircuitBreakerState:
        def __init__(self):
            self.failure_count = 0
            self.last_failure_time = None
            self.state = 'closed'  # closed, open, half-open

    state = CircuitBreakerState()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()

            # Check if we should transition from open to half-open
            if (state.state == 'open' and
                state.last_failure_time and
                now - state.last_failure_time > timeout):
                state.state = 'half-open'
                logger.info(f"Circuit breaker for {func.__qualname__} transitioning to half-open")

            # Reject calls if circuit is open
            if state.state == 'open':
                raise RuntimeError(f"Circuit breaker open for {func.__qualname__}")

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success - reset failure count and close circuit
                if state.state == 'half-open':
                    state.state = 'closed'
                    logger.info(f"Circuit breaker for {func.__qualname__} closed")

                state.failure_count = 0
                return result

            except expected_exception:
                state.failure_count += 1
                state.last_failure_time = now

                if state.failure_count >= failure_threshold:
                    state.state = 'open'
                    logger.warning(f"Circuit breaker for {func.__qualname__} opened after {state.failure_count} failures")

                raise

        return wrapper

    return decorator


# ============================================================================
# Caching and Memoization Decorators
# ============================================================================

def memoize(
    max_size: Optional[int] = 128,
    ttl: Optional[float] = None,
    typed: bool = False
):
    """
    Advanced memoization with TTL and type-aware caching.

    Args:
        max_size: Maximum cache size (None for unlimited)
        ttl: Time-to-live for cache entries in seconds
        typed: Whether to treat different types as distinct cache keys
    """
    def decorator(func: F) -> F:
        cache = {}
        cache_info = {'hits': 0, 'misses': 0}

        def make_key(*args, **kwargs):
            """Create cache key from arguments."""
            key = args + tuple(sorted(kwargs.items()))
            if typed:
                key += tuple(type(arg) for arg in args)
                key += tuple(type(v) for v in kwargs.values())
            return key

        def is_expired(timestamp: float) -> bool:
            """Check if cache entry has expired."""
            return ttl is not None and time.time() - timestamp > ttl

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = make_key(*args, **kwargs)

            # Check if we have a cached result
            if key in cache:
                result, timestamp = cache[key]
                if not is_expired(timestamp):
                    cache_info['hits'] += 1
                    return result
                else:
                    # Remove expired entry
                    del cache[key]

            # Cache miss - compute result
            cache_info['misses'] += 1

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Store in cache
            cache[key] = (result, time.time())

            # Enforce max_size limit
            if max_size is not None and len(cache) > max_size:
                # Remove oldest entry (simple LRU approximation)
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]

            return result

        # Add cache management methods
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: cache_info.copy()
        wrapper.cache_size = lambda: len(cache)

        return wrapper

    return decorator


# ============================================================================
# Validation and Type Checking Decorators
# ============================================================================

def validate_args(**validators):
    """
    Validate function arguments using custom validators.

    Args:
        **validators: Mapping of argument names to validator functions
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Bind arguments to parameter names
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate each argument
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        if not validator(value):
                            raise ValueError(f"Validation failed for parameter '{param_name}': {value}")
                    except Exception as e:
                        raise ValueError(f"Validation error for parameter '{param_name}': {e}")

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def ensure_authenticated(user_param: str = 'user_id'):
    """
    Ensure user is authenticated before executing function.

    Args:
        user_param: Name of the parameter containing user ID
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            user_id = bound_args.arguments.get(user_param)
            if not user_id or user_id == 'anonymous':
                raise PermissionError(f"Authentication required for {func.__qualname__}")

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Context and State Management Decorators
# ============================================================================

def with_context(**context_vars):
    """
    Inject context variables into function execution.

    Args:
        **context_vars: Context variables to inject
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Store original context if it exists
            original_context = getattr(wrapper, '_context', {})

            # Merge with new context
            merged_context = {**original_context, **context_vars}
            wrapper._context = merged_context

            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            finally:
                # Restore original context
                wrapper._context = original_context

        # Provide access to current context
        wrapper.get_context = lambda: getattr(wrapper, '_context', {})

        return wrapper

    return decorator


def singleton(cls):
    """
    Singleton decorator that maintains one instance per class.

    Thread-safe implementation with lazy initialization.
    """
    instances = {}
    lock = asyncio.Lock()

    @functools.wraps(cls)
    async def get_instance(*args, **kwargs):
        if cls not in instances:
            async with lock:
                if cls not in instances:  # Double-check locking
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    # Also support synchronous access
    def sync_get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    # Replace the class with the factory function
    get_instance.sync = sync_get_instance
    get_instance.__qualname__ = cls.__qualname__
    get_instance.__name__ = cls.__name__

    return get_instance


# ============================================================================
# Utility Functions for Decorator Composition
# ============================================================================

def compose_decorators(*decorators):
    """
    Compose multiple decorators into a single decorator.

    Args:
        *decorators: Decorators to compose (applied right to left)
    """
    def composed_decorator(func):
        for decorator in reversed(decorators):
            func = decorator(func)
        return func
    return composed_decorator


# Common decorator combinations
def robust_api_endpoint(
    operation_name: Optional[str] = None,
    max_attempts: int = 3,
    rate_limit_calls: int = 100,
    cache_ttl: Optional[float] = None
):
    """
    Pre-composed decorator for robust API endpoints.

    Combines performance monitoring, retry logic, rate limiting, and caching.
    """
    return compose_decorators(
        measure_performance(operation_name=operation_name),
        retry(max_attempts=max_attempts),
        rate_limit(rate_limit_calls, 60.0),  # 60-second window
        memoize(ttl=cache_ttl) if cache_ttl else lambda x: x
    )


# ============================================================================
# Example Usage and Testing
# ============================================================================

if __name__ == "__main__":
    # Example usage of the decorators

    @measure_performance("test_operation")
    @retry(max_attempts=2)
    @memoize(max_size=10, ttl=30.0)
    async def example_async_function(x: int, y: int) -> int:
        """Example function demonstrating decorator composition."""
        if x < 0:
            raise ValueError("x must be positive")
        await asyncio.sleep(0.1)  # Simulate work
        return x + y

    @validate_args(
        name=lambda x: len(x) > 0,
        age=lambda x: 0 <= x <= 150
    )
    def create_user(name: str, age: int) -> dict:
        """Example function with argument validation."""
        return {"name": name, "age": age}

    @singleton
    class ConfigManager:
        """Example singleton class."""
        def __init__(self):
            self.config = {"initialized": True}

    async def test_decorators():
        """Test the decorator functionality."""
        # Test async function with decorators
        result1 = await example_async_function(5, 3)
        result2 = await example_async_function(5, 3)  # Should be cached
        assert result1 == result2 == 8

        # Test validation decorator
        user = create_user("Alice", 30)
        assert user["name"] == "Alice"

        try:
            create_user("", 30)  # Should fail validation
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        # Test singleton
        config1 = ConfigManager.sync()
        config2 = ConfigManager.sync()
        assert config1 is config2

        print("All decorator tests passed!")

    # Run tests
    asyncio.run(test_decorators())
