"""
FastAPI Dependencies - Clean implementation
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader


# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key - simple implementation for now."""
    # For now, accept any non-empty API key
    # In production, check against database or environment variable
    if not api_key:
        # Allow requests without API key for development
        return "dev-key"
    return api_key


async def get_current_user(api_key: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get current user from API key."""
    # Simple implementation - return a default user
    return {
        "id": "default-user",
        "api_key": api_key,
        "is_authenticated": True
    }


# Service dependencies
def get_memory_service():
    """Get memory service instance."""
    # Import here to avoid circular imports
    from app.services.memory_service import MemoryService
    return MemoryService()


def get_health_service():
    """Get health service instance."""
    # Simple mock for now
    class HealthService:
        async def check_health(self):
            return {"status": "healthy", "database": "connected"}
    
    return HealthService()


def get_session_service():
    """Get session service instance."""
    # Simple mock for now
    class SessionService:
        async def create_session(self, user_id: str):
            return {"session_id": "mock-session", "user_id": user_id}
    
    return SessionService()