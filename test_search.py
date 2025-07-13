# app/tests/test_search.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_empty():
    headers = {"Authorization": "Bearer test-token"}
    response = client.get("/search?q=nonexistent", headers=headers)
    assert response.status_code == 200
    assert "results" in response.json()

