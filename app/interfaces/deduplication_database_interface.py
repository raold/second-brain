"""
Deduplication Database Interface

Clean abstraction layer for deduplication database operations,
enabling proper testing and dependency injection.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DeduplicationDatabaseInterface(ABC):
    """Abstract interface for deduplication database operations."""

    @abstractmethod
    async def get_memories_for_deduplication(
        self, filter_criteria: Optional[dict[str, Any]] = None, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve memories for deduplication analysis.

        Args:
            filter_criteria: Optional filtering criteria
            limit: Optional limit on number of memories

        Returns:
            List of memory dictionaries with required fields:
            - id: Memory identifier
            - content: Memory content for comparison
            - created_at: Creation timestamp
            - metadata: Memory metadata including importance_score
        """
        pass

    @abstractmethod
    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        """
        Retrieve specific memories by their IDs.

        Args:
            memory_ids: List of memory IDs to retrieve

        Returns:
            List of memory dictionaries for found memories
        """
        pass

    @abstractmethod
    async def merge_memories(
        self,
        primary_id: str,
        duplicate_ids: list[str],
        merge_strategy: str,
        merged_metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Merge duplicate memories into a primary memory.

        Args:
            primary_id: ID of the memory to keep as primary
            duplicate_ids: List of duplicate memory IDs to merge
            merge_strategy: Strategy used for merging
            merged_metadata: Optional metadata for the merged result

        Returns:
            True if merge successful, False otherwise
        """
        pass

    @abstractmethod
    async def mark_as_duplicate(self, memory_id: str, primary_id: str) -> bool:
        """
        Mark a memory as a duplicate of another memory.

        Args:
            memory_id: ID of memory to mark as duplicate
            primary_id: ID of the primary memory

        Returns:
            True if marking successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str, reason: str = "deduplication") -> bool:
        """
        Delete a memory from the database.

        Args:
            memory_id: ID of memory to delete
            reason: Reason for deletion (for audit trail)

        Returns:
            True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    async def backup_memories(self, memory_ids: list[str]) -> Optional[str]:
        """
        Create a backup of memories before deduplication.

        Args:
            memory_ids: List of memory IDs to backup

        Returns:
            Backup identifier if successful, None otherwise
        """
        pass

    @abstractmethod
    async def get_memory_embeddings(self, memory_ids: list[str]) -> dict[str, list[float]]:
        """
        Get semantic embeddings for memories.

        Args:
            memory_ids: List of memory IDs

        Returns:
            Dictionary mapping memory IDs to embedding vectors
        """
        pass


class PostgreSQLDeduplicationDatabase(DeduplicationDatabaseInterface):
    """PostgreSQL implementation of deduplication database interface."""

    def __init__(self, database_service):
        """
        Initialize with database service dependency.

        Args:
            database_service: Database service instance
        """
        self.database_service = database_service

    async def get_memories_for_deduplication(
        self, filter_criteria: Optional[dict[str, Any]] = None, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get memories from PostgreSQL database."""
        try:
            # Build query based on filter criteria
            query = """
                SELECT id, content, created_at, updated_at, metadata
                FROM memories 
                WHERE deleted_at IS NULL
            """
            params = []

            if filter_criteria:
                if "created_after" in filter_criteria:
                    query += " AND created_at > $%s"
                    params.append(filter_criteria["created_after"])
                if "content_length_min" in filter_criteria:
                    query += " AND LENGTH(content) >= $%s"
                    params.append(filter_criteria["content_length_min"])

            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)

            query += " ORDER BY created_at DESC"

            async with self.database_service.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get memories for deduplication: {e}")
            return []

    async def merge_memories(
        self,
        primary_id: str,
        duplicate_ids: list[str],
        merge_strategy: str,
        merged_metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Merge memories in PostgreSQL."""
        try:
            async with self.database_service.pool.acquire() as conn:
                async with conn.transaction():
                    # Update primary memory with merged metadata if provided
                    if merged_metadata:
                        await conn.execute(
                            "UPDATE memories SET metadata = $1, updated_at = NOW() WHERE id = $2",
                            merged_metadata,
                            primary_id,
                        )

                    # Mark duplicates as deleted and reference primary
                    for duplicate_id in duplicate_ids:
                        await conn.execute(
                            """UPDATE memories 
                               SET deleted_at = NOW(), 
                                   metadata = metadata || $1 
                               WHERE id = $2""",
                            {
                                "duplicate_of": primary_id,
                                "merge_strategy": merge_strategy,
                                "merged_at": str(datetime.now()),
                            },
                            duplicate_id,
                        )

                    # Log merge operation
                    await conn.execute(
                        """INSERT INTO memory_operations 
                           (operation_type, primary_memory_id, affected_memory_ids, metadata)
                           VALUES ($1, $2, $3, $4)""",
                        "merge",
                        primary_id,
                        duplicate_ids,
                        {"merge_strategy": merge_strategy, "merged_count": len(duplicate_ids)},
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to merge memories {duplicate_ids} into {primary_id}: {e}")
            return False

    async def mark_as_duplicate(self, memory_id: str, primary_id: str) -> bool:
        """Mark memory as duplicate in PostgreSQL."""
        try:
            async with self.database_service.pool.acquire() as conn:
                await conn.execute(
                    """UPDATE memories 
                       SET metadata = metadata || $1, updated_at = NOW() 
                       WHERE id = $2""",
                    {"is_duplicate": True, "duplicate_of": primary_id, "marked_duplicate_at": str(datetime.now())},
                    memory_id,
                )
            return True

        except Exception as e:
            logger.error(f"Failed to mark {memory_id} as duplicate of {primary_id}: {e}")
            return False

    async def delete_memory(self, memory_id: str, reason: str = "deduplication") -> bool:
        """Delete memory from PostgreSQL."""
        try:
            async with self.database_service.pool.acquire() as conn:
                await conn.execute(
                    """UPDATE memories 
                       SET deleted_at = NOW(), 
                           metadata = metadata || $1 
                       WHERE id = $2""",
                    {"deletion_reason": reason, "deleted_by": "deduplication_engine"},
                    memory_id,
                )
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def backup_memories(self, memory_ids: list[str]) -> Optional[str]:
        """Create backup of memories in PostgreSQL."""
        try:
            backup_id = f"dedup_backup_{int(time.time())}"

            async with self.database_service.pool.acquire() as conn:
                for memory_id in memory_ids:
                    # Copy memory to backup table
                    await conn.execute(
                        """INSERT INTO memory_backups 
                           (backup_id, original_memory_id, content, metadata, created_at)
                           SELECT $1, id, content, metadata, created_at 
                           FROM memories WHERE id = $2""",
                        backup_id,
                        memory_id,
                    )

            return backup_id

        except Exception as e:
            logger.error(f"Failed to backup memories {memory_ids}: {e}")
            return None

    async def get_memory_embeddings(self, memory_ids: list[str]) -> dict[str, list[float]]:
        """Get embeddings from PostgreSQL."""
        try:
            async with self.database_service.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT id, embedding FROM memory_embeddings WHERE memory_id = ANY($1)", memory_ids
                )
                return {row["id"]: row["embedding"] for row in rows if row["embedding"]}

        except Exception as e:
            logger.error(f"Failed to get embeddings for {memory_ids}: {e}")
            return {}


class MockDeduplicationDatabase(DeduplicationDatabaseInterface):
    """Mock implementation for testing."""

    def __init__(self):
        """Initialize mock database with sample data."""
        self.memories = [
            {
                "id": "mem_1",
                "content": "This is a test memory for deduplication.",
                "created_at": "2024-01-01T10:00:00Z",
                "metadata": {"importance_score": 0.8},
            },
            {
                "id": "mem_2",
                "content": "This is a test memory for deduplication.",  # Exact duplicate
                "created_at": "2024-01-01T11:00:00Z",
                "metadata": {"importance_score": 0.6},
            },
            {
                "id": "mem_3",
                "content": "A different memory with unique content.",
                "created_at": "2024-01-01T12:00:00Z",
                "metadata": {"importance_score": 0.7},
            },
        ]
        self.embeddings = {
            "mem_1": [0.1, 0.2, 0.3, 0.4],
            "mem_2": [0.1, 0.2, 0.3, 0.4],  # Same embedding (duplicate)
            "mem_3": [0.5, 0.6, 0.7, 0.8],  # Different embedding
        }
        self.operations = []
        self.backups = {}

    async def get_memories_for_deduplication(
        self, filter_criteria: Optional[dict[str, Any]] = None, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return mock memories."""
        filtered_memories = self.memories.copy()

        if filter_criteria:
            if "content_length_min" in filter_criteria:
                min_length = filter_criteria["content_length_min"]
                filtered_memories = [m for m in filtered_memories if len(m["content"]) >= min_length]

        if limit:
            filtered_memories = filtered_memories[:limit]

        return filtered_memories

    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict[str, Any]]:
        """Return memories with matching IDs."""
        return [m for m in self.memories if m["id"] in memory_ids]

    async def merge_memories(
        self,
        primary_id: str,
        duplicate_ids: list[str],
        merge_strategy: str,
        merged_metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Mock memory merging."""
        operation = {
            "type": "merge",
            "primary_id": primary_id,
            "duplicate_ids": duplicate_ids,
            "strategy": merge_strategy,
            "merged_metadata": merged_metadata,
        }
        self.operations.append(operation)
        return True

    async def mark_as_duplicate(self, memory_id: str, primary_id: str) -> bool:
        """Mock duplicate marking."""
        operation = {"type": "mark_duplicate", "memory_id": memory_id, "primary_id": primary_id}
        self.operations.append(operation)
        return True

    async def delete_memory(self, memory_id: str, reason: str = "deduplication") -> bool:
        """Mock memory deletion."""
        operation = {"type": "delete", "memory_id": memory_id, "reason": reason}
        self.operations.append(operation)
        return True

    async def backup_memories(self, memory_ids: list[str]) -> Optional[str]:
        """Mock backup creation."""
        backup_id = f"mock_backup_{len(self.backups)}"
        self.backups[backup_id] = {"memory_ids": memory_ids, "created_at": str(datetime.now())}
        return backup_id

    async def get_memory_embeddings(self, memory_ids: list[str]) -> dict[str, list[float]]:
        """Return mock embeddings."""
        return {mid: self.embeddings[mid] for mid in memory_ids if mid in self.embeddings}
