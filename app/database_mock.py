"""
Mock version of the database for testing without OpenAI API calls.
"""

import json
import logging
import os
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class MockDatabase:
    """Mock PostgreSQL database client for testing."""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def initialize(self):
        """Initialize database connection."""
        # Database connection
        db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'secondbrain')}"

        try:
            self.pool = await asyncpg.create_pool(db_url, min_size=1, max_size=10)
            logger.info("Database connection established")

            # Ensure table exists
            await self._setup_database()

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def _setup_database(self):
        """Setup database schema."""
        async with self.pool.acquire() as conn:
            # Create memories table without vector column for testing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories_mock (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info("Mock database schema setup complete")

    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()

    def _get_mock_embedding(self, text: str) -> list[float]:
        """Generate a mock embedding based on text hash."""
        # Simple hash-based mock embedding
        text_hash = hash(text)
        return [float((text_hash + i) % 1000) / 1000.0 for i in range(1536)]

    async def store_memory(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Store a memory (mock version)."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        # Store in database
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO memories_mock (content, metadata)
                VALUES ($1, $2)
                RETURNING id
            """,
                content,
                json.dumps(metadata or {}),
            )

            memory_id = str(result["id"])
            logger.info(f"Stored memory with ID: {memory_id}")
            return memory_id

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories using text search (mock version)."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        # Simple text search
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    content,
                    metadata,
                    created_at,
                    updated_at,
                    CASE
                        WHEN LOWER(content) LIKE LOWER($1) THEN 0.9
                        WHEN LOWER(content) LIKE LOWER('%' || $1 || '%') THEN 0.7
                        ELSE 0.5
                    END as similarity
                FROM memories_mock
                WHERE LOWER(content) LIKE LOWER('%' || $1 || '%')
                ORDER BY similarity DESC
                LIMIT $2
            """,
                query,
                limit,
            )

            results = []
            for row in rows:
                results.append(
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]),
                        "similarity": float(row["similarity"]),
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                    }
                )

            logger.info(f"Found {len(results)} memories for query")
            return results

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a specific memory by ID."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content, metadata, created_at, updated_at
                FROM memories_mock
                WHERE id = $1
            """,
                memory_id,
            )

            if not row:
                return None

            return {
                "id": str(row["id"]),
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories_mock WHERE id = $1
            """,
                memory_id,
            )

            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info(f"Deleted memory with ID: {memory_id}")
            return deleted

    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Get all memories with pagination."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, created_at, updated_at
                FROM memories_mock
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """,
                limit,
                offset,
            )

            results = []
            for row in rows:
                results.append(
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]),
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                    }
                )

            return results

    async def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about vector index performance (mock version)."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            # Get table statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_memories,
                    COUNT(*) as memories_with_embeddings,
                    AVG(LENGTH(content)) as avg_content_length
                FROM memories_mock
            """)

            return {
                "total_memories": stats["total_memories"],
                "memories_with_embeddings": stats["memories_with_embeddings"],
                "avg_content_length": float(stats["avg_content_length"]) if stats["avg_content_length"] else 0,
                "hnsw_index_exists": False,  # Mock doesn't use real indexes
                "ivf_index_exists": False,
                "recommended_index_threshold": 1000,
                "index_ready": False,  # Mock doesn't need real indexes
            }

    async def force_create_index(self) -> bool:
        """Force creation of vector index (mock version - always succeeds)."""
        logger.info("Mock database: Index creation simulated")
        return True


# Global mock database instance
mock_database = MockDatabase()


async def get_mock_database() -> MockDatabase:
    """Get initialized mock database instance."""
    if not mock_database.pool:
        await mock_database.initialize()
    return mock_database
