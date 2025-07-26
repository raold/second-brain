"""
Test the MemoryService implementation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.memory_service import MemoryService


class TestMemoryService:
    """Test MemoryService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.memory_service = MemoryService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self):
        """Test successful memory creation"""
        self.mock_db.store_memory.return_value = "memory-123"
        
        memory_id = await self.memory_service.create_memory(
            content="Test memory content",
            metadata={"type": "note", "importance": 0.8}
        )
        
        assert memory_id == "memory-123"
        self.mock_db.store_memory.assert_called_once_with(
            "Test memory content",
            {"type": "note", "importance": 0.8}
        )
    
    @pytest.mark.asyncio
    async def test_create_memory_with_empty_content(self):
        """Test memory creation with empty content"""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            await self.memory_service.create_memory("", {})
    
    @pytest.mark.asyncio
    async def test_create_memory_with_none_content(self):
        """Test memory creation with None content"""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            await self.memory_service.create_memory(None, {})
    
    @pytest.mark.asyncio
    async def test_get_memory_success(self):
        """Test successful memory retrieval"""
        mock_memory = {
            "id": "memory-123",
            "content": "Test memory content",
            "metadata": {"type": "note"},
            "created_at": "2024-01-01T12:00:00Z"
        }
        self.mock_db.get_memory.return_value = mock_memory
        
        memory = await self.memory_service.get_memory("memory-123")
        
        assert memory == mock_memory
        self.mock_db.get_memory.assert_called_once_with("memory-123")
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self):
        """Test memory retrieval when memory doesn't exist"""
        self.mock_db.get_memory.return_value = None
        
        memory = await self.memory_service.get_memory("nonexistent")
        
        assert memory is None
    
    @pytest.mark.asyncio
    async def test_get_memories_success(self):
        """Test successful retrieval of multiple memories"""
        mock_memories = [
            {"id": "memory-1", "content": "First memory"},
            {"id": "memory-2", "content": "Second memory"}
        ]
        self.mock_db.get_all_memories.return_value = mock_memories
        
        memories = await self.memory_service.get_memories(limit=10, offset=0)
        
        assert memories == mock_memories
        self.mock_db.get_all_memories.assert_called_once_with(limit=10, offset=0)
    
    @pytest.mark.asyncio
    async def test_get_memories_with_default_params(self):
        """Test get_memories with default parameters"""
        self.mock_db.get_all_memories.return_value = []
        
        memories = await self.memory_service.get_memories()
        
        self.mock_db.get_all_memories.assert_called_once_with(limit=100, offset=0)
    
    @pytest.mark.asyncio
    async def test_search_memories_success(self):
        """Test successful memory search"""
        mock_results = [
            {"id": "memory-1", "content": "Python programming", "score": 0.95},
            {"id": "memory-2", "content": "Code examples", "score": 0.87}
        ]
        self.mock_db.search_memories.return_value = mock_results
        
        results = await self.memory_service.search_memories("Python", limit=5)
        
        assert results == mock_results
        self.mock_db.search_memories.assert_called_once_with("Python", limit=5)
    
    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self):
        """Test search with empty query"""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await self.memory_service.search_memories("")
    
    @pytest.mark.asyncio
    async def test_search_memories_none_query(self):
        """Test search with None query"""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            await self.memory_service.search_memories(None)
    
    @pytest.mark.asyncio
    async def test_update_memory_success(self):
        """Test successful memory update"""
        self.mock_db.update_memory.return_value = True
        
        result = await self.memory_service.update_memory(
            "memory-123",
            content="Updated content",
            metadata={"updated": True}
        )
        
        assert result is True
        self.mock_db.update_memory.assert_called_once_with(
            "memory-123",
            content="Updated content",
            metadata={"updated": True}
        )
    
    @pytest.mark.asyncio
    async def test_update_memory_not_found(self):
        """Test update when memory doesn't exist"""
        self.mock_db.update_memory.return_value = False
        
        result = await self.memory_service.update_memory(
            "nonexistent",
            content="New content"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        """Test successful memory deletion"""
        self.mock_db.delete_memory.return_value = True
        
        result = await self.memory_service.delete_memory("memory-123")
        
        assert result is True
        self.mock_db.delete_memory.assert_called_once_with("memory-123")
    
    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self):
        """Test deletion when memory doesn't exist"""
        self.mock_db.delete_memory.return_value = False
        
        result = await self.memory_service.delete_memory("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_memory_stats(self):
        """Test memory statistics retrieval"""
        self.mock_db.get_memory_count.return_value = 150
        self.mock_db.get_database_size.return_value = 1024 * 1024  # 1MB
        
        stats = await self.memory_service.get_memory_stats()
        
        assert stats["total_memories"] == 150
        assert stats["database_size_bytes"] == 1024 * 1024
        assert "last_updated" in stats
    
    @pytest.mark.asyncio
    async def test_bulk_create_memories(self):
        """Test bulk memory creation"""
        memories_data = [
            {"content": "First memory", "metadata": {"type": "note"}},
            {"content": "Second memory", "metadata": {"type": "idea"}},
            {"content": "Third memory", "metadata": {"type": "reminder"}}
        ]
        
        # Mock store_memory to return different IDs
        self.mock_db.store_memory.side_effect = ["mem-1", "mem-2", "mem-3"]
        
        results = await self.memory_service.bulk_create_memories(memories_data)
        
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[0]["memory_id"] == "mem-1"
        assert results[1]["memory_id"] == "mem-2"
        assert results[2]["memory_id"] == "mem-3"
    
    @pytest.mark.asyncio
    async def test_bulk_create_memories_with_failures(self):
        """Test bulk creation with some failures"""
        memories_data = [
            {"content": "Valid memory", "metadata": {}},
            {"content": "", "metadata": {}},  # Invalid - empty content
            {"content": "Another valid memory", "metadata": {}}
        ]
        
        self.mock_db.store_memory.side_effect = ["mem-1", None, "mem-3"]
        
        results = await self.memory_service.bulk_create_memories(memories_data)
        
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "empty" in results[1]["error"].lower()
        assert results[2]["success"] is True


class TestMemoryServiceErrorHandling:
    """Test error handling in MemoryService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.memory_service = MemoryService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_create_memory_database_error(self):
        """Test memory creation when database fails"""
        self.mock_db.store_memory.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await self.memory_service.create_memory("Test content", {})
    
    @pytest.mark.asyncio
    async def test_search_memories_database_error(self):
        """Test search when database fails"""
        self.mock_db.search_memories.side_effect = Exception("Search index error")
        
        with pytest.raises(Exception, match="Search index error"):
            await self.memory_service.search_memories("test query")
    
    @pytest.mark.asyncio
    async def test_get_memory_stats_database_error(self):
        """Test stats retrieval when database fails"""
        self.mock_db.get_memory_count.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            await self.memory_service.get_memory_stats()


class TestMemoryServiceIntegration:
    """Integration tests for MemoryService"""
    
    @pytest.mark.asyncio
    async def test_memory_lifecycle(self):
        """Test complete memory lifecycle: create, read, update, delete"""
        mock_db = AsyncMock()
        memory_service = MemoryService(mock_db)
        
        # Create
        mock_db.store_memory.return_value = "memory-123"
        memory_id = await memory_service.create_memory(
            "Test memory",
            {"type": "note"}
        )
        assert memory_id == "memory-123"
        
        # Read
        mock_memory = {
            "id": "memory-123",
            "content": "Test memory",
            "metadata": {"type": "note"}
        }
        mock_db.get_memory.return_value = mock_memory
        retrieved = await memory_service.get_memory("memory-123")
        assert retrieved == mock_memory
        
        # Update
        mock_db.update_memory.return_value = True
        updated = await memory_service.update_memory(
            "memory-123",
            content="Updated memory"
        )
        assert updated is True
        
        # Delete
        mock_db.delete_memory.return_value = True
        deleted = await memory_service.delete_memory("memory-123")
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_memory_service_with_real_data_types(self):
        """Test memory service with realistic data types"""
        mock_db = AsyncMock()
        memory_service = MemoryService(mock_db)
        
        # Test with complex metadata
        complex_metadata = {
            "type": "code_snippet",
            "language": "python",
            "tags": ["async", "testing", "pytest"],
            "importance": 0.85,
            "created_by": "user@example.com",
            "last_accessed": datetime.now().isoformat()
        }
        
        mock_db.store_memory.return_value = "complex-memory-456"
        
        memory_id = await memory_service.create_memory(
            "async def test_function():\n    assert True",
            complex_metadata
        )
        
        assert memory_id == "complex-memory-456"
        mock_db.store_memory.assert_called_once_with(
            "async def test_function():\n    assert True",
            complex_metadata
        )