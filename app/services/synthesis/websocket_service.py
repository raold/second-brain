from typing import Any

from fastapi import WebSocket

from app.utils.logging_config import get_logger
from app.events.domain_events import SystemHealthEvent


"""WebSocket service for real-time communication"""




logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.user_connections: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str | None = None):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Clean up user connections
        for _user_id, connections in self.user_connections.items():
            if connection_id in connections:
                connections.remove(connection_id)

    async def send_message(self, connection_id: str, message: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Broadcast a message to all connections"""
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")


class EventBroadcaster:
    """Broadcasts events to WebSocket connections"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def broadcast_event(self, event_type: str, data: dict[str, Any]):
        """Broadcast an event to all connected clients"""
        message = {"type": event_type, "data": data}
        await self.connection_manager.broadcast(str(message))


class WebSocketService:
    """Main WebSocket service for managing connections and events"""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.event_broadcaster = EventBroadcaster(self.connection_manager)
        self.active_subscriptions: dict[str, set[str]] = {}

    async def handle_connection(
        self, websocket: WebSocket, connection_id: str, user_id: str | None = None
    ):
        """Handle a new WebSocket connection"""
        await self.connection_manager.connect(websocket, connection_id, user_id)

        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                # Process incoming messages if needed
                logger.info(f"Received message from {connection_id}: {data}")
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            self.connection_manager.disconnect(connection_id)

    async def send_notification(self, user_id: str, notification: dict[str, Any]):
        """Send a notification to all connections for a specific user"""
        if user_id in self.connection_manager.user_connections:
            for connection_id in self.connection_manager.user_connections[user_id]:
                await self.connection_manager.send_message(connection_id, str(notification))

    def get_metrics(self) -> dict[str, Any]:
        """Get WebSocket service metrics"""
        return {
            "active_connections": len(self.connection_manager.active_connections),
            "users_connected": len(self.connection_manager.user_connections),
            "subscriptions": len(self.active_subscriptions),
        }


# Singleton instance
_websocket_service = None


def get_websocket_service() -> WebSocketService:
    """Get singleton instance of WebSocket service"""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service
