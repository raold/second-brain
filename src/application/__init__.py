"""
Application layer for Second Brain.

Contains use cases, services, and DTOs.
"""

from .dependencies import Dependencies, get_dependencies
from .exceptions import (
    ApplicationError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
)

__all__ = [
    "Dependencies",
    "get_dependencies",
    "ApplicationError",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
]