# /tests/test_health.py

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

import app.router as app_router
from app.main import app

AUTH_HEADER = {"Authorization": "Bearer test-token"}
client = TestClient(app)

def always_allow(request: Request):
    return None

@patch("app.storage.qdrant_client.qdrant_upsert")
@patch("app.storage.qdrant_client.qdrant_search")
def test_health_check(mock_qdrant_search, mock_qdrant_upsert):
    app.dependency_overrides[app_router.verify_token] = always_allow
    mock_qdrant_search.return_value = []
    mock_qdrant_upsert.return_value = None

    response = client.get("/health", headers=AUTH_HEADER)
    assert response.status_code == 200
    
    # Check the new detailed health response format
    health_data = response.json()
    assert health_data["status"] == "ok"
    assert "timestamp" in health_data
    assert "version" in health_data
    assert "services" in health_data
    
    # Check that services are included
    services = health_data["services"]
    assert "postgresql" in services
    assert "qdrant" in services

def test_ws_generate_stream():
    app.dependency_overrides[app_router.verify_token] = always_allow
    token = "test-token"  # Replace with a valid token if needed
    prompt = "Hello world this is a test"
    with client.websocket_connect(f"/ws/generate?token={token}") as ws:
        ws.send_json({"prompt": prompt, "json": True})
        received = []
        for _ in range(len(prompt.split())):
            msg = ws.receive_json()
            # Accept both 'text' and 'chunk' keys for compatibility
            if "text" in msg:
                received.append(msg["text"].strip())
            elif "chunk" in msg:
                received.append(msg["chunk"].strip())
            else:
                assert False, f"Unexpected message format: {msg}"
        assert " ".join(received).strip() == prompt

def test_models_endpoint():
    app.dependency_overrides[app_router.verify_token] = always_allow
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "model_versions" in data
    assert "llm" in data["model_versions"]
    assert "embedding" in data["model_versions"]

@patch("app.storage.qdrant_client.to_uuid", lambda x: str(x))
@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.upsert", return_value=None)
@patch("app.storage.qdrant_client.client.search", return_value=[SimpleNamespace(
    id="test-id-123",
    score=0.99,
    embedding_model="text-embedding-3-small",
    model_version="gpt-4o",
    note="Test note for version tracking",
    timestamp="2025-07-14T00:00:00Z",
    type="test",
    priority="low",
    payload={
        "data": {"note": "Test note for version tracking"},
        "type": "test",
        "priority": "low",
        "meta": {"model_version": "gpt-4o", "embedding_model": "text-embedding-3-small"}
    }
)])
def test_ingest_and_search_versions(mock_search, mock_upsert, mock_embedding):
    app.dependency_overrides[app_router.verify_token] = always_allow
    # Simulate ingestion
    payload = {
        "id": "test-id-123",
        "data": {"note": "Test note for version tracking"},
        "type": "test",
        "priority": "low"
    }
    from app.storage.qdrant_client import qdrant_search, qdrant_upsert
    qdrant_upsert(payload)
    # Search for the note
    results = qdrant_search("Test note for version tracking", top_k=1)
    assert results, "No results returned from search"
    result = results[0]
    assert result["embedding_model"] == "text-embedding-3-small"
    assert result["model_version"] == "gpt-4o"
    assert result["id"] == "test-id-123"
    assert result["note"] == "Test note for version tracking"

@patch("app.storage.qdrant_client.client.scroll", return_value=([
    SimpleNamespace(
        id="abc123",
        payload={
            "data": {"note": "Test note"},
            "type": "test",
            "metadata": {"timestamp": "2025-07-14T00:00:00Z"}
        }
    )
], None, None))
def test_records_endpoint(mock_scroll):
    app.dependency_overrides[app_router.verify_token] = always_allow
    # Print all registered routes and their endpoint functions
    print("\nRegistered routes:")
    for route in app.routes:
        path = getattr(route, 'path', None)
        methods = getattr(route, 'methods', None)
        endpoint = getattr(route, 'endpoint', None)
        if path and methods:
            print(f"{path} [{','.join(methods)}] -> {endpoint} ({getattr(endpoint, '__module__', None)})")
        else:
            print(f"{route}")
    response = client.get("/zzzzzzzzzz", headers=AUTH_HEADER)
    if response.status_code != 200:
        print(f"\nRESPONSE BODY FOR 422: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert data["records"][0]["id"] == "abc123"
    assert data["records"][0]["note"] == "Test note"
    assert data["records"][0]["type"] == "test"
    assert data["records"][0]["timestamp"] == "2025-07-14T00:00:00Z"


def test_metrics_endpoint():
    app.dependency_overrides[app_router.verify_token] = always_allow
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text and "# TYPE" in response.text

def test_plugin_registration():
    from app.plugins import get_registered_plugins, plugin_registry
    plugins = get_registered_plugins()
    assert plugins, "No plugins registered"
    for name in plugins:
        plugin = plugin_registry[name]
        assert hasattr(plugin, 'on_memory'), f"Plugin {name} missing on_memory method"
