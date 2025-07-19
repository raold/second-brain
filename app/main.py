"""
Second Brain - PostgreSQL-Centered Architecture
A simplified, focused implementation using PostgreSQL + pgvector as the primary storage.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/second_brain")

# Global database pool
db_pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global db_pool

    # Startup
    logger.info("🚀 Starting Second Brain PostgreSQL Edition")

    # Initialize database connection pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20, command_timeout=60)
        logger.info("✅ Database connection pool initialized")

        # Ensure pgvector extension is enabled
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                logger.info("✅ PostgreSQL extensions (vector, pg_trgm) enabled")

            # Create tables if they don't exist
            await initialize_database()

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("🔄 Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Second Brain - PostgreSQL Edition",
    description="A simplified memory management system built on PostgreSQL + pgvector",
    version="2.4.1",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")


# Models
class Memory(BaseModel):
    """Memory model for storage and retrieval."""

    id: Optional[str] = None
    content: str = Field(..., description="The memory content")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    importance: float = Field(default=1.0, ge=0.0, le=10.0, description="Importance score")
    tags: list[str] = Field(default_factory=list, description="Memory tags")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    tags: Optional[list[str]] = Field(default=None, description="Filter by tags")
    importance_min: Optional[float] = Field(default=None, description="Minimum importance")


class SearchResult(BaseModel):
    """Search result model."""

    memory: Memory
    similarity: float = Field(description="Similarity score")
    rank: int = Field(description="Result rank")


# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify authentication token."""
    token = credentials.credentials
    valid_tokens = os.getenv("API_TOKENS", "demo-token").split(",")

    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return token


# Database functions
async def get_db_connection():
    """Get database connection from pool."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_pool


async def initialize_database():
    """Initialize database schema."""
    async with db_pool.acquire() as conn:
        # Create memories table with pgvector
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                content_vector vector(1536),  -- OpenAI embedding dimension
                metadata JSONB DEFAULT '{}',
                importance REAL DEFAULT 1.0,
                tags TEXT[] DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
            )
        """)

        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_vector 
            ON memories USING ivfflat (content_vector vector_cosine_ops) 
            WITH (lists = 100)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_search 
            ON memories USING GIN (search_vector)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_tags 
            ON memories USING GIN (tags)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_importance 
            ON memories (importance DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_created_at 
            ON memories (created_at DESC)
        """)

        logger.info("✅ Database schema initialized")


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text using OpenAI API."""
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Return a dummy embedding for development
        logger.warning("⚠️  No OpenAI API key - using dummy embedding")
        return [0.1] * 1536

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"❌ Failed to generate embedding: {e}")
        # Return dummy embedding as fallback
        return [0.1] * 1536


# API Routes
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Second Brain - PostgreSQL Edition",
        "version": "2.4.1",
        "description": "Memory management system built on PostgreSQL + pgvector",
        "endpoints": {
            "memories": "/memories",
            "search": "/search",
            "dashboard": "/dashboard",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM memories")
            return {"status": "healthy", "database": "connected", "memory_count": result, "timestamp": time.time()}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e), "timestamp": time.time()}


@app.post("/memories", response_model=dict)
async def create_memory(memory: Memory, token: str = Depends(verify_token), db_pool=Depends(get_db_connection)):
    """Create a new memory."""
    try:
        # Generate embedding for the content
        embedding = await generate_embedding(memory.content)

        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO memories (content, content_vector, metadata, importance, tags)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, created_at
            """,
                memory.content,
                embedding,
                memory.metadata,
                memory.importance,
                memory.tags,
            )

            return {
                "id": str(result["id"]),
                "message": "Memory created successfully",
                "created_at": result["created_at"].isoformat(),
            }
    except Exception as e:
        logger.error(f"❌ Failed to create memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@app.get("/memories", response_model=list[Memory])
async def list_memories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
    importance_min: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    token: str = Depends(verify_token),
    db_pool=Depends(get_db_connection),
):
    """List memories with optional filtering."""
    try:
        # Build query conditions
        conditions = []
        params = []
        param_count = 0

        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            param_count += 1
            conditions.append(f"tags && ${param_count}")
            params.append(tag_list)

        if importance_min is not None:
            param_count += 1
            conditions.append(f"importance >= ${param_count}")
            params.append(importance_min)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Add limit and offset
        param_count += 1
        params.append(limit)
        limit_clause = f"LIMIT ${param_count}"

        param_count += 1
        params.append(offset)
        offset_clause = f"OFFSET ${param_count}"

        query = f"""
            SELECT id, content, metadata, importance, tags, created_at, updated_at
            FROM memories 
            WHERE {where_clause}
            ORDER BY importance DESC, created_at DESC
            {limit_clause} {offset_clause}
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            memories = []
            for row in rows:
                memories.append(
                    Memory(
                        id=str(row["id"]),
                        content=row["content"],
                        metadata=row["metadata"],
                        importance=row["importance"],
                        tags=row["tags"],
                        created_at=row["created_at"].isoformat(),
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                    )
                )

            return memories
    except Exception as e:
        logger.error(f"❌ Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(e)}")


@app.post("/search", response_model=list[SearchResult])
async def search_memories(
    search_request: SearchRequest, token: str = Depends(verify_token), db_pool=Depends(get_db_connection)
):
    """Search memories using vector similarity and text search."""
    try:
        # Generate embedding for query
        query_embedding = await generate_embedding(search_request.query)

        # Build additional filters
        conditions = []
        params = [query_embedding, search_request.threshold, search_request.limit]
        param_count = 3

        if search_request.tags:
            param_count += 1
            conditions.append(f"tags && ${param_count}")
            params.append(search_request.tags)

        if search_request.importance_min is not None:
            param_count += 1
            conditions.append(f"importance >= ${param_count}")
            params.append(search_request.importance_min)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Combined vector and text search
        query = f"""
            WITH vector_search AS (
                SELECT 
                    id, content, metadata, importance, tags, created_at, updated_at,
                    1 - (content_vector <=> $1) as similarity,
                    'vector' as search_type
                FROM memories 
                WHERE (1 - (content_vector <=> $1)) > $2 AND {where_clause}
            ),
            text_search AS (
                SELECT 
                    id, content, metadata, importance, tags, created_at, updated_at,
                    ts_rank(search_vector, plainto_tsquery('english', %s)) as similarity,
                    'text' as search_type
                FROM memories 
                WHERE search_vector @@ plainto_tsquery('english', %s) AND {where_clause}
            ),
            combined AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY similarity DESC) as rn
                FROM (
                    SELECT * FROM vector_search
                    UNION ALL 
                    SELECT * FROM text_search
                ) combined_results
            )
            SELECT id, content, metadata, importance, tags, created_at, updated_at, 
                   MAX(similarity) as similarity
            FROM combined 
            WHERE rn = 1
            ORDER BY similarity DESC, importance DESC
            LIMIT $3
        """ % (f"'{search_request.query}'", f"'{search_request.query}'")

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            results = []
            for i, row in enumerate(rows):
                memory = Memory(
                    id=str(row["id"]),
                    content=row["content"],
                    metadata=row["metadata"],
                    importance=row["importance"],
                    tags=row["tags"],
                    created_at=row["created_at"].isoformat(),
                    updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                )

                results.append(SearchResult(memory=memory, similarity=float(row["similarity"]), rank=i + 1))

            return results
    except Exception as e:
        logger.error(f"❌ Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@app.get("/memories/{memory_id}", response_model=Memory)
async def get_memory(memory_id: str, token: str = Depends(verify_token), db_pool=Depends(get_db_connection)):
    """Get a specific memory by ID."""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content, metadata, importance, tags, created_at, updated_at
                FROM memories 
                WHERE id = $1
            """,
                memory_id,
            )

            if not row:
                raise HTTPException(status_code=404, detail="Memory not found")

            return Memory(
                id=str(row["id"]),
                content=row["content"],
                metadata=row["metadata"],
                importance=row["importance"],
                tags=row["tags"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, token: str = Depends(verify_token), db_pool=Depends(get_db_connection)):
    """Delete a memory by ID."""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories WHERE id = $1
            """,
                memory_id,
            )

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Memory not found")

            return {"message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML page."""
    from fastapi.responses import FileResponse

    return FileResponse("static/dashboard.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
