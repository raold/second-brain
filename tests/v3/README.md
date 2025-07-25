# Second Brain v3.0.0 Test Suite

Comprehensive test suite for the v3.0.0 implementation covering unit, integration, API, end-to-end, and performance tests.

## Test Structure

```
tests/v3/
├── unit/                    # Unit tests (fast, isolated)
│   ├── domain/             # Domain model tests
│   └── application/        # Use case tests
├── integration/            # Integration tests (with real/mock services)
├── api/                    # API endpoint tests
├── e2e/                    # End-to-end tests
├── performance/            # Performance benchmarks
└── fixtures/               # Test utilities and factories
```

## Running Tests

### Using the Test Runner Script

```bash
# Check if required services are running
python scripts/test_v3.py check

# Run all tests
python scripts/test_v3.py all --coverage

# Run specific test suites
python scripts/test_v3.py unit --parallel --coverage
python scripts/test_v3.py integration --mock
python scripts/test_v3.py api
python scripts/test_v3.py e2e --slow
python scripts/test_v3.py performance --save baseline
```

### Using pytest directly

```bash
# Run all tests
pytest tests/v3/

# Run with coverage
pytest tests/v3/ --cov=src --cov-report=html

# Run specific markers
pytest tests/v3/ -m unit
pytest tests/v3/ -m integration
pytest tests/v3/ -m "integration and not requires_real_db"

# Run in parallel
pytest tests/v3/ -n auto

# Run with verbose output
pytest tests/v3/ -vv
```

## Test Configuration

### Environment Variables

- `USE_MOCK_DATABASE`: Use mock implementations instead of real services
- `MOCK_EMBEDDINGS`: Use mock embedding generation
- `TEST_DATABASE_URL`: PostgreSQL test database URL
- `TEST_REDIS_URL`: Redis test instance URL
- `TEST_RABBITMQ_URL`: RabbitMQ test instance URL
- `TEST_MINIO_ENDPOINT`: MinIO test endpoint
- `OPENAI_API_KEY`: OpenAI API key (for real embedding tests)

### GitHub Actions

The test suite is configured to run in GitHub Actions with:
- Secrets: `OPENAI_API_KEY`, `API_TOKENS`
- Variables: `CI_USE_MOCK_DATABASE=true`

### Local Development

For local testing with real services:

```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/v3/

# Stop services
docker-compose -f docker-compose.test.yml down
```

For local testing with mocks:

```bash
export USE_MOCK_DATABASE=true
export MOCK_EMBEDDINGS=true
pytest tests/v3/
```

## Test Categories

### Unit Tests
- **Location**: `tests/v3/unit/`
- **Purpose**: Test individual components in isolation
- **Coverage**:
  - Domain models (Memory, User, Session, Tag)
  - Value objects
  - Domain events
  - Use cases
  - Business logic

### Integration Tests
- **Location**: `tests/v3/integration/`
- **Purpose**: Test component integration with infrastructure
- **Coverage**:
  - Repository implementations
  - Database operations
  - Cache operations
  - Message queue publishing/consuming
  - Object storage operations
  - External service integration

### API Tests
- **Location**: `tests/v3/api/`
- **Purpose**: Test REST API endpoints
- **Coverage**:
  - Authentication/authorization
  - CRUD operations
  - Request validation
  - Response formatting
  - Error handling
  - Rate limiting

### End-to-End Tests
- **Location**: `tests/v3/e2e/`
- **Purpose**: Test complete user workflows
- **Coverage**:
  - User registration and login
  - Memory creation and retrieval
  - Search functionality
  - File uploads
  - Multi-service interactions

### Performance Tests
- **Location**: `tests/v3/performance/`
- **Purpose**: Benchmark and profile application performance
- **Coverage**:
  - Database query performance
  - API response times
  - Concurrent request handling
  - Memory usage
  - Cache effectiveness

## Test Fixtures

### Factories
Located in `tests/v3/fixtures/factories.py`:
- `UserFactory`: Create test users
- `MemoryFactory`: Create test memories with embeddings
- `SessionFactory`: Create test sessions with messages
- `TagFactory`: Create test tags and hierarchies
- `TestDataBuilder`: Create complete test scenarios

### Mocks
Located in `tests/v3/fixtures/mocks.py`:
- `MockMemoryRepository`: In-memory repository
- `MockEmbeddingClient`: Mock embedding generation
- `MockCache`: In-memory cache
- `MockMessageBroker`: In-memory message queue
- `MockStorageClient`: In-memory object storage

## Writing Tests

### Unit Test Example

```python
@pytest.mark.unit
class TestMemory:
    def test_create_memory(self):
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="Test content",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.title == "Test Memory"
        assert memory.status == MemoryStatus.ACTIVE
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestMemoryRepository:
    async def test_save_and_get(self, async_db_session):
        repo = SQLMemoryRepository(async_db_session)
        memory = MemoryFactory.create()
        
        saved = await repo.save(memory)
        retrieved = await repo.get(memory.id)
        
        assert retrieved.id == memory.id
```

### Using Mocks

```python
@pytest.mark.asyncio
async def test_with_mocks(self):
    # Automatically uses mocks when USE_MOCK_DATABASE=true
    repo = MockMemoryRepository()
    cache = MockCache()
    
    # Test with mocks
    memory = MemoryFactory.create()
    await repo.save(memory)
    
    await cache.set(f"memory:{memory.id}", memory)
    cached = await cache.get(f"memory:{memory.id}")
    
    assert cached.id == memory.id
```

## Coverage Requirements

- Overall coverage target: 80%
- Unit tests: 90%+ coverage
- Integration tests: 70%+ coverage
- Critical paths: 100% coverage

Generate coverage reports:

```bash
# HTML report
pytest tests/v3/ --cov=src --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest tests/v3/ --cov=src --cov-report=xml
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
3. **Mock External Services**: Use mocks for external dependencies in unit tests
4. **Test Edge Cases**: Include error scenarios and boundary conditions
5. **Descriptive Names**: Use clear, descriptive test names
6. **Arrange-Act-Assert**: Follow the AAA pattern
7. **Async Tests**: Use `@pytest.mark.asyncio` for async tests
8. **Markers**: Use appropriate markers (unit, integration, etc.)
9. **Factories**: Use factories for consistent test data
10. **Performance**: Keep unit tests fast (<100ms each)

## Troubleshooting

### Services Not Running
```bash
# Check services
python scripts/test_v3.py check

# Run with mocks
export USE_MOCK_DATABASE=true
pytest tests/v3/
```

### Flaky Tests
- Check for timing issues in async tests
- Ensure proper cleanup in fixtures
- Use explicit waits instead of sleep

### Database Issues
- Ensure test database exists
- Check migrations are applied
- Verify connection string

### Performance Test Issues
- Warm up before benchmarking
- Run on consistent hardware
- Disable other processes

## CI/CD Integration

Tests run automatically on:
- Push to main/v3.0.0 branches
- Pull requests
- Nightly builds (performance tests)

See `.github/workflows/test-v3.yml` for configuration.