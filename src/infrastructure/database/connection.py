"""
Database connection management.

Handles PostgreSQL connections with async support.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """Manages database connections."""
    
    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database connection.
        
        Args:
            database_url: PostgreSQL connection string
            echo: Whether to log SQL statements
        """
        self.database_url = database_url
        self.echo = echo
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
    
    async def initialize(self) -> None:
        """Initialize the database engine."""
        if self._engine:
            return
        
        logger.info("Initializing database connection")
        
        # Create async engine
        self._engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            poolclass=NullPool,  # Disable pooling for now
            future=True,
        )
        
        # Create session factory
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("Database connection initialized")
    
    async def close(self) -> None:
        """Close the database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session.
        
        Yields:
            Database session
        """
        if not self._sessionmaker:
            await self.initialize()
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if not self._engine:
            raise RuntimeError("Database not initialized")
        return self._engine


# Global connection instance
_connection: Optional[DatabaseConnection] = None


async def get_connection() -> DatabaseConnection:
    """
    Get the global database connection.
    
    Returns:
        Database connection instance
    """
    global _connection
    
    if not _connection:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://secondbrain:changeme@localhost:5432/secondbrain"
        )
        _connection = DatabaseConnection(database_url)
        await _connection.initialize()
    
    return _connection