"""
Message handlers for async event processing.

Provides base classes and implementations for handling events.
"""

from abc import ABC, abstractmethod
from typing import Any, Type

from src.domain.events.base import DomainEvent
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MessageHandler(ABC):
    """Base class for message handlers."""
    
    @abstractmethod
    async def handle(self, message: dict[str, Any]) -> None:
        """
        Handle a message.
        
        Args:
            message: Message payload
        """
        pass


class EventHandler(MessageHandler):
    """Base class for domain event handlers."""
    
    def __init__(self):
        """Initialize event handler."""
        self._handlers: dict[str, callable] = {}
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register event handlers - override in subclasses."""
        pass
    
    def handles(self, event_type: Type[DomainEvent]) -> callable:
        """
        Decorator to register an event handler.
        
        Args:
            event_type: Type of event to handle
            
        Returns:
            Decorator function
        """
        def decorator(func: callable) -> callable:
            self._handlers[event_type.__name__] = func
            return func
        return decorator
    
    async def handle(self, message: dict[str, Any]) -> None:
        """
        Handle an event message.
        
        Args:
            message: Event message
        """
        event_type = message.get("event_type")
        if not event_type:
            logger.error("Message missing event_type")
            return
        
        handler = self._handlers.get(event_type)
        if not handler:
            logger.warning(f"No handler for event type: {event_type}")
            return
        
        try:
            await handler(self, message)
            logger.info(f"Successfully handled {event_type} event")
        except Exception as e:
            logger.error(f"Error handling {event_type} event: {e}")
            raise


class LoggingEventHandler(EventHandler):
    """Simple event handler that logs all events."""
    
    def _register_handlers(self) -> None:
        """Register handlers for all event types."""
        # This handler logs all events
        pass
    
    async def handle(self, message: dict[str, Any]) -> None:
        """Log the event."""
        event_type = message.get("event_type", "Unknown")
        event_id = message.get("event_id", "Unknown")
        aggregate_id = message.get("aggregate_id", "Unknown")
        
        logger.info(
            f"Event received: {event_type}",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "occurred_at": message.get("occurred_at"),
            }
        )