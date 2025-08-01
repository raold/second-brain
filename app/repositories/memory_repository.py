import json
from datetime import datetime
from typing import Any

from app.models.memory import Memory, MemoryType
from app.utils.logging_config import get_logger

"""
Memory repository implementation following Repository pattern.

Provides data access abstraction for Memory entities, separating
database concerns from business logic.
"""

from abc import abstractmethod

import asyncpg

from app.models.memory import MemoryMetrics
from app.models.search import SearchCriteria
from app.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class MemoryRepository(BaseRepository[Memory]):
    """
    Abstract repository interface for Memory entities.

    Defines the contract for memory data access operations,
    enabling different storage implementations.
    """

    @abstractmethod
    async def save(self, memory: Memory) -> str:
        """Save a memory and return its ID."""
        pass

    @abstractmethod
    async def update(self, memory: Memory) -> bool:
        """Update an existing memory."""
        pass

    @abstractmethod
    async def search_by_content(
        self,
        query: str,
        limit: int = 50,
        memory_type: MemoryType | None = None,
        user_id: str | None = None,
    ) -> list[Memory]:
        """Search memories by content similarity."""
        pass

    @abstractmethod
    async def search_by_criteria(self, criteria: SearchCriteria) -> list[Memory]:
        """Search memories using complex criteria."""
        pass

    @abstractmethod
    async def find_by_user(self, user_id: str, limit: int = 100) -> list[Memory]:
        """Find all memories for a specific user."""
        pass

    @abstractmethod
    async def find_related(self, memory_id: str, limit: int = 10) -> list[Memory]:
        """Find memories related to the given memory."""
        pass

    @abstractmethod
    async def get_metrics(self, user_id: str | None = None) -> MemoryMetrics:
        """Get memory statistics and metrics."""
        pass

    @abstractmethod
    async def update_importance_score(self, memory_id: str, score: float) -> bool:
        """Update the importance score of a memory."""
        pass

    @abstractmethod
    async def mark_as_accessed(self, memory_id: str) -> None:
        """Mark memory as accessed for importance tracking."""
        pass


class PostgreSQLMemoryRepository(MemoryRepository):
    """
    PostgreSQL implementation of the Memory repository.

    Provides concrete data access operations using PostgreSQL
    with proper SQL abstraction and error handling.
    """

    @property
    def table_name(self) -> str:
        return "memories"

    async def _map_row_to_entity(self, row: asyncpg.Record) -> Memory:
        """Map database row to Memory entity."""
        return Memory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            importance_score=float(row["importance_score"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            user_id=row.get("user_id"),
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
            embedding=list(row["embedding"]) if row.get("embedding") else None,
            access_count=row.get("access_count", 0),
            last_accessed=row.get("last_accessed"),
        )

    async def _map_entity_to_values(self, memory: Memory) -> dict[str, Any]:
        """Map Memory entity to database values."""
        return {
            "id": memory.id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "importance_score": memory.importance_score,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "user_id": memory.user_id,
            "metadata": json.dumps(memory.metadata) if memory.metadata else "{}",
            "embedding": memory.embedding,
            "access_count": memory.access_count,
            "last_accessed": memory.last_accessed,
        }

    async def save(self, memory: Memory) -> str:
        """
        Save a new memory to the database.

        Args:
            memory: Memory entity to save

        Returns:
            The ID of the saved memory
        """
        values = await self._map_entity_to_values(memory)

        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO memories (
                    id, content, memory_type, importance_score, created_at,
                    updated_at, user_id, metadata, embedding, access_count, last_accessed
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """

            memory_id = await conn.fetchval(
                query,
                values["id"],
                values["content"],
                values["memory_type"],
                values["importance_score"],
                values["created_at"],
                values["updated_at"],
                values["user_id"],
                values["metadata"],
                values["embedding"],
                values["access_count"],
                values["last_accessed"],
            )

            await self._log_operation("save", memory_id)
            return memory_id

    async def update(self, memory: Memory) -> bool:
        """
        Update an existing memory.

        Args:
            memory: Memory entity to update

        Returns:
            True if memory was updated, False if not found
        """
        values = await self._map_entity_to_values(memory)

        async with self.pool.acquire() as conn:
            query = """
                UPDATE memories SET
                    content = $2,
                    memory_type = $3,
                    importance_score = $4,
                    updated_at = $5,
                    user_id = $6,
                    metadata = $7,
                    embedding = $8,
                    access_count = $9,
                    last_accessed = $10
                WHERE id = $1
            """

            result = await conn.execute(
                query,
                values["id"],
                values["content"],
                values["memory_type"],
                values["importance_score"],
                values["updated_at"],
                values["user_id"],
                values["metadata"],
                values["embedding"],
                values["access_count"],
                values["last_accessed"],
            )

            rows_affected = int(result.split()[-1]) if result.split() else 0
            success = rows_affected > 0

            if success:
                await self._log_operation("update", memory.id)

            return success

    async def search_by_content(
        self,
        query: str,
        limit: int = 50,
        memory_type: MemoryType | None = None,
        user_id: str | None = None,
    ) -> list[Memory]:
        """
        Search memories by content using full-text search.

        Args:
            query: Search query string
            limit: Maximum number of results
            memory_type: Optional memory type filter
            user_id: Optional user ID filter

        Returns:
            List of matching memories ordered by relevance
        """
        params = [query, limit]
        where_conditions = ["content ILIKE '%' || $1 || '%'"]

        if memory_type:
            params.append(memory_type.value)
            where_conditions.append(f"memory_type = ${len(params)}")

        if user_id:
            params.append(user_id)
            where_conditions.append(f"user_id = ${len(params)}")

        where_clause = " AND ".join(where_conditions)

        async with self.pool.acquire() as conn:
            query_sql = f"""
                SELECT *,
                       ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank
                FROM {self.table_name}
                WHERE {where_clause}
                ORDER BY rank DESC, importance_score DESC
                LIMIT ${len(params)}
            """

            rows = await conn.fetch(query_sql, *params)
            memories = [await self._map_row_to_entity(row) for row in rows]

            await self._log_operation(
                "search_by_content", query_text=query, results_count=len(memories)
            )
            return memories

    async def search_by_criteria(self, criteria: SearchCriteria) -> list[Memory]:
        """
        Search memories using complex criteria.

        Args:
            criteria: Search criteria object

        Returns:
            List of matching memories
        """
        where_conditions = []
        params = []

        if criteria.query:
            params.append(criteria.query)
            where_conditions.append(f"content ILIKE '%' || ${len(params)} || '%'")

        if criteria.memory_type:
            params.append(criteria.memory_type.value)
            where_conditions.append(f"memory_type = ${len(params)}")

        if criteria.user_id:
            params.append(criteria.user_id)
            where_conditions.append(f"user_id = ${len(params)}")

        if criteria.min_importance is not None:
            params.append(criteria.min_importance)
            where_conditions.append(f"importance_score >= ${len(params)}")

        if criteria.created_after:
            params.append(criteria.created_after)
            where_conditions.append(f"created_at >= ${len(params)}")

        if criteria.created_before:
            params.append(criteria.created_before)
            where_conditions.append(f"created_at <= ${len(params)}")

        if not where_conditions:
            where_conditions.append("TRUE")  # No filters, return all

        where_clause = " AND ".join(where_conditions)
        order_by = "importance_score DESC, created_at DESC"

        memories = await self.find_by_criteria(
            where_clause,
            params,
            limit=criteria.limit,
            offset=criteria.offset or 0,
            order_by=order_by,
        )

        await self._log_operation("search_by_criteria", results_count=len(memories))
        return memories

    async def find_by_user(self, user_id: str, limit: int = 100) -> list[Memory]:
        """Find all memories for a specific user."""
        where_clause = "user_id = $1"
        params = [user_id]

        memories = await self.find_by_criteria(
            where_clause, params, limit=limit, order_by="created_at DESC"
        )

        await self._log_operation("find_by_user", user_id=user_id, results_count=len(memories))
        return memories

    async def find_related(self, memory_id: str, limit: int = 10) -> list[Memory]:
        """
        Find memories related to the given memory using similarity.

        This is a simplified implementation. In a production system,
        you might use vector similarity search with embeddings.
        """
        # First get the target memory
        target_memory = await self.find_by_id(memory_id)
        if not target_memory:
            return []

        # Find memories with similar content or from same user
        async with self.pool.acquire() as conn:
            query = """
                SELECT *,
                       similarity(content, $2) as content_similarity
                FROM memories
                WHERE id != $1
                  AND (user_id = $3 OR similarity(content, $2) > 0.1)
                ORDER BY content_similarity DESC, importance_score DESC
                LIMIT $4
            """

            rows = await conn.fetch(
                query, memory_id, target_memory.content, target_memory.user_id, limit
            )

            memories = [await self._map_row_to_entity(row) for row in rows]

            await self._log_operation(
                "find_related", memory_id=memory_id, results_count=len(memories)
            )
            return memories

    async def get_metrics(self, user_id: str | None = None) -> MemoryMetrics:
        """Get memory statistics and metrics."""
        async with self.pool.acquire() as conn:
            if user_id:
                base_query = "FROM memories WHERE user_id = $1"
                params = [user_id]
            else:
                base_query = "FROM memories"
                params = []

            # Get basic counts
            total_count = await conn.fetchval(f"SELECT COUNT(*) {base_query}", *params)

            # Get counts by type
            type_query = f"""
                SELECT memory_type, COUNT(*) as count
                {base_query}
                GROUP BY memory_type
            """
            type_rows = await conn.fetch(type_query, *params)
            type_counts = {row["memory_type"]: row["count"] for row in type_rows}

            # Get average importance
            avg_importance = (
                await conn.fetchval(f"SELECT AVG(importance_score) {base_query}", *params) or 0.0
            )

            # Get recent activity (last 7 days)
            recent_query = f"""
                SELECT COUNT(*) {base_query}
                AND created_at >= NOW() - INTERVAL '7 days'
            """
            recent_count = await conn.fetchval(recent_query, *params)

            return MemoryMetrics(
                total_memories=total_count,
                memories_by_type=type_counts,
                average_importance=float(avg_importance),
                recent_memories=recent_count,
                total_access_count=0,  # Would need additional query
                last_updated=datetime.utcnow(),
            )

    async def update_importance_score(self, memory_id: str, score: float) -> bool:
        """Update the importance score of a memory."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE memories
                SET importance_score = $2, updated_at = NOW()
                WHERE id = $1
            """

            result = await conn.execute(query, memory_id, score)
            rows_affected = int(result.split()[-1]) if result.split() else 0
            success = rows_affected > 0

            if success:
                await self._log_operation("update_importance", memory_id, new_score=score)

            return success

    async def mark_as_accessed(self, memory_id: str) -> None:
        """Mark memory as accessed for importance tracking."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE memories
                SET access_count = COALESCE(access_count, 0) + 1,
                    last_accessed = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """

            await conn.execute(query, memory_id)
            await self._log_operation("mark_accessed", memory_id)
