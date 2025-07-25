# Second Brain v3.0.0 - Testing Guide

## Overview

This guide covers comprehensive testing strategies for Second Brain v3.0.0, including unit tests, integration tests, end-to-end tests, and performance testing.

## Testing Philosophy

1. **Test Pyramid**: Many unit tests, fewer integration tests, minimal E2E tests
2. **Test Behavior**: Focus on what, not how
3. **Fast Feedback**: Quick test execution
4. **Reliable Tests**: No flaky tests
5. **Maintainable**: Easy to understand and modify

## Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── domain/             # Domain logic tests
│   │   ├── models/         # Entity and value object tests
│   │   ├── events/         # Domain event tests
│   │   └── services/       # Domain service tests
│   ├── application/        # Use case tests
│   │   ├── use_cases/      # Business logic tests
│   │   └── dto/            # DTO validation tests
│   └── api/                # API route tests
│       ├── routes/         # Endpoint tests
│       └── middleware/     # Middleware tests
├── integration/            # Tests with real dependencies
│   ├── database/          # Database integration
│   ├── cache/             # Redis integration
│   ├── messaging/         # RabbitMQ integration
│   ├── storage/           # MinIO integration
│   └── external/          # External API integration
├── e2e/                   # End-to-end scenarios
│   ├── workflows/         # Complete user workflows
│   └── api/              # Full API testing
├── performance/           # Performance and load tests
│   ├── benchmarks/       # Performance benchmarks
│   └── load/             # Load testing scenarios
├── fixtures/             # Shared test data
│   ├── factories.py      # Test data factories
│   ├── mocks.py         # Mock implementations
│   └── data/            # Static test data
└── conftest.py          # Pytest configuration
```

## Unit Testing

### Domain Model Tests

```python
# tests/unit/domain/models/test_memory.py
import pytest
from uuid import uuid4
from datetime import datetime
from src.domain.models.memory import Memory
from src.domain.events.memory_events import MemoryCreatedEvent, MemoryUpdatedEvent

class TestMemory:
    """Test Memory aggregate."""
    
    def test_create_memory_success(self):
        """Test successful memory creation."""
        # Arrange
        content = "Test memory content"
        user_id = uuid4()
        tags = ["test", "unit-test"]
        
        # Act
        memory = Memory.create(
            content=content,
            user_id=user_id,
            tags=tags
        )
        
        # Assert
        assert memory.id is not None
        assert memory.content == content
        assert memory.user_id == user_id
        assert memory.tags == tags
        assert memory.version == 1
        assert len(memory._events) == 1
        assert isinstance(memory._events[0], MemoryCreatedEvent)
    
    def test_create_memory_empty_content_raises_error(self):
        """Test memory creation with empty content raises ValueError."""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Memory.create(content="", user_id=user_id)
    
    def test_update_content_success(self):
        """Test successful content update."""
        # Arrange
        memory = Memory.create(
            content="Original content",
            user_id=uuid4()
        )
        memory._events.clear()  # Clear creation event
        new_content = "Updated content"
        
        # Act
        memory.update_content(new_content)
        
        # Assert
        assert memory.content == new_content
        assert memory.version == 2
        assert memory.embedding is None  # Should be cleared
        assert len(memory._events) == 1
        assert isinstance(memory._events[0], MemoryUpdatedEvent)
    
    @pytest.mark.parametrize("invalid_content", [
        "",
        "   ",
        "\t\n",
        None
    ])
    def test_update_content_invalid_raises_error(self, invalid_content):
        """Test content update with invalid values raises error."""
        # Arrange
        memory = Memory.create(
            content="Valid content",
            user_id=uuid4()
        )
        
        # Act & Assert
        with pytest.raises(ValueError):
            memory.update_content(invalid_content)
    
    def test_add_tags_deduplication(self):
        """Test adding tags with deduplication."""
        # Arrange
        memory = Memory.create(
            content="Test content",
            user_id=uuid4(),
            tags=["existing"]
        )
        memory._events.clear()
        
        # Act
        memory.add_tags(["NEW", "existing", "another"])
        
        # Assert
        assert set(memory.tags) == {"existing", "new", "another"}
        assert memory.version == 2
        events = memory.collect_events()
        assert len(events) == 1
        assert events[0].added_tags == ["new", "another"]
```

### Use Case Tests

```python
# tests/unit/application/use_cases/test_memory_use_cases.py
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from src.application.use_cases.memory_use_cases import CreateMemoryUseCase
from src.domain.models.memory import Memory

class TestCreateMemoryUseCase:
    """Test CreateMemoryUseCase."""
    
    @pytest.fixture
    def mock_repository(self):
        repository = Mock()
        repository.save = AsyncMock(side_effect=lambda m: m)
        return repository
    
    @pytest.fixture
    def mock_event_publisher(self):
        publisher = Mock()
        publisher.publish = AsyncMock()
        return publisher
    
    @pytest.fixture
    def use_case(self, mock_repository, mock_event_publisher):
        return CreateMemoryUseCase(
            memory_repository=mock_repository,
            event_publisher=mock_event_publisher
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_repository, mock_event_publisher):
        """Test successful memory creation."""
        # Arrange
        content = "Test memory"
        user_id = uuid4()
        tags = ["test"]
        
        # Act
        result = await use_case.execute(
            content=content,
            user_id=user_id,
            tags=tags
        )
        
        # Assert
        assert isinstance(result, Memory)
        assert result.content == content
        assert result.user_id == user_id
        assert result.tags == tags
        
        # Verify interactions
        mock_repository.save.assert_called_once()
        mock_event_publisher.publish.assert_called_once()
        
        # Verify event was published
        published_events = mock_event_publisher.publish.call_args[0][0]
        assert len(published_events) == 1
        assert published_events[0].event_type == "memory.created"
```

### API Route Tests

```python
# tests/unit/api/routes/test_memories.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from src.api.app import create_app
from src.domain.models.memory import Memory

class TestMemoryRoutes:
    """Test memory API routes."""
    
    @pytest.fixture
    def mock_use_cases(self):
        """Mock use cases."""
        create_use_case = Mock()
        create_use_case.execute = AsyncMock()
        
        get_use_case = Mock()
        get_use_case.execute = AsyncMock()
        
        return {
            "create": create_use_case,
            "get": get_use_case
        }
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user."""
        return Mock(id=uuid4(), email="test@example.com")
    
    @pytest.fixture
    def client(self, mock_use_cases, mock_current_user):
        """Create test client with mocked dependencies."""
        app = create_app()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_create_memory_use_case] = lambda: mock_use_cases["create"]
        app.dependency_overrides[get_memory_use_case] = lambda: mock_use_cases["get"]
        
        return TestClient(app)
    
    def test_create_memory_success(self, client, mock_use_cases, mock_current_user):
        """Test successful memory creation."""
        # Arrange
        memory = Memory.create(
            content="Test memory",
            user_id=mock_current_user.id
        )
        mock_use_cases["create"].execute.return_value = memory
        
        # Act
        response = client.post(
            "/api/v1/memories",
            json={"content": "Test memory"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Test memory"
        assert data["id"] == str(memory.id)
        
        # Verify use case was called
        mock_use_cases["create"].execute.assert_called_once_with(
            content="Test memory",
            user_id=mock_current_user.id,
            tags=[],
            metadata={}
        )
    
    def test_create_memory_validation_error(self, client):
        """Test memory creation with validation error."""
        # Act
        response = client.post(
            "/api/v1/memories",
            json={"content": ""},  # Empty content
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assert
        assert response.status_code == 422
        assert "Content cannot be empty" in response.text
```

## Integration Testing

### Database Integration Tests

```python
# tests/integration/database/test_memory_repository.py
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models.memory import Memory
from src.infrastructure.database.repositories.memory_repository import SQLMemoryRepository

@pytest.mark.integration
@pytest.mark.asyncio
class TestSQLMemoryRepository:
    """Test SQLMemoryRepository with real database."""
    
    @pytest.fixture
    async def repository(self, db_session: AsyncSession):
        """Create repository instance."""
        return SQLMemoryRepository(db_session)
    
    async def test_save_and_find_by_id(self, repository, db_session):
        """Test saving and retrieving a memory."""
        # Arrange
        memory = Memory.create(
            content="Integration test memory",
            user_id=uuid4(),
            tags=["test", "integration"]
        )
        
        # Act
        saved_memory = await repository.save(memory)
        await db_session.commit()
        
        found_memory = await repository.find_by_id(saved_memory.id)
        
        # Assert
        assert found_memory is not None
        assert found_memory.id == saved_memory.id
        assert found_memory.content == memory.content
        assert found_memory.tags == memory.tags
        assert found_memory.version == 1
    
    async def test_find_by_user_id(self, repository, db_session):
        """Test finding memories by user ID."""
        # Arrange
        user_id = uuid4()
        memories = [
            Memory.create(content=f"Memory {i}", user_id=user_id)
            for i in range(3)
        ]
        
        for memory in memories:
            await repository.save(memory)
        await db_session.commit()
        
        # Act
        found_memories = await repository.find_by_user_id(user_id, limit=10)
        
        # Assert
        assert len(found_memories) == 3
        assert all(m.user_id == user_id for m in found_memories)
    
    async def test_vector_search(self, repository, db_session):
        """Test vector similarity search."""
        # Arrange
        memory1 = Memory.create(
            content="Python programming tutorial",
            user_id=uuid4()
        )
        memory1.embedding = [0.1] * 1536  # Mock embedding
        
        memory2 = Memory.create(
            content="Cooking pasta recipe",
            user_id=uuid4()
        )
        memory2.embedding = [0.9] * 1536  # Different embedding
        
        await repository.save(memory1)
        await repository.save(memory2)
        await db_session.commit()
        
        # Act
        query_embedding = [0.1] * 1536  # Similar to memory1
        results = await repository.search_by_vector(
            embedding=query_embedding,
            limit=2,
            threshold=0.5
        )
        
        # Assert
        assert len(results) > 0
        assert results[0].id == memory1.id  # Most similar should be first
```

### Cache Integration Tests

```python
# tests/integration/cache/test_redis_cache.py
import pytest
from src.infrastructure.caching.cache import RedisCache

@pytest.mark.integration
@pytest.mark.asyncio
class TestRedisCache:
    """Test Redis cache integration."""
    
    @pytest.fixture
    async def cache(self, redis_client):
        """Create cache instance."""
        return RedisCache(redis_client)
    
    async def test_set_and_get(self, cache):
        """Test setting and getting values."""
        # Act
        await cache.set("test_key", {"data": "test_value"}, ttl=60)
        result = await cache.get("test_key")
        
        # Assert
        assert result == {"data": "test_value"}
    
    async def test_delete(self, cache):
        """Test deleting keys."""
        # Arrange
        await cache.set("test_key", "test_value")
        
        # Act
        await cache.delete("test_key")
        result = await cache.get("test_key")
        
        # Assert
        assert result is None
    
    async def test_pattern_delete(self, cache):
        """Test deleting keys by pattern."""
        # Arrange
        await cache.set("user:1:profile", {"name": "User 1"})
        await cache.set("user:1:settings", {"theme": "dark"})
        await cache.set("user:2:profile", {"name": "User 2"})
        
        # Act
        await cache.delete_pattern("user:1:*")
        
        # Assert
        assert await cache.get("user:1:profile") is None
        assert await cache.get("user:1:settings") is None
        assert await cache.get("user:2:profile") is not None
```

### Message Queue Integration Tests

```python
# tests/integration/messaging/test_rabbitmq.py
import pytest
import asyncio
from src.infrastructure.messaging.broker import RabbitMQBroker

@pytest.mark.integration
@pytest.mark.asyncio
class TestRabbitMQBroker:
    """Test RabbitMQ broker integration."""
    
    @pytest.fixture
    async def broker(self, rabbitmq_url):
        """Create broker instance."""
        broker = RabbitMQBroker(rabbitmq_url)
        await broker.connect()
        yield broker
        await broker.disconnect()
    
    async def test_publish_and_consume(self, broker):
        """Test publishing and consuming messages."""
        # Arrange
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        # Subscribe to queue
        await broker.subscribe(
            routing_key="test.message",
            handler=handler,
            queue_name="test_queue"
        )
        
        # Act
        test_message = {"type": "test", "data": "Hello RabbitMQ"}
        await broker.publish(
            routing_key="test.message",
            message=test_message
        )
        
        # Wait for message to be consumed
        await asyncio.sleep(0.5)
        
        # Assert
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
```

## End-to-End Testing

### Complete Workflow Tests

```python
# tests/e2e/workflows/test_memory_workflow.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.e2e
@pytest.mark.asyncio
class TestMemoryWorkflow:
    """Test complete memory workflow."""
    
    @pytest.fixture
    async def authenticated_client(self, api_client: AsyncClient):
        """Create authenticated client."""
        # Login and get token
        response = await api_client.post(
            "/api/v1/auth/token",
            json={"username": "test@example.com", "password": "testpass"}
        )
        token = response.json()["access_token"]
        
        # Set authorization header
        api_client.headers["Authorization"] = f"Bearer {token}"
        return api_client
    
    async def test_complete_memory_lifecycle(self, authenticated_client):
        """Test creating, updating, searching, and deleting a memory."""
        # 1. Create memory
        create_response = await authenticated_client.post(
            "/api/v1/memories",
            json={
                "content": "E2E test memory about Python programming",
                "tags": ["python", "programming", "test"]
            }
        )
        assert create_response.status_code == 201
        memory_id = create_response.json()["id"]
        
        # 2. Verify memory was created
        get_response = await authenticated_client.get(
            f"/api/v1/memories/{memory_id}"
        )
        assert get_response.status_code == 200
        memory = get_response.json()
        assert memory["content"] == "E2E test memory about Python programming"
        assert memory["tags"] == ["python", "programming", "test"]
        
        # 3. Update memory
        update_response = await authenticated_client.put(
            f"/api/v1/memories/{memory_id}",
            json={
                "content": "Updated E2E test memory about Python and FastAPI",
                "tags": ["python", "programming", "test", "fastapi"]
            }
        )
        assert update_response.status_code == 200
        
        # 4. Search for memory
        search_response = await authenticated_client.post(
            "/api/v1/memories/search",
            json={
                "query": "Python FastAPI programming",
                "limit": 10
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()["results"]
        assert len(results) > 0
        assert any(r["memory"]["id"] == memory_id for r in results)
        
        # 5. List memories with filters
        list_response = await authenticated_client.get(
            "/api/v1/memories?tag=python&page=1&size=10"
        )
        assert list_response.status_code == 200
        memories = list_response.json()["items"]
        assert any(m["id"] == memory_id for m in memories)
        
        # 6. Delete memory
        delete_response = await authenticated_client.delete(
            f"/api/v1/memories/{memory_id}"
        )
        assert delete_response.status_code == 204
        
        # 7. Verify deletion
        get_deleted_response = await authenticated_client.get(
            f"/api/v1/memories/{memory_id}"
        )
        assert get_deleted_response.status_code == 404
```

### API Contract Tests

```python
# tests/e2e/api/test_api_contracts.py
import pytest
from httpx import AsyncClient
from jsonschema import validate

@pytest.mark.e2e
@pytest.mark.asyncio
class TestAPIContracts:
    """Test API contract compliance."""
    
    MEMORY_SCHEMA = {
        "type": "object",
        "required": ["id", "content", "user_id", "created_at", "updated_at"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "content": {"type": "string", "minLength": 1},
            "embedding": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 1536,
                "maxItems": 1536
            },
            "user_id": {"type": "string", "format": "uuid"},
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "metadata": {"type": "object"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"},
            "version": {"type": "integer", "minimum": 1}
        }
    }
    
    async def test_memory_response_schema(self, authenticated_client):
        """Test memory response matches schema."""
        # Create memory
        response = await authenticated_client.post(
            "/api/v1/memories",
            json={"content": "Schema test memory"}
        )
        
        # Validate response
        assert response.status_code == 201
        memory = response.json()
        validate(instance=memory, schema=self.MEMORY_SCHEMA)
```

## Performance Testing

### Benchmark Tests

```python
# tests/performance/benchmarks/test_memory_operations.py
import pytest
from uuid import uuid4
import time

@pytest.mark.benchmark
class TestMemoryPerformance:
    """Benchmark memory operations."""
    
    def test_memory_creation_performance(self, benchmark):
        """Benchmark memory creation."""
        def create_memory():
            return Memory.create(
                content="Performance test memory",
                user_id=uuid4(),
                tags=["perf", "test"]
            )
        
        result = benchmark(create_memory)
        assert result is not None
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.001  # Less than 1ms
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, benchmark, db_session):
        """Benchmark database queries."""
        repository = SQLMemoryRepository(db_session)
        
        # Setup test data
        user_id = uuid4()
        for i in range(100):
            memory = Memory.create(
                content=f"Test memory {i}",
                user_id=user_id
            )
            await repository.save(memory)
        await db_session.commit()
        
        # Benchmark query
        async def query_memories():
            return await repository.find_by_user_id(user_id, limit=20)
        
        result = await benchmark(query_memories)
        assert len(result) == 20
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.1  # Less than 100ms
```

### Load Tests

```python
# tests/performance/load/test_api_load.py
import asyncio
import pytest
from httpx import AsyncClient
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.load
@pytest.mark.asyncio
class TestAPILoad:
    """Load test API endpoints."""
    
    async def test_concurrent_memory_creation(self, authenticated_client):
        """Test concurrent memory creation."""
        
        async def create_memory(index: int):
            response = await authenticated_client.post(
                "/api/v1/memories",
                json={
                    "content": f"Load test memory {index}",
                    "tags": ["load-test"]
                }
            )
            return response.status_code
        
        # Create 100 memories concurrently
        tasks = [create_memory(i) for i in range(100)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Assertions
        assert all(status == 201 for status in results)
        assert duration < 10  # Should complete within 10 seconds
        
        # Calculate throughput
        throughput = len(results) / duration
        assert throughput > 10  # At least 10 requests per second
```

## Test Fixtures and Utilities

### Test Factories

```python
# tests/fixtures/factories.py
import factory
from factory import Faker, LazyFunction, Trait
from uuid import uuid4
from datetime import datetime

class UserFactory(factory.Factory):
    """User factory for testing."""
    
    class Meta:
        model = User
    
    id = LazyFunction(uuid4)
    email = Faker('email')
    name = Faker('name')
    created_at = LazyFunction(datetime.utcnow)
    
    class Params:
        admin = Trait(
            role='admin',
            email='admin@example.com'
        )

class MemoryFactory(factory.Factory):
    """Memory factory for testing."""
    
    class Meta:
        model = Memory
    
    id = LazyFunction(uuid4)
    content = Faker('text', max_nb_chars=500)
    user_id = LazyFunction(uuid4)
    tags = factory.List([Faker('word') for _ in range(3)])
    created_at = LazyFunction(datetime.utcnow)
    updated_at = LazyFunction(datetime.utcnow)
    version = 1
    
    @factory.post_generation
    def embedding(obj, create, extracted, **kwargs):
        if create and not extracted:
            # Generate mock embedding
            obj.embedding = [0.1] * 1536
```

### Mock Services

```python
# tests/fixtures/mocks.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from src.domain.models.memory import Memory

class MockMemoryRepository:
    """Mock memory repository for testing."""
    
    def __init__(self):
        self._memories: Dict[UUID, Memory] = {}
    
    async def save(self, memory: Memory) -> Memory:
        self._memories[memory.id] = memory
        return memory
    
    async def find_by_id(self, memory_id: UUID) -> Optional[Memory]:
        return self._memories.get(memory_id)
    
    async def find_by_user_id(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[Memory]:
        user_memories = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]
        return user_memories[offset:offset + limit]

class MockCache:
    """Mock cache for testing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._cache[key] = value
    
    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
```

### Pytest Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.rabbitmq import RabbitMQContainer

# Configure async tests
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def postgres_container():
    """Start PostgreSQL container for tests."""
    with PostgresContainer("ankane/pgvector:v0.5.1-pg16") as postgres:
        yield postgres

@pytest.fixture(scope="session")
async def redis_container():
    """Start Redis container for tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture
async def db_session(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    engine = create_async_engine(
        postgres_container.get_connection_url(),
        echo=False
    )
    
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
def anyio_backend():
    """Configure anyio backend."""
    return "asyncio"

# Markers
def pytest_configure(config):
    """Configure pytest markers."""
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
        "markers", "benchmark: Performance benchmark tests"
    )
    config.addinivalue_line(
        "markers", "load: Load tests"
    )
```

## Testing Best Practices

### 1. Test Naming
```python
# Good: Descriptive test names
def test_create_memory_with_valid_content_returns_memory():
    pass

def test_create_memory_with_empty_content_raises_value_error():
    pass

# Bad: Vague test names
def test_memory():
    pass

def test_error():
    pass
```

### 2. Test Organization
- One test class per class/module being tested
- Group related tests together
- Use descriptive class names

### 3. Test Data
- Use factories for complex objects
- Keep test data minimal
- Avoid hardcoded IDs

### 4. Assertions
- One logical assertion per test
- Use specific assertions
- Include helpful error messages

### 5. Mocking
- Mock at boundaries
- Don't mock what you don't own
- Verify interactions when appropriate

## CI/CD Integration

### GitHub Actions Test Pipeline

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: ankane/pgvector:v0.5.1-pg16
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-v3.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          pytest tests/unit/ -v --cov=src
          pytest tests/integration/ -v --cov=src --cov-append
          pytest tests/e2e/ -v --cov=src --cov-append
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Debugging

### Running Specific Tests

```bash
# Run single test
pytest tests/unit/domain/models/test_memory.py::TestMemory::test_create_memory_success

# Run tests matching pattern
pytest -k "test_create"

# Run tests with specific marker
pytest -m unit

# Run with debugging
pytest --pdb

# Run with verbose output
pytest -vv

# Run with print statements
pytest -s
```

### Debugging Failed Tests

```python
# Use pytest fixtures for debugging
@pytest.fixture
def debug_info(request):
    """Print debug information."""
    print(f"\nTest: {request.node.name}")
    print(f"Module: {request.module.__name__}")
    yield
    print(f"Test completed")

# Use in test
def test_something(debug_info):
    # Test code
    pass
```

## Coverage Requirements

### Minimum Coverage
- Overall: 80%
- Domain layer: 95%
- Application layer: 90%
- Infrastructure layer: 80%
- API layer: 85%

### Coverage Report
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

## Performance Monitoring

### Test Performance
```bash
# Run with test durations
pytest --durations=10

# Profile slow tests
pytest --profile

# Run benchmarks
pytest tests/performance/benchmarks/ --benchmark-only
```

### Memory Testing
```python
# Use memory profiler
@profile
def test_memory_usage():
    # Test code
    pass

# Run with memory profiler
python -m memory_profiler test_file.py
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [Property-Based Testing](https://hypothesis.readthedocs.io/)
- [Load Testing with Locust](https://docs.locust.io/)