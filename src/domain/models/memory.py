"""
Memory Domain Model

Core entity representing a memory in the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class MemoryType(str, Enum):
    """Types of memories supported by the system."""
    
    EPISODIC = "episodic"  # Personal experiences
    SEMANTIC = "semantic"  # Facts and concepts
    PROCEDURAL = "procedural"  # How-to knowledge
    PROSPECTIVE = "prospective"  # Future intentions
    WORKING = "working"  # Temporary active memory


class MemoryStatus(str, Enum):
    """Memory lifecycle status."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(frozen=True)
class MemoryId:
    """Value object for Memory ID."""
    
    value: UUID
    
    @classmethod
    def generate(cls) -> MemoryId:
        """Generate a new memory ID."""
        return cls(value=uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> MemoryId:
        """Create from string representation."""
        return cls(value=UUID(value))
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)


@dataclass
class Memory:
    """
    Core memory entity.
    
    Represents a single unit of knowledge in the system.
    """
    
    # Identity
    id: MemoryId
    user_id: UUID
    
    # Core content
    title: str
    content: str
    memory_type: MemoryType
    
    # Metadata
    status: MemoryStatus = MemoryStatus.ACTIVE
    importance_score: float = 0.5  # 0.0 to 1.0
    confidence_score: float = 1.0  # 0.0 to 1.0
    
    # Relationships
    tags: list[str] = field(default_factory=list)
    linked_memories: list[MemoryId] = field(default_factory=list)
    source_url: Optional[str] = None
    
    # Embeddings and search
    embedding: Optional[list[float]] = None
    embedding_model: Optional[str] = None
    
    # Additional data
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Cognitive properties
    retention_strength: float = 1.0  # Decay over time
    retrieval_count: int = 0
    
    def __post_init__(self) -> None:
        """Validate memory after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate memory state."""
        if not self.title:
            raise ValueError("Memory title cannot be empty")
        
        if not self.content:
            raise ValueError("Memory content cannot be empty")
        
        if not 0 <= self.importance_score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
        
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if not 0 <= self.retention_strength <= 1:
            raise ValueError("Retention strength must be between 0 and 1")
    
    def update_content(self, title: str, content: str) -> None:
        """Update memory content."""
        self.title = title
        self.content = content
        self.updated_at = datetime.now(timezone.utc)
        self._validate()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the memory."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the memory."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def link_to(self, memory_id: MemoryId) -> None:
        """Create a link to another memory."""
        if memory_id not in self.linked_memories and memory_id != self.id:
            self.linked_memories.append(memory_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def unlink_from(self, memory_id: MemoryId) -> None:
        """Remove a link to another memory."""
        if memory_id in self.linked_memories:
            self.linked_memories.remove(memory_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def record_access(self) -> None:
        """Record that the memory was accessed."""
        self.accessed_at = datetime.now(timezone.utc)
        self.retrieval_count += 1
    
    def archive(self) -> None:
        """Archive the memory."""
        self.status = MemoryStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)
    
    def unarchive(self) -> None:
        """Unarchive the memory."""
        self.status = MemoryStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete the memory."""
        self.status = MemoryStatus.DELETED
        self.updated_at = datetime.now(timezone.utc)
    
    def update_importance(self, score: float) -> None:
        """Update importance score."""
        if not 0 <= score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
        self.importance_score = score
        self.updated_at = datetime.now(timezone.utc)
    
    def decay_retention(self, decay_factor: float = 0.99) -> None:
        """Apply retention decay."""
        self.retention_strength *= decay_factor
        if self.retention_strength < 0.01:
            self.retention_strength = 0.01  # Minimum retention
    
    def boost_retention(self, boost_factor: float = 1.1) -> None:
        """Boost retention strength (e.g., after retrieval)."""
        self.retention_strength = min(1.0, self.retention_strength * boost_factor)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "status": self.status.value,
            "importance_score": self.importance_score,
            "confidence_score": self.confidence_score,
            "tags": self.tags,
            "linked_memories": [str(m) for m in self.linked_memories],
            "source_url": self.source_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "retention_strength": self.retention_strength,
            "retrieval_count": self.retrieval_count,
        }