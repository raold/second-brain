"""
Test configuration and fixtures for the Second Brain application.
Provides comprehensive mocking and CI-ready test infrastructure.
"""

import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Force test environment before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["SECURITY_LEVEL"] = "development"
os.environ["API_TOKENS"] = (
    "test-token-32-chars-long-for-auth-1234567890abcdef,test-token-32-chars-long-for-auth-0987654321fedcba"
)
os.environ["API_KEY"] = "test-token-32-chars-long-for-auth-1234567890abcdef"
os.environ["OPENAI_API_KEY"] = "test-key-mock-for-ci-pipeline-testing"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

# Disable external service connections in tests
os.environ["DISABLE_EXTERNAL_SERVICES"] = "true"
os.environ["MOCK_EXTERNAL_APIS"] = "true"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Clear any cached imports to ensure clean test environment
modules_to_clear = [
    "app.app",
    "app.database",
    "app.security",
    "app.connection_pool",
    "app.core.redis_manager",
]
for module in modules_to_clear:
    if module in sys.modules:
        del sys.modules[module]


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_key():
    """Test API key for authentication."""
    return "test-token-32-chars-long-for-auth-1234567890abcdef"


@pytest.fixture
def test_headers(api_key):
    """Standard test headers with authentication."""
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


@pytest_asyncio.fixture
async def mock_database():
    """Mock database with all necessary methods for testing."""
    mock_db = AsyncMock()

    # Setup common database methods
    mock_db.initialize = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.create_memory = AsyncMock()
    mock_db.get_memory = AsyncMock()
    mock_db.update_memory = AsyncMock()
    mock_db.delete_memory = AsyncMock()
    mock_db.list_memories = AsyncMock(return_value=[])
    mock_db.search_memories = AsyncMock(return_value=[])
    mock_db.create_user = AsyncMock()
    mock_db.get_user = AsyncMock()
    mock_db.create_session = AsyncMock()
    mock_db.get_session = AsyncMock()

    # Mock database connection pool
    mock_pool = AsyncMock()
    mock_connection = AsyncMock()
    mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
    mock_connection.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire.return_value = mock_connection
    mock_db.pool = mock_pool

    yield mock_db


@pytest_asyncio.fixture
async def mock_openai_client():
    """Mock OpenAI client for testing without API calls."""
    mock_client = AsyncMock()

    # Mock embeddings
    mock_embeddings = AsyncMock()
    mock_embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
    )
    mock_client.embeddings = mock_embeddings

    # Mock chat completions
    mock_chat = AsyncMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Test response from OpenAI"))]
    mock_chat.completions.create = AsyncMock(return_value=mock_completion)
    mock_client.chat = mock_chat

    yield mock_client


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client for testing without Redis connection."""
    mock_redis = AsyncMock()

    # Mock Redis operations
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.close = AsyncMock()

    yield mock_redis


@pytest_asyncio.fixture
async def app_with_mocks(mock_database, mock_openai_client, mock_redis):
    """FastAPI app with all external dependencies mocked."""
    with (
        patch("app.database.get_database", return_value=mock_database),
        patch("app.utils.openai_client.get_openai_client", return_value=mock_openai_client),
        patch("app.core.redis_manager.get_redis", return_value=mock_redis),
    ):

        from app.app import app

        yield app


@pytest_asyncio.fixture
async def client(app_with_mocks):
    """Async HTTP client for testing with mocked dependencies."""
    async with AsyncClient(app=app_with_mocks, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing."""
    return {
        "title": "Test Memory",
        "content": "This is a test memory for CI pipeline",
        "memory_type": "note",
        "tags": ["test", "ci"],
        "importance_score": 0.7,
        "metadata": {"source": "test"},
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {"username": "testuser", "email": "test@example.com", "full_name": "Test User"}


@pytest_asyncio.fixture
async def isolated_test_environment():
    """Isolated test environment with cleanup."""
    # Setup
    test_data = {}

    yield test_data

    # Cleanup
    test_data.clear()


@pytest.fixture
def timeout_config():
    """Timeout configuration for CI tests."""
    return {
        "short_timeout": 5.0,  # Quick operations
        "medium_timeout": 15.0,  # API calls
        "long_timeout": 30.0,  # Complex operations
    }


@pytest.fixture
def retry_config():
    """Retry configuration for flaky tests."""
    return {
        "max_retries": 3,
        "backoff_factor": 0.5,
        "retry_exceptions": (ConnectionError, TimeoutError),
    }


@pytest.fixture(autouse=True)
def mock_external_services():
    """Auto-mock external services to prevent network calls in CI."""
    with (
        patch("httpx.AsyncClient") as mock_client,
        patch("openai.AsyncOpenAI") as mock_openai,
        patch("redis.asyncio.Redis") as mock_redis_client,
        patch("asyncpg.create_pool") as mock_pg_pool,
    ):

        # Setup mock responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "mocked"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        yield {
            "http_client": mock_client,
            "openai_client": mock_openai,
            "redis_client": mock_redis_client,
            "pg_pool": mock_pg_pool,
        }


@pytest.fixture
def ci_environment_check():
    """Check if running in CI environment and adjust behavior."""
    is_ci = os.getenv("CI", "").lower() in ("true", "1", "yes")
    github_actions = os.getenv("GITHUB_ACTIONS", "").lower() == "true"

    return {
        "is_ci": is_ci,
        "is_github_actions": github_actions,
        "should_skip_integration": is_ci and not os.getenv("RUN_INTEGRATION_TESTS"),
        "timeout_multiplier": 2.0 if is_ci else 1.0,
    }


@pytest.fixture
def performance_metrics():
    """Track performance metrics during tests."""
    import time

    start_time = time.time()

    yield {"start_time": start_time, "get_elapsed": lambda: time.time() - start_time}


class MockDependencies:
    """Container for mock dependencies used across tests."""

    def __init__(self):
        self.database = AsyncMock()
        self.openai_client = AsyncMock()
        self.redis_client = AsyncMock()
        self.setup_defaults()

    def setup_defaults(self):
        """Setup default mock responses."""
        # Database defaults
        self.database.list_memories.return_value = []
        self.database.get_memory.return_value = None

        # OpenAI defaults
        embedding_response = MagicMock()
        embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        self.openai_client.embeddings.create.return_value = embedding_response

        # Redis defaults
        self.redis_client.get.return_value = None
        self.redis_client.set.return_value = True


@pytest.fixture
def mock_deps():
    """Centralized mock dependencies."""
    return MockDependencies()


# Pytest markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.validation = pytest.mark.validation
pytest.mark.slow = pytest.mark.slow
pytest.mark.ci_skip = pytest.mark.skipif(
    os.getenv("CI", "").lower() in ("true", "1", "yes"), reason="Skipped in CI environment"
)
