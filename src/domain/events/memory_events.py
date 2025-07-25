"""
Memory-related domain events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from src.domain.events.base import DomainEvent
from src.domain.models.memory import MemoryType, MemoryStatus


@dataclass(frozen=True)
class MemoryCreated(DomainEvent):
    """Event raised when a memory is created."""
    
    title: str
    content: str
    memory_type: MemoryType
    user_id: UUID
    tags: list[str]
    importance_score: float
    
    @property
    def event_type(self) -> str:
        return "memory.created"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "title": self.title,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "user_id": str(self.user_id),
            "tags": self.tags,
            "importance_score": self.importance_score,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryUpdated(DomainEvent):
    """Event raised when a memory is updated."""
    
    title: str
    content: str
    old_title: str
    old_content: str
    
    @property
    def event_type(self) -> str:
        return "memory.updated"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "title": self.title,
            "content": self.content,
            "old_title": self.old_title,
            "old_content": self.old_content,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryDeleted(DomainEvent):
    """Event raised when a memory is deleted."""
    
    deletion_type: str  # "soft" or "hard"
    reason: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "memory.deleted"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "deletion_type": self.deletion_type,
            "reason": self.reason,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryAccessed(DomainEvent):
    """Event raised when a memory is accessed."""
    
    access_type: str  # "view", "search", "link", etc.
    retrieval_count: int
    
    @property
    def event_type(self) -> str:
        return "memory.accessed"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "access_type": self.access_type,
            "retrieval_count": self.retrieval_count,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryLinked(DomainEvent):
    """Event raised when a memory is linked to another."""
    
    linked_memory_id: UUID
    link_type: str  # "related", "prerequisite", "followup", etc.
    
    @property
    def event_type(self) -> str:
        return "memory.linked"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "linked_memory_id": str(self.linked_memory_id),
            "link_type": self.link_type,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryUnlinked(DomainEvent):
    """Event raised when a memory link is removed."""
    
    unlinked_memory_id: UUID
    
    @property
    def event_type(self) -> str:
        return "memory.unlinked"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "unlinked_memory_id": str(self.unlinked_memory_id),
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryTagged(DomainEvent):
    """Event raised when a tag is added to a memory."""
    
    tag: str
    
    @property
    def event_type(self) -> str:
        return "memory.tagged"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "tag": self.tag,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MemoryUntagged(DomainEvent):
    """Event raised when a tag is removed from a memory."""
    
    tag: str
    
    @property
    def event_type(self) -> str:
        return "memory.untagged"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "tag": self.tag,
            "metadata": self.metadata.to_dict(),
        }