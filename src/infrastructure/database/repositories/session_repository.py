"""
Concrete session repository implementation using SQLAlchemy.

Implements the SessionRepository interface with PostgreSQL.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.memory import MemoryId
from src.domain.models.session import Session, SessionId
from src.domain.repositories.session_repository import SessionRepository
from src.infrastructure.database.models import SessionModel, session_memories
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLSessionRepository(SessionRepository):
    """SQL implementation of session repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get(self, session_id: SessionId) -> Optional[Session]:
        """Get a session by ID."""
        result = await self.session.get(
            SessionModel,
            session_id.value,
            options=[selectinload(SessionModel.memories)]
        )
        
        if not result:
            return None
        
        return self._to_domain(result)
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> list[Session]:
        """Get sessions for a user."""
        query = self.session.query(SessionModel).filter(
            SessionModel.user_id == user_id
        )
        
        if is_active is not None:
            query = query.filter(SessionModel.is_active == is_active)
        
        query = query.order_by(SessionModel.last_activity_at.desc())
        query = query.offset(skip).limit(limit)
        
        results = await self.session.execute(
            query.options(selectinload(SessionModel.memories))
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def save(self, session: Session) -> Session:
        """Save a session (create or update)."""
        # Check if session exists
        existing = await self.session.get(SessionModel, session.id.value)
        
        if existing:
            # Update existing
            existing.title = session.title
            existing.description = session.description
            existing.messages = session.messages
            existing.is_active = session.is_active
            existing.context = session.context
            existing.tags = session.tags
            existing.metadata = session.metadata
            existing.updated_at = datetime.utcnow()
            existing.last_activity_at = session.last_activity_at
            
            db_session = existing
        else:
            # Create new
            db_session = SessionModel(
                id=session.id.value,
                user_id=session.user_id,
                title=session.title,
                description=session.description,
                messages=session.messages,
                is_active=session.is_active,
                context=session.context,
                tags=session.tags,
                metadata=session.metadata,
                created_at=session.created_at,
                updated_at=session.updated_at,
                last_activity_at=session.last_activity_at,
            )
            self.session.add(db_session)
        
        await self.session.flush()
        return session
    
    async def delete(self, session_id: SessionId) -> bool:
        """Delete a session."""
        result = await self.session.get(SessionModel, session_id.value)
        if not result:
            return False
        
        await self.session.delete(result)
        await self.session.flush()
        return True
    
    async def get_active_sessions(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[Session]:
        """Get active sessions for a user."""
        results = await self.session.execute(
            self.session.query(SessionModel).filter(
                and_(
                    SessionModel.user_id == user_id,
                    SessionModel.is_active == True,
                )
            ).order_by(SessionModel.last_activity_at.desc()).limit(limit).options(
                selectinload(SessionModel.memories)
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
    ) -> list[Session]:
        """Search sessions by title or content."""
        search_query = f"%{query}%"
        
        results = await self.session.execute(
            self.session.query(SessionModel).filter(
                and_(
                    SessionModel.user_id == user_id,
                    (SessionModel.title.ilike(search_query)) |
                    (SessionModel.description.ilike(search_query)),
                )
            ).order_by(SessionModel.last_activity_at.desc()).limit(limit).options(
                selectinload(SessionModel.memories)
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def add_memory(
        self,
        session_id: SessionId,
        memory_id: MemoryId,
    ) -> bool:
        """Add a memory to a session."""
        stmt = session_memories.insert().values(
            session_id=session_id.value,
            memory_id=memory_id.value,
        )
        
        try:
            await self.session.execute(stmt)
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to add memory to session: {e}")
            return False
    
    async def remove_memory(
        self,
        session_id: SessionId,
        memory_id: MemoryId,
    ) -> bool:
        """Remove a memory from a session."""
        stmt = session_memories.delete().where(
            and_(
                session_memories.c.session_id == session_id.value,
                session_memories.c.memory_id == memory_id.value,
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
    
    async def get_memory_ids(self, session_id: SessionId) -> list[MemoryId]:
        """Get memory IDs for a session."""
        results = await self.session.execute(
            self.session.query(session_memories.c.memory_id).filter(
                session_memories.c.session_id == session_id.value
            )
        )
        
        return [MemoryId(row[0]) for row in results]
    
    async def update_activity(self, session_id: SessionId) -> None:
        """Update session's last activity timestamp."""
        session = await self.session.get(SessionModel, session_id.value)
        if session:
            session.last_activity_at = datetime.utcnow()
            await self.session.flush()
    
    async def count_by_user(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count sessions for a user."""
        query = func.count(SessionModel.id).filter(
            SessionModel.user_id == user_id
        )
        
        if is_active is not None:
            query = query.filter(SessionModel.is_active == is_active)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def close_inactive_sessions(
        self,
        inactive_hours: int = 24,
    ) -> int:
        """Close sessions that have been inactive."""
        cutoff = datetime.utcnow() - timedelta(hours=inactive_hours)
        
        result = await self.session.execute(
            self.session.query(SessionModel).filter(
                and_(
                    SessionModel.is_active == True,
                    SessionModel.last_activity_at < cutoff,
                )
            )
        )
        
        count = 0
        for session in result.scalars():
            session.is_active = False
            count += 1
        
        await self.session.flush()
        return count
    
    def _to_domain(self, db_session: SessionModel) -> Session:
        """Convert database model to domain model."""
        return Session(
            id=SessionId(db_session.id),
            user_id=db_session.user_id,
            title=db_session.title,
            description=db_session.description,
            messages=db_session.messages,
            is_active=db_session.is_active,
            context=db_session.context,
            tags=db_session.tags,
            metadata=db_session.metadata,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            last_activity_at=db_session.last_activity_at,
            memory_ids=[MemoryId(mem.id) for mem in db_session.memories],
        )