"""
Service factory implementations following Factory pattern.

Provides specialized factories for different service categories
with proper dependency injection and lifecycle management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from ..events.event_bus import EventBus
from ..repositories.repository_factory import RepositoryFactory
from .dependency_container import DependencyContainer

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ServiceConfiguration:
    """Configuration for service creation."""
    enable_events: bool = True
    enable_caching: bool = True
    enable_metrics: bool = True
    debug_mode: bool = False
    timeout_seconds: int = 30


class ServiceFactory(ABC):
    """
    Abstract base class for service factories.

    Defines the contract for creating services with proper
    dependency injection and configuration management.
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: ServiceConfiguration
    ):
        self.container = container
        self.config = config
        self._created_services: dict[type, Any] = {}

    @abstractmethod
    async def create_services(self) -> None:
        """Create and register all services managed by this factory."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all created services."""
        pass

    async def get_service(self, service_type: type[T]) -> T:
        """Get service instance from container."""
        return await self.container.get_service(service_type)

    async def dispose(self) -> None:
        """Dispose factory and created services."""
        self._created_services.clear()


class MemoryServiceFactory(ServiceFactory):
    """
    Factory for creating memory-related services.

    Manages memory service, relationship analyzer, and related components
    with proper dependency injection.
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: ServiceConfiguration,
        repository_factory: RepositoryFactory,
        event_bus: EventBus
    ):
        super().__init__(container, config)
        self.repository_factory = repository_factory
        self.event_bus = event_bus

    async def create_services(self) -> None:
        """Create and register memory-related services."""
        # Import here to avoid circular imports
        from ..services.memory_service import MemoryService
        from ..services.relationship_analyzer import RelationshipAnalyzer
        from ..utils.openai_client import OpenAIClient

        # Register dependencies first
        memory_repo = await self.repository_factory.create_memory_repository()

        # Create OpenAI client factory
        async def create_openai_client() -> OpenAIClient:
            return OpenAIClient()

        # Register repositories and utilities
        self.container.register_singleton(type(memory_repo), instance=memory_repo)
        self.container.register_singleton(EventBus, instance=self.event_bus)
        self.container.register_transient(OpenAIClient, factory=create_openai_client)

        # Register memory services
        self.container.register_singleton(MemoryService, MemoryService)
        self.container.register_singleton(RelationshipAnalyzer, RelationshipAnalyzer)

        # Create and cache service instances
        self._created_services[MemoryService] = await self.container.get_service(MemoryService)
        self._created_services[RelationshipAnalyzer] = await self.container.get_service(RelationshipAnalyzer)

        logger.info(f"Created {len(self._created_services)} memory services")

    async def health_check(self) -> dict[str, Any]:
        """Health check for memory services."""
        health_results = {}

        for service_type, service in self._created_services.items():
            try:
                # Check if service has health_check method
                if hasattr(service, 'health_check') and callable(service.health_check):
                    if asyncio.iscoroutinefunction(service.health_check):
                        result = await service.health_check()
                    else:
                        result = service.health_check()
                    health_results[service_type.__name__] = result
                else:
                    # Basic health check - just verify service exists
                    health_results[service_type.__name__] = {'status': 'healthy', 'message': 'Service available'}

            except Exception as e:
                health_results[service_type.__name__] = {'status': 'unhealthy', 'error': str(e)}

        overall_status = 'healthy' if all(
            result.get('status') == 'healthy'
            for result in health_results.values()
        ) else 'degraded'

        return {
            'overall_status': overall_status,
            'services': health_results,
            'factory_config': {
                'enable_events': self.config.enable_events,
                'enable_caching': self.config.enable_caching,
                'enable_metrics': self.config.enable_metrics
            }
        }


class AnalyticsServiceFactory(ServiceFactory):
    """
    Factory for creating analytics and intelligence services.

    Manages predictive insights, anomaly detection, and analytics dashboard
    services with proper configuration and dependencies.
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: ServiceConfiguration,
        repository_factory: RepositoryFactory,
        event_bus: EventBus
    ):
        super().__init__(container, config)
        self.repository_factory = repository_factory
        self.event_bus = event_bus

    async def create_services(self) -> None:
        """Create and register analytics services."""
        # Import analytics services
        from ..database import Database
        from ..services.intelligence.analytics_dashboard import AnalyticsDashboardService
        from ..services.intelligence.anomaly_detection import AnomalyDetectionService
        from ..services.intelligence.knowledge_gap_analysis import KnowledgeGapAnalyzer
        from ..services.intelligence.predictive_insights import PredictiveInsightsService
        from ..services.memory_service import MemoryService
        from ..utils.openai_client import OpenAIClient

        # Get required dependencies
        memory_repo = await self.repository_factory.create_memory_repository()

        # Create mock dependencies for now (these would be properly configured in production)
        async def create_database() -> Database:
            # This would be properly configured with real database connection
            return Database()

        async def create_openai_client() -> OpenAIClient:
            return OpenAIClient()

        async def create_memory_service() -> MemoryService:
            # Get existing memory service or create new one
            if self.container.is_registered(MemoryService):
                return await self.container.get_service(MemoryService)
            # Create new instance with dependencies
            database = await create_database()
            return MemoryService(database)

        # Register dependencies
        self.container.register_transient(Database, factory=create_database)
        self.container.register_transient(OpenAIClient, factory=create_openai_client)
        self.container.register_singleton(MemoryService, factory=create_memory_service)

        # Register analytics services
        self.container.register_singleton(PredictiveInsightsService, PredictiveInsightsService)
        self.container.register_singleton(AnomalyDetectionService, AnomalyDetectionService)
        self.container.register_singleton(KnowledgeGapAnalyzer, KnowledgeGapAnalyzer)
        self.container.register_singleton(AnalyticsDashboardService, AnalyticsDashboardService)

        # Create service instances
        services_to_create = [
            PredictiveInsightsService,
            AnomalyDetectionService,
            KnowledgeGapAnalyzer,
            AnalyticsDashboardService
        ]

        for service_type in services_to_create:
            try:
                service_instance = await self.container.get_service(service_type)
                self._created_services[service_type] = service_instance
                logger.debug(f"Created {service_type.__name__}")
            except Exception as e:
                logger.error(f"Failed to create {service_type.__name__}: {e}")

        logger.info(f"Created {len(self._created_services)} analytics services")

    async def health_check(self) -> dict[str, Any]:
        """Health check for analytics services."""
        health_results = {}

        for service_type, service in self._created_services.items():
            try:
                # Basic health check
                health_results[service_type.__name__] = {
                    'status': 'healthy',
                    'service_type': 'analytics',
                    'has_dependencies': hasattr(service, 'db') or hasattr(service, 'database')
                }
            except Exception as e:
                health_results[service_type.__name__] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }

        # Check repository factory health
        repo_health = await self.repository_factory.health_check()

        overall_status = 'healthy'
        if repo_health.get('status') != 'healthy':
            overall_status = 'degraded'
        if any(result.get('status') != 'healthy' for result in health_results.values()):
            overall_status = 'degraded'

        return {
            'overall_status': overall_status,
            'services': health_results,
            'repository_health': repo_health,
            'factory_config': {
                'enable_events': self.config.enable_events,
                'enable_metrics': self.config.enable_metrics
            }
        }


class SynthesisServiceFactory(ServiceFactory):
    """
    Factory for creating synthesis and advanced processing services.

    Manages advanced synthesis, graph visualization, workflow automation,
    and other complex processing services.
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: ServiceConfiguration,
        repository_factory: RepositoryFactory,
        event_bus: EventBus
    ):
        super().__init__(container, config)
        self.repository_factory = repository_factory
        self.event_bus = event_bus

    async def create_services(self) -> None:
        """Create and register synthesis services."""
        # Import synthesis services
        from ..database import Database
        from ..services.memory_service import MemoryService
        from ..services.synthesis.advanced_synthesis import AdvancedSynthesisEngine
        from ..services.synthesis.export_import import ExportImportService
        from ..services.synthesis.graph_visualization import GraphVisualizationService
        from ..services.synthesis.report_generator import ReportGenerator
        from ..services.synthesis.workflow_automation import WorkflowAutomationService
        from ..utils.openai_client import OpenAIClient

        # Create dependency factories
        async def create_database() -> Database:
            return Database()

        async def create_memory_service() -> MemoryService:
            if self.container.is_registered(MemoryService):
                return await self.container.get_service(MemoryService)
            database = await create_database()
            return MemoryService(database)

        async def create_openai_client() -> OpenAIClient:
            return OpenAIClient()

        # Register dependencies
        self.container.register_transient(Database, factory=create_database)
        self.container.register_transient(OpenAIClient, factory=create_openai_client)
        self.container.register_singleton(MemoryService, factory=create_memory_service)

        # Register synthesis services
        self.container.register_singleton(AdvancedSynthesisEngine, AdvancedSynthesisEngine)
        self.container.register_singleton(GraphVisualizationService, GraphVisualizationService)
        self.container.register_singleton(WorkflowAutomationService, WorkflowAutomationService)
        self.container.register_singleton(ExportImportService, ExportImportService)
        self.container.register_singleton(ReportGenerator, ReportGenerator)

        # Create service instances
        services_to_create = [
            AdvancedSynthesisEngine,
            GraphVisualizationService,
            WorkflowAutomationService,
            ExportImportService,
            ReportGenerator
        ]

        for service_type in services_to_create:
            try:
                service_instance = await self.container.get_service(service_type)
                self._created_services[service_type] = service_instance
                logger.debug(f"Created {service_type.__name__}")
            except Exception as e:
                logger.error(f"Failed to create {service_type.__name__}: {e}")

        logger.info(f"Created {len(self._created_services)} synthesis services")

    async def health_check(self) -> dict[str, Any]:
        """Health check for synthesis services."""
        health_results = {}

        for service_type, service in self._created_services.items():
            try:
                health_results[service_type.__name__] = {
                    'status': 'healthy',
                    'service_type': 'synthesis',
                    'capabilities': getattr(service, 'get_capabilities', lambda: [])()
                }
            except Exception as e:
                health_results[service_type.__name__] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }

        overall_status = 'healthy' if all(
            result.get('status') == 'healthy'
            for result in health_results.values()
        ) else 'degraded'

        return {
            'overall_status': overall_status,
            'services': health_results,
            'factory_config': {
                'enable_events': self.config.enable_events,
                'enable_caching': self.config.enable_caching
            }
        }


class MasterServiceFactory:
    """
    Master factory that coordinates all service factories.

    Provides a unified interface for creating and managing
    all application services with proper initialization order.
    """

    def __init__(
        self,
        repository_factory: RepositoryFactory,
        event_bus: EventBus,
        config: Optional[ServiceConfiguration] = None
    ):
        self.repository_factory = repository_factory
        self.event_bus = event_bus
        self.config = config or ServiceConfiguration()
        self.container = DependencyContainer()

        self.factories: dict[str, ServiceFactory] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all service factories."""
        if self._initialized:
            return

        try:
            # Create specialized factories
            self.factories['memory'] = MemoryServiceFactory(
                self.container, self.config, self.repository_factory, self.event_bus
            )

            self.factories['analytics'] = AnalyticsServiceFactory(
                self.container, self.config, self.repository_factory, self.event_bus
            )

            self.factories['synthesis'] = SynthesisServiceFactory(
                self.container, self.config, self.repository_factory, self.event_bus
            )

            # Initialize services in dependency order
            initialization_order = ['memory', 'analytics', 'synthesis']

            for factory_name in initialization_order:
                factory = self.factories[factory_name]
                await factory.create_services()
                logger.info(f"Initialized {factory_name} factory")

            # Validate all registrations
            validation_results = await self.container.validate_registrations()
            if any(validation_results.values()):
                logger.warning(f"Service validation issues found: {validation_results}")

            self._initialized = True
            logger.info("Master service factory initialization complete")

        except Exception as e:
            logger.error(f"Service factory initialization failed: {e}")
            raise

    async def get_service(self, service_type: type[T]) -> T:
        """Get service instance."""
        if not self._initialized:
            await self.initialize()

        return await self.container.get_service(service_type)

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check of all services."""
        if not self._initialized:
            return {'status': 'not_initialized'}

        health_results = {}

        # Check each factory
        for factory_name, factory in self.factories.items():
            try:
                factory_health = await factory.health_check()
                health_results[factory_name] = factory_health
            except Exception as e:
                health_results[factory_name] = {
                    'overall_status': 'error',
                    'error': str(e)
                }

        # Check repository factory
        repo_health = await self.repository_factory.health_check()
        health_results['repository'] = repo_health

        # Check event bus
        event_health = await self.event_bus.health_check()
        health_results['event_bus'] = event_health

        # Check container
        container_stats = self.container.get_stats()
        health_results['dependency_container'] = {
            'status': 'healthy',
            'registrations': container_stats
        }

        # Determine overall status
        overall_status = 'healthy'
        for result in health_results.values():
            status = result.get('overall_status') or result.get('status')
            if status in ['unhealthy', 'error']:
                overall_status = 'unhealthy'
                break
            elif status in ['degraded']:
                overall_status = 'degraded'

        return {
            'overall_status': overall_status,
            'components': health_results,
            'initialized': self._initialized,
            'configuration': {
                'enable_events': self.config.enable_events,
                'enable_caching': self.config.enable_caching,
                'enable_metrics': self.config.enable_metrics,
                'debug_mode': self.config.debug_mode
            }
        }

    async def dispose(self) -> None:
        """Dispose all factories and services."""
        # Dispose factories in reverse order
        for factory_name in reversed(list(self.factories.keys())):
            try:
                await self.factories[factory_name].dispose()
                logger.debug(f"Disposed {factory_name} factory")
            except Exception as e:
                logger.error(f"Error disposing {factory_name} factory: {e}")

        # Dispose container
        await self.container.dispose()

        # Dispose repository factory
        await self.repository_factory.dispose()

        self.factories.clear()
        self._initialized = False

        logger.info("Master service factory disposed")


# Global master factory instance
_master_factory: Optional[MasterServiceFactory] = None


async def get_master_factory() -> MasterServiceFactory:
    """Get the global master service factory."""
    global _master_factory
    if _master_factory is None:
        raise RuntimeError("Master service factory not initialized. Call initialize_services() first.")
    return _master_factory


async def initialize_services(
    repository_factory: RepositoryFactory,
    event_bus: EventBus,
    config: Optional[ServiceConfiguration] = None
) -> MasterServiceFactory:
    """
    Initialize the global service factory system.

    Args:
        repository_factory: Repository factory for data access
        event_bus: Event bus for domain events
        config: Service configuration

    Returns:
        Initialized master service factory
    """
    global _master_factory

    if _master_factory is not None:
        await _master_factory.dispose()

    _master_factory = MasterServiceFactory(repository_factory, event_bus, config)
    await _master_factory.initialize()

    logger.info("Global service factory system initialized")
    return _master_factory


async def dispose_services() -> None:
    """Dispose the global service factory system."""
    global _master_factory
    if _master_factory is not None:
        await _master_factory.dispose()
        _master_factory = None
