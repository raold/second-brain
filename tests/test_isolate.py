from fastapi.testclient import TestClient

from app.isolate_test import app


def test_isolate():
    client = TestClient(app)
    response = client.get("/zzzzzzzzzz")
    print(response.status_code, response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["records"][0]["id"] == "abc123" 