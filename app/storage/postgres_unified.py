"""
PostgreSQL Unified Storage Backend with pgvector
Provides vector search, full-text search, and JSONB storage in a single database
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncpg
import numpy as np
from contextlib import asynccontextmanager

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PostgresUnifiedBackend:
    """
    Unified PostgreSQL backend with pgvector for all storage needs
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        pool_size: int = 20,
        max_inactive_connection_lifetime: float = 300.0
    ):
        """
        Initialize PostgreSQL backend with connection pooling
        
        Args:
            connection_string: PostgreSQL connection string
            pool_size: Maximum number of connections in pool
            max_inactive_connection_lifetime: Max idle time for connections
        """
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/second_brain"
        )
        self.pool_size = pool_size
        self.max_inactive_lifetime = max_inactive_connection_lifetime
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize connection pool and ensure schema exists"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=self.pool_size,
                max_inactive_connection_lifetime=self.max_inactive_lifetime,
                command_timeout=60
            )
            
            # Ensure extensions are installed
            async with self.pool.acquire() as conn:
                # Check if extensions exist first
                for ext in ['uuid-ossp', 'vector', 'pg_trgm']:
                    exists = await conn.fetchval(
                        "SELECT 1 FROM pg_extension WHERE extname = $1",
                        ext
                    )
                    if not exists:
                        # Use 'vector' not 'pgvector' as extension name
                        ext_name = ext if ext != 'vector' else 'vector'
                        try:
                            await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext_name}"')
                        except Exception as e:
                            logger.warning(f"Could not create extension {ext_name}: {e}")
                
            logger.info("PostgreSQL unified backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL backend: {e}")
            raise
            
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
            
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool"""
        async with self.pool.acquire() as conn:
            yield conn
            
    # ==================== Memory CRUD Operations ====================
    
    async def create_memory(
        self,
        memory: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Create a new memory with optional embedding
        
        Args:
            memory: Memory data dictionary
            embedding: Optional vector embedding
            
        Returns:
            Created memory with ID
        """
        memory_id = memory.get("id") or str(uuid.uuid4())
        
        query = """
            INSERT INTO memories (
                id, content, memory_type, importance_score,
                tags, metadata, embedding, embedding_model,
                embedding_generated_at, container_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6::jsonb, $7::vector, $8, $9, $10
            )
            RETURNING *
        """
        
        async with self.acquire() as conn:
            # Convert embedding to pgvector format if provided
            embedding_vector = None
            embedding_model = None
            embedding_generated_at = None
            
            if embedding:
                # Convert embedding to PostgreSQL vector format
                embedding_vector = self._format_vector(embedding)
                embedding_model = memory.get("embedding_model", "text-embedding-ada-002")
                embedding_generated_at = datetime.utcnow()
            
            row = await conn.fetchrow(
                query,
                uuid.UUID(memory_id),
                memory["content"],
                memory.get("memory_type", "generic"),
                memory.get("importance_score", 0.5),
                memory.get("tags", []),
                json.dumps(memory.get("metadata", {})),
                embedding_vector,
                embedding_model,
                embedding_generated_at,
                memory.get("container_id", "default")
            )
            
            return self._row_to_dict(row)
            
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        query = """
            SELECT * FROM memories 
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, uuid.UUID(memory_id))
            
            if row:
                # Track access
                await conn.execute(
                    "SELECT track_memory_access($1)",
                    uuid.UUID(memory_id)
                )
                return self._row_to_dict(row)
                
            return None
            
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any],
        new_embedding: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a memory with optional new embedding"""
        
        # Build dynamic update query
        set_clauses = []
        params = [uuid.UUID(memory_id)]
        param_count = 1
        
        if "content" in updates:
            param_count += 1
            set_clauses.append(f"content = ${param_count}")
            params.append(updates["content"])
            
        if "importance_score" in updates:
            param_count += 1
            set_clauses.append(f"importance_score = ${param_count}")
            params.append(updates["importance_score"])
            
        if "tags" in updates:
            param_count += 1
            set_clauses.append(f"tags = ${param_count}")
            params.append(updates["tags"])
            
        if "metadata" in updates:
            param_count += 1
            set_clauses.append(f"metadata = ${param_count}::jsonb")
            params.append(json.dumps(updates["metadata"]))
            
        if new_embedding:
            param_count += 1
            set_clauses.append(f"embedding = ${param_count}::vector")
            # Convert embedding to PostgreSQL vector format
            embedding_vector = self._format_vector(new_embedding)
            params.append(embedding_vector)
            
            param_count += 1
            set_clauses.append(f"embedding_generated_at = ${param_count}")
            params.append(datetime.utcnow())
            
        if not set_clauses:
            return await self.get_memory(memory_id)
            
        # Increment version
        set_clauses.append("version = version + 1")
        
        query = f"""
            UPDATE memories 
            SET {', '.join(set_clauses)}
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING *
        """
        
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            return self._row_to_dict(row) if row else None
            
    async def delete_memory(self, memory_id: str, soft: bool = True) -> bool:
        """Delete a memory (soft delete by default)"""
        
        if soft:
            query = """
                UPDATE memories 
                SET deleted_at = NOW()
                WHERE id = $1 AND deleted_at IS NULL
                RETURNING id
            """
        else:
            query = """
                DELETE FROM memories 
                WHERE id = $1
                RETURNING id
            """
            
        async with self.acquire() as conn:
            result = await conn.fetchrow(query, uuid.UUID(memory_id))
            return result is not None
            
    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
        container_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """List memories with filtering"""
        
        where_clauses = ["deleted_at IS NULL", "container_id = $1"]
        params = [container_id]
        param_count = 1
        
        if memory_type:
            param_count += 1
            where_clauses.append(f"memory_type = ${param_count}")
            params.append(memory_type)
            
        if tags:
            param_count += 1
            where_clauses.append(f"tags && ${param_count}")
            params.append(tags)
            
        if min_importance is not None:
            param_count += 1
            where_clauses.append(f"importance_score >= ${param_count}")
            params.append(min_importance)
            
        param_count += 1
        limit_param = param_count
        params.append(limit)
        
        param_count += 1
        offset_param = param_count
        params.append(offset)
        
        query = f"""
            SELECT * FROM memories
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_dict(row) for row in rows]
            
    # ==================== Search Operations ====================
    
    async def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        container_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Pure vector similarity search"""
        
        query = """
            SELECT 
                *,
                1 - (embedding <=> $1::vector) AS similarity
            FROM memories
            WHERE deleted_at IS NULL
                AND container_id = $2
                AND embedding IS NOT NULL
                AND 1 - (embedding <=> $1::vector) >= $3
            ORDER BY embedding <=> $1::vector
            LIMIT $4
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(
                query,
                self._format_vector(embedding),
                container_id,
                min_similarity,
                limit
            )
            
            results = []
            for row in rows:
                memory = self._row_to_dict(row)
                memory["similarity"] = float(row["similarity"])
                results.append(memory)
                
            return results
            
    async def text_search(
        self,
        query: str,
        limit: int = 10,
        container_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL FTS"""
        
        query_sql = """
            SELECT 
                *,
                ts_rank(content_tsvector, plainto_tsquery('english', $1)) AS rank
            FROM memories
            WHERE deleted_at IS NULL
                AND container_id = $2
                AND content_tsvector @@ plainto_tsquery('english', $1)
            ORDER BY rank DESC
            LIMIT $3
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(query_sql, query, container_id, limit)
            
            results = []
            for row in rows:
                memory = self._row_to_dict(row)
                memory["text_rank"] = float(row["rank"])
                results.append(memory)
                
            return results
            
    async def hybrid_search(
        self,
        query: str,
        embedding: Optional[List[float]] = None,
        limit: int = 10,
        vector_weight: float = 0.5,
        min_score: float = 0.0,
        container_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and text search"""
        
        if not embedding:
            # Fall back to text-only search
            return await self.text_search(query, limit, container_id)
            
        query_sql = """
            SELECT * FROM hybrid_search($1, $2::vector, $3, $4, $5)
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(
                query_sql,
                query,
                self._format_vector(embedding),
                limit,
                vector_weight,
                min_score
            )
            
            results = []
            for row in rows:
                memory = {
                    "id": str(row["id"]),
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "importance_score": float(row["importance_score"]),
                    "tags": row["tags"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat(),
                    "similarity_score": float(row["similarity_score"]),
                    "text_rank": float(row["text_rank"]),
                    "combined_score": float(row["combined_score"])
                }
                results.append(memory)
                
            return results
            
    # ==================== Relationship Operations ====================
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a relationship between memories"""
        
        query = """
            INSERT INTO memory_relationships (
                source_memory_id, target_memory_id, 
                relationship_type, strength, metadata
            ) VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (source_memory_id, target_memory_id, relationship_type)
            DO UPDATE SET 
                strength = EXCLUDED.strength,
                metadata = EXCLUDED.metadata
            RETURNING *
        """
        
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                query,
                uuid.UUID(source_id),
                uuid.UUID(target_id),
                relationship_type,
                strength,
                json.dumps(metadata or {})
            )
            
            return {
                "id": str(row["id"]),
                "source_memory_id": str(row["source_memory_id"]),
                "target_memory_id": str(row["target_memory_id"]),
                "relationship_type": row["relationship_type"],
                "strength": float(row["strength"]),
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat()
            }
            
    async def get_related_memories(
        self,
        memory_id: str,
        relationship_type: Optional[str] = None,
        min_strength: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Get memories related to a given memory"""
        
        where_clauses = ["r.strength >= $2"]
        params = [uuid.UUID(memory_id), min_strength]
        param_count = 2
        
        if relationship_type:
            param_count += 1
            where_clauses.append(f"r.relationship_type = ${param_count}")
            params.append(relationship_type)
            
        query = f"""
            SELECT 
                m.*,
                r.relationship_type,
                r.strength as relationship_strength
            FROM memory_relationships r
            JOIN memories m ON (
                (r.source_memory_id = $1 AND m.id = r.target_memory_id)
                OR
                (r.target_memory_id = $1 AND m.id = r.source_memory_id)
            )
            WHERE m.deleted_at IS NULL
                AND {' AND '.join(where_clauses)}
            ORDER BY r.strength DESC
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                memory = self._row_to_dict(row)
                memory["relationship_type"] = row["relationship_type"]
                memory["relationship_strength"] = float(row["relationship_strength"])
                results.append(memory)
                
            return results
            
    # ==================== Consolidation Operations ====================
    
    async def consolidate_memories(
        self,
        source_ids: List[str],
        consolidated_content: str,
        consolidation_type: str = "merge",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Consolidate multiple memories into one"""
        
        async with self.acquire() as conn:
            async with conn.transaction():
                # Create the consolidated memory
                consolidated_memory = await self.create_memory({
                    "content": consolidated_content,
                    "memory_type": "consolidated",
                    "importance_score": 0.8,
                    "metadata": {
                        "consolidation_type": consolidation_type,
                        "source_count": len(source_ids),
                        **(metadata or {})
                    }
                })
                
                # Record consolidation
                await conn.execute("""
                    INSERT INTO memory_consolidations (
                        consolidated_memory_id, source_memory_ids,
                        consolidation_type, metadata
                    ) VALUES ($1, $2, $3, $4::jsonb)
                """,
                    uuid.UUID(consolidated_memory["id"]),
                    [uuid.UUID(sid) for sid in source_ids],
                    consolidation_type,
                    json.dumps(metadata or {})
                )
                
                # Soft delete source memories if merging
                if consolidation_type == "merge":
                    for source_id in source_ids:
                        await self.delete_memory(source_id, soft=True)
                        
                return consolidated_memory
                
    async def find_duplicates(
        self,
        similarity_threshold: float = 0.95
    ) -> List[Tuple[str, str, float]]:
        """Find duplicate memories based on embedding similarity"""
        
        query = """
            SELECT * FROM find_duplicate_memories($1)
        """
        
        async with self.acquire() as conn:
            rows = await conn.fetch(query, similarity_threshold)
            
            return [
                (str(row["memory1_id"]), str(row["memory2_id"]), float(row["similarity"]))
                for row in rows
            ]
            
    # ==================== Analytics Operations ====================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        query = """
            SELECT * FROM memory_statistics
        """
        
        async with self.acquire() as conn:
            row = await conn.fetchrow(query)
            
            if row:
                return {
                    "total_memories": row["total_memories"],
                    "unique_types": row["unique_types"],
                    "avg_importance": float(row["avg_importance"]) if row["avg_importance"] else 0,
                    "max_access_count": row["max_access_count"],
                    "containers": row["containers"],
                    "memories_with_embeddings": row["memories_with_embeddings"],
                    "table_size": row["table_size"],
                    "latest_memory": row["latest_memory"].isoformat() if row["latest_memory"] else None,
                    "oldest_memory": row["oldest_memory"].isoformat() if row["oldest_memory"] else None,
                    "backend": "postgresql_unified"
                }
            
            return {
                "total_memories": 0,
                "backend": "postgresql_unified"
            }
            
    async def record_search(
        self,
        query: str,
        embedding: Optional[List[float]],
        results_count: int,
        selected_ids: List[str],
        search_type: str = "hybrid",
        metadata: Optional[Dict[str, Any]] = None,
        container_id: str = "default"
    ):
        """Record search history for learning patterns"""
        
        query_sql = """
            INSERT INTO search_history (
                query, query_embedding, results_count,
                selected_memory_ids, search_type, metadata, container_id
            ) VALUES ($1, $2::vector, $3, $4, $5, $6::jsonb, $7)
        """
        
        async with self.acquire() as conn:
            await conn.execute(
                query_sql,
                query,
                self._format_vector(embedding) if embedding else None,
                results_count,
                [uuid.UUID(sid) for sid in selected_ids],
                search_type,
                json.dumps(metadata or {}),
                container_id
            )
            
    # ==================== Migration Operations ====================
    
    async def migrate_from_sqlite(self, sqlite_path: str):
        """Migrate data from SQLite to PostgreSQL"""
        import aiosqlite
        
        async with aiosqlite.connect(sqlite_path) as sqlite_conn:
            cursor = await sqlite_conn.execute("""
                SELECT * FROM memories ORDER BY created_at
            """)
            
            rows = await cursor.fetchall()
            
            for row in rows:
                # Convert SQLite row to dict
                memory = {
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "importance_score": row[3],
                    "tags": json.loads(row[4]) if row[4] else [],
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "created_at": row[6],
                    "updated_at": row[7]
                }
                
                await self.create_memory(memory)
                
            logger.info(f"Migrated {len(rows)} memories from SQLite")
            
    # ==================== Helper Methods ====================
    
    def _format_vector(self, embedding: List[float]) -> str:
        """Convert embedding list to PostgreSQL vector format"""
        return f"[{','.join(str(x) for x in embedding)}]"
    
    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if not row:
            return None
            
        result = {
            "id": str(row["id"]),
            "content": row["content"],
            "memory_type": row["memory_type"],
            "importance_score": float(row["importance_score"]),
            "tags": row["tags"] or [],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else {},
            "access_count": row["access_count"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "last_accessed_at": row["last_accessed_at"].isoformat() if row["last_accessed_at"] else None,
            "container_id": row["container_id"],
            "version": row["version"]
        }
        
        # Only include embedding info if present
        if row.get("embedding"):
            result["has_embedding"] = True
            result["embedding_model"] = row["embedding_model"]
            result["embedding_generated_at"] = row["embedding_generated_at"].isoformat() if row["embedding_generated_at"] else None
        else:
            result["has_embedding"] = False
            
        return result