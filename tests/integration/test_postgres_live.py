"""
Live PostgreSQL integration tests for v4.2.0
Tests against the running PostgreSQL instance with pgvector
"""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import List, Dict, Any
import numpy as np
from datetime import datetime

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.services.memory_service_postgres import MemoryServicePostgres


class TestPostgreSQLLive:
    """Test PostgreSQL with pgvector against live database"""
    
    @pytest_asyncio.fixture
    async def backend(self):
        """Create backend connected to live database"""
        # Use the Docker database
        backend = PostgresUnifiedBackend("postgresql://secondbrain:changeme@localhost/secondbrain")
        await backend.initialize()
        
        # Clean test data
        async with backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'pytest'")
        
        yield backend
        
        # Cleanup
        async with backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'pytest'")
        
        await backend.close()
    
    @pytest_asyncio.fixture
    async def service(self):
        """Create memory service with embeddings enabled"""
        service = MemoryServicePostgres(
            connection_string="postgresql://secondbrain:changeme@localhost/secondbrain",
            enable_embeddings=True
        )
        await service.initialize()
        yield service
    
    @pytest.mark.asyncio
    async def test_database_connection(self, backend):
        """Test basic database connectivity"""
        async with backend.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
            # Check pgvector extension
            vector_check = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            assert vector_check == 1
    
    @pytest.mark.asyncio
    async def test_create_memory_with_embedding(self, backend):
        """Test creating memory with vector embedding"""
        # Create sample embedding (1536 dimensions for OpenAI)
        embedding = np.random.rand(1536).tolist()
        
        memory_data = {
            "content": "PostgreSQL with pgvector test",
            "memory_type": "test",
            "importance_score": 0.8,
            "tags": ["test", "pgvector"],
            "metadata": {"test": True},
            "container_id": "pytest"
        }
        
        created = await backend.create_memory(memory_data, embedding)
        
        assert created["id"] is not None
        assert created["content"] == memory_data["content"]
        assert created["has_embedding"] is True
        assert created["embedding_model"] == "text-embedding-ada-002"
    
    @pytest.mark.asyncio
    async def test_vector_search(self, backend):
        """Test vector similarity search"""
        # Create test memories with embeddings
        embeddings = [
            np.random.rand(1536).tolist(),
            np.random.rand(1536).tolist(),
            np.random.rand(1536).tolist()
        ]
        
        memories = []
        for i, embedding in enumerate(embeddings):
            memory = await backend.create_memory({
                "content": f"Test memory {i} for vector search",
                "container_id": "pytest",
                "importance_score": 0.5 + i * 0.1
            }, embedding)
            memories.append(memory)
        
        # Search with first embedding (should find itself)
        results = await backend.vector_search(
            embedding=embeddings[0],
            limit=3,
            min_similarity=0.0,
            container_id="pytest"
        )
        
        assert len(results) == 3
        assert results[0]["id"] == memories[0]["id"]  # Most similar to itself
        assert results[0]["similarity"] > 0.99  # Should be very close to 1.0
    
    @pytest.mark.asyncio
    async def test_hybrid_search_function(self, backend):
        """Test hybrid search SQL function"""
        # Create memories with embeddings
        embedding1 = np.random.rand(1536).tolist()
        embedding2 = np.random.rand(1536).tolist()
        
        await backend.create_memory({
            "content": "PostgreSQL database with vector extensions",
            "container_id": "pytest"
        }, embedding1)
        
        await backend.create_memory({
            "content": "Machine learning embeddings for semantic search",
            "container_id": "pytest"
        }, embedding2)
        
        # Test hybrid search
        results = await backend.hybrid_search(
            query="vector embeddings",
            embedding=embedding1,
            limit=2,
            vector_weight=0.5,
            container_id="pytest"
        )
        
        assert len(results) > 0
        assert "content" in results[0]
    
    @pytest.mark.asyncio
    async def test_service_with_openai_embeddings(self, service):
        """Test memory service with real OpenAI embeddings"""
        # Skip if no OpenAI key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        # Create memory with automatic embedding
        created = await service.create_memory(
            content="Testing automatic embedding generation with OpenAI",
            memory_type="test",
            importance_score=0.9,
            tags=["openai", "embedding", "test"],
            generate_embedding=True
        )
        
        assert created["id"] is not None
        
        # Search for it
        results = await service.semantic_search(
            query="OpenAI embeddings",
            limit=5,
            min_similarity=0.5
        )
        
        # Should find our memory
        found = any(r["id"] == created["id"] for r in results)
        assert found, "Created memory should be found in semantic search"
    
    @pytest.mark.asyncio
    async def test_hnsw_index_performance(self, backend):
        """Test HNSW index exists and is used"""
        async with backend.acquire() as conn:
            # Check index exists
            index_exists = await conn.fetchval("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_memories_embedding'
            """)
            assert index_exists == 1
            
            # Check index definition includes HNSW
            index_def = await conn.fetchval("""
                SELECT indexdef FROM pg_indexes 
                WHERE indexname = 'idx_memories_embedding'
            """)
            assert 'hnsw' in index_def.lower()
            assert 'vector_cosine_ops' in index_def
    
    @pytest.mark.asyncio
    async def test_full_text_search(self, backend):
        """Test PostgreSQL full-text search"""
        # Create test memories
        await backend.create_memory({
            "content": "Python programming language tutorial",
            "container_id": "pytest"
        })
        
        await backend.create_memory({
            "content": "JavaScript web development guide",
            "container_id": "pytest"
        })
        
        # Search for Python
        results = await backend.text_search(
            query="Python programming",
            limit=10,
            container_id="pytest"
        )
        
        assert len(results) > 0
        assert "python" in results[0]["content"].lower()
        assert results[0]["text_rank"] > 0
    
    @pytest.mark.asyncio
    async def test_statistics(self, backend):
        """Test database statistics"""
        # Create some test data
        for i in range(3):
            await backend.create_memory({
                "content": f"Test memory {i}",
                "container_id": "pytest",
                "memory_type": "test" if i < 2 else "other"
            })
        
        stats = await backend.get_statistics("pytest")
        
        assert stats["total_memories"] == 3
        assert stats["memories_by_type"]["test"] == 2
        assert stats["memories_by_type"]["other"] == 1
        assert stats["backend"] == "postgresql_unified"
        assert stats["has_vector_support"] is True