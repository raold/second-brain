"""
Dependency injection container for the application.

Manages creation and lifecycle of services and repositories.
"""

import os
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
from src.infrastructure.messaging import EventPublisher, MessageBroker, get_message_broker
from src.infrastructure.caching import Cache, get_cache

logger = get_logger(__name__)


class Dependencies:
    """
    Dependency injection container.
    
    Manages the creation and lifecycle of application dependencies.
    """
    
    def __init__(self):
        """Initialize dependencies container."""
        self._db_connection: Optional[DatabaseConnection] = None
        self._message_broker: Optional[MessageBroker] = None
        self._event_publisher: Optional[EventPublisher] = None
        self._cache: Optional[Cache] = None
        self._repositories: dict[str, object] = {}
        self._services: dict[str, object] = {}
    
    async def initialize(self) -> None:
        """Initialize all dependencies."""
        logger.info("Initializing dependencies")
        
        # Initialize database connection
        self._db_connection = await get_connection()
        
        # Initialize message broker
        broker_url = os.getenv("MESSAGE_BROKER_URL", "amqp://guest:guest@localhost:5672/")
        if broker_url and broker_url != "none":
            try:
                self._message_broker = await get_message_broker(broker_url)
                self._event_publisher = EventPublisher(self._message_broker)
                logger.info("Message broker connected")
            except Exception as e:
                logger.warning(f"Failed to connect to message broker: {e}")
                # Continue without message broker - events will be logged only
        
        # Initialize cache
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        if redis_url and redis_url != "none":
            try:
                self._cache = await get_cache(redis_url)
                logger.info("Cache connected")
            except Exception as e:
                logger.warning(f"Failed to connect to cache: {e}")
                # Continue without cache
        
        logger.info("Dependencies initialized")
    
    async def close(self) -> None:
        """Close all dependencies."""
        logger.info("Closing dependencies")
        
        # Close cache
        if self._cache:
            await self._cache.close()
        
        # Close message broker
        if self._message_broker:
            await self._message_broker.disconnect()
        
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
    
    async def get_message_broker(self) -> Optional[MessageBroker]:
        """Get message broker instance."""
        return self._message_broker
    
    async def get_event_publisher(self) -> Optional[EventPublisher]:
        """Get event publisher instance."""
        return self._event_publisher
    
    async def get_cache(self) -> Optional[Cache]:
        """Get cache instance."""
        return self._cache


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