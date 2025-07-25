"""
Redis caching layer for graph metrics
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    RedisError = Exception
    REDIS_AVAILABLE = False

from app.config import get_settings
from app.models.synthesis.metrics_models import GraphMetrics
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GraphCacheService:
    """Service for caching graph metrics and related data"""

    def __init__(self):
        self.redis_client = None
        self.cache_ttl = timedelta(minutes=15)  # Default TTL
        self.is_connected = False

    async def connect(self):
        """Initialize Redis connection"""
        if self.is_connected:
            return

        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if hasattr(settings, 'REDIS_PASSWORD') else None,
                decode_responses=False  # We'll handle encoding/decoding
            )

            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to Redis cache")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Running without cache.")
            self.redis_client = None
            self.is_connected = False

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False

    async def get_metrics(
        self,
        user_id: str,
        graph_id: str = "main"
    ) -> Optional[GraphMetrics]:
        """Get cached graph metrics"""
        if not self.is_connected:
            return None

        try:
            key = self._get_metrics_key(user_id, graph_id)
            data = await self.redis_client.get(key)

            if data:
                metrics_dict = json.loads(data)
                # Convert timestamp string back to datetime
                metrics_dict['timestamp'] = datetime.fromisoformat(metrics_dict['timestamp'])
                return GraphMetrics(**metrics_dict)

            return None

        except Exception as e:
            logger.error(f"Error getting cached metrics: {e}")
            return None

    async def set_metrics(
        self,
        user_id: str,
        graph_id: str,
        metrics: GraphMetrics,
        ttl: Optional[timedelta] = None
    ):
        """Cache graph metrics"""
        if not self.is_connected:
            return

        try:
            key = self._get_metrics_key(user_id, graph_id)

            # Convert to dict and handle datetime
            metrics_dict = metrics.dict()
            metrics_dict['timestamp'] = metrics_dict['timestamp'].isoformat()

            data = json.dumps(metrics_dict)

            ttl = ttl or self.cache_ttl
            await self.redis_client.setex(
                key,
                int(ttl.total_seconds()),
                data
            )

        except Exception as e:
            logger.error(f"Error caching metrics: {e}")

    async def get_graph(
        self,
        user_id: str,
        graph_type: str = "main"
    ) -> Optional[Any]:
        """Get cached graph object (NetworkX)"""
        if not self.is_connected:
            return None

        try:
            key = self._get_graph_key(user_id, graph_type)
            data = await self.redis_client.get(key)

            if data:
                return pickle.loads(data)

            return None

        except Exception as e:
            logger.error(f"Error getting cached graph: {e}")
            return None

    async def set_graph(
        self,
        user_id: str,
        graph_type: str,
        graph: Any,
        ttl: Optional[timedelta] = None
    ):
        """Cache graph object"""
        if not self.is_connected:
            return

        try:
            key = self._get_graph_key(user_id, graph_type)
            data = pickle.dumps(graph)

            ttl = ttl or self.cache_ttl
            await self.redis_client.setex(
                key,
                int(ttl.total_seconds()),
                data
            )

        except Exception as e:
            logger.error(f"Error caching graph: {e}")

    async def get_visualization_data(
        self,
        user_id: str,
        viz_type: str
    ) -> Optional[dict[str, Any]]:
        """Get cached visualization data"""
        if not self.is_connected:
            return None

        try:
            key = self._get_viz_key(user_id, viz_type)
            data = await self.redis_client.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Error getting cached visualization: {e}")
            return None

    async def set_visualization_data(
        self,
        user_id: str,
        viz_type: str,
        data: dict[str, Any],
        ttl: Optional[timedelta] = None
    ):
        """Cache visualization data"""
        if not self.is_connected:
            return

        try:
            key = self._get_viz_key(user_id, viz_type)
            json_data = json.dumps(data)

            ttl = ttl or self.cache_ttl
            await self.redis_client.setex(
                key,
                int(ttl.total_seconds()),
                json_data
            )

        except Exception as e:
            logger.error(f"Error caching visualization: {e}")

    async def get_summary(
        self,
        user_id: str,
        summary_type: str,
        target: str
    ) -> Optional[dict[str, Any]]:
        """Get cached summary"""
        if not self.is_connected:
            return None

        try:
            key = self._get_summary_key(user_id, summary_type, target)
            data = await self.redis_client.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Error getting cached summary: {e}")
            return None

    async def set_summary(
        self,
        user_id: str,
        summary_type: str,
        target: str,
        summary: dict[str, Any],
        ttl: Optional[timedelta] = None
    ):
        """Cache summary data"""
        if not self.is_connected:
            return

        try:
            key = self._get_summary_key(user_id, summary_type, target)
            data = json.dumps(summary)

            ttl = ttl or timedelta(hours=1)  # Summaries cached longer
            await self.redis_client.setex(
                key,
                int(ttl.total_seconds()),
                data
            )

        except Exception as e:
            logger.error(f"Error caching summary: {e}")

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        if not self.is_connected:
            return

        try:
            # Find all keys for user
            pattern = f"secondbrain:{user_id}:*"
            cursor = 0

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    await self.redis_client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Invalidated cache for user {user_id}")

        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")

    async def invalidate_metrics(self, user_id: str, graph_id: str = "main"):
        """Invalidate specific metrics cache"""
        if not self.is_connected:
            return

        try:
            key = self._get_metrics_key(user_id, graph_id)
            await self.redis_client.delete(key)

        except Exception as e:
            logger.error(f"Error invalidating metrics: {e}")

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        if not self.is_connected:
            return {"connected": False}

        try:
            info = await self.redis_client.info()

            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_keys": await self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0)
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}

    def _get_metrics_key(self, user_id: str, graph_id: str) -> str:
        """Generate cache key for metrics"""
        return f"secondbrain:{user_id}:metrics:{graph_id}"

    def _get_graph_key(self, user_id: str, graph_type: str) -> str:
        """Generate cache key for graph object"""
        return f"secondbrain:{user_id}:graph:{graph_type}"

    def _get_viz_key(self, user_id: str, viz_type: str) -> str:
        """Generate cache key for visualization"""
        return f"secondbrain:{user_id}:viz:{viz_type}"

    def _get_summary_key(self, user_id: str, summary_type: str, target: str) -> str:
        """Generate cache key for summary"""
        # Clean target for use in key
        clean_target = target.replace(" ", "_").replace(":", "").lower()[:50]
        return f"secondbrain:{user_id}:summary:{summary_type}:{clean_target}"

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100

    async def warm_cache(self, user_id: str):
        """Pre-warm cache with commonly accessed data"""
        # This would be implemented based on usage patterns
        pass

    async def set_lock(
        self,
        key: str,
        ttl: timedelta = timedelta(seconds=30)
    ) -> bool:
        """Set a distributed lock"""
        if not self.is_connected:
            return True  # Allow operation without cache

        try:
            lock_key = f"secondbrain:lock:{key}"
            result = await self.redis_client.set(
                lock_key,
                "1",
                nx=True,  # Only set if not exists
                ex=int(ttl.total_seconds())
            )
            return bool(result)

        except Exception as e:
            logger.error(f"Error setting lock: {e}")
            return True  # Allow operation on error

    async def release_lock(self, key: str):
        """Release a distributed lock"""
        if not self.is_connected:
            return

        try:
            lock_key = f"secondbrain:lock:{key}"
            await self.redis_client.delete(lock_key)

        except Exception as e:
            logger.error(f"Error releasing lock: {e}")


# Singleton instance
_cache_service = None


async def get_cache_service() -> GraphCacheService:
    """Get or create cache service instance"""
    global _cache_service

    if _cache_service is None:
        _cache_service = GraphCacheService()
        await _cache_service.connect()

    return _cache_service
