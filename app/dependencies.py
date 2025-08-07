"""
FastAPI Dependencies - Single User Implementation
Simplified for single-user-per-container architecture
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from app.config import Config


# API Key header for container access
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_container_access(api_key: str = Security(api_key_header)) -> bool:
    """
    Verify container API key.
    In K8s deployment, this key is injected as environment variable per pod.
    """
    if not api_key:
        # In development, allow no key
        if Config.ENVIRONMENT == "development":
            return True
        raise HTTPException(status_code=401, detail="API key required")
    
    # Check against environment variable (set per container in K8s)
    expected_key = Config.CONTAINER_API_KEY
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True


# Service dependencies - Simple direct instantiation for single-user container
def get_memory_service():
    """Get memory service instance - single instance per container."""
    from app.services.memory_service import MemoryService
    return MemoryService()


