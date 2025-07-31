"""
Common dependencies for FastAPI routes
"""

from typing import Optional
from fastapi import Depends, HTTPException, Header
from app.models.memory import User
from app.shared import get_db_instance
from typing import Optional
from fastapi import Depends
from fastapi import HTTPException


async def get_db():
    """Get database instance"""
    return await get_db_instance()


# Alias for backwards compatibility
get_database = get_db_instance


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> User:
    """
    Get current user from authorization header.
    For now, returns a demo user. In production, implement proper auth.
    """
    # Demo user for development
    return User(
        id="demo-user",
        email="demo@example.com",
        username="demo"
    )