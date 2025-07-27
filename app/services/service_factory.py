"""Service factory for dependency injection"""

from typing import Any
import logging
import json
import uuid
from datetime import datetime
from app.database import get_database

logger = logging.getLogger(__name__)


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
            import subprocess
            import os
            
            # Get current branch
            try:
                branch = subprocess.check_output(
                    ["git", "branch", "--show-current"], 
                    text=True, 
                    cwd=os.getcwd()
                ).strip()
            except:
                branch = "unknown"
            
            # Get latest commit hash
            try:
                commit = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"], 
                    text=True, 
                    cwd=os.getcwd()
                ).strip()
            except:
                commit = "unknown"
            
            # Get status
            try:
                status_output = subprocess.check_output(
                    ["git", "status", "--porcelain"], 
                    text=True, 
                    cwd=os.getcwd()
                ).strip()
                status = "clean" if not status_output else "dirty"
            except:
                status = "unknown"
            
            return {
                "branch": branch,
                "commit": commit,
                "status": status
            }
        except Exception as e:
            logger.error(f"Failed to get git info: {e}")
            return {
                "branch": "unknown",
                "commit": "unknown",
                "status": "error"
            }


class HealthService:
    """Real health service with actual system checks"""
    
    def __init__(self):
        self.status = "unknown"
    
    async def check_health(self) -> dict:
        """Check real system health"""
        health_status = {
            "status": "healthy",
            "database": "unknown",
            "redis": "unknown", 
            "services": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check database
        try:
            db = await get_database()
            if db.pool:
                health_status["database"] = "connected"
            else:
                health_status["database"] = "disconnected"
                health_status["status"] = "degraded"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["database"] = "error"
            health_status["status"] = "unhealthy"
        
        # Check Redis connection
        try:
            import redis as redis_sync
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Use synchronous Redis client for health check (more compatible)
            redis_client = redis_sync.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
            redis_client.ping()
            
            health_status["redis"] = "healthy"
            logger.debug("Redis health check passed")
        except ImportError:
            health_status["redis"] = "not_available"
            logger.warning("Redis client not installed")
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["redis"] = "error"
        
        # Check OpenAI API
        try:
            db = await get_database()
            if db.openai_client:
                health_status["openai"] = "connected"
            else:
                health_status["openai"] = "not_configured"
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            health_status["openai"] = "error"
        
        # Overall service status
        if health_status["database"] == "connected":
            health_status["services"] = "operational"
        else:
            health_status["services"] = "degraded"
            health_status["status"] = "degraded"
        
        return health_status
    
    async def get_health_status(self) -> dict:
        """Get health status with version info for routes"""
        basic_health = await self.check_health()
        return {
            "status": basic_health["status"],
            "version": "3.0.0",
            "timestamp": basic_health["timestamp"]
        }
    
    async def get_system_status(self) -> dict:
        """Get system status with database and performance metrics"""
        try:
            db = await get_database()
            stats = await db.get_index_stats()
            
            recommendations = []
            if not stats["index_ready"]:
                recommendations.append("Consider creating vector index for better performance")
            if stats["total_memories"] == 0:
                recommendations.append("No memories found - try adding some content")
            
            return {
                "database": {
                    "connected": db.pool is not None,
                    "total_memories": stats["total_memories"],
                    "avg_content_length": stats["avg_content_length"]
                },
                "index_status": {
                    "hnsw_ready": stats["hnsw_index_exists"],
                    "ivf_ready": stats["ivf_index_exists"],
                    "index_ready": stats["index_ready"]
                },
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "database": "disconnected",
                "index_status": {
                    "total_memories": 0,
                    "memories_with_embeddings": 0,
                    "hnsw_index_exists": False,
                    "ivf_index_exists": False,
                    "index_ready": False
                },
                "recommendations": {
                    "create_index": False,
                    "index_type": "None",
                    "error": str(e)
                }
            }
    
    async def run_diagnostics(self) -> dict:
        """Run comprehensive system diagnostics"""
        diagnostics = {
            "overall_status": "healthy",
            "checks": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Database connectivity check
        try:
            db = await get_database()
            if db.pool:
                async with db.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                diagnostics["checks"].append({
                    "name": "database_connectivity",
                    "status": "pass",
                    "message": "Database connection successful"
                })
            else:
                diagnostics["checks"].append({
                    "name": "database_connectivity", 
                    "status": "fail",
                    "message": "Database pool not available"
                })
                diagnostics["overall_status"] = "critical"
        except Exception as e:
            diagnostics["checks"].append({
                "name": "database_connectivity",
                "status": "fail", 
                "message": f"Database connection failed: {e}"
            })
            diagnostics["overall_status"] = "critical"
        
        # OpenAI API check
        try:
            db = await get_database()
            if db.openai_client:
                diagnostics["checks"].append({
                    "name": "openai_api",
                    "status": "pass",
                    "message": "OpenAI client configured"
                })
            else:
                diagnostics["checks"].append({
                    "name": "openai_api",
                    "status": "fail",
                    "message": "OpenAI client not configured"
                })
                if diagnostics["overall_status"] == "healthy":
                    diagnostics["overall_status"] = "degraded"
        except Exception as e:
            diagnostics["checks"].append({
                "name": "openai_api",
                "status": "fail",
                "message": f"OpenAI check failed: {e}"
            })
            if diagnostics["overall_status"] == "healthy":
                diagnostics["overall_status"] = "degraded"
        
        return diagnostics
    
    async def get_performance_metrics(self) -> dict:
        """Get detailed performance metrics"""
        try:
            db = await get_database()
            stats = await db.get_index_stats()
            
            return {
                "database_metrics": {
                    "total_memories": stats["total_memories"],
                    "memories_with_embeddings": stats["memories_with_embeddings"],
                    "avg_content_length": stats["avg_content_length"],
                    "embedding_coverage": stats["memories_with_embeddings"] / max(stats["total_memories"], 1) * 100
                },
                "index_metrics": {
                    "hnsw_available": stats["hnsw_index_exists"],
                    "ivf_available": stats["ivf_index_exists"],
                    "recommended_threshold": stats["recommended_index_threshold"],
                    "ready_for_optimization": stats["index_ready"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class MemoryService:
    """Real memory service with database integration"""
    
    def __init__(self):
        pass
    
    async def get_memories(self, limit: int = 100, offset: int = 0) -> list:
        """Get all memories from database"""
        try:
            db = await get_database()
            memories = await db.get_all_memories(limit=limit, offset=offset)
            logger.info(f"Retrieved {len(memories)} memories")
            return memories
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    async def create_memory(self, content: str, memory_type: str = None, metadata: dict = None) -> dict:
        """Create a new memory in database"""
        try:
            db = await get_database()
            
            # Auto-classify memory type if not provided
            if not memory_type:
                memory_type = db.classify_memory_type(content, metadata)
            
            # Generate smart metadata
            smart_metadata = db.generate_smart_metadata(content, memory_type)
            if metadata:
                smart_metadata.update(metadata)
            
            # Store memory with type-specific metadata
            type_metadata = {}
            if memory_type == "semantic":
                type_metadata = {"semantic_metadata": smart_metadata}
            elif memory_type == "episodic":
                type_metadata = {"episodic_metadata": smart_metadata}
            elif memory_type == "procedural":
                type_metadata = {"procedural_metadata": smart_metadata}
            
            memory_id = await db.store_memory(
                content=content,
                memory_type=memory_type,
                metadata=metadata or {},
                **type_metadata
            )
            
            # Retrieve the stored memory
            memory = await db.get_memory(memory_id)
            logger.info(f"Created {memory_type} memory: {memory_id}")
            return memory
            
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            raise
    
    async def get_memory(self, memory_id: str) -> dict:
        """Get specific memory by ID"""
        try:
            db = await get_database()
            memory = await db.get_memory(memory_id)
            if memory:
                logger.info(f"Retrieved memory: {memory_id}")
                return memory
            else:
                logger.warning(f"Memory not found: {memory_id}")
                return {}
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return {}
    
    async def search_memories(self, query: str, limit: int = 10, memory_types: list = None) -> list:
        """Search memories using vector similarity"""
        try:
            db = await get_database()
            results = await db.contextual_search(
                query=query,
                limit=limit,
                memory_types=memory_types
            )
            logger.info(f"Search found {len(results)} memories for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory by ID"""
        try:
            db = await get_database()
            deleted = await db.delete_memory(memory_id)
            if deleted:
                logger.info(f"Deleted memory: {memory_id}")
            else:
                logger.warning(f"Memory not found for deletion: {memory_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False


class SessionService:
    """Real session service with proper session management"""
    
    def __init__(self):
        self.sessions = {}  # In-memory for now, could move to Redis/database
        self.current_session_id = None
    
    async def create_session(self, user_id: str = None) -> dict:
        """Create a new session"""
        try:
            session_id = str(uuid.uuid4())
            session = {
                "id": session_id,
                "user_id": user_id or "anonymous",
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "memories_created": 0,
                "queries_made": 0,
                "status": "active",
                "paused": False,
                "ideas_processed": 0
            }
            self.sessions[session_id] = session
            self.current_session_id = session_id
            logger.info(f"Created session: {session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> dict:
        """Get a session and update last accessed"""
        try:
            session = self.sessions.get(session_id)
            if session:
                session["last_accessed"] = datetime.utcnow().isoformat()
                logger.info(f"Retrieved session: {session_id}")
                return session
            else:
                logger.warning(f"Session not found: {session_id}")
                return {}
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return {}
    
    async def get_session_status(self) -> dict:
        """Get current session status"""
        try:
            if self.current_session_id:
                session = self.sessions.get(self.current_session_id)
                if session:
                    return {
                        "session_id": self.current_session_id,
                        "status": session["status"],
                        "paused": session.get("paused", False),
                        "memories_created": session.get("memories_created", 0),
                        "ideas_processed": session.get("ideas_processed", 0),
                        "last_accessed": session["last_accessed"],
                        "uptime": datetime.utcnow().isoformat()
                    }
            
            # No current session, create one
            session = await self.create_session()
            return {
                "session_id": session["id"],
                "status": "active",
                "paused": False,
                "memories_created": 0,
                "ideas_processed": 0,
                "last_accessed": session["created_at"],
                "uptime": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return {"error": str(e)}
    
    async def ingest_idea(self, idea: str, source: str = "mobile", priority: str = "medium", context: str = None) -> dict:
        """Ingest and process an idea (woodchipper functionality)"""
        try:
            # Ensure we have a current session
            if not self.current_session_id:
                await self.create_session()
            
            # Process the idea by storing it as a memory
            from app.core.dependencies import get_memory_service
            memory_service = get_memory_service()
            
            # Determine memory type based on idea content
            if any(word in idea.lower() for word in ["how to", "process", "step", "procedure"]):
                memory_type = "procedural"
            elif any(word in idea.lower() for word in ["meeting", "today", "just", "fixed", "discovered"]):
                memory_type = "episodic"
            else:
                memory_type = "semantic"
            
            # Store the idea as a memory
            memory = await memory_service.create_memory(
                content=idea,
                memory_type=memory_type,
                metadata={
                    "source": source,
                    "priority": priority,
                    "context": context,
                    "session_id": self.current_session_id,
                    "ingestion_method": "woodchipper"
                }
            )
            
            # Update session stats
            session = self.sessions.get(self.current_session_id)
            if session:
                session["ideas_processed"] += 1
                session["memories_created"] += 1
                session["last_accessed"] = datetime.utcnow().isoformat()
            
            logger.info(f"Idea ingested successfully: {memory['id']}")
            return {
                "success": True,
                "memory_id": memory["id"],
                "memory_type": memory_type,
                "classification": f"Classified as {memory_type} memory",
                "session_id": self.current_session_id,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest idea: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": self.current_session_id
            }
    
    async def pause_session(self, reason: str = "User requested") -> dict:
        """Pause the current session"""
        try:
            if self.current_session_id:
                session = self.sessions.get(self.current_session_id)
                if session:
                    session["paused"] = True
                    session["pause_reason"] = reason
                    session["paused_at"] = datetime.utcnow().isoformat()
                    logger.info(f"Session paused: {self.current_session_id}")
                    return {
                        "success": True,
                        "session_id": self.current_session_id,
                        "reason": reason,
                        "paused_at": session["paused_at"]
                    }
            
            return {"success": False, "error": "No active session to pause"}
        except Exception as e:
            logger.error(f"Failed to pause session: {e}")
            return {"success": False, "error": str(e)}
    
    async def resume_session(self, session_id: str = None, device_context: str = None) -> dict:
        """Resume a paused session"""
        try:
            target_session_id = session_id or self.current_session_id
            
            if target_session_id and target_session_id in self.sessions:
                session = self.sessions[target_session_id]
                session["paused"] = False
                session["resumed_at"] = datetime.utcnow().isoformat()
                session["device_context"] = device_context
                self.current_session_id = target_session_id
                
                logger.info(f"Session resumed: {target_session_id}")
                return {
                    "success": True,
                    "session_id": target_session_id,
                    "resumed_at": session["resumed_at"],
                    "device_context": device_context
                }
            
            return {"success": False, "error": "Session not found or invalid"}
        except Exception as e:
            logger.error(f"Failed to resume session: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_conversation_message(self, message: str, context_type: str = "general") -> dict:
        """Process a conversation message"""
        try:
            # For now, treat conversation messages like ideas
            return await self.ingest_idea(
                idea=message,
                source="conversation",
                context=f"context_type: {context_type}"
            )
        except Exception as e:
            logger.error(f"Failed to process conversation message: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_session_stats(self, session_id: str, memories_created: int = 0, queries_made: int = 0) -> bool:
        """Update session statistics"""
        try:
            session = self.sessions.get(session_id)
            if session:
                session["memories_created"] += memories_created
                session["queries_made"] += queries_made
                session["last_accessed"] = datetime.utcnow().isoformat()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update session stats: {e}")
            return False
    
    async def list_sessions(self) -> list:
        """List all active sessions"""
        try:
            return list(self.sessions.values())
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                if self.current_session_id == session_id:
                    self.current_session_id = None
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False


# DEPRECATED: Use app.core.dependencies instead
# This module is kept for backward compatibility

# Import from the new centralized dependency injection system
from app.core.dependencies import (
    get_dashboard_service as _get_dashboard_service,
    get_git_service as _get_git_service,
    get_health_service as _get_health_service,
    get_memory_service as _get_memory_service,
    get_session_service as _get_session_service,
)


def get_dashboard_service() -> DashboardService:
    """Get dashboard service instance (DEPRECATED: use app.core.dependencies)"""
    import warnings
    warnings.warn(
        "app.services.service_factory.get_dashboard_service is deprecated. "
        "Use app.core.dependencies.get_dashboard_service instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_dashboard_service()


def get_git_service() -> GitService:
    """Get git service instance (DEPRECATED: use app.core.dependencies)"""
    import warnings
    warnings.warn(
        "app.services.service_factory.get_git_service is deprecated. "
        "Use app.core.dependencies.get_git_service instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_git_service()


def get_health_service() -> HealthService:
    """Get health service instance (DEPRECATED: use app.core.dependencies)"""
    import warnings
    warnings.warn(
        "app.services.service_factory.get_health_service is deprecated. "
        "Use app.core.dependencies.get_health_service instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_health_service()


def get_memory_service() -> MemoryService:
    """Get memory service instance (DEPRECATED: use app.core.dependencies)"""
    import warnings
    warnings.warn(
        "app.services.service_factory.get_memory_service is deprecated. "
        "Use app.core.dependencies.get_memory_service instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_memory_service()


def get_session_service() -> SessionService:
    """Get session service instance (DEPRECATED: use app.core.dependencies)"""
    import warnings
    warnings.warn(
        "app.services.service_factory.get_session_service is deprecated. "
        "Use app.core.dependencies.get_session_service instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_session_service()


class ServiceFactory:
    """Factory for creating service instances"""
    
    def __init__(self):
        self.database = None
        self.security_manager = None
    
    def set_database(self, database):
        """Set database instance for services"""
        self.database = database
    
    def set_security_manager(self, security_manager):
        """Set security manager instance for services"""
        self.security_manager = security_manager
    
    @staticmethod
    def get_dashboard_service() -> DashboardService:
        """Get dashboard service (DEPRECATED: use app.core.dependencies)"""
        return get_dashboard_service()
    
    @staticmethod
    def get_git_service() -> GitService:
        """Get git service (DEPRECATED: use app.core.dependencies)"""
        return get_git_service()
    
    @staticmethod
    def get_health_service() -> HealthService:
        """Get health service (DEPRECATED: use app.core.dependencies)"""
        return get_health_service()
    
    @staticmethod
    def get_memory_service() -> MemoryService:
        """Get memory service (DEPRECATED: use app.core.dependencies)"""
        return get_memory_service()
    
    @staticmethod
    def get_session_service() -> SessionService:
        """Get session service (DEPRECATED: use app.core.dependencies)"""
        return get_session_service()


# Singleton factory instance
_service_factory = None


def get_service_factory() -> ServiceFactory:
    """Get singleton instance of service factory"""
    global _service_factory
    if _service_factory is None:
        _service_factory = ServiceFactory()
    return _service_factory