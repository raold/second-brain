"""
Custom exception hierarchy for Second Brain application.
Provides granular error handling for async operations and different failure modes.
"""

import asyncio
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecondBrainError(Exception):
    """Base exception for all Second Brain errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.context = context or {}
        self.timestamp = None  # Will be set by error handler


# === Storage Errors ===
class StorageError(SecondBrainError):
    """Base class for storage-related errors."""
    pass


class DatabaseError(StorageError):
    """Database operation errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection failures."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, ErrorSeverity.HIGH)
        self.retry_after = retry_after


class DatabaseTimeoutError(DatabaseError):
    """Database operation timeout."""
    def __init__(self, message: str, operation: str, timeout_seconds: float):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class DatabaseIntegrityError(DatabaseError):
    """Database integrity constraint violations."""
    def __init__(self, message: str, constraint: Optional[str] = None):
        super().__init__(message, ErrorSeverity.HIGH)
        self.constraint = constraint


class VectorStoreError(StorageError):
    """Vector store (Qdrant) errors."""
    pass


class VectorStoreConnectionError(VectorStoreError):
    """Vector store connection failures."""
    def __init__(self, message: str, host: str, port: int):
        super().__init__(message, ErrorSeverity.HIGH)
        self.host = host
        self.port = port


class VectorStoreTimeoutError(VectorStoreError):
    """Vector store operation timeout."""
    def __init__(self, message: str, operation: str, timeout_seconds: float):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class EmbeddingDimensionError(VectorStoreError):
    """Embedding dimension mismatch."""
    def __init__(self, expected: int, actual: int):
        message = f"Embedding dimension mismatch: expected {expected}, got {actual}"
        super().__init__(message, ErrorSeverity.HIGH)
        self.expected = expected
        self.actual = actual


# === API Errors ===
class APIError(SecondBrainError):
    """Base class for API-related errors."""
    pass


class OpenAIError(APIError):
    """OpenAI API errors."""
    pass


class OpenAIRateLimitError(OpenAIError):
    """OpenAI API rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.retry_after = retry_after


class OpenAIQuotaError(OpenAIError):
    """OpenAI API quota exceeded."""
    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.HIGH)


class OpenAITimeoutError(OpenAIError):
    """OpenAI API timeout."""
    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.timeout_seconds = timeout_seconds


class OpenAIAuthError(OpenAIError):
    """OpenAI API authentication error."""
    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.CRITICAL)


# === Authentication Errors ===
class AuthError(SecondBrainError):
    """Authentication and authorization errors."""
    pass


class InvalidTokenError(AuthError):
    """Invalid or expired token."""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, ErrorSeverity.MEDIUM)


class MissingTokenError(AuthError):
    """Missing authentication token."""
    def __init__(self, message: str = "Missing authentication token"):
        super().__init__(message, ErrorSeverity.MEDIUM)


# === Validation Errors ===
class ValidationError(SecondBrainError):
    """Input validation errors."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, ErrorSeverity.LOW)
        self.field = field


class PayloadValidationError(ValidationError):
    """Payload structure validation error."""
    def __init__(self, message: str, payload_id: Optional[str] = None):
        super().__init__(message)
        self.payload_id = payload_id


# === Async Operation Errors ===
class AsyncOperationError(SecondBrainError):
    """Async operation specific errors."""
    pass


class TaskCancellationError(AsyncOperationError):
    """Async task was cancelled."""
    def __init__(self, message: str, task_name: Optional[str] = None):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.task_name = task_name


class ConcurrencyLimitError(AsyncOperationError):
    """Too many concurrent operations."""
    def __init__(self, message: str, current_count: int, max_count: int):
        super().__init__(message, ErrorSeverity.MEDIUM)
        self.current_count = current_count
        self.max_count = max_count


class CircuitBreakerError(AsyncOperationError):
    """Circuit breaker is open."""
    def __init__(self, service: str, failure_count: int):
        message = f"Circuit breaker open for {service} (failures: {failure_count})"
        super().__init__(message, ErrorSeverity.HIGH)
        self.service = service
        self.failure_count = failure_count


# === Configuration Errors ===
class ConfigurationError(SecondBrainError):
    """Configuration-related errors."""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, ErrorSeverity.CRITICAL)
        self.config_key = config_key


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""
    def __init__(self, config_key: str):
        message = f"Missing required configuration: {config_key}"
        super().__init__(message, config_key=config_key)


# === Business Logic Errors ===
class BusinessLogicError(SecondBrainError):
    """Business logic constraint violations."""
    pass


class DuplicateMemoryError(BusinessLogicError):
    """Attempt to create duplicate memory."""
    def __init__(self, memory_id: str):
        message = f"Memory already exists: {memory_id}"
        super().__init__(message, ErrorSeverity.LOW)
        self.memory_id = memory_id


class MemoryNotFoundError(BusinessLogicError):
    """Memory not found."""
    def __init__(self, memory_id: str):
        message = f"Memory not found: {memory_id}"
        super().__init__(message, ErrorSeverity.LOW)
        self.memory_id = memory_id


# === Utility Functions ===
def map_external_exception(exc: Exception) -> SecondBrainError:
    """Map external exceptions to our custom hierarchy."""
    
    # AsyncPG exceptions
    if "asyncpg" in str(type(exc)):
        if "connection" in str(exc).lower():
            return DatabaseConnectionError(str(exc))
        elif "timeout" in str(exc).lower():
            return DatabaseTimeoutError(str(exc), "unknown", 30.0)
        else:
            return DatabaseError(str(exc))
    
    # Asyncio exceptions
    elif isinstance(exc, asyncio.TimeoutError):
        return DatabaseTimeoutError(str(exc), "async_operation", 30.0)
    elif isinstance(exc, asyncio.CancelledError):
        return TaskCancellationError(str(exc))
    
    # OpenAI exceptions
    elif "openai" in str(type(exc)).lower():
        if "rate" in str(exc).lower():
            return OpenAIRateLimitError(str(exc))
        elif "quota" in str(exc).lower():
            return OpenAIQuotaError(str(exc))
        elif "auth" in str(exc).lower():
            return OpenAIAuthError(str(exc))
        else:
            return OpenAIError(str(exc))
    
    # Default fallback
    else:
        return SecondBrainError(str(exc), ErrorSeverity.MEDIUM)


def is_retryable_error(exc: Exception) -> bool:
    """Determine if an error is retryable."""
    retryable_types = (
        DatabaseConnectionError,
        DatabaseTimeoutError,
        VectorStoreConnectionError,
        VectorStoreTimeoutError,
        OpenAIRateLimitError,
        OpenAITimeoutError,
    )
    
    return isinstance(exc, retryable_types)


def get_retry_delay(exc: Exception) -> Optional[float]:
    """Get suggested retry delay for an error."""
    if hasattr(exc, 'retry_after') and exc.retry_after:
        return float(exc.retry_after)
    
    if isinstance(exc, (DatabaseTimeoutError, VectorStoreTimeoutError)):
        return 5.0  # 5 seconds for timeout errors
    
    if isinstance(exc, (DatabaseConnectionError, VectorStoreConnectionError)):
        return 10.0  # 10 seconds for connection errors
    
    return None 