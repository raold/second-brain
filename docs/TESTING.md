# LLM Output Processor - Testing Guide

## Overview

This document describes how to run, extend, and maintain the test suite for the LLM Output Processor, including our approach to mocking external dependencies (OpenAI, Qdrant) for fast, reliable integration tests.

---

## Running Tests

- **All tests:**
  ```bash
  make test
  # or
  pytest
  ```
- **Linting:**
  ```bash
  make lint
  # or
  ruff .
  ```
- **Test coverage report:**
  ```bash
  pytest --cov=app --cov-report=term-missing
  ```

---

## Mocking External Dependencies

### Why Mock?
- **No real API keys required** (OpenAI)
- **No running Qdrant instance required**
- **Tests are fast, reliable, and isolated**
- **CI/CD is deterministic and secure**

### OpenAI Embedding
- Patch `get_openai_embedding` in all test files to return a fixed vector:
  ```python
  @pytest.fixture(autouse=True)
  def mock_openai_embedding():
      with patch("app.utils.openai_client.get_openai_embedding", return_value=[0.1] * 1536):
          yield
  ```

### Qdrant Vector DB
- Patch `QdrantClient.upsert` and `QdrantClient.search` in tests that require Qdrant operations:
  ```python
  @patch("app.storage.qdrant_client.client.upsert", return_value=None)
  @patch("app.storage.qdrant_client.client.search", return_value=[...])
  def test_something(...):
      ...
  ```
- Patch `to_uuid` to return a string for test compatibility:
  ```python
  @patch("app.storage.qdrant_client.to_uuid", lambda x: str(x))
  ```

### General Best Practice
- Always patch external API calls at the import path used in the code under test, returning controlled results.
- Use fixtures for global mocks, and decorators for test-specific mocks.

---

## Example: Full Integration Test with Mocks
```python
from unittest.mock import patch
import pytest

@patch("app.storage.qdrant_client.to_uuid", lambda x: str(x))
@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.upsert", return_value=None)
@patch("app.storage.qdrant_client.client.search", return_value=[type("Result", (), {"id": "test-id-123", "score": 0.99, "payload": {"data": {"note": "Test note for version tracking"}, "metadata": {"embedding_model": "text-embedding-3-small", "model_version": "gpt-4o", "timestamp": "2025-07-14T00:00:00Z"}}, "type": "test", "priority": "low"})()])
def test_ingest_and_search_versions(mock_search, mock_upsert, mock_embedding):
    from app.storage.qdrant_client import qdrant_upsert, qdrant_search
    payload = {"id": "test-id-123", "data": {"note": "Test note for version tracking"}, "type": "test", "priority": "low"}
    qdrant_upsert(payload)
    results = qdrant_search("Test note for version tracking", top_k=1)
    assert results, "No results returned from search"
    result = results[0]
    assert result["embedding_model"] == "text-embedding-3-small"
    assert result["model_version"] == "gpt-4o"
```

---

## Testing Metrics & Monitoring

### Prometheus Metrics
- The `/metrics` endpoint is public and returns Prometheus-formatted metrics.
- Test with:
  ```python
  def test_metrics_endpoint():
      response = client.get("/metrics")
      assert response.status_code == 200
      assert "# HELP" in response.text and "# TYPE" in response.text
  ```
- No mocking required for Prometheus; metrics are in-memory.

### Sentry Error Monitoring
- Sentry is only enabled if `SENTRY_DSN` is set in the environment.
- To test Sentry integration, set a dummy DSN and trigger an error.
- To mock Sentry in tests:
  ```python
  import sentry_sdk
  from unittest.mock import patch
  @patch.object(sentry_sdk, 'init')
  def test_sentry_integration(mock_init):
      # Your test code here
      mock_init.assert_called()
  ```

---

## Testing the /records Endpoint
- The `/records` endpoint lists records with filtering and pagination.
- Mock Qdrant's `client.scroll` in tests:
  ```python
  @patch("app.storage.qdrant_client.client.scroll", return_value=([type("Point", (), {"id": "abc123", "payload": {"data": {"note": "Test note"}, "type": "test", "metadata": {"timestamp": "2025-07-14T00:00:00Z"}}})()], None, None))
  def test_records_endpoint(mock_scroll):
      response = client.get("/records", headers=AUTH_HEADER)
      assert response.status_code == 200
      # ...
  ```

---

## Best Practices
- **Isolate all external dependencies** in tests.
- **Use fixtures** for repeated setup/teardown.
- **Test both success and failure cases** (e.g., mock exceptions).
- **Keep tests fast**—avoid real network or disk I/O.
- **Document new test patterns** in this file.

---

## See Also
- [USAGE.md](./USAGE.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [CI_CACHING.md](./CI_CACHING.md)
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md) 