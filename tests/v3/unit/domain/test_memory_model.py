"""
Unit tests for Memory domain model.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.models.memory import (
    Memory,
    MemoryId,
    MemoryType,
    MemoryStatus,
    MemoryFactory,
)


class TestMemoryId:
    """Tests for MemoryId value object."""
    
    def test_create_memory_id(self):
        """Test creating a MemoryId."""
        id_value = uuid4()
        memory_id = MemoryId(id_value)
        assert memory_id.value == id_value
    
    def test_memory_id_equality(self):
        """Test MemoryId equality."""
        id_value = uuid4()
        memory_id1 = MemoryId(id_value)
        memory_id2 = MemoryId(id_value)
        memory_id3 = MemoryId(uuid4())
        
        assert memory_id1 == memory_id2
        assert memory_id1 != memory_id3
    
    def test_memory_id_string_representation(self):
        """Test MemoryId string conversion."""
        id_value = uuid4()
        memory_id = MemoryId(id_value)
        assert str(memory_id) == str(id_value)


class TestMemoryType:
    """Tests for MemoryType enum."""
    
    def test_memory_type_values(self):
        """Test all memory type values exist."""
        assert MemoryType.FACT == "fact"
        assert MemoryType.EXPERIENCE == "experience"
        assert MemoryType.CONCEPT == "concept"
        assert MemoryType.PROCEDURE == "procedure"
        assert MemoryType.REFLECTION == "reflection"
    
    def test_memory_type_from_string(self):
        """Test creating MemoryType from string."""
        assert MemoryType("fact") == MemoryType.FACT
        assert MemoryType("experience") == MemoryType.EXPERIENCE
    
    def test_invalid_memory_type(self):
        """Test invalid memory type raises error."""
        with pytest.raises(ValueError):
            MemoryType("invalid_type")


class TestMemoryStatus:
    """Tests for MemoryStatus enum."""
    
    def test_memory_status_values(self):
        """Test all memory status values exist."""
        assert MemoryStatus.ACTIVE == "active"
        assert MemoryStatus.ARCHIVED == "archived"
        assert MemoryStatus.DELETED == "deleted"
    
    def test_memory_status_transitions(self):
        """Test valid status transitions."""
        active = MemoryStatus.ACTIVE
        archived = MemoryStatus.ARCHIVED
        deleted = MemoryStatus.DELETED
        
        # Active can transition to archived or deleted
        assert active != archived
        assert active != deleted


class TestMemory:
    """Tests for Memory aggregate."""
    
    def test_create_memory(self):
        """Test creating a memory."""
        memory_id = MemoryId(uuid4())
        user_id = uuid4()
        
        memory = Memory(
            id=memory_id,
            user_id=user_id,
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.id == memory_id
        assert memory.user_id == user_id
        assert memory.title == "Test Memory"
        assert memory.content == "This is test content"
        assert memory.memory_type == MemoryType.FACT
        assert memory.status == MemoryStatus.ACTIVE
        assert memory.importance_score == 0.5
        assert memory.confidence_score == 1.0
        assert memory.retention_strength == 1.0
        assert memory.retrieval_count == 0
    
    def test_memory_with_optional_fields(self):
        """Test creating memory with all optional fields."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.EXPERIENCE,
            status=MemoryStatus.ARCHIVED,
            importance_score=0.8,
            confidence_score=0.9,
            source_url="https://example.com",
            embedding=[0.1, 0.2, 0.3],
            embedding_model="test-model",
            metadata={"key": "value"},
            tags=[uuid4(), uuid4()],
            linked_memories=[MemoryId(uuid4())],
            attachments=["file1.pdf", "file2.jpg"],
        )
        
        assert memory.status == MemoryStatus.ARCHIVED
        assert memory.importance_score == 0.8
        assert memory.confidence_score == 0.9
        assert memory.source_url == "https://example.com"
        assert memory.embedding == [0.1, 0.2, 0.3]
        assert memory.embedding_model == "test-model"
        assert memory.metadata == {"key": "value"}
        assert len(memory.tags) == 2
        assert len(memory.linked_memories) == 1
        assert len(memory.attachments) == 2
    
    def test_memory_timestamps(self):
        """Test memory timestamps."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)
        assert isinstance(memory.accessed_at, datetime)
        assert memory.created_at == memory.updated_at == memory.accessed_at
    
    def test_memory_validation(self):
        """Test memory validation rules."""
        # Test empty title
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Memory(
                id=MemoryId(uuid4()),
                user_id=uuid4(),
                title="",
                content="Content",
                memory_type=MemoryType.FACT,
            )
        
        # Test empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Memory(
                id=MemoryId(uuid4()),
                user_id=uuid4(),
                title="Title",
                content="",
                memory_type=MemoryType.FACT,
            )
        
        # Test invalid importance score
        with pytest.raises(ValueError, match="Importance score must be between 0 and 1"):
            Memory(
                id=MemoryId(uuid4()),
                user_id=uuid4(),
                title="Title",
                content="Content",
                memory_type=MemoryType.FACT,
                importance_score=1.5,
            )
        
        # Test invalid confidence score
        with pytest.raises(ValueError, match="Confidence score must be between 0 and 1"):
            Memory(
                id=MemoryId(uuid4()),
                user_id=uuid4(),
                title="Title",
                content="Content",
                memory_type=MemoryType.FACT,
                confidence_score=-0.1,
            )
    
    def test_update_retention_strength(self):
        """Test updating retention strength."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        initial_strength = memory.retention_strength
        memory.update_retention_strength(0.9)
        
        assert memory.retention_strength == 0.9
        assert memory.retention_strength != initial_strength
    
    def test_increment_retrieval_count(self):
        """Test incrementing retrieval count."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.retrieval_count == 0
        
        memory.increment_retrieval_count()
        assert memory.retrieval_count == 1
        
        memory.increment_retrieval_count()
        assert memory.retrieval_count == 2
    
    def test_add_tag(self):
        """Test adding tags to memory."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        tag_id = uuid4()
        memory.add_tag(tag_id)
        
        assert tag_id in memory.tags
        
        # Test duplicate tag
        memory.add_tag(tag_id)
        assert len(memory.tags) == 1  # Should not add duplicate
    
    def test_remove_tag(self):
        """Test removing tags from memory."""
        tag_id = uuid4()
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
            tags=[tag_id],
        )
        
        assert tag_id in memory.tags
        
        memory.remove_tag(tag_id)
        assert tag_id not in memory.tags
        
        # Test removing non-existent tag
        memory.remove_tag(uuid4())  # Should not raise error
    
    def test_link_memory(self):
        """Test linking memories."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        linked_id = MemoryId(uuid4())
        memory.link_memory(linked_id)
        
        assert linked_id in memory.linked_memories
        
        # Test duplicate link
        memory.link_memory(linked_id)
        assert len(memory.linked_memories) == 1  # Should not add duplicate
    
    def test_unlink_memory(self):
        """Test unlinking memories."""
        linked_id = MemoryId(uuid4())
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
            linked_memories=[linked_id],
        )
        
        assert linked_id in memory.linked_memories
        
        memory.unlink_memory(linked_id)
        assert linked_id not in memory.linked_memories
    
    def test_archive_memory(self):
        """Test archiving a memory."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.status == MemoryStatus.ACTIVE
        
        memory.archive()
        assert memory.status == MemoryStatus.ARCHIVED
    
    def test_delete_memory(self):
        """Test soft deleting a memory."""
        memory = Memory(
            id=MemoryId(uuid4()),
            user_id=uuid4(),
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.status == MemoryStatus.ACTIVE
        
        memory.delete()
        assert memory.status == MemoryStatus.DELETED


class TestMemoryFactory:
    """Tests for MemoryFactory."""
    
    def test_create_fact_memory(self):
        """Test creating a fact memory."""
        user_id = uuid4()
        memory = MemoryFactory.create_fact(
            user_id=user_id,
            title="Fact Title",
            content="Fact content",
            source_url="https://example.com",
            confidence_score=0.95,
        )
        
        assert memory.memory_type == MemoryType.FACT
        assert memory.user_id == user_id
        assert memory.title == "Fact Title"
        assert memory.content == "Fact content"
        assert memory.source_url == "https://example.com"
        assert memory.confidence_score == 0.95
    
    def test_create_experience_memory(self):
        """Test creating an experience memory."""
        user_id = uuid4()
        memory = MemoryFactory.create_experience(
            user_id=user_id,
            title="Experience Title",
            content="Experience content",
            importance_score=0.8,
        )
        
        assert memory.memory_type == MemoryType.EXPERIENCE
        assert memory.importance_score == 0.8
    
    def test_create_concept_memory(self):
        """Test creating a concept memory."""
        user_id = uuid4()
        memory = MemoryFactory.create_concept(
            user_id=user_id,
            title="Concept Title",
            content="Concept content",
            related_memories=[MemoryId(uuid4()), MemoryId(uuid4())],
        )
        
        assert memory.memory_type == MemoryType.CONCEPT
        assert len(memory.linked_memories) == 2
    
    def test_create_procedure_memory(self):
        """Test creating a procedure memory."""
        user_id = uuid4()
        memory = MemoryFactory.create_procedure(
            user_id=user_id,
            title="Procedure Title",
            content="Step 1\\nStep 2\\nStep 3",
            metadata={"steps": 3},
        )
        
        assert memory.memory_type == MemoryType.PROCEDURE
        assert memory.metadata["steps"] == 3
    
    def test_create_reflection_memory(self):
        """Test creating a reflection memory."""
        user_id = uuid4()
        source_memory = MemoryId(uuid4())
        memory = MemoryFactory.create_reflection(
            user_id=user_id,
            title="Reflection Title",
            content="Reflection content",
            source_memory=source_memory,
        )
        
        assert memory.memory_type == MemoryType.REFLECTION
        assert source_memory in memory.linked_memories