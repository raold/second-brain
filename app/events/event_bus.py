"""
Event bus implementation for handling domain events.

Provides a centralized event dispatching mechanism following
the Observer pattern for loose coupling between components.
"""

import asyncio
from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class EventHandler(ABC):
    """
    Abstract base class for event handlers.

    Event handlers process domain events and can perform
    side effects like updating read models, sending notifications,
    or triggering other business processes.
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a domain event.

        Args:
            event: The domain event to handle
        """
        pass

    @property
    def handler_name(self) -> str:
        """Return the handler name for logging."""
        return self.__class__.__name__

    async def can_handle(self, event: DomainEvent) -> bool:
        """
        Check if this handler can process the given event.
        Override this method for conditional handling.

        Args:
            event: The domain event to check

        Returns:
            True if handler can process the event
        """
        return True


class EventBus:
    """
    Event bus for publishing and subscribing to domain events.

    Implements the Observer pattern to enable loose coupling
    between event publishers and subscribers.
    """

    def __init__(self, max_retry_attempts: int = 3):
        """
        Initialize the event bus.

        Args:
            max_retry_attempts: Maximum number of retry attempts for failed handlers
        """
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._middleware: list[Callable[[DomainEvent], DomainEvent]] = []
        self._max_retry_attempts = max_retry_attempts
        self._event_stats: dict[str, int] = defaultdict(int)
        self._handler_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to subscribe to
            handler: The event handler
        """
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed {handler.handler_name} to {event_type.__name__}")

    def subscribe_to_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to all events.

        Args:
            handler: The event handler
        """
        self._global_handlers.append(handler)
        logger.info(f"Subscribed {handler.handler_name} to all events")

    def unsubscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The event handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.info(f"Unsubscribed {handler.handler_name} from {event_type.__name__}")

    def add_middleware(self, middleware: Callable[[DomainEvent], DomainEvent]) -> None:
        """
        Add middleware that processes events before handlers.

        Args:
            middleware: Function that takes and returns a domain event
        """
        self._middleware.append(middleware)

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a single event to all relevant handlers.

        Args:
            event: The domain event to publish
        """
        await self.publish_batch([event])

    async def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple events in a batch.

        Args:
            events: List of domain events to publish
        """
        if not events:
            return

        # Apply middleware to each event
        processed_events = []
        for event in events:
            processed_event = event
            for middleware in self._middleware:
                try:
                    processed_event = middleware(processed_event)
                except Exception as e:
                    logger.error(f"Middleware failed for event {event.event_type}: {e}")
                    # Continue with original event if middleware fails
                    processed_event = event
                    break
            processed_events.append(processed_event)

        # Group events by type for efficient processing
        events_by_type = defaultdict(list)
        for event in processed_events:
            events_by_type[type(event)].append(event)

        # Process events by type
        tasks = []
        for event_type, type_events in events_by_type.items():
            # Get specific handlers for this event type
            specific_handlers = self._handlers.get(event_type, [])

            # Process each event with its handlers
            for event in type_events:
                # Update stats
                self._event_stats[event.event_type] += 1

                # Collect all handlers (specific + global)
                all_handlers = []

                # Add specific handlers
                for handler in specific_handlers:
                    if await handler.can_handle(event):
                        all_handlers.append(handler)

                # Add global handlers
                for handler in self._global_handlers:
                    if await handler.can_handle(event):
                        all_handlers.append(handler)

                # Create tasks for concurrent execution
                for handler in all_handlers:
                    task = self._handle_event_with_retry(event, handler)
                    tasks.append(task)

        # Execute all handlers concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Event handler failed: {result}")

    async def _handle_event_with_retry(
        self,
        event: DomainEvent,
        handler: EventHandler
    ) -> None:
        """
        Handle an event with retry logic.

        Args:
            event: The domain event
            handler: The event handler
        """
        last_exception = None

        for attempt in range(self._max_retry_attempts + 1):
            try:
                start_time = datetime.utcnow()
                await handler.handle(event)
                end_time = datetime.utcnow()

                # Update success stats
                self._handler_stats[handler.handler_name]['success'] += 1

                # Log performance if slow
                duration_ms = (end_time - start_time).total_seconds() * 1000
                if duration_ms > 1000:  # Log if > 1 second
                    logger.warning(
                        f"Slow event handler: {handler.handler_name} took {duration_ms:.1f}ms "
                        f"for {event.event_type}"
                    )

                return  # Success, no retry needed

            except Exception as e:
                last_exception = e
                self._handler_stats[handler.handler_name]['error'] += 1

                if attempt < self._max_retry_attempts:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Handler {handler.handler_name} failed for {event.event_type}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self._max_retry_attempts})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Final failure
                    logger.error(
                        f"Handler {handler.handler_name} failed permanently for {event.event_type}: {e}",
                        extra={
                            'event_id': event.event_id,
                            'event_type': event.event_type,
                            'handler': handler.handler_name,
                            'attempts': self._max_retry_attempts + 1,
                            'stack_trace': traceback.format_exc()
                        }
                    )

        # If we get here, all retries failed
        self._handler_stats[handler.handler_name]['permanent_failure'] += 1

    def get_subscribers(self, event_type: type[DomainEvent]) -> list[EventHandler]:
        """
        Get all handlers subscribed to an event type.

        Args:
            event_type: The event type

        Returns:
            List of subscribed handlers
        """
        return self._handlers.get(event_type, []).copy()

    def get_stats(self) -> dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary containing event and handler statistics
        """
        return {
            'event_stats': dict(self._event_stats),
            'handler_stats': dict(self._handler_stats),
            'total_events_published': sum(self._event_stats.values()),
            'total_handlers': len(self._global_handlers) + sum(len(handlers) for handlers in self._handlers.values()),
            'event_types_count': len(self._handlers),
            'global_handlers_count': len(self._global_handlers)
        }

    def clear_stats(self) -> None:
        """Clear all statistics."""
        self._event_stats.clear()
        self._handler_stats.clear()

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the event bus.

        Returns:
            Health status information
        """
        stats = self.get_stats()

        # Calculate error rates
        total_successes = sum(
            handler_stats.get('success', 0)
            for handler_stats in self._handler_stats.values()
        )
        total_errors = sum(
            handler_stats.get('error', 0) + handler_stats.get('permanent_failure', 0)
            for handler_stats in self._handler_stats.values()
        )

        total_handled = total_successes + total_errors
        error_rate = (total_errors / total_handled) if total_handled > 0 else 0

        health_status = 'healthy'
        if error_rate > 0.1:  # > 10% error rate
            health_status = 'unhealthy'
        elif error_rate > 0.05:  # > 5% error rate
            health_status = 'degraded'

        return {
            'status': health_status,
            'error_rate': error_rate,
            'total_events_handled': total_handled,
            'total_successes': total_successes,
            'total_errors': total_errors,
            'handlers_registered': stats['total_handlers'],
            'event_types_registered': stats['event_types_count']
        }


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.

    Returns:
        The global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """
    Set the global event bus instance.

    Args:
        event_bus: The EventBus instance to use globally
    """
    global _event_bus
    _event_bus = event_bus


# Utility decorators and functions

def event_handler(event_type: type[DomainEvent]):
    """
    Decorator to automatically register event handlers.

    Args:
        event_type: The event type to handle
    """
    def decorator(handler_class):
        # Register the handler when the class is created
        if hasattr(handler_class, '_auto_register') and handler_class._auto_register:
            bus = get_event_bus()
            handler = handler_class()
            bus.subscribe(event_type, handler)
        return handler_class
    return decorator


async def publish_event(event: DomainEvent) -> None:
    """
    Convenience function to publish an event using the global bus.

    Args:
        event: The domain event to publish
    """
    bus = get_event_bus()
    await bus.publish(event)
