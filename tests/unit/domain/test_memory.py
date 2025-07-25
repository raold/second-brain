"""
Unit tests for Memory domain model.
"""

import pytest
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus


class TestMemoryId:
    """Test MemoryId value object."""
    
    def test_generate_creates_unique_ids(self):
        """Test that generate creates unique IDs."""
        id1 = MemoryId.generate()
        id2 = MemoryId.generate()
        assert id1 != id2
        assert isinstance(id1.value, UUID)
    
    def test_from_string_creates_valid_id(self):
        """Test creating ID from string."""
        uuid_str = str(uuid4())
        memory_id = MemoryId.from_string(uuid_str)
        assert str(memory_id) == uuid_str
    
    def test_from_string_invalid_uuid_raises_error(self):
        """Test that invalid UUID string raises error."""
        with pytest.raises(ValueError):
            MemoryId.from_string("not-a-uuid")
    
    def test_memory_id_is_immutable(self):
        """Test that MemoryId is immutable."""
        memory_id = MemoryId.generate()
        with pytest.raises(AttributeError):
            memory_id.value = uuid4()


class TestMemory:
    """Test Memory entity."""
    
    @pytest.fixture
    def valid_memory_data(self):
        """Provide valid memory data."""
        return {
            "id": MemoryId.generate(),
            "user_id": uuid4(),
            "title": "Test Memory",
            "content": "This is a test memory content.",
            "memory_type": MemoryType.SEMANTIC,
        }
    
    def test_create_memory_with_valid_data(self, valid_memory_data):
        """Test creating memory with valid data."""
        memory = Memory(**valid_memory_data)
        assert memory.id == valid_memory_data["id"]
        assert memory.title == valid_memory_data["title"]
        assert memory.status == MemoryStatus.ACTIVE
        assert memory.importance_score == 0.5
        assert memory.retention_strength == 1.0
    
    def test_memory_requires_title(self, valid_memory_data):
        """Test that memory requires title."""
        valid_memory_data["title"] = ""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Memory(**valid_memory_data)
    
    def test_memory_requires_content(self, valid_memory_data):
        """Test that memory requires content."""
        valid_memory_data["content"] = ""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Memory(**valid_memory_data)
    
    def test_importance_score_validation(self, valid_memory_data):
        """Test importance score validation."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            valid_memory_data["importance_score"] = score
            memory = Memory(**valid_memory_data)
            assert memory.importance_score == score
        
        # Invalid scores
        for score in [-0.1, 1.1, 2.0]:
            valid_memory_data["importance_score"] = score
            with pytest.raises(ValueError, match="Importance score must be between 0 and 1"):
                Memory(**valid_memory_data)
    
    def test_update_content(self, valid_memory_data):
        """Test updating memory content."""
        memory = Memory(**valid_memory_data)
        old_updated_at = memory.updated_at
        
        # Add small delay to ensure timestamp difference
        time.sleep(0.001)
        
        memory.update_content("New Title", "New content")
        assert memory.title == "New Title"
        assert memory.content == "New content"
        assert memory.updated_at > old_updated_at
    
    def test_tag_operations(self, valid_memory_data):
        """Test tag operations."""
        memory = Memory(**valid_memory_data)
        
        # Add tags
        memory.add_tag("python")
        memory.add_tag("testing")
        assert "python" in memory.tags
        assert "testing" in memory.tags
        assert len(memory.tags) == 2
        
        # Add duplicate tag (should not add)
        memory.add_tag("python")
        assert len(memory.tags) == 2
        
        # Remove tag
        memory.remove_tag("python")
        assert "python" not in memory.tags
        assert len(memory.tags) == 1
        
        # Remove non-existent tag (should not error)
        memory.remove_tag("nonexistent")
        assert len(memory.tags) == 1
    
    def test_memory_linking(self, valid_memory_data):
        """Test memory linking functionality."""
        memory = Memory(**valid_memory_data)
        other_id = MemoryId.generate()
        
        # Link to another memory
        memory.link_to(other_id)
        assert other_id in memory.linked_memories
        
        # Link to same memory again (should not duplicate)
        memory.link_to(other_id)
        assert len(memory.linked_memories) == 1
        
        # Cannot link to self
        memory.link_to(memory.id)
        assert memory.id not in memory.linked_memories
        
        # Unlink
        memory.unlink_from(other_id)
        assert other_id not in memory.linked_memories
    
    def test_access_tracking(self, valid_memory_data):
        """Test access tracking."""
        memory = Memory(**valid_memory_data)
        initial_count = memory.retrieval_count
        old_accessed_at = memory.accessed_at
        
        # Add small delay to ensure timestamp difference
        time.sleep(0.001)
        
        memory.record_access()
        assert memory.retrieval_count == initial_count + 1
        assert memory.accessed_at > old_accessed_at
    
    def test_archiving(self, valid_memory_data):
        """Test archiving functionality."""
        memory = Memory(**valid_memory_data)
        
        # Archive
        memory.archive()
        assert memory.status == MemoryStatus.ARCHIVED
        
        # Unarchive
        memory.unarchive()
        assert memory.status == MemoryStatus.ACTIVE
    
    def test_soft_delete(self, valid_memory_data):
        """Test soft delete."""
        memory = Memory(**valid_memory_data)
        memory.soft_delete()
        assert memory.status == MemoryStatus.DELETED
    
    def test_retention_decay(self, valid_memory_data):
        """Test retention decay."""
        memory = Memory(**valid_memory_data)
        initial_strength = memory.retention_strength
        
        memory.decay_retention(0.9)
        assert memory.retention_strength == initial_strength * 0.9
        
        # Test minimum retention
        for _ in range(1000):
            memory.decay_retention(0.1)
        assert memory.retention_strength >= 0.01
    
    def test_retention_boost(self, valid_memory_data):
        """Test retention boost."""
        memory = Memory(**valid_memory_data)
        memory.retention_strength = 0.5
        
        memory.boost_retention(1.2)
        assert memory.retention_strength == 0.6
        
        # Test maximum retention
        memory.retention_strength = 0.9
        memory.boost_retention(2.0)
        assert memory.retention_strength == 1.0
    
    def test_to_dict(self, valid_memory_data):
        """Test dictionary conversion."""
        memory = Memory(**valid_memory_data)
        memory.add_tag("test")
        
        data = memory.to_dict()
        assert data["id"] == str(memory.id)
        assert data["title"] == memory.title
        assert data["tags"] == ["test"]
        assert "created_at" in data
        assert "updated_at" in data


class TestMemoryType:
    """Test MemoryType enum."""
    
    def test_memory_types_exist(self):
        """Test that all memory types exist."""
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.SEMANTIC.value == "semantic"
        assert MemoryType.PROCEDURAL.value == "procedural"
        assert MemoryType.PROSPECTIVE.value == "prospective"
        assert MemoryType.WORKING.value == "working"


class TestMemoryStatus:
    """Test MemoryStatus enum."""
    
    def test_memory_statuses_exist(self):
        """Test that all memory statuses exist."""
        assert MemoryStatus.DRAFT.value == "draft"
        assert MemoryStatus.ACTIVE.value == "active"
        assert MemoryStatus.ARCHIVED.value == "archived"
        assert MemoryStatus.DELETED.value == "deleted"