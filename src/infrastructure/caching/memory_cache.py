"""
Memory-specific caching layer.

Provides caching for memory operations.
"""

from typing import Optional
from uuid import UUID

from src.domain.models.memory import Memory, MemoryId, MemoryStatus, MemoryType
from src.domain.repositories.memory_repository import MemoryRepository
from src.infrastructure.caching import Cache, CacheKey, cache_aside, cache_invalidate
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CachedMemoryRepository(MemoryRepository):
    """Memory repository with caching layer."""
    
    def __init__(
        self,
        repository: MemoryRepository,
        cache: Cache,
        ttl: int = 3600,
    ):
        """
        Initialize cached repository.
        
        Args:
            repository: Underlying repository
            cache: Cache instance
            ttl: Default TTL in seconds
        """
        self.repository = repository
        self.cache = cache
        self.ttl = ttl
        self.key_builder = CacheKey("memory")
    
    async def get(self, memory_id: MemoryId) -> Optional[Memory]:
        """Get a memory by ID with caching."""
        # Build cache key
        cache_key = self.key_builder.build("get", str(memory_id))
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return Memory(**cached)
        
        # Get from repository
        memory = await self.repository.get(memory_id)
        
        # Cache if found
        if memory:
            await self.cache.set(
                cache_key,
                memory.to_dict(),
                ttl=self.ttl,
            )
        
        return memory
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[MemoryStatus] = None,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """Get memories for a user with caching."""
        # Build cache key
        cache_key = self.key_builder.build(
            "list",
            str(user_id),
            skip,
            limit,
            status.value if status else "all",
            memory_type.value if memory_type else "all",
        )
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [Memory(**m) for m in cached]
        
        # Get from repository
        memories = await self.repository.get_by_user(
            user_id, skip, limit, status, memory_type
        )
        
        # Cache results
        await self.cache.set(
            cache_key,
            [m.to_dict() for m in memories],
            ttl=self.ttl // 2,  # Shorter TTL for lists
        )
        
        return memories
    
    async def save(self, memory: Memory) -> Memory:
        """Save a memory and invalidate cache."""
        # Save to repository
        saved = await self.repository.save(memory)
        
        # Invalidate specific memory cache
        memory_key = self.key_builder.build("get", str(memory.id))
        await self.cache.delete(memory_key)
        
        # Invalidate user list caches
        user_pattern = self.key_builder.pattern("list", str(memory.user_id), "*")
        await self.cache.delete_pattern(user_pattern)
        
        # Invalidate search caches for this user
        search_pattern = self.key_builder.pattern("search", str(memory.user_id), "*")
        await self.cache.delete_pattern(search_pattern)
        
        # Cache the saved memory
        await self.cache.set(
            memory_key,
            saved.to_dict(),
            ttl=self.ttl,
        )
        
        return saved
    
    async def delete(self, memory_id: MemoryId) -> bool:
        """Delete a memory and clear cache."""
        # Get memory first to get user_id
        memory = await self.get(memory_id)
        
        # Delete from repository
        deleted = await self.repository.delete(memory_id)
        
        if deleted and memory:
            # Clear specific memory cache
            memory_key = self.key_builder.build("get", str(memory_id))
            await self.cache.delete(memory_key)
            
            # Clear user list caches
            user_pattern = self.key_builder.pattern("list", str(memory.user_id), "*")
            await self.cache.delete_pattern(user_pattern)
            
            # Clear search caches
            search_pattern = self.key_builder.pattern("search", str(memory.user_id), "*")
            await self.cache.delete_pattern(search_pattern)
        
        return deleted
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """Search memories with caching."""
        # Build cache key
        cache_key = self.key_builder.build(
            "search",
            str(user_id),
            query,
            limit,
            memory_type.value if memory_type else "all",
        )
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [Memory(**m) for m in cached]
        
        # Search in repository
        results = await self.repository.search(user_id, query, limit, memory_type)
        
        # Cache results
        await self.cache.set(
            cache_key,
            [m.to_dict() for m in results],
            ttl=self.ttl // 4,  # Shorter TTL for search results
        )
        
        return results
    
    async def get_by_tags(
        self,
        user_id: UUID,
        tags: list[str],
        match_all: bool = False,
        limit: int = 100,
    ) -> list[Memory]:
        """Get memories by tags with caching."""
        # Build cache key
        cache_key = self.key_builder.build(
            "tags",
            str(user_id),
            ":".join(sorted(tags)),
            "all" if match_all else "any",
            limit,
        )
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [Memory(**m) for m in cached]
        
        # Get from repository
        memories = await self.repository.get_by_tags(
            user_id, tags, match_all, limit
        )
        
        # Cache results
        await self.cache.set(
            cache_key,
            [m.to_dict() for m in memories],
            ttl=self.ttl // 2,
        )
        
        return memories
    
    async def get_linked(self, memory_id: MemoryId) -> list[Memory]:
        """Get linked memories with caching."""
        # Build cache key
        cache_key = self.key_builder.build("linked", str(memory_id))
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [Memory(**m) for m in cached]
        
        # Get from repository
        memories = await self.repository.get_linked(memory_id)
        
        # Cache results
        await self.cache.set(
            cache_key,
            [m.to_dict() for m in memories],
            ttl=self.ttl,
        )
        
        return memories
    
    async def count_by_user(
        self,
        user_id: UUID,
        status: Optional[MemoryStatus] = None,
    ) -> int:
        """Count memories with caching."""
        # Build cache key
        cache_key = self.key_builder.build(
            "count",
            str(user_id),
            status.value if status else "all",
        )
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Get from repository
        count = await self.repository.count_by_user(user_id, status)
        
        # Cache result
        await self.cache.set(
            cache_key,
            count,
            ttl=self.ttl // 2,
        )
        
        return count
    
    async def get_similar(
        self,
        memory_id: MemoryId,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[tuple[Memory, float]]:
        """Get similar memories (not cached due to dynamic nature)."""
        # Similar search is compute-intensive and dynamic
        # so we don't cache it
        return await self.repository.get_similar(memory_id, limit, threshold)
    
    async def update_embedding(
        self,
        memory_id: MemoryId,
        embedding: list[float],
        model: str,
    ) -> bool:
        """Update embedding and invalidate cache."""
        # Update in repository
        updated = await self.repository.update_embedding(memory_id, embedding, model)
        
        if updated:
            # Invalidate memory cache
            memory_key = self.key_builder.build("get", str(memory_id))
            await self.cache.delete(memory_key)
            
            # Invalidate similar memories cache (if we add it later)
            similar_pattern = self.key_builder.pattern("similar", "*")
            await self.cache.delete_pattern(similar_pattern)
        
        return updated