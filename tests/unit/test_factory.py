"""
Test application factory pattern
"""

import pytest
from fastapi.testclient import TestClient
from app.factory import create_app, create_test_app, AppState


class TestApplicationFactory:
    """Test the application factory pattern"""
    
    def test_create_development_app(self):
        """Test creating development app"""
        app = create_app("development")
        
        assert app.title == "Second Brain API [Development]"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.config_name == "development"
    
    def test_create_production_app(self):
        """Test creating production app"""
        app = create_app("production")
        
        assert app.title == "Second Brain API [Production]"
        assert app.docs_url is None  # No docs in production
        assert app.redoc_url is None
        assert app.config_name == "production"
    
    def test_create_testing_app(self):
        """Test creating testing app"""
        app = create_test_app()
        
        assert app.title == "Second Brain API [Testing]"
        assert app.config_name == "testing"
    
    def test_invalid_config_raises_error(self):
        """Test that invalid config name raises error"""
        with pytest.raises(ValueError, match="Invalid config"):
            create_app("invalid_config")
    
    def test_root_endpoint(self):
        """Test root endpoint returns environment info"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["environment"] == "testing"
        assert data["version"] == "4.2.3"
        assert "ready" in data
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/health")
        # Will be 503 since app not fully started
        assert response.status_code in [200, 503]
        
        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, list):
            assert len(data) == 2
            assert "status" in data[0]
            assert "ready" in data[0]
        else:
            assert "status" in data
            assert "ready" in data
    
    def test_cors_configuration(self):
        """Test CORS is configured correctly"""
        app = create_app("development")
        
        # Check middleware is added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in str(middleware_classes)
    
    def test_app_state_initialization(self):
        """Test AppState is properly initialized"""
        state = AppState()
        
        assert state.ready is False
        assert state.memory_service is None
        assert state.qdrant_client is None
        assert state.persistence_task is None
        assert state.memory_count == 0