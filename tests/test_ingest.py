# /tests/test_ingest.py

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import app
from app.models import PayloadType, Priority, Memory
import app.utils.openai_client as openai_client
from sqlalchemy import select
import asyncio

client = TestClient(app)

def mock_detect_intent_via_llm(text, client=None, model=None):
    if 'remind' in text:
        return 'reminder'
    if '?' in text:
        return 'question'
    return 'note'

@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    monkeypatch.setattr(openai_client, 'detect_intent_via_llm', lambda text, client=None, model=None: mock_detect_intent_via_llm(text))

@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    monkeypatch.setattr(Config, 'API_TOKENS', {'test-token'})

AUTH_HEADER = {"Authorization": "Bearer test-token"}

@pytest.fixture(autouse=True)
def mock_openai_embedding():
    with patch("app.utils.openai_client.get_openai_embedding", return_value=[0.1] * 1536):
        yield

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

def test_ingest_intent_detection():
    payload = {
        "id": "test-intent-001",
        "type": "note",
        "context": "test",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "Remind me to call Alice."},
        "metadata": {}
    }
    headers = {"Authorization": "Bearer testtoken"}
    response = client.post("/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "reminder"

@pytest.fixture
def memory_in_db(client, patch_openai):
    # Insert a memory for testing
    payload = {
        "id": "test-feedback-001",
        "type": "note",
        "context": "test",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "Remember to test delete."},
        "metadata": {}
    }
    headers = {"Authorization": "Bearer testtoken"}
    client.post("/ingest", json=payload, headers=headers)
    yield payload["id"]


def test_delete_memory(client, memory_in_db, monkeypatch):
    # Mock Qdrant delete
    monkeypatch.setattr("app.storage.qdrant_client.client.delete", lambda *a, **kw: None)
    resp = client.delete(f"/memories/{memory_in_db}", headers={"Authorization": "Bearer testtoken"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    # Check not in Postgres
    from app.storage.postgres import AsyncSessionLocal
    async def check():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Memory).where(Memory.id == memory_in_db))
            assert result.scalar() is None
    asyncio.run(check())


def test_update_memory(client, memory_in_db, monkeypatch):
    # Mock Qdrant upsert
    monkeypatch.setattr("app.storage.qdrant_client.qdrant_upsert", lambda *a, **kw: None)
    new_note = "Updated note for feedback test."
    new_intent = "todo"
    resp = client.put(f"/memories/{memory_in_db}?note={new_note}&intent={new_intent}", headers={"Authorization": "Bearer testtoken"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "updated"
    # Check updated in Postgres
    from app.storage.postgres import AsyncSessionLocal
    async def check():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Memory).where(Memory.id == memory_in_db))
            mem = result.scalar()
            assert mem is not None
            assert mem.note == new_note
            assert mem.intent == new_intent
    asyncio.run(check())
