"""
Session Domain Model

Represents a conversation session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SessionId:
    """Value object for Session ID."""
    
    value: UUID
    
    @classmethod
    def generate(cls) -> SessionId:
        """Generate a new session ID."""
        return cls(value=uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> SessionId:
        """Create from string representation."""
        return cls(value=UUID(value))
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)


@dataclass
class Message:
    """A message within a session."""
    
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """
    Conversation session entity.
    
    Represents a conversation between a user and the system.
    """
    
    # Identity
    id: SessionId
    user_id: UUID
    
    # Content
    title: str
    description: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    
    # State
    is_active: bool = True
    context: dict[str, Any] = field(default_factory=dict)
    
    # Related data
    memory_ids: list[UUID] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self) -> None:
        """Validate session after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate session state."""
        if not self.title:
            raise ValueError("Session title cannot be empty")
    
    def add_message(self, role: str, content: str, metadata: Optional[dict[str, Any]] = None) -> Message:
        """Add a message to the session."""
        if role not in ["user", "assistant"]:
            raise ValueError("Role must be 'user' or 'assistant'")
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        return message
    
    def add_user_message(self, content: str, metadata: Optional[dict[str, Any]] = None) -> Message:
        """Add a user message."""
        return self.add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[dict[str, Any]] = None) -> Message:
        """Add an assistant message."""
        return self.add_message("assistant", content, metadata)
    
    def update_title(self, title: str) -> None:
        """Update session title."""
        if not title:
            raise ValueError("Title cannot be empty")
        self.title = title
        self.updated_at = datetime.now(timezone.utc)
    
    def update_description(self, description: str) -> None:
        """Update session description."""
        self.description = description
        self.updated_at = datetime.now(timezone.utc)
    
    def add_memory_reference(self, memory_id: UUID) -> None:
        """Add a reference to a memory."""
        if memory_id not in self.memory_ids:
            self.memory_ids.append(memory_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_memory_reference(self, memory_id: UUID) -> None:
        """Remove a memory reference."""
        if memory_id in self.memory_ids:
            self.memory_ids.remove(memory_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the session."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the session."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def update_context(self, key: str, value: Any) -> None:
        """Update session context."""
        self.context[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.context.get(key, default)
    
    def clear_context(self) -> None:
        """Clear session context."""
        self.context.clear()
        self.updated_at = datetime.now(timezone.utc)
    
    def close(self) -> None:
        """Close the session."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def reopen(self) -> None:
        """Reopen a closed session."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)
    
    def get_user_message_count(self) -> int:
        """Get user message count."""
        return sum(1 for msg in self.messages if msg.role == "user")
    
    def get_assistant_message_count(self) -> int:
        """Get assistant message count."""
        return sum(1 for msg in self.messages if msg.role == "assistant")
    
    def get_last_message(self) -> Optional[Message]:
        """Get the last message."""
        return self.messages[-1] if self.messages else None
    
    def get_messages_since(self, since: datetime) -> list[Message]:
        """Get messages since a specific time."""
        return [msg for msg in self.messages if msg.timestamp > since]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in self.messages
            ],
            "is_active": self.is_active,
            "context": self.context,
            "memory_ids": [str(mid) for mid in self.memory_ids],
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "message_count": self.get_message_count(),
        }