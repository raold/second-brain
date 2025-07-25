"""
Session-related Data Transfer Objects.

DTOs for session operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateSessionDTO:
    """DTO for creating a new session."""
    
    title: str
    description: Optional[str] = None
    tags: list[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UpdateSessionDTO:
    """DTO for updating session information."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


@dataclass
class AddMessageDTO:
    """DTO for adding a message to a session."""
    
    role: str  # "user" or "assistant"
    content: str
    metadata: dict = None
    
    def __post_init__(self):
        """Validate fields."""
        if self.role not in ["user", "assistant"]:
            raise ValueError("Role must be 'user' or 'assistant'")
        if not self.content:
            raise ValueError("Content cannot be empty")
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SessionDTO:
    """DTO for session data."""
    
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    messages: list[dict]
    is_active: bool
    context: dict
    tags: list[str]
    memory_ids: list[UUID]
    metadata: dict
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    
    @classmethod
    def from_domain(cls, session):
        """Create DTO from domain model."""
        return cls(
            id=session.id.value,
            user_id=session.user_id,
            title=session.title,
            description=session.description,
            messages=session.messages,
            is_active=session.is_active,
            context=session.context,
            tags=session.tags,
            memory_ids=[mem_id.value for mem_id in session.memory_ids],
            metadata=session.metadata,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity_at=session.last_activity_at,
        )


@dataclass
class SessionListDTO:
    """DTO for a list of sessions."""
    
    sessions: list[SessionDTO]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1