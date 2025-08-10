# Testing Guide

## Run Tests
```bash
# All tests
pytest tests/

# Specific suite
pytest tests/unit/
pytest tests/integration/

# With coverage
pytest --cov=app tests/
```

## Test Structure
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Database/API tests
└── conftest.py     # Shared fixtures
```

## Writing Tests
```python
# tests/unit/test_memory.py
async def test_create_memory():
    service = MemoryService()
    memory = await service.create_memory(
        content="Test memory",
        importance_score=0.8
    )
    assert memory.id
    assert memory.content == "Test memory"
```

## Database Tests
Tests use a separate test database. Set `TEST_DATABASE_URL` in `.env`.

## Fixtures
Common fixtures in `conftest.py`:
- `async_client` - Test API client
- `test_db` - Clean database per test
- `mock_openai` - Mocked embeddings