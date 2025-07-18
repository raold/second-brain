"""
Service Factory - Manages service instantiation and dependency injection.
Provides a centralized way to create and access service instances.
"""

import logging
from typing import Optional

from app.database import Database
from app.database_mock import MockDatabase
from app.security import InputValidator, SecurityManager
from app.session_manager import SessionManager, get_session_manager
from app.conversation_processor import ConversationProcessor
from app.dashboard import ProjectDashboard

from .memory_service import MemoryService
from .session_service import SessionService
from .dashboard_service import DashboardService
from .health_service import HealthService

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory for creating and managing service instances.
    Implements singleton pattern for service reuse.
    """
    
    def __init__(self):
        self._memory_service: Optional[MemoryService] = None
        self._session_service: Optional[SessionService] = None
        self._dashboard_service: Optional[DashboardService] = None
        self._health_service: Optional[HealthService] = None
        self._database: Optional[Database | MockDatabase] = None
        self._security_manager: Optional[SecurityManager] = None
        self.logger = logger
    
    def set_database(self, database: Database | MockDatabase):
        """Set the database instance to be used by services."""
        self._database = database
        # Reset services when database changes
        self._memory_service = None
        self._health_service = None
    
    def set_security_manager(self, security_manager: SecurityManager):
        """Set the security manager instance."""
        self._security_manager = security_manager
        # Reset services that depend on security
        self._memory_service = None
    
    def get_memory_service(self) -> MemoryService:
        """
        Get or create memory service instance.
        
        Returns:
            MemoryService instance
        """
        if self._memory_service is None:
            if not self._database:
                raise RuntimeError("Database not set. Call set_database() first.")
            if not self._security_manager:
                raise RuntimeError("Security manager not set. Call set_security_manager() first.")
            
            input_validator = self._security_manager.input_validator
            self._memory_service = MemoryService(self._database, input_validator)
            self.logger.info("Created MemoryService instance")
        
        return self._memory_service
    
    def get_session_service(self) -> SessionService:
        """
        Get or create session service instance.
        
        Returns:
            SessionService instance
        """
        if self._session_service is None:
            # Get required components
            session_manager = get_session_manager()
            
            # Create conversation processor
            conversation_processor = ConversationProcessor()
            
            # Create project dashboard
            project_dashboard = ProjectDashboard()
            
            self._session_service = SessionService(
                session_manager=session_manager,
                conversation_processor=conversation_processor,
                project_dashboard=project_dashboard
            )
            self.logger.info("Created SessionService instance")
        
        return self._session_service
    
    def get_dashboard_service(self) -> DashboardService:
        """
        Get or create dashboard service instance.
        
        Returns:
            DashboardService instance
        """
        if self._dashboard_service is None:
            # Create project dashboard
            project_dashboard = ProjectDashboard()
            
            self._dashboard_service = DashboardService(project_dashboard)
            self.logger.info("Created DashboardService instance")
        
        return self._dashboard_service
    
    def get_health_service(self) -> HealthService:
        """
        Get or create health service instance.
        
        Returns:
            HealthService instance
        """
        if self._health_service is None:
            if not self._database:
                raise RuntimeError("Database not set. Call set_database() first.")
            
            self._health_service = HealthService(self._database)
            self.logger.info("Created HealthService instance")
        
        return self._health_service
    
    def reset_all_services(self):
        """Reset all service instances. Useful for testing."""
        self._memory_service = None
        self._session_service = None
        self._dashboard_service = None
        self._health_service = None
        self.logger.info("Reset all service instances")


# Global factory instance
_service_factory = ServiceFactory()


def get_service_factory() -> ServiceFactory:
    """
    Get the global service factory instance.
    
    Returns:
        ServiceFactory instance
    """
    return _service_factory


# Convenience functions for getting services
def get_memory_service() -> MemoryService:
    """Get memory service instance."""
    return _service_factory.get_memory_service()


def get_session_service() -> SessionService:
    """Get session service instance."""
    return _service_factory.get_session_service()


def get_dashboard_service() -> DashboardService:
    """Get dashboard service instance."""
    return _service_factory.get_dashboard_service()


def get_health_service() -> HealthService:
    """Get health service instance."""
    return _service_factory.get_health_service() 