"""
Session repository implementation following Repository pattern.

Provides data access abstraction for Session entities.
"""

import json
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional

import asyncpg

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class Session:
    """Domain entity for user sessions."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        created_at: datetime,
        last_accessed: datetime,
        metadata: Optional[dict[str, Any]] = None,
        is_active: bool = True
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.last_accessed = last_accessed
        self.metadata = metadata or {}
        self.is_active = is_active

    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the session."""
        self.is_active = False

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired."""
        if not self.is_active:
            return True

        time_diff = datetime.utcnow() - self.last_accessed
        return time_diff.total_seconds() > (timeout_minutes * 60)


class SessionRepository(BaseRepository[Session]):
    """
    Abstract repository interface for Session entities.
    """

    @abstractmethod
    async def create_session(self, user_id: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Create a new session and return session ID."""
        pass

    @abstractmethod
    async def find_by_session_id(self, session_id: str) -> Optional[Session]:
        """Find session by session ID."""
        pass

    @abstractmethod
    async def find_active_sessions(self, user_id: str) -> list[Session]:
        """Find all active sessions for a user."""
        pass

    @abstractmethod
    async def update_access_time(self, session_id: str) -> bool:
        """Update the last accessed time for a session."""
        pass

    @abstractmethod
    async def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session."""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """Remove expired sessions and return count of removed sessions."""
        pass


class PostgreSQLSessionRepository(SessionRepository):
    """
    PostgreSQL implementation of the Session repository.
    """

    @property
    def table_name(self) -> str:
        return "sessions"

    async def _map_row_to_entity(self, row: asyncpg.Record) -> Session:
        """Map database row to Session entity."""
        return Session(
            session_id=row['session_id'],
            user_id=row['user_id'],
            created_at=row['created_at'],
            last_accessed=row['last_accessed'],
            metadata=json.loads(row['metadata']) if row.get('metadata') else {},
            is_active=row.get('is_active', True)
        )

    async def _map_entity_to_values(self, session: Session) -> dict[str, Any]:
        """Map Session entity to database values."""
        return {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'created_at': session.created_at,
            'last_accessed': session.last_accessed,
            'metadata': json.dumps(session.metadata),
            'is_active': session.is_active
        }

    async def create_session(self, user_id: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Create a new session and return session ID."""
        from uuid import uuid4

        session_id = str(uuid4())
        now = datetime.utcnow()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_accessed=now,
            metadata=metadata or {},
            is_active=True
        )

        values = await self._map_entity_to_values(session)

        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO sessions (
                    session_id, user_id, created_at, last_accessed, metadata, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING session_id
            """

            result = await conn.fetchval(
                query,
                values['session_id'],
                values['user_id'],
                values['created_at'],
                values['last_accessed'],
                values['metadata'],
                values['is_active']
            )

            await self._log_operation('create_session', session_id, user_id=user_id)
            return result

    async def find_by_session_id(self, session_id: str) -> Optional[Session]:
        """Find session by session ID."""
        session = await self.find_by_id(session_id)
        if session:
            await self._log_operation('find_by_session_id', session_id)
        return session

    async def find_active_sessions(self, user_id: str) -> list[Session]:
        """Find all active sessions for a user."""
        where_clause = "user_id = $1 AND is_active = TRUE"
        params = [user_id]

        sessions = await self.find_by_criteria(
            where_clause,
            params,
            order_by="last_accessed DESC"
        )

        await self._log_operation('find_active_sessions', user_id=user_id, count=len(sessions))
        return sessions

    async def update_access_time(self, session_id: str) -> bool:
        """Update the last accessed time for a session."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE sessions
                SET last_accessed = $2
                WHERE session_id = $1 AND is_active = TRUE
            """

            result = await conn.execute(query, session_id, datetime.utcnow())
            rows_affected = int(result.split()[-1]) if result.split() else 0
            success = rows_affected > 0

            if success:
                await self._log_operation('update_access_time', session_id)

            return success

    async def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE sessions
                SET is_active = FALSE
                WHERE session_id = $1
            """

            result = await conn.execute(query, session_id)
            rows_affected = int(result.split()[-1]) if result.split() else 0
            success = rows_affected > 0

            if success:
                await self._log_operation('deactivate_session', session_id)

            return success

    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """Remove expired sessions and return count of removed sessions."""
        async with self.pool.acquire() as conn:
            # First deactivate expired sessions
            deactivate_query = """
                UPDATE sessions
                SET is_active = FALSE
                WHERE is_active = TRUE
                  AND last_accessed < NOW() - INTERVAL '%s minutes'
            """ % timeout_minutes

            deactivate_result = await conn.execute(deactivate_query)
            deactivated_count = int(deactivate_result.split()[-1]) if deactivate_result.split() else 0

            # Then delete very old inactive sessions (older than 7 days)
            delete_query = """
                DELETE FROM sessions
                WHERE is_active = FALSE
                  AND last_accessed < NOW() - INTERVAL '7 days'
            """

            delete_result = await conn.execute(delete_query)
            deleted_count = int(delete_result.split()[-1]) if delete_result.split() else 0

            total_cleaned = deactivated_count + deleted_count

            await self._log_operation(
                'cleanup_expired_sessions',
                deactivated=deactivated_count,
                deleted=deleted_count,
                total=total_cleaned
            )

            return total_cleaned
