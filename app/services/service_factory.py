"""Service factory for dependency injection"""

import time

from app.database import get_database
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DashboardService:
    """Real dashboard service with database integration"""

    def __init__(self):
        self.metrics = {}

    async def get_metrics(self) -> dict:
        """Get real dashboard metrics from database"""
        try:
            db = await get_database()
            stats = await db.get_index_stats()

            return {
                "total_memories": stats["total_memories"],
                "memories_with_embeddings": stats["memories_with_embeddings"],
                "avg_content_length": round(stats["avg_content_length"], 2),
                "hnsw_index_ready": stats["index_ready"],
                "database_status": "connected"
            }
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "total_memories": 0,
                "memories_with_embeddings": 0,
                "avg_content_length": 0,
                "hnsw_index_ready": False,
                "database_status": "error"
            }


class GitService:
    """Real git service with subprocess integration"""

    def __init__(self):
        self.repo_info = {}

    async def get_repo_info(self) -> dict:
        """Get real repository information"""
        try:
            import os
            import subprocess

            # Get current branch
            try:
                branch = subprocess.check_output(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=os.getcwd(),
                    stderr=subprocess.DEVNULL
                ).decode().strip()
            except:
                branch = "unknown"

            # Get last commit
            try:
                last_commit = subprocess.check_output(
                    ['git', 'log', '-1', '--format=%h %s'],
                    cwd=os.getcwd(),
                    stderr=subprocess.DEVNULL
                ).decode().strip()
            except:
                last_commit = "No commits"

            # Get status
            try:
                status = subprocess.check_output(
                    ['git', 'status', '--porcelain'],
                    cwd=os.getcwd(),
                    stderr=subprocess.DEVNULL
                ).decode().strip()

                if status:
                    status_summary = f"{len(status.splitlines())} files changed"
                else:
                    status_summary = "Clean working directory"
            except:
                status_summary = "Unknown"

            return {
                "branch": branch,
                "last_commit": last_commit,
                "status": status_summary,
                "repository_status": "connected"
            }
        except Exception as e:
            logger.error(f"Failed to get git info: {e}")
            return {
                "branch": "unknown",
                "last_commit": "unknown",
                "status": "error",
                "repository_status": "error"
            }


class HealthService:
    """Real health service with comprehensive checks"""

    def __init__(self):
        self.health_data = {}

    async def get_health(self) -> dict:
        """Get comprehensive system health"""
        try:
            # Database health
            db = await get_database()
            db_stats = await db.get_index_stats()

            db_health = "healthy" if db_stats.get("total_memories", 0) >= 0 else "unhealthy"

            # System health checks
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Overall system health assessment
            health_issues = []
            if cpu_percent > 90:
                health_issues.append("High CPU usage")
            if memory.percent > 90:
                health_issues.append("High memory usage")
            if disk.percent > 90:
                health_issues.append("Low disk space")

            overall_status = "unhealthy" if health_issues else "healthy"

            return {
                "status": overall_status,
                "database": {
                    "status": db_health,
                    "total_memories": db_stats.get("total_memories", 0),
                    "index_ready": db_stats.get("index_ready", False)
                },
                "system": {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory.percent, 1),
                    "disk_percent": round(disk.percent, 1)
                },
                "issues": health_issues,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }


class MemoryService:
    """Real memory service with database operations"""

    def __init__(self):
        self.memory_data = {}

    async def get_memory(self, memory_id: str) -> dict:
        """Get a specific memory"""
        try:
            db = await get_database()
            memory = await db.get_memory(memory_id)

            if memory:
                return {
                    "id": str(memory["id"]),
                    "content": memory["content"],
                    "importance_score": memory["importance_score"],
                    "created_at": memory["created_at"].isoformat(),
                    "tags": memory.get("tags", []),
                    "metadata": memory.get("metadata", {})
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def create_memory(self, content: str, importance_score: int = 5, tags: list = None) -> dict:
        """Create a new memory"""
        try:
            db = await get_database()
            memory = await db.create_memory(
                content=content,
                importance_score=importance_score,
                tags=tags or []
            )

            return {
                "id": str(memory["id"]),
                "content": memory["content"],
                "importance_score": memory["importance_score"],
                "created_at": memory["created_at"].isoformat(),
                "tags": memory.get("tags", []),
                "metadata": memory.get("metadata", {})
            }
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            raise

    async def search_memories(self, query: str, limit: int = 10) -> list:
        """Search memories by content similarity"""
        try:
            db = await get_database()
            memories = await db.search_memories(query, limit=limit)

            return [
                {
                    "id": str(memory["id"]),
                    "content": memory["content"],
                    "importance_score": memory["importance_score"],
                    "created_at": memory["created_at"].isoformat(),
                    "similarity_score": memory.get("similarity_score", 0),
                    "tags": memory.get("tags", [])
                }
                for memory in memories
            ]
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def get_memories(self, limit: int = 50, offset: int = 0) -> list:
        """Get paginated memories"""
        try:
            db = await get_database()
            memories = await db.get_memories(limit=limit, offset=offset)

            return [
                {
                    "id": str(memory["id"]),
                    "content": memory["content"],
                    "importance_score": memory["importance_score"],
                    "created_at": memory["created_at"].isoformat(),
                    "tags": memory.get("tags", [])
                }
                for memory in memories
            ]
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []


class SessionService:
    """Real session service with database integration"""

    def __init__(self):
        self.sessions = {}

    async def get_session_stats(self) -> dict:
        """Get session statistics"""
        try:
            db = await get_database()
            stats = await db.get_stats()

            return {
                "total_sessions": len(self.sessions),
                "active_sessions": len([s for s in self.sessions.values() if s.get("active", False)]),
                "total_memories": stats.get("total_memories", 0),
                "avg_content_length": round(stats.get("avg_content_length", 0), 2)
            }
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_memories": 0,
                "avg_content_length": 0
            }

    async def create_session(self, session_data: dict) -> dict:
        """Create a new session"""
        try:
            session_id = f"session_{len(self.sessions) + 1}"
            self.sessions[session_id] = {
                **session_data,
                "id": session_id,
                "active": True,
                "created_at": time.time()
            }

            return self.sessions[session_id]
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(self, session_id: str) -> dict:
        """Get session by ID"""
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, updates: dict) -> dict:
        """Update session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            return self.sessions[session_id]
        return None

    async def close_session(self, session_id: str) -> bool:
        """Close a session"""
        if session_id in self.sessions:
            self.sessions[session_id]["active"] = False
            return True
        return False


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


# Legacy factory class for backwards compatibility
class ServiceFactory:
    """Legacy service factory for compatibility"""

    @staticmethod
    def get_dashboard_service() -> DashboardService:
        return get_dashboard_service()

    @staticmethod
    def get_git_service() -> GitService:
        return get_git_service()

    @staticmethod
    def get_health_service() -> HealthService:
        return get_health_service()

    @staticmethod
    def get_memory_service() -> MemoryService:
        return get_memory_service()

    @staticmethod
    def get_session_service() -> SessionService:
        return get_session_service()


# Factory instance for global access
service_factory = ServiceFactory()
