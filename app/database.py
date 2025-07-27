"""
Simple PostgreSQL database client with pgvector support.
Single source of truth for all data operations.
"""

import json
import logging
import os
import re
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
        # Database connection - prefer DATABASE_URL if provided
        db_url = os.getenv('DATABASE_URL')
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
        """Setup database schema with pgvector extension and memory types."""
        if not self.pool:
            raise RuntimeError("Database connection pool not initialized")

        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create memory type enum
            await conn.execute("""
                DO $$ BEGIN
                    CREATE TYPE memory_type_enum AS ENUM ('semantic', 'episodic', 'procedural');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Create enhanced memories table with memory types
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding vector(1536),

                    -- Memory type classification
                    memory_type memory_type_enum NOT NULL DEFAULT 'semantic',

                    -- Cognitive metadata
                    importance_score DECIMAL(5,4) DEFAULT 0.5000,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                    -- Type-specific metadata
                    semantic_metadata JSONB DEFAULT '{}',
                    episodic_metadata JSONB DEFAULT '{}',
                    procedural_metadata JSONB DEFAULT '{}',

                    -- Consolidation tracking
                    consolidation_score DECIMAL(5,4) DEFAULT 0.5000,
                    last_consolidated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    decay_applied BOOLEAN DEFAULT FALSE,

                    -- General metadata (legacy compatibility)
                    metadata JSONB DEFAULT '{}',

                    -- Constraints
                    CONSTRAINT valid_importance CHECK (importance_score >= 0.0000 AND importance_score <= 1.0000),
                    CONSTRAINT valid_consolidation CHECK (consolidation_score >= 0.0000 AND consolidation_score <= 1.0000)
                )
            """)

            # Create specialized indices for memory types
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_memory_type
                ON memories(memory_type)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance
                ON memories(importance_score DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_consolidation
                ON memories(consolidation_score DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_last_accessed
                ON memories(last_accessed DESC)
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

            # Vector index with importance weighting
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_embedding_weighted
                ON memories USING ivfflat (embedding vector_cosine_ops)
                WHERE importance_score > 0.1000
            """)

            logger.info("Enhanced database schema with memory types setup complete")

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
        # In test environment, return mock embeddings
        if os.getenv("ENVIRONMENT") == "test" and not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
            # Generate deterministic mock embedding based on text hash
            import hashlib
            text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            # Return a 1536-dimensional vector (matching text-embedding-3-small)
            return [(text_hash + i) % 1000 / 1000.0 for i in range(1536)]
        
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

    async def store_memory(
        self,
        content: str,
        memory_type: str = "semantic",
        semantic_metadata: dict[str, Any] | None = None,
        episodic_metadata: dict[str, Any] | None = None,
        procedural_metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory with its embedding and cognitive metadata."""
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
                INSERT INTO memories (
                    content, memory_type, embedding, importance_score,
                    semantic_metadata, episodic_metadata, procedural_metadata, metadata
                )
                VALUES ($1, $2::memory_type_enum, $3::vector, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                content,
                memory_type,
                embedding_str,
                importance_score,
                json.dumps(semantic_metadata or {}),
                json.dumps(episodic_metadata or {}),
                json.dumps(procedural_metadata or {}),
                json.dumps(metadata or {}),
            )

            memory_id = str(result["id"])
            logger.info(f"Stored {memory_type} memory with ID: {memory_id}")

            # Check if we should create/update the vector index
            await self._ensure_vector_index()

            return memory_id

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories using vector similarity (legacy method)."""
        return await self.contextual_search(
            query=query, limit=limit, memory_types=None, importance_threshold=None, timeframe=None
        )

    async def contextual_search(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        importance_threshold: float | None = None,
        timeframe: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Advanced contextual search with memory type filtering and multi-dimensional scoring."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        # Generate query embedding
        query_embedding = await self._get_embedding(query)

        # Build dynamic WHERE clause
        where_conditions = ["embedding IS NOT NULL"]
        params: list[Any] = [f"[{','.join(map(str, query_embedding))}]"]
        param_count = 1

        # Memory type filtering
        if memory_types:
            param_count += 1
            where_conditions.append(f"memory_type = ANY(${param_count})")
            params.append(memory_types)

        # Importance threshold filtering
        if importance_threshold is not None:
            param_count += 1
            where_conditions.append(f"importance_score >= ${param_count}")
            params.append(importance_threshold)

        # Timeframe filtering
        if timeframe:
            timeframe_clause = self._build_timeframe_clause(timeframe)
            if timeframe_clause:
                where_conditions.append(timeframe_clause)

        # Archive filtering
        if not include_archived:
            where_conditions.append("importance_score > 0.1")  # Archived threshold

        where_clause = " AND ".join(where_conditions)

        # Search with contextual scoring
        async with self.pool.acquire() as conn:
            query_sql = f"""
                SELECT
                    id, content, memory_type,
                    importance_score, access_count, last_accessed,
                    semantic_metadata, episodic_metadata, procedural_metadata,
                    consolidation_score, metadata, created_at, updated_at,

                    -- Multi-dimensional scoring
                    (1 - (embedding <=> $1::vector)) as vector_similarity,
                    importance_score as importance_weight,

                    -- Combined contextual score
                    (
                        (1 - (embedding <=> $1::vector)) * 0.4 +
                        importance_score * 0.25 +
                        consolidation_score * 0.15 +
                        LEAST(access_count / 10.0, 1.0) * 0.2
                    ) as contextual_score

                FROM memories
                WHERE {where_clause}
                ORDER BY contextual_score DESC, vector_similarity DESC
                LIMIT ${param_count + 1}
            """

            params.append(limit)
            rows = await conn.fetch(query_sql, *params)

            # Update access counts for retrieved memories
            memory_ids = [str(row["id"]) for row in rows]
            if memory_ids:
                await conn.execute(
                    """
                    UPDATE memories
                    SET access_count = access_count + 1, last_accessed = NOW()
                    WHERE id = ANY($1)
                    """,
                    memory_ids,
                )

            results = []
            for row in rows:
                results.append(
                    {
                        "id": str(row["id"]),
                        "content": row["content"],
                        "memory_type": row["memory_type"],
                        "importance_score": float(row["importance_score"]),
                        "access_count": row["access_count"],
                        "last_accessed": row["last_accessed"].isoformat(),
                        "semantic_metadata": json.loads(row["semantic_metadata"]) if row["semantic_metadata"] else {},
                        "episodic_metadata": json.loads(row["episodic_metadata"]) if row["episodic_metadata"] else {},
                        "procedural_metadata": json.loads(row["procedural_metadata"])
                        if row["procedural_metadata"]
                        else {},
                        "consolidation_score": float(row["consolidation_score"]),
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "similarity": float(row["vector_similarity"]),
                        "contextual_score": float(row["contextual_score"]),
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                    }
                )

            logger.info(f"Found {len(results)} memories for contextual query: {query}")
            return results

    def _build_timeframe_clause(self, timeframe: str) -> str | None:
        """Build SQL WHERE clause for timeframe filtering."""
        timeframe_map = {
            "last_hour": "created_at >= NOW() - INTERVAL '1 hour'",
            "last_day": "created_at >= NOW() - INTERVAL '1 day'",
            "last_week": "created_at >= NOW() - INTERVAL '1 week'",
            "last_month": "created_at >= NOW() - INTERVAL '1 month'",
            "last_year": "created_at >= NOW() - INTERVAL '1 year'",
        }
        return timeframe_map.get(timeframe)

    def classify_memory_type(self, content: str, existing_metadata: dict[str, Any] | None = None) -> str:
        """
        Intelligently classify memory type based on content analysis.

        Returns: 'semantic', 'episodic', or 'procedural'
        """
        content_lower = content.lower()

        # Check for explicit type hints in metadata
        if existing_metadata:
            if existing_metadata.get("type") in ["semantic", "episodic", "procedural"]:
                return existing_metadata["type"]

        # Episodic memory indicators (time-bound, personal experiences)
        episodic_patterns = [
            # Temporal indicators
            r"\b(today|yesterday|last week|last month|this morning|this afternoon|tonight)\b",
            r"\b(on \w+day|at \d+:\d+|in \d{4})\b",
            r"\b(meeting|session|call|conversation|discussion)\b",
            r"\b(fixed|solved|debugged|resolved|completed|finished)\b",
            r"\b(issue|problem|bug|error|failure)\b.*\b(resolved|fixed|solved)\b",
            r"\b(learned|discovered|found|realized|noticed)\b",
            r"\b(during|while|when|after|before)\b.*\b(doing|working|coding)\b",
            # Personal experience indicators
            r"\b(I|we|my|our|team)\b.*\b(did|worked|created|built|implemented)\b",
            r"\b(client|customer|user|stakeholder)\b.*\b(said|asked|requested|wanted)\b",
            r"\b(deployment|release|launch|rollout)\b",
            r"\b(outage|incident|emergency|urgent)\b",
        ]

        # Procedural memory indicators (how-to, processes, workflows)
        procedural_patterns = [
            # Process indicators
            r"\b(step|steps|process|procedure|workflow|method|approach)\b",
            r"\b(how to|instruction|guide|tutorial|documentation)\b",
            r"\b(first|then|next|finally|last|step \d+)\b",
            r"\b(setup|configure|install|deploy|build|run)\b",
            r"\b(command|script|code|function|method|class)\b",
            r"\b(pipeline|automation|ci/cd|devops)\b",
            r"\b(best practice|pattern|strategy|technique)\b",
            r"\b(checklist|template|framework|standard)\b",
            # Action-oriented language
            r"\b(run|execute|perform|do|make|create|build|deploy)\b",
            r"\b(configure|setup|initialize|start|stop|restart)\b",
            r"[:\n]\s*[1-9]\.\s",  # Numbered lists
            r"[:\n]\s*[-*]\s",  # Bullet points
        ]

        # Semantic memory indicators (facts, concepts, knowledge)
        semantic_patterns = [
            # Technical facts and concepts
            r"\b(definition|concept|theory|principle|law|rule)\b",
            r"\b(technology|framework|library|database|system|architecture)\b",
            r"\b(algorithm|data structure|design pattern|methodology)\b",
            r"\b(feature|capability|functionality|specification)\b",
            r"\b(documentation|reference|manual|guide|standard)\b",
            r"\b(enables|provides|supports|allows|offers)\b",
            r"\b(postgres|postgresql|python|javascript|react|docker|kubernetes)\b",
            r"\b(api|rest|graphql|http|https|json|xml|yaml)\b",
            # Factual language patterns
            r"\b(is|are|was|were)\b.*\b(a|an|the)\b",
            r"\b(means|refers to|represents|indicates|denotes)\b",
            r"\b(typically|usually|generally|commonly|often)\b",
            r"\b(advantage|benefit|limitation|drawback|characteristic)\b",
        ]

        import re

        # Count pattern matches
        episodic_score = sum(1 for pattern in episodic_patterns if re.search(pattern, content_lower))
        procedural_score = sum(1 for pattern in procedural_patterns if re.search(pattern, content_lower))
        semantic_score = sum(1 for pattern in semantic_patterns if re.search(pattern, content_lower))

        # Additional scoring based on content structure

        # Episodic bonus: Past tense verbs, personal pronouns, time references
        if re.search(r"\b(fixed|solved|completed|resolved|implemented|deployed|discovered)\b", content_lower):
            episodic_score += 2
        if re.search(r"\b(I|we|my|our|team)\b", content_lower):
            episodic_score += 1
        if re.search(r"\b(meeting|call|session|discussion|conversation)\b", content_lower):
            episodic_score += 2

        # Procedural bonus: Imperative verbs, step indicators, code patterns
        if re.search(r"^(run|execute|start|stop|create|build|deploy|install)", content_lower):
            procedural_score += 2
        if re.search(r"\b\d+\.\s|\b(first|then|next|finally)\b", content_lower):
            procedural_score += 2
        if re.search(r"```|`[^`]+`|\$\s*\w+", content):  # Code blocks or commands
            procedural_score += 2

        # Semantic bonus: Factual statements, definitions, explanations
        if re.search(r"\b(enables|provides|allows|supports|is a|are)\b", content_lower):
            semantic_score += 2
        if re.search(r"\b(definition|concept|feature|capability|specification)\b", content_lower):
            semantic_score += 2
        if len(content.split()) > 50:  # Longer content often semantic
            semantic_score += 1

        # Length-based adjustments
        word_count = len(content.split())
        if word_count < 20:  # Short content more likely procedural or episodic
            if procedural_score > 0:
                procedural_score += 1
            if episodic_score > 0:
                episodic_score += 1
        elif word_count > 100:  # Long content more likely semantic
            semantic_score += 2

        # Determine the winning type
        scores = {"episodic": episodic_score, "procedural": procedural_score, "semantic": semantic_score}

        # Find the type with highest score
        max_score = max(scores.values())

        # If no clear winner or tie, default to semantic
        if max_score == 0:
            return "semantic"

        # Return the type with highest score (first in case of tie)
        for memory_type, score in scores.items():
            if score == max_score:
                return memory_type

        return "semantic"  # Fallback

    def generate_smart_metadata(self, content: str, memory_type: str) -> dict[str, Any]:
        """
        Generate intelligent metadata based on content analysis and memory type.
        """
        content_lower = content.lower()
        metadata = {}

        if memory_type == "semantic":
            # Detect domain and category
            if any(tech in content_lower for tech in ["database", "postgres", "sql", "query"]):
                metadata["domain"] = "database"
                metadata["category"] = "technology"
            elif any(tech in content_lower for tech in ["python", "javascript", "code", "programming"]):
                metadata["domain"] = "programming"
                metadata["category"] = "technology"
            elif any(tech in content_lower for tech in ["api", "rest", "http", "web"]):
                metadata["domain"] = "web_development"
                metadata["category"] = "technology"
            elif any(tech in content_lower for tech in ["docker", "kubernetes", "deployment", "devops"]):
                metadata["domain"] = "devops"
                metadata["category"] = "technology"

            # Confidence based on factual language
            if any(word in content_lower for word in ["enables", "provides", "supports", "allows", "specification"]):
                metadata["confidence"] = 0.9
            elif any(word in content_lower for word in ["generally", "typically", "usually", "often"]):
                metadata["confidence"] = 0.75
            else:
                metadata["confidence"] = 0.8

        elif memory_type == "episodic":
            # Detect context and outcome
            if any(word in content_lower for word in ["meeting", "call", "discussion", "session"]):
                metadata["context"] = "meeting"
            elif any(word in content_lower for word in ["debug", "fix", "solve", "issue", "problem"]):
                metadata["context"] = "debugging_session"
            elif any(word in content_lower for word in ["deploy", "release", "launch"]):
                metadata["context"] = "deployment"

            if any(word in content_lower for word in ["resolved", "fixed", "solved", "completed"]):
                metadata["outcome"] = "resolved"
                metadata["emotional_valence"] = "satisfaction"
            elif any(word in content_lower for word in ["failed", "broke", "error", "issue"]):
                metadata["outcome"] = "unresolved"
                metadata["emotional_valence"] = "concern"

            # Detect location
            if any(word in content_lower for word in ["production", "prod", "live"]):
                metadata["location"] = "production_environment"
            elif any(word in content_lower for word in ["dev", "development", "staging"]):
                metadata["location"] = "development_environment"

        elif memory_type == "procedural":
            # Detect skill level and complexity
            step_count = len([m for m in re.finditer(r"\b\d+\.\s|\b(first|then|next|finally)\b", content_lower)])
            if step_count > 0:
                metadata["steps"] = step_count

            if step_count > 10 or len(content.split()) > 200:
                metadata["complexity"] = "high"
                metadata["skill_level"] = "expert"
            elif step_count > 5 or len(content.split()) > 100:
                metadata["complexity"] = "medium"
                metadata["skill_level"] = "intermediate"
            else:
                metadata["complexity"] = "low"
                metadata["skill_level"] = "beginner"

            # Detect domain
            if any(word in content_lower for word in ["deploy", "ci/cd", "pipeline", "automation"]):
                metadata["domain"] = "devops"
            elif any(word in content_lower for word in ["code", "programming", "development"]):
                metadata["domain"] = "programming"
            elif any(word in content_lower for word in ["database", "query", "sql"]):
                metadata["domain"] = "database"

            # Success rate estimation
            if any(word in content_lower for word in ["best practice", "proven", "reliable", "tested"]):
                metadata["success_rate"] = 0.95
            elif any(word in content_lower for word in ["experimental", "untested", "new"]):
                metadata["success_rate"] = 0.7
            else:
                metadata["success_rate"] = 0.85

        return metadata

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a specific memory by ID with full cognitive metadata."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    id, content, memory_type, importance_score, access_count, last_accessed,
                    semantic_metadata, episodic_metadata, procedural_metadata,
                    consolidation_score, metadata, created_at, updated_at
                FROM memories
                WHERE id = $1
            """,
                memory_id,
            )

            if not row:
                return None

            # Update access count
            await conn.execute(
                """
                UPDATE memories
                SET access_count = access_count + 1, last_accessed = NOW()
                WHERE id = $1
                """,
                memory_id,
            )

            return {
                "id": str(row["id"]),
                "content": row["content"],
                "memory_type": row["memory_type"],
                "importance_score": float(row["importance_score"]),
                "access_count": row["access_count"] + 1,  # Reflect the increment
                "last_accessed": row["last_accessed"].isoformat() if row["last_accessed"] else None,
                "semantic_metadata": json.loads(row["semantic_metadata"]) if row["semantic_metadata"] else {},
                "episodic_metadata": json.loads(row["episodic_metadata"]) if row["episodic_metadata"] else {},
                "procedural_metadata": json.loads(row["procedural_metadata"]) if row["procedural_metadata"] else {},
                "consolidation_score": float(row["consolidation_score"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
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
        """Get all memories with pagination and full cognitive metadata."""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id, content, memory_type, importance_score, access_count, last_accessed,
                    semantic_metadata, episodic_metadata, procedural_metadata,
                    consolidation_score, metadata, created_at, updated_at
                FROM memories
                ORDER BY importance_score DESC, created_at DESC
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
                        "memory_type": row["memory_type"],
                        "importance_score": float(row["importance_score"]),
                        "access_count": row["access_count"],
                        "last_accessed": row["last_accessed"].isoformat() if row["last_accessed"] else None,
                        "semantic_metadata": json.loads(row["semantic_metadata"]) if row["semantic_metadata"] else {},
                        "episodic_metadata": json.loads(row["episodic_metadata"]) if row["episodic_metadata"] else {},
                        "procedural_metadata": json.loads(row["procedural_metadata"])
                        if row["procedural_metadata"]
                        else {},
                        "consolidation_score": float(row["consolidation_score"]),
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
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
    # Check if we should use mock database
    if os.getenv("USE_MOCK_DATABASE", "false").lower() == "true":
        from app.database_mock import MockDatabase
        global database
        if not isinstance(database, MockDatabase):
            database = MockDatabase()
        if not database.is_initialized:
            await database.initialize()
        return database
    
    # Use real database
    if not database.pool:
        await database.initialize()
    return database
