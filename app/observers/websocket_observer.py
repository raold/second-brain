"""
WebSocket observer implementation for real-time updates.

Provides WebSocket-based real-time notifications to connected clients
using the Observer pattern.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from starlette.websockets import WebSocketState
except ImportError:
    # Fallback for testing without FastAPI
    WebSocket = None
    WebSocketDisconnect = Exception
    class WebSocketState:
        CONNECTED = "connected"
        DISCONNECTED = "disconnected"

from .observable import ChangeNotification, ChangeType, Observer

logger = logging.getLogger(__name__)


@dataclass
class WebSocketMessage:
    """Structure for WebSocket messages."""
    type: str
    data: dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(asdict(self))


@dataclass
class ClientSubscription:
    """Client subscription configuration."""
    client_id: str
    websocket: 'WebSocket'
    entity_types: set[str] = None
    change_types: set[ChangeType] = None
    user_id: Optional[str] = None
    filters: dict[str, Any] = None

    def __post_init__(self):
        if self.entity_types is None:
            self.entity_types = set()
        if self.change_types is None:
            self.change_types = set()
        if self.filters is None:
            self.filters = {}

    def should_receive(self, notification: ChangeNotification) -> bool:
        """Check if client should receive this notification."""
        # Check entity type filter
        if self.entity_types and notification.entity_type not in self.entity_types:
            return False

        # Check change type filter
        if self.change_types and notification.change_type not in self.change_types:
            return False

        # Check user-specific filter
        if self.user_id and hasattr(notification, 'user_id'):
            if getattr(notification, 'user_id', None) != self.user_id:
                return False

        # Apply custom filters
        for filter_key, filter_value in self.filters.items():
            if filter_key in notification.metadata:
                if notification.metadata[filter_key] != filter_value:
                    return False

        return True


class WebSocketManager:
    """
    Manager for WebSocket connections and real-time updates.

    Handles client connections, subscriptions, and message broadcasting
    with proper error handling and connection cleanup.
    """

    def __init__(self):
        self._clients: dict[str, ClientSubscription] = {}
        self._connections: dict[str, WebSocket] = {}
        self._client_stats: dict[str, dict[str, int]] = {}
        self._lock = asyncio.Lock()

        # Configuration
        self.max_clients = 1000
        self.message_queue_size = 100
        self.ping_interval = 30  # seconds
        self.connection_timeout = 300  # seconds

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the WebSocket manager background tasks."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        self._ping_task = asyncio.create_task(self._ping_clients())

        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager and close all connections."""
        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()

        # Close all connections
        await self._close_all_connections()

        logger.info("WebSocket manager stopped")

    async def add_client(
        self,
        client_id: str,
        websocket: WebSocket,
        entity_types: Optional[set[str]] = None,
        change_types: Optional[set[ChangeType]] = None,
        user_id: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Add a new WebSocket client.

        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection
            entity_types: Entity types to subscribe to (None = all)
            change_types: Change types to subscribe to (None = all)
            user_id: User ID for user-specific filtering
            filters: Additional custom filters

        Returns:
            True if client was added successfully
        """
        async with self._lock:
            if len(self._clients) >= self.max_clients:
                logger.warning(f"Max clients ({self.max_clients}) reached, rejecting client {client_id}")
                return False

            if client_id in self._clients:
                # Remove existing client
                await self._remove_client_internal(client_id)

            subscription = ClientSubscription(
                client_id=client_id,
                websocket=websocket,
                entity_types=entity_types or set(),
                change_types=change_types or set(),
                user_id=user_id,
                filters=filters or {}
            )

            self._clients[client_id] = subscription
            self._connections[client_id] = websocket
            self._client_stats[client_id] = {
                'messages_sent': 0,
                'messages_failed': 0,
                'connected_at': int(datetime.utcnow().timestamp())
            }

            logger.info(f"Added WebSocket client {client_id} (total clients: {len(self._clients)})")
            return True

    async def remove_client(self, client_id: str) -> None:
        """Remove a WebSocket client."""
        async with self._lock:
            await self._remove_client_internal(client_id)

    async def _remove_client_internal(self, client_id: str) -> None:
        """Internal method to remove client without locking."""
        if client_id in self._clients:
            # Close WebSocket connection
            websocket = self._connections.get(client_id)
            if websocket and websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.debug(f"Error closing WebSocket for client {client_id}: {e}")

            # Remove from tracking
            del self._clients[client_id]
            self._connections.pop(client_id, None)
            self._client_stats.pop(client_id, None)

            logger.info(f"Removed WebSocket client {client_id}")

    async def broadcast_message(self, message: WebSocketMessage) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast

        Returns:
            Number of clients that received the message
        """
        if not self._clients:
            return 0

        successful_sends = 0
        failed_clients = []

        for client_id, subscription in list(self._clients.items()):
            try:
                websocket = subscription.websocket
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message.to_json())
                    self._client_stats[client_id]['messages_sent'] += 1
                    successful_sends += 1
                else:
                    failed_clients.append(client_id)
            except Exception as e:
                logger.warning(f"Failed to send message to client {client_id}: {e}")
                self._client_stats[client_id]['messages_failed'] += 1
                failed_clients.append(client_id)

        # Remove failed clients
        for client_id in failed_clients:
            await self._remove_client_internal(client_id)

        return successful_sends

    async def send_to_client(self, client_id: str, message: WebSocketMessage) -> bool:
        """
        Send a message to a specific client.

        Args:
            client_id: Target client ID
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        subscription = self._clients.get(client_id)
        if not subscription:
            return False

        try:
            websocket = subscription.websocket
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message.to_json())
                self._client_stats[client_id]['messages_sent'] += 1
                return True
            else:
                await self._remove_client_internal(client_id)
                return False
        except Exception as e:
            logger.warning(f"Failed to send message to client {client_id}: {e}")
            self._client_stats[client_id]['messages_failed'] += 1
            await self._remove_client_internal(client_id)
            return False

    async def send_notification(self, notification: ChangeNotification) -> int:
        """
        Send a change notification to relevant clients.

        Args:
            notification: Change notification to send

        Returns:
            Number of clients that received the notification
        """
        if not self._clients:
            return 0

        message = WebSocketMessage(
            type="change_notification",
            data={
                'change_type': notification.change_type.value,
                'entity_id': notification.entity_id,
                'entity_type': notification.entity_type,
                'old_value': notification.old_value,
                'new_value': notification.new_value,
                'metadata': notification.metadata,
                'timestamp': notification.timestamp
            }
        )

        successful_sends = 0
        failed_clients = []

        for client_id, subscription in list(self._clients.items()):
            if subscription.should_receive(notification):
                try:
                    websocket = subscription.websocket
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(message.to_json())
                        self._client_stats[client_id]['messages_sent'] += 1
                        successful_sends += 1
                    else:
                        failed_clients.append(client_id)
                except Exception as e:
                    logger.warning(f"Failed to send notification to client {client_id}: {e}")
                    self._client_stats[client_id]['messages_failed'] += 1
                    failed_clients.append(client_id)

        # Remove failed clients
        for client_id in failed_clients:
            await self._remove_client_internal(client_id)

        return successful_sends

    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._clients)

    def get_client_stats(self) -> dict[str, Any]:
        """Get statistics about connected clients."""
        now = int(datetime.utcnow().timestamp())

        stats = {
            'total_clients': len(self._clients),
            'clients': {},
            'total_messages_sent': 0,
            'total_messages_failed': 0
        }

        for client_id, client_stats in self._client_stats.items():
            subscription = self._clients.get(client_id)
            stats['clients'][client_id] = {
                'messages_sent': client_stats['messages_sent'],
                'messages_failed': client_stats['messages_failed'],
                'connected_duration': now - client_stats['connected_at'],
                'subscriptions': {
                    'entity_types': list(subscription.entity_types) if subscription else [],
                    'change_types': [ct.value for ct in subscription.change_types] if subscription else [],
                    'user_id': subscription.user_id if subscription else None
                }
            }

            stats['total_messages_sent'] += client_stats['messages_sent']
            stats['total_messages_failed'] += client_stats['messages_failed']

        return stats

    async def _cleanup_connections(self) -> None:
        """Background task to cleanup dead connections."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                failed_clients = []
                for client_id, websocket in list(self._connections.items()):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        failed_clients.append(client_id)

                for client_id in failed_clients:
                    await self._remove_client_internal(client_id)

                if failed_clients:
                    logger.info(f"Cleaned up {len(failed_clients)} disconnected clients")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")

    async def _ping_clients(self) -> None:
        """Background task to ping clients and detect dead connections."""
        while self._running:
            try:
                await asyncio.sleep(self.ping_interval)

                if not self._clients:
                    continue

                ping_message = WebSocketMessage(
                    type="ping",
                    data={"timestamp": datetime.utcnow().isoformat()}
                )

                failed_clients = []
                for client_id, subscription in list(self._clients.items()):
                    try:
                        websocket = subscription.websocket
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_text(ping_message.to_json())
                        else:
                            failed_clients.append(client_id)
                    except Exception:
                        failed_clients.append(client_id)

                for client_id in failed_clients:
                    await self._remove_client_internal(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in client ping: {e}")

    async def _close_all_connections(self) -> None:
        """Close all WebSocket connections."""
        for client_id in list(self._clients.keys()):
            await self._remove_client_internal(client_id)


class WebSocketObserver(Observer):
    """
    Observer that sends change notifications via WebSocket.

    Integrates with WebSocketManager to provide real-time updates
    to connected clients based on domain events.
    """

    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self._stats = {
            'notifications_processed': 0,
            'notifications_sent': 0,
            'notifications_failed': 0
        }

    async def on_change(self, notification: ChangeNotification) -> None:
        """Handle change notification by sending to WebSocket clients."""
        self._stats['notifications_processed'] += 1

        try:
            sent_count = await self.websocket_manager.send_notification(notification)
            self._stats['notifications_sent'] += sent_count

            logger.debug(
                f"WebSocket notification sent to {sent_count} clients",
                extra={
                    'change_type': notification.change_type.value,
                    'entity_id': notification.entity_id,
                    'entity_type': notification.entity_type,
                    'clients_notified': sent_count
                }
            )

        except Exception as e:
            self._stats['notifications_failed'] += 1
            logger.error(f"Failed to send WebSocket notification: {e}")
            raise

    def should_observe(self, entity_type: str, change_type: ChangeType) -> bool:
        """Only observe if there are connected clients."""
        return self.websocket_manager.get_client_count() > 0

    def get_stats(self) -> dict[str, Any]:
        """Get observer statistics."""
        return {
            'notifications_processed': self._stats['notifications_processed'],
            'notifications_sent': self._stats['notifications_sent'],
            'notifications_failed': self._stats['notifications_failed'],
            'connected_clients': self.websocket_manager.get_client_count()
        }


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


async def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
        await _websocket_manager.start()
    return _websocket_manager


async def create_websocket_observer() -> WebSocketObserver:
    """Create a WebSocket observer with the global manager."""
    manager = await get_websocket_manager()
    return WebSocketObserver(manager)
