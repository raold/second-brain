"""
Test configuration and fixtures for the Second Brain application.
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Force test environment before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_MOCK_DATABASE"] = "true"  # Use mock database for tests
os.environ["SECURITY_LEVEL"] = "development"
os.environ["API_TOKENS"] = "test-token-32-chars-long-for-auth-1234567890abcdef,test-token-32-chars-long-for-auth-0987654321fedcba"
# Use real OpenAI key if available (from GitHub secrets), otherwise use mock
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test-key-mock"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["POSTGRES_USER"] = "secondbrain"
os.environ["POSTGRES_PASSWORD"] = "changeme"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "secondbrain"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Clear any cached imports
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
from app.app import app
# MockDatabase removed - using real database with test environment


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-token-32-chars-long-for-auth-1234567890abcdef"


@pytest_asyncio.fixture
async def mock_database():
    """Mock database instance for testing."""
    from app.database_mock import MockDatabase
    mock_db = MockDatabase()
    await mock_db.initialize()
    yield mock_db
    await mock_db.close()


@pytest_asyncio.fixture
async def initialized_mock_db():
    """Initialized mock database."""
    from app.database_mock import MockDatabase
    mock_db = MockDatabase()
    await mock_db.initialize()
    yield mock_db
    await mock_db.close()


@pytest_asyncio.fixture
async def db():
    """Database fixture for edge case tests (alias for initialized_mock_db)."""
    from app.database_mock import MockDatabase
    mock_db = MockDatabase()
    await mock_db.initialize()
    yield mock_db
    await mock_db.close()
