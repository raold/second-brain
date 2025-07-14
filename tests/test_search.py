# /tests/test_search.py

from fastapi.testclient import TestClient
from app.main import app
from app.config import Config
from unittest.mock import patch, MagicMock
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    monkeypatch.setattr(Config, 'API_TOKENS', {'test-token'})

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@patch("app.storage.qdrant_client.qdrant_search", return_value=[])
@patch("app.storage.qdrant_client.get_openai_client")
def test_search_empty(mock_get_openai_client, mock_qdrant_search):
    mock_openai_client = MagicMock()
    mock_get_openai_client.return_value = mock_openai_client

    response = client.get("/search?q=nonexistent", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"query": "nonexistent", "results": []}
    mock_qdrant_search.assert_called_once()
