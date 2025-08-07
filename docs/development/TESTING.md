# Testing Guide - Second Brain v3.0.0

## Overview

Second Brain v3.0.0 uses a comprehensive testing strategy with pytest, focusing on:
- Unit tests for individual components
- Integration tests for API endpoints
- Security and monitoring tests
- Clean Architecture validation

## Test Structure

```
tests/
├── unit/                           # Unit tests
│   ├── domain/                     # Domain model tests
│   │   ├── test_memory.py
│   │   └── test_user.py
│   ├── synthesis/                  # Synthesis feature tests
│   │   ├── test_report_models.py
│   │   └── test_websocket_models.py
│   ├── test_exceptions.py          # Exception handling tests
│   ├── test_logging_monitoring.py  # Logging/monitoring tests
│   ├── test_security_audit.py      # Security tests
│   ├── test_dependency_injection.py # DI tests
│   ├── test_memory_service.py      # Memory service tests
│   ├── test_session_service.py     # Session service tests
│   └── test_health_service.py      # Health service tests
├── integration/                    # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_health.py
│   └── synthesis/
│       └── test_synthesis_integration.py
├── validation/                     # Validation tests
│   ├── test_ci_simulation.py
│   └── test_env.py
├── conftest.py                     # Shared fixtures
└── pytest.ini                      # Pytest configuration
```

## Running Tests

### Quick Start

```bash
# Activate virtual environment
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Run all tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Run with coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=app --cov-report=html
```

### Test Categories

#### Unit Tests
```bash
# Run all unit tests
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# Run specific test file
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py -v

# Run specific test
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py::TestErrorResponse::test_error_response_creation -v
```

#### Integration Tests
```bash
# Run integration tests
.venv/Scripts/python.exe -m pytest tests/integration/ -v

# Run with markers
.venv/Scripts/python.exe -m pytest -m "not slow" tests/
```

#### Working Test Suites

Currently validated and working:
```bash
# Core functionality tests
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_logging_monitoring.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_security_audit.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_dependency_injection.py -v

# Domain tests
.venv/Scripts/python.exe -m pytest tests/unit/domain/ -v

# Synthesis tests
.venv/Scripts/python.exe -m pytest tests/unit/synthesis/test_report_models.py -v
```

## Test Configuration

### Environment Setup

Create `.env.test` for test configuration:
```bash
# Test environment
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_secondbrain
REDIS_URL=redis://localhost:6379/1
USE_MOCK_DATABASE=false
LOG_LEVEL=DEBUG
ENVIRONMENT=test

# Test API keys
OPENAI_API_KEY=test-key
API_TOKENS=test-token-1,test-token-2

# Security
SECRET_KEY=test-secret-key-for-jwt-tokens
```

### Pytest Configuration

`pytest.ini` configuration:
```ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra 
    -q 
    --strict-markers
    --ignore=tests/manual
    --ignore=tests/performance
    --tb=short

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    security: marks tests as security-related
    
asyncio_mode = strict

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## Writing Tests

### Unit Test Example

```python
"""Test memory service functionality"""
import pytest
from unittest.mock import Mock, AsyncMock

from app.services.memory_service import MemoryService
from app.core.exceptions import NotFoundException, ValidationException


class TestMemoryService:
    """Test memory service operations"""
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database"""
        db = AsyncMock()
        db.store_memory = AsyncMock(return_value="mem-123")
        db.get_memory = AsyncMock(return_value={
            "id": "mem-123",
            "content": "Test memory",
            "created_at": "2025-01-26T10:00:00Z"
        })
        return db
    
    @pytest.fixture
    def memory_service(self, mock_database):
        """Create memory service with mock database"""
        service = MemoryService(database=mock_database)
        return service
    
    @pytest.mark.asyncio
    async def test_store_memory_success(self, memory_service):
        """Test successful memory storage"""
        # Act
        memory_id = await memory_service.store_memory(
            content="Test memory content",
            memory_type="semantic"
        )
        
        # Assert
        assert memory_id == "mem-123"
        memory_service.database.store_memory.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, memory_service):
        """Test getting non-existent memory"""
        # Arrange
        memory_service.database.get_memory.return_value = None
        
        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            await memory_service.get_memory("invalid-id")
        
        assert "Memory" in str(exc_info.value)
```

### Integration Test Example

```python
"""Test API endpoints"""
import pytest
from fastapi.testclient import TestClient

from app.app import app


class TestMemoryEndpoints:
    """Test memory API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers"""
        return {"api_key": "test-token-1"}
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_create_memory(self, client, auth_headers):
        """Test memory creation"""
        memory_data = {
            "content": "Test memory",
            "memory_type": "semantic",
            "importance_score": 0.8
        }
        
        response = client.post(
            "/memories",
            json=memory_data,
            params=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Test memory"
```

## Test Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names that explain what's being tested
- Include docstrings for complex test scenarios
- Follow AAA pattern: Arrange, Act, Assert

### 2. Fixtures
```python
@pytest.fixture
async def test_database():
    """Create test database connection"""
    from app.database import Database
    
    db = Database(database_url=os.getenv("TEST_DATABASE_URL"))
    await db.initialize()
    
    yield db
    
    # Cleanup
    await db.close()
```

### 3. Mocking
```python
# Mock external services
@pytest.fixture
def mock_openai():
    with patch("app.services.openai_service.OpenAI") as mock:
        mock.return_value.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        yield mock

# Mock time-dependent functions
@pytest.fixture
def frozen_time():
    with patch("app.services.session_service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2025, 1, 26, 10, 0, 0)
        yield mock_dt
```

### 4. Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations"""
    result = await some_async_function()
    assert result is not None

# Use async fixtures
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### 5. Error Testing
```python
def test_validation_error():
    """Test validation error handling"""
    with pytest.raises(ValidationException) as exc_info:
        validate_input("")
    
    assert "required" in str(exc_info.value).lower()

def test_http_error_response(client):
    """Test HTTP error responses"""
    response = client.get("/memories/invalid-id")
    assert response.status_code == 404
    
    data = response.json()
    assert data["error_code"] == "NOT_FOUND"
```

## Coverage Requirements

### Target Coverage
- Overall: >80%
- Core services: >90%
- API routes: >85%
- Utilities: >70%

### Generate Coverage Reports
```bash
# HTML report
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=html

# Terminal report with missing lines
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing

# XML report for CI
.venv/Scripts/python.exe -m pytest --cov=app --cov-report=xml
```

## Debugging Tests

### Verbose Output
```bash
# Show print statements
.venv/Scripts/python.exe -m pytest -s tests/

# Verbose test names
.venv/Scripts/python.exe -m pytest -v tests/

# Extra verbose with setup/teardown
.venv/Scripts/python.exe -m pytest -vv tests/
```

### Debug on Failure
```bash
# Drop into debugger on failure
.venv/Scripts/python.exe -m pytest --pdb tests/

# Stop on first failure
.venv/Scripts/python.exe -m pytest -x tests/

# Show local variables on failure
.venv/Scripts/python.exe -m pytest -l tests/
```

### Logging in Tests
```python
import logging

# Configure test logging
logging.basicConfig(level=logging.DEBUG)

def test_with_logging(caplog):
    """Test with captured logs"""
    with caplog.at_level(logging.INFO):
        some_function()
    
    assert "Expected log message" in caplog.text
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r config/requirements.txt
        pip install -r config/requirements-dev.txt
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        API_TOKENS: test-token
      run: |
        python -m pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: .venv/Scripts/python.exe -m pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Common Issues and Solutions

### 1. Import Errors
```python
# Problem: ModuleNotFoundError
# Solution: Ensure PYTHONPATH includes project root
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### 2. Async Test Warnings
```python
# Problem: RuntimeWarning: coroutine was never awaited
# Solution: Use @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
```

### 3. Database Connection Issues
```python
# Problem: Database connection fails in tests
# Solution: Use test database or mock
@pytest.fixture
def use_test_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test@localhost/test_db")
```

### 4. Flaky Tests
```python
# Problem: Tests pass/fail randomly
# Solution: Fix timing issues and external dependencies
@pytest.mark.flaky(retries=3, delay=1)
def test_external_api():
    # Test with retries for external services
    pass
```

## Test Maintenance

### Regular Tasks
1. **Weekly**: Review and fix failing tests
2. **Monthly**: Update test data and fixtures
3. **Quarterly**: Review coverage and add missing tests
4. **Yearly**: Refactor test structure and remove obsolete tests

### Adding New Tests
1. Write test first (TDD approach)
2. Ensure test fails initially
3. Implement feature
4. Verify test passes
5. Add to appropriate test suite
6. Update documentation

---

This testing guide provides a comprehensive approach to testing Second Brain v3.0.0. Always use the virtual environment and follow the established patterns for consistent, maintainable tests.