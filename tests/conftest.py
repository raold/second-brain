"""
Test configuration and fixtures for the Second Brain application.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Add project root to path first
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import platform context for intelligent environment setup
from app.utils.platform_context import (
    PlatformDetector, 
    EnvironmentManager,
    get_platform_context,
    is_ci,
    is_mock_database
)

# Get platform context
context = get_platform_context()

# Print context in verbose mode
if os.getenv("PYTEST_VERBOSE", "").lower() == "true":
    EnvironmentManager.print_context()

# Setup test environment with platform awareness
EnvironmentManager.setup_test_environment()

# Platform-specific test configuration
if context.is_ci:
    # CI/CD environment (GitHub Actions, etc.)
    os.environ["USE_MOCK_DATABASE"] = "true"  # Always use mock in CI
    os.environ["LOG_LEVEL"] = "WARNING"  # Less verbose
    os.environ["PYTEST_TIMEOUT"] = "30"  # Shorter timeout
elif not context.database_available:
    # Local dev without database
    os.environ["USE_MOCK_DATABASE"] = "true"
    print(f"[INFO] No {context.database_type.value} database detected, using mock database")
else:
    # Local dev with database available
    use_mock = os.environ.get("USE_MOCK_DATABASE", "false")
    print(f"[INFO] {context.database_type.value} database available, mock={use_mock}")

# Security and API configuration
os.environ.setdefault("SECURITY_LEVEL", "development")
os.environ.setdefault("API_TOKENS", "test-token-32-chars-long-for-auth-1234567890abcdef,test-token-32-chars-long-for-auth-0987654321fedcba")
os.environ.setdefault("API_KEY", "test-token-32-chars-long-for-auth-1234567890abcdef")

# Use real OpenAI key if available (from GitHub secrets), otherwise use mock
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test-key-mock"

# Database configuration (platform-aware)
if context.database_type.value == "postgresql":
    os.environ.setdefault("POSTGRES_USER", "secondbrain")
    os.environ.setdefault("POSTGRES_PASSWORD", "changeme")
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_DB", "secondbrain")

# Path is already added at the top of file

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
    """Async HTTP client for testing (platform-aware)."""
    context = get_platform_context()
    
    # Platform-specific client configuration
    timeout = 30.0 if context.is_ci else 60.0
    
    async with AsyncClient(
        app=app, 
        base_url="http://test",
        timeout=timeout
    ) as ac:
        yield ac


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-token-32-chars-long-for-auth-1234567890abcdef"


@pytest_asyncio.fixture
async def mock_database():
    """Mock database instance for testing (always available)."""
    from app.database_mock import MockDatabase
    
    context = get_platform_context()
    mock_db = MockDatabase()
    
    # Add platform context to mock database
    mock_db.platform_context = context
    
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
    """Database fixture that intelligently chooses backend."""
    context = get_platform_context()
    
    if is_mock_database():
        # Use mock database
        from app.database_mock import MockDatabase
        mock_db = MockDatabase()
        mock_db.platform_context = context
        await mock_db.initialize()
        yield mock_db
        await mock_db.close()
    else:
        # Use real database
        from app.database import get_database
        real_db = await get_database()
        yield real_db
        # Real database manages its own lifecycle


@pytest.fixture
def mock_external_services(monkeypatch):
    """Mock external services for testing."""
    # Mock any external service calls if needed
    # No Redis to mock anymore
    pass
