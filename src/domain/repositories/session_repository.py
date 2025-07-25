"""
Session repository interface.

Defines the contract for session persistence.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.models.session import Session, SessionId


class SessionRepository(ABC):
    """Abstract repository for session persistence."""
    
    @abstractmethod
    async def get(self, session_id: SessionId) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> list[Session]:
        """
        Get sessions for a user.
        
        Args:
            user_id: The user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            
        Returns:
            List of sessions
        """
        pass
    
    @abstractmethod
    async def save(self, session: Session) -> Session:
        """
        Save a session (create or update).
        
        Args:
            session: The session to save
            
        Returns:
            The saved session
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: SessionId) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_active_sessions(
        self,
        user_id: UUID,
        since: Optional[datetime] = None,
    ) -> list[Session]:
        """
        Get active sessions for a user.
        
        Args:
            user_id: The user ID
            since: Only return sessions active since this time
            
        Returns:
            List of active sessions
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
    ) -> list[Session]:
        """
        Search sessions by title or message content.
        
        Args:
            user_id: The user ID
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching sessions
        """
        pass
    
    @abstractmethod
    async def get_by_memory_reference(
        self,
        memory_id: UUID,
        user_id: UUID,
    ) -> list[Session]:
        """
        Get sessions that reference a specific memory.
        
        Args:
            memory_id: The memory ID
            user_id: The user ID
            
        Returns:
            List of sessions referencing the memory
        """
        pass
    
    @abstractmethod
    async def count_by_user(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Count sessions for a user.
        
        Args:
            user_id: The user ID
            is_active: Filter by active status
            
        Returns:
            Number of sessions
        """
        pass
    
    @abstractmethod
    async def cleanup_old_sessions(
        self,
        days: int = 30,
        keep_active: bool = True,
    ) -> int:
        """
        Clean up old sessions.
        
        Args:
            days: Delete sessions older than this many days
            keep_active: Whether to keep active sessions regardless of age
            
        Returns:
            Number of sessions deleted
        """
        pass