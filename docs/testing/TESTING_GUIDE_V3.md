# Second Brain v3.0.0 - Testing Guide

## Overview

This guide covers the testing strategy for Second Brain v3.0.0, focusing on practical, working tests that match our current architecture.

## Testing Philosophy

1. **Pragmatic Testing**: Focus on tests that actually work and provide value
2. **Fast Feedback**: Quick test execution for development velocity
3. **Real Dependencies**: Use actual services where practical, mock where necessary
4. **Clean Architecture**: Test each layer appropriately

## Current Test Structure

```
tests/
├── unit/                    # Fast, focused unit tests
│   ├── domain/             # Domain model tests
│   │   ├── test_memory.py  # Memory model tests
│   │   └── test_user.py    # User model tests
│   ├── synthesis/          # Synthesis feature tests
│   │   ├── test_report_models.py
│   │   └── test_websocket_models.py
│   ├── test_exceptions.py  # Exception handling
│   ├── test_logging_monitoring.py
│   ├── test_security_audit.py
│   ├── test_dependency_injection.py
│   ├── test_memory_service.py
│   ├── test_session_service.py
│   └── test_health_service.py
├── integration/            # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_health.py
│   └── synthesis/
│       └── test_synthesis_integration.py
├── validation/             # Environment validation
│   ├── test_ci_simulation.py
│   └── test_env.py
├── test_ingestion_engine.py  # Ingestion tests
├── conftest.py            # Shared fixtures
└── pytest.ini             # Pytest configuration
```

## Running Tests

### Quick Start with Virtual Environment

```bash
# Always use the project's virtual environment
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Run all tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Run with coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=app --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# Integration tests
.venv/Scripts/python.exe -m pytest tests/integration/ -v

# Specific test file
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py -v

# Specific test
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py::TestErrorResponse::test_error_response_creation -v
```

### Currently Working Test Suites

These tests are validated and working:

```bash
# Core functionality
.venv/Scripts/python.exe -m pytest tests/unit/test_exceptions.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_logging_monitoring.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_security_audit.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_dependency_injection.py -v

# Domain tests
.venv/Scripts/python.exe -m pytest tests/unit/domain/ -v

# Ingestion tests
.venv/Scripts/python.exe -m pytest tests/test_ingestion_engine.py -v
```

## Writing Tests

### Unit Test Example - Domain Model

```python
"""Test memory domain model"""
import pytest
from app.models.memory import Memory, MemoryType

class TestMemory:
    """Test Memory model"""
    
    def test_memory_creation(self):
        """Test creating a memory"""
        memory = Memory(
            content="Test memory content",
            memory_type=MemoryType.SEMANTIC,
            user_id="user123",
            tags=["test", "unit-test"]
        )
        
        assert memory.content == "Test memory content"
        assert memory.memory_type == "semantic"  # Enum value
        assert memory.user_id == "user123"
        assert memory.tags == ["test", "unit-test"]
        assert memory.importance_score == 0.5  # Default
    
    def test_memory_with_metadata(self):
        """Test memory with metadata"""
        metadata = {"source": "test", "category": "unit-test"}
        memory = Memory(
            content="Test content",
            metadata=metadata
        )
        
        assert memory.metadata == metadata
        assert memory.metadata["source"] == "test"
```

### Unit Test Example - Service Layer

```python
"""Test memory service"""
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.memory_service import MemoryService
from app.core.exceptions import NotFoundException

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
        return MemoryService(database=mock_database)
    
    @pytest.mark.asyncio
    async def test_store_memory_success(self, memory_service):
        """Test successful memory storage"""
        memory_id = await memory_service.store_memory(
            content="Test memory content",
            memory_type="semantic"
        )
        
        assert memory_id == "mem-123"
        memory_service.database.store_memory.assert_called_once()
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

`pytest.ini`:
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

## Test Best Practices

### 1. Use Proper Fixtures

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

### 2. Mock External Services

```python
# Mock OpenAI service
@pytest.fixture
def mock_openai():
    with patch("app.services.openai_service.OpenAI") as mock:
        mock.return_value.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        yield mock
```

### 3. Test Async Code Properly

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations"""
    result = await some_async_function()
    assert result is not None
```

### 4. Validate Error Handling

```python
def test_validation_error():
    """Test validation error handling"""
    with pytest.raises(ValidationException) as exc_info:
        validate_input("")
    
    assert "required" in str(exc_info.value).lower()
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

## Test Maintenance

### Regular Tasks
1. **Weekly**: Review and fix failing tests
2. **Monthly**: Update test data and fixtures
3. **Quarterly**: Review coverage and add missing tests
4. **Yearly**: Refactor test structure and remove obsolete tests

### Adding New Tests
1. Write test first (TDD approach when appropriate)
2. Ensure test fails initially
3. Implement feature
4. Verify test passes
5. Add to appropriate test suite
6. Update documentation

---

This testing guide provides a practical approach to testing Second Brain v3.0.0. Always use the virtual environment and follow the established patterns for consistent, maintainable tests.