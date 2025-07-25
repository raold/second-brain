"""
API dependencies.

FastAPI dependency injection functions.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.application import Dependencies
from src.application.exceptions import AuthenticationError
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()


async def get_dependencies(request: Request) -> Dependencies:
    """
    Get application dependencies from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Dependencies container
    """
    return request.app.state.dependencies


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> UUID:
    """
    Get current user ID from token.
    
    Args:
        credentials: HTTP authorization credentials
        deps: Application dependencies
        
    Returns:
        User ID
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # In production, validate JWT token properly
        # For now, extract user ID from token
        token = credentials.credentials
        
        if not token.startswith("access_"):
            raise AuthenticationError("Invalid token format")
        
        user_id_str = token.replace("access_", "")
        user_id = UUID(user_id_str)
        
        # Verify user exists
        user_repo = await deps.get_user_repository()
        user = await user_repo.get(user_id)
        
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        return user_id
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user_id(
    authorization: Optional[str] = Header(None),
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
) -> Optional[UUID]:
    """
    Get optional user ID from token.
    
    Args:
        authorization: Authorization header
        deps: Application dependencies
        
    Returns:
        User ID if authenticated, None otherwise
    """
    if not authorization:
        return None
    
    try:
        # Parse bearer token
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            return None
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme=scheme,
            credentials=token,
        )
        
        # Get user ID
        return await get_current_user_id(credentials, deps)
        
    except Exception:
        return None


class Pagination:
    """Pagination parameters dependency."""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100,
    ):
        """
        Initialize pagination parameters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            max_page_size: Maximum allowed page size
        """
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page must be >= 1",
            )
        
        if page_size < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page size must be >= 1",
            )
        
        if page_size > max_page_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Page size must be <= {max_page_size}",
            )
        
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


async def require_admin(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> UUID:
    """
    Require admin role for access.
    
    Args:
        user_id: Current user ID
        deps: Application dependencies
        
    Returns:
        User ID if admin
        
    Raises:
        HTTPException: If not admin
    """
    user_repo = await deps.get_user_repository()
    user = await user_repo.get(user_id)
    
    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user_id