"""
Test configuration and fixtures for the Second Brain application.
"""

import os
import sys

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Set up test environment - Force override any existing values
os.environ["USE_MOCK_DATABASE"] = "true"
os.environ["API_TOKENS"] = "test-key-1,test-key-2"

# Ensure the app gets the test values by clearing any cached imports
modules_to_clear = ["app.app", "app.database", "app.database_mock"]
for module in modules_to_clear:
    if module in sys.modules:
        del sys.modules[module]

# Import after environment is set (required for test configuration)
from app.app import app  # noqa: E402
from app.database_mock import MockDatabase  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def api_key():
    """Get API key for testing."""
    return "test-key-1"


@pytest_asyncio.fixture(scope="function")
async def db():
    """Get mock database instance for testing."""
    mock_db = MockDatabase()
    await mock_db.initialize()
    yield mock_db
