# Testing Strategy - Second Brain v3.0.0

## Overview

Second Brain v3.0.0 follows a comprehensive testing strategy aligned with Clean Architecture principles, emphasizing testability, maintainability, and reliability.

## Testing Philosophy

### Core Principles
1. **Test Pyramid**: More unit tests, fewer integration tests, minimal E2E tests
2. **Clean Architecture**: Test each layer independently
3. **TDD When Appropriate**: Write tests first for complex logic
4. **Fast Feedback**: Quick test execution for rapid development
5. **Deterministic**: Tests should produce consistent results

## Test Categories

### 1. Unit Tests (70%)
**Location**: `tests/unit/`  
**Purpose**: Test individual components in isolation  
**Speed**: Fast (<100ms per test)  
**Dependencies**: Mocked

```python
# Example: Domain model test
class TestMemory:
    def test_memory_creation(self):
        memory = Memory(
            content="Test content",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.content == "Test content"
        assert memory.importance_score == 0.5  # default
```

### 2. Integration Tests (20%)
**Location**: `tests/integration/`  
**Purpose**: Test component interactions  
**Speed**: Medium (100ms-1s per test)  
**Dependencies**: Real or test doubles

```python
# Example: API endpoint test
def test_create_memory_endpoint(client, auth_headers):
    response = client.post(
        "/memories",
        json={"content": "Test", "memory_type": "semantic"},
        params=auth_headers
    )
    assert response.status_code == 200
```

### 3. E2E Tests (10%)
**Location**: `tests/e2e/`  
**Purpose**: Test complete user workflows  
**Speed**: Slow (>1s per test)  
**Dependencies**: Full system

## Testing Layers

### Domain Layer
- **What to test**: Business logic, domain models, value objects
- **What not to test**: Framework-specific code
- **Example tests**:
  - Memory importance calculation
  - Session state transitions
  - Business rule validation

### Application Layer
- **What to test**: Use cases, service orchestration
- **What not to test**: Direct database queries
- **Example tests**:
  - Memory storage workflow
  - Session management logic
  - Search and retrieval operations

### Infrastructure Layer
- **What to test**: External integrations, database operations
- **What not to test**: Third-party library internals
- **Example tests**:
  - Database connection and queries
  - OpenAI API integration
  - Redis caching

### Presentation Layer
- **What to test**: Request/response handling, validation
- **What not to test**: FastAPI framework internals
- **Example tests**:
  - Route parameter validation
  - Response serialization
  - Error response formatting

## Test Organization

```
tests/
├── unit/
│   ├── domain/           # Pure business logic
│   ├── application/      # Use cases and services
│   ├── infrastructure/   # External integrations
│   └── presentation/     # API routes
├── integration/
│   ├── api/             # API endpoint tests
│   ├── database/        # Database integration
│   └── services/        # Service integration
├── e2e/
│   └── workflows/       # Complete user scenarios
├── fixtures/            # Test data
├── utils/              # Test helpers
└── conftest.py         # Shared fixtures
```

## Testing Patterns

### 1. Arrange-Act-Assert (AAA)
```python
def test_memory_update():
    # Arrange
    memory = Memory(content="Original")
    
    # Act
    memory.update_content("Updated")
    
    # Assert
    assert memory.content == "Updated"
    assert memory.updated_at is not None
```

### 2. Given-When-Then (BDD)
```python
def test_session_pause():
    # Given an active session
    session = Session(state=SessionState.ACTIVE)
    
    # When the session is paused
    session.pause()
    
    # Then the state should be paused
    assert session.state == SessionState.PAUSED
```

### 3. Test Builders
```python
class MemoryBuilder:
    def __init__(self):
        self._memory = Memory()
    
    def with_content(self, content):
        self._memory.content = content
        return self
    
    def with_type(self, memory_type):
        self._memory.memory_type = memory_type
        return self
    
    def build(self):
        return self._memory

# Usage
memory = MemoryBuilder()\
    .with_content("Test")\
    .with_type(MemoryType.EPISODIC)\
    .build()
```

## Mocking Strategies

### 1. Interface Mocking
```python
class MockDatabase:
    async def store_memory(self, content, metadata):
        return "mock-id-123"
    
    async def get_memory(self, memory_id):
        return {"id": memory_id, "content": "Mock content"}
```

### 2. Dependency Injection
```python
@pytest.fixture
def memory_service(mock_database):
    return MemoryService(database=mock_database)

def test_store_memory(memory_service):
    result = await memory_service.store("Test")
    assert result == "mock-id-123"
```

### 3. Monkey Patching
```python
def test_with_fixed_time(monkeypatch):
    fixed_time = datetime(2025, 1, 1)
    monkeypatch.setattr(
        "app.services.datetime",
        lambda: fixed_time
    )
```

## Test Data Management

### Fixtures
```python
@pytest.fixture
def sample_memories():
    return [
        Memory(content="Memory 1", memory_type=MemoryType.SEMANTIC),
        Memory(content="Memory 2", memory_type=MemoryType.EPISODIC),
        Memory(content="Memory 3", memory_type=MemoryType.PROCEDURAL)
    ]
```

### Factories
```python
class MemoryFactory:
    @staticmethod
    def create_semantic(content="Default content"):
        return Memory(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.7
        )
```

### Test Database
```python
@pytest.fixture
async def test_db():
    """Create isolated test database"""
    db = Database(TEST_DATABASE_URL)
    await db.initialize()
    
    yield db
    
    # Cleanup
    await db.execute("TRUNCATE memories CASCADE")
    await db.close()
```

## Performance Testing

### Benchmarking
```python
@pytest.mark.benchmark
def test_search_performance(benchmark):
    result = benchmark(
        search_memories,
        query="test query",
        limit=100
    )
    assert len(result) <= 100
```

### Load Testing
```python
@pytest.mark.slow
async def test_concurrent_requests():
    tasks = [
        create_memory(f"Memory {i}")
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)
```

## Security Testing

### Authentication Tests
```python
def test_unauthorized_access(client):
    response = client.get("/memories")
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"
```

### Input Validation
```python
def test_sql_injection_protection(client, auth_headers):
    malicious_input = "'; DROP TABLE memories; --"
    response = client.post(
        "/memories/search",
        json={"query": malicious_input},
        params=auth_headers
    )
    assert response.status_code == 400
    assert "dangerous" in response.json()["message"]
```

## Test Environments

### Local Development
```bash
# Unit tests only (fast feedback)
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# Full test suite
.venv/Scripts/python.exe -m pytest tests/ -v
```

### CI/CD Pipeline
```yaml
test:
  script:
    - pytest tests/unit/ --cov=app
    - pytest tests/integration/
    - pytest tests/e2e/ --slow
```

### Pre-Production
```bash
# Smoke tests
pytest tests/smoke/ --env=staging

# Performance tests
pytest tests/performance/ --benchmark
```

## Coverage Goals

### Minimum Coverage Requirements
- **Overall**: 80%
- **Domain Layer**: 95%
- **Application Layer**: 90%
- **Infrastructure Layer**: 80%
- **Presentation Layer**: 85%

### Coverage Reports
```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Check coverage thresholds
pytest --cov=app --cov-fail-under=80
```

## Continuous Testing

### Pre-commit Hooks
```yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Run unit tests
        entry: pytest tests/unit/ -x
        language: system
        pass_filenames: false
```

### CI/CD Integration
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        test-type: [unit, integration, e2e]
    
    steps:
      - name: Run ${{ matrix.test-type }} tests
        run: pytest tests/${{ matrix.test-type }}/
```

## Test Maintenance

### Regular Reviews
1. **Weekly**: Fix flaky tests
2. **Monthly**: Update test data
3. **Quarterly**: Refactor test structure
4. **Yearly**: Audit test coverage

### Test Quality Metrics
- **Execution Time**: Track and optimize slow tests
- **Flakiness**: Monitor and fix intermittent failures
- **Coverage Trends**: Ensure coverage doesn't decrease
- **Maintenance Cost**: Time spent fixing vs writing tests

## Best Practices

### Do's
- ✅ Write tests before fixing bugs
- ✅ Keep tests simple and focused
- ✅ Use descriptive test names
- ✅ Test one thing at a time
- ✅ Make tests deterministic
- ✅ Use appropriate test doubles
- ✅ Clean up test data

### Don'ts
- ❌ Test implementation details
- ❌ Write brittle tests
- ❌ Ignore flaky tests
- ❌ Test third-party code
- ❌ Use production data
- ❌ Share state between tests
- ❌ Make tests dependent on order

## Testing Checklist

### Before Committing
- [ ] All unit tests pass
- [ ] New code has tests
- [ ] Coverage hasn't decreased
- [ ] No hardcoded test data
- [ ] Tests are deterministic

### Before Merging
- [ ] Integration tests pass
- [ ] No flaky tests introduced
- [ ] Performance benchmarks met
- [ ] Security tests pass
- [ ] Documentation updated

### Before Releasing
- [ ] E2E tests pass
- [ ] Smoke tests on staging
- [ ] Performance regression tests
- [ ] Security audit complete
- [ ] Test data cleaned up

---

This testing strategy ensures Second Brain v3.0.0 maintains high quality through comprehensive, efficient testing practices aligned with Clean Architecture principles.