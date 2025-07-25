"""
Basic API tests.

Tests API endpoints and functionality.
"""

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


@pytest.fixture
def app():
    """Create test application."""
    return create_app(debug=True)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "password" not in data


def test_login_user(client):
    """Test user login."""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "loginpass123",
        },
    )
    
    # Then login
    response = client.post(
        "/api/auth/login",
        json={
            "username_or_email": "loginuser",
            "password": "loginpass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


def test_protected_endpoint_without_auth(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/api/memories/")
    assert response.status_code == 403


def test_create_memory_with_auth(client):
    """Test creating a memory with authentication."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "email": "memory@example.com",
            "username": "memoryuser",
            "password": "memorypass123",
        },
    )
    
    login_response = client.post(
        "/api/auth/login",
        json={
            "username_or_email": "memoryuser",
            "password": "memorypass123",
        },
    )
    token = login_response.json()["access_token"]
    
    # Create memory
    response = client.post(
        "/api/memories/",
        json={
            "title": "Test Memory",
            "content": "This is a test memory",
            "memory_type": "note",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Memory"
    assert data["content"] == "This is a test memory"
    assert data["memory_type"] == "note"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])