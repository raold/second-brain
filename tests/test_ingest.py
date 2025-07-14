# /tests/test_ingest.py

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

@patch("app.storage.qdrant_client.get_openai_client")
@patch("app.storage.qdrant_client.qdrant_upsert")
@patch("app.storage.markdown_writer.write_markdown")
def test_ingest(mock_write_markdown, mock_qdrant_upsert, mock_get_openai_client):
    mock_openai_client = MagicMock()
    mock_get_openai_client.return_value = mock_openai_client

    payload = {
        "id": "test-id",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "metadata": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"}
    }

    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 200
    mock_write_markdown.assert_called_once()
    mock_qdrant_upsert.assert_called_once()
