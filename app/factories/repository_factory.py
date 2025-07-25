"""
Factory for creating repository instances.

Implements the Abstract Factory pattern for repository creation
with different storage backends and configurations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

import asyncpg

from ..repositories.base_repository import BaseRepository
from ..repositories.memory_repository import MemoryRepository, PostgreSQLMemoryRepository
from ..repositories.session_repository import PostgreSQLSessionRepository, SessionRepository

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseRepository)


class RepositoryFactory(ABC):
    """
    Abstract factory for creating repository instances.

    Provides a consistent interface for creating repositories
    regardless of the underlying storage implementation.
    """

    @abstractmethod
    async def create_memory_repository(self) -> MemoryRepository:
        """Create a memory repository instance."""
        pass

    @abstractmethod
    async def create_session_repository(self) -> SessionRepository:
        """Create a session repository instance."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the storage backend."""
        pass

    @abstractmethod
    async def dispose(self) -> None:
        """Dispose factory resources."""
        pass


class PostgreSQLRepositoryFactory(RepositoryFactory):
    """
    PostgreSQL implementation of the repository factory.

    Creates PostgreSQL-backed repository instances with
    proper connection pool management.
    """

    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Initialize the PostgreSQL repository factory.

        Args:
            connection_pool: AsyncPG connection pool
        """
        self.connection_pool = connection_pool
        self._repositories: dict[type, BaseRepository] = {}

    async def create_memory_repository(self) -> MemoryRepository:
        """Create a PostgreSQL memory repository."""
        if MemoryRepository not in self._repositories:
            repository = PostgreSQLMemoryRepository(self.connection_pool)
            self._repositories[MemoryRepository] = repository
            logger.debug("Created PostgreSQL memory repository")

        return self._repositories[MemoryRepository]

    async def create_session_repository(self) -> SessionRepository:
        """Create a PostgreSQL session repository."""
        if SessionRepository not in self._repositories:
            repository = PostgreSQLSessionRepository(self.connection_pool)
            self._repositories[SessionRepository] = repository
            logger.debug("Created PostgreSQL session repository")

        return self._repositories[SessionRepository]

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on PostgreSQL connection."""
        try:
            async with self.connection_pool.acquire() as conn:
                # Test basic connectivity
                result = await conn.fetchval("SELECT 1")

                # Get pool stats
                pool_stats = {
                    'size': self.connection_pool.get_size(),
                    'min_size': self.connection_pool.get_min_size(),
                    'max_size': self.connection_pool.get_max_size(),
                    'idle_connections': self.connection_pool.get_idle_size()
                }

                # Test memory table exists
                memory_table_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')"
                )

                # Test session table exists
                session_table_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sessions')"
                )

                return {
                    'status': 'healthy',
                    'connection_test': result == 1,
                    'pool_stats': pool_stats,
                    'tables': {
                        'memories': memory_table_exists,
                        'sessions': session_table_exists
                    },
                    'repositories_created': len(self._repositories)
                }

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'repositories_created': len(self._repositories)
            }

    async def dispose(self) -> None:
        """Dispose factory resources."""
        # Clear repository cache
        self._repositories.clear()

        # Note: We don't close the connection pool here as it might be
        # shared with other components. Pool lifecycle should be managed
        # at the application level.
        logger.debug("Disposed PostgreSQL repository factory")


class MockRepositoryFactory(RepositoryFactory):
    """
    Mock implementation for testing purposes.

    Creates in-memory repository implementations that don't
    require a real database connection.
    """

    def __init__(self):
        self._repositories: dict[type, BaseRepository] = {}
        self._mock_data: dict[str, Any] = {
            'memories': {},
            'sessions': {}
        }

    async def create_memory_repository(self) -> MemoryRepository:
        """Create a mock memory repository."""
        if MemoryRepository not in self._repositories:
            # For testing, we'd implement MockMemoryRepository
            # For now, return a special instance that uses mock data
            repository = MockMemoryRepository(self._mock_data['memories'])
            self._repositories[MemoryRepository] = repository
            logger.debug("Created mock memory repository")

        return self._repositories[MemoryRepository]

    async def create_session_repository(self) -> SessionRepository:
        """Create a mock session repository."""
        if SessionRepository not in self._repositories:
            repository = MockSessionRepository(self._mock_data['sessions'])
            self._repositories[SessionRepository] = repository
            logger.debug("Created mock session repository")

        return self._repositories[SessionRepository]

    async def health_check(self) -> dict[str, Any]:
        """Mock health check always returns healthy."""
        return {
            'status': 'healthy',
            'mock_data_size': {
                'memories': len(self._mock_data['memories']),
                'sessions': len(self._mock_data['sessions'])
            },
            'repositories_created': len(self._repositories)
        }

    async def dispose(self) -> None:
        """Dispose mock resources."""
        self._repositories.clear()
        self._mock_data.clear()
        logger.debug("Disposed mock repository factory")


# Mock repository implementations (simplified for example)

class MockMemoryRepository(MemoryRepository):
    """Mock implementation of memory repository for testing."""

    def __init__(self, mock_data: dict[str, Any]):
        self.mock_data = mock_data
        super().__init__(None)  # No connection pool needed

    @property
    def table_name(self) -> str:
        return "mock_memories"

    async def _map_row_to_entity(self, row):
        # Implementation would depend on your Memory model
        pass

    async def _map_entity_to_values(self, entity):
        # Implementation would depend on your Memory model
        pass

    async def save(self, memory) -> str:
        memory_id = memory.id
        self.mock_data[memory_id] = memory
        return memory_id

    async def update(self, memory) -> bool:
        if memory.id in self.mock_data:
            self.mock_data[memory.id] = memory
            return True
        return False

    async def search_by_content(self, query: str, limit: int = 50, **kwargs):
        # Simple mock search
        return [mem for mem in self.mock_data.values() if query.lower() in mem.content.lower()][:limit]

    async def search_by_criteria(self, criteria):
        # Mock implementation
        return list(self.mock_data.values())[:criteria.limit or 50]

    async def find_by_user(self, user_id: str, limit: int = 100):
        return [mem for mem in self.mock_data.values() if mem.user_id == user_id][:limit]

    async def find_related(self, memory_id: str, limit: int = 10):
        # Mock related memories
        return list(self.mock_data.values())[:limit]

    async def get_metrics(self, user_id: Optional[str] = None):
        from datetime import datetime

        from ..models.memory import MemoryMetrics

        total_count = len(self.mock_data)
        return MemoryMetrics(
            total_memories=total_count,
            memories_by_type={},
            average_importance=0.5,
            recent_memories=total_count,
            total_access_count=0,
            last_updated=datetime.utcnow()
        )

    async def update_importance_score(self, memory_id: str, score: float) -> bool:
        if memory_id in self.mock_data:
            self.mock_data[memory_id].importance_score = score
            return True
        return False

    async def mark_as_accessed(self, memory_id: str) -> None:
        if memory_id in self.mock_data:
            memory = self.mock_data[memory_id]
            memory.access_count = getattr(memory, 'access_count', 0) + 1


class MockSessionRepository(SessionRepository):
    """Mock implementation of session repository for testing."""

    def __init__(self, mock_data: dict[str, Any]):
        self.mock_data = mock_data
        super().__init__(None)  # No connection pool needed

    @property
    def table_name(self) -> str:
        return "mock_sessions"

    async def _map_row_to_entity(self, row):
        pass

    async def _map_entity_to_values(self, entity):
        pass

    async def create_session(self, user_id: str, metadata: Optional[dict[str, Any]] = None) -> str:
        from datetime import datetime
        from uuid import uuid4

        from ..repositories.session_repository import Session

        session_id = str(uuid4())
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.mock_data[session_id] = session
        return session_id

    async def find_by_session_id(self, session_id: str):
        return self.mock_data.get(session_id)

    async def find_active_sessions(self, user_id: str):
        return [s for s in self.mock_data.values() if s.user_id == user_id and s.is_active]

    async def update_access_time(self, session_id: str) -> bool:
        if session_id in self.mock_data:
            from datetime import datetime
            self.mock_data[session_id].last_accessed = datetime.utcnow()
            return True
        return False

    async def deactivate_session(self, session_id: str) -> bool:
        if session_id in self.mock_data:
            self.mock_data[session_id].is_active = False
            return True
        return False

    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        from datetime import datetime, timedelta

        expired_count = 0
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        for session in list(self.mock_data.values()):
            if session.last_accessed < cutoff_time:
                session.is_active = False
                expired_count += 1

        return expired_count


# Factory creation functions

async def create_postgresql_factory(connection_pool: asyncpg.Pool) -> PostgreSQLRepositoryFactory:
    """
    Create a PostgreSQL repository factory.

    Args:
        connection_pool: AsyncPG connection pool

    Returns:
        Configured PostgreSQL repository factory
    """
    factory = PostgreSQLRepositoryFactory(connection_pool)

    # Perform health check to ensure factory is working
    health = await factory.health_check()
    if health['status'] != 'healthy':
        logger.warning(f"PostgreSQL factory health check failed: {health}")

    return factory


def create_mock_factory() -> MockRepositoryFactory:
    """
    Create a mock repository factory for testing.

    Returns:
        Mock repository factory
    """
    return MockRepositoryFactory()


# Global factory instance management

_repository_factory: Optional[RepositoryFactory] = None


def get_repository_factory() -> RepositoryFactory:
    """Get the global repository factory instance."""
    global _repository_factory
    if _repository_factory is None:
        # Default to mock factory if none set
        _repository_factory = create_mock_factory()
        logger.warning("Using mock repository factory as default")
    return _repository_factory


async def set_repository_factory(factory: RepositoryFactory) -> None:
    """Set the global repository factory instance."""
    global _repository_factory

    # Dispose previous factory if it exists
    if _repository_factory is not None:
        await _repository_factory.dispose()

    _repository_factory = factory

    # Verify new factory health
    health = await factory.health_check()
    logger.info(f"Repository factory set with health status: {health['status']}")


async def dispose_repository_factory() -> None:
    """Dispose the global repository factory."""
    global _repository_factory
    if _repository_factory is not None:
        await _repository_factory.dispose()
        _repository_factory = None
