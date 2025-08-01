"""
Shared utilities and helpers
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


# Re-export verify_api_key for compatibility
from app.dependencies_new import verify_api_key


# Common exceptions
class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)


class BadRequestException(HTTPException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=400, detail=detail)


# Utility functions
def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format."""
    import re
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def sanitize_input(text: str) -> str:
    """Sanitize user input."""
    # Basic sanitization
    return text.strip()[:10000]  # Limit length