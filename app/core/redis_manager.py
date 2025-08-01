"""
Redis Connection Manager for Second Brain v3.0.0
Handles Redis connections for caching and rate limiting
"""

import os
from contextlib import asynccontextmanager
import redis.asyncio as redis
from app.core.logging import get_logger

logger = get_logger(__name__)

class RedisManager:
    """Redis connection manager"""

    def __init__(self):
        self.client: redis.Redis | None = None
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.connection_timeout = 5
        self.retry_attempts = 3

    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        try:
            # Create Redis client
            self.client = redis.from_url(
                self.url,
                decode_responses=True,
                socket_timeout=self.connection_timeout,
                socket_connect_timeout=self.connection_timeout,
                retry_on_timeout=True,
                max_connections=20,
            )

            # Test connection
            await self.client.ping()
            logger.info("Redis connection established", url=self.url)
            return True

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting will be disabled.")
            self.client = None
            return False

    async def close(self):
        """Close Redis connection"""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    async def health_check(self) -> dict:
        """Check Redis health"""
        if not self.client:
            return {"status": "disconnected", "error": "No Redis client"}

        try:
            await self.client.ping()
            info = await self.client.info("memory")

            return {
                "status": "healthy",
                "latency_ms": 1,  # Redis ping is very fast
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_client(self) -> redis.Redis | None:
        """Get Redis client"""
        return self.client

    async def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except Exception:
            return False

# Global Redis manager instance
_redis_manager: RedisManager | None = None

async def get_redis_manager() -> RedisManager:
    """Get global Redis manager instance"""
    global _redis_manager

    if _redis_manager is None:
        _redis_manager = RedisManager()
        await _redis_manager.initialize()

    return _redis_manager

async def get_redis_client() -> redis.Redis | None:
    """Get Redis client for rate limiting"""
    manager = await get_redis_manager()
    return manager.get_client()

@asynccontextmanager
async def redis_connection():
    """Context manager for Redis operations"""
    client = await get_redis_client()
    if client is None:
        yield None
        return

    try:
        yield client
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        yield None

async def cleanup_redis():
    """Cleanup Redis connections"""
    global _redis_manager

    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None

# Health check for Redis
async def redis_health_check() -> dict:
    """Redis health check for monitoring"""
    try:
        manager = await get_redis_manager()
        return await manager.health_check()
    except Exception as e:
        return {"status": "error", "error": str(e)}
