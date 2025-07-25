"""
Application layer exceptions.

Defines exceptions for use case failures.
"""

from typing import Any, Optional


class ApplicationError(Exception):
    """Base class for application errors."""
    
    def __init__(self, message: str, code: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize application error.
        
        Args:
            message: Error message
            code: Error code for identification
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class NotFoundError(ApplicationError):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, identifier: str):
        """
        Initialize not found error.
        
        Args:
            resource: Type of resource
            identifier: Resource identifier
        """
        super().__init__(
            f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class ValidationError(ApplicationError):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        """
        Initialize validation error.
        
        Args:
            message: Validation error message
            field: Field that failed validation
            value: Invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
            
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        """
        Initialize authentication error.
        
        Args:
            message: Error message
        """
        super().__init__(
            message,
            code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(ApplicationError):
    """Raised when authorization fails."""
    
    def __init__(self, action: str, resource: str):
        """
        Initialize authorization error.
        
        Args:
            action: Action being attempted
            resource: Resource being accessed
        """
        super().__init__(
            f"Not authorized to {action} {resource}",
            code="AUTHORIZATION_ERROR",
            details={"action": action, "resource": resource}
        )


class ConflictError(ApplicationError):
    """Raised when there's a resource conflict."""
    
    def __init__(self, message: str, resource: str, identifier: str):
        """
        Initialize conflict error.
        
        Args:
            message: Error message
            resource: Type of resource
            identifier: Resource identifier
        """
        super().__init__(
            message,
            code="CONFLICT",
            details={"resource": resource, "identifier": identifier}
        )


class QuotaExceededError(ApplicationError):
    """Raised when a quota is exceeded."""
    
    def __init__(self, resource: str, limit: int, current: int):
        """
        Initialize quota exceeded error.
        
        Args:
            resource: Resource type
            limit: Maximum allowed
            current: Current usage
        """
        super().__init__(
            f"{resource} quota exceeded. Limit: {limit}, Current: {current}",
            code="QUOTA_EXCEEDED",
            details={"resource": resource, "limit": limit, "current": current}
        )