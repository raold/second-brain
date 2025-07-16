"""
Async retry utilities with exponential backoff and circuit breaker pattern.
Provides granular error handling for async operations.
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Optional, Tuple, Type, Union, Any
from dataclasses import dataclass
from enum import Enum

from app.utils.exceptions import (
    SecondBrainError, AsyncOperationError, CircuitBreakerError,
    is_retryable_error, get_retry_delay, map_external_exception
)
from app.utils.logger import get_logger

logger = get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3  # Successes needed to close circuit


class CircuitBreaker:
    """Circuit breaker implementation for async operations."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed after recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} reopened during recovery")


# Global circuit breakers
_circuit_breakers = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig()
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def async_retry(
    config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
):
    """
    Decorator for async functions with retry logic and circuit breaker.
    
    Args:
        config: Retry configuration
        circuit_breaker_name: Name for circuit breaker (optional)
        circuit_breaker_config: Circuit breaker configuration
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = None
            if circuit_breaker_name:
                circuit_breaker = get_circuit_breaker(circuit_breaker_name, circuit_breaker_config)
            
            last_exception = None
            
            for attempt in range(config.max_attempts):
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.can_execute():
                    raise CircuitBreakerError(circuit_breaker_name, circuit_breaker.failure_count)
                
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Map to our exception hierarchy
                    mapped_exc = map_external_exception(e)
                    
                    # Record failure in circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Check if we should retry
                    if not is_retryable_error(mapped_exc):
                        logger.warning(f"Non-retryable error in {func.__name__}: {mapped_exc}")
                        raise mapped_exc
                    
                    # Check if we've exhausted attempts
                    if attempt == config.max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {config.max_attempts} attempts")
                        raise mapped_exc
                    
                    # Calculate delay
                    delay = get_retry_delay(mapped_exc)
                    if delay is None:
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                    
                    # Add jitter
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}/{config.max_attempts}, "
                        f"retrying in {delay:.2f}s: {mapped_exc}"
                    )
                    
                    await asyncio.sleep(delay)
            
            # This shouldn't be reached, but just in case
            raise last_exception or SecondBrainError("Unexpected retry loop termination")
        
        return wrapper
    return decorator


def async_timeout(seconds: float, operation_name: str = "operation"):
    """
    Decorator to add timeout to async functions.
    
    Args:
        seconds: Timeout in seconds
        operation_name: Name of operation for error messages
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                from app.utils.exceptions import DatabaseTimeoutError
                raise DatabaseTimeoutError(
                    f"{operation_name} timed out after {seconds} seconds",
                    operation_name,
                    seconds
                )
        return wrapper
    return decorator


def async_with_semaphore(max_concurrent: int, operation_name: str = "operation"):
    """
    Decorator to limit concurrent executions of an async function.
    
    Args:
        max_concurrent: Maximum concurrent executions
        operation_name: Name of operation for error messages
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if semaphore.locked():
                from app.utils.exceptions import ConcurrencyLimitError
                raise ConcurrencyLimitError(
                    f"Too many concurrent {operation_name} operations",
                    max_concurrent,
                    max_concurrent
                )
            
            async with semaphore:
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience decorators with common configurations
def database_retry(circuit_breaker_name: Optional[str] = None):
    """Retry decorator optimized for database operations."""
    return async_retry(
        config=RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0
        ),
        circuit_breaker_name=circuit_breaker_name,
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2
        )
    )


def api_retry(circuit_breaker_name: Optional[str] = None):
    """Retry decorator optimized for API operations."""
    return async_retry(
        config=RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0
        ),
        circuit_breaker_name=circuit_breaker_name,
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2
        )
    )


def vector_store_retry(circuit_breaker_name: Optional[str] = None):
    """Retry decorator optimized for vector store operations."""
    return async_retry(
        config=RetryConfig(
            max_attempts=3,
            base_delay=1.5,
            max_delay=45.0,
            exponential_base=2.0
        ),
        circuit_breaker_name=circuit_breaker_name,
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=4,
            recovery_timeout=45.0,
            success_threshold=2
        )
    ) 