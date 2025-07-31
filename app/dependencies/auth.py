"""
Authentication dependencies for FastAPI routes
"""


from fastapi import Depends, Header

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


async def verify_api_key(api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """
    Verify the API key is valid

    Args:
        api_key: API key from header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is invalid
    """
    # Stub implementation - always return valid
    logger.info("API key verification (stub)")
    return api_key or "default-api-key"


async def get_current_user(api_key: str = Depends(verify_api_key)) -> dict[str, str]:
    """
    Get the current user from the API key

    Args:
        api_key: Validated API key

    Returns:
        User information dict
    """
    # Stub implementation - return default user
    return {
        "user_id": "default-user",
        "username": "Default User",
        "email": "user@example.com"
    }


async def get_db_instance():
    """
    Get database instance

    Returns:
        Database instance (stub returns None)
    """
    # Stub implementation
    logger.info("Getting database instance (stub)")
    return None


async def get_db():
    """Get database instance - alias for get_db_instance"""
    return await get_db_instance()


async def get_redis_instance():
    """
    Get Redis instance

    Returns:
        Redis instance (stub returns None)
    """
    # Stub implementation
    logger.info("Getting Redis instance (stub)")
    return None
