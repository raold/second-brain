from fastapi.testclient import TestClient
from app.main import app
from app.config import Config
from unittest.mock import patch
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    monkeypatch.setattr(Config, 'API_TOKENS', {'test-token'})

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@patch("app.qdrant_client.qdrant_search", return_value=[])
def test_search_empty(mock_qdrant_search):
    response = client.get("/search?q=nonexistent", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == []
    mock_qdrant_search.assert_called_once()
