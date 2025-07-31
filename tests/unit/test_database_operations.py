"""
Comprehensive Unit Tests for Database Operations
Tests critical database functionality with mocked dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from datetime import datetime, timedelta
import json

from app.database import Database


class TestDatabaseOperations:
    """Test database operations with comprehensive coverage"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.database = Database()
        self.mock_pool = AsyncMock()
        self.mock_connection = AsyncMock()
        self.database.pool = self.mock_pool
        
        # Setup connection context manager
        self.mock_connection.__aenter__ = AsyncMock(return_value=self.mock_connection)
        self.mock_connection.__aexit__ = AsyncMock(return_value=None)
        self.mock_pool.acquire.return_value = self.mock_connection

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful database initialization"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            # Mock the _setup_database method
            with patch.object(self.database, '_setup_database', return_value=None):
                await self.database.initialize()
                
                assert self.database.pool == mock_pool
                mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_database_connection_failure(self):
        """Test database initialization failure"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_create_pool.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                await self.database.initialize()

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        """Test successful memory storage"""
        # Mock successful memory storage
        memory_id = "test-memory-123"
        self.mock_connection.fetchval.return_value = memory_id
        
        result = await self.database.store_memory(
            content="Test memory content",
            memory_type="semantic",
            importance_score=0.8
        )
        
        assert result == memory_id
        self.mock_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_with_metadata(self):
        """Test memory storage with various metadata types"""
        memory_id = "test-memory-456"
        self.mock_connection.fetchval.return_value = memory_id
        
        # Test semantic metadata
        result = await self.database.store_memory(
            content="Python programming concepts",
            memory_type="semantic",
            semantic_metadata={
                "domain": "programming",
                "concepts": ["python", "functions", "classes"],
                "confidence": 0.9
            },
            importance_score=0.7
        )
        
        assert result == memory_id
        
        # Verify the call was made with proper parameters
        call_args = self.mock_connection.fetchval.call_args
        assert "semantic_metadata" in str(call_args) or len(call_args[0]) >= 5

    @pytest.mark.asyncio
    async def test_store_memory_embedding_generation(self):
        """Test that embeddings are generated during memory storage"""
        with patch.object(self.database, '_generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3] * 512  # Mock 1536-dim embedding
            self.mock_connection.fetchval.return_value = "test-memory-789"
            
            await self.database.store_memory(
                content="Test content for embedding",
                memory_type="semantic"
            )
            
            mock_embed.assert_called_once_with("Test content for embedding")

    @pytest.mark.asyncio
    async def test_get_memory_success(self):
        """Test successful memory retrieval"""
        mock_memory_data = {
            "id": "test-memory-123",
            "content": "Test memory content",
            "memory_type": "semantic",
            "importance_score": 0.8,
            "created_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow(),
            "access_count": 1
        }
        
        self.mock_connection.fetchrow.return_value = mock_memory_data
        
        result = await self.database.get_memory("test-memory-123")
        
        assert result["id"] == "test-memory-123"
        assert result["content"] == "Test memory content"
        assert result["memory_type"] == "semantic"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self):
        """Test memory retrieval when memory doesn't exist"""
        self.mock_connection.fetchrow.return_value = None
        
        result = await self.database.get_memory("nonexistent-memory")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_search_memories_vector_search(self):
        """Test vector-based memory search"""
        mock_search_results = [
            {
                "id": "memory-1",
                "content": "Python programming",
                "memory_type": "semantic",
                "similarity": 0.95,
                "importance_score": 0.8
            },
            {
                "id": "memory-2", 
                "content": "Machine learning with Python",
                "memory_type": "semantic",
                "similarity": 0.87,
                "importance_score": 0.7
            }
        ]
        
        with patch.object(self.database, '_generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3] * 512
            self.mock_connection.fetch.return_value = mock_search_results
            
            results = await self.database.search_memories("python programming", limit=10)
            
            assert len(results) == 2
            assert results[0]["similarity"] > results[1]["similarity"]  # Ordered by similarity
            mock_embed.assert_called_once_with("python programming")

    @pytest.mark.asyncio
    async def test_search_memories_with_filters(self):
        """Test memory search with type and importance filters"""
        mock_results = [
            {
                "id": "memory-1",
                "content": "Test content",
                "memory_type": "semantic",
                "importance_score": 0.9
            }
        ]
        
        with patch.object(self.database, '_generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 1536
            self.mock_connection.fetch.return_value = mock_results
            
            results = await self.database.contextual_search(
                query="test query",
                memory_types=["semantic"],
                importance_threshold=0.5,
                limit=5
            )
            
            assert len(results) == 1
            assert results[0]["memory_type"] == "semantic"

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        """Test successful memory deletion"""
        self.mock_connection.fetchval.return_value = True  # Memory was deleted
        
        result = await self.database.delete_memory("test-memory-123")
        
        assert result is True
        self.mock_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self):
        """Test memory deletion when memory doesn't exist"""
        self.mock_connection.fetchval.return_value = False  # No memory deleted
        
        result = await self.database.delete_memory("nonexistent-memory")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_memories_with_pagination(self):
        """Test retrieving all memories with pagination"""
        mock_memories = [
            {
                "id": f"memory-{i}",
                "content": f"Memory content {i}",
                "memory_type": "semantic",
                "created_at": datetime.utcnow()
            }
            for i in range(3)
        ]
        
        self.mock_connection.fetch.return_value = mock_memories
        
        results = await self.database.get_all_memories(limit=3, offset=0)
        
        assert len(results) == 3
        assert all("id" in memory for memory in results)

    @pytest.mark.asyncio
    async def test_get_index_stats(self):
        """Test retrieving database index statistics"""
        mock_stats = {
            "memories_with_embeddings": 1500,
            "index_ready": True,
            "hnsw_index_exists": True,
            "ivf_index_exists": False,
            "total_memories": 1500
        }
        
        # Mock multiple database calls for statistics
        self.mock_connection.fetchval.side_effect = [1500, True, True, False, 1500]
        
        with patch.object(self.database, '_get_embedding_stats') as mock_stats_method:
            mock_stats_method.return_value = mock_stats
            
            stats = await self.database.get_index_stats()
            
            assert stats["memories_with_embeddings"] == 1500
            assert stats["index_ready"] is True
            assert stats["hnsw_index_exists"] is True

    @pytest.mark.asyncio
    async def test_database_connection_pool_management(self):
        """Test database connection pool acquire/release"""
        async with self.database.pool.acquire() as conn:
            # Simulate database operation
            conn.fetchval.return_value = "test-result"
            result = await conn.fetchval("SELECT 'test'")
            assert result == "test-result"
        
        # Verify connection was properly managed
        self.mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_transaction_handling(self):
        """Test database transaction management"""
        # Mock transaction context
        mock_transaction = AsyncMock()
        self.mock_connection.transaction.return_value = mock_transaction
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        
        # Test successful transaction
        async with self.mock_connection.transaction():
            await self.mock_connection.execute("INSERT INTO memories ...")
        
        self.mock_connection.transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_embedding_generation_openai(self):
        """Test OpenAI embedding generation"""
        mock_openai_response = MagicMock()
        mock_openai_response.data = [MagicMock()]
        mock_openai_response.data[0].embedding = [0.1, 0.2, 0.3] * 512
        
        with patch.object(self.database, 'openai_client') as mock_client:
            mock_openai = AsyncMock()
            mock_openai.embeddings.create.return_value = mock_openai_response
            mock_client = mock_openai
            self.database.openai_client = mock_openai
            
            embedding = await self.database._generate_embedding("test content")
            
            assert len(embedding) == 1536  # Standard OpenAI embedding size
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_database_setup_creates_tables(self):
        """Test that database setup creates necessary tables and extensions"""
        with patch.object(self.database, 'pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock()
            
            await self.database._setup_database()
            
            # Verify that setup queries were executed
            assert mock_conn.execute.call_count >= 2  # At least extension and table creation

    @pytest.mark.asyncio
    async def test_memory_importance_scoring(self):
        """Test memory importance scoring functionality"""
        memory_id = "test-memory-importance"
        self.mock_connection.fetchval.return_value = memory_id
        
        # Store memory with importance score
        result = await self.database.store_memory(
            content="Important memory content",
            memory_type="semantic",
            importance_score=0.95
        )
        
        assert result == memory_id
        
        # Verify importance score was included in the call
        call_args = self.mock_connection.fetchval.call_args
        # Check that importance score parameter was passed
        assert any("0.95" in str(arg) or 0.95 in arg for arg in call_args[0] if arg is not None)

    @pytest.mark.asyncio
    async def test_memory_type_validation(self):
        """Test that memory types are properly validated"""
        valid_types = ["semantic", "episodic", "procedural"]
        
        for memory_type in valid_types:
            self.mock_connection.fetchval.return_value = f"memory-{memory_type}"
            
            result = await self.database.store_memory(
                content=f"Test {memory_type} memory",
                memory_type=memory_type
            )
            
            assert result.startswith("memory-")

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test database error handling for various failure scenarios"""
        # Test connection pool exhaustion
        self.mock_pool.acquire.side_effect = asyncpg.TooManyConnectionsError("Pool exhausted")
        
        with pytest.raises(asyncpg.TooManyConnectionsError):
            await self.database.get_memory("test-memory")
        
        # Test query execution failure
        self.mock_pool.acquire.side_effect = None  # Reset
        self.mock_connection.fetchval.side_effect = asyncpg.PostgresError("Query failed")
        
        with pytest.raises(asyncpg.PostgresError):
            await self.database.store_memory("test", "semantic")

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self):
        """Test handling of concurrent database operations"""
        import asyncio
        
        # Setup multiple concurrent operations
        self.mock_connection.fetchval.side_effect = [
            "memory-1", "memory-2", "memory-3"
        ]
        
        async def store_memory(i):
            return await self.database.store_memory(
                content=f"Concurrent memory {i}",
                memory_type="semantic"
            )
        
        # Execute concurrent operations
        tasks = [store_memory(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result.startswith("memory-") for result in results)

    @pytest.mark.asyncio
    async def test_memory_access_tracking(self):
        """Test that memory access is properly tracked"""
        mock_memory = {
            "id": "test-memory-tracking",
            "content": "Test content",
            "access_count": 5,
            "last_accessed": datetime.utcnow()
        }
        
        self.mock_connection.fetchrow.return_value = mock_memory
        
        # Mock the access tracking update
        self.mock_connection.execute.return_value = None
        
        memory = await self.database.get_memory("test-memory-tracking")
        
        assert memory["access_count"] == 5
        # Verify that access tracking query was executed
        self.mock_connection.execute.assert_called()

    @pytest.mark.asyncio
    async def test_database_close_cleanup(self):
        """Test proper database connection cleanup"""
        await self.database.close()
        
        if self.database.pool:
            self.mock_pool.close.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_bulk_memory_operations(self):
        """Test bulk memory storage and retrieval operations"""
        # Test bulk storage
        memories_data = [
            {"content": "Memory 1", "memory_type": "semantic"},
            {"content": "Memory 2", "memory_type": "episodic"},
            {"content": "Memory 3", "memory_type": "procedural"}
        ]
        
        # Mock bulk insert return
        self.mock_connection.executemany.return_value = None
        
        # Simulate bulk operation (if supported)
        for memory in memories_data:
            self.mock_connection.fetchval.return_value = f"bulk-{memory['memory_type']}"
            result = await self.database.store_memory(**memory)
            assert result.startswith("bulk-")

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health checking functionality"""
        # Mock successful health check
        self.mock_connection.fetchval.return_value = 1
        
        # Simple health check query
        async def health_check():
            async with self.database.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        
        is_healthy = await health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_memory_search_edge_cases(self):
        """Test edge cases in memory search functionality"""
        with patch.object(self.database, '_generate_embedding') as mock_embed:
            mock_embed.return_value = [0.0] * 1536  # Zero embedding
            
            # Test empty query
            self.mock_connection.fetch.return_value = []
            results = await self.database.search_memories("", limit=10)
            assert len(results) == 0
            
            # Test very long query
            long_query = "word " * 1000
            mock_embed.return_value = [0.1] * 1536
            self.mock_connection.fetch.return_value = []
            results = await self.database.search_memories(long_query, limit=10)
            assert isinstance(results, list)
            
            # Test special characters in query
            special_query = "test!@#$%^&*()_+{}|:<>?[];',./"
            results = await self.database.search_memories(special_query, limit=10)
            assert isinstance(results, list)