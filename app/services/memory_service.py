"""
Memory Service - Handles all memory-related business logic.
Separates concerns from route handlers, making the code more testable and maintainable.

Enhanced with protocol-based interfaces and duck typing for maximum flexibility.
"""

from typing import Any, Optional, Union

from app.database import Database, get_database
from app.database_importance_schema import setup_importance_tracking_schema
from app.database_mock import MockDatabase
from app.services.importance_engine import ImportanceEngine, get_importance_engine
from app.services.monitoring import get_metrics_collector
from app.utils.logging_config import PerformanceLogger, get_logger
from app.utils.protocols import (
    Cacheable,
    MemoryLike,
    ProtocolChecker,
    Repository,
    Searchable,
    Service,
    call_if_callable,
    duck_type_check,
)

logger = get_logger(__name__)


def _is_real_database_with_pool(database: Union[Database, MockDatabase] | None) -> bool:
    """Check if database is a real Database instance with pool access."""
    if not database:
        return False
    # Check class name to avoid MockDatabase
    return (
        hasattr(database, "pool")
        and hasattr(database, "__class__")
        and database.__class__.__name__ == "Database"
        and getattr(database, "pool", None) is not None
    )


class MemoryService:
    """
    Enhanced Memory Service with Automated Importance Scoring and Protocol-Based Design

    Integrates the importance engine to automatically:
    - Track memory access patterns
    - Update importance scores based on usage
    - Log search result appearances
    - Calculate content quality scores

    Implements multiple protocols for maximum flexibility:
    - Service: Lifecycle management
    - Repository[MemoryLike]: CRUD operations
    - Searchable: Advanced search capabilities
    - Cacheable: Caching support
    """

    def __init__(self, database: Union[Database, MockDatabase] | None = None):
        self.database: Union[Database, MockDatabase] | None = database
        self.importance_engine: ImportanceEngine | None = None
        self._initialized = False
        self._running = False
        self._start_time: Optional[float] = None
        self._protocol_checker = ProtocolChecker()

    async def initialize(self):
        """Initialize the memory service and importance tracking"""
        if self._initialized:
            return

        with PerformanceLogger("memory_service_init", logger):
            try:
                logger.info("Initializing memory service", extra={
                    "service": "MemoryService",
                    "has_database": self.database is not None
                })

                # Use provided database or get default
                if not self.database:
                    self.database = await get_database()

                self.importance_engine = get_importance_engine(self.database)

                # Set up importance tracking schema if using real database
                schema_initialized = False
                if _is_real_database_with_pool(self.database):
                    # Type narrowing: we know this is a Database with pool
                    real_db = self.database  # type: ignore
                    schema_setup = await setup_importance_tracking_schema(real_db.pool)
                    if schema_setup:
                        logger.info("Importance tracking schema initialized", extra={
                            "component": "importance_tracking",
                            "database_type": "real"
                        })
                        schema_initialized = True
                    else:
                        logger.warning("Importance tracking schema setup failed", extra={
                            "component": "importance_tracking",
                            "database_type": "real"
                        })

                self._initialized = True
                logger.info("Memory service initialized successfully", extra={
                    "service": "MemoryService",
                    "importance_engine_available": self.importance_engine is not None,
                    "schema_initialized": schema_initialized,
                    "database_type": type(self.database).__name__
                })

            except Exception as e:
                logger.exception("Failed to initialize memory service", extra={
                    "service": "MemoryService",
                    "error_type": type(e).__name__,
                    "has_database": self.database is not None
                })
                # Fallback to basic service without importance tracking
                if not self.database:
                    self.database = await get_database()
                self._initialized = True

    async def store_memory(
        self,
        content: str,
        memory_type: str = "semantic",
        semantic_metadata: dict | None = None,
        episodic_metadata: dict | None = None,
        procedural_metadata: dict | None = None,
        importance_score: float | None = None,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> str:
        """
        Store a memory with automatic importance calculation
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        with PerformanceLogger("memory_storage", logger):
            logger.info("Storing memory", extra={
                "operation": "store_memory",
                "memory_type": memory_type,
                "content_length": len(content),
                "has_semantic_metadata": semantic_metadata is not None,
                "has_episodic_metadata": episodic_metadata is not None,
                "has_procedural_metadata": procedural_metadata is not None,
                "user_id": user_id
            })

            # Calculate initial importance score if not provided
            calculated_importance = False
            if importance_score is None and self.importance_engine:
                try:
                    # Use content quality score as initial importance
                    quality_score = self.importance_engine._calculate_content_quality_score(content)
                    type_weight = self.importance_engine.memory_type_weights.get(memory_type, 1.0)
                    importance_score = quality_score * type_weight
                    importance_score = max(0.3, min(1.0, importance_score))  # Reasonable bounds
                    calculated_importance = True

                    logger.debug("Calculated initial importance score", extra={
                        "operation": "calculate_importance",
                        "importance_score": importance_score,
                        "quality_score": quality_score,
                        "type_weight": type_weight,
                        "memory_type": memory_type
                    })
                except Exception as e:
                    logger.warning("Failed to calculate initial importance", extra={
                        "operation": "calculate_importance",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "memory_type": memory_type
                    })
                    importance_score = 0.5  # Default fallback

            try:
                # Store the memory
                memory_id = await self.database.store_memory(
                    content=content,
                    memory_type=memory_type,
                    semantic_metadata=semantic_metadata,
                    episodic_metadata=episodic_metadata,
                    procedural_metadata=procedural_metadata,
                    importance_score=importance_score or 0.5,
                    metadata=metadata,
                )

                # Record metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="store",
                    memory_type=memory_type,
                    success=True,
                    user_id=user_id
                )

                # Log the initial memory creation
                if self.importance_engine and memory_id:
                    try:
                        await self.importance_engine.log_memory_access(
                            memory_id=memory_id, access_type="creation", user_action="store_memory"
                        )
                    except Exception as e:
                        logger.warning("Failed to log memory creation", extra={
                            "operation": "log_memory_access",
                            "memory_id": memory_id,
                            "error": str(e)
                        })

                logger.info("Memory stored successfully", extra={
                    "operation": "store_memory",
                    "memory_id": memory_id,
                    "memory_type": memory_type,
                    "final_importance": importance_score or 0.5,
                    "importance_calculated": calculated_importance,
                    "user_id": user_id
                })

                return memory_id

            except Exception as e:
                # Record failed metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="store",
                    memory_type=memory_type,
                    success=False,
                    user_id=user_id
                )

                logger.exception("Failed to store memory", extra={
                    "operation": "store_memory",
                    "memory_type": memory_type,
                    "content_length": len(content),
                    "error_type": type(e).__name__,
                    "user_id": user_id
                })
                raise

    async def get_memory(self, memory_id: str, track_access: bool = True) -> dict[str, Any] | None:
        """
        Retrieve a memory and automatically track access for importance scoring
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        with PerformanceLogger("memory_retrieval", logger):
            logger.info("Retrieving memory", extra={
                "operation": "get_memory",
                "memory_id": memory_id,
                "track_access": track_access
            })

            try:
                memory = await self.database.get_memory(memory_id)

                # Record metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="get",
                    memory_type=memory.get("memory_type", "unknown") if memory else "unknown",
                    success=memory is not None
                )

                # Track access for importance calculation
                if memory and track_access and self.importance_engine:
                    try:
                        await self.importance_engine.log_memory_access(
                            memory_id=memory_id, access_type="retrieval", user_action="get_memory"
                        )
                        logger.debug("Tracked access for memory", extra={
                            "operation": "track_access",
                            "memory_id": memory_id,
                            "access_type": "retrieval"
                        })
                    except Exception as e:
                        logger.warning("Failed to track memory access", extra={
                            "operation": "track_access",
                            "memory_id": memory_id,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })

                if memory:
                    logger.info("Memory retrieved successfully", extra={
                        "operation": "get_memory",
                        "memory_id": memory_id,
                        "memory_type": memory.get("memory_type"),
                        "content_length": len(memory.get("content", ""))
                    })
                else:
                    logger.warning("Memory not found", extra={
                        "operation": "get_memory",
                        "memory_id": memory_id
                    })

                return memory

            except Exception as e:
                # Record failed metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="get",
                    memory_type="unknown",
                    success=False
                )

                logger.exception("Failed to retrieve memory", extra={
                    "operation": "get_memory",
                    "memory_id": memory_id,
                    "error_type": type(e).__name__
                })
                raise

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        importance_threshold: float | None = None,
        track_results: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search memories and track result appearances for importance scoring
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        with PerformanceLogger("memory_search", logger):
            logger.info("Searching memories", extra={
                "operation": "search_memories",
                "query_length": len(query),
                "limit": limit,
                "memory_types": memory_types,
                "importance_threshold": importance_threshold,
                "track_results": track_results
            })

            try:
                # Perform the search
                if hasattr(self.database, "contextual_search"):
                    results = await self.database.contextual_search(
                        query=query, limit=limit, memory_types=memory_types, importance_threshold=importance_threshold
                    )
                    search_method = "contextual_search"
                else:
                    results = await self.database.search_memories(query, limit)
                    search_method = "basic_search"

                # Record metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="search",
                    memory_type="mixed" if not memory_types or len(memory_types) > 1 else memory_types[0],
                    success=True
                )

                # Track search result appearances for importance calculation
                if results and track_results and self.importance_engine:
                    try:
                        for i, result in enumerate(results):
                            memory_id = result.get("id")
                            if memory_id:
                                # Log search result appearance
                                await self._log_search_result(
                                    memory_id=memory_id,
                                    query=query,
                                    position=i + 1,
                                    relevance_score=result.get("relevance_score", result.get("similarity", 0.0)),
                                )
                        logger.debug("Tracked search results", extra={
                            "operation": "track_search_results",
                            "query": query[:50] + "..." if len(query) > 50 else query,
                            "results_count": len(results)
                        })
                    except Exception as e:
                        logger.warning("Failed to track search results", extra={
                            "operation": "track_search_results",
                            "query": query[:50] + "..." if len(query) > 50 else query,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })

                logger.info("Memory search completed", extra={
                    "operation": "search_memories",
                    "search_method": search_method,
                    "results_count": len(results),
                    "query_length": len(query),
                    "limit": limit
                })

                return results

            except Exception as e:
                # Record failed metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_memory_operation(
                    operation_type="search",
                    memory_type="unknown",
                    success=False
                )

                logger.exception("Failed to search memories", extra={
                    "operation": "search_memories",
                    "query_length": len(query),
                    "limit": limit,
                    "error_type": type(e).__name__
                })
                raise

    async def _log_search_result(self, memory_id: str, query: str, position: int, relevance_score: float):
        """Log search result appearance for importance tracking"""
        if not self.importance_engine or not _is_real_database_with_pool(self.database):
            return

        try:
            real_db = self.database  # type: ignore
            async with real_db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO search_result_log
                        (memory_id, search_query, position, relevance_score)
                        VALUES ($1, $2, $3, $4)
                    """,
                    memory_id,
                    query,
                    position,
                    relevance_score,
                )

            logger.debug("Search result logged", extra={
                "operation": "log_search_result",
                "memory_id": memory_id,
                "position": position,
                "relevance_score": relevance_score
            })
        except Exception as e:
            logger.debug("Failed to log search result", extra={
                "operation": "log_search_result",
                "memory_id": memory_id,
                "position": position,
                "error": str(e),
                "error_type": type(e).__name__
            })

    async def click_search_result(self, memory_id: str, query: str) -> dict[str, Any] | None:
        """
        Handle search result click - tracks interaction and retrieves memory
        """
        await self.initialize()

        with PerformanceLogger("search_click", logger):
            logger.info("Processing search result click", extra={
                "operation": "click_search_result",
                "memory_id": memory_id,
                "query_length": len(query)
            })

            # Track the click for importance calculation
            if self.importance_engine:
                try:
                    await self.importance_engine.log_memory_access(
                        memory_id=memory_id, access_type="search_click", user_action="click_result"
                    )

                    # Update search result log to mark as clicked
                    if self.database and hasattr(self.database, "pool") and self.database.pool:
                        async with self.database.pool.acquire() as conn:
                            await conn.execute(
                                """
                                UPDATE search_result_log
                                SET clicked = TRUE, click_timestamp = NOW()
                                WHERE memory_id = $1 AND search_query = $2
                                  AND clicked = FALSE
                                ORDER BY search_timestamp DESC
                                LIMIT 1
                            """,
                                memory_id,
                                query,
                            )

                    logger.debug("Search click tracked", extra={
                        "operation": "track_search_click",
                        "memory_id": memory_id
                    })

                except Exception as e:
                    logger.warning("Failed to track search click", extra={
                        "operation": "track_search_click",
                        "memory_id": memory_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })

            # Retrieve and return the memory
            memory = await self.get_memory(memory_id, track_access=False)  # Already tracked above

            logger.info("Search click processed", extra={
                "operation": "click_search_result",
                "memory_id": memory_id,
                "memory_found": memory is not None
            })

            return memory

    async def add_user_feedback(
        self,
        memory_id: str,
        feedback_type: str,
        feedback_value: int | None = None,
        feedback_text: str | None = None,
    ) -> bool:
        """
        Add user feedback for a memory (upvote, downvote, save, etc.)
        This helps improve importance scoring accuracy
        """
        await self.initialize()

        if not self.importance_engine or not self.database or not hasattr(self.database, "pool"):
            logger.warning("User feedback not available", extra={
                "operation": "add_user_feedback",
                "memory_id": memory_id,
                "feedback_type": feedback_type,
                "reason": "importance_engine_or_database_unavailable"
            })
            return False

        with PerformanceLogger("user_feedback", logger):
            logger.info("Adding user feedback", extra={
                "operation": "add_user_feedback",
                "memory_id": memory_id,
                "feedback_type": feedback_type,
                "has_feedback_value": feedback_value is not None,
                "has_feedback_text": feedback_text is not None
            })

            try:
                if self.database.pool:
                    async with self.database.pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO user_feedback_log
                            (memory_id, feedback_type, feedback_value, feedback_text)
                            VALUES ($1, $2, $3, $4)
                        """,
                            memory_id,
                            feedback_type,
                            feedback_value,
                            feedback_text,
                        )

                # Log as access with user feedback
                await self.importance_engine.log_memory_access(
                    memory_id=memory_id, access_type="user_feedback", user_action=feedback_type
                )

                logger.info("User feedback added successfully", extra={
                    "operation": "add_user_feedback",
                    "memory_id": memory_id,
                    "feedback_type": feedback_type,
                    "feedback_value": feedback_value
                })
                return True

            except Exception as e:
                logger.exception("Failed to add user feedback", extra={
                    "operation": "add_user_feedback",
                    "memory_id": memory_id,
                    "feedback_type": feedback_type,
                    "error_type": type(e).__name__
                })
                return False

    async def get_importance_analytics(self) -> dict[str, Any]:
        """Get comprehensive importance analytics"""
        await self.initialize()

        if not self.importance_engine:
            logger.warning("Importance analytics unavailable", extra={
                "operation": "get_importance_analytics",
                "reason": "importance_engine_not_available"
            })
            return {"error": "Importance engine not available"}

        with PerformanceLogger("importance_analytics", logger):
            logger.info("Generating importance analytics", extra={
                "operation": "get_importance_analytics"
            })

            try:
                analytics = await self.importance_engine.get_importance_analytics()

                logger.info("Importance analytics generated", extra={
                    "operation": "get_importance_analytics",
                    "analytics_keys": list(analytics.keys()) if isinstance(analytics, dict) else "non_dict"
                })

                return analytics

            except Exception as e:
                logger.exception("Failed to generate importance analytics", extra={
                    "operation": "get_importance_analytics",
                    "error_type": type(e).__name__
                })
                return {"error": str(e)}

    async def recalculate_importance_scores(self, limit: int = 100) -> dict[str, Any]:
        """
        Manually trigger importance score recalculation
        Useful for maintenance or after configuration changes
        """
        await self.initialize()

        if not self.importance_engine:
            logger.warning("Importance recalculation unavailable", extra={
                "operation": "recalculate_importance_scores",
                "reason": "importance_engine_not_available",
                "limit": limit
            })
            return {"error": "Importance engine not available"}

        with PerformanceLogger("importance_recalculation", logger):
            logger.info("Starting batch importance recalculation", extra={
                "operation": "recalculate_importance_scores",
                "limit": limit
            })

            try:
                result = await self.importance_engine.batch_recalculate_importance(limit)

                logger.info("Importance recalculation completed", extra={
                    "operation": "recalculate_importance_scores",
                    "limit": limit,
                    "result": result
                })

                return result

            except Exception as e:
                logger.exception("Failed to recalculate importance scores", extra={
                    "operation": "recalculate_importance_scores",
                    "limit": limit,
                    "error_type": type(e).__name__
                })
                return {"error": str(e)}

    async def get_memory_importance_breakdown(self, memory_id: str) -> dict[str, Any]:
        """
        Get detailed importance score breakdown for a specific memory
        Useful for debugging and understanding why certain memories are ranked highly
        """
        await self.initialize()

        if not self.importance_engine:
            logger.warning("Importance breakdown unavailable", extra={
                "operation": "get_memory_importance_breakdown",
                "memory_id": memory_id,
                "reason": "importance_engine_not_available"
            })
            return {"error": "Importance engine not available"}

        with PerformanceLogger("importance_breakdown", logger):
            logger.info("Generating importance breakdown", extra={
                "operation": "get_memory_importance_breakdown",
                "memory_id": memory_id
            })

            try:
                # Get current memory data
                memory = await self.database.get_memory(memory_id)
                if not memory:
                    logger.warning("Memory not found for importance breakdown", extra={
                        "operation": "get_memory_importance_breakdown",
                        "memory_id": memory_id
                    })
                    return {"error": "Memory not found"}

                # Calculate detailed importance score
                score = await self.importance_engine.calculate_importance_score(
                    memory_id=memory_id,
                    content=memory["content"],
                    memory_type=memory["memory_type"],
                    current_score=memory.get("importance_score", 0.5),
                )

                # Get importance history
                if hasattr(self.database, "pool"):
                    from app.database_importance_schema import get_memory_importance_history

                    history = await get_memory_importance_history(self.database.pool, memory_id, 10)
                else:
                    history = []

                breakdown = {
                    "memory_id": memory_id,
                    "current_score": score.final_score,
                    "breakdown": {
                        "frequency_score": score.frequency_score,
                        "recency_score": score.recency_score,
                        "search_relevance_score": score.search_relevance_score,
                        "content_quality_score": score.content_quality_score,
                        "type_weight": score.type_weight,
                        "decay_factor": score.decay_factor,
                        "confidence": score.confidence,
                    },
                    "explanation": score.explanation,
                    "history": history,
                }

                logger.info("Importance breakdown generated", extra={
                    "operation": "get_memory_importance_breakdown",
                    "memory_id": memory_id,
                    "final_score": score.final_score,
                    "history_count": len(history)
                })

                return breakdown

            except Exception as e:
                logger.exception("Failed to get importance breakdown", extra={
                    "operation": "get_memory_importance_breakdown",
                    "memory_id": memory_id,
                    "error_type": type(e).__name__
                })
                return {"error": str(e)}

    async def get_high_importance_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get memories with highest importance scores"""
        await self.initialize()

        with PerformanceLogger("high_importance_memories", logger):
            logger.info("Retrieving high importance memories", extra={
                "operation": "get_high_importance_memories",
                "limit": limit
            })

            try:
                if hasattr(self.database, "pool"):
                    async with self.database.pool.acquire() as conn:
                        memories = await conn.fetch(
                            """
                            SELECT id, content[1:200] as content_preview, memory_type,
                                   importance_score, access_count, last_accessed,
                                   created_at
                            FROM memories
                            ORDER BY importance_score DESC, access_count DESC
                            LIMIT $1
                        """,
                            limit,
                        )

                        result = [dict(memory) for memory in memories]

                        logger.info("High importance memories retrieved", extra={
                            "operation": "get_high_importance_memories",
                            "limit": limit,
                            "found_count": len(result)
                        })

                        return result
                else:
                    # Fallback for mock database
                    logger.warning("High importance memories unavailable", extra={
                        "operation": "get_high_importance_memories",
                        "limit": limit,
                        "reason": "mock_database_no_pool"
                    })
                    return []

            except Exception as e:
                logger.exception("Failed to get high importance memories", extra={
                    "operation": "get_high_importance_memories",
                    "limit": limit,
                    "error_type": type(e).__name__
                })
                return []

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> dict[str, Any]:
        """Clean up old access logs to prevent database bloat"""
        await self.initialize()

        if not hasattr(self.database, "pool"):
            logger.warning("Log cleanup unavailable", extra={
                "operation": "cleanup_old_logs",
                "days_to_keep": days_to_keep,
                "reason": "database_pool_not_available"
            })
            return {"error": "Database pool not available"}

        with PerformanceLogger("log_cleanup", logger):
            logger.info("Starting log cleanup", extra={
                "operation": "cleanup_old_logs",
                "days_to_keep": days_to_keep
            })

            try:
                from app.database_importance_schema import cleanup_old_access_logs

                result = await cleanup_old_access_logs(self.database.pool, days_to_keep)

                logger.info("Log cleanup completed", extra={
                    "operation": "cleanup_old_logs",
                    "days_to_keep": days_to_keep,
                    "result": result
                })

                return result
            except Exception as e:
                logger.exception("Failed to cleanup old logs", extra={
                    "operation": "cleanup_old_logs",
                    "days_to_keep": days_to_keep,
                    "error_type": type(e).__name__
                })
                return {"error": str(e)}

    # ============================================================================
    # Protocol Implementations - Service Protocol
    # ============================================================================

    async def start(self) -> None:
        """Start the memory service (Service protocol)."""
        if self._running:
            return

        import time
        self._start_time = time.time()
        self._running = True

        await self.initialize()

        logger.info("Memory service started", extra={
            "service": "MemoryService",
            "start_time": self._start_time
        })

    async def stop(self) -> None:
        """Stop the memory service (Service protocol)."""
        if not self._running:
            return

        self._running = False

        # Cleanup any resources
        await call_if_callable(self.database, 'close')

        logger.info("Memory service stopped", extra={
            "service": "MemoryService",
            "was_running": True
        })

    def is_running(self) -> bool:
        """Check if service is running (Service protocol)."""
        return self._running

    async def health_check(self) -> dict[str, Any]:
        """Perform health check (Service protocol)."""
        import time

        status = "healthy"
        issues = []

        # Check database connectivity
        try:
            if self.database:
                # Test database connection
                if hasattr(self.database, 'pool') and self.database.pool:
                    async with self.database.pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                elif duck_type_check(self.database, ['get_memory']):
                    # Mock database - just check if methods exist
                    pass
                else:
                    issues.append("Database not properly initialized")
                    status = "degraded"
            else:
                issues.append("No database configured")
                status = "degraded"
        except Exception as e:
            issues.append(f"Database connectivity issue: {e}")
            status = "unhealthy"

        # Check importance engine
        if not self.importance_engine:
            issues.append("Importance engine not available")
            if status == "healthy":
                status = "degraded"

        uptime = time.time() - self._start_time if self._start_time else 0

        return {
            "service": "MemoryService",
            "status": status,
            "running": self._running,
            "uptime_seconds": uptime,
            "database_available": self.database is not None,
            "importance_engine_available": self.importance_engine is not None,
            "issues": issues,
            "timestamp": time.time()
        }

    # ============================================================================
    # Protocol Implementations - Repository Protocol
    # ============================================================================

    async def save(self, entity: MemoryLike) -> MemoryLike:
        """Save memory entity (Repository protocol)."""
        # Extract data from entity using duck typing
        content = getattr(entity, 'content', '')
        memory_type = getattr(entity, 'memory_type', 'semantic')
        importance_score = getattr(entity, 'importance_score', 0.5)

        # Get additional attributes if available
        metadata = getattr(entity, 'metadata', {}) if hasattr(entity, 'metadata') else {}

        memory_id = await self.store_memory(
            content=content,
            memory_type=memory_type,
            importance_score=importance_score,
            metadata=metadata
        )

        # Update entity with new ID if it didn't have one
        if hasattr(entity, 'id') and not entity.id:
            if hasattr(entity, '__setattr__'):
                entity.id = memory_id

        return entity

    async def find_by_id(self, entity_id: str) -> Optional[MemoryLike]:
        """Find memory by ID (Repository protocol)."""
        memory_data = await self.get_memory(entity_id)

        if memory_data:
            # Create a MemoryLike object from the data using duck typing
            from app.utils.protocols import UniversalMemory

            return UniversalMemory(
                id=memory_data.get('id', entity_id),
                content=memory_data.get('content', ''),
                memory_type=memory_data.get('memory_type', 'semantic'),
                importance_score=memory_data.get('importance_score', 0.5),
                created_at=memory_data.get('created_at', 0.0),
                updated_at=memory_data.get('updated_at'),
                embedding=memory_data.get('embedding'),
                metadata=memory_data.get('metadata', {})
            )

        return None

    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> list[MemoryLike]:
        """Find all memories (Repository protocol)."""
        await self.initialize()

        if not self.database:
            return []

        try:
            # Use database method if available
            memories_data = await self.database.get_all_memories(
                limit=limit or 100,
                offset=offset
            )

            # Convert to MemoryLike objects
            from app.utils.protocols import UniversalMemory

            memories = []
            for data in memories_data:
                memory = UniversalMemory(
                    id=data.get('id', ''),
                    content=data.get('content', ''),
                    memory_type=data.get('memory_type', 'semantic'),
                    importance_score=data.get('importance_score', 0.5),
                    created_at=data.get('created_at', 0.0),
                    updated_at=data.get('updated_at'),
                    embedding=data.get('embedding'),
                    metadata=data.get('metadata', {})
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Failed to find all memories: {e}")
            return []

    async def delete(self, entity_id: str) -> bool:
        """Delete memory by ID (Repository protocol)."""
        await self.initialize()

        if not self.database:
            return False

        try:
            return await self.database.delete_memory(entity_id)
        except Exception as e:
            logger.error(f"Failed to delete memory {entity_id}: {e}")
            return False

    async def exists(self, entity_id: str) -> bool:
        """Check if memory exists (Repository protocol)."""
        memory = await self.find_by_id(entity_id)
        return memory is not None

    # ============================================================================
    # Protocol Implementations - Searchable Protocol
    # ============================================================================

    async def search(self, query: str, limit: int = 10) -> list[Any]:
        """Search memories (Searchable protocol)."""
        return await self.search_memories(query, limit)

    def supports_filters(self) -> bool:
        """Check if advanced filtering is supported (Searchable protocol)."""
        return hasattr(self.database, 'contextual_search')

    async def search_with_filters(self, query: str, filters: dict[str, Any]) -> list[Any]:
        """Search with filters (Searchable protocol)."""
        await self.initialize()

        if not self.database or not hasattr(self.database, 'contextual_search'):
            # Fallback to basic search
            return await self.search(query, filters.get('limit', 10))

        try:
            return await self.database.contextual_search(
                query=query,
                limit=filters.get('limit', 10),
                memory_types=filters.get('memory_types'),
                importance_threshold=filters.get('importance_threshold'),
                timeframe=filters.get('timeframe'),
                include_archived=filters.get('include_archived', False)
            )
        except Exception as e:
            logger.error(f"Failed filtered search: {e}")
            return []

    # ============================================================================
    # Protocol Implementations - Cacheable Protocol
    # ============================================================================

    @property
    def cache_key(self) -> str:
        """Generate cache key (Cacheable protocol)."""
        return f"memory_service:{id(self)}"

    @property
    def cache_ttl(self) -> int:
        """Cache TTL in seconds (Cacheable protocol)."""
        return 300  # 5 minutes

    def is_cache_valid(self) -> bool:
        """Check cache validity (Cacheable protocol)."""
        return self._running and self._initialized

    # ============================================================================
    # Protocol Validation and Introspection
    # ============================================================================

    def validate_protocols(self) -> dict[str, dict[str, Any]]:
        """Validate that this service properly implements its protocols."""
        protocols_to_check = [Service, Repository, Searchable, Cacheable]

        return self._protocol_checker.validate_protocol_implementations(
            self, *protocols_to_check
        )

    def get_supported_protocols(self) -> list[str]:
        """Get list of protocols this service supports."""
        protocols = []

        if self._protocol_checker.implements_protocol(self, Service):
            protocols.append("Service")
        if self._protocol_checker.implements_protocol(self, Repository):
            protocols.append("Repository[MemoryLike]")
        if self._protocol_checker.implements_protocol(self, Searchable):
            protocols.append("Searchable")
        if self._protocol_checker.implements_protocol(self, Cacheable):
            protocols.append("Cacheable")

        return protocols

    def demonstrate_duck_typing(self, obj: Any) -> dict[str, Any]:
        """Demonstrate duck typing capabilities with any object."""
        results = {
            "object_type": type(obj).__name__,
            "duck_typing_results": {}
        }

        # Test for MemoryLike duck typing
        memory_methods = ['content', 'memory_type', 'importance_score']
        memory_duck = duck_type_check(obj, [], memory_methods)
        results["duck_typing_results"]["MemoryLike"] = memory_duck

        # Test for Service-like duck typing
        service_methods = ['start', 'stop', 'is_running', 'health_check']
        service_duck = duck_type_check(obj, service_methods, [])
        results["duck_typing_results"]["ServiceLike"] = service_duck

        # Test for callable methods
        callable_methods = []
        for method in service_methods + ['search', 'find_by_id', 'save']:
            if hasattr(obj, method) and callable(getattr(obj, method)):
                callable_methods.append(method)

        results["available_methods"] = callable_methods

        return results


# ============================================================================
# Memory Service Factory with Protocol Validation
# ============================================================================

class MemoryServiceFactory:
    """Factory for creating memory services with protocol validation."""

    @staticmethod
    async def create_service(
        database: Union[Database, MockDatabase] = None,
        validate_protocols: bool = True
    ) -> MemoryService:
        """Create and initialize a memory service."""
        service = MemoryService(database)
        await service.start()

        if validate_protocols:
            validation_results = service.validate_protocols()

            for protocol_name, result in validation_results.items():
                if not result['implements']:
                    logger.warning(f"Service does not fully implement {result['protocol_name']}", extra={
                        "missing_methods": result['missing_methods']
                    })

        return service

    @staticmethod
    def create_protocol_adapter(target_service: Any) -> Any:
        """Create a protocol adapter for any service-like object."""
        from app.utils.protocols import ProtocolAdapter

        adapter = ProtocolAdapter(target_service)

        # Add missing Service protocol methods if needed
        if not duck_type_check(target_service, ['start'], []):
            adapter.add_adapter(Service, 'start', lambda: logger.info("Service started (adapted)"))

        if not duck_type_check(target_service, ['stop'], []):
            adapter.add_adapter(Service, 'stop', lambda: logger.info("Service stopped (adapted)"))

        if not duck_type_check(target_service, ['is_running'], []):
            adapter.add_adapter(Service, 'is_running', lambda: True)

        if not duck_type_check(target_service, ['health_check'], []):
            adapter.add_adapter(Service, 'health_check', lambda: {"status": "adapted", "healthy": True})

        return adapter
