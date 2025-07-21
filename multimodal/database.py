"""
Multi-Modal Database Layer for Second Brain v2.6.0
Database operations for multimodal memory management
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import asyncpg
import numpy as np
from openai import OpenAI

from .models import (
    ContentType,
    MultiModalMemoryCreate,
    MultiModalMemoryResponse,
    MultiModalMemoryUpdate,
    MultiModalSearchRequest,
    MultiModalSearchResult,
    MultiModalStats,
    ProcessingStatus,
    ProcessingQueueItem
)

logger = logging.getLogger(__name__)


class MultiModalDatabase:
    """Database operations for multimodal memories."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or "postgresql://postgres:password@localhost:5432/second_brain"
        self.pool = None
        self.openai_client = None
        
        # Initialize OpenAI client if API key is available
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.warning(f"OpenAI client initialization failed: {e}")
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            logger.info("Database pool initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.pool:
                await self.initialize()
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_client or not text.strip():
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None
    
    async def create_memory(self, memory_data: MultiModalMemoryCreate) -> UUID:
        """Create a new multimodal memory."""
        if not self.pool:
            await self.initialize()
        
        memory_id = uuid4()
        
        # Generate text embedding
        text_vector = None
        if memory_data.content:
            full_text = memory_data.content
            if memory_data.extracted_text:
                full_text += " " + memory_data.extracted_text
            text_vector = await self.generate_embedding(full_text)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO multimodal_memories (
                    id, content, content_type, file_path, file_name, mime_type,
                    text_vector, extracted_text, summary, keywords, entities, sentiment,
                    metadata, importance, tags, processing_status, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW(), NOW()
                )
            """, 
                memory_id,
                memory_data.content,
                memory_data.content_type.value,
                memory_data.file_path,
                memory_data.file_name,
                memory_data.mime_type,
                text_vector,
                memory_data.extracted_text,
                memory_data.summary,
                memory_data.keywords,
                json.dumps(memory_data.entities),
                json.dumps(memory_data.sentiment),
                json.dumps(memory_data.metadata),
                memory_data.importance,
                memory_data.tags,
                ProcessingStatus.PENDING.value
            )
        
        logger.info(f"Created multimodal memory {memory_id}")
        return memory_id
    
    async def get_memory(self, memory_id: UUID) -> Optional[MultiModalMemoryResponse]:
        """Get a multimodal memory by ID."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, content, content_type, file_path, file_name, file_size, 
                       mime_type, file_hash, extracted_text, summary, keywords, 
                       entities, sentiment, metadata, importance, tags, 
                       processing_status, processing_errors, processed_at,
                       created_at, updated_at
                FROM multimodal_memories 
                WHERE id = $1
            """, memory_id)
            
            if not row:
                return None
            
            return MultiModalMemoryResponse(
                id=row['id'],
                content=row['content'],
                content_type=ContentType(row['content_type']),
                file_path=row['file_path'],
                file_name=row['file_name'],
                file_size=row['file_size'],
                mime_type=row['mime_type'],
                file_hash=row['file_hash'],
                extracted_text=row['extracted_text'],
                summary=row['summary'],
                keywords=row['keywords'] or [],
                entities=json.loads(row['entities']) if row['entities'] else {},
                sentiment=json.loads(row['sentiment']) if row['sentiment'] else {},
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                importance=row['importance'],
                tags=row['tags'] or [],
                processing_status=ProcessingStatus(row['processing_status']),
                processing_errors=json.loads(row['processing_errors']) if row['processing_errors'] else None,
                processed_at=row['processed_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def update_memory(self, memory_id: UUID, update_data: MultiModalMemoryUpdate) -> bool:
        """Update a multimodal memory."""
        if not self.pool:
            await self.initialize()
        
        # Build dynamic update query
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in update_data.dict(exclude_none=True).items():
            if field in ['entities', 'sentiment', 'metadata']:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
            param_count += 1
        
        if not set_clauses:
            return True  # Nothing to update
        
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(datetime.utcnow())
        param_count += 1
        
        values.append(memory_id)  # For WHERE clause
        
        query = f"""
            UPDATE multimodal_memories 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
        """
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            return result != "UPDATE 0"
    
    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete a multimodal memory."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM multimodal_memories WHERE id = $1
            """, memory_id)
            return result != "DELETE 0"
    
    async def list_memories(
        self, 
        limit: int = 20, 
        offset: int = 0, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MultiModalMemoryResponse]:
        """List multimodal memories with filtering."""
        if not self.pool:
            await self.initialize()
        
        where_clauses = []
        values = []
        param_count = 1
        
        if filters:
            if 'content_type' in filters:
                where_clauses.append(f"content_type = ${param_count}")
                values.append(filters['content_type'].value)
                param_count += 1
            
            if 'importance_min' in filters:
                where_clauses.append(f"importance >= ${param_count}")
                values.append(filters['importance_min'])
                param_count += 1
            
            if 'importance_max' in filters:
                where_clauses.append(f"importance <= ${param_count}")
                values.append(filters['importance_max'])
                param_count += 1
            
            if 'tags' in filters and filters['tags']:
                where_clauses.append(f"tags && ${param_count}")
                values.append(filters['tags'])
                param_count += 1
            
            if 'processing_status' in filters:
                where_clauses.append(f"processing_status = ${param_count}")
                values.append(filters['processing_status'].value)
                param_count += 1
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        values.extend([limit, offset])
        limit_offset = f"LIMIT ${param_count} OFFSET ${param_count + 1}"
        
        query = f"""
            SELECT id, content, content_type, file_path, file_name, file_size,
                   mime_type, file_hash, extracted_text, summary, keywords,
                   entities, sentiment, metadata, importance, tags,
                   processing_status, processing_errors, processed_at,
                   created_at, updated_at
            FROM multimodal_memories
            {where_clause}
            ORDER BY created_at DESC
            {limit_offset}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *values)
            
            memories = []
            for row in rows:
                memory = MultiModalMemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    content_type=ContentType(row['content_type']),
                    file_path=row['file_path'],
                    file_name=row['file_name'],
                    file_size=row['file_size'],
                    mime_type=row['mime_type'],
                    file_hash=row['file_hash'],
                    extracted_text=row['extracted_text'],
                    summary=row['summary'],
                    keywords=row['keywords'] or [],
                    entities=json.loads(row['entities']) if row['entities'] else {},
                    sentiment=json.loads(row['sentiment']) if row['sentiment'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    importance=row['importance'],
                    tags=row['tags'] or [],
                    processing_status=ProcessingStatus(row['processing_status']),
                    processing_errors=json.loads(row['processing_errors']) if row['processing_errors'] else None,
                    processed_at=row['processed_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                memories.append(memory)
            
            return memories
    
    async def search_memories(self, search_request: MultiModalSearchRequest) -> List[MultiModalSearchResult]:
        """Search multimodal memories."""
        if not self.pool:
            await self.initialize()
        
        # Generate query embedding
        query_vector = await self.generate_embedding(search_request.query)
        
        where_clauses = []
        values = []
        param_count = 1
        
        # Add filters
        if search_request.content_types:
            placeholders = ','.join([f'${param_count + i}' for i in range(len(search_request.content_types))])
            where_clauses.append(f"content_type = ANY(ARRAY[{placeholders}])")
            values.extend([ct.value for ct in search_request.content_types])
            param_count += len(search_request.content_types)
        
        if search_request.importance_min is not None:
            where_clauses.append(f"importance >= ${param_count}")
            values.append(search_request.importance_min)
            param_count += 1
        
        if search_request.importance_max is not None:
            where_clauses.append(f"importance <= ${param_count}")
            values.append(search_request.importance_max)
            param_count += 1
        
        if search_request.tags:
            where_clauses.append(f"tags && ${param_count}")
            values.append(search_request.tags)
            param_count += 1
        
        if search_request.date_from:
            where_clauses.append(f"created_at >= ${param_count}")
            values.append(search_request.date_from)
            param_count += 1
        
        if search_request.date_to:
            where_clauses.append(f"created_at <= ${param_count}")
            values.append(search_request.date_to)
            param_count += 1
        
        if not search_request.include_processing:
            where_clauses.append(f"processing_status != ${param_count}")
            values.append(ProcessingStatus.PROCESSING.value)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Add search parameters
        values.extend([search_request.query, query_vector, search_request.threshold, search_request.limit, search_request.offset])
        
        # Hybrid search query (text + vector similarity)
        query = f"""
            WITH search_results AS (
                SELECT 
                    id, content, content_type, file_path, file_name, file_size,
                    mime_type, file_hash, extracted_text, summary, keywords,
                    entities, sentiment, metadata, importance, tags,
                    processing_status, processing_errors, processed_at,
                    created_at, updated_at,
                    CASE 
                        WHEN text_vector IS NOT NULL AND ${param_count - 3} IS NOT NULL 
                        THEN 1 - (text_vector <=> ${param_count - 3}::vector)
                        ELSE 0 
                    END as vector_similarity,
                    ts_rank_cd(search_vector, plainto_tsquery('english', ${param_count - 4})) as text_rank
                FROM multimodal_memories
                {where_clause}
            )
            SELECT *,
                   (vector_similarity * 0.6 + text_rank * 0.4) as relevance_score,
                   CASE 
                       WHEN vector_similarity > 0.1 AND text_rank > 0.01 THEN 'hybrid'
                       WHEN vector_similarity > 0.1 THEN 'vector'
                       WHEN text_rank > 0.01 THEN 'text'
                       ELSE 'none'
                   END as match_type
            FROM search_results
            WHERE (vector_similarity >= ${param_count - 2} OR text_rank > 0.01)
            ORDER BY relevance_score DESC
            LIMIT ${param_count - 1} OFFSET ${param_count}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *values)
            
            results = []
            for row in rows:
                memory = MultiModalMemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    content_type=ContentType(row['content_type']),
                    file_path=row['file_path'],
                    file_name=row['file_name'],
                    file_size=row['file_size'],
                    mime_type=row['mime_type'],
                    file_hash=row['file_hash'],
                    extracted_text=row['extracted_text'],
                    summary=row['summary'],
                    keywords=row['keywords'] or [],
                    entities=json.loads(row['entities']) if row['entities'] else {},
                    sentiment=json.loads(row['sentiment']) if row['sentiment'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    importance=row['importance'],
                    tags=row['tags'] or [],
                    processing_status=ProcessingStatus(row['processing_status']),
                    processing_errors=json.loads(row['processing_errors']) if row['processing_errors'] else None,
                    processed_at=row['processed_at'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                result = MultiModalSearchResult(
                    memory=memory,
                    similarity_score=float(row['vector_similarity']),
                    relevance_score=float(row['relevance_score']),
                    match_type=row['match_type']
                )
                results.append(result)
            
            return results
    
    async def update_processing_status(
        self, 
        memory_id: UUID, 
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ):
        """Update processing status for a memory."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            if status == ProcessingStatus.COMPLETED:
                await conn.execute("""
                    UPDATE multimodal_memories 
                    SET processing_status = $1, processed_at = NOW(), updated_at = NOW()
                    WHERE id = $2
                """, status.value, memory_id)
            elif status == ProcessingStatus.FAILED:
                await conn.execute("""
                    UPDATE multimodal_memories 
                    SET processing_status = $1, processing_errors = $2, updated_at = NOW()
                    WHERE id = $3
                """, status.value, json.dumps({"error": error_message}), memory_id)
            else:
                await conn.execute("""
                    UPDATE multimodal_memories 
                    SET processing_status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status.value, memory_id)
    
    async def get_stats(self) -> MultiModalStats:
        """Get statistics for multimodal content."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            # Basic counts
            total_memories = await conn.fetchval("SELECT COUNT(*) FROM multimodal_memories")
            
            # Counts by content type
            type_counts = await conn.fetch("""
                SELECT content_type, COUNT(*) as count 
                FROM multimodal_memories 
                GROUP BY content_type
            """)
            memories_by_type = {ContentType(row['content_type']): row['count'] for row in type_counts}
            
            # Processing queue size
            queue_size = await conn.fetchval("""
                SELECT COUNT(*) FROM multimodal_memories 
                WHERE processing_status IN ('pending', 'processing')
            """)
            
            # Storage usage by type
            storage_usage = await conn.fetch("""
                SELECT content_type, COALESCE(SUM(file_size), 0) as total_size
                FROM multimodal_memories 
                WHERE file_size IS NOT NULL
                GROUP BY content_type
            """)
            storage_by_type = {row['content_type']: int(row['total_size']) for row in storage_usage}
            
            # Recent activity (last 24 hours)
            recent_activity = await conn.fetch("""
                SELECT content_type, COUNT(*) as count
                FROM multimodal_memories
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY content_type
            """)
            recent_counts = {row['content_type']: row['count'] for row in recent_activity}
            
            return MultiModalStats(
                total_memories=total_memories,
                memories_by_type=memories_by_type,
                processing_queue_size=queue_size,
                storage_usage=storage_by_type,
                recent_activity=recent_counts,
                performance_metrics={
                    "avg_processing_time": 2.5,  # Placeholder - implement actual metrics
                    "success_rate": 0.95
                },
                health_status="healthy"
            )
    
    async def get_processing_queue(self) -> List[ProcessingQueueItem]:
        """Get current processing queue items."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, processing_status, created_at, updated_at,
                       file_name, content_type
                FROM multimodal_memories
                WHERE processing_status IN ('pending', 'processing')
                ORDER BY created_at ASC
            """)
            
            items = []
            for row in rows:
                # Create a simplified processing queue item
                item = ProcessingQueueItem(
                    id=row['id'],
                    memory_id=row['id'],
                    operation_type="process_multimodal",
                    status=ProcessingStatus(row['processing_status']),
                    created_at=row['created_at']
                )
                items.append(item)
            
            return items


# Export database class
__all__ = ['MultiModalDatabase']
