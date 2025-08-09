"""
Database connection and management - Clean implementation
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg


class Database:
    """Database connection manager."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.is_connected = False

    async def connect(self):
        """Connect to the database."""
        if self.is_connected:
            return

        try:
            # Try to get database URL from environment
            database_url = os.getenv("DATABASE_URL", "postgresql://localhost/secondbrain")

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                database_url, min_size=1, max_size=10, command_timeout=60
            )
            self.is_connected = True
            print("✅ Database connected")
        except Exception as e:
            print(f"⚠️ Database connection failed: {e}")
            # Don't fail - app can work without database for now
            self.is_connected = False

    async def disconnect(self):
        """Disconnect from the database."""
        if self.pool:
            await self.pool.close()
            self.is_connected = False
            print("👋 Database disconnected")

    async def execute(self, query: str, *args):
        """Execute a query."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_one(self, query: str, *args):
        """Fetch one row."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args):
        """Fetch all rows."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)


# Global database instance
_database: Optional[Database] = None


async def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = Database()
        await _database.connect()
    return _database


@asynccontextmanager
async def database_session():
    """Context manager for database operations."""
    db = await get_database()
    try:
        yield db
    finally:
        # Cleanup if needed
        pass
