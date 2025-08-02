"""
Service Factory
Provides singleton instances of services
"""

from typing import Optional, Dict, Any, List
from app.services.memory_service_new import MemoryService
from app.services.knowledge_graph_builder import KnowledgeGraphBuilder
from app.services.reasoning_engine import ReasoningEngine
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# Stub service classes for missing services
class DashboardService:
    """Dashboard service stub"""
    def __init__(self):
        logger.info("DashboardService initialized (stub)")
    
    async def get_stats(self) -> Dict[str, Any]:
        return {"total_memories": 0, "active_users": 0}


class GitService:
    """Git service stub"""
    def __init__(self):
        logger.info("GitService initialized (stub)")
    
    async def get_status(self) -> str:
        return "No git repository"


class HealthService:
    """Health service stub"""
    def __init__(self):
        logger.info("HealthService initialized (stub)")
    
    async def check_health(self) -> Dict[str, Any]:
        return {"status": "healthy", "services": {}}


class SessionService:
    """Session service stub"""
    def __init__(self):
        logger.info("SessionService initialized (stub)")
        self.sessions = {}
    
    async def create_session(self, user_id: str) -> str:
        session_id = f"session_{user_id}"
        self.sessions[session_id] = {"user_id": user_id}
        return session_id


# Singleton instances
_memory_service: Optional[MemoryService] = None
_knowledge_graph: Optional[KnowledgeGraphBuilder] = None
_reasoning_engine: Optional[ReasoningEngine] = None
_dashboard_service: Optional[DashboardService] = None
_git_service: Optional[GitService] = None
_health_service: Optional[HealthService] = None
_session_service: Optional[SessionService] = None


def get_memory_service() -> MemoryService:
    """Get or create memory service instance"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
        logger.info("Created new MemoryService instance")
    return _memory_service


def get_knowledge_graph_builder() -> KnowledgeGraphBuilder:
    """Get or create knowledge graph builder instance"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraphBuilder()
        logger.info("Created new KnowledgeGraphBuilder instance")
    return _knowledge_graph


def get_reasoning_engine() -> ReasoningEngine:
    """Get or create reasoning engine instance"""
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
        logger.info("Created new ReasoningEngine instance")
    return _reasoning_engine


def get_dashboard_service() -> DashboardService:
    """Get or create dashboard service instance"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
        logger.info("Created new DashboardService instance")
    return _dashboard_service


def get_git_service() -> GitService:
    """Get or create git service instance"""
    global _git_service
    if _git_service is None:
        _git_service = GitService()
        logger.info("Created new GitService instance")
    return _git_service


def get_health_service() -> HealthService:
    """Get or create health service instance"""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
        logger.info("Created new HealthService instance")
    return _health_service


def get_session_service() -> SessionService:
    """Get or create session service instance"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
        logger.info("Created new SessionService instance")
    return _session_service


def reset_services():
    """Reset all service instances (for testing)"""
    global _memory_service, _knowledge_graph, _reasoning_engine
    global _dashboard_service, _git_service, _health_service, _session_service
    _memory_service = None
    _knowledge_graph = None
    _reasoning_engine = None
    _dashboard_service = None
    _git_service = None
    _health_service = None
    _session_service = None
    logger.info("All services reset")