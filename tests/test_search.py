# /tests/test_search.py

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    monkeypatch.setattr(Config, 'API_TOKENS', ['test-token'])

@pytest.fixture(autouse=True)
def mock_openai_embedding():
    with patch("app.utils.openai_client.get_openai_embedding", return_value=[0.1] * 1536):
        yield

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@patch("app.router.qdrant_search", return_value=[])
def test_search_empty(mock_qdrant_search):
    response = client.get("/search?q=nonexistent", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"query": "nonexistent", "results": []}
    mock_qdrant_search.assert_called_once_with("nonexistent", filters={})

@patch("app.router.qdrant_search")
def test_search_embedding_failure(mock_qdrant_search):
    # Mock the search function to raise an exception
    mock_qdrant_search.side_effect = Exception("OpenAI API error")

    response = client.get("/search?q=nonexistent", headers=AUTH_HEADER)
    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]

@patch("app.router.qdrant_search")
def test_search_with_results(mock_qdrant_search):
    # Mock search results
    mock_results = [
        {
            "id": "test-1",
            "score": 0.95,
            "note": "Test note 1",
            "timestamp": "2025-07-13T00:00:00Z",
            "source": "test",
            "type": "note",
            "priority": "normal"
        }
    ]
    mock_qdrant_search.return_value = mock_results

    response = client.get("/search?q=test", headers=AUTH_HEADER)
    assert response.status_code == 200
    result = response.json()
    assert result["query"] == "test"
    assert len(result["results"]) == 1
    assert result["results"][0]["note"] == "Test note 1"
