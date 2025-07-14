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

@patch("app.qdrant_client_wrapper.qdrant_client.upsert")
@patch("app.utils.openai_client.embed_text", return_value=[0.0] * Config.QDRANT_VECTOR_SIZE)
def test_ingest(mock_embed_text, mock_qdrant_upsert):
    payload = {
        "id": "test-id",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {
            "note": "This is a test note for ingestion."
        },
        "metadata": {
            "source": "unit-test",
            "timestamp": "2025-07-13T00:00:00Z"
        }
    }

    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 200
    mock_embed_text.assert_called_once()
    mock_qdrant_upsert.assert_called_once()