"""
Session-related domain events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from src.domain.events.base import DomainEvent


@dataclass(frozen=True)
class SessionCreated(DomainEvent):
    """Event raised when a session is created."""
    
    user_id: UUID
    title: str
    description: Optional[str]
    
    @property
    def event_type(self) -> str:
        return "session.created"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class SessionClosed(DomainEvent):
    """Event raised when a session is closed."""
    
    message_count: int
    duration_seconds: int
    
    @property
    def event_type(self) -> str:
        return "session.closed"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "message_count": self.message_count,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class MessageAdded(DomainEvent):
    """Event raised when a message is added to a session."""
    
    role: str  # "user" or "assistant"
    content: str
    message_index: int
    
    @property
    def event_type(self) -> str:
        return "session.message_added"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "role": self.role,
            "content": self.content,
            "message_index": self.message_index,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class SessionUpdated(DomainEvent):
    """Event raised when session metadata is updated."""
    
    changes: dict[str, Any]
    
    @property
    def event_type(self) -> str:
        return "session.updated"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "changes": self.changes,
            "metadata": self.metadata.to_dict(),
        }