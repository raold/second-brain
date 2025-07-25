"""
Dependency injection container implementation.

Provides a modern dependency injection system following the
Inversion of Control pattern with proper lifecycle management.
"""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceScope(Enum):
    """Service lifecycle scopes."""
    SINGLETON = "singleton"      # One instance for entire application
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"           # One instance per scope (e.g., per request)


@dataclass
class ServiceRegistration:
    """Service registration information."""
    interface: type
    implementation: Optional[type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: ServiceScope = ServiceScope.TRANSIENT
    dependencies: list[type] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ServiceProvider(ABC):
    """Abstract service provider interface."""

    @abstractmethod
    async def get_service(self, service_type: type[T]) -> T:
        """Get service instance."""
        pass

    @abstractmethod
    def is_registered(self, service_type: type) -> bool:
        """Check if service is registered."""
        pass


class DependencyContainer(ServiceProvider):
    """
    Dependency injection container with automatic dependency resolution.

    Features:
    - Constructor injection with automatic dependency resolution
    - Multiple service lifetimes (Singleton, Transient, Scoped)
    - Async factory functions support
    - Circular dependency detection
    - Service validation and health checks
    """

    def __init__(self):
        self._registrations: dict[type, ServiceRegistration] = {}
        self._instances: dict[type, Any] = {}
        self._scoped_instances: dict[str, dict[type, Any]] = {}
        self._building_stack: list[type] = []  # For circular dependency detection
        self._lock = asyncio.Lock()

    def register_singleton(
        self,
        interface: type[T],
        implementation: Optional[type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None
    ) -> 'DependencyContainer':
        """
        Register a singleton service.

        Args:
            interface: Service interface type
            implementation: Concrete implementation type
            factory: Factory function to create instance
            instance: Pre-created instance

        Returns:
            Self for method chaining
        """
        return self._register(interface, implementation, factory, instance, ServiceScope.SINGLETON)

    def register_transient(
        self,
        interface: type[T],
        implementation: Optional[type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'DependencyContainer':
        """Register a transient service (new instance each time)."""
        return self._register(interface, implementation, factory, None, ServiceScope.TRANSIENT)

    def register_scoped(
        self,
        interface: type[T],
        implementation: Optional[type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'DependencyContainer':
        """Register a scoped service (one instance per scope)."""
        return self._register(interface, implementation, factory, None, ServiceScope.SCOPED)

    def _register(
        self,
        interface: type[T],
        implementation: Optional[type[T]],
        factory: Optional[Callable],
        instance: Optional[T],
        scope: ServiceScope
    ) -> 'DependencyContainer':
        """Internal registration method."""
        # Validate registration
        if sum(x is not None for x in [implementation, factory, instance]) != 1:
            raise ValueError("Exactly one of implementation, factory, or instance must be provided")

        # Auto-detect dependencies for implementation classes
        dependencies = []
        if implementation:
            dependencies = self._get_constructor_dependencies(implementation)

        registration = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            factory=factory,
            instance=instance,
            scope=scope,
            dependencies=dependencies
        )

        self._registrations[interface] = registration

        # Store singleton instances immediately if provided
        if scope == ServiceScope.SINGLETON and instance is not None:
            self._instances[interface] = instance

        logger.debug(f"Registered {interface.__name__} as {scope.value}")
        return self

    def _get_constructor_dependencies(self, cls: type) -> list[type]:
        """Extract constructor dependencies from type hints."""
        try:
            signature = inspect.signature(cls.__init__)
            dependencies = []

            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                if param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)

            return dependencies
        except Exception as e:
            logger.warning(f"Could not extract dependencies for {cls.__name__}: {e}")
            return []

    async def get_service(self, service_type: type[T]) -> T:
        """
        Get service instance with dependency resolution.

        Args:
            service_type: Type of service to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered or circular dependency detected
        """
        async with self._lock:
            return await self._resolve_service(service_type)

    async def _resolve_service(self, service_type: type[T], scope_id: Optional[str] = None) -> T:
        """Internal service resolution with scope support."""
        if not self.is_registered(service_type):
            raise ValueError(f"Service {service_type.__name__} is not registered")

        # Check for circular dependencies
        if service_type in self._building_stack:
            cycle = " -> ".join(cls.__name__ for cls in self._building_stack) + f" -> {service_type.__name__}"
            raise ValueError(f"Circular dependency detected: {cycle}")

        registration = self._registrations[service_type]

        # Handle different scopes
        if registration.scope == ServiceScope.SINGLETON:
            return await self._get_singleton(service_type, registration)
        elif registration.scope == ServiceScope.SCOPED:
            return await self._get_scoped(service_type, registration, scope_id or "default")
        else:  # TRANSIENT
            return await self._create_instance(service_type, registration)

    async def _get_singleton(self, service_type: type[T], registration: ServiceRegistration) -> T:
        """Get or create singleton instance."""
        if service_type in self._instances:
            return self._instances[service_type]

        instance = await self._create_instance(service_type, registration)
        self._instances[service_type] = instance
        return instance

    async def _get_scoped(self, service_type: type[T], registration: ServiceRegistration, scope_id: str) -> T:
        """Get or create scoped instance."""
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}

        scope_cache = self._scoped_instances[scope_id]

        if service_type in scope_cache:
            return scope_cache[service_type]

        instance = await self._create_instance(service_type, registration)
        scope_cache[service_type] = instance
        return instance

    async def _create_instance(self, service_type: type[T], registration: ServiceRegistration) -> T:
        """Create new service instance."""
        # Track building stack for circular dependency detection
        self._building_stack.append(service_type)

        try:
            # Use pre-created instance
            if registration.instance is not None:
                return registration.instance

            # Use factory function
            if registration.factory is not None:
                if asyncio.iscoroutinefunction(registration.factory):
                    return await registration.factory()
                else:
                    return registration.factory()

            # Use implementation class with dependency injection
            if registration.implementation is not None:
                return await self._create_with_dependencies(registration.implementation, registration.dependencies)

            raise ValueError(f"No way to create instance for {service_type.__name__}")

        finally:
            self._building_stack.remove(service_type)

    async def _create_with_dependencies(self, implementation: type[T], dependencies: list[type]) -> T:
        """Create instance with injected dependencies."""
        if not dependencies:
            return implementation()

        # Resolve all dependencies
        resolved_deps = []
        for dep_type in dependencies:
            dep_instance = await self._resolve_service(dep_type)
            resolved_deps.append(dep_instance)

        # Create instance with dependencies
        return implementation(*resolved_deps)

    def is_registered(self, service_type: type) -> bool:
        """Check if service type is registered."""
        return service_type in self._registrations

    def get_registrations(self) -> dict[type, ServiceRegistration]:
        """Get all service registrations (for debugging)."""
        return self._registrations.copy()

    async def validate_registrations(self) -> dict[str, list[str]]:
        """
        Validate all service registrations.

        Returns:
            Dictionary with validation results
        """
        issues = {
            'missing_dependencies': [],
            'circular_dependencies': [],
            'invalid_factories': []
        }

        for service_type, registration in self._registrations.items():
            # Check for missing dependencies
            for dep_type in registration.dependencies:
                if not self.is_registered(dep_type):
                    issues['missing_dependencies'].append(
                        f"{service_type.__name__} depends on unregistered {dep_type.__name__}"
                    )

            # Test factory functions
            if registration.factory:
                try:
                    if asyncio.iscoroutinefunction(registration.factory):
                        await registration.factory()
                    else:
                        registration.factory()
                except Exception as e:
                    issues['invalid_factories'].append(
                        f"{service_type.__name__} factory failed: {e}"
                    )

        # Check for circular dependencies by attempting to resolve all services
        for service_type in self._registrations:
            try:
                self._building_stack.clear()
                await self._resolve_service(service_type)
            except ValueError as e:
                if "circular dependency" in str(e).lower():
                    issues['circular_dependencies'].append(str(e))

        return issues

    @asynccontextmanager
    async def create_scope(self, scope_id: Optional[str] = None):
        """
        Create a new scope for scoped services.

        Args:
            scope_id: Optional scope identifier
        """
        scope_id = scope_id or f"scope_{id(self)}"

        try:
            # Initialize scope
            if scope_id not in self._scoped_instances:
                self._scoped_instances[scope_id] = {}

            yield ScopedServiceProvider(self, scope_id)

        finally:
            # Cleanup scope
            if scope_id in self._scoped_instances:
                # Dispose scoped services that implement disposal
                for instance in self._scoped_instances[scope_id].values():
                    if hasattr(instance, 'dispose') and callable(instance.dispose):
                        try:
                            if asyncio.iscoroutinefunction(instance.dispose):
                                await instance.dispose()
                            else:
                                instance.dispose()
                        except Exception as e:
                            logger.error(f"Error disposing service: {e}")

                del self._scoped_instances[scope_id]

    async def dispose(self):
        """Dispose the container and all singleton services."""
        # Dispose singleton services
        for instance in self._instances.values():
            if hasattr(instance, 'dispose') and callable(instance.dispose):
                try:
                    if asyncio.iscoroutinefunction(instance.dispose):
                        await instance.dispose()
                    else:
                        instance.dispose()
                except Exception as e:
                    logger.error(f"Error disposing singleton service: {e}")

        # Clear all caches
        self._instances.clear()
        self._scoped_instances.clear()
        self._registrations.clear()


class ScopedServiceProvider(ServiceProvider):
    """Service provider for scoped service resolution."""

    def __init__(self, container: DependencyContainer, scope_id: str):
        self.container = container
        self.scope_id = scope_id

    async def get_service(self, service_type: type[T]) -> T:
        """Get service within this scope."""
        async with self.container._lock:
            return await self.container._resolve_service(service_type, self.scope_id)

    def is_registered(self, service_type: type) -> bool:
        """Check if service is registered."""
        return self.container.is_registered(service_type)


# Global container instance
_global_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _global_container
    if _global_container is None:
        _global_container = DependencyContainer()
    return _global_container


def set_container(container: DependencyContainer) -> None:
    """Set the global dependency container."""
    global _global_container
    _global_container = container


# Utility decorators

def injectable(cls):
    """
    Decorator to mark a class as injectable.

    This decorator analyzes the constructor and automatically
    registers dependencies for dependency injection.
    """
    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

    cls.__init__ = __init__
    cls._injectable = True
    return cls


def service(scope: ServiceScope = ServiceScope.TRANSIENT):
    """
    Decorator to automatically register a service.

    Args:
        scope: Service scope (singleton, transient, scoped)
    """
    def decorator(cls):
        # Auto-register with global container when class is defined
        container = get_container()

        if scope == ServiceScope.SINGLETON:
            container.register_singleton(cls, cls)
        elif scope == ServiceScope.SCOPED:
            container.register_scoped(cls, cls)
        else:
            container.register_transient(cls, cls)

        return cls

    return decorator
