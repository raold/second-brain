"""Domain events for the application"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base domain event"""

    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = {}


class MemoryEvent(DomainEvent):
    """Base memory event"""

    memory_id: str
    user_id: str | None = None


class MemoryCreatedEvent(MemoryEvent):
    """Event when memory is created"""

    event_type: str = "memory.created"


class MemoryUpdatedEvent(MemoryEvent):
    """Event when memory is updated"""

    event_type: str = "memory.updated"
    changes: dict[str, Any] = {}


class MemoryDeletedEvent(MemoryEvent):
    """Event when memory is deleted"""

    event_type: str = "memory.deleted"


class MemoryConsolidatedEvent(DomainEvent):
    """Event when memories are consolidated"""

    event_type: str = "memory.consolidated"
    memory_ids: list[str] = []
    result_id: str | None = None


class ConsolidationEvent(DomainEvent):
    """General consolidation event"""

    event_type: str = "consolidation"
    consolidation_id: str
    status: str = "started"
    details: dict[str, Any] = {}


class SystemHealthEvent(DomainEvent):
    """System health event"""

    event_type: str = "system.health"
    status: str = "healthy"
    metrics: dict[str, Any] = {}
