"""
Integration tests for memory repository.
"""

import pytest
from uuid import uuid4

from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus
from src.infrastructure.database.repositories.memory_repository import SQLMemoryRepository

from ..fixtures.factories import MemoryFactory, UserFactory, TagFactory


@pytest.mark.integration
@pytest.mark.asyncio
class TestSQLMemoryRepository:
    """Integration tests for SQLMemoryRepository."""
    
    async def test_save_and_get_memory(self, async_db_session):
        """Test saving and retrieving a memory."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory = MemoryFactory.create()
        
        # Act
        saved_memory = await repo.save(memory)
        retrieved_memory = await repo.get(memory.id)
        
        # Assert
        assert saved_memory.id == memory.id
        assert retrieved_memory is not None
        assert retrieved_memory.id == memory.id
        assert retrieved_memory.title == memory.title
        assert retrieved_memory.content == memory.content
        assert retrieved_memory.memory_type == memory.memory_type
    
    async def test_get_nonexistent_memory(self, async_db_session):
        """Test getting a memory that doesn't exist."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory_id = MemoryId(uuid4())
        
        # Act
        result = await repo.get(memory_id)
        
        # Assert
        assert result is None
    
    async def test_update_memory(self, async_db_session):
        """Test updating an existing memory."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory = MemoryFactory.create()
        await repo.save(memory)
        
        # Act
        memory.title = "Updated Title"
        memory.content = "Updated content"
        memory.importance_score = 0.9
        
        updated_memory = await repo.save(memory)
        retrieved_memory = await repo.get(memory.id)
        
        # Assert
        assert updated_memory.title == "Updated Title"
        assert retrieved_memory.title == "Updated Title"
        assert retrieved_memory.content == "Updated content"
        assert retrieved_memory.importance_score == 0.9
    
    async def test_delete_memory(self, async_db_session):
        """Test deleting a memory."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory = MemoryFactory.create()
        await repo.save(memory)
        
        # Act
        deleted = await repo.delete(memory.id)
        retrieved = await repo.get(memory.id)
        
        # Assert
        assert deleted is True
        assert retrieved is None
    
    async def test_delete_nonexistent_memory(self, async_db_session):
        """Test deleting a memory that doesn't exist."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory_id = MemoryId(uuid4())
        
        # Act
        deleted = await repo.delete(memory_id)
        
        # Assert
        assert deleted is False
    
    async def test_get_by_user(self, async_db_session):
        """Test getting memories by user."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Create memories for user
        user_memories = MemoryFactory.create_batch(5, user_id=user_id)
        for memory in user_memories:
            await repo.save(memory)
        
        # Create memories for other user
        other_memories = MemoryFactory.create_batch(3, user_id=other_user_id)
        for memory in other_memories:
            await repo.save(memory)
        
        # Act
        result = await repo.get_by_user(user_id, skip=0, limit=10)
        
        # Assert
        assert len(result) == 5
        assert all(m.user_id == user_id for m in result)
    
    async def test_get_by_user_with_pagination(self, async_db_session):
        """Test pagination when getting memories by user."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        
        memories = MemoryFactory.create_batch(10, user_id=user_id)
        for memory in memories:
            await repo.save(memory)
        
        # Act
        page1 = await repo.get_by_user(user_id, skip=0, limit=3)
        page2 = await repo.get_by_user(user_id, skip=3, limit=3)
        page3 = await repo.get_by_user(user_id, skip=6, limit=10)
        
        # Assert
        assert len(page1) == 3
        assert len(page2) == 3
        assert len(page3) == 4
        
        # Check no overlap
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert len(page1_ids & page2_ids) == 0
    
    async def test_get_by_user_with_filters(self, async_db_session):
        """Test filtering when getting memories by user."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        
        # Create memories of different types
        fact_memories = MemoryFactory.create_batch(
            3, user_id=user_id, memory_type=MemoryType.FACT
        )
        experience_memories = MemoryFactory.create_batch(
            2, user_id=user_id, memory_type=MemoryType.EXPERIENCE
        )
        archived_memory = MemoryFactory.create(
            user_id=user_id, status=MemoryStatus.ARCHIVED
        )
        
        for memory in fact_memories + experience_memories + [archived_memory]:
            await repo.save(memory)
        
        # Act
        facts = await repo.get_by_user(
            user_id, memory_type=MemoryType.FACT
        )
        archived = await repo.get_by_user(
            user_id, status=MemoryStatus.ARCHIVED
        )
        
        # Assert
        assert len(facts) == 3
        assert all(m.memory_type == MemoryType.FACT for m in facts)
        
        assert len(archived) == 1
        assert archived[0].status == MemoryStatus.ARCHIVED
    
    async def test_search_memories(self, async_db_session):
        """Test searching memories by content."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        
        # Create memories with specific content
        python_memory = MemoryFactory.create(
            user_id=user_id,
            title="Python Programming",
            content="Python is a versatile programming language",
        )
        java_memory = MemoryFactory.create(
            user_id=user_id,
            title="Java Development",
            content="Java is used for enterprise applications",
        )
        unrelated_memory = MemoryFactory.create(
            user_id=user_id,
            title="Cooking Recipe",
            content="How to make pasta",
        )
        
        for memory in [python_memory, java_memory, unrelated_memory]:
            await repo.save(memory)
        
        # Act
        programming_results = await repo.search(user_id, "programming", limit=10)
        java_results = await repo.search(user_id, "java", limit=10)
        pasta_results = await repo.search(user_id, "pasta", limit=10)
        
        # Assert
        assert len(programming_results) == 1
        assert programming_results[0].id == python_memory.id
        
        assert len(java_results) == 1
        assert java_results[0].id == java_memory.id
        
        assert len(pasta_results) == 1
        assert pasta_results[0].id == unrelated_memory.id
    
    @pytest.mark.requires_real_db
    async def test_find_similar_with_embeddings(self, async_db_session):
        """Test finding similar memories using embeddings."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        
        # Create memories with embeddings
        memories = []
        for i in range(5):
            memory = MemoryFactory.create_with_embedding(
                user_id=user_id,
                title=f"Memory {i}",
                embedding_dim=1536,
            )
            await repo.save(memory)
            memories.append(memory)
        
        # Create query embedding similar to first memory
        query_embedding = memories[0].embedding.copy()
        query_embedding[0] += 0.01  # Slight variation
        
        # Act
        similar = await repo.find_similar(
            user_id, query_embedding, limit=3, threshold=0.9
        )
        
        # Assert
        assert len(similar) <= 3
        # First memory should be most similar
        if similar:
            assert similar[0].id == memories[0].id
    
    async def test_link_memories(self, async_db_session):
        """Test linking memories."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory1 = MemoryFactory.create()
        memory2 = MemoryFactory.create(user_id=memory1.user_id)
        
        await repo.save(memory1)
        await repo.save(memory2)
        
        # Act
        linked = await repo.link_memories(memory1.id, memory2.id, "related")
        linked_memories = await repo.get_linked_memories(memory1.id)
        
        # Assert
        assert linked is True
        assert len(linked_memories) == 1
        assert linked_memories[0].id == memory2.id
    
    async def test_link_memories_duplicate(self, async_db_session):
        """Test linking memories that are already linked."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory1 = MemoryFactory.create()
        memory2 = MemoryFactory.create(user_id=memory1.user_id)
        
        await repo.save(memory1)
        await repo.save(memory2)
        await repo.link_memories(memory1.id, memory2.id, "related")
        
        # Act
        linked_again = await repo.link_memories(memory1.id, memory2.id, "related")
        
        # Assert
        assert linked_again is False
    
    async def test_unlink_memories(self, async_db_session):
        """Test unlinking memories."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory1 = MemoryFactory.create()
        memory2 = MemoryFactory.create(user_id=memory1.user_id)
        
        await repo.save(memory1)
        await repo.save(memory2)
        await repo.link_memories(memory1.id, memory2.id, "related")
        
        # Act
        unlinked = await repo.unlink_memories(memory1.id, memory2.id)
        linked_memories = await repo.get_linked_memories(memory1.id)
        
        # Assert
        assert unlinked is True
        assert len(linked_memories) == 0
    
    async def test_update_access_time(self, async_db_session):
        """Test updating memory access time."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        memory = MemoryFactory.create()
        await repo.save(memory)
        
        original_access_time = memory.accessed_at
        original_count = memory.retrieval_count
        
        # Act
        await repo.update_access_time(memory.id)
        updated_memory = await repo.get(memory.id)
        
        # Assert
        assert updated_memory.accessed_at > original_access_time
        assert updated_memory.retrieval_count == original_count + 1
    
    async def test_count_by_user(self, async_db_session):
        """Test counting memories by user."""
        # Arrange
        repo = SQLMemoryRepository(async_db_session)
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Create memories
        user_memories = MemoryFactory.create_batch(7, user_id=user_id)
        other_memories = MemoryFactory.create_batch(3, user_id=other_user_id)
        
        for memory in user_memories + other_memories:
            await repo.save(memory)
        
        # Act
        user_count = await repo.count_by_user(user_id)
        other_count = await repo.count_by_user(other_user_id)
        empty_count = await repo.count_by_user(uuid4())
        
        # Assert
        assert user_count == 7
        assert other_count == 3
        assert empty_count == 0