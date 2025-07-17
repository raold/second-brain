# /tests/test_health.py

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

import app.router as app_router
from app.main import app
from app.config import Config

AUTH_HEADER = {"Authorization": "Bearer test-token"}
client = TestClient(app)

def always_allow(request: Request):
    return None

@patch("app.storage.qdrant_client.qdrant_upsert")
@patch("app.storage.qdrant_client.qdrant_search")
def test_health_check(mock_qdrant_search, mock_qdrant_upsert):
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    mock_qdrant_search.return_value = []
    mock_qdrant_upsert.return_value = None

    response = client.get("/health", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ws_generate_stream():
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    token = "test-token"  # Replace with a valid token if needed
    
    with client.websocket_connect(f"/ws/generate?token={token}") as ws:
        ws.send_json({"prompt": "Hello, world!"})
        received = []
        while True:
            data = ws.receive_json()
            # Accept both 'text' and 'chunk' keys for compatibility
            if 'text' in data:
                received.append(data['text'])
                if data.get('done', False):
                    break
            elif 'chunk' in data:
                received.append(data['chunk'])
                if data.get('done', False):
                    break
        assert len(received) > 0

def test_models_endpoint():
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    response = client.get("/models", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert "model_versions" in response.json()

@patch("app.storage.qdrant_client.qdrant_upsert")
@patch("app.storage.qdrant_client.qdrant_search")
def test_ingest_and_search_versions(mock_qdrant_search, mock_qdrant_upsert):
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    mock_qdrant_upsert.return_value = None
    mock_qdrant_search.return_value = [{
        "id": "test-id-123",
<<<<<<< HEAD
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
    print(f"\nMock object: {mock_scroll}")
    print(f"Mock called: {mock_scroll.called}")
    
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
    print(f"\nRESPONSE DATA: {data}")
    assert "records" in data
    assert data["records"][0]["id"] == "abc123"
    assert data["records"][0]["note"] == "Test note"
    assert data["records"][0]["type"] == "test"
    assert data["records"][0]["timestamp"] == "2025-07-14T00:00:00Z"
=======
        "score": 0.99,
        "note": "Test note for version tracking",
        "timestamp": "2023-01-01T00:00:00Z",
        "embedding_model": "text-embedding-3-small",
        "model_version": "gpt-4o",
        "type": "note",
        "priority": "low",
        "meta": {"version_history": []}
    }]
    
    # Test that version history is included in search results
    response = client.get("/search?q=test", headers=AUTH_HEADER)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) > 0
    assert "meta" in results[0]
>>>>>>> dadecf57943bc8b3cc6163208145afb933568392

def test_records_endpoint():
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    response = client.get("/records", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert "records" in response.json()
    assert "total" in response.json()

def test_metrics_endpoint():
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    response = client.get("/metrics")
    assert response.status_code == 200
    # Prometheus metrics return text/plain
    assert response.headers["content-type"].startswith("text/plain")

def test_plugin_registration():
    app.dependency_overrides[app_router.verify_token] = always_allow
    Config.API_TOKENS = ['test-token']
    # Test that plugins are registered
    from app.plugins import plugin_registry
    assert isinstance(plugin_registry, dict)
    # Should have at least reminder plugin
    assert len(plugin_registry) >= 1
