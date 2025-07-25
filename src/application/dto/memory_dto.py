"""
Memory-related Data Transfer Objects.

DTOs for memory operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.models.memory import MemoryStatus, MemoryType


@dataclass
class CreateMemoryDTO:
    """DTO for creating a new memory."""
    
    title: str
    content: str
    memory_type: MemoryType
    importance_score: float = 0.5
    confidence_score: float = 1.0
    source_url: Optional[str] = None
    tags: list[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        """Validate and set defaults."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        
        # Validate scores
        if not 0 <= self.importance_score <= 1:
            raise ValueError("importance_score must be between 0 and 1")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1")


@dataclass
class UpdateMemoryDTO:
    """DTO for updating an existing memory."""
    
    title: Optional[str] = None
    content: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    status: Optional[MemoryStatus] = None
    importance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    source_url: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """Validate fields."""
        if self.importance_score is not None and not 0 <= self.importance_score <= 1:
            raise ValueError("importance_score must be between 0 and 1")
        if self.confidence_score is not None and not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1")


@dataclass
class MemoryDTO:
    """DTO for memory data."""
    
    id: UUID
    user_id: UUID
    title: str
    content: str
    memory_type: MemoryType
    status: MemoryStatus
    importance_score: float
    confidence_score: float
    source_url: Optional[str]
    tags: list[str]
    linked_memory_ids: list[UUID]
    metadata: dict
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    retention_strength: float
    retrieval_count: int
    
    @classmethod
    def from_domain(cls, memory):
        """Create DTO from domain model."""
        return cls(
            id=memory.id.value,
            user_id=memory.user_id,
            title=memory.title,
            content=memory.content,
            memory_type=memory.memory_type,
            status=memory.status,
            importance_score=memory.importance_score,
            confidence_score=memory.confidence_score,
            source_url=memory.source_url,
            tags=[str(tag_id) for tag_id in memory.tags],
            linked_memory_ids=[str(mem_id) for mem_id in memory.linked_memory_ids],
            metadata=memory.metadata,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            accessed_at=memory.accessed_at,
            retention_strength=memory.retention_strength,
            retrieval_count=memory.retrieval_count,
        )


@dataclass
class MemoryListDTO:
    """DTO for a list of memories."""
    
    memories: list[MemoryDTO]
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