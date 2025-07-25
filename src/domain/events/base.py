"""
Base domain event classes.

Domain events represent things that have happened in the system.
They are immutable and contain all information about what occurred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EventMetadata:
    """Metadata for domain events."""
    
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
        }


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events.
    
    Domain events are immutable records of things that have happened.
    They form the basis of our event-sourced architecture.
    """
    
    aggregate_id: UUID
    metadata: EventMetadata = field(default_factory=EventMetadata)
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type identifier."""
        pass
    
    @property
    @abstractmethod
    def event_version(self) -> int:
        """Get the event version for schema evolution."""
        pass
    
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        pass
    
    def with_metadata(self, **kwargs: Any) -> DomainEvent:
        """Create a new event with updated metadata."""
        # Since dataclasses are frozen, we need to create a new instance
        from dataclasses import replace
        
        new_metadata = EventMetadata(
            event_id=kwargs.get("event_id", self.metadata.event_id),
            timestamp=kwargs.get("timestamp", self.metadata.timestamp),
            user_id=kwargs.get("user_id", self.metadata.user_id),
            correlation_id=kwargs.get("correlation_id", self.metadata.correlation_id),
            causation_id=kwargs.get("causation_id", self.metadata.causation_id),
        )
        
        return replace(self, metadata=new_metadata)