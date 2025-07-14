# /tests/test_ingest.py

from fastapi.testclient import TestClient
from app.main import app
from app.config import Config
from app.models import PayloadType, Priority
from unittest.mock import patch, MagicMock
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    monkeypatch.setattr(Config, 'API_TOKENS', {'test-token'})

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@patch("app.router.qdrant_upsert", return_value=True)
@patch("app.router.write_markdown", return_value=True)
def test_ingest(mock_write_markdown, mock_qdrant_upsert):
    payload = {
        "id": "test-id",
        "type": PayloadType.NOTE,
        "context": "test-context",
        "priority": Priority.NORMAL,
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "metadata": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"}
    }

    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json()["status"] == "ingested"
    mock_write_markdown.assert_called_once()
    mock_qdrant_upsert.assert_called_once()

@patch("app.router.qdrant_upsert")
@patch("app.router.write_markdown", return_value=True)
def test_ingest_qdrant_failure(mock_write_markdown, mock_qdrant_upsert):
    # Mock the upsert function to raise an exception
    mock_qdrant_upsert.side_effect = Exception("Qdrant connection failed")

    payload = {
        "id": "test-id",
        "type": PayloadType.NOTE,
        "context": "test-context",
        "priority": Priority.NORMAL,
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "metadata": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"}
    }

    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 500
    assert "Failed to ingest payload" in response.json()["detail"]

@patch("app.router.write_markdown")
def test_ingest_markdown_failure(mock_write_markdown):
    # Mock the markdown function to raise an exception
    mock_write_markdown.side_effect = Exception("File system error")

    payload = {
        "id": "test-id",
        "type": PayloadType.NOTE,
        "context": "test-context",
        "priority": Priority.NORMAL,
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "metadata": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"}
    }

    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 500
    assert "Failed to ingest payload" in response.json()["detail"]
