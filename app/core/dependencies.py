"""
Centralized Dependency Injection Container
Implements the Service Factory pattern for clean, testable dependency management
"""

from typing import Any, Dict, Optional, TypeVar, Callable
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DependencyContainer:
    """Centralized container for managing service dependencies"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        
    def register_factory(self, service_name: str, factory: Callable) -> None:
        """Register a factory function for a service"""
        self._factories[service_name] = factory
        logger.debug(f"Registered factory for {service_name}")
    
    def register_singleton(self, service_name: str, instance: Any) -> None:
        """Register a singleton instance"""
        self._singletons[service_name] = instance
        logger.debug(f"Registered singleton for {service_name}")
    
    def get_service(self, service_name: str) -> Any:
        """Get a service instance"""
        # Check if it's a registered singleton
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Check if it's in the services cache
        if service_name in self._services:
            return self._services[service_name]
        
        # Create from factory
        if service_name in self._factories:
            service = self._factories[service_name]()
            self._services[service_name] = service
            logger.debug(f"Created service instance for {service_name}")
            return service
        
        raise ValueError(f"No factory or instance registered for service: {service_name}")
    
    def clear_cache(self) -> None:
        """Clear all cached service instances (including singletons for testing)"""
        self._services.clear()
        # Also clear singletons for testing purposes
        self._singletons.clear()
        logger.debug("Cleared service cache")
    
    def reset(self) -> None:
        """Reset the entire container"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Reset dependency container")


# Global container instance (initialize at end of file)
_container = None


def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    return _container


# Service factory functions following the established pattern
@lru_cache(maxsize=1)
def get_database():
    """Get database instance (cached)"""
    from app.database import get_database as _get_database
    import asyncio
    
    # Handle async database initialization in sync context
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get_database())
    except RuntimeError:
        # No event loop, create one
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_get_database())


def get_dashboard_service():
    """Get dashboard service instance"""
    try:
        return _container.get_service("dashboard_service")
    except ValueError:
        from app.services.service_factory import DashboardService
        service = DashboardService()
        _container.register_singleton("dashboard_service", service)
        return service


def get_git_service():
    """Get git service instance"""
    try:
        return _container.get_service("git_service")
    except ValueError:
        from app.services.service_factory import GitService
        service = GitService()
        _container.register_singleton("git_service", service)
        return service


def get_health_service():
    """Get health service instance"""
    try:
        return _container.get_service("health_service")
    except ValueError:
        from app.services.service_factory import HealthService
        service = HealthService()
        _container.register_singleton("health_service", service)
        return service


def get_memory_service():
    """Get memory service instance"""
    try:
        return _container.get_service("memory_service")
    except ValueError:
        from app.services.service_factory import MemoryService
        service = MemoryService()
        _container.register_singleton("memory_service", service)
        return service


def get_session_service():
    """Get session service instance"""
    try:
        return _container.get_service("session_service")
    except ValueError:
        from app.services.service_factory import SessionService
        service = SessionService()
        _container.register_singleton("session_service", service)
        return service


def get_importance_engine():
    """Get importance engine instance"""
    try:
        return _container.get_service("importance_engine")
    except ValueError:
        from app.services.importance_engine import get_importance_engine as _get_importance_engine
        db = get_database()
        engine = _get_importance_engine(db)
        _container.register_singleton("importance_engine", engine)
        return engine


def get_metrics_collector():
    """Get metrics collector instance"""
    try:
        return _container.get_service("metrics_collector")
    except ValueError:
        from app.services.monitoring import get_metrics_collector as _get_metrics_collector
        collector = _get_metrics_collector()
        _container.register_singleton("metrics_collector", collector)
        return collector


# FastAPI dependency functions
def get_dashboard_service_dep():
    """FastAPI dependency for dashboard service"""
    return get_dashboard_service()


def get_git_service_dep():
    """FastAPI dependency for git service"""
    return get_git_service()


def get_health_service_dep():
    """FastAPI dependency for health service"""
    return get_health_service()


def get_memory_service_dep():
    """FastAPI dependency for memory service"""
    return get_memory_service()


def get_session_service_dep():
    """FastAPI dependency for session service"""
    return get_session_service()


def get_importance_engine_dep():
    """FastAPI dependency for importance engine"""
    return get_importance_engine()


def get_metrics_collector_dep():
    """FastAPI dependency for metrics collector"""
    return get_metrics_collector()


# Initialize container with default services
def initialize_dependencies():
    """Initialize the dependency container with default services"""
    logger.info("Initializing dependency injection container")
    
    # The get_* functions handle their own registration, so no need to pre-register
    # This avoids circular dependency issues
    
    logger.info("Dependency injection container initialized")


# Utility functions for testing
def override_service(service_name: str, mock_instance: Any):
    """Override a service with a mock instance (for testing)"""
    _container.register_singleton(service_name, mock_instance)
    logger.debug(f"Overrode service {service_name} with mock instance")


def clear_service_cache():
    """Clear service cache (for testing)"""
    _container.clear_cache()
    # Re-initialize to register factories again
    initialize_dependencies()


def reset_dependencies():
    """Reset all dependencies (for testing)"""
    _container.reset()
    initialize_dependencies()


# Initialize the global container at module import
if _container is None:
    _container = DependencyContainer()
    initialize_dependencies()