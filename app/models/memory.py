"""
Memory models for Second Brain
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


class MemoryType(str, Enum):
    """Memory type enumeration"""

    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class Memory(BaseModel):
    """Memory model for Second Brain"""

    id: str | None = None
    content: str
    memory_type: MemoryType = MemoryType.FACTUAL
    importance_score: float = 0.5
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    embedding: list[float] | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def create(cls, content: str, memory_type: MemoryType) -> "Memory":
        """Create a new memory with default values."""

        now = datetime.utcnow()
        return cls(
            id=str(uuid4()),
            content=content,
            memory_type=memory_type,
            created_at=now,
            updated_at=now,
        )


class MemoryMetrics(BaseModel):
    """Memory metrics and statistics"""

    total_memories: int
    memories_by_type: dict[str, int]
    average_importance: float
    recent_memories: int
    total_access_count: int
    last_updated: datetime
