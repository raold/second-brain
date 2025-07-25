"""
Pytest configuration for v3.0.0 tests.

Provides fixtures and test configuration for the entire test suite.
"""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.application import Dependencies
from src.domain.models.memory import Memory, MemoryId, MemoryType
from src.domain.models.session import Session as DomainSession, SessionId
from src.domain.models.tag import Tag, TagId
from src.domain.models.user import User, UserId, UserRole
from src.infrastructure.caching import Cache
from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.models import Base
from src.infrastructure.embeddings import EmbeddingClient
from src.infrastructure.messaging import MessageBroker
from src.infrastructure.storage import StorageClient

from .fixtures.mocks import (
    MockCache,
    MockEmbeddingClient,
    MockMemoryRepository,
    MockMessageBroker,
    MockStorageClient,
)


# Test database URLs
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/secondbrain_test"
)
TEST_DATABASE_URL_SYNC = TEST_DATABASE_URL.replace("+asyncpg", "")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL_SYNC)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_test_engine():
    """Create async test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create database session for tests."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest_asyncio.fixture
async def async_db_session(async_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(async_test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def db_connection(async_test_engine) -> AsyncGenerator[DatabaseConnection, None]:
    """Create database connection for tests."""
    conn = DatabaseConnection(str(async_test_engine.url))
    await conn.connect()
    yield conn
    await conn.disconnect()


@pytest_asyncio.fixture
async def cache() -> AsyncGenerator[Cache, None]:
    """Create cache instance for tests."""
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        cache = MockCache()
    else:
        cache = Cache(
            host=os.getenv("TEST_REDIS_HOST", "localhost"),
            port=int(os.getenv("TEST_REDIS_PORT", "6379")),
            db=int(os.getenv("TEST_REDIS_DB", "1")),
        )
    
    await cache.connect()
    yield cache
    await cache.flush()  # Clear test data
    await cache.disconnect()


@pytest_asyncio.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Create message broker for tests."""
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        broker = MockMessageBroker()
    else:
        broker = MessageBroker(
            url=os.getenv(
                "TEST_RABBITMQ_URL",
                "amqp://test:test@localhost:5672/test"
            )
        )
    
    await broker.connect()
    yield broker
    await broker.disconnect()


@pytest_asyncio.fixture
async def storage_client() -> AsyncGenerator[StorageClient, None]:
    """Create storage client for tests."""
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        client = MockStorageClient()
    else:
        client = StorageClient(
            endpoint=os.getenv("TEST_MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("TEST_MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("TEST_MINIO_SECRET_KEY", "minioadmin"),
            secure=False,
        )
    
    await client.connect()
    
    # Create test bucket
    test_bucket = "test-bucket"
    if not await client.bucket_exists(test_bucket):
        await client.create_bucket(test_bucket)
    
    yield client
    
    # Clean up test bucket
    await client.remove_bucket(test_bucket, force=True)
    await client.disconnect()


@pytest.fixture
def embedding_client() -> EmbeddingClient:
    """Create embedding client for tests."""
    if os.getenv("MOCK_EMBEDDINGS", "false").lower() == "true":
        return MockEmbeddingClient()
    else:
        # Use local model for tests to avoid API calls
        return EmbeddingClient(model="local")


@pytest_asyncio.fixture
async def dependencies(
    db_connection,
    cache,
    message_broker,
    storage_client,
    embedding_client,
) -> AsyncGenerator[Dependencies, None]:
    """Create application dependencies for tests."""
    deps = Dependencies()
    
    # Set test dependencies
    deps._db_connection = db_connection
    deps._cache = cache
    deps._message_broker = message_broker
    deps._storage_client = storage_client
    deps._embedding_client = embedding_client
    
    yield deps


# Test data fixtures

@pytest.fixture
def test_user_id() -> UUID:
    """Get test user ID."""
    return uuid4()


@pytest.fixture
def test_user(test_user_id) -> User:
    """Create test user."""
    return User(
        id=UserId(test_user_id),
        email="test@example.com",
        username="testuser",
        password_hash="$2b$12$test_hash",
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def test_memory(test_user_id) -> Memory:
    """Create test memory."""
    return Memory(
        id=MemoryId(uuid4()),
        user_id=test_user_id,
        title="Test Memory",
        content="This is test memory content.",
        memory_type=MemoryType.FACT,
        importance_score=0.7,
        confidence_score=0.9,
        source_url="https://example.com",
        metadata={"test": True},
    )


@pytest.fixture
def test_session(test_user_id) -> DomainSession:
    """Create test session."""
    return DomainSession(
        id=SessionId(uuid4()),
        user_id=test_user_id,
        title="Test Session",
        description="This is a test session.",
        is_active=True,
    )


@pytest.fixture
def test_tag(test_user_id) -> Tag:
    """Create test tag."""
    return Tag(
        id=TagId(uuid4()),
        name="test-tag",
        user_id=test_user_id,
        color="#FF5733",
        icon="🏷️",
        description="Test tag for unit tests",
    )


# Utility fixtures

@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime for consistent testing."""
    class MockDatetime:
        @staticmethod
        def utcnow():
            return datetime(2024, 1, 15, 12, 0, 0)
        
        @staticmethod
        def now():
            return datetime(2024, 1, 15, 12, 0, 0)
    
    monkeypatch.setattr("datetime.datetime", MockDatetime)
    return MockDatetime


@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing."""
    def _create_file(name: str, content: str = "") -> str:
        file_path = tmp_path / name
        file_path.write_text(content)
        return str(file_path)
    
    return _create_file


# Async test markers

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "requires_real_db: Tests that require real database"
    )