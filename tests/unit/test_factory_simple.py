"""
Simple tests for application factory without external dependencies
"""

import pytest
from app.factory import create_app, create_test_app, AppState


def test_create_development_app():
    """Test creating development app"""
    app = create_app("development")
    
    assert app.title == "Second Brain API [Development]"
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.config_name == "development"
    print("✅ Development app created")


def test_create_production_app():
    """Test creating production app"""
    app = create_app("production")
    
    assert app.title == "Second Brain API [Production]"
    assert app.docs_url is None  # No docs in production
    assert app.redoc_url is None
    assert app.config_name == "production"
    print("✅ Production app created")


def test_create_testing_app():
    """Test creating testing app"""
    app = create_test_app()
    
    assert app.title == "Second Brain API [Testing]"
    assert app.config_name == "testing"
    print("✅ Testing app created")


def test_invalid_config_raises_error():
    """Test that invalid config name raises error"""
    with pytest.raises(ValueError, match="Invalid config"):
        create_app("invalid_config")
    print("✅ Invalid config handled")


def test_app_state_initialization():
    """Test AppState is properly initialized"""
    state = AppState()
    
    assert state.ready is False
    assert state.memory_service is None
    assert state.qdrant_client is None
    assert state.persistence_task is None
    assert state.memory_count == 0
    print("✅ AppState initialized")


if __name__ == "__main__":
    test_create_development_app()
    test_create_production_app()
    test_create_testing_app()
    test_invalid_config_raises_error()
    test_app_state_initialization()
    print("\n🎉 All factory tests passed!")