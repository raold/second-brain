"""
Shared utilities for the Second Brain application.
Contains commonly used functions that need to be shared across modules.
"""

import os
import logging
from fastapi import HTTPException, Query

logger = logging.getLogger(__name__)

# Global mock database instance for testing
_mock_db_instance = None

async def get_db_instance():
    """Get database instance (mock or real)."""
    global _mock_db_instance
    
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        if _mock_db_instance is None:
            logger.info("Creating mock database instance for testing")
            from app.database_mock import MockDatabase
            _mock_db_instance = MockDatabase()
            await _mock_db_instance.initialize()
        return _mock_db_instance
    else:
        from app.database import get_database
        return await get_database()


async def verify_api_key(api_key: str = Query(..., alias="api_key")):
    """Simple API key authentication."""
    # Allow bypassing authentication in test mode
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        valid_tokens = ["test-key-1", "test-key-2"]
    else:
        valid_tokens = os.getenv("API_TOKENS", "").split(",")
        valid_tokens = [token.strip() for token in valid_tokens if token.strip()]

    if not valid_tokens or api_key not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
