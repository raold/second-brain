"""
Background workers for async event processing.

Provides worker services that consume events from message queue.
"""

from .event_worker import EventWorker

__all__ = ["EventWorker"]