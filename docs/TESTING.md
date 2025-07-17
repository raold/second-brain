# Second Brain v2.0.0 - Testing Guide

## Overview
Second Brain v2.0.0 includes a comprehensive testing framework with both unit tests and integration tests. This guide covers testing strategies, mock database usage, and development workflows.

## Testing Framework

### Test Structure
```
tests/
├── test_refactored.py      # Main test suite
├── test_mock_database.py   # Mock database tests
├── test_db_setup.py        # Database setup tests
└── test_storage_handler.py # Legacy storage tests
```

### Core Test Files
- **`test_refactored.py`**: Complete test suite for v2.0.0
- **`test_mock_database.py`**: Standalone mock database tests
- **`test_db_setup.py`**: Database initialization tests

## Running Tests

### Quick Test
```bash
# Run main test suite
python -m pytest test_refactored.py -v

# Run with coverage
python -m pytest test_refactored.py --cov=app --cov-report=html

# Run specific test
python -m pytest test_refactored.py::test_health_check -v
```

### Mock Database Testing
```bash
# Run mock database tests (no OpenAI API required)
python test_mock_database.py

# Run mock database with pytest
python -m pytest test_mock_database.py -v
```

### Database Setup Testing
```bash
# Test database initialization
python test_db_setup.py

# Test with pytest
python -m pytest test_db_setup.py -v
```

## Test Configuration

### Environment Setup
```bash
# Test environment variables
export DATABASE_URL="postgresql://test:test@localhost:5432/test_db"
export OPENAI_API_KEY="test_key"
export AUTH_TOKEN="test_token"

# Or create .env.test
cp .env.example .env.test
```

### Test Database
```sql
-- Create test database
CREATE DATABASE test_second_brain;

-- Setup test user
CREATE USER test_user WITH PASSWORD 'test_password';
GRANT ALL PRIVILEGES ON DATABASE test_second_brain TO test_user;
```

## Test Categories

### 1. Unit Tests
```python
# Example unit test
def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### 2. Integration Tests
```python
# Example integration test
def test_store_and_retrieve_memory():
    """Test full memory lifecycle"""
    # Store memory
    memory_data = {
        "content": "Test memory content",
        "metadata": {"category": "test"}
    }
    response = client.post("/memories", json=memory_data)
    assert response.status_code == 201
    
    # Retrieve memory
    memory_id = response.json()["id"]
    response = client.get(f"/memories/{memory_id}")
    assert response.status_code == 200
    assert response.json()["content"] == "Test memory content"
```

### 3. Mock Database Tests
```python
# Example mock database test
async def test_mock_database():
    """Test mock database operations"""
    mock_db = MockDatabase()
    
    # Store memory
    memory_id = await mock_db.store_memory(
        "Test content",
        {"category": "test"}
    )
    
    # Search memories
    results = await mock_db.search_memories("test")
    assert len(results) > 0
    assert results[0]["content"] == "Test content"
```

## Test Suite Details

### `test_refactored.py`
Complete test suite with the following test cases:

#### API Endpoint Tests
- `test_health_check()` - Health endpoint
- `test_store_memory()` - Memory creation
- `test_get_memory()` - Memory retrieval
- `test_list_memories()` - Memory listing
- `test_delete_memory()` - Memory deletion
- `test_search_memories()` - Semantic search

#### Authentication Tests
- `test_authentication_required()` - Auth validation
- `test_invalid_token()` - Token validation
- `test_missing_token()` - Missing auth header

#### Error Handling Tests
- `test_memory_not_found()` - 404 handling
- `test_invalid_request_data()` - Validation errors
- `test_database_connection_error()` - DB error handling

#### Database Integration Tests
- `test_database_connection()` - Connection testing
- `test_vector_search()` - pgvector functionality
- `test_metadata_storage()` - JSONB operations

### `test_mock_database.py`
Standalone mock database tests:

```python
#!/usr/bin/env python3

import asyncio
import uuid
from app.database_mock import MockDatabase

async def test_mock_database():
    print("Testing Mock Database...")
    
    # Initialize mock database
    mock_db = MockDatabase()
    
    # Test 1: Store memory
    print("\n1. Testing store_memory...")
    memory_id = await mock_db.store_memory(
        "I learned about PostgreSQL pgvector for semantic search",
        {"category": "learning", "tags": ["database", "AI"]}
    )
    print(f"✓ Stored memory with ID: {memory_id}")
    
    # Test 2: Get memory
    print("\n2. Testing get_memory...")
    memory = await mock_db.get_memory(memory_id)
    print(f"✓ Retrieved memory: {memory['content'][:50]}...")
    
    # Test 3: Search memories
    print("\n3. Testing search_memories...")
    results = await mock_db.search_memories("database search", limit=3)
    print(f"✓ Found {len(results)} matching memories")
    
    # Test 4: List all memories
    print("\n4. Testing list_memories...")
    all_memories = await mock_db.list_memories(limit=10)
    print(f"✓ Listed {len(all_memories)} total memories")
    
    # Test 5: Delete memory
    print("\n5. Testing delete_memory...")
    deleted = await mock_db.delete_memory(memory_id)
    print(f"✓ Memory deleted: {deleted}")
    
    print("\n✅ All mock database tests passed!")

if __name__ == "__main__":
    asyncio.run(test_mock_database())
```

## Mock Database Usage

### Purpose
The mock database allows testing without:
- OpenAI API costs
- Real database setup
- Network dependencies
- External service dependencies

### Features
- In-memory storage
- Simulated embeddings
- Compatible API interface
- Deterministic results

### Usage Example
```python
from app.database_mock import MockDatabase

# Initialize mock database
mock_db = MockDatabase()

# Use exactly like real database
memory_id = await mock_db.store_memory(
    "Test content",
    {"category": "test"}
)

# Search with simulated embeddings
results = await mock_db.search_memories("query")
```

## Performance Testing

### Memory Performance
```python
import time
import asyncio

async def test_performance():
    """Test memory operation performance"""
    mock_db = MockDatabase()
    
    # Test store performance
    start_time = time.time()
    for i in range(100):
        await mock_db.store_memory(f"Test memory {i}", {"index": i})
    store_time = time.time() - start_time
    
    # Test search performance
    start_time = time.time()
    for i in range(10):
        await mock_db.search_memories("test query", limit=5)
    search_time = time.time() - start_time
    
    print(f"Store 100 memories: {store_time:.2f}s")
    print(f"10 searches: {search_time:.2f}s")
```

### Load Testing
```python
import asyncio
import aiohttp

async def load_test():
    """Basic load test for API endpoints"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(50):
            task = session.get(
                "http://localhost:8000/health",
                headers={"Authorization": "Bearer test_token"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        success_count = sum(1 for r in responses if r.status == 200)
        print(f"Load test: {success_count}/50 successful requests")
```

## Test Data Management

### Test Data Setup
```python
# Test data fixtures
TEST_MEMORIES = [
    {
        "content": "PostgreSQL is a powerful relational database",
        "metadata": {"category": "database", "difficulty": "beginner"}
    },
    {
        "content": "pgvector extension enables vector similarity search",
        "metadata": {"category": "database", "difficulty": "intermediate"}
    },
    {
        "content": "FastAPI provides modern Python web framework",
        "metadata": {"category": "web", "difficulty": "intermediate"}
    }
]

async def setup_test_data(db):
    """Setup test data for testing"""
    for memory_data in TEST_MEMORIES:
        await db.store_memory(
            memory_data["content"],
            memory_data["metadata"]
        )
```

### Test Data Cleanup
```python
async def cleanup_test_data(db):
    """Clean up test data after testing"""
    # For mock database, just reinitialize
    if isinstance(db, MockDatabase):
        db.memories = {}
        return
    
    # For real database, delete test data
    await db.execute("DELETE FROM memories WHERE metadata->>'category' = 'test'")
```

## Continuous Integration

### GitHub Actions Setup
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: ankane/pgvector
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-minimal.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        python -m pytest test_refactored.py --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres
        OPENAI_API_KEY: test_key
        AUTH_TOKEN: test_token
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Test Coverage

### Coverage Configuration
```ini
# .coveragerc
[run]
source = app
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

### Coverage Reports
```bash
# Generate HTML coverage report
python -m pytest test_refactored.py --cov=app --cov-report=html

# Generate XML coverage report
python -m pytest test_refactored.py --cov=app --cov-report=xml

# View coverage summary
python -m pytest test_refactored.py --cov=app --cov-report=term-missing
```

## Debugging Tests

### Debug Mode
```python
# Run tests with debug output
python -m pytest test_refactored.py -v -s

# Run single test with debug
python -m pytest test_refactored.py::test_store_memory -v -s

# Run with pdb debugger
python -m pytest test_refactored.py --pdb
```

### Test Logging
```python
import logging
import pytest

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture
def debug_logger():
    return logging.getLogger(__name__)
```

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test names
- Include docstrings for complex tests
- Use fixtures for common setup

### Mock Usage
- Use mock database for unit tests
- Mock external services (OpenAI API)
- Test error conditions with mocks
- Validate mock interactions

### Assertions
- Use specific assertions
- Test both success and failure cases
- Validate response structure
- Check error messages

### Test Data
- Use realistic test data
- Test edge cases
- Clean up after tests
- Isolate test data

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database is running
   psql $DATABASE_URL -c "SELECT 1"
   
   # Check pgvector extension
   psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname='vector'"
   ```

2. **OpenAI API Errors**
   ```python
   # Use mock database for testing
   from app.database_mock import MockDatabase
   mock_db = MockDatabase()
   ```

3. **Authentication Errors**
   ```python
   # Check auth token in tests
   headers = {"Authorization": "Bearer test_token"}
   response = client.get("/health", headers=headers)
   ```

### Debug Commands
```bash
# Run tests with verbose output
python -m pytest test_refactored.py -v

# Run with coverage and debug
python -m pytest test_refactored.py --cov=app --cov-report=term-missing -v

# Run single test
python -m pytest test_refactored.py::test_health_check -v

# Run with print statements
python -m pytest test_refactored.py -s
```

## Contributing

### Test Requirements
- All new features must have tests
- Maintain >90% test coverage
- Include both unit and integration tests
- Test error conditions
- Update documentation

### Test Review Checklist
- [ ] Tests cover new functionality
- [ ] Tests cover error conditions
- [ ] Tests are deterministic
- [ ] Tests clean up after themselves
- [ ] Tests have descriptive names
- [ ] Tests include docstrings
- [ ] Coverage remains above 90%

---

This testing guide ensures reliable and maintainable code for Second Brain v2.0.0. For questions or issues, please check the GitHub repository or open an issue.
