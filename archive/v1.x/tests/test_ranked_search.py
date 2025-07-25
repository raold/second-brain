from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test-token"}

<<<<<<< HEAD
@pytest.fixture(autouse=True)
def inject_test_token(monkeypatch):
    from app.config import Config
    monkeypatch.setattr(Config, 'API_TOKENS', ['test-token'])

import types

@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.search")
def test_ranked_search_vector_only(mock_search, mock_embed):
    mock_search.return_value = [
        type("Result", (), {
            "id": "id1",
            "score": 0.9,
            "payload": {
                "data": {"note": "A"},
                "metadata": {"model_version": "v1", "embedding_model": "em1", "timestamp": "2025-07-14T00:00:00Z"},
                "type": "test"
            }
        })()
    ]
=======

@patch("app.router.qdrant_search")
def test_ranked_search_vector_only(mock_search):
    mock_search.return_value = [{
        "id": "id1",
        "score": 0.9,
        "note": "A",
        "model_version": "v1",
        "embedding_model": "em1",
        "timestamp": "2025-07-14T00:00:00Z",
        "type": "test",
        "priority": "normal",
        "source": ""
    }]
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    resp = client.get("/ranked-search?q=test", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["vector_score"] == 0.9
    assert data["results"][0]["metadata_score"] == 0.0
    assert data["results"][0]["final_score"] == pytest.approx(0.72)
    assert "vector only" in data["results"][0]["explanation"]

<<<<<<< HEAD
@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.search")
@patch("app.storage.qdrant_client._process_qdrant_results", side_effect=lambda x: x)
def test_ranked_search_metadata_match(mock_process, mock_search, mock_embed):
    mock_search.return_value = [
        {
            "id": "id2",
            "score": 0.5,
            "note": "B",
            "timestamp": "2025-07-14T00:00:00Z",
            "type": "special",
            "embedding_model": "em2",
            "model_version": "v2",
            "payload": {
                "data": {"note": "B"},
                "metadata": {"model_version": "v2", "embedding_model": "em2", "timestamp": "2025-07-14T00:00:00Z"},
                "type": "special"
            }
        }
    ]
=======
@patch("app.router.qdrant_search")
def test_ranked_search_metadata_match(mock_search):
    mock_search.return_value = [{
        "id": "id2",
        "score": 0.5,
        "note": "B",
        "timestamp": "2025-07-14T00:00:00Z",
        "type": "special",
        "embedding_model": "em2",
        "model_version": "v2",
        "priority": "normal",
        "source": ""
    }]
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    url = "/ranked-search?q=test&model_version=v2&embedding_model=em2&type=special"
    resp = client.get(url, headers=AUTH_HEADER)
    assert resp.status_code == 200
    r = resp.json()["results"][0]
    assert r["metadata_score"] > 0.0
    assert "model_version match" in r["explanation"]
    assert "embedding_model match" in r["explanation"]
    assert "type match" in r["explanation"]
    assert r["final_score"] > r["vector_score"]

<<<<<<< HEAD
@patch("app.storage.qdrant_client.get_openai_embedding", return_value=[0.1] * 1536)
@patch("app.storage.qdrant_client.client.search")
@patch("app.storage.qdrant_client._process_qdrant_results", side_effect=lambda x: x)
def test_ranked_search_timestamp_range(mock_process, mock_search, mock_embed):
    mock_search.return_value = [
        {
            "id": "id3",
            "score": 0.7,
            "note": "C",
            "timestamp": "2025-07-14T12:00:00Z",
            "type": "test",
            "embedding_model": "em3",
            "model_version": "v3",
            "payload": {
                "data": {"note": "C"},
                "metadata": {"model_version": "v3", "embedding_model": "em3", "timestamp": "2025-07-14T12:00:00Z"},
                "type": "test"
            }
        }
    ]
=======
@patch("app.router.qdrant_search")
def test_ranked_search_timestamp_range(mock_search):
    mock_search.return_value = [{
        "id": "id3",
        "score": 0.7,
        "note": "C",
        "timestamp": "2025-07-14T12:00:00Z",
        "type": "test",
        "embedding_model": "em3",
        "model_version": "v3",
        "priority": "normal",
        "source": ""
    }]
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    url = "/ranked-search?q=test&timestamp_from=2025-07-14T00:00:00Z&timestamp_to=2025-07-15T00:00:00Z"
    resp = client.get(url, headers=AUTH_HEADER)
    assert resp.status_code == 200
    r = resp.json()["results"][0]
    assert r["metadata_score"] > 0.0
    assert "timestamp in range" in r["explanation"]
    assert r["final_score"] > 0.0 