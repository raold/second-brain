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

def test_ws_generate_stream():
    token = "test-token"  # Replace with a valid token if needed
    prompt = "Hello world this is a test"
    with client.websocket_connect(f"/ws/generate?token={token}") as ws:
        ws.send_json({"prompt": prompt, "json": True})
        received = []
        for _ in range(len(prompt.split())):
            msg = ws.receive_json()
            assert "text" in msg
            received.append(msg["text"].strip())
        assert " ".join(received).strip() == prompt

def test_models_endpoint():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "model_versions" in data
    assert "llm" in data["model_versions"]
    assert "embedding" in data["model_versions"]

@patch("app.storage.qdrant_client.to_uuid", lambda x: str(x))
@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.upsert", return_value=None)
@patch("app.storage.qdrant_client.client.search", return_value=[type("Result", (), {"id": "test-id-123", "score": 0.99, "payload": {"data": {"note": "Test note for version tracking"}, "metadata": {"embedding_model": "text-embedding-3-small", "model_version": "gpt-4o", "timestamp": "2025-07-14T00:00:00Z"}}, "type": "test", "priority": "low"})()])
def test_ingest_and_search_versions(mock_search, mock_upsert, mock_embedding):
    # Simulate ingestion
    payload = {
        "id": "test-id-123",
        "data": {"note": "Test note for version tracking"},
        "type": "test",
        "priority": "low"
    }
    from app.storage.qdrant_client import qdrant_upsert, qdrant_search
    qdrant_upsert(payload)
    # Search for the note
    results = qdrant_search("Test note for version tracking", top_k=1)
    assert results, "No results returned from search"
    result = results[0]
    assert "embedding_model" in result
    assert "model_version" in result
    assert result["embedding_model"] == "text-embedding-3-small"
    assert result["model_version"] == "gpt-4o"

@patch("app.storage.qdrant_client.client.scroll", return_value=([type("Point", (), {"id": "abc123", "payload": {"data": {"note": "Test note"}, "type": "test", "metadata": {"timestamp": "2025-07-14T00:00:00Z"}}})()], None, None))
def test_records_endpoint(mock_scroll):
    response = client.get("/records", headers=AUTH_HEADER)
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert data["records"][0]["id"] == "abc123"
    assert data["records"][0]["note"] == "Test note"
    assert data["records"][0]["type"] == "test"
    assert data["records"][0]["timestamp"] == "2025-07-14T00:00:00Z"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text and "# TYPE" in response.text
