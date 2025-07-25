"""
Base Observer pattern implementation.

Provides the foundation for observable objects and observers
with type-safe notifications and proper lifecycle management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from weakref import WeakSet

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ChangeType(Enum):
    """Types of changes that can be observed."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACCESSED = "accessed"
    STATE_CHANGED = "state_changed"
    BATCH_OPERATION = "batch_operation"


@dataclass
class ChangeNotification:
    """
    Notification about a change in an observable object.

    Contains all the information observers need to react to changes.
    """
    change_type: ChangeType
    entity_id: str
    entity_type: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    metadata: dict[str, Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class Observer(ABC):
    """
    Abstract observer interface.

    Observers implement this interface to receive notifications
    about changes in observable objects.
    """

    @abstractmethod
    async def on_change(self, notification: ChangeNotification) -> None:
        """
        Handle a change notification.

        Args:
            notification: Details about the change that occurred
        """
        pass

    @property
    def observer_id(self) -> str:
        """Unique identifier for this observer."""
        return f"{self.__class__.__name__}_{id(self)}"

    async def on_error(self, error: Exception, notification: ChangeNotification) -> None:
        """
        Handle errors that occur during notification processing.

        Override this method to implement custom error handling.

        Args:
            error: The exception that occurred
            notification: The notification that caused the error
        """
        logger.error(
            f"Observer {self.observer_id} failed to process notification: {error}",
            extra={
                'observer_id': self.observer_id,
                'notification': {
                    'change_type': notification.change_type.value,
                    'entity_id': notification.entity_id,
                    'entity_type': notification.entity_type
                },
                'error': str(error)
            }
        )

    def should_observe(self, entity_type: str, change_type: ChangeType) -> bool:
        """
        Determine if this observer should be notified for the given change.

        Override this method to implement selective observation.

        Args:
            entity_type: Type of entity that changed
            change_type: Type of change that occurred

        Returns:
            True if observer should be notified
        """
        return True


class Observable:
    """
    Observable base class implementing the Observer pattern.

    Maintains a list of observers and notifies them of changes.
    Supports both synchronous and asynchronous observers.
    """

    def __init__(self):
        self._observers: WeakSet[Observer] = WeakSet()
        self._observer_filters: dict[Observer, Callable[[ChangeNotification], bool]] = {}
        self._notification_queue: list[ChangeNotification] = []
        self._batch_mode = False
        self._notification_lock = asyncio.Lock()
        self._stats = {
            'notifications_sent': 0,
            'observers_count': 0,
            'failed_notifications': 0
        }

    def add_observer(
        self,
        observer: Observer,
        filter_func: Optional[Callable[[ChangeNotification], bool]] = None
    ) -> None:
        """
        Add an observer to receive change notifications.

        Args:
            observer: Observer to add
            filter_func: Optional filter function to selectively notify observer
        """
        self._observers.add(observer)
        if filter_func:
            self._observer_filters[observer] = filter_func

        self._stats['observers_count'] = len(self._observers)

        logger.debug(f"Added observer {observer.observer_id} to {self.__class__.__name__}")

    def remove_observer(self, observer: Observer) -> None:
        """
        Remove an observer from receiving notifications.

        Args:
            observer: Observer to remove
        """
        self._observers.discard(observer)
        if observer in self._observer_filters:
            del self._observer_filters[observer]

        self._stats['observers_count'] = len(self._observers)

        logger.debug(f"Removed observer {observer.observer_id} from {self.__class__.__name__}")

    async def notify_observers(self, notification: ChangeNotification) -> None:
        """
        Notify all observers of a change.

        Args:
            notification: Change notification to send
        """
        if self._batch_mode:
            self._notification_queue.append(notification)
            return

        await self._send_notification(notification)

    async def _send_notification(self, notification: ChangeNotification) -> None:
        """Internal method to send notification to observers."""
        async with self._notification_lock:
            if not self._observers:
                return

            # Create tasks for all relevant observers
            tasks = []

            for observer in list(self._observers):  # Create list to avoid iteration issues
                try:
                    # Check if observer should receive this notification
                    if not observer.should_observe(notification.entity_type, notification.change_type):
                        continue

                    # Apply custom filter if exists
                    if observer in self._observer_filters:
                        filter_func = self._observer_filters[observer]
                        if not filter_func(notification):
                            continue

                    # Create notification task
                    task = self._notify_observer_safe(observer, notification)
                    tasks.append(task)

                except Exception as e:
                    logger.error(f"Error preparing notification for observer {observer.observer_id}: {e}")
                    self._stats['failed_notifications'] += 1

            # Execute all notifications concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self._stats['notifications_sent'] += len(tasks)

    async def _notify_observer_safe(self, observer: Observer, notification: ChangeNotification) -> None:
        """Safely notify an observer with error handling."""
        try:
            await observer.on_change(notification)
        except Exception as e:
            self._stats['failed_notifications'] += 1
            try:
                await observer.on_error(e, notification)
            except Exception as error_handler_error:
                logger.error(
                    f"Observer {observer.observer_id} error handler also failed: {error_handler_error}",
                    extra={'original_error': str(e)}
                )

    def start_batch_notifications(self) -> None:
        """
        Start batch mode for notifications.

        In batch mode, notifications are queued and sent together
        when flush_notifications() is called.
        """
        self._batch_mode = True
        self._notification_queue.clear()

    async def flush_notifications(self) -> None:
        """
        Flush all queued notifications and exit batch mode.
        """
        if not self._batch_mode:
            return

        notifications = self._notification_queue.copy()
        self._notification_queue.clear()
        self._batch_mode = False

        # Send all queued notifications
        for notification in notifications:
            await self._send_notification(notification)

    def get_observer_count(self) -> int:
        """Get the number of active observers."""
        return len(self._observers)

    def get_stats(self) -> dict[str, Any]:
        """Get notification statistics."""
        return {
            'observers_count': len(self._observers),
            'notifications_sent': self._stats['notifications_sent'],
            'failed_notifications': self._stats['failed_notifications'],
            'batch_mode': self._batch_mode,
            'queued_notifications': len(self._notification_queue)
        }

    def clear_stats(self) -> None:
        """Clear notification statistics."""
        self._stats = {
            'notifications_sent': 0,
            'observers_count': len(self._observers),
            'failed_notifications': 0
        }


class ObservableEntity(Observable, Generic[T]):
    """
    Generic observable entity that wraps a value and notifies observers of changes.

    Useful for creating observable properties and state objects.
    """

    def __init__(self, initial_value: T, entity_id: str, entity_type: str):
        super().__init__()
        self._value = initial_value
        self._entity_id = entity_id
        self._entity_type = entity_type
        self._change_history: list[ChangeNotification] = []
        self._max_history = 100

    @property
    def value(self) -> T:
        """Get the current value."""
        return self._value

    async def set_value(self, new_value: T) -> None:
        """
        Set a new value and notify observers.

        Args:
            new_value: The new value to set
        """
        old_value = self._value
        self._value = new_value

        notification = ChangeNotification(
            change_type=ChangeType.UPDATED,
            entity_id=self._entity_id,
            entity_type=self._entity_type,
            old_value=old_value,
            new_value=new_value
        )

        # Add to change history
        self._change_history.append(notification)
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history:]

        await self.notify_observers(notification)

    async def update_value(self, update_func: Callable[[T], T]) -> None:
        """
        Update value using a function and notify observers.

        Args:
            update_func: Function that takes current value and returns new value
        """
        new_value = update_func(self._value)
        await self.set_value(new_value)

    def get_change_history(self) -> list[ChangeNotification]:
        """Get the change history for this entity."""
        return self._change_history.copy()

    async def mark_accessed(self) -> None:
        """Mark entity as accessed and notify observers."""
        notification = ChangeNotification(
            change_type=ChangeType.ACCESSED,
            entity_id=self._entity_id,
            entity_type=self._entity_type,
            new_value=self._value
        )

        await self.notify_observers(notification)


class ObservableCollection(Observable, Generic[T]):
    """
    Observable collection that notifies observers of changes to the collection.

    Supports common collection operations with automatic notifications.
    """

    def __init__(self, collection_id: str, collection_type: str):
        super().__init__()
        self._items: dict[str, T] = {}
        self._collection_id = collection_id
        self._collection_type = collection_type

    async def add_item(self, item_id: str, item: T) -> None:
        """Add an item to the collection."""
        self._items[item_id] = item

        notification = ChangeNotification(
            change_type=ChangeType.CREATED,
            entity_id=item_id,
            entity_type=self._collection_type,
            new_value=item,
            metadata={'collection_id': self._collection_id}
        )

        await self.notify_observers(notification)

    async def update_item(self, item_id: str, item: T) -> None:
        """Update an item in the collection."""
        old_item = self._items.get(item_id)
        self._items[item_id] = item

        notification = ChangeNotification(
            change_type=ChangeType.UPDATED,
            entity_id=item_id,
            entity_type=self._collection_type,
            old_value=old_item,
            new_value=item,
            metadata={'collection_id': self._collection_id}
        )

        await self.notify_observers(notification)

    async def remove_item(self, item_id: str) -> Optional[T]:
        """Remove an item from the collection."""
        removed_item = self._items.pop(item_id, None)

        if removed_item is not None:
            notification = ChangeNotification(
                change_type=ChangeType.DELETED,
                entity_id=item_id,
                entity_type=self._collection_type,
                old_value=removed_item,
                metadata={'collection_id': self._collection_id}
            )

            await self.notify_observers(notification)

        return removed_item

    def get_item(self, item_id: str) -> Optional[T]:
        """Get an item from the collection."""
        return self._items.get(item_id)

    def get_all_items(self) -> dict[str, T]:
        """Get all items in the collection."""
        return self._items.copy()

    def size(self) -> int:
        """Get the size of the collection."""
        return len(self._items)

    async def clear(self) -> None:
        """Clear all items from the collection."""
        if not self._items:
            return

        # Notify about batch deletion
        notification = ChangeNotification(
            change_type=ChangeType.BATCH_OPERATION,
            entity_id=self._collection_id,
            entity_type=self._collection_type,
            metadata={
                'operation': 'clear',
                'items_count': len(self._items)
            }
        )

        self._items.clear()
        await self.notify_observers(notification)
