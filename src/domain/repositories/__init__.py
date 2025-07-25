"""
Repository interfaces (abstractions).

These are the contracts that the infrastructure layer must implement.
The domain layer depends on these abstractions, not concrete implementations.
"""

from .memory_repository import MemoryRepository
from .user_repository import UserRepository
from .session_repository import SessionRepository
from .tag_repository import TagRepository
from .event_store import EventStore

__all__ = [
    "MemoryRepository",
    "UserRepository", 
    "SessionRepository",
    "TagRepository",
    "EventStore",
]