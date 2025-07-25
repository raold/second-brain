"""
Concrete memory repository implementation using SQLAlchemy.

Implements the MemoryRepository interface with PostgreSQL.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector

from src.domain.models.memory import Memory, MemoryId, MemoryStatus, MemoryType
from src.domain.models.tag import TagId
from src.domain.repositories.memory_repository import MemoryRepository
from src.infrastructure.database.models import MemoryModel, memory_links, memory_tags
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLMemoryRepository(MemoryRepository):
    """SQL implementation of memory repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get(self, memory_id: MemoryId) -> Optional[Memory]:
        """Get a memory by ID."""
        result = await self.session.get(
            MemoryModel,
            memory_id.value,
            options=[
                selectinload(MemoryModel.tags),
                selectinload(MemoryModel.linked_to),
            ]
        )
        
        if not result:
            return None
        
        return self._to_domain(result)
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        memory_type: Optional[MemoryType] = None,
        status: Optional[MemoryStatus] = None,
    ) -> list[Memory]:
        """Get memories for a user."""
        query = self.session.query(MemoryModel).filter(
            MemoryModel.user_id == user_id
        )
        
        if memory_type:
            query = query.filter(MemoryModel.memory_type == memory_type.value)
        
        if status:
            query = query.filter(MemoryModel.status == status.value)
        
        query = query.order_by(MemoryModel.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        results = await self.session.execute(
            query.options(
                selectinload(MemoryModel.tags),
                selectinload(MemoryModel.linked_to),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def save(self, memory: Memory) -> Memory:
        """Save a memory (create or update)."""
        # Check if memory exists
        existing = await self.session.get(MemoryModel, memory.id.value)
        
        if existing:
            # Update existing
            existing.title = memory.title
            existing.content = memory.content
            existing.memory_type = memory.memory_type.value
            existing.status = memory.status.value
            existing.importance_score = memory.importance_score
            existing.confidence_score = memory.confidence_score
            existing.source_url = memory.source_url
            existing.embedding = memory.embedding
            if memory.embedding:
                existing.embedding_vector = memory.embedding
            existing.embedding_model = memory.embedding_model
            existing.metadata = memory.metadata
            existing.attachments = memory.attachments
            existing.updated_at = datetime.utcnow()
            existing.retention_strength = memory.retention_strength
            existing.retrieval_count = memory.retrieval_count
            
            db_memory = existing
        else:
            # Create new
            db_memory = MemoryModel(
                id=memory.id.value,
                user_id=memory.user_id,
                title=memory.title,
                content=memory.content,
                memory_type=memory.memory_type.value,
                status=memory.status.value,
                importance_score=memory.importance_score,
                confidence_score=memory.confidence_score,
                source_url=memory.source_url,
                embedding=memory.embedding,
                embedding_vector=memory.embedding if memory.embedding else None,
                embedding_model=memory.embedding_model,
                metadata=memory.metadata,
                attachments=memory.attachments,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                accessed_at=memory.accessed_at,
                retention_strength=memory.retention_strength,
                retrieval_count=memory.retrieval_count,
            )
            self.session.add(db_memory)
        
        await self.session.flush()
        return memory
    
    async def delete(self, memory_id: MemoryId) -> bool:
        """Delete a memory."""
        result = await self.session.get(MemoryModel, memory_id.value)
        if not result:
            return False
        
        await self.session.delete(result)
        await self.session.flush()
        return True
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """Search memories by content."""
        search_filter = or_(
            MemoryModel.title.ilike(f"%{query}%"),
            MemoryModel.content.ilike(f"%{query}%"),
        )
        
        db_query = self.session.query(MemoryModel).filter(
            and_(
                MemoryModel.user_id == user_id,
                search_filter,
            )
        )
        
        if memory_type:
            db_query = db_query.filter(MemoryModel.memory_type == memory_type.value)
        
        db_query = db_query.order_by(MemoryModel.created_at.desc()).limit(limit)
        
        results = await self.session.execute(
            db_query.options(
                selectinload(MemoryModel.tags),
                selectinload(MemoryModel.linked_to),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def find_similar(
        self,
        user_id: UUID,
        embedding: list[float],
        limit: int = 10,
        threshold: float = 0.8,
    ) -> list[Memory]:
        """Find memories with similar embeddings using pgvector."""
        # Convert threshold from similarity to distance (1 - similarity)
        distance_threshold = 1 - threshold
        
        # Use pgvector for efficient similarity search
        query = text("""
            SELECT m.*, 1 - (m.embedding_vector <=> :embedding::vector) as similarity
            FROM memories m
            WHERE m.user_id = :user_id
            AND m.embedding_vector IS NOT NULL
            AND m.embedding_vector <=> :embedding::vector < :threshold
            ORDER BY m.embedding_vector <=> :embedding::vector
            LIMIT :limit
        """)
        
        results = await self.session.execute(
            query,
            {
                "user_id": user_id,
                "embedding": embedding,
                "threshold": distance_threshold,
                "limit": limit
            }
        )
        
        memories = []
        for row in results:
            memory_model = await self.session.get(
                MemoryModel,
                row.id,
                options=[
                    selectinload(MemoryModel.tags),
                    selectinload(MemoryModel.linked_to),
                ]
            )
            if memory_model:
                memories.append(self._to_domain(memory_model))
        
        return memories
    
    async def get_by_tag(
        self,
        user_id: UUID,
        tag_id: TagId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Memory]:
        """Get memories with a specific tag."""
        query = self.session.query(MemoryModel).join(
            memory_tags
        ).filter(
            and_(
                MemoryModel.user_id == user_id,
                memory_tags.c.tag_id == tag_id.value,
            )
        ).order_by(MemoryModel.created_at.desc()).offset(skip).limit(limit)
        
        results = await self.session.execute(
            query.options(
                selectinload(MemoryModel.tags),
                selectinload(MemoryModel.linked_to),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def get_linked_memories(
        self,
        memory_id: MemoryId,
        link_type: Optional[str] = None,
    ) -> list[Memory]:
        """Get memories linked to a specific memory."""
        query = self.session.query(MemoryModel).join(
            memory_links,
            MemoryModel.id == memory_links.c.to_memory_id
        ).filter(
            memory_links.c.from_memory_id == memory_id.value
        )
        
        if link_type:
            query = query.filter(memory_links.c.link_type == link_type)
        
        results = await self.session.execute(
            query.options(
                selectinload(MemoryModel.tags),
                selectinload(MemoryModel.linked_to),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def link_memories(
        self,
        from_memory_id: MemoryId,
        to_memory_id: MemoryId,
        link_type: Optional[str] = None,
    ) -> bool:
        """Create a link between memories."""
        stmt = memory_links.insert().values(
            from_memory_id=from_memory_id.value,
            to_memory_id=to_memory_id.value,
            link_type=link_type,
        )
        
        try:
            await self.session.execute(stmt)
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to link memories: {e}")
            return False
    
    async def unlink_memories(
        self,
        from_memory_id: MemoryId,
        to_memory_id: MemoryId,
    ) -> bool:
        """Remove a link between memories."""
        stmt = memory_links.delete().where(
            and_(
                memory_links.c.from_memory_id == from_memory_id.value,
                memory_links.c.to_memory_id == to_memory_id.value,
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
    
    async def update_access_time(self, memory_id: MemoryId) -> None:
        """Update the last access time for a memory."""
        memory = await self.session.get(MemoryModel, memory_id.value)
        if memory:
            memory.accessed_at = datetime.utcnow()
            memory.retrieval_count += 1
            await self.session.flush()
    
    async def count_by_user(self, user_id: UUID) -> int:
        """Count memories for a user."""
        result = await self.session.execute(
            func.count(MemoryModel.id).filter(MemoryModel.user_id == user_id)
        )
        return result.scalar() or 0
    
    def _to_domain(self, db_memory: MemoryModel) -> Memory:
        """Convert database model to domain model."""
        return Memory(
            id=MemoryId(db_memory.id),
            user_id=db_memory.user_id,
            title=db_memory.title,
            content=db_memory.content,
            memory_type=MemoryType(db_memory.memory_type),
            status=MemoryStatus(db_memory.status),
            importance_score=db_memory.importance_score,
            confidence_score=db_memory.confidence_score,
            source_url=db_memory.source_url,
            embedding=db_memory.embedding,
            embedding_model=db_memory.embedding_model,
            metadata=db_memory.metadata,
            created_at=db_memory.created_at,
            updated_at=db_memory.updated_at,
            accessed_at=db_memory.accessed_at,
            retention_strength=db_memory.retention_strength,
            retrieval_count=db_memory.retrieval_count,
            tags=[tag.id for tag in db_memory.tags],
            linked_memories=[MemoryId(mem.id) for mem in db_memory.linked_to],
            attachments=db_memory.attachments or [],
        )
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)