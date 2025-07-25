"""
Factory pattern implementations for service instantiation.

This module provides factory classes and dependency injection
containers following the Factory and Abstract Factory patterns.
"""

from .dependency_container import DependencyContainer, ServiceScope
from .repository_factory import RepositoryFactory
from .service_factory import AnalyticsServiceFactory, MemoryServiceFactory, ServiceFactory

__all__ = [
    'ServiceFactory',
    'MemoryServiceFactory',
    'AnalyticsServiceFactory',
    'RepositoryFactory',
    'DependencyContainer',
    'ServiceScope',
]
