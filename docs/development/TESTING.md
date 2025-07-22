# Testing Guide for Second Brain v2.6.0-dev

## Overview

Second Brain uses a comprehensive testing strategy with 85% minimum coverage requirement. This guide covers testing practices, tools, and workflows.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage (enforces 85% minimum)
pytest --cov=app --cov-fail-under=85

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m performance   # Performance tests only

# Run tests and generate HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_batch_processing.py      # Batch processing tests
│   ├── test_security_comprehensive.py # Security tests
│   ├── test_routes_comprehensive.py   # Route tests
│   └── test_core_modules.py          # Core functionality tests
├── integration/             # Integration tests
│   ├── test_api_endpoints.py         # API integration tests
│   └── test_insights_api.py          # Insights API tests
├── performance/             # Performance tests
│   └── test_performance_benchmark.py # Performance benchmarks
├── comprehensive/           # End-to-end tests
├── multimodal/             # Multimodal feature tests
├── manual/                 # Manual test scripts
├── conftest.py             # Shared fixtures
├── test_template.py        # Template for new tests
└── TESTING_GUIDELINES.md   # Detailed guidelines
```

## Test Configuration

### pytest.ini
The project uses pytest with the following configuration:
- **Coverage requirement**: 85% minimum (`--cov-fail-under=85`)
- **Async support**: Enabled with `asyncio_mode = auto`
- **Mock database**: Uses `USE_MOCK_DATABASE=true` for testing
- **Test markers**: unit, integration, performance, asyncio, slow

### Environment Variables
```bash
USE_MOCK_DATABASE=true     # Use mock database for tests
API_TOKENS=test-key-1,test-key-2  # Test API tokens
```

## Writing Tests

### Use the Template
Start with the test template for consistency:
```bash
cp tests/test_template.py tests/unit/test_new_feature.py
```

### Test Categories

#### 1. Unit Tests
Test individual components in isolation:
```python
@pytest.mark.unit
def test_memory_validation():
    """Test memory validation logic."""
    memory = Memory(content="test", importance=7.5)
    assert memory.is_valid()
```

#### 2. Integration Tests
Test component interactions:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_workflow(client, api_key):
    """Test complete API workflow."""
    response = await client.post("/memories", json=data, headers=auth)
    assert response.status_code == 201
```

#### 3. Performance Tests
Test performance requirements:
```python
@pytest.mark.performance
def test_search_speed():
    """Test search performance."""
    start = time.time()
    results = search_memories(query, large_dataset)
    elapsed = time.time() - start
    assert elapsed < 1.0  # Under 1 second
```

### Async Testing
Always use `@pytest.mark.asyncio` for async tests:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Mocking Patterns

#### Database Mocking
```python
def test_with_database_mock():
    with patch('app.database.get_db') as mock_db:
        mock_conn = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": "123"}
        
        # Test code here
```

#### External Service Mocking
```python
def test_with_service_mock():
    with patch('app.services.openai_client') as mock_openai:
        mock_openai.embed.return_value = [0.1] * 1536
        
        # Test code here
```

## Test Quality Standards

### Coverage Requirements
- **Overall Coverage**: 85% minimum (enforced)
- **Critical Paths**: 95% (auth, core operations)
- **New Code**: 90% coverage requirement
- **Complex Logic**: 100% branch coverage

### Quality Metrics
- Test execution time: <5 minutes for full suite
- Flaky test rate: <1%
- Test maintenance: <10% of development time

### Code Quality
- Use descriptive test names
- Include docstrings for complex tests
- Follow Arrange-Act-Assert pattern
- One assertion per concept
- Mock external dependencies

## Test Infrastructure

### Mock Database
The project uses a mock database for testing:
```python
from app.database_mock import MockDatabase

# Automatically used when USE_MOCK_DATABASE=true
```

### Fixtures
Common fixtures are defined in `conftest.py`:
- `client`: HTTP test client
- `api_key`: Test API key
- `sample_memory`: Sample memory data

### Test Data Factories
Use factories for generating test data:
```python
from tests.factories import MemoryFactory

memory = MemoryFactory.create(importance=8.0)
memories = MemoryFactory.create_batch(10)
```

## Running Tests

### Local Development
```bash
# Run all tests
pytest

# Run specific file
pytest tests/unit/test_batch_processing.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run fast tests only
pytest -m "not slow"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

### CI/CD Pipeline
Tests run automatically on:
- Every push to `develop` branch
- Pull requests to `main` branch
- Weekly quality reviews (Sundays 2 AM UTC)

### Performance Testing
```bash
# Run performance tests
pytest -m performance

# Run with performance profiling
pytest --profile tests/performance/
```

## Test Quality Review

### Automated Analysis
The project includes automated test quality analysis:
```bash
# Run quality analyzer
python scripts/test-quality-analyzer.py

# Generates:
# - test-quality-report.md
# - test-quality-data.json
# - coverage reports
```

### Weekly Reviews
- Automated quality reports generated weekly
- Coverage trend analysis
- Performance regression detection
- Test maintenance recommendations

### Metrics Tracked
- Coverage percentages by module
- Test execution times
- Flaky test detection
- Test code quality metrics

## Debugging Tests

### Debug Failed Tests
```bash
# Run with detailed output
pytest -vvv --tb=long

# Drop into debugger on failure
pytest --pdb

# Run specific failing test
pytest tests/unit/test_feature.py::test_specific_case -vvv
```

### Debug Performance Issues
```bash
# Profile test execution
pytest --durations=20

# Memory profiling
pytest --profile-mem
```

### Common Issues
1. **Async test failures**: Ensure `@pytest.mark.asyncio` is used
2. **Mock issues**: Patch at the right import level
3. **Database conflicts**: Use test database or mocks
4. **Flaky tests**: Check for race conditions or external dependencies

## Best Practices

### Do's
✅ Use descriptive test names
✅ Mock external dependencies
✅ Test both success and error paths
✅ Use fixtures for setup/teardown
✅ Keep tests focused and isolated
✅ Include performance tests for critical paths
✅ Document complex test scenarios

### Don'ts
❌ Test implementation details
❌ Create overly complex test setup
❌ Skip error case testing
❌ Use real external services in tests
❌ Write tests that depend on each other
❌ Ignore test execution time
❌ Forget to clean up resources

## Contributing

### Before Submitting PRs
1. Ensure all tests pass: `pytest`
2. Check coverage: `pytest --cov=app --cov-fail-under=85`
3. Run quality analyzer: `python scripts/test-quality-analyzer.py`
4. Follow testing guidelines
5. Add tests for new functionality

### Test Review Checklist
- [ ] Tests cover happy path and edge cases
- [ ] Error conditions are tested
- [ ] Mocks are used appropriately
- [ ] Test names are descriptive
- [ ] No test dependencies
- [ ] Performance requirements tested
- [ ] Documentation updated

## Resources

- [Testing Guidelines](../tests/TESTING_GUIDELINES.md) - Detailed patterns and practices
- [Test Template](../tests/test_template.py) - Template for new tests
- [pytest Documentation](https://docs.pytest.org/) - Official pytest docs
- [Test Quality Reports](../../test-quality-report.md) - Generated quality reports

## Troubleshooting

### Common Errors

**ImportError during tests**:
```bash
# Install test dependencies
pip install -r requirements.txt
```

**Coverage fails to reach 85%**:
```bash
# Generate coverage report to see gaps
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

**Async tests failing**:
```python
# Ensure proper async test decoration
@pytest.mark.asyncio
async def test_async_function():
    pass
```

**Database connection errors**:
```bash
# Ensure mock database is enabled
export USE_MOCK_DATABASE=true
```

### Getting Help
- Check existing tests for patterns
- Review testing guidelines
- Run test quality analyzer for insights
- Consult the test template for structure

---

**Remember**: Good tests are an investment in code quality and development velocity. Follow the guidelines and maintain high standards.