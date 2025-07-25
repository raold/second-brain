"""
Event store interface for event sourcing.

Defines the contract for persisting domain events.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Type, TypeVar
from uuid import UUID

from src.domain.events.base import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class EventStore(ABC):
    """Abstract event store for persisting domain events."""
    
    @abstractmethod
    async def append(self, event: DomainEvent) -> None:
        """
        Append an event to the store.
        
        Args:
            event: The domain event to store
        """
        pass
    
    @abstractmethod
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
    ) -> list[DomainEvent]:
        """
        Get events for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            from_version: Start from this version (inclusive)
            to_version: End at this version (inclusive)
            
        Returns:
            List of events in order
        """
        pass
    
    @abstractmethod
    async def get_events_by_type(
        self,
        event_type: Type[T],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[T]:
        """
        Get events of a specific type.
        
        Args:
            event_type: The event class
            since: Events after this time
            until: Events before this time
            limit: Maximum number of events
            
        Returns:
            List of events of the specified type
        """
        pass
    
    @abstractmethod
    async def get_events_by_correlation_id(
        self,
        correlation_id: UUID,
    ) -> list[DomainEvent]:
        """
        Get all events with a correlation ID.
        
        Args:
            correlation_id: The correlation ID
            
        Returns:
            List of correlated events
        """
        pass
    
    @abstractmethod
    async def get_last_event(
        self,
        aggregate_id: UUID,
    ) -> Optional[DomainEvent]:
        """
        Get the last event for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            
        Returns:
            The last event or None
        """
        pass
    
    @abstractmethod
    async def get_snapshot(
        self,
        aggregate_id: UUID,
        max_version: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get the latest snapshot for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            max_version: Maximum version to consider
            
        Returns:
            Snapshot data or None
        """
        pass
    
    @abstractmethod
    async def save_snapshot(
        self,
        aggregate_id: UUID,
        version: int,
        data: dict,
    ) -> None:
        """
        Save a snapshot for an aggregate.
        
        Args:
            aggregate_id: The aggregate ID
            version: The version number
            data: Snapshot data
        """
        pass
    
    @abstractmethod
    async def get_stream_version(self, aggregate_id: UUID) -> int:
        """
        Get the current version of an event stream.
        
        Args:
            aggregate_id: The aggregate ID
            
        Returns:
            The current version number (0 if no events)
        """
        pass