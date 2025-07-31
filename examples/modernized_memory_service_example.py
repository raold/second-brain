"""
Example: Modernized Memory Service with structured logging.

This shows how to migrate the memory service to use the new logging system.
This is an EXAMPLE file - not for production use.
"""

from typing import Union

from app.database import Database
from app.database_mock import MockDatabase
from app.models.memory import Memory
from app.utils.logging_config import LogContext, PerformanceLogger, get_logger

logger = get_logger(__name__)


class ModernizedMemoryService:
    """
    Example of Memory Service with modern structured logging.

    Key improvements:
    - Structured logging with context
    - Performance monitoring
    - Request tracing
    - Better error handling
    """

    def __init__(self, database: Union[Database, MockDatabase] | None = None):
        self.database = database
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory service with logging."""
        if self._initialized:
            return

        logger.info("Initializing memory service", extra={
            "service": "MemoryService",
            "database_type": type(self.database).__name__
        })

        try:
            with PerformanceLogger("memory_service_init", logger):
                # Database initialization logic here
                await self._setup_database_schema()
                self._initialized = True

            logger.info("Memory service initialized successfully", extra={
                "service": "MemoryService",
                "initialization_time_ms": 150  # Would be captured by PerformanceLogger
            })

        except Exception as e:
            logger.exception("Failed to initialize memory service", extra={
                "service": "MemoryService",
                "error_type": type(e).__name__,
                "database_available": self.database is not None
            })
            raise

    async def create_memory(
        self,
        memory: Memory,
        user_id: str = None,
        request_id: str = None
    ) -> Memory:
        """Create a new memory with full logging context."""

        with LogContext(
            operation="create_memory",
            user_id=user_id,
            request_id=request_id
        ):
            logger.info("Creating memory", extra={
                "memory_type": memory.memory_type.value,
                "importance": memory.importance,
                "has_tags": bool(memory.tags),
                "tag_count": len(memory.tags) if memory.tags else 0,
                "content_length": len(memory.content)
            })

            try:
                with PerformanceLogger("database_insert", logger):
                    # Database insertion logic
                    created_memory = await self._insert_memory(memory)

                # Success logging with structured data
                logger.info("Memory created successfully", extra={
                    "memory_id": str(created_memory.id),
                    "memory_type": created_memory.memory_type.value,
                    "final_importance": created_memory.importance,
                    "embedding_generated": created_memory.embedding is not None
                })

                return created_memory

            except ValueError as e:
                logger.warning("Memory creation validation failed", extra={
                    "error": str(e),
                    "validation_type": "business_logic",
                    "memory_type": memory.memory_type.value
                })
                raise

            except Exception as e:
                logger.exception("Database error during memory creation", extra={
                    "error_type": type(e).__name__,
                    "memory_type": memory.memory_type.value,
                    "database_available": self.database is not None
                })
                raise

    async def search_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        request_id: str = None
    ) -> list[Memory]:
        """Search memories with performance and relevance logging."""

        with LogContext(
            operation="search_memories",
            user_id=user_id,
            request_id=request_id
        ):
            logger.info("Starting memory search", extra={
                "query_length": len(query),
                "limit": limit,
                "search_type": "semantic"
            })

            try:
                with PerformanceLogger("memory_search", logger):
                    # Search logic here
                    results = await self._execute_search(query, limit)

                    # Log search metrics
                    logger.info("Memory search completed", extra={
                        "results_count": len(results),
                        "query_length": len(query),
                        "average_relevance": self._calculate_average_relevance(results),
                        "top_result_score": results[0].relevance_score if results else 0
                    })

                    # Log search analytics for later analysis
                    if results:
                        logger.debug("Search result details", extra={
                            "result_memory_types": [r.memory_type.value for r in results[:5]],
                            "result_importances": [r.importance for r in results[:5]],
                            "result_ids": [str(r.id) for r in results[:3]]
                        })
                    else:
                        logger.warning("Search returned no results", extra={
                            "query": query[:100],  # Truncate for logging
                            "user_memory_count": await self._get_user_memory_count(user_id)
                        })

                return results

            except Exception as e:
                logger.exception("Memory search failed", extra={
                    "query_length": len(query),
                    "error_type": type(e).__name__,
                    "search_parameters": {
                        "limit": limit,
                        "has_user_id": bool(user_id)
                    }
                })
                raise

    async def get_memory(self, memory_id: str, user_id: str = None) -> Memory | None:
        """Get memory by ID with access logging."""

        with LogContext(operation="get_memory", user_id=user_id):
            logger.debug("Retrieving memory by ID", extra={
                "memory_id": memory_id
            })

            try:
                with PerformanceLogger("memory_lookup", logger):
                    memory = await self._fetch_memory_by_id(memory_id)

                if memory:
                    logger.info("Memory retrieved successfully", extra={
                        "memory_id": memory_id,
                        "memory_type": memory.memory_type.value,
                        "importance": memory.importance,
                        "access_count": getattr(memory, 'access_count', 0) + 1
                    })

                    # Update access tracking
                    await self._track_memory_access(memory_id, user_id)

                else:
                    logger.warning("Memory not found", extra={
                        "memory_id": memory_id,
                        "user_has_access": await self._user_has_access(user_id, memory_id)
                    })

                return memory

            except Exception as e:
                logger.exception("Failed to retrieve memory", extra={
                    "memory_id": memory_id,
                    "error_type": type(e).__name__
                })
                raise

    async def delete_memory(self, memory_id: str, user_id: str = None) -> bool:
        """Delete memory with audit logging."""

        with LogContext(operation="delete_memory", user_id=user_id):
            # First get memory for audit log
            memory = await self.get_memory(memory_id, user_id)
            if not memory:
                logger.warning("Attempted to delete non-existent memory", extra={
                    "memory_id": memory_id
                })
                return False

            logger.info("Deleting memory", extra={
                "memory_id": memory_id,
                "memory_type": memory.memory_type.value,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat()
            })

            try:
                with PerformanceLogger("memory_deletion", logger):
                    success = await self._delete_memory_by_id(memory_id)

                if success:
                    logger.info("Memory deleted successfully", extra={
                        "memory_id": memory_id,
                        "cascade_deletions": await self._get_cascade_count(memory_id)
                    })
                else:
                    logger.error("Memory deletion failed", extra={
                        "memory_id": memory_id,
                        "database_error": "Unknown"
                    })

                return success

            except Exception as e:
                logger.exception("Database error during memory deletion", extra={
                    "memory_id": memory_id,
                    "error_type": type(e).__name__
                })
                raise

    # Private helper methods (stubs for example)

    async def _setup_database_schema(self):
        """Setup database schema."""
        pass

    async def _insert_memory(self, memory: Memory) -> Memory:
        """Insert memory into database."""
        return memory  # Stub

    async def _execute_search(self, query: str, limit: int) -> list[Memory]:
        """Execute search query."""
        return []  # Stub

    async def _fetch_memory_by_id(self, memory_id: str) -> Memory | None:
        """Fetch memory by ID."""
        return None  # Stub

    async def _delete_memory_by_id(self, memory_id: str) -> bool:
        """Delete memory by ID."""
        return True  # Stub

    async def _track_memory_access(self, memory_id: str, user_id: str):
        """Track memory access for analytics."""
        logger.debug("Tracking memory access", extra={
            "memory_id": memory_id,
            "access_type": "retrieval"
        })

    async def _get_user_memory_count(self, user_id: str) -> int:
        """Get total memory count for user."""
        return 0  # Stub

    async def _user_has_access(self, user_id: str, memory_id: str) -> bool:
        """Check if user has access to memory."""
        return True  # Stub

    async def _get_cascade_count(self, memory_id: str) -> int:
        """Get count of cascade deletions."""
        return 0  # Stub

    def _calculate_average_relevance(self, results: list[Memory]) -> float:
        """Calculate average relevance score."""
        if not results:
            return 0.0
        return sum(getattr(r, 'relevance_score', 0.5) for r in results) / len(results)


# Usage example for API endpoints
async def create_memory_endpoint_example(request, memory_data, current_user):
    """Example of using modernized service in API endpoint."""

    # Extract request context
    request_id = request.headers.get("X-Request-ID", "unknown")
    user_id = current_user["user_id"]

    # Use service with context
    service = ModernizedMemoryService()

    try:
        memory = await service.create_memory(
            memory=memory_data,
            user_id=user_id,
            request_id=request_id
        )

        return {"status": "success", "memory_id": str(memory.id)}

    except Exception:
        # Exception already logged by service
        logger.error("API endpoint failed", extra={
            "endpoint": "create_memory",
            "user_id": user_id,
            "request_id": request_id
        })
        raise
