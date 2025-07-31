"""
Base repository pattern implementation with common functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import asyncpg

from app.utils.logging_config import get_logger

T = TypeVar('T')

logger = get_logger(__name__)


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations.

    Implements the Repository pattern to abstract data access operations
    and provide a consistent interface for all entities.
    """

    def __init__(self, connection_pool: asyncpg.Pool):
        """Initialize repository with database connection pool."""
        self.pool = connection_pool

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the table name for this repository."""
        pass

    @abstractmethod
    async def _map_row_to_entity(self, row: asyncpg.Record) -> T:
        """Map database row to domain entity."""
        pass

    @abstractmethod
    async def _map_entity_to_values(self, entity: T) -> dict[str, Any]:
        """Map domain entity to database values."""
        pass

    async def find_by_id(self, entity_id: str) -> T | None:
        """
        Find entity by ID.

        Args:
            entity_id: The entity identifier

        Returns:
            The entity if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            query = f"SELECT * FROM {self.table_name} WHERE id = $1"
            row = await conn.fetchrow(query, entity_id)

            if row:
                return await self._map_row_to_entity(row)
            return None

    async def find_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """
        Find all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        async with self.pool.acquire() as conn:
            if limit:
                query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT $1 OFFSET $2"
                rows = await conn.fetch(query, limit, offset)
            else:
                query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
                rows = await conn.fetch(query)

            return [await self._map_row_to_entity(row) for row in rows]

    async def exists(self, entity_id: str) -> bool:
        """
        Check if entity exists by ID.

        Args:
            entity_id: The entity identifier

        Returns:
            True if entity exists, False otherwise
        """
        async with self.pool.acquire() as conn:
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE id = $1"
            count = await conn.fetchval(query, entity_id)
            return count > 0

    async def count(self, where_clause: str | None = None, params: list[Any] | None = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            where_clause: Optional WHERE clause
            params: Parameters for the WHERE clause

        Returns:
            Number of entities
        """
        async with self.pool.acquire() as conn:
            if where_clause:
                query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
                count = await conn.fetchval(query, *(params or []))
            else:
                query = f"SELECT COUNT(*) FROM {self.table_name}"
                count = await conn.fetchval(query)

            return count

    async def delete_by_id(self, entity_id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: The entity identifier

        Returns:
            True if entity was deleted, False if not found
        """
        async with self.pool.acquire() as conn:
            query = f"DELETE FROM {self.table_name} WHERE id = $1"
            result = await conn.execute(query, entity_id)

            # Extract row count from result string like "DELETE 1"
            rows_affected = int(result.split()[-1]) if result.split() else 0
            return rows_affected > 0

    async def find_by_criteria(
        self,
        where_clause: str,
        params: list[Any],
        limit: int | None = None,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> list[T]:
        """
        Find entities by custom criteria.

        Args:
            where_clause: WHERE clause conditions
            params: Parameters for the WHERE clause
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            order_by: ORDER BY clause

        Returns:
            List of matching entities
        """
        async with self.pool.acquire() as conn:
            base_query = f"SELECT * FROM {self.table_name} WHERE {where_clause} ORDER BY {order_by}"

            if limit:
                query = f"{base_query} LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
                rows = await conn.fetch(query, *params, limit, offset)
            else:
                rows = await conn.fetch(base_query, *params)

            return [await self._map_row_to_entity(row) for row in rows]

    async def execute_query(
        self,
        query: str,
        params: list[Any] | None = None
    ) -> list[asyncpg.Record]:
        """
        Execute custom query and return raw results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of database records
        """
        async with self.pool.acquire() as conn:
            if params:
                return await conn.fetch(query, *params)
            else:
                return await conn.fetch(query)

    async def execute_transaction(self, operations: list[dict[str, Any]]) -> None:
        """
        Execute multiple operations in a transaction.

        Args:
            operations: List of operations, each containing 'query' and optional 'params'
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for operation in operations:
                    query = operation['query']
                    params = operation.get('params', [])

                    if params:
                        await conn.execute(query, *params)
                    else:
                        await conn.execute(query)

    async def _log_operation(self, operation: str, entity_id: str | None = None, **kwargs):
        """Log repository operations for debugging and monitoring."""
        log_data = {
            'repository': self.__class__.__name__,
            'table': self.table_name,
            'operation': operation,
        }

        if entity_id:
            log_data['entity_id'] = entity_id

        log_data.update(kwargs)

        logger.debug("Repository operation", extra=log_data)
