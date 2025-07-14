# app/tests/test_search.py

from fastapi.testclient import TestClient
from app.main import app
from app.config import Config

client = TestClient(app)
AUTH_HEADER = {"Authorization": Config.API_TOKENS[0]}

def test_search_empty():
    response = client.get("/search?q=nonexistent", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == []
