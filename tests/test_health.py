# /tests/test_health.py

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    from app.config import Config
    monkeypatch.setattr(Config, 'API_TOKENS', {'test-token'})

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@patch("app.storage.qdrant_client.qdrant_upsert")
@patch("app.storage.qdrant_client.qdrant_search")
def test_health_check(mock_qdrant_search, mock_qdrant_upsert):
    mock_qdrant_search.return_value = []
    mock_qdrant_upsert.return_value = None

    response = client.get("/health", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
