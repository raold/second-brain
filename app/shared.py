"""Shared utilities and dependencies for the application"""


from fastapi import Header, HTTPException

from app.config import get_settings


# Simple replacements for archived functions
async def get_db_instance():
    """Get database instance"""
    from app.database import get_database
    return get_database()


# API key verification for routes that still use it
async def verify_api_key(x_api_key: str | None = Header(None)):
    """Verify API key - simplified version"""
    settings = get_settings()

    # In development/test mode, allow no API key
    if settings.ENVIRONMENT in ["development", "test"]:
        return True

    # In production, require API key
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Simple key verification (in real app would check against database)
    # For now, just check if any key is provided
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True
