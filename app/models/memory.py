"""
Memory models for Second Brain
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """User model"""
    id: str
    email: str
    username: str


class MemoryType(str, Enum):
    """Memory type enumeration"""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class Memory(BaseModel):
    """Memory model for Second Brain"""

    id: Optional[str] = None
    content: str
    memory_type: MemoryType = MemoryType.FACTUAL
    importance_score: float = 0.5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    embedding: Optional[list[float]] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def create(cls, content: str, memory_type: MemoryType, user_id: Optional[str] = None) -> 'Memory':
        """Create a new memory with default values."""
        from uuid import uuid4
        now = datetime.utcnow()
        return cls(
            id=str(uuid4()),
            content=content,
            memory_type=memory_type,
            created_at=now,
            updated_at=now,
            user_id=user_id
        )


class SearchCriteria(BaseModel):
    """Search criteria for memory queries"""
    query: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    user_id: Optional[str] = None
    min_importance: Optional[float] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = 50
    offset: Optional[int] = None


class MemoryMetrics(BaseModel):
    """Memory metrics and statistics"""
    total_memories: int
    memories_by_type: dict[str, int]
    average_importance: float
    recent_memories: int
    total_access_count: int
    last_updated: datetime
