"""
WebSocket router for real-time updates
Handles live connections and event broadcasting
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["Real-time"],
)


# ==================== Models ====================


class WebSocketMessage(BaseModel):
    """WebSocket message format"""

    type: str = Field(..., pattern="^(subscribe|unsubscribe|ping|message)$")
    channel: str | None = None
    data: Dict[str, Any] | None = None


class WebSocketResponse(BaseModel):
    """WebSocket response format"""

    type: str
    channel: str | None = None
    data: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None


# ==================== Connection Manager ====================


class ConnectionManager:
    """Manages WebSocket connections for single-user container"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "connected_at": datetime.now(timezone.utc),
            "subscriptions": set(),
        }

        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "data": {
                    "status": "connected",
                    "message": "Welcome to Second Brain real-time updates",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a connection and clean up"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Clean up subscriptions
        if websocket in self.connection_metadata:
            for channel in self.connection_metadata[websocket].get("subscriptions", []):
                if channel in self.subscriptions:
                    self.subscriptions[channel].remove(websocket)
            del self.connection_metadata[websocket]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a connection to a channel"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []

        if websocket not in self.subscriptions[channel]:
            self.subscriptions[channel].append(websocket)
            self.connection_metadata[websocket]["subscriptions"].add(channel)

            await websocket.send_json(
                {
                    "type": "subscribed",
                    "channel": channel,
                    "data": {"message": f"Subscribed to {channel}"},
                }
            )

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a connection from a channel"""
        if channel in self.subscriptions and websocket in self.subscriptions[channel]:
            self.subscriptions[channel].remove(websocket)
            self.connection_metadata[websocket]["subscriptions"].discard(channel)

            await websocket.send_json(
                {
                    "type": "unsubscribed",
                    "channel": channel,
                    "data": {"message": f"Unsubscribed from {channel}"},
                }
            )

    async def broadcast(self, message: Dict[str, Any], channel: str | None = None):
        """Broadcast message to all connections or specific channel"""
        disconnected = []

        if channel and channel in self.subscriptions:
            connections = self.subscriptions[channel]
        else:
            connections = self.active_connections

        for connection in connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


# ==================== Endpoints ====================


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Supports:
    - Event subscriptions
    - Real-time memory updates
    - Ping/pong for connection health
    - Custom message broadcasting

    Message format:
    ```json
    {
        "type": "subscribe|unsubscribe|ping|message",
        "channel": "memories|analytics|system",
        "data": {...}
    }
    ```
    """
    try:
        await manager.connect(websocket)

        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")
                channel = message.get("channel")
                msg_data = message.get("data", {})

                # Handle message types
                if msg_type == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
                            "correlation_id": msg_data.get("id"),
                        }
                    )

                elif msg_type == "subscribe" and channel:
                    await manager.subscribe(websocket, channel)

                elif msg_type == "unsubscribe" and channel:
                    await manager.unsubscribe(websocket, channel)

                elif msg_type == "message":
                    # Echo message to all subscribers
                    await manager.broadcast(
                        {
                            "type": "message",
                            "channel": channel,
                            "data": msg_data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        channel,
                    )

                else:
                    await websocket.send_json(
                        {"type": "error", "data": {"message": f"Unknown message type: {msg_type}"}}
                    )

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"message": "Invalid JSON"}})
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({"type": "error", "data": {"message": str(e)}})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ==================== Event Broadcasting Functions ====================


async def broadcast_memory_created(memory_id: str, memory_data: Dict[str, Any]):
    """Broadcast memory creation event"""
    await manager.broadcast(
        {
            "type": "memory_created",
            "channel": "memories",
            "data": {"memory_id": memory_id, "memory": memory_data},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "memories",
    )


async def broadcast_memory_updated(memory_id: str, memory_data: Dict[str, Any]):
    """Broadcast memory update event"""
    await manager.broadcast(
        {
            "type": "memory_updated",
            "channel": "memories",
            "data": {"memory_id": memory_id, "memory": memory_data},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "memories",
    )


async def broadcast_memory_deleted(memory_id: str):
    """Broadcast memory deletion event"""
    await manager.broadcast(
        {
            "type": "memory_deleted",
            "channel": "memories",
            "data": {"memory_id": memory_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "memories",
    )


async def broadcast_system_event(event_type: str, data: Dict[str, Any]):
    """Broadcast system event"""
    await manager.broadcast(
        {
            "type": event_type,
            "channel": "system",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "system",
    )
