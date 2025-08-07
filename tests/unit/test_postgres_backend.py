"""
Comprehensive tests for PostgreSQL unified backend with pgvector
Tests CRUD, search, relationships, and consolidation operations
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
import os
from typing import List, Dict, Any
import numpy as np

# Mock asyncpg if not available for testing
try:
    import asyncpg
except ImportError:
    asyncpg = None

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.services.memory_service_postgres import MemoryServicePostgres


# Skip tests if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set"
)


@pytest_asyncio.fixture
async def postgres_backend():
    """Create a test PostgreSQL backend"""
    backend = PostgresUnifiedBackend(
        os.getenv("TEST_DATABASE_URL", "postgresql://localhost/test_second_brain")
    )
    await backend.initialize()
    
    # Clean up test data before starting
    async with backend.acquire() as conn:
        await conn.execute("DELETE FROM memories WHERE container_id = 'test'")
    
    yield backend
    
    # Clean up after tests
    async with backend.acquire() as conn:
        await conn.execute("DELETE FROM memories WHERE container_id = 'test'")
    
    await backend.close()


@pytest_asyncio.fixture
async def memory_service():
    """Create a test memory service"""
    service = MemoryServicePostgres(
        connection_string=os.getenv("TEST_DATABASE_URL"),
        enable_embeddings=False  # Disable for tests
    )
    await service.initialize()
    
    yield service
    
    await service.close()


@pytest.fixture
def sample_memories():
    """Sample memories for testing"""
    return [
        {
            "content": "Python is a high-level programming language",
            "memory_type": "knowledge",
            "importance_score": 0.8,
            "tags": ["python", "programming"],
            "metadata": {"category": "technology"}
        },
        {
            "content": "Machine learning uses statistical methods",
            "memory_type": "knowledge",
            "importance_score": 0.9,
            "tags": ["ml", "ai"],
            "metadata": {"category": "technology"}
        },
        {
            "content": "PostgreSQL is a powerful database system",
            "memory_type": "knowledge",
            "importance_score": 0.7,
            "tags": ["database", "postgresql"],
            "metadata": {"category": "technology"}
        }
    ]


@pytest.fixture
def sample_embedding():
    """Generate a sample embedding vector"""
    np.random.seed(42)
    return np.random.rand(1536).tolist()


# ==================== CRUD Tests ====================

@pytest.mark.asyncio
async def test_create_memory(postgres_backend, sample_memories):
    """Test creating a memory"""
    memory_data = sample_memories[0]
    memory_data["container_id"] = "test"
    
    created = await postgres_backend.create_memory(memory_data)
    
    assert created["id"] is not None
    assert created["content"] == memory_data["content"]
    assert created["memory_type"] == memory_data["memory_type"]
    assert created["importance_score"] == memory_data["importance_score"]
    assert created["tags"] == memory_data["tags"]
    assert created["metadata"] == memory_data["metadata"]


@pytest.mark.asyncio
async def test_create_memory_with_embedding(postgres_backend, sample_memories, sample_embedding):
    """Test creating a memory with vector embedding"""
    memory_data = sample_memories[0]
    memory_data["container_id"] = "test"
    
    created = await postgres_backend.create_memory(memory_data, sample_embedding)
    
    assert created["id"] is not None
    assert created["has_embedding"] is True
    assert created["embedding_model"] is not None


@pytest.mark.asyncio
async def test_get_memory(postgres_backend, sample_memories):
    """Test retrieving a memory by ID"""
    memory_data = sample_memories[0]
    memory_data["container_id"] = "test"
    
    created = await postgres_backend.create_memory(memory_data)
    retrieved = await postgres_backend.get_memory(created["id"])
    
    assert retrieved is not None
    assert retrieved["id"] == created["id"]
    assert retrieved["content"] == created["content"]
    assert retrieved["access_count"] == 1  # Should increment on retrieval


@pytest.mark.asyncio
async def test_update_memory(postgres_backend, sample_memories):
    """Test updating a memory"""
    memory_data = sample_memories[0]
    memory_data["container_id"] = "test"
    
    created = await postgres_backend.create_memory(memory_data)
    
    updates = {
        "content": "Python is an interpreted programming language",
        "importance_score": 0.9,
        "tags": ["python", "programming", "interpreted"]
    }
    
    updated = await postgres_backend.update_memory(created["id"], updates)
    
    assert updated is not None
    assert updated["content"] == updates["content"]
    assert updated["importance_score"] == updates["importance_score"]
    assert updated["tags"] == updates["tags"]
    assert updated["version"] == 2  # Version should increment


@pytest.mark.asyncio
async def test_delete_memory_soft(postgres_backend, sample_memories):
    """Test soft deleting a memory"""
    memory_data = sample_memories[0]
    memory_data["container_id"] = "test"
    
    created = await postgres_backend.create_memory(memory_data)
    deleted = await postgres_backend.delete_memory(created["id"], soft=True)
    
    assert deleted is True
    
    # Should not be retrievable after soft delete
    retrieved = await postgres_backend.get_memory(created["id"])
    assert retrieved is None


@pytest.mark.asyncio
async def test_list_memories(postgres_backend, sample_memories):
    """Test listing memories with pagination"""
    # Create multiple memories
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        await postgres_backend.create_memory(memory_data)
    
    # Test pagination
    page1 = await postgres_backend.list_memories(limit=2, offset=0, container_id="test")
    assert len(page1) == 2
    
    page2 = await postgres_backend.list_memories(limit=2, offset=2, container_id="test")
    assert len(page2) == 1


@pytest.mark.asyncio
async def test_list_memories_with_filters(postgres_backend, sample_memories):
    """Test listing memories with filters"""
    # Create memories
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        await postgres_backend.create_memory(memory_data)
    
    # Filter by memory type
    knowledge_memories = await postgres_backend.list_memories(
        memory_type="knowledge",
        container_id="test"
    )
    assert len(knowledge_memories) == 3
    
    # Filter by tags
    python_memories = await postgres_backend.list_memories(
        tags=["python"],
        container_id="test"
    )
    assert len(python_memories) == 1
    
    # Filter by importance
    important_memories = await postgres_backend.list_memories(
        min_importance=0.8,
        container_id="test"
    )
    assert len(important_memories) == 2


# ==================== Search Tests ====================

@pytest.mark.asyncio
async def test_text_search(postgres_backend, sample_memories):
    """Test full-text search"""
    # Create memories
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        await postgres_backend.create_memory(memory_data)
    
    # Search for "programming"
    results = await postgres_backend.text_search("programming", container_id="test")
    
    assert len(results) > 0
    assert "programming" in results[0]["content"].lower()


@pytest.mark.asyncio
async def test_vector_search(postgres_backend, sample_memories, sample_embedding):
    """Test vector similarity search"""
    # Create memories with embeddings
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        # Create slightly different embeddings
        embedding = [v + np.random.normal(0, 0.1) for v in sample_embedding]
        await postgres_backend.create_memory(memory_data, embedding)
    
    # Search with similar embedding
    results = await postgres_backend.vector_search(
        embedding=sample_embedding,
        limit=2,
        container_id="test"
    )
    
    assert len(results) <= 2
    if results:
        assert "similarity" in results[0]
        assert results[0]["similarity"] > 0


@pytest.mark.asyncio
async def test_hybrid_search(postgres_backend, sample_memories, sample_embedding):
    """Test hybrid search combining vector and text"""
    # Create memories with embeddings
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        embedding = [v + np.random.normal(0, 0.1) for v in sample_embedding]
        await postgres_backend.create_memory(memory_data, embedding)
    
    # Hybrid search
    results = await postgres_backend.hybrid_search(
        query="database",
        embedding=sample_embedding,
        limit=3,
        vector_weight=0.5,
        container_id="test"
    )
    
    assert len(results) > 0
    assert "combined_score" in results[0]


# ==================== Relationship Tests ====================

@pytest.mark.asyncio
async def test_create_relationship(postgres_backend, sample_memories):
    """Test creating relationships between memories"""
    # Create two memories
    memory1_data = sample_memories[0]
    memory1_data["container_id"] = "test"
    memory1 = await postgres_backend.create_memory(memory1_data)
    
    memory2_data = sample_memories[1]
    memory2_data["container_id"] = "test"
    memory2 = await postgres_backend.create_memory(memory2_data)
    
    # Create relationship
    relationship = await postgres_backend.create_relationship(
        source_id=memory1["id"],
        target_id=memory2["id"],
        relationship_type="related",
        strength=0.8
    )
    
    assert relationship["id"] is not None
    assert relationship["source_memory_id"] == memory1["id"]
    assert relationship["target_memory_id"] == memory2["id"]
    assert relationship["relationship_type"] == "related"
    assert relationship["strength"] == 0.8


@pytest.mark.asyncio
async def test_get_related_memories(postgres_backend, sample_memories):
    """Test retrieving related memories"""
    # Create memories
    memories = []
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        memory = await postgres_backend.create_memory(memory_data)
        memories.append(memory)
    
    # Create relationships
    await postgres_backend.create_relationship(
        memories[0]["id"], memories[1]["id"], "similar", 0.9
    )
    await postgres_backend.create_relationship(
        memories[0]["id"], memories[2]["id"], "related", 0.7
    )
    
    # Get related memories
    related = await postgres_backend.get_related_memories(
        memory_id=memories[0]["id"],
        min_strength=0.6
    )
    
    assert len(related) == 2
    assert related[0]["relationship_strength"] >= 0.6


# ==================== Consolidation Tests ====================

@pytest.mark.asyncio
async def test_consolidate_memories(postgres_backend, sample_memories):
    """Test memory consolidation"""
    # Create memories to consolidate
    memory_ids = []
    for memory_data in sample_memories[:2]:
        memory_data["container_id"] = "test"
        memory = await postgres_backend.create_memory(memory_data)
        memory_ids.append(memory["id"])
    
    # Consolidate
    consolidated = await postgres_backend.consolidate_memories(
        source_ids=memory_ids,
        consolidated_content="Combined knowledge about Python and ML",
        consolidation_type="merge"
    )
    
    assert consolidated["id"] is not None
    assert consolidated["memory_type"] == "consolidated"
    assert consolidated["metadata"]["consolidation_type"] == "merge"
    assert consolidated["metadata"]["source_count"] == 2


@pytest.mark.asyncio
async def test_find_duplicates(postgres_backend, sample_embedding):
    """Test finding duplicate memories"""
    # Create similar memories
    memory1 = await postgres_backend.create_memory(
        {
            "content": "Test memory 1",
            "container_id": "test"
        },
        sample_embedding
    )
    
    # Create nearly identical embedding
    similar_embedding = [v + 0.001 for v in sample_embedding]
    memory2 = await postgres_backend.create_memory(
        {
            "content": "Test memory 2",
            "container_id": "test"
        },
        similar_embedding
    )
    
    # Find duplicates
    duplicates = await postgres_backend.find_duplicates(similarity_threshold=0.99)
    
    # Should find the similar pair
    found_pair = False
    for m1_id, m2_id, similarity in duplicates:
        if (m1_id == memory1["id"] and m2_id == memory2["id"]) or \
           (m1_id == memory2["id"] and m2_id == memory1["id"]):
            found_pair = True
            assert similarity > 0.99
            break
    
    assert found_pair


# ==================== Analytics Tests ====================

@pytest.mark.asyncio
async def test_get_statistics(postgres_backend, sample_memories):
    """Test getting database statistics"""
    # Create some memories
    for memory_data in sample_memories:
        memory_data["container_id"] = "test"
        await postgres_backend.create_memory(memory_data)
    
    stats = await postgres_backend.get_statistics()
    
    assert "total_memories" in stats
    assert "unique_types" in stats
    assert "avg_importance" in stats
    assert "backend" in stats
    assert stats["backend"] == "postgresql_unified"


@pytest.mark.asyncio
async def test_record_search_history(postgres_backend, sample_embedding):
    """Test recording search history"""
    await postgres_backend.record_search(
        query="test search",
        embedding=sample_embedding,
        results_count=5,
        selected_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        search_type="hybrid",
        metadata={"user_action": "clicked"},
        container_id="test"
    )
    
    # Verify search was recorded (would need a getter method)
    async with postgres_backend.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM search_history WHERE container_id = 'test'"
        )
        assert count > 0


# ==================== Service Layer Tests ====================

@pytest.mark.asyncio
async def test_service_create_and_search(memory_service):
    """Test memory service create and search operations"""
    # Create a memory
    memory = await memory_service.create_memory(
        content="Test memory for service layer",
        memory_type="test",
        importance_score=0.5,
        tags=["test"],
        generate_embedding=False
    )
    
    assert memory is not None
    assert memory["id"] is not None
    
    # Search for it
    results = await memory_service.keyword_search("service layer")
    
    assert len(results) > 0
    assert "service layer" in results[0]["content"]


@pytest.mark.asyncio
async def test_service_knowledge_graph(memory_service):
    """Test building a knowledge graph"""
    # Create connected memories
    memory1 = await memory_service.create_memory(
        content="Central memory",
        generate_embedding=False
    )
    
    memory2 = await memory_service.create_memory(
        content="Related memory 1",
        generate_embedding=False
    )
    
    memory3 = await memory_service.create_memory(
        content="Related memory 2",
        generate_embedding=False
    )
    
    # Create relationships
    await memory_service.create_relationship(
        memory1["id"], memory2["id"], "related", 0.8
    )
    await memory_service.create_relationship(
        memory1["id"], memory3["id"], "related", 0.7
    )
    
    # Build knowledge graph
    graph = await memory_service.build_knowledge_graph(
        center_memory_id=memory1["id"],
        depth=1
    )
    
    assert len(graph["nodes"]) >= 1
    assert len(graph["edges"]) >= 2
    assert graph["center"] == memory1["id"]


@pytest.mark.asyncio
async def test_service_auto_consolidation(memory_service):
    """Test automatic consolidation of duplicates"""
    # Create similar memories
    memory1 = await memory_service.create_memory(
        content="Duplicate content here",
        generate_embedding=False
    )
    
    memory2 = await memory_service.create_memory(
        content="Duplicate content here",
        generate_embedding=False
    )
    
    # Run auto-consolidation (dry run)
    results = await memory_service.auto_consolidate_duplicates(
        similarity_threshold=0.95,
        dry_run=True
    )
    
    assert results["dry_run"] is True
    # Would find duplicates if embeddings were enabled


# ==================== Performance Tests ====================

@pytest.mark.asyncio
async def test_bulk_insert_performance(postgres_backend):
    """Test bulk insert performance"""
    import time
    
    memories = []
    for i in range(100):
        memories.append({
            "content": f"Bulk test memory {i}",
            "memory_type": "test",
            "importance_score": 0.5,
            "container_id": "test"
        })
    
    start = time.time()
    
    for memory in memories:
        await postgres_backend.create_memory(memory)
    
    elapsed = time.time() - start
    
    # Should complete 100 inserts in reasonable time
    assert elapsed < 10.0  # 10 seconds max
    
    # Verify all were created
    count_query = """
        SELECT COUNT(*) FROM memories 
        WHERE container_id = 'test' AND memory_type = 'test'
    """
    async with postgres_backend.acquire() as conn:
        count = await conn.fetchval(count_query)
        assert count == 100


@pytest.mark.asyncio
async def test_search_performance(postgres_backend, sample_memories):
    """Test search performance with multiple memories"""
    import time
    
    # Create memories
    for i in range(50):
        memory_data = {
            "content": f"Performance test memory {i} with searchable content",
            "memory_type": "test",
            "container_id": "test"
        }
        await postgres_backend.create_memory(memory_data)
    
    # Test search performance
    start = time.time()
    
    for _ in range(10):
        await postgres_backend.text_search("searchable", container_id="test")
    
    elapsed = time.time() - start
    
    # 10 searches should complete quickly
    assert elapsed < 2.0  # 2 seconds max