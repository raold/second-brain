"""
API exception handlers.

Maps application exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from src.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    QuotaExceededError,
    ValidationError,
)
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle application errors."""
    logger.error(
        "Application error occurred",
        error_code=exc.code,
        error_message=exc.message,
        error_details=exc.details,
        path=request.url.path,
    )
    
    # Map error codes to HTTP status codes
    status_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "QUOTA_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    
    status_code = status_map.get(exc.code, status.HTTP_400_BAD_REQUEST)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Handle authentication errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
        content={
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": exc.message,
            }
        },
    )


async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Handle authorization errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": {
                "code": "AUTHORIZATION_ERROR",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Handle conflict errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "CONFLICT",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def quota_exceeded_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
    """Handle quota exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": "3600"},
        content={
            "error": {
                "code": "QUOTA_EXCEEDED",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.error(
        "Unexpected error occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup exception handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Application exceptions
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(QuotaExceededError, quota_exceeded_handler)
    
    # Generic exception handler
    app.add_exception_handler(Exception, generic_error_handler)