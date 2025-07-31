"""
Centralized exception handling for Second Brain v3.0.0

This module provides:
- Custom exception hierarchy
- Error codes and messages
- Exception handlers for FastAPI
- Structured error responses
"""

import traceback
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for the application"""

    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    QUERY_ERROR = "QUERY_ERROR"

    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT = "TIMEOUT"

    # Business logic errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorResponse(BaseModel):
    """Standardized error response format"""

    error_code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    timestamp: str = None
    request_id: str | None = None

    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)


class SecondBrainException(Exception):
    """Base exception for all Second Brain custom exceptions"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_error_response(self, request_id: str | None = None) -> ErrorResponse:
        """Convert exception to error response"""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            request_id=request_id
        )


# Authentication & Authorization Exceptions
class UnauthorizedException(SecondBrainException):
    """Raised when authentication is required but not provided"""

    def __init__(self, message: str = "Authentication required", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class ForbiddenException(SecondBrainException):
    """Raised when user lacks permission for requested resource"""

    def __init__(self, message: str = "Access forbidden", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidTokenException(SecondBrainException):
    """Raised when provided token is invalid"""

    def __init__(self, message: str = "Invalid token", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_TOKEN,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


# Resource Exceptions
class NotFoundException(SecondBrainException):
    """Raised when requested resource is not found"""

    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"

        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier) if identifier else None}
        )


class AlreadyExistsException(SecondBrainException):
    """Raised when attempting to create a resource that already exists"""

    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} already exists"
        if identifier:
            message = f"{resource} with identifier '{identifier}' already exists"

        super().__init__(
            message=message,
            error_code=ErrorCode.ALREADY_EXISTS,
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "identifier": str(identifier) if identifier else None}
        )


class ConflictException(SecondBrainException):
    """Raised when operation would cause a conflict"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


# Validation Exceptions
class ValidationException(SecondBrainException):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        if not details:
            details = {}
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


# Database Exceptions
class DatabaseException(SecondBrainException):
    """Base exception for database-related errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails"""

    def __init__(self, message: str = "Database connection failed", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details
        )
        self.error_code = ErrorCode.CONNECTION_ERROR


# Service Exceptions
class ServiceUnavailableException(SecondBrainException):
    """Raised when a service is temporarily unavailable"""

    def __init__(self, service: str, message: str | None = None):
        if not message:
            message = f"{service} service is temporarily unavailable"

        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service}
        )


class ExternalServiceException(SecondBrainException):
    """Raised when external service call fails"""

    def __init__(self, service: str, message: str, details: dict[str, Any] | None = None):
        if not details:
            details = {}
        details["service"] = service

        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class TimeoutException(SecondBrainException):
    """Raised when operation times out"""

    def __init__(self, operation: str, timeout_seconds: float | None = None):
        message = f"Operation '{operation}' timed out"
        details = {"operation": operation}

        if timeout_seconds:
            message += f" after {timeout_seconds} seconds"
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details
        )


# Business Logic Exceptions
class BusinessRuleViolationException(SecondBrainException):
    """Raised when business rule is violated"""

    def __init__(self, rule: str, message: str | None = None, details: dict[str, Any] | None = None):
        if not message:
            message = f"Business rule violation: {rule}"

        if not details:
            details = {}
        details["rule"] = rule

        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class RateLimitExceededException(SecondBrainException):
    """Raised when rate limit is exceeded"""

    def __init__(self, limit: int, window: str, retry_after: int | None = None):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        details = {
            "limit": limit,
            "window": window
        }

        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# Exception Handlers for FastAPI
async def second_brain_exception_handler(request: Request, exc: SecondBrainException) -> JSONResponse:
    """Handle SecondBrainException and return structured error response"""

    # Extract request ID from headers or generate one
    request_id = request.headers.get("X-Request-ID", str(datetime.utcnow().timestamp()))

    # Log the exception
    logger.error(
        f"SecondBrainException: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )

    # Create error response
    error_response = exc.to_error_response(request_id=request_id)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers={
            "X-Request-ID": request_id
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions and return structured error response"""

    # Extract request ID
    request_id = request.headers.get("X-Request-ID", str(datetime.utcnow().timestamp()))

    # Log the full exception with traceback
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )

    # Create generic error response
    error_response = ErrorResponse(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        details={
            "type": type(exc).__name__,
            "message": str(exc) if not isinstance(exc, Exception) or str(exc) else None
        },
        request_id=request_id
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
        headers={
            "X-Request-ID": request_id
        }
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation exceptions"""

    request_id = request.headers.get("X-Request-ID", str(datetime.utcnow().timestamp()))

    # Extract validation errors
    errors = []
    if hasattr(exc, 'errors'):
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "validation_error")
            })

    error_response = ErrorResponse(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details={"errors": errors},
        request_id=request_id
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
        headers={
            "X-Request-ID": request_id
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(SecondBrainException, second_brain_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Add HTTP exception handler for better error messages
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = request.headers.get("X-Request-ID", str(datetime.utcnow().timestamp()))

        # Map HTTP status codes to error codes
        status_to_error_code = {
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            422: ErrorCode.VALIDATION_ERROR,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_ERROR,
            502: ErrorCode.EXTERNAL_SERVICE_ERROR,
            503: ErrorCode.SERVICE_UNAVAILABLE,
            504: ErrorCode.TIMEOUT
        }

        error_code = status_to_error_code.get(exc.status_code, ErrorCode.UNKNOWN_ERROR)

        error_response = ErrorResponse(
            error_code=error_code,
            message=exc.detail,
            request_id=request_id
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers={
                "X-Request-ID": request_id
            }
        )
