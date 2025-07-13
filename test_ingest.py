# app/tests/test_ingest.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
    headers = {"Authorization": "Bearer test-token"}
    response = client.post("/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ingested"

