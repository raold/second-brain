"""Service factory for dependency injection"""

from typing import Any
import logging

logger = logging.getLogger(__name__)


class DashboardService:
    """Mock dashboard service"""
    
    def __init__(self):
        self.metrics = {}
    
    async def get_metrics(self) -> dict:
        """Get dashboard metrics"""
        return {
            "total_memories": 100,
            "active_users": 5,
            "storage_used": "150MB",
            "api_calls": 1000
        }


class GitService:
    """Mock git service"""
    
    def __init__(self):
        self.repo_info = {}
    
    async def get_repo_info(self) -> dict:
        """Get repository information"""
        return {
            "branch": "main",
            "commit": "abc123",
            "status": "clean"
        }


class HealthService:
    """Mock health service"""
    
    def __init__(self):
        self.status = "healthy"
    
    async def check_health(self) -> dict:
        """Check system health"""
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "services": "operational"
        }


class MemoryService:
    """Mock memory service"""
    
    def __init__(self):
        self.memories = []
    
    async def get_memories(self) -> list:
        """Get all memories"""
        return self.memories
    
    async def create_memory(self, memory_data: dict) -> dict:
        """Create a new memory"""
        self.memories.append(memory_data)
        return memory_data


class SessionService:
    """Mock session service"""
    
    def __init__(self):
        self.sessions = {}
    
    async def create_session(self, user_id: str) -> dict:
        """Create a new session"""
        session = {
            "id": f"session_{len(self.sessions)}",
            "user_id": user_id,
            "created_at": "2024-01-01T00:00:00Z"
        }
        self.sessions[session["id"]] = session
        return session
    
    async def get_session(self, session_id: str) -> dict:
        """Get a session"""
        return self.sessions.get(session_id, {})


# Singleton instances
_dashboard_service = None
_git_service = None
_health_service = None
_memory_service = None
_session_service = None


def get_dashboard_service() -> DashboardService:
    """Get dashboard service instance"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service


def get_git_service() -> GitService:
    """Get git service instance"""
    global _git_service
    if _git_service is None:
        _git_service = GitService()
    return _git_service


def get_health_service() -> HealthService:
    """Get health service instance"""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


def get_memory_service() -> MemoryService:
    """Get memory service instance"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def get_session_service() -> SessionService:
    """Get session service instance"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service


class ServiceFactory:
    """Factory for creating service instances"""
    
    @staticmethod
    def get_dashboard_service() -> DashboardService:
        """Get dashboard service"""
        return get_dashboard_service()
    
    @staticmethod
    def get_git_service() -> GitService:
        """Get git service"""
        return get_git_service()
    
    @staticmethod
    def get_health_service() -> HealthService:
        """Get health service"""
        return get_health_service()
    
    @staticmethod
    def get_memory_service() -> MemoryService:
        """Get memory service"""
        return get_memory_service()
    
    @staticmethod
    def get_session_service() -> SessionService:
        """Get session service"""
        return get_session_service()


# Singleton factory instance
_service_factory = None


def get_service_factory() -> ServiceFactory:
    """Get singleton instance of service factory"""
    global _service_factory
    if _service_factory is None:
        _service_factory = ServiceFactory()
    return _service_factory