"""
Integration tests for caching layer.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.infrastructure.caching import Cache, CacheStrategy, cache_decorator
from src.infrastructure.caching.memory_cache import CachedMemoryRepository

from ..fixtures.factories import MemoryFactory
from ..fixtures.mocks import MockMemoryRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestCache:
    """Integration tests for Cache."""
    
    async def test_basic_get_set(self, cache):
        """Test basic get and set operations."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        
        # Act
        set_result = await cache.set(key, value)
        get_result = await cache.get(key)
        
        # Assert
        assert set_result is True
        assert get_result == value
    
    async def test_set_with_ttl(self, cache):
        """Test setting value with TTL."""
        # Arrange
        key = "ttl_key"
        value = "temporary_value"
        ttl = 1  # 1 second
        
        # Act
        await cache.set(key, value, ttl=ttl)
        immediate_result = await cache.get(key)
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        expired_result = await cache.get(key)
        
        # Assert
        assert immediate_result == value
        assert expired_result is None
    
    async def test_delete(self, cache):
        """Test deleting keys."""
        # Arrange
        key = "delete_key"
        value = "to_be_deleted"
        await cache.set(key, value)
        
        # Act
        delete_result = await cache.delete(key)
        get_result = await cache.get(key)
        
        # Assert
        assert delete_result is True
        assert get_result is None
    
    async def test_delete_nonexistent(self, cache):
        """Test deleting non-existent key."""
        # Act
        result = await cache.delete("nonexistent_key")
        
        # Assert
        assert result is False
    
    async def test_mget_mset(self, cache):
        """Test batch get and set operations."""
        # Arrange
        data = {
            "key1": "value1",
            "key2": {"nested": "value2"},
            "key3": [1, 2, 3],
        }
        
        # Act
        mset_result = await cache.mset(data)
        mget_result = await cache.mget(list(data.keys()))
        
        # Assert
        assert mset_result is True
        assert mget_result == data
    
    async def test_mget_partial(self, cache):
        """Test mget with some missing keys."""
        # Arrange
        await cache.set("exists1", "value1")
        await cache.set("exists2", "value2")
        
        # Act
        result = await cache.mget(["exists1", "missing", "exists2"])
        
        # Assert
        assert result == {
            "exists1": "value1",
            "exists2": "value2",
            "missing": None,
        }
    
    async def test_keys_pattern(self, cache):
        """Test getting keys by pattern."""
        # Arrange
        await cache.set("user:1:profile", {"name": "User 1"})
        await cache.set("user:2:profile", {"name": "User 2"})
        await cache.set("user:1:settings", {"theme": "dark"})
        await cache.set("post:1:content", {"title": "Post 1"})
        
        # Act
        all_user_keys = await cache.keys("user:*")
        user1_keys = await cache.keys("user:1:*")
        profile_keys = await cache.keys("*:profile")
        
        # Assert
        assert len(all_user_keys) == 3
        assert len(user1_keys) == 2
        assert len(profile_keys) == 2
    
    async def test_delete_pattern(self, cache):
        """Test deleting keys by pattern."""
        # Arrange
        keys = {
            "session:1": "data1",
            "session:2": "data2",
            "session:3": "data3",
            "permanent:1": "keep_this",
        }
        
        for key, value in keys.items():
            await cache.set(key, value)
        
        # Act
        deleted_count = await cache.delete_pattern("session:*")
        
        # Verify
        session_keys = await cache.keys("session:*")
        permanent_value = await cache.get("permanent:1")
        
        # Assert
        assert deleted_count == 3
        assert len(session_keys) == 0
        assert permanent_value == "keep_this"
    
    async def test_serialization(self, cache):
        """Test automatic serialization/deserialization."""
        # Arrange
        test_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "datetime": datetime.utcnow().isoformat(),
        }
        
        # Act
        await cache.set("complex_data", test_data)
        result = await cache.get("complex_data")
        
        # Assert
        assert result == test_data
    
    async def test_large_value(self, cache):
        """Test handling large values."""
        # Arrange
        large_list = list(range(10000))
        large_dict = {str(i): f"value_{i}" for i in range(1000)}
        
        # Act
        await cache.set("large_list", large_list)
        await cache.set("large_dict", large_dict)
        
        retrieved_list = await cache.get("large_list")
        retrieved_dict = await cache.get("large_dict")
        
        # Assert
        assert retrieved_list == large_list
        assert retrieved_dict == large_dict


@pytest.mark.integration
@pytest.mark.asyncio
class TestCacheDecorator:
    """Tests for cache decorator."""
    
    async def test_cache_decorator_basic(self, cache):
        """Test basic cache decorator functionality."""
        call_count = 0
        
        @cache_decorator(cache, ttl=60)
        async def expensive_function(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return x + y
        
        # First call - should execute function
        result1 = await expensive_function(5, 3)
        assert result1 == 8
        assert call_count == 1
        
        # Second call - should use cache
        result2 = await expensive_function(5, 3)
        assert result2 == 8
        assert call_count == 1  # Not incremented
        
        # Different arguments - should execute function
        result3 = await expensive_function(10, 20)
        assert result3 == 30
        assert call_count == 2
    
    async def test_cache_decorator_with_prefix(self, cache):
        """Test cache decorator with custom prefix."""
        @cache_decorator(cache, prefix="math", ttl=60)
        async def multiply(x: int, y: int) -> int:
            return x * y
        
        # Call function
        result = await multiply(4, 5)
        assert result == 20
        
        # Check cache key format
        keys = await cache.keys("math:*")
        assert len(keys) == 1
        assert keys[0].startswith("math:")
    
    async def test_cache_decorator_ttl_expiry(self, cache):
        """Test cache decorator TTL expiration."""
        call_count = 0
        
        @cache_decorator(cache, ttl=1)  # 1 second TTL
        async def timestamp_function() -> float:
            nonlocal call_count
            call_count += 1
            return datetime.utcnow().timestamp()
        
        # First call
        time1 = await timestamp_function()
        assert call_count == 1
        
        # Immediate second call - cached
        time2 = await timestamp_function()
        assert time2 == time1
        assert call_count == 1
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Third call - cache expired
        time3 = await timestamp_function()
        assert time3 > time1
        assert call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
class TestCachedMemoryRepository:
    """Tests for cached memory repository."""
    
    async def test_cached_get(self, cache):
        """Test cached get operation."""
        # Arrange
        base_repo = MockMemoryRepository()
        cached_repo = CachedMemoryRepository(base_repo, cache)
        
        memory = MemoryFactory.create()
        await base_repo.save(memory)
        
        # Act - First get (cache miss)
        result1 = await cached_repo.get(memory.id)
        
        # Verify cached
        cache_key = f"memory:{memory.id.value}"
        cached_data = await cache.get(cache_key)
        assert cached_data is not None
        
        # Act - Second get (cache hit)
        # Clear base repo to ensure cache is used
        base_repo._memories.clear()
        result2 = await cached_repo.get(memory.id)
        
        # Assert
        assert result1.id == memory.id
        assert result2.id == memory.id
    
    async def test_cached_save_invalidates_cache(self, cache):
        """Test that save invalidates cache."""
        # Arrange
        base_repo = MockMemoryRepository()
        cached_repo = CachedMemoryRepository(base_repo, cache)
        
        memory = MemoryFactory.create()
        await cached_repo.save(memory)
        
        # Prime cache
        await cached_repo.get(memory.id)
        
        # Act - Update memory
        memory.title = "Updated Title"
        await cached_repo.save(memory)
        
        # Get from cache
        result = await cached_repo.get(memory.id)
        
        # Assert - Should have updated value
        assert result.title == "Updated Title"
    
    async def test_cached_delete_invalidates_cache(self, cache):
        """Test that delete invalidates cache."""
        # Arrange
        base_repo = MockMemoryRepository()
        cached_repo = CachedMemoryRepository(base_repo, cache)
        
        memory = MemoryFactory.create()
        await cached_repo.save(memory)
        
        # Prime cache
        await cached_repo.get(memory.id)
        
        # Act - Delete memory
        await cached_repo.delete(memory.id)
        
        # Try to get
        result = await cached_repo.get(memory.id)
        
        # Assert
        assert result is None
    
    async def test_cached_search(self, cache):
        """Test cached search operation."""
        # Arrange
        base_repo = MockMemoryRepository()
        cached_repo = CachedMemoryRepository(base_repo, cache)
        
        user_id = uuid4()
        memories = MemoryFactory.create_batch(5, user_id=user_id)
        for memory in memories:
            memory.title = f"Python {memory.title}"
            await base_repo.save(memory)
        
        # Act - First search (cache miss)
        results1 = await cached_repo.search(user_id, "Python", limit=10)
        
        # Clear base repo to ensure cache is used
        base_repo._memories.clear()
        
        # Act - Second search (cache hit)
        results2 = await cached_repo.search(user_id, "Python", limit=10)
        
        # Assert
        assert len(results1) == 5
        assert len(results2) == 5
        assert [m.id for m in results1] == [m.id for m in results2]
    
    async def test_cache_warming(self, cache):
        """Test cache warming functionality."""
        # Arrange
        base_repo = MockMemoryRepository()
        cached_repo = CachedMemoryRepository(base_repo, cache)
        
        user_id = uuid4()
        memories = MemoryFactory.create_batch(10, user_id=user_id)
        for memory in memories:
            await base_repo.save(memory)
        
        # Act - Warm cache
        await cached_repo.warm_cache(user_id, limit=5)
        
        # Clear base repo
        base_repo._memories.clear()
        
        # Get memories (should come from cache)
        cached_memories = []
        for memory in memories[:5]:  # Only first 5 should be cached
            result = await cached_repo.get(memory.id)
            if result:
                cached_memories.append(result)
        
        # Assert
        assert len(cached_memories) == 5