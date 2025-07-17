from fastapi.testclient import TestClient
<<<<<<< HEAD
from app.isolate_test import app
=======

from app.main import app

>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

def test_isolate():
    client = TestClient(app)
    response = client.get("/zzzzzzzzzz")
    print(response.status_code, response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["records"][0]["id"] == "abc123" 