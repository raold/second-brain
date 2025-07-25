"""Domain events for Second Brain."""

from .base import DomainEvent, EventMetadata
from .memory_events import (
    MemoryCreated,
    MemoryUpdated,
    MemoryDeleted,
    MemoryAccessed,
    MemoryLinked,
    MemoryUnlinked,
    MemoryTagged,
    MemoryUntagged,
)
from .user_events import (
    UserCreated,
    UserUpdated,
    UserDeleted,
    UserLoggedIn,
    UserPromoted,
    UserVerified,
)
from .session_events import (
    SessionCreated,
    SessionClosed,
    MessageAdded,
    SessionUpdated,
)

__all__ = [
    # Base
    "DomainEvent",
    "EventMetadata",
    # Memory events
    "MemoryCreated",
    "MemoryUpdated",
    "MemoryDeleted",
    "MemoryAccessed",
    "MemoryLinked",
    "MemoryUnlinked",
    "MemoryTagged",
    "MemoryUntagged",
    # User events
    "UserCreated",
    "UserUpdated",
    "UserDeleted",
    "UserLoggedIn",
    "UserPromoted",
    "UserVerified",
    # Session events
    "SessionCreated",
    "SessionClosed",
    "MessageAdded",
    "SessionUpdated",
]