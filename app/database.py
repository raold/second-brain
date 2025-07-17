"""
Simple PostgreSQL database client with pgvector support.
Single source of truth for all data operations.
"""

import json
import logging
import os
from typing import Any

import asyncpg
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class Database:
    """Simple PostgreSQL database client with pgvector support."""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.openai_client: AsyncOpenAI | None = None

    async def initialize(self):
        """Initialize database connection and OpenAI client."""
        # Database connection
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
        """Setup database schema with pgvector extension."""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create memories table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    embedding vector(1536),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create metadata index for filtering
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_metadata_idx
                ON memories USING GIN (metadata)
            """)

            # Create timestamp index for ordering
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_created_at_idx
                ON memories (created_at DESC)
            """)

            logger.info("Database schema setup complete")

    async def _ensure_vector_index(self):
        """Create HNSW index for vector similarity search after data exists."""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            # Check if we have enough data for indexing (recommended minimum: 1000 vectors)
            result = await conn.fetchval("""
                SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL
            """)

            if result < 1000:
                logger.info(f"Vector index not created - only {result} embeddings (need 1000+ for optimal performance)")
                return

            # Check if index already exists
            index_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'memories'
                    AND indexname = 'memories_embedding_hnsw_idx'
                )
            """)

            if not index_exists:
                try:
                    # Create HNSW index with optimized parameters
                    # m=16: number of connections (good balance of speed vs accuracy)
                    # ef_construction=64: controls trade-off between index quality and build time
                    await conn.execute("""
                        CREATE INDEX memories_embedding_hnsw_idx
                        ON memories USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                    """)
                    logger.info("HNSW vector index created successfully")
                except Exception as e:
                    logger.warning(f"Failed to create HNSW index: {e}")
                    # Fallback to IVFFlat if HNSW fails
                    try:
                        await conn.execute("""
                            CREATE INDEX IF NOT EXISTS memories_embedding_ivf_idx
                            ON memories USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = 100)
                        """)
                        logger.info("IVFFlat vector index created as fallback")
                    except Exception as e2:
                        logger.error(f"Failed to create fallback index: {e2}")
            else:
                logger.info("HNSW vector index already exists")

    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI API."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = await self.openai_client.embeddings.create(
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise

    async def store_memory(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Store a memory with its embedding."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        # Generate embedding
        embedding = await self._get_embedding(content)

        # Store in database
        async with self.pool.acquire() as conn:
            # Convert embedding list to string format for pgvector
            embedding_str = f"[{','.join(map(str, embedding))}]"

            result = await conn.fetchrow(
                """
                INSERT INTO memories (content, metadata, embedding)
                VALUES ($1, $2, $3::vector)
                RETURNING id
            """,
                content,
                json.dumps(metadata or {}),
                embedding_str,
            )

            memory_id = str(result["id"])
            logger.info(f"Stored memory with ID: {memory_id}")

            # Check if we should create/update the vector index
            # This runs periodically to optimize performance as data grows
            await self._ensure_vector_index()

            return memory_id

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories using vector similarity."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        # Generate query embedding
        query_embedding = await self._get_embedding(query)

        # Search similar memories
        async with self.pool.acquire() as conn:
            # Convert embedding list to string format for pgvector
            query_embedding_str = f"[{','.join(map(str, query_embedding))}]"

            rows = await conn.fetch(
                """
                SELECT
                    id,
                    content,
                    metadata,
                    created_at,
                    updated_at,
                    1 - (embedding <=> $1::vector) as similarity
                FROM memories
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """,
                query_embedding_str,
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
                FROM memories
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
                DELETE FROM memories WHERE id = $1
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
                FROM memories
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
        """Get statistics about vector index performance."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            # Get table statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_memories,
                    COUNT(embedding) as memories_with_embeddings,
                    AVG(LENGTH(content)) as avg_content_length
                FROM memories
            """)

            # Check index existence
            hnsw_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'memories'
                    AND indexname = 'memories_embedding_hnsw_idx'
                )
            """)

            ivf_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'memories'
                    AND indexname = 'memories_embedding_ivf_idx'
                )
            """)

            return {
                "total_memories": stats["total_memories"],
                "memories_with_embeddings": stats["memories_with_embeddings"],
                "avg_content_length": float(stats["avg_content_length"]) if stats["avg_content_length"] else 0,
                "hnsw_index_exists": hnsw_exists,
                "ivf_index_exists": ivf_exists,
                "recommended_index_threshold": 1000,
                "index_ready": stats["memories_with_embeddings"] >= 1000,
            }

    async def force_create_index(self) -> bool:
        """Force creation of vector index regardless of data size."""
        try:
            await self._ensure_vector_index()
            return True
        except Exception as e:
            logger.error(f"Failed to force create index: {e}")
            return False


# Global database instance
database = Database()


async def get_database() -> Database:
    """Get initialized database instance."""
    if not database.pool:
        await database.initialize()
    return database
