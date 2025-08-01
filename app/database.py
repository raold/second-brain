import json
import os
from typing import Any

from app.utils.logging_config import get_logger

"""
Simple PostgreSQL database client with pgvector support.
Single source of truth for all data operations.
"""


import asyncpg
from openai import AsyncOpenAI

logger = get_logger(__name__)


class Database:
    """Simple PostgreSQL database client with pgvector support."""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.openai_client: AsyncOpenAI | None = None

    async def initialize(self):
        """Initialize database connection and OpenAI client."""
        # Database connection - prefer DATABASE_URL if provided
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # Fall back to individual components
            db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'secondbrain')}"

        try:
            self.pool = await asyncpg.create_pool(db_url, min_size=1, max_size=10)
            logger.info("Database connection established")

            # Ensure pgvector extension and table exist
            await self._setup_database()

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

        # OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")

    async def _setup_database(self):
        """Setup database schema and ensure pgvector extension exists."""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create memories table if it doesn't exist
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    metadata JSONB DEFAULT '{}',
                    importance_score INTEGER DEFAULT 5,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    tags TEXT[] DEFAULT '{}',
                    memory_type VARCHAR(50) DEFAULT 'general'
                )
            """
            )

            # Create index on embedding column for fast similarity search
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_embedding_idx
                ON memories USING hnsw (embedding vector_cosine_ops)
            """
            )

            # Create additional useful indexes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_created_at_idx
                ON memories (created_at DESC)
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_importance_idx
                ON memories (importance_score DESC)
            """
            )

    async def get_memories(
        self, limit: int | None = None, offset: int | None = None, memory_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get memories with optional filtering and pagination."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            query = "SELECT * FROM memories"
            args = []

            if memory_type:
                query += f" WHERE memory_type = ${len(args) + 1}"
                args.append(memory_type)

            query += " ORDER BY created_at DESC"

            if limit:
                query += f" LIMIT ${len(args) + 1}"
                args.append(limit)

            if offset:
                query += f" OFFSET ${len(args) + 1}"
                args.append(offset)

            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a specific memory by ID."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", memory_id)
            return dict(row) if row else None

    async def create_memory(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance_score: int = 5,
        tags: list[str] | None = None,
        memory_type: str = "general",
    ) -> dict[str, Any]:
        """Create a new memory with automatic embedding generation."""
        if not self.pool or not self.openai_client:
            raise RuntimeError("Database not initialized")

        # Generate embedding
        try:
            embedding_response = await self.openai_client.embeddings.create(
                input=content, model="text-embedding-ada-002"
            )
            embedding = embedding_response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            embedding = None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO memories (content, embedding, metadata, importance_score, tags, memory_type)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """,
                content,
                embedding,
                json.dumps(metadata or {}),
                importance_score,
                tags or [],
                memory_type,
            )

            return dict(row)

    async def search_memories(
        self, query: str, limit: int = 10, similarity_threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Search memories using embedding similarity."""
        if not self.pool or not self.openai_client:
            raise RuntimeError("Database not initialized")

        # Generate query embedding
        try:
            embedding_response = await self.openai_client.embeddings.create(
                input=query, model="text-embedding-ada-002"
            )
            query_embedding = embedding_response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *, 1 - (embedding <=> $1) as similarity_score
                FROM memories
                WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> $1) > $2
                ORDER BY similarity_score DESC
                LIMIT $3
            """,
                query_embedding,
                similarity_threshold,
                limit,
            )

            return [dict(row) for row in rows]

    async def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing memory."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        updates = []
        args = []
        arg_count = 1

        if content is not None:
            updates.append(f"content = ${arg_count}")
            args.append(content)
            arg_count += 1

            # Regenerate embedding if content changed
            if self.openai_client:
                try:
                    embedding_response = await self.openai_client.embeddings.create(
                        input=content, model="text-embedding-ada-002"
                    )
                    embedding = embedding_response.data[0].embedding
                    updates.append(f"embedding = ${arg_count}")
                    args.append(embedding)
                    arg_count += 1
                except Exception as e:
                    logger.error(f"Failed to regenerate embedding: {e}")

        if metadata is not None:
            updates.append(f"metadata = ${arg_count}")
            args.append(json.dumps(metadata))
            arg_count += 1

        if importance_score is not None:
            updates.append(f"importance_score = ${arg_count}")
            args.append(importance_score)
            arg_count += 1

        if tags is not None:
            updates.append(f"tags = ${arg_count}")
            args.append(tags)
            arg_count += 1

        if not updates:
            return await self.get_memory(memory_id)

        updates.append("updated_at = NOW()")
        args.append(memory_id)

        query = f"""
            UPDATE memories
            SET {', '.join(updates)}
            WHERE id = ${arg_count}
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM memories WHERE id = $1", memory_id)
            return result == "DELETE 1"

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_memories,
                    COUNT(embedding) as memories_with_embeddings,
                    AVG(LENGTH(content)) as avg_content_length,
                    MIN(created_at) as oldest_memory,
                    MAX(created_at) as newest_memory
                FROM memories
            """
            )

            return dict(stats) if stats else {}

    async def get_index_stats(self) -> dict[str, Any]:
        """Get index statistics for monitoring."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            # Basic stats
            basic_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_memories,
                    COUNT(embedding) as memories_with_embeddings,
                    AVG(LENGTH(content)) as avg_content_length
                FROM memories
            """
            )

            # Check if HNSW index exists and is ready
            index_info = await conn.fetchrow(
                """
                SELECT EXISTS(
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'memories'
                    AND indexname = 'memories_embedding_idx'
                ) as index_exists
            """
            )

            result = dict(basic_stats) if basic_stats else {}
            result["index_ready"] = index_info["index_exists"] if index_info else False

            return result

    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")


# Global database instance
_database: Database | None = None


async def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = Database()
        await _database.initialize()
    return _database


async def close_database():
    """Close the global database instance."""
    global _database
    if _database:
        await _database.close()
        _database = None
