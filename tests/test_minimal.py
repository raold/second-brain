from fastapi.testclient import TestClient
from app.main import app

def test_minimal():
    client = TestClient(app)
    response = client.get("/health")
    print(response.status_code, response.text)
    assert response.status_code == 200 