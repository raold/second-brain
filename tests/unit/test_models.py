"""
import pytest

pytestmark = pytest.mark.unit

Unit tests for core models in Second Brain
"""

from datetime import datetime
from uuid import UUID

from app.models.memory import Memory, MemoryMetrics, MemoryType


class TestMemoryModel:
    """Test cases for Memory model"""

    def test_memory_creation_basic(self):
        """Test basic memory creation"""
        memory = Memory(content="Test memory content", memory_type=MemoryType.FACTUAL)
        assert memory.content == "Test memory content"
        assert memory.memory_type == MemoryType.FACTUAL
        assert memory.importance_score == 0.5
        assert memory.tags == []
        assert memory.metadata == {}
        assert memory.access_count == 0

    def test_memory_creation_with_all_fields(self):
        """Test memory creation with all fields"""
        now = datetime.utcnow()
        memory = Memory(
            id="test-id",
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.8,
            created_at=now,
            updated_at=now,
            user_id="user-123",
            tags=["test", "unit"],
            metadata={"source": "test"},
            embedding=[0.1, 0.2, 0.3],
            access_count=5,
            last_accessed=now,
        )

        assert memory.id == "test-id"
        assert memory.content == "Test content"
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.importance_score == 0.8
        assert memory.created_at == now
        assert memory.updated_at == now
        assert memory.user_id == "user-123"
        assert memory.tags == ["test", "unit"]
        assert memory.metadata == {"source": "test"}
        assert memory.embedding == [0.1, 0.2, 0.3]
        assert memory.access_count == 5
        assert memory.last_accessed == now

    def test_memory_create_classmethod(self):
        """Test Memory.create class method"""
        memory = Memory.create(
            content="Created memory", memory_type=MemoryType.EPISODIC, user_id="user-456"
        )

        assert memory.content == "Created memory"
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.user_id == "user-456"
        assert memory.id is not None
        assert memory.created_at is not None
        assert memory.updated_at is not None
        # Verify ID is a valid UUID string
        UUID(memory.id)

    def test_memory_type_enum(self):
        """Test MemoryType enumeration"""
        assert MemoryType.FACTUAL == "factual"
        assert MemoryType.PROCEDURAL == "procedural"
        assert MemoryType.EPISODIC == "episodic"
        assert MemoryType.SEMANTIC == "semantic"

    def test_memory_type_validation(self):
        """Test memory type validation"""
        # Valid types should work
        for mem_type in MemoryType:
            memory = Memory(content="test", memory_type=mem_type)
            assert memory.memory_type == mem_type

    def test_memory_serialization(self):
        """Test memory model serialization"""
        memory = Memory(
            content="Test content",
            memory_type=MemoryType.FACTUAL,
            tags=["test"],
            metadata={"key": "value"},
        )

        data = memory.model_dump()
        assert isinstance(data, dict)
        assert data["content"] == "Test content"
        assert data["memory_type"] == "factual"  # Should be string value
        assert data["tags"] == ["test"]
        assert data["metadata"] == {"key": "value"}

    def test_memory_deserialization(self):
        """Test memory model deserialization"""
        data = {
            "content": "Deserialized content",
            "memory_type": "semantic",
            "importance_score": 0.9,
            "tags": ["deserialized"],
            "metadata": {"test": True},
        }

        memory = Memory(**data)
        assert memory.content == "Deserialized content"
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.importance_score == 0.9
        assert memory.tags == ["deserialized"]
        assert memory.metadata == {"test": True}


class TestMemoryMetrics:
    """Test cases for MemoryMetrics model"""

    def test_memory_metrics_creation(self):
        """Test MemoryMetrics creation"""
        now = datetime.utcnow()
        metrics = MemoryMetrics(
            total_memories=100,
            memories_by_type={"factual": 50, "semantic": 30, "episodic": 20},
            average_importance=0.65,
            recent_memories=25,
            total_access_count=500,
            last_updated=now,
        )

        assert metrics.total_memories == 100
        assert metrics.memories_by_type == {"factual": 50, "semantic": 30, "episodic": 20}
        assert metrics.average_importance == 0.65
        assert metrics.recent_memories == 25
        assert metrics.total_access_count == 500
        assert metrics.last_updated == now

    def test_memory_metrics_serialization(self):
        """Test MemoryMetrics serialization"""
        now = datetime.utcnow()
        metrics = MemoryMetrics(
            total_memories=50,
            memories_by_type={},
            average_importance=0.5,
            recent_memories=0,
            total_access_count=0,
            last_updated=now,
        )

        data = metrics.model_dump()
        assert isinstance(data, dict)
        assert data["total_memories"] == 50
        assert data["memories_by_type"] == {}
        assert data["average_importance"] == 0.5
