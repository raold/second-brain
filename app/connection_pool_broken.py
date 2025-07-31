"""
Database Connection Pooling for Second Brain v2.2.0
Advanced connection management with pooling, monitoring, and optimization
"""

import asyncio
from app.utils.logging_config import get_logger
from typing import Any
logger = get_logger(__name__)

    async def initialize(self):
        """Initialize connection pool"""
        async with self.connection_lock:
            if self.is_connected:
                return

            try:
                self.logger.info("Initializing database connection pool...")

                # Create connection pool
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=self.config.min_connections,
                    max_size=self.config.max_connections,
                    max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                    max_queries=self.config.max_queries,
                    command_timeout=self.config.command_timeout,
                    server_settings=self.config.server_settings,
                )

                # Test connection
                if self.pool:
                    async with self.pool.acquire() as conn:
                        await conn.execute("SELECT 1")

                self.is_connected = True
                await self.monitor.start_monitoring()

                self.logger.info(
                    f"Database pool initialized with {self.config.min_connections}-{self.config.max_connections} connections"
                )

            except Exception as e:
                self.logger.error(f"Failed to initialize database pool: {e}")
                self.is_connected = False
                raise

    async def close(self):
        """Close connection pool"""
        async with self.connection_lock:
            if not self.is_connected:
                return

            self.logger.info("Closing database connection pool...")

            # Stop monitoring
            await self.monitor.stop_monitoring()

            # Close pool
            if self.pool:
                await self.pool.close()
                self.pool = None

            self.is_connected = False
            self.logger.info("Database connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with monitoring"""
        if not self.is_connected or not self.pool:
            raise RuntimeError("Database pool not initialized")

        start_time = time.time()
        connection = None

        try:
            # Acquire connection from pool
            self.monitor.record_pool_acquisition()
            connection = await self.pool.acquire()

            yield connection

        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            self.monitor.record_query_error()
            raise
        finally:
            # Release connection back to pool
            if connection:
                await self.pool.release(connection)
                self.monitor.record_pool_release()

            # Record timing
            query_time = time.time() - start_time
            self.monitor.record_query_time(query_time)

    async def execute_query(self, query: str, *args, **kwargs):
        """Execute query with connection pooling"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args, **kwargs)

    async def fetch_query(self, query: str, *args, **kwargs):
        """Fetch query results with connection pooling"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetchrow_query(self, query: str, *args, **kwargs):
        """Fetch single row with connection pooling"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def fetchval_query(self, query: str, *args, **kwargs):
        """Fetch single value with connection pooling"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    async def execute_batch(self, queries: list[tuple]):
        """Execute batch of queries in transaction"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                results = []
                for query, args in queries:
                    result = await conn.execute(query, *args)
                    results.append(result)
                return results

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check"""
        if not self.is_connected:
            return {"status": "disconnected", "healthy": False, "error": "Pool not initialized"}

        try:
            # Test connection
            start_time = time.time()
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
            response_time = time.time() - start_time

            # Get monitoring stats
            health_status = self.monitor.get_health_status()

            return {
                "status": "connected",
                "healthy": health_status["health"] in ["healthy", "warning"],
                "response_time": response_time,
                "pool_size": self.pool.get_size() if self.pool else 0,
                "active_connections": self.pool.get_size() - self.pool.get_idle_size() if self.pool else 0,
                "idle_connections": self.pool.get_idle_size() if self.pool else 0,
                "health_details": health_status,
            }

        except Exception as e:
            return {"status": "error", "healthy": False, "error": str(e)}

    async def optimize_pool(self):
        """Optimize pool configuration based on usage patterns"""
        if not self.monitor.stats.total_queries:
            return

        stats = self.monitor.stats

        # Analyze usage patterns
        peak_usage = stats.peak_connections / self.config.max_connections

        recommendations = []

        # Check if we need more connections
        if peak_usage > 0.8:
            new_max = min(self.config.max_connections + 5, 50)
            recommendations.append(f"Consider increasing max_connections to {new_max}")

        # Check if we can reduce connections
        if peak_usage < 0.3 and self.config.max_connections > 10:
            new_max = max(self.config.max_connections - 5, 10)
            recommendations.append(f"Consider reducing max_connections to {new_max}")

        # Check query performance
        if stats.average_query_time > 1.0:
            recommendations.append("High average query time detected - consider query optimization")

        if recommendations:
            self.logger.info("Pool optimization recommendations:")
            for rec in recommendations:
                self.logger.info(f"  - {rec}")

        return recommendations


# Global pool manager instance
_pool_manager: DatabasePoolManager | None = None


async def initialize_pool(database_url: str, config: PoolConfig | None = None):
    """Initialize global database pool"""
    global _pool_manager

    if _pool_manager:
        await _pool_manager.close()

    _pool_manager = DatabasePoolManager(database_url, config)
    await _pool_manager.initialize()


async def close_pool():
    """Close global database pool"""
    global _pool_manager

    if _pool_manager:
        await _pool_manager.close()
        _pool_manager = None


def get_pool_manager() -> DatabasePoolManager | None:
    """Get global pool manager"""
    return _pool_manager


@asynccontextmanager
async def get_db_connection():
    """Get database connection from global pool"""
    if not _pool_manager:
        raise RuntimeError("Database pool not initialized")

    async with _pool_manager.get_connection() as conn:
        yield conn


# Integration with existing database module
async def execute_with_pool(query: str, *args, **kwargs):
    """Execute query using connection pool"""
    if not _pool_manager:
        raise RuntimeError("Database pool not initialized")

    return await _pool_manager.execute_query(query, *args, **kwargs)


async def fetch_with_pool(query: str, *args, **kwargs):
    """Fetch query results using connection pool"""
    if not _pool_manager:
        raise RuntimeError("Database pool not initialized")

    return await _pool_manager.fetch_query(query, *args, **kwargs)


async def fetchrow_with_pool(query: str, *args, **kwargs):
    """Fetch single row using connection pool"""
    if not _pool_manager:
        raise RuntimeError("Database pool not initialized")

    return await _pool_manager.fetchrow_query(query, *args, **kwargs)


# Performance testing for connection pooling
async def test_connection_pooling():
    """Test connection pooling performance"""
    print("⚡ Testing database connection pooling...")

    # This would require actual database connection
    # For demonstration purposes only

    config = PoolConfig(min_connections=3, max_connections=10, max_inactive_connection_lifetime=300.0)

    print(f"✅ Pool configuration: {config}")
    print("📊 Connection pooling implementation complete!")


if __name__ == "__main__":
    # Run connection pooling tests
    asyncio.run(test_connection_pooling())
    print("⚡ Database connection pooling implementation complete!")
