"""
Embedding cache implementation for performance optimization.
Caches OpenAI embeddings to reduce API calls and improve response times.
"""

import hashlib
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import redis.asyncio as aioredis
from app.utils.logging_config import get_logger
from typing import Optional
from typing import Dict
from typing import List
from typing import Tuple
from datetime import datetime
from datetime import timedelta

logger = get_logger(__name__)


class EmbeddingCache:
    """Cache for OpenAI embeddings with Redis and in-memory LRU cache."""
    
    def __init__(self, redis_url: Optional[str] = None, ttl_hours: int = 24, memory_cache_size: int = 1000):
        """
        Initialize embedding cache.
        
        Args:
            redis_url: Redis connection URL (optional)
            ttl_hours: Time-to-live for cache entries in hours
            memory_cache_size: Size of in-memory LRU cache
        """
        self.redis_client: Optional[aioredis.Redis] = None
        self.redis_url = redis_url
        self.ttl_seconds = ttl_hours * 3600
        self.memory_cache: Dict[str, Tuple[List[float], datetime]] = {}
        self.memory_cache_size = memory_cache_size
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Stats tracking
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "api_calls": 0,
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize Redis connection if available."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            if self.redis_url:
                try:
                    self.redis_client = await aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=False
                    )
                    await self.redis_client.ping()
                    logger.info("Redis embedding cache initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize Redis cache: {e}")
                    self.redis_client = None
            
            self._initialized = True
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate consistent cache key for text and model."""
        content = f"{model}:{text}"
        return f"emb:{hashlib.sha256(content.encode()).hexdigest()[:32]}"
    
    async def get_embedding(
        self,
        text: str,
        model: str,
        generate_func
    ) -> List[float]:
        """
        Get embedding from cache or generate new one.
        
        Args:
            text: Text to get embedding for
            model: Model name
            generate_func: Async function to generate embedding if not cached
            
        Returns:
            Embedding vector
        """
        await self.initialize()
        
        cache_key = self._get_cache_key(text, model)
        
        # Check memory cache first (fastest)
        embedding = self._get_from_memory_cache(cache_key)
        if embedding is not None:
            self.stats["memory_hits"] += 1
            return embedding
        
        self.stats["memory_misses"] += 1
        
        # Check Redis cache (fast)
        if self.redis_client:
            embedding = await self._get_from_redis(cache_key)
            if embedding is not None:
                self.stats["redis_hits"] += 1
                # Update memory cache
                await self._update_memory_cache(cache_key, embedding)
                return embedding
            
            self.stats["redis_misses"] += 1
        
        # Generate new embedding (slow)
        try:
            self.stats["api_calls"] += 1
            embedding = await generate_func(text)
            
            # Cache the result
            await self._cache_embedding(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _get_from_memory_cache(self, key: str) -> Optional[List[float]]:
        """Get embedding from memory cache if not expired."""
        if key not in self.memory_cache:
            return None
            
        embedding, timestamp = self.memory_cache[key]
        
        # Check if expired
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self.memory_cache[key]
            return None
            
        # Move to end (LRU behavior)
        del self.memory_cache[key]
        self.memory_cache[key] = (embedding, timestamp)
        
        return embedding
    
    async def _get_from_redis(self, key: str) -> Optional[List[float]]:
        """Get embedding from Redis cache."""
        if not self.redis_client:
            return None
            
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
            
        return None
    
    async def _cache_embedding(self, key: str, embedding: List[float]):
        """Cache embedding in both memory and Redis."""
        # Update memory cache
        await self._update_memory_cache(key, embedding)
        
        # Update Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    key,
                    self.ttl_seconds,
                    json.dumps(embedding)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
    
    async def _update_memory_cache(self, key: str, embedding: List[float]):
        """Update memory cache with LRU eviction."""
        async with self._lock:
            # Remove oldest entry if at capacity
            if len(self.memory_cache) >= self.memory_cache_size and key not in self.memory_cache:
                # Remove first (oldest) item
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
            
            # Add to end
            self.memory_cache[key] = (embedding, datetime.now())
    
    async def clear_cache(self):
        """Clear all caches."""
        async with self._lock:
            self.memory_cache.clear()
            
        if self.redis_client:
            try:
                # Clear all embedding keys
                keys = await self.redis_client.keys("emb:*")
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Failed to clear Redis cache: {e}")
    
    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        total_requests = (
            self.stats["memory_hits"] + 
            self.stats["memory_misses"]
        )
        
        memory_hit_rate = (
            self.stats["memory_hits"] / total_requests 
            if total_requests > 0 else 0
        )
        
        redis_requests = (
            self.stats["redis_hits"] + 
            self.stats["redis_misses"]
        )
        
        redis_hit_rate = (
            self.stats["redis_hits"] / redis_requests 
            if redis_requests > 0 else 0
        )
        
        return {
            "memory_cache_size": len(self.memory_cache),
            "memory_hit_rate": memory_hit_rate,
            "redis_hit_rate": redis_hit_rate,
            "total_api_calls_saved": self.stats["memory_hits"] + self.stats["redis_hits"],
            "stats": self.stats
        }
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache(redis_url: Optional[str] = None) -> EmbeddingCache:
    """Get global embedding cache instance."""
    global _embedding_cache
    
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache(redis_url=redis_url)
    
    return _embedding_cache