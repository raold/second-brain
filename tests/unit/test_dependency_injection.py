"""
Test the standardized dependency injection system
"""

import pytest
from unittest.mock import MagicMock

from app.core.dependencies import (
    get_dashboard_service,
    get_git_service,
    get_health_service,
    get_memory_service,
    get_session_service,
    get_container,
    override_service,
    clear_service_cache,
    reset_dependencies
)


class TestDependencyInjection:
    """Test dependency injection container functionality"""
    
    def setup_method(self):
        """Reset dependencies before each test"""
        reset_dependencies()
    
    def test_get_health_service(self):
        """Test health service creation"""
        service1 = get_health_service()
        service2 = get_health_service()
        
        # Should return the same instance (singleton)
        assert service1 is service2
        assert service1.__class__.__name__ == "HealthService"
    
    def test_get_memory_service(self):
        """Test memory service creation"""
        service1 = get_memory_service()
        service2 = get_memory_service()
        
        # Should return the same instance (singleton)
        assert service1 is service2
        assert service1.__class__.__name__ == "MemoryService"
    
    def test_get_session_service(self):
        """Test session service creation"""
        service1 = get_session_service()
        service2 = get_session_service()
        
        # Should return the same instance (singleton)
        assert service1 is service2
        assert service1.__class__.__name__ == "SessionService"
    
    def test_get_git_service(self):
        """Test git service creation"""
        service1 = get_git_service()
        service2 = get_git_service()
        
        # Should return the same instance (singleton)
        assert service1 is service2
        assert service1.__class__.__name__ == "GitService"
    
    def test_get_dashboard_service(self):
        """Test dashboard service creation"""
        service1 = get_dashboard_service()
        service2 = get_dashboard_service()
        
        # Should return the same instance (singleton)
        assert service1 is service2
        assert service1.__class__.__name__ == "DashboardService"
    
    def test_service_override(self):
        """Test service override functionality for testing"""
        # Create a mock service
        mock_service = MagicMock()
        mock_service.__class__.__name__ = "MockHealthService"
        
        # Override the health service
        override_service("health_service", mock_service)
        
        # Should return the mock service
        service = get_health_service()
        assert service is mock_service
    
    def test_clear_service_cache(self):
        """Test clearing service cache"""
        # Get a service to populate cache
        service1 = get_health_service()
        
        # Clear cache
        clear_service_cache()
        
        # Get service again - should be a new instance
        service2 = get_health_service()
        assert service1 is not service2
    
    def test_container_functionality(self):
        """Test the underlying container functionality"""
        container = get_container()
        
        # Test factory registration
        mock_factory = lambda: MagicMock()
        container.register_factory("test_service", mock_factory)
        
        # Test service retrieval
        service1 = container.get_service("test_service")
        service2 = container.get_service("test_service")
        
        # Should return same instance
        assert service1 is service2
        
        # Test singleton registration
        mock_singleton = MagicMock()
        container.register_singleton("singleton_service", mock_singleton)
        
        service3 = container.get_service("singleton_service")
        assert service3 is mock_singleton
    
    def test_nonexistent_service(self):
        """Test error handling for non-existent services"""
        container = get_container()
        
        with pytest.raises(ValueError, match="No factory or instance registered"):
            container.get_service("nonexistent_service")


@pytest.mark.asyncio
class TestServiceFunctionality:
    """Test that services work correctly"""
    
    async def test_health_service_basic_functionality(self):
        """Test health service provides expected methods"""
        service = get_health_service()
        
        # Should have expected methods
        assert hasattr(service, 'get_health_status')
        assert hasattr(service, 'get_system_status')
        assert hasattr(service, 'run_diagnostics')
        assert hasattr(service, 'get_performance_metrics')
        
        # Methods should be callable
        assert callable(service.get_health_status)
        assert callable(service.get_system_status)
        assert callable(service.run_diagnostics)
        assert callable(service.get_performance_metrics)
    
    async def test_memory_service_basic_functionality(self):
        """Test memory service provides expected methods"""
        service = get_memory_service()
        
        # Should have expected methods
        assert hasattr(service, 'get_memories')
        assert hasattr(service, 'create_memory')
        assert hasattr(service, 'search_memories')
        assert hasattr(service, 'get_memory')
        assert hasattr(service, 'delete_memory')
        
        # Methods should be callable
        assert callable(service.get_memories)
        assert callable(service.create_memory)
        assert callable(service.search_memories)
        assert callable(service.get_memory)
        assert callable(service.delete_memory)
    
    async def test_session_service_basic_functionality(self):
        """Test session service provides expected methods"""
        service = get_session_service()
        
        # Should have expected methods
        assert hasattr(service, 'create_session')
        assert hasattr(service, 'get_session')
        assert hasattr(service, 'get_session_status')
        assert hasattr(service, 'ingest_idea')
        assert hasattr(service, 'pause_session')
        assert hasattr(service, 'resume_session')
        
        # Methods should be callable
        assert callable(service.create_session)
        assert callable(service.get_session)
        assert callable(service.get_session_status)
        assert callable(service.ingest_idea)
        assert callable(service.pause_session)
        assert callable(service.resume_session)