# Testing Guidelines for Second Brain v2.6.0-dev

## Overview

This document establishes standardized testing patterns and best practices for Second Brain. All new tests should follow these guidelines to ensure consistency, maintainability, and reliability.

## Test Organization

### Directory Structure
```
tests/
├── unit/                 # Unit tests for individual components
├── integration/          # Integration tests for component interaction
├── performance/          # Performance and load tests
├── comprehensive/        # End-to-end system tests
├── multimodal/          # Multimodal feature tests
├── manual/              # Manual test scripts
├── conftest.py          # Shared fixtures and configuration
├── test_template.py     # Template for new tests
└── TESTING_GUIDELINES.md # This file
```

### File Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<descriptive_name>`
- Fixtures: `<descriptive_name>` (no test_ prefix)

## Test Categories and Markers

### Available Markers
```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.performance   # Performance tests
@pytest.mark.asyncio       # Async tests
@pytest.mark.slow          # Long-running tests
```

### Test Categories

#### 1. Unit Tests
- Test individual functions/methods in isolation
- Mock all external dependencies
- Fast execution (< 1ms per test)
- High coverage of edge cases

```python
@pytest.mark.unit
def test_memory_validation():
    """Test memory validation logic."""
    memory = Memory(content="test", importance=7.5)
    assert memory.is_valid()
```

#### 2. Integration Tests
- Test interaction between components
- May use test database or mock services
- Medium execution time (< 100ms per test)
- Focus on API contracts and data flow

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_creation_workflow(client, api_key):
    """Test complete memory creation workflow."""
    response = await client.post("/memories", json=data, headers=auth)
    assert response.status_code == 201
```

#### 3. Performance Tests
- Test performance requirements
- Measure execution time and memory usage
- Use realistic data sizes
- Set clear performance thresholds

```python
@pytest.mark.performance
def test_bulk_processing_speed():
    """Test bulk processing meets performance requirements."""
    start = time.time()
    result = process_batch(large_dataset)
    elapsed = time.time() - start
    assert elapsed < 5.0  # Under 5 seconds
```

## Test Structure Standards

### Arrange-Act-Assert Pattern
```python
def test_feature():
    """Test description."""
    # Arrange - Set up test data and mocks
    data = {"key": "value"}
    mock_service = Mock()
    
    # Act - Execute the code under test
    result = function_under_test(data, mock_service)
    
    # Assert - Verify the result
    assert result.success is True
    assert mock_service.called
```

### Fixtures Best Practices

#### Simple Data Fixtures
```python
@pytest.fixture
def sample_memory():
    """Create sample memory for testing."""
    return Memory(
        id=uuid4(),
        content="Test memory content",
        importance=7.5,
        tags=["test", "fixture"]
    )
```

#### Async Resource Fixtures
```python
@pytest.fixture
async def database_session():
    """Create database session for testing."""
    async with get_test_db() as session:
        yield session
        await session.rollback()
```

#### Mock Fixtures
```python
@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('app.services.openai_client') as mock:
        mock.embed.return_value = [0.1] * 1536
        yield mock
```

## Mocking Guidelines

### When to Mock
- External APIs (OpenAI, third-party services)
- Database connections (use test DB or mock)
- File system operations
- Network requests
- Time-dependent operations

### Mock Patterns

#### Database Mocking
```python
def test_with_database_mock():
    with patch('app.database.get_db') as mock_db:
        mock_conn = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": "123"}
        
        # Test code here
```

#### Async Service Mocking
```python
@pytest.mark.asyncio
async def test_with_async_mock():
    with patch('app.services.external_service') as mock_service:
        mock_service.fetch_data = AsyncMock(return_value="data")
        
        result = await my_function()
        assert result == "processed_data"
```

#### Time Mocking
```python
def test_time_dependent_feature():
    fixed_time = datetime(2025, 1, 1, 12, 0, 0)
    with patch('app.module.datetime') as mock_dt:
        mock_dt.utcnow.return_value = fixed_time
        
        result = create_timestamped_item()
        assert result.created_at == fixed_time
```

## Error Testing

### Exception Testing
```python
def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError) as exc_info:
        process_data(invalid_data)
    
    assert "invalid format" in str(exc_info.value)
```

### Error Handling Testing
```python
@pytest.mark.asyncio
async def test_network_error_handling():
    """Test graceful handling of network errors."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Network error")
        
        result = await fetch_with_retry()
        assert result.success is False
        assert result.error_type == "network_error"
```

## Async Testing

### Async Test Markers
```python
@pytest.mark.asyncio
async def test_async_function():
    """All async tests must use this marker."""
    result = await async_function()
    assert result is not None
```

### Async Fixtures
```python
@pytest.fixture
async def async_client():
    """Async fixture for HTTP client."""
    async with AsyncClient() as client:
        yield client
```

### Async Mocking
```python
def test_async_mock():
    with patch('app.service.async_method') as mock_method:
        mock_method.return_value = AsyncMock(return_value="result")
        
        # Test async code
```

## Performance Testing

### Performance Test Structure
```python
@pytest.mark.performance
def test_performance_requirement():
    """Test specific performance requirement."""
    # Setup
    large_dataset = generate_test_data(10000)
    
    # Measure
    start_time = time.time()
    result = process_dataset(large_dataset)
    elapsed = time.time() - start_time
    
    # Assert performance
    assert elapsed < 5.0  # Max 5 seconds
    assert len(result) == 10000
    
    # Memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    assert memory_mb < 500  # Max 500MB
```

### Benchmarking
```python
@pytest.mark.performance
@pytest.mark.slow
def test_search_performance_benchmark():
    """Benchmark search performance across dataset sizes."""
    sizes = [100, 1000, 10000, 100000]
    times = []
    
    for size in sizes:
        dataset = generate_memories(size)
        
        start = time.time()
        search_memories(dataset, "query")
        elapsed = time.time() - start
        times.append(elapsed)
    
    # Performance should scale linearly
    assert times[-1] / times[0] < size[-1] / sizes[0] * 2
```

## Integration Testing

### API Integration Tests
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_integration(client: AsyncClient, api_key):
    """Test complete API workflow."""
    # Create
    create_response = await client.post(
        "/memories",
        json={"content": "Test", "importance": 7.0},
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert create_response.status_code == 201
    memory_id = create_response.json()["id"]
    
    # Read
    get_response = await client.get(
        f"/memories/{memory_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert get_response.status_code == 200
    
    # Update
    update_response = await client.put(
        f"/memories/{memory_id}",
        json={"importance": 8.0},
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert update_response.status_code == 200
    
    # Delete
    delete_response = await client.delete(
        f"/memories/{memory_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert delete_response.status_code == 200
```

### Database Integration Tests
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_integration():
    """Test database operations integration."""
    async with get_test_db() as db:
        # Create
        memory = await MemoryService.create(db, memory_data)
        assert memory.id is not None
        
        # Read
        retrieved = await MemoryService.get(db, memory.id)
        assert retrieved.content == memory_data["content"]
        
        # Update
        updated = await MemoryService.update(db, memory.id, {"importance": 9.0})
        assert updated.importance == 9.0
        
        # Delete
        await MemoryService.delete(db, memory.id)
        deleted = await MemoryService.get(db, memory.id)
        assert deleted is None
```

## Test Data Management

### Test Data Factories
```python
class MemoryFactory:
    """Factory for creating test memories."""
    
    @staticmethod
    def create(**kwargs):
        """Create memory with default values."""
        defaults = {
            "id": uuid4(),
            "content": "Test memory",
            "importance": 5.0,
            "tags": ["test"],
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return Memory(**defaults)
    
    @staticmethod
    def create_batch(count: int, **kwargs):
        """Create multiple memories."""
        return [MemoryFactory.create(**kwargs) for _ in range(count)]
```

### Test Data Constants
```python
# tests/test_constants.py
TEST_MEMORY_CONTENT = "This is test memory content for testing purposes"
TEST_IMPORTANCE_HIGH = 9.0
TEST_IMPORTANCE_MEDIUM = 5.0
TEST_IMPORTANCE_LOW = 2.0
TEST_TAGS = ["test", "automation", "validation"]
```

## Coverage Requirements

### Coverage Goals
- **Overall Coverage**: 85% minimum (enforced by pytest)
- **Critical Paths**: 95% (auth, core memory operations)
- **New Code**: 90% coverage requirement
- **Complex Logic**: 100% branch coverage

### Coverage Exclusions
```python
# Use pragma comments for uncoverable code
def debug_function():  # pragma: no cover
    """Debug function not used in production."""
    print("Debug information")

# Platform-specific code
if sys.platform == "win32":  # pragma: no cover
    # Windows-specific code
    pass
```

### Coverage Reporting
```bash
# Run tests with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html

# Coverage will fail if below 85%
pytest --cov-fail-under=85
```

## Common Anti-Patterns to Avoid

### 1. Testing Implementation Details
```python
# BAD - Testing internal implementation
def test_internal_method_called():
    obj = MyClass()
    obj.public_method()
    assert obj._internal_method_called  # Don't test private methods

# GOOD - Testing behavior
def test_public_behavior():
    obj = MyClass()
    result = obj.public_method()
    assert result.is_valid()
```

### 2. Overly Complex Test Setup
```python
# BAD - Complex setup in test
def test_feature():
    # 50 lines of setup code
    complex_setup()
    more_setup()
    even_more_setup()
    result = simple_function()
    assert result

# GOOD - Use fixtures
@pytest.fixture
def complex_setup():
    # Setup code here
    return setup_result

def test_feature(complex_setup):
    result = simple_function(complex_setup)
    assert result
```

### 3. Multiple Assertions Without Clear Purpose
```python
# BAD - Multiple unrelated assertions
def test_everything():
    result = function()
    assert result.a == 1
    assert result.b == 2
    assert result.c == 3
    assert result.method1() == "x"
    assert result.method2() == "y"

# GOOD - Focused assertions
def test_result_structure():
    result = function()
    assert result.a == 1
    assert result.b == 2
    assert result.c == 3

def test_result_methods():
    result = function()
    assert result.method1() == "x"
    assert result.method2() == "y"
```

## CI/CD Integration

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        args: [--cov-fail-under=85]
```

### GitHub Actions
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml --cov-fail-under=85
    
- name: Upload coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Debugging Tests

### Debugging Strategies
```python
# Use pytest's built-in debugging
def test_debug_example():
    result = complex_function()
    import pdb; pdb.set_trace()  # Debugger breakpoint
    assert result.is_valid()

# Use print statements for simple debugging
def test_with_debug_output(capfd):
    print("Debug: input data", test_data)
    result = function(test_data)
    print("Debug: result", result)
    
    # Capture and verify output if needed
    captured = capfd.readouterr()
    assert "Debug: result" in captured.out
```

### Test Isolation Issues
```python
# Ensure test isolation
def test_isolated():
    # Reset global state
    reset_global_cache()
    
    # Use fresh instances
    service = create_fresh_service()
    
    # Clean up after test
    cleanup_test_artifacts()
```

## Documentation Standards

### Test Docstrings
```python
def test_memory_creation_with_validation():
    """
    Test memory creation with comprehensive validation.
    
    This test verifies that:
    1. Valid memory data creates a memory successfully
    2. Invalid data raises appropriate validation errors
    3. Default values are applied correctly
    4. Timestamps are set automatically
    """
    # Test implementation
```

### Complex Test Explanation
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_memory_operations():
    """
    Test concurrent memory operations don't cause race conditions.
    
    This test simulates multiple users creating, updating, and deleting
    memories simultaneously to ensure database consistency and proper
    isolation between operations.
    
    Expected behavior:
    - All operations complete successfully
    - No data corruption occurs
    - Database constraints are maintained
    - Performance remains acceptable under load
    """
    # Test implementation
```

## Conclusion

Following these guidelines ensures:
- **Consistency** across all test files
- **Maintainability** through clear patterns
- **Reliability** through comprehensive coverage
- **Performance** through efficient test design
- **Debugging** through clear test structure

When in doubt, refer to the `test_template.py` file and existing high-quality tests like `test_batch_processing.py` and `test_security_comprehensive.py`.

Remember: Good tests are an investment in code quality, developer productivity, and system reliability.