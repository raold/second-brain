from fastapi.testclient import TestClient
<<<<<<< HEAD
from app.main import app

=======

from app.main import app


>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
def test_minimal():
    client = TestClient(app)
    response = client.get("/health")
    print(response.status_code, response.text)
    assert response.status_code == 200 