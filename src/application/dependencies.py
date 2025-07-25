"""
Dependency injection container for the application.

Manages creation and lifecycle of services and repositories.
"""

from typing import Optional

from src.domain.repositories.event_store import EventStore
from src.domain.repositories.memory_repository import MemoryRepository
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.tag_repository import TagRepository
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database import (
    DatabaseConnection,
    SQLEventStore,
    SQLMemoryRepository,
    SQLSessionRepository,
    SQLTagRepository,
    SQLUserRepository,
    get_connection,
)
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class Dependencies:
    """
    Dependency injection container.
    
    Manages the creation and lifecycle of application dependencies.
    """
    
    def __init__(self):
        """Initialize dependencies container."""
        self._db_connection: Optional[DatabaseConnection] = None
        self._repositories: dict[str, object] = {}
        self._services: dict[str, object] = {}
    
    async def initialize(self) -> None:
        """Initialize all dependencies."""
        logger.info("Initializing dependencies")
        
        # Initialize database connection
        self._db_connection = await get_connection()
        
        logger.info("Dependencies initialized")
    
    async def close(self) -> None:
        """Close all dependencies."""
        logger.info("Closing dependencies")
        
        # Close database connection
        if self._db_connection:
            await self._db_connection.close()
        
        # Clear caches
        self._repositories.clear()
        self._services.clear()
        
        logger.info("Dependencies closed")
    
    async def get_db_connection(self) -> DatabaseConnection:
        """Get database connection."""
        if not self._db_connection:
            self._db_connection = await get_connection()
        return self._db_connection
    
    async def get_user_repository(self) -> UserRepository:
        """Get user repository instance."""
        if "user_repository" not in self._repositories:
            async with self._db_connection.get_session() as session:
                self._repositories["user_repository"] = SQLUserRepository(session)
        return self._repositories["user_repository"]
    
    async def get_memory_repository(self) -> MemoryRepository:
        """Get memory repository instance."""
        if "memory_repository" not in self._repositories:
            async with self._db_connection.get_session() as session:
                self._repositories["memory_repository"] = SQLMemoryRepository(session)
        return self._repositories["memory_repository"]
    
    async def get_session_repository(self) -> SessionRepository:
        """Get session repository instance."""
        if "session_repository" not in self._repositories:
            async with self._db_connection.get_session() as session:
                self._repositories["session_repository"] = SQLSessionRepository(session)
        return self._repositories["session_repository"]
    
    async def get_tag_repository(self) -> TagRepository:
        """Get tag repository instance."""
        if "tag_repository" not in self._repositories:
            async with self._db_connection.get_session() as session:
                self._repositories["tag_repository"] = SQLTagRepository(session)
        return self._repositories["tag_repository"]
    
    async def get_event_store(self) -> EventStore:
        """Get event store instance."""
        if "event_store" not in self._repositories:
            async with self._db_connection.get_session() as session:
                self._repositories["event_store"] = SQLEventStore(session)
        return self._repositories["event_store"]
    
    async def begin_transaction(self):
        """Begin a new database transaction."""
        return self._db_connection.get_session()


# Global dependencies instance
_dependencies: Optional[Dependencies] = None


async def get_dependencies() -> Dependencies:
    """
    Get the global dependencies instance.
    
    Returns:
        Dependencies container
    """
    global _dependencies
    
    if not _dependencies:
        _dependencies = Dependencies()
        await _dependencies.initialize()
    
    return _dependencies


async def reset_dependencies() -> None:
    """Reset the global dependencies instance."""
    global _dependencies
    
    if _dependencies:
        await _dependencies.close()
        _dependencies = None