"""
Event streaming system for real-time event processing
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar

from app.infrastructure.streaming.base import Stream, StreamItem, StreamMetadata, StreamProcessor

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Event')


class EventType(str, Enum):
    """Common event types in the system"""
    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_SEARCHED = "memory.searched"
    
    # Ingestion events
    INGESTION_STARTED = "ingestion.started"
    INGESTION_COMPLETED = "ingestion.completed"
    INGESTION_FAILED = "ingestion.failed"
    
    # Processing events
    PROCESSING_STARTED = "processing.started"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"
    
    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    
    # User events
    USER_ACTION = "user.action"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"


@dataclass
class Event:
    """Base event class"""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "system"
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_id=data.get("event_id"),
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "system"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class MemoryEvent(Event):
    """Memory-specific event"""
    memory_id: str = None
    memory_type: str = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        if self.memory_id:
            self.data["memory_id"] = self.memory_id
        if self.memory_type:
            self.data["memory_type"] = self.memory_type
        if self.user_id:
            self.data["user_id"] = self.user_id


@dataclass
class ProcessingEvent(Event):
    """Processing-specific event"""
    processor_name: str = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.processor_name:
            self.data["processor_name"] = self.processor_name
        if self.input_size is not None:
            self.data["input_size"] = self.input_size
        if self.output_size is not None:
            self.data["output_size"] = self.output_size
        if self.duration_ms is not None:
            self.data["duration_ms"] = self.duration_ms
        if self.error:
            self.data["error"] = self.error


class EventBus:
    """
    Central event bus for publishing and subscribing to events
    """
    
    def __init__(self, name: str = "event-bus", buffer_size: int = 10000):
        self.name = name
        self._stream = Stream[Event](name=name, buffer_size=buffer_size)
        self._subscribers: dict[EventType, list[Callable[[Event], Any]]] = {}
        self._type_subscribers: dict[Type[Event], list[Callable[[Event], Any]]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the event bus"""
        if self._running:
            return
            
        self._running = True
        await self._stream.start()
        self._task = asyncio.create_task(self._process_events())
        logger.info(f"Event bus {self.name} started")
        
    async def stop(self):
        """Stop the event bus"""
        self._running = False
        await self._stream.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logger.info(f"Event bus {self.name} stopped")
        
    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus
        
        Args:
            event: Event to publish
            
        Returns:
            bool: True if published successfully
        """
        metadata = StreamMetadata(
            source=event.source,
            headers={
                "event_type": event.event_type.value,
                "event_id": event.event_id
            }
        )
        
        return await self._stream.emit(event, metadata)
        
    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """
        Subscribe to specific event type
        
        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle events
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        
    def subscribe_type(self, event_class: Type[T], handler: Callable[[T], Any]):
        """
        Subscribe to specific event class
        
        Args:
            event_class: Class of event to subscribe to
            handler: Callback function to handle events
        """
        if event_class not in self._type_subscribers:
            self._type_subscribers[event_class] = []
        self._type_subscribers[event_class].append(handler)
        
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Any]):
        """Unsubscribe from event type"""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            
    async def _process_events(self):
        """Process events from the stream"""
        async for item in self._stream:
            event = item.data
            
            # Notify type-specific subscribers
            if event.event_type in self._subscribers:
                for handler in self._subscribers[event.event_type]:
                    try:
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
                        
            # Notify class-specific subscribers
            for event_class, handlers in self._type_subscribers.items():
                if isinstance(event, event_class):
                    for handler in handlers:
                        try:
                            result = handler(event)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}")
                            
    @property
    def metrics(self) -> dict[str, Any]:
        """Get event bus metrics"""
        return {
            "name": self.name,
            "running": self._running,
            "stream_metrics": self._stream.metrics,
            "subscriber_count": sum(len(handlers) for handlers in self._subscribers.values()),
            "type_subscriber_count": sum(len(handlers) for handlers in self._type_subscribers.values())
        }


class EventStore:
    """
    Store for persisting and querying events
    """
    
    def __init__(self, max_events: int = 100000):
        self.max_events = max_events
        self._events: list[Event] = []
        self._event_index: dict[str, Event] = {}
        self._type_index: dict[EventType, list[Event]] = {}
        
    async def store(self, event: Event):
        """Store an event"""
        # Add to list
        self._events.append(event)
        
        # Add to indexes
        self._event_index[event.event_id] = event
        
        if event.event_type not in self._type_index:
            self._type_index[event.event_type] = []
        self._type_index[event.event_type].append(event)
        
        # Trim if needed
        if len(self._events) > self.max_events:
            removed = self._events.pop(0)
            del self._event_index[removed.event_id]
            self._type_index[removed.event_type].remove(removed)
            
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self._event_index.get(event_id)
        
    async def get_events_by_type(
        self,
        event_type: EventType,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> list[Event]:
        """Get events by type"""
        events = self._type_index.get(event_type, [])
        
        if since:
            events = [e for e in events if e.timestamp >= since]
            
        return events[-limit:]
        
    async def get_recent_events(self, limit: int = 100) -> list[Event]:
        """Get recent events"""
        return self._events[-limit:]
        
    async def query_events(
        self,
        event_types: Optional[list[EventType]] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Event]:
        """Query events with filters"""
        events = self._events
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
            
        if source:
            events = [e for e in events if e.source == source]
            
        if since:
            events = [e for e in events if e.timestamp >= since]
            
        if until:
            events = [e for e in events if e.timestamp <= until]
            
        return events[-limit:]


class EventProcessor(StreamProcessor[Event, Event]):
    """Base class for event processors"""
    
    def __init__(self, name: str = None):
        super().__init__(name=name or "event-processor")
        
    @abstractmethod
    async def process_event(self, event: Event) -> Optional[Event]:
        """Process an event"""
        pass
        
    async def process(self, item: StreamItem[Event]) -> Optional[StreamItem[Event]]:
        """Process stream item containing event"""
        processed_event = await self.process_event(item.data)
        if processed_event:
            return StreamItem(data=processed_event, metadata=item.metadata)
        return None


class EventLogger(EventProcessor):
    """Log events to storage or external system"""
    
    def __init__(self, name: str = "event-logger", store: Optional[EventStore] = None):
        super().__init__(name=name)
        self.store = store or EventStore()
        
    async def process_event(self, event: Event) -> Optional[Event]:
        """Log event and pass through"""
        logger.info(f"Event: {event.event_type.value} - {event.event_id}")
        
        if self.store:
            await self.store.store(event)
            
        return event


class EventFilter(EventProcessor):
    """Filter events based on criteria"""
    
    def __init__(
        self,
        name: str = "event-filter",
        event_types: Optional[list[EventType]] = None,
        predicate: Optional[Callable[[Event], bool]] = None
    ):
        super().__init__(name=name)
        self.event_types = event_types
        self.predicate = predicate
        
    async def process_event(self, event: Event) -> Optional[Event]:
        """Filter events"""
        if self.event_types and event.event_type not in self.event_types:
            return None
            
        if self.predicate and not self.predicate(event):
            return None
            
        return event


class EventTransformer(EventProcessor):
    """Transform events"""
    
    def __init__(
        self,
        name: str = "event-transformer",
        transform: Callable[[Event], Event]
    ):
        super().__init__(name=name)
        self.transform = transform
        
    async def process_event(self, event: Event) -> Optional[Event]:
        """Transform event"""
        return self.transform(event)


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(name="global-event-bus")
    return _event_bus


async def publish_event(event: Event) -> bool:
    """Publish event to global bus"""
    bus = get_event_bus()
    if not bus._running:
        await bus.start()
    return await bus.publish(event)