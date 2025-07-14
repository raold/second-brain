# app/tests/test_ingest.py

from fastapi.testclient import TestClient
from app.main import app
from app.config import Config

client = TestClient(app)
AUTH_HEADER = {"Authorization": Config.API_TOKENS[0]}

def test_ingest():
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
