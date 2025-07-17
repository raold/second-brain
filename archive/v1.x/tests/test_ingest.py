# /tests/test_ingest.py

<<<<<<< HEAD
import asyncio
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from fastapi import Request

import app.utils.openai_client as openai_client
from app.config import Config
from app.main import app
from app.models import Memory, PayloadType, Priority
import app.auth as app_auth
import app.router as app_router
import types
=======
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import app.router as app_router
from app.main import app

>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

def always_allow(request: Request):
    return None

# FastAPI dependency override for verify_token
app.dependency_overrides[app_router.verify_token] = always_allow

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test-token"}

@pytest.fixture(autouse=True)
def patch_all(monkeypatch):
    # Patch OpenAI and Qdrant at the location used in app.router
    monkeypatch.setattr("app.router.qdrant_upsert", MagicMock(return_value=None))
    monkeypatch.setattr("app.router.qdrant_search", MagicMock(return_value=[{
        "id": "test-id-123",
        "score": 0.99,
        "note": "Test note for version tracking",
        "timestamp": "2023-01-01T00:00:00Z",
        "embedding_model": "text-embedding-3-small",
        "model_version": "gpt-4o",
        "type": "test",
        "priority": "low",
        "meta": {"model_version": "gpt-4o", "embedding_model": "text-embedding-3-small"}
    }]))
    # Patch get_openai_embedding in app.storage.qdrant_client for ingest tests
    monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", MagicMock(return_value=[0.1, 0.2, 0.3]))
    # Patch detect_intent_via_llm as async function
    async def async_detect_intent_via_llm(*args, **kwargs):
        return "reminder"
    monkeypatch.setattr("app.utils.openai_client.detect_intent_via_llm", async_detect_intent_via_llm)
    # Patch OpenAI ChatCompletion and Embedding to prevent real API calls
    monkeypatch.setattr("openai.ChatCompletion", MagicMock())
    monkeypatch.setattr("openai.Embedding", MagicMock())
    # Patch auth dependency to always allow any token
    monkeypatch.setattr(app_router, "verify_token", lambda *a, **kw: None)

@patch("app.router.qdrant_upsert", return_value=True)
@patch("app.router.write_markdown", return_value=True)
@patch("app.router.store_memory_pg", return_value=None)
@patch("app.router.store_memory_pg_background", return_value=None)
def test_ingest(mock_store_bg, mock_store_pg, mock_write_markdown, mock_qdrant_upsert):
    payload = {
        "id": "test-id",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "meta": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"},
        "intent": "note",
        "target": "test-target"
    }
    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
    if response.status_code != 200:
        print("RESPONSE JSON:", response.json())
    assert response.status_code == 200
<<<<<<< HEAD
    assert response.json()["status"] == "ingested"
=======
    assert response.json()["status"] == "success"
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    mock_write_markdown.assert_called_once()
    mock_qdrant_upsert.assert_called_once()

@patch("app.router.qdrant_upsert")
@patch("app.router.write_markdown", return_value=True)
def test_ingest_qdrant_failure(mock_write_markdown, mock_qdrant_upsert):
    mock_qdrant_upsert.side_effect = Exception("Qdrant connection failed")
    payload = {
        "id": "test-id",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "meta": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"},
        "intent": "note",
        "target": "test-target"
    }
    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
<<<<<<< HEAD
    assert response.status_code == 500
    assert "Failed to ingest payload" in response.json()["detail"]
=======
    assert response.status_code == 200  # App handles errors gracefully
    assert response.json()["status"] == "success"
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

@patch("app.router.write_markdown")
def test_ingest_markdown_failure(mock_write_markdown):
    mock_write_markdown.side_effect = Exception("File system error")
    payload = {
        "id": "test-id",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "This is a test note for ingestion."},
        "meta": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"},
        "intent": "note",
        "target": "test-target"
    }
    response = client.post("/ingest", json=payload, headers=AUTH_HEADER)
<<<<<<< HEAD
    assert response.status_code == 500
    assert "Failed to ingest payload" in response.json()["detail"]
=======
    assert response.status_code == 200  # App handles errors gracefully
    assert response.json()["status"] == "success"
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

@patch("app.router.store_memory_pg", return_value=None)
@patch("app.router.store_memory_pg_background", return_value=None)
def test_ingest_intent_detection(mock_store_bg, mock_store_pg):
    payload = {
        "id": "test-intent-001",
        "type": "note",
        "context": "test",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "Remind me to call Alice."},
        "meta": {},
        "intent": "reminder",
        "target": "test-target"
    }
    headers = {"Authorization": "Bearer testtoken"}
    response = client.post("/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-intent-001"
