"""
Unit tests for memory use cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.application.dto.memory_dto import (
    CreateMemoryDTO,
    MemoryDTO,
    UpdateMemoryDTO,
)
from src.application.exceptions import NotFoundError, ValidationError
from src.application.use_cases.memory_use_cases import (
    CreateMemoryUseCase,
    DeleteMemoryUseCase,
    FindSimilarMemoriesUseCase,
    GetMemoryUseCase,
    LinkMemoriesUseCase,
    SearchMemoriesUseCase,
    UpdateMemoryUseCase,
)
from src.domain.events.memory_events import MemoryCreated, MemoryDeleted, MemoryLinked, MemoryUpdated
from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus
from src.infrastructure.embeddings.models import EmbeddingResult


@pytest.mark.unit
class TestCreateMemoryUseCase:
    """Tests for CreateMemoryUseCase."""
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, dependencies):
        """Test successful memory creation."""
        # Arrange
        use_case = CreateMemoryUseCase(dependencies)
        request = CreateMemoryDTO(
            title="Test Memory",
            content="Test content",
            memory_type=MemoryType.FACT,
            importance_score=0.8,
            confidence_score=0.9,
            source_url="https://example.com",
            metadata={"key": "value"},
            tags=["test", "example"],
        )
        
        # Mock repositories and services
        memory_repo = AsyncMock()
        memory_repo.save = AsyncMock(side_effect=lambda m: m)
        
        event_store = AsyncMock()
        event_publisher = AsyncMock()
        tag_repo = AsyncMock()
        tag_repo.get_by_name = AsyncMock(return_value=None)
        
        # Mock embedding generation
        with patch("src.infrastructure.embeddings.EmbeddingClient.generate_embedding") as mock_embed:
            mock_embed.return_value = EmbeddingResult(
                text="Test Memory\n\nTest content",
                embedding=[0.1] * 1536,
                model="text-embedding-ada-002",
                dimensions=1536,
            )
            
            with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
                 patch.object(dependencies, "get_event_store", return_value=event_store), \
                 patch.object(dependencies, "get_event_publisher", return_value=event_publisher), \
                 patch.object(dependencies, "get_tag_repository", return_value=tag_repo), \
                 patch.object(dependencies, "begin_transaction") as mock_transaction:
                
                mock_session = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_session
                
                # Act
                result = await use_case.execute(request)
        
        # Assert
        assert isinstance(result, MemoryDTO)
        assert result.title == "Test Memory"
        assert result.content == "Test content"
        assert result.memory_type == MemoryType.FACT
        assert result.importance_score == 0.8
        assert result.confidence_score == 0.9
        
        # Verify repository was called
        memory_repo.save.assert_called_once()
        saved_memory = memory_repo.save.call_args[0][0]
        assert isinstance(saved_memory, Memory)
        assert saved_memory.title == "Test Memory"
        assert saved_memory.embedding is not None
        assert len(saved_memory.embedding) == 1536
        
        # Verify event was stored and published
        event_store.append.assert_called_once()
        event = event_store.append.call_args[0][0]
        assert isinstance(event, MemoryCreated)
        
        event_publisher.publish.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_create_memory_with_embedding_failure(self, dependencies):
        """Test memory creation when embedding generation fails."""
        # Arrange
        use_case = CreateMemoryUseCase(dependencies)
        request = CreateMemoryDTO(
            title="Test Memory",
            content="Test content",
            memory_type=MemoryType.FACT,
        )
        
        memory_repo = AsyncMock()
        memory_repo.save = AsyncMock(side_effect=lambda m: m)
        
        # Mock embedding generation failure
        with patch("src.infrastructure.embeddings.EmbeddingClient.generate_embedding") as mock_embed:
            mock_embed.side_effect = Exception("Embedding service unavailable")
            
            with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
                 patch.object(dependencies, "begin_transaction") as mock_transaction:
                
                mock_session = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_session
                
                # Act - should not raise, but use fallback
                result = await use_case.execute(request)
        
        # Assert - memory created with zero embedding
        assert isinstance(result, MemoryDTO)
        saved_memory = memory_repo.save.call_args[0][0]
        assert saved_memory.embedding == [0.0] * 1536  # Fallback zero vector


@pytest.mark.unit
class TestGetMemoryUseCase:
    """Tests for GetMemoryUseCase."""
    
    @pytest.mark.asyncio
    async def test_get_memory_success(self, dependencies, test_memory):
        """Test successful memory retrieval."""
        # Arrange
        use_case = GetMemoryUseCase(dependencies)
        memory_id = test_memory.id.value
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(return_value=test_memory)
        memory_repo.update_access_time = AsyncMock()
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await use_case.execute(memory_id)
        
        # Assert
        assert isinstance(result, MemoryDTO)
        assert result.id == memory_id
        assert result.title == test_memory.title
        
        memory_repo.get.assert_called_once_with(MemoryId(memory_id))
        memory_repo.update_access_time.assert_called_once_with(test_memory.id)
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, dependencies):
        """Test memory retrieval when not found."""
        # Arrange
        use_case = GetMemoryUseCase(dependencies)
        memory_id = uuid4()
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(return_value=None)
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act & Assert
            with pytest.raises(NotFoundError) as exc_info:
                await use_case.execute(memory_id)
            
            assert "Memory" in str(exc_info.value)
            assert str(memory_id) in str(exc_info.value)


@pytest.mark.unit
class TestUpdateMemoryUseCase:
    """Tests for UpdateMemoryUseCase."""
    
    @pytest.mark.asyncio
    async def test_update_memory_success(self, dependencies, test_memory):
        """Test successful memory update."""
        # Arrange
        use_case = UpdateMemoryUseCase(dependencies)
        memory_id = test_memory.id.value
        update_dto = UpdateMemoryDTO(
            title="Updated Title",
            content="Updated content",
            importance_score=0.9,
        )
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(return_value=test_memory)
        memory_repo.save = AsyncMock(return_value=test_memory)
        
        event_store = AsyncMock()
        
        # Mock embedding regeneration
        with patch("src.infrastructure.embeddings.EmbeddingClient.generate_embedding") as mock_embed:
            mock_embed.return_value = EmbeddingResult(
                text="Updated Title\n\nUpdated content",
                embedding=[0.2] * 1536,
                model="text-embedding-ada-002",
                dimensions=1536,
            )
            
            with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
                 patch.object(dependencies, "get_event_store", return_value=event_store), \
                 patch.object(dependencies, "begin_transaction") as mock_transaction:
                
                mock_session = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_session
                
                # Act
                result = await use_case.execute((memory_id, update_dto))
        
        # Assert
        assert isinstance(result, MemoryDTO)
        assert test_memory.title == "Updated Title"
        assert test_memory.content == "Updated content"
        assert test_memory.importance_score == 0.9
        
        # Verify embedding was regenerated
        assert test_memory.embedding == [0.2] * 1536
        
        # Verify event was stored
        event_store.append.assert_called_once()
        event = event_store.append.call_args[0][0]
        assert isinstance(event, MemoryUpdated)
        assert event.aggregate_id == memory_id
    
    @pytest.mark.asyncio
    async def test_update_memory_partial(self, dependencies, test_memory):
        """Test partial memory update."""
        # Arrange
        use_case = UpdateMemoryUseCase(dependencies)
        memory_id = test_memory.id.value
        original_content = test_memory.content
        update_dto = UpdateMemoryDTO(title="Only Title Updated")
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(return_value=test_memory)
        memory_repo.save = AsyncMock(return_value=test_memory)
        
        event_store = AsyncMock()
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "get_event_store", return_value=event_store), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await use_case.execute((memory_id, update_dto))
        
        # Assert
        assert test_memory.title == "Only Title Updated"
        assert test_memory.content == original_content  # Unchanged


@pytest.mark.unit
class TestDeleteMemoryUseCase:
    """Tests for DeleteMemoryUseCase."""
    
    @pytest.mark.asyncio
    async def test_delete_memory_success(self, dependencies, test_memory):
        """Test successful memory deletion."""
        # Arrange
        use_case = DeleteMemoryUseCase(dependencies)
        memory_id = test_memory.id.value
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(return_value=test_memory)
        memory_repo.delete = AsyncMock(return_value=True)
        
        event_store = AsyncMock()
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "get_event_store", return_value=event_store), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await use_case.execute(memory_id)
        
        # Assert
        assert result is True
        memory_repo.delete.assert_called_once_with(test_memory.id)
        
        # Verify event was stored
        event_store.append.assert_called_once()
        event = event_store.append.call_args[0][0]
        assert isinstance(event, MemoryDeleted)
        assert event.aggregate_id == memory_id


@pytest.mark.unit
class TestSearchMemoriesUseCase:
    """Tests for SearchMemoriesUseCase."""
    
    @pytest.mark.asyncio
    async def test_search_memories_success(self, dependencies, test_memory):
        """Test successful memory search."""
        # Arrange
        use_case = SearchMemoriesUseCase(dependencies)
        user_id = test_memory.user_id
        query = "test"
        limit = 10
        
        memory_repo = AsyncMock()
        memory_repo.search = AsyncMock(return_value=[test_memory])
        memory_repo.count_by_user = AsyncMock(return_value=1)
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await use_case.execute((user_id, query, limit))
        
        # Assert
        assert result.total == 1
        assert len(result.memories) == 1
        assert result.memories[0].id == test_memory.id.value
        
        memory_repo.search.assert_called_once_with(user_id, query, limit)


@pytest.mark.unit
class TestFindSimilarMemoriesUseCase:
    """Tests for FindSimilarMemoriesUseCase."""
    
    @pytest.mark.asyncio
    async def test_find_similar_memories_success(self, dependencies, test_memory):
        """Test finding similar memories."""
        # Arrange
        use_case = FindSimilarMemoriesUseCase(dependencies)
        user_id = test_memory.user_id
        query_text = "similar content"
        limit = 5
        threshold = 0.8
        
        memory_repo = AsyncMock()
        memory_repo.find_similar = AsyncMock(return_value=[test_memory])
        memory_repo.count_by_user = AsyncMock(return_value=10)
        
        # Mock embedding generation
        with patch("src.infrastructure.embeddings.EmbeddingClient.generate_embedding") as mock_embed:
            mock_embed.return_value = EmbeddingResult(
                text=query_text,
                embedding=[0.3] * 1536,
                model="text-embedding-ada-002",
                dimensions=1536,
            )
            
            with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
                 patch.object(dependencies, "begin_transaction") as mock_transaction:
                
                mock_session = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_session
                
                # Act
                result = await use_case.execute((user_id, query_text, limit, threshold))
        
        # Assert
        assert result.total == 10
        assert len(result.memories) == 1
        assert result.memories[0].id == test_memory.id.value
        
        memory_repo.find_similar.assert_called_once()
        call_args = memory_repo.find_similar.call_args[0]
        assert call_args[0] == user_id
        assert call_args[1] == [0.3] * 1536
        assert call_args[2] == limit
        assert call_args[3] == threshold


@pytest.mark.unit
class TestLinkMemoriesUseCase:
    """Tests for LinkMemoriesUseCase."""
    
    @pytest.mark.asyncio
    async def test_link_memories_success(self, dependencies, test_memory):
        """Test successful memory linking."""
        # Arrange
        use_case = LinkMemoriesUseCase(dependencies)
        from_memory = test_memory
        to_memory = Memory(
            id=MemoryId(uuid4()),
            user_id=test_memory.user_id,
            title="Target Memory",
            content="Target content",
            memory_type=MemoryType.CONCEPT,
        )
        link_type = "related"
        
        memory_repo = AsyncMock()
        memory_repo.get = AsyncMock(side_effect=lambda id: from_memory if id == from_memory.id else to_memory)
        memory_repo.link_memories = AsyncMock(return_value=True)
        
        event_store = AsyncMock()
        
        with patch.object(dependencies, "get_memory_repository", return_value=memory_repo), \
             patch.object(dependencies, "get_event_store", return_value=event_store), \
             patch.object(dependencies, "begin_transaction") as mock_transaction:
            
            mock_session = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await use_case.execute((from_memory.id.value, to_memory.id.value, link_type))
        
        # Assert
        assert result is True
        memory_repo.link_memories.assert_called_once_with(from_memory.id, to_memory.id, link_type)
        
        # Verify event was stored
        event_store.append.assert_called_once()
        event = event_store.append.call_args[0][0]
        assert isinstance(event, MemoryLinked)
    
    @pytest.mark.asyncio
    async def test_link_memories_self_link(self, dependencies):
        """Test linking memory to itself raises error."""
        # Arrange
        use_case = LinkMemoriesUseCase(dependencies)
        memory_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute((memory_id, memory_id, "related"))
        
        assert "Cannot link a memory to itself" in str(exc_info.value)