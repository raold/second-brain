"""
Event publisher for domain events.

Publishes domain events to message queue for async processing.
"""

from typing import Optional

from src.domain.events.base import DomainEvent
from src.infrastructure.logging import get_logger
from src.infrastructure.messaging.broker import MessageBroker

logger = get_logger(__name__)


class EventPublisher:
    """Publishes domain events to message queue."""
    
    def __init__(self, broker: MessageBroker):
        """
        Initialize event publisher.
        
        Args:
            broker: Message broker instance
        """
        self.broker = broker
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.
        
        Args:
            event: Domain event to publish
        """
        # Convert event to message
        message = {
            "event_id": str(event.metadata.event_id),
            "event_type": event.__class__.__name__,
            "aggregate_id": str(event.aggregate_id),
            "occurred_at": event.metadata.occurred_at.isoformat(),
            "version": event.metadata.version,
            "user_id": str(event.metadata.user_id) if event.metadata.user_id else None,
            "correlation_id": str(event.metadata.correlation_id) if event.metadata.correlation_id else None,
            "causation_id": str(event.metadata.causation_id) if event.metadata.causation_id else None,
            "payload": event.to_dict(),
        }
        
        # Determine routing key
        routing_key = f"events.{event.__class__.__module__.split('.')[-1]}.{event.__class__.__name__}"
        
        try:
            await self.broker.publish(routing_key, message)
            logger.info(f"Published event {event.__class__.__name__} with ID {event.metadata.event_id}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Don't raise - we don't want to fail the main operation
    
    async def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple events.
        
        Args:
            events: List of domain events
        """
        for event in events:
            await self.publish(event)