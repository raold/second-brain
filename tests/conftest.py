"""
Test configuration and fixtures for the Second Brain application.
"""

import os
import sys

import pytest
import pytest_asyncio
from httpx import AsyncClient


# Set up test environment BEFORE any imports
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run."""
    # Set up test environment - Force override any existing values
    os.environ["USE_MOCK_DATABASE"] = "true"
    os.environ["API_TOKENS"] = "test-key-1,test-key-2"
    os.environ["OPENAI_API_KEY"] = "test-key-mock"
    os.environ["POSTGRES_USER"] = "test"
    os.environ["POSTGRES_PASSWORD"] = "test"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "test"

    # Ensure the app gets the test values by clearing any cached imports
    modules_to_clear = [
        "app.app",
        "app.database",
        "app.database_mock",
        "app.security",
        "app.connection_pool",
        "app.dashboard",
        "app.docs",
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]


# Import after environment setup
from app.app import app  # noqa: E402
from app.database_mock import MockDatabase  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-key-1"


@pytest.fixture
def mock_database():
    """Mock database instance for testing."""
    return MockDatabase()


@pytest_asyncio.fixture
async def initialized_mock_db():
    """Initialized mock database."""
    db = MockDatabase()
    await db.initialize()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def db():
    """Database fixture for edge case tests (alias for initialized_mock_db)."""
    db = MockDatabase()
    await db.initialize()
    yield db
    await db.close()
