"""
Memory Service - Handles all memory-related business logic.
Separates concerns from route handlers, making the code more testable and maintainable.
"""

import logging
from typing import Any, Optional, Union

from app.database import Database, get_database
from app.database_importance_schema import setup_importance_tracking_schema
from app.database_mock import MockDatabase
from app.importance_engine import ImportanceEngine, get_importance_engine

logger = logging.getLogger(__name__)


def _is_real_database_with_pool(database: Optional[Union[Database, MockDatabase]]) -> bool:
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
    Enhanced Memory Service with Automated Importance Scoring

    Integrates the importance engine to automatically:
    - Track memory access patterns
    - Update importance scores based on usage
    - Log search result appearances
    - Calculate content quality scores
    """

    def __init__(self, database: Optional[Union[Database, MockDatabase]] = None):
        self.database: Optional[Union[Database, MockDatabase]] = database
        self.importance_engine: Optional[ImportanceEngine] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the memory service and importance tracking"""
        if self._initialized:
            return

        try:
            # Use provided database or get default
            if not self.database:
                self.database = await get_database()

            self.importance_engine = get_importance_engine(self.database)

            # Set up importance tracking schema if using real database
            if _is_real_database_with_pool(self.database):
                # Type narrowing: we know this is a Database with pool
                real_db = self.database  # type: ignore
                schema_setup = await setup_importance_tracking_schema(real_db.pool)
                if schema_setup:
                    logger.info("✅ Importance tracking schema initialized")
                else:
                    logger.warning("⚠️ Importance tracking schema setup failed")

            self._initialized = True
            logger.info("🧠 Memory service with importance tracking initialized")

        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            # Fallback to basic service without importance tracking
            if not self.database:
                self.database = await get_database()
            self._initialized = True

    async def store_memory(
        self,
        content: str,
        memory_type: str = "semantic",
        semantic_metadata: Optional[dict] = None,
        episodic_metadata: Optional[dict] = None,
        procedural_metadata: Optional[dict] = None,
        importance_score: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a memory with automatic importance calculation
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        # Calculate initial importance score if not provided
        if importance_score is None and self.importance_engine:
            try:
                # Use content quality score as initial importance
                quality_score = self.importance_engine._calculate_content_quality_score(content)
                type_weight = self.importance_engine.memory_type_weights.get(memory_type, 1.0)
                importance_score = quality_score * type_weight
                importance_score = max(0.3, min(1.0, importance_score))  # Reasonable bounds
                logger.debug(f"Calculated initial importance score: {importance_score:.3f}")
            except Exception as e:
                logger.warning(f"Failed to calculate initial importance: {e}")
                importance_score = 0.5  # Default fallback

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

        # Log the initial memory creation
        if self.importance_engine and memory_id:
            try:
                await self.importance_engine.log_memory_access(
                    memory_id=memory_id, access_type="creation", user_action="store_memory"
                )
            except Exception as e:
                logger.warning(f"Failed to log memory creation: {e}")

        return memory_id

    async def get_memory(self, memory_id: str, track_access: bool = True) -> Optional[dict[str, Any]]:
        """
        Retrieve a memory and automatically track access for importance scoring
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        memory = await self.database.get_memory(memory_id)

        # Track access for importance calculation
        if memory and track_access and self.importance_engine:
            try:
                await self.importance_engine.log_memory_access(
                    memory_id=memory_id, access_type="retrieval", user_action="get_memory"
                )
                logger.debug(f"Tracked access for memory {memory_id}")
            except Exception as e:
                logger.warning(f"Failed to track memory access: {e}")

        return memory

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: Optional[list[str]] = None,
        importance_threshold: Optional[float] = None,
        track_results: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search memories and track result appearances for importance scoring
        """
        await self.initialize()

        if not self.database:
            raise RuntimeError("Database not initialized")

        # Perform the search
        if hasattr(self.database, "contextual_search"):
            results = await self.database.contextual_search(
                query=query, limit=limit, memory_types=memory_types, importance_threshold=importance_threshold
            )
        else:
            results = await self.database.search_memories(query, limit)

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
                logger.debug(f"Tracked {len(results)} search results for query: {query}")
            except Exception as e:
                logger.warning(f"Failed to track search results: {e}")

        return results

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
        except Exception as e:
            logger.debug(f"Failed to log search result: {e}")

    async def click_search_result(self, memory_id: str, query: str) -> Optional[dict[str, Any]]:
        """
        Handle search result click - tracks interaction and retrieves memory
        """
        await self.initialize()

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

            except Exception as e:
                logger.warning(f"Failed to track search click: {e}")

        # Retrieve and return the memory
        return await self.get_memory(memory_id, track_access=False)  # Already tracked above

    async def add_user_feedback(
        self,
        memory_id: str,
        feedback_type: str,
        feedback_value: Optional[int] = None,
        feedback_text: Optional[str] = None,
    ) -> bool:
        """
        Add user feedback for a memory (upvote, downvote, save, etc.)
        This helps improve importance scoring accuracy
        """
        await self.initialize()

        if not self.importance_engine or not self.database or not hasattr(self.database, "pool"):
            return False

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

            logger.info(f"Added user feedback for {memory_id}: {feedback_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to add user feedback: {e}")
            return False

    async def get_importance_analytics(self) -> dict[str, Any]:
        """Get comprehensive importance analytics"""
        await self.initialize()

        if not self.importance_engine:
            return {"error": "Importance engine not available"}

        return await self.importance_engine.get_importance_analytics()

    async def recalculate_importance_scores(self, limit: int = 100) -> dict[str, Any]:
        """
        Manually trigger importance score recalculation
        Useful for maintenance or after configuration changes
        """
        await self.initialize()

        if not self.importance_engine:
            return {"error": "Importance engine not available"}

        logger.info(f"Starting batch importance recalculation for {limit} memories")
        result = await self.importance_engine.batch_recalculate_importance(limit)
        logger.info(f"Importance recalculation completed: {result}")

        return result

    async def get_memory_importance_breakdown(self, memory_id: str) -> dict[str, Any]:
        """
        Get detailed importance score breakdown for a specific memory
        Useful for debugging and understanding why certain memories are ranked highly
        """
        await self.initialize()

        if not self.importance_engine:
            return {"error": "Importance engine not available"}

        try:
            # Get current memory data
            memory = await self.database.get_memory(memory_id)
            if not memory:
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

            return {
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

        except Exception as e:
            logger.error(f"Failed to get importance breakdown for {memory_id}: {e}")
            return {"error": str(e)}

    async def get_high_importance_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get memories with highest importance scores"""
        await self.initialize()

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

                    return [dict(memory) for memory in memories]
            else:
                # Fallback for mock database
                return []

        except Exception as e:
            logger.error(f"Failed to get high importance memories: {e}")
            return []

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> dict[str, Any]:
        """Clean up old access logs to prevent database bloat"""
        await self.initialize()

        if not hasattr(self.database, "pool"):
            return {"error": "Database pool not available"}

        try:
            from app.database_importance_schema import cleanup_old_access_logs

            result = await cleanup_old_access_logs(self.database.pool, days_to_keep)
            logger.info(f"Log cleanup completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return {"error": str(e)}
