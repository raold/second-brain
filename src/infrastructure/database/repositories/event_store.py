"""
Concrete event store implementation using SQLAlchemy.

Implements the EventStore interface with PostgreSQL.
"""

import json
from datetime import datetime
from typing import Optional, Type, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.events.base import DomainEvent, EventMetadata
from src.domain.repositories.event_store import EventStore
from src.infrastructure.database.models import EventModel, SnapshotModel
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=DomainEvent)


class SQLEventStore(EventStore):
    """SQL implementation of event store."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize event store with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def append(self, event: DomainEvent) -> None:
        """Append an event to the store."""
        # Get current stream version
        stream_version = await self.get_stream_version(event.aggregate_id)
        next_version = stream_version + 1
        
        # Create event record
        db_event = EventModel(
            id=event.metadata.event_id,
            aggregate_id=event.aggregate_id,
            event_type=event.__class__.__name__,
            event_version=event.metadata.version,
            event_data=self._serialize_event(event),
            user_id=event.metadata.user_id,
            correlation_id=event.metadata.correlation_id,
            causation_id=event.metadata.causation_id,
            created_at=event.metadata.occurred_at,
            stream_version=next_version,
        )
        
        self.session.add(db_event)
        
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            raise
    
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
    ) -> list[DomainEvent]:
        """Get events for an aggregate."""
        query = self.session.query(EventModel).filter(
            EventModel.aggregate_id == aggregate_id
        )
        
        if from_version is not None:
            query = query.filter(EventModel.stream_version >= from_version)
        
        if to_version is not None:
            query = query.filter(EventModel.stream_version <= to_version)
        
        query = query.order_by(EventModel.stream_version)
        
        results = await self.session.execute(query)
        
        events = []
        for row in results.scalars():
            event = self._deserialize_event(row)
            if event:
                events.append(event)
        
        return events
    
    async def get_events_by_type(
        self,
        event_type: Type[T],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[T]:
        """Get events of a specific type."""
        query = self.session.query(EventModel).filter(
            EventModel.event_type == event_type.__name__
        )
        
        if since:
            query = query.filter(EventModel.created_at >= since)
        
        if until:
            query = query.filter(EventModel.created_at <= until)
        
        query = query.order_by(EventModel.created_at.desc()).limit(limit)
        
        results = await self.session.execute(query)
        
        events = []
        for row in results.scalars():
            event = self._deserialize_event(row)
            if event and isinstance(event, event_type):
                events.append(event)
        
        return events
    
    async def get_events_by_correlation_id(
        self,
        correlation_id: UUID,
    ) -> list[DomainEvent]:
        """Get all events with a correlation ID."""
        results = await self.session.execute(
            self.session.query(EventModel).filter(
                EventModel.correlation_id == correlation_id
            ).order_by(EventModel.created_at)
        )
        
        events = []
        for row in results.scalars():
            event = self._deserialize_event(row)
            if event:
                events.append(event)
        
        return events
    
    async def get_last_event(
        self,
        aggregate_id: UUID,
    ) -> Optional[DomainEvent]:
        """Get the last event for an aggregate."""
        result = await self.session.execute(
            self.session.query(EventModel).filter(
                EventModel.aggregate_id == aggregate_id
            ).order_by(EventModel.stream_version.desc()).limit(1)
        )
        
        row = result.scalar_one_or_none()
        if not row:
            return None
        
        return self._deserialize_event(row)
    
    async def get_snapshot(
        self,
        aggregate_id: UUID,
        max_version: Optional[int] = None,
    ) -> Optional[dict]:
        """Get the latest snapshot for an aggregate."""
        query = self.session.query(SnapshotModel).filter(
            SnapshotModel.aggregate_id == aggregate_id
        )
        
        if max_version is not None:
            query = query.filter(SnapshotModel.version <= max_version)
        
        query = query.order_by(SnapshotModel.version.desc()).limit(1)
        
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        
        if not row:
            return None
        
        return row.data
    
    async def save_snapshot(
        self,
        aggregate_id: UUID,
        version: int,
        data: dict,
    ) -> None:
        """Save a snapshot for an aggregate."""
        snapshot = SnapshotModel(
            id=uuid4(),
            aggregate_id=aggregate_id,
            version=version,
            data=data,
            created_at=datetime.utcnow(),
        )
        
        self.session.add(snapshot)
        await self.session.flush()
    
    async def get_stream_version(self, aggregate_id: UUID) -> int:
        """Get the current version of an event stream."""
        result = await self.session.execute(
            func.max(EventModel.stream_version).filter(
                EventModel.aggregate_id == aggregate_id
            )
        )
        
        version = result.scalar()
        return version if version is not None else 0
    
    def _serialize_event(self, event: DomainEvent) -> dict:
        """Serialize an event to JSON-compatible dict."""
        data = {
            "aggregate_id": str(event.aggregate_id),
            "metadata": {
                "event_id": str(event.metadata.event_id),
                "occurred_at": event.metadata.occurred_at.isoformat(),
                "version": event.metadata.version,
                "user_id": str(event.metadata.user_id) if event.metadata.user_id else None,
                "correlation_id": str(event.metadata.correlation_id) if event.metadata.correlation_id else None,
                "causation_id": str(event.metadata.causation_id) if event.metadata.causation_id else None,
            }
        }
        
        # Add event-specific data
        for key, value in event.__dict__.items():
            if key not in ["aggregate_id", "metadata"]:
                if isinstance(value, UUID):
                    data[key] = str(value)
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif hasattr(value, "value"):  # Value objects
                    data[key] = value.value
                else:
                    data[key] = value
        
        return data
    
    def _deserialize_event(self, db_event: EventModel) -> Optional[DomainEvent]:
        """Deserialize an event from database."""
        try:
            # Import event classes dynamically
            from src.domain.events import memory_events, session_events, user_events
            
            # Map event type names to classes
            event_classes = {
                # Memory events
                "MemoryCreated": memory_events.MemoryCreated,
                "MemoryUpdated": memory_events.MemoryUpdated,
                "MemoryDeleted": memory_events.MemoryDeleted,
                "MemoryAccessed": memory_events.MemoryAccessed,
                "MemoryLinked": memory_events.MemoryLinked,
                "MemoryUnlinked": memory_events.MemoryUnlinked,
                "MemoryTagged": memory_events.MemoryTagged,
                "MemoryUntagged": memory_events.MemoryUntagged,
                
                # Session events
                "SessionCreated": session_events.SessionCreated,
                "SessionUpdated": session_events.SessionUpdated,
                "SessionClosed": session_events.SessionClosed,
                "SessionMessageAdded": session_events.SessionMessageAdded,
                "SessionMemoryAdded": session_events.SessionMemoryAdded,
                "SessionMemoryRemoved": session_events.SessionMemoryRemoved,
                
                # User events
                "UserRegistered": user_events.UserRegistered,
                "UserUpdated": user_events.UserUpdated,
                "UserDeleted": user_events.UserDeleted,
                "UserLoggedIn": user_events.UserLoggedIn,
                "UserLoggedOut": user_events.UserLoggedOut,
                "UserVerified": user_events.UserVerified,
                "UserPasswordChanged": user_events.UserPasswordChanged,
            }
            
            event_class = event_classes.get(db_event.event_type)
            if not event_class:
                logger.warning(f"Unknown event type: {db_event.event_type}")
                return None
            
            # Reconstruct metadata
            metadata_data = db_event.event_data.get("metadata", {})
            metadata = EventMetadata(
                event_id=UUID(metadata_data["event_id"]),
                occurred_at=datetime.fromisoformat(metadata_data["occurred_at"]),
                version=metadata_data["version"],
                user_id=UUID(metadata_data["user_id"]) if metadata_data.get("user_id") else None,
                correlation_id=UUID(metadata_data["correlation_id"]) if metadata_data.get("correlation_id") else None,
                causation_id=UUID(metadata_data["causation_id"]) if metadata_data.get("causation_id") else None,
            )
            
            # Create event instance
            event_data = {
                k: v for k, v in db_event.event_data.items()
                if k not in ["metadata", "aggregate_id"]
            }
            
            event = event_class(
                aggregate_id=db_event.aggregate_id,
                metadata=metadata,
                **event_data
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to deserialize event: {e}")
            return None