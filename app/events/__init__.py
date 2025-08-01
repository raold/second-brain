from app.events.domain_events import SearchPerformedEvent, SystemHealthEvent

"""
Event-driven architecture components for the Second Brain application.

This module provides domain events, event bus, and event handlers
to enable loose coupling and cross-cutting concerns handling.
"""

from .domain_events import (
    DomainEvent,
    ImportanceUpdatedEvent,
    MemoryAccessedEvent,
    MemoryCreatedEvent,
    MemoryUpdatedEvent,
    SearchPerformedEvent,
    SessionCreatedEvent,
    SessionExpiredEvent,
    SystemHealthEvent,
)
from .event_bus import EventBus, EventHandler
from .event_handlers import (
    ImportanceTrackingHandler,
    NotificationHandler,
    SearchAnalyticsHandler,
    SystemMonitoringHandler,
)

__all__ = [
    # Domain Events
    "DomainEvent",
    "MemoryCreatedEvent",
    "MemoryUpdatedEvent",
    "MemoryAccessedEvent",
    "ImportanceUpdatedEvent",
    "SessionCreatedEvent",
    "SessionExpiredEvent",
    "SearchPerformedEvent",
    "SystemHealthEvent",
    # Event Infrastructure
    "EventBus",
    "EventHandler",
    # Event Handlers
    "ImportanceTrackingHandler",
    "SearchAnalyticsHandler",
    "SystemMonitoringHandler",
    "NotificationHandler",
]
