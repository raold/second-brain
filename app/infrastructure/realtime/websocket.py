"""
WebSocket support for real-time communication
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.infrastructure.streaming import Event, EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    # Client to server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    REQUEST = "request"
    PING = "ping"
    
    # Server to client
    EVENT = "event"
    RESPONSE = "response"
    ERROR = "error"
    PONG = "pong"
    
    # Bidirectional
    MESSAGE = "message"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    id: str = None
    type: MessageType = MessageType.MESSAGE
    channel: Optional[str] = None
    data: Any = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
            
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "channel": self.channel,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'WebSocketMessage':
        """Create from dictionary"""
        return cls(
            id=data.get("id"),
            type=MessageType(data.get("type", "message")),
            channel=data.get("channel"),
            data=data.get("data"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        )


class WebSocketConnection:
    """Manages a single WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, connection_id: str = None):
        self.websocket = websocket
        self.connection_id = connection_id or str(uuid4())
        self.subscriptions: Set[str] = set()
        self.metadata: dict[str, Any] = {}
        self._send_queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        
    async def accept(self):
        """Accept the WebSocket connection"""
        await self.websocket.accept()
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._send_task = asyncio.create_task(self._send_loop())
        logger.info(f"WebSocket connection {self.connection_id} accepted")
        
    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection"""
        if self._receive_task:
            self._receive_task.cancel()
        if self._send_task:
            self._send_task.cancel()
            
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.close(code, reason)
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
            
        logger.info(f"WebSocket connection {self.connection_id} closed")
        
    async def send_message(self, message: WebSocketMessage):
        """Send a message to the client"""
        await self._send_queue.put(message)
        
    async def send_event(self, event: Event, channel: str = None):
        """Send an event to the client"""
        message = WebSocketMessage(
            type=MessageType.EVENT,
            channel=channel or event.event_type.value,
            data=event.to_dict()
        )
        await self.send_message(message)
        
    async def send_error(self, error: str, request_id: str = None):
        """Send an error message to the client"""
        message = WebSocketMessage(
            id=request_id,
            type=MessageType.ERROR,
            data={"error": error}
        )
        await self.send_message(message)
        
    def subscribe(self, channel: str):
        """Subscribe to a channel"""
        self.subscriptions.add(channel)
        logger.debug(f"Connection {self.connection_id} subscribed to {channel}")
        
    def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        self.subscriptions.discard(channel)
        logger.debug(f"Connection {self.connection_id} unsubscribed from {channel}")
        
    def is_subscribed(self, channel: str) -> bool:
        """Check if subscribed to a channel"""
        return channel in self.subscriptions
        
    async def _receive_loop(self):
        """Receive messages from client"""
        try:
            while True:
                # Receive message
                data = await self.websocket.receive_json()
                
                # Parse message
                try:
                    message = WebSocketMessage.from_dict(data)
                except Exception as e:
                    await self.send_error(f"Invalid message format: {e}")
                    continue
                    
                # Handle message
                await self._handle_message(message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket {self.connection_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            
    async def _send_loop(self):
        """Send queued messages to client"""
        try:
            while True:
                message = await self._send_queue.get()
                
                if self.websocket.client_state == WebSocketState.CONNECTED:
                    await self.websocket.send_json(message.to_dict())
                else:
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            
    async def _handle_message(self, message: WebSocketMessage):
        """Handle incoming message"""
        if message.type == MessageType.PING:
            # Respond to ping
            pong = WebSocketMessage(
                id=message.id,
                type=MessageType.PONG,
                data=message.data
            )
            await self.send_message(pong)
            
        elif message.type == MessageType.SUBSCRIBE:
            # Subscribe to channel
            channel = message.data.get("channel")
            if channel:
                self.subscribe(channel)
                
        elif message.type == MessageType.UNSUBSCRIBE:
            # Unsubscribe from channel
            channel = message.data.get("channel")
            if channel:
                self.unsubscribe(channel)
                
        # Let subclasses handle other message types


class WebSocketManager:
    """Manages multiple WebSocket connections"""
    
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._channel_connections: Dict[str, Set[str]] = {}
        self._event_bus: Optional[EventBus] = None
        self._event_handler_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the WebSocket manager"""
        # Connect to event bus
        self._event_bus = get_event_bus()
        
        # Subscribe to all events
        for event_type in EventType:
            self._event_bus.subscribe(event_type, self._handle_event)
            
        # Start event handler
        self._event_handler_task = asyncio.create_task(self._event_handler())
        
        logger.info("WebSocket manager started")
        
    async def stop(self):
        """Stop the WebSocket manager"""
        # Cancel event handler
        if self._event_handler_task:
            self._event_handler_task.cancel()
            
        # Close all connections
        tasks = []
        for connection in self._connections.values():
            tasks.append(connection.close())
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self._connections.clear()
        self._channel_connections.clear()
        
        logger.info("WebSocket manager stopped")
        
    async def connect(self, websocket: WebSocket, connection_id: str = None) -> WebSocketConnection:
        """Handle new WebSocket connection"""
        connection = WebSocketConnection(websocket, connection_id)
        await connection.accept()
        
        # Store connection
        self._connections[connection.connection_id] = connection
        
        # Send welcome message
        welcome = WebSocketMessage(
            type=MessageType.MESSAGE,
            data={
                "message": "Connected to real-time system",
                "connection_id": connection.connection_id
            }
        )
        await connection.send_message(welcome)
        
        return connection
        
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        connection = self._connections.pop(connection_id, None)
        
        if connection:
            # Remove from all channels
            for channel in connection.subscriptions:
                if channel in self._channel_connections:
                    self._channel_connections[channel].discard(connection_id)
                    
            await connection.close()
            
    async def broadcast(self, message: WebSocketMessage, channel: str = None):
        """Broadcast message to all connections or specific channel"""
        if channel:
            # Send to channel subscribers
            connection_ids = self._channel_connections.get(channel, set())
        else:
            # Send to all connections
            connection_ids = set(self._connections.keys())
            
        # Send message to each connection
        tasks = []
        for conn_id in connection_ids:
            connection = self._connections.get(conn_id)
            if connection:
                tasks.append(connection.send_message(message))
                
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection"""
        connection = self._connections.get(connection_id)
        if connection:
            await connection.send_message(message)
            
    def subscribe_connection(self, connection_id: str, channel: str):
        """Subscribe connection to channel"""
        connection = self._connections.get(connection_id)
        if connection:
            connection.subscribe(channel)
            
            # Update channel mapping
            if channel not in self._channel_connections:
                self._channel_connections[channel] = set()
            self._channel_connections[channel].add(connection_id)
            
    def unsubscribe_connection(self, connection_id: str, channel: str):
        """Unsubscribe connection from channel"""
        connection = self._connections.get(connection_id)
        if connection:
            connection.unsubscribe(channel)
            
            # Update channel mapping
            if channel in self._channel_connections:
                self._channel_connections[channel].discard(connection_id)
                
    async def _handle_event(self, event: Event):
        """Handle event from event bus"""
        # Broadcast event to subscribers
        channel = event.event_type.value
        
        # Get connections subscribed to this event type
        connection_ids = self._channel_connections.get(channel, set())
        
        # Send event to each connection
        tasks = []
        for conn_id in connection_ids:
            connection = self._connections.get(conn_id)
            if connection:
                tasks.append(connection.send_event(event, channel))
                
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _event_handler(self):
        """Handle events from event bus"""
        # This is handled by event subscriptions
        while True:
            await asyncio.sleep(1)
            
    def get_metrics(self) -> dict[str, Any]:
        """Get WebSocket metrics"""
        channel_stats = {
            channel: len(connections)
            for channel, connections in self._channel_connections.items()
        }
        
        return {
            "total_connections": len(self._connections),
            "channels": channel_stats,
            "connections": {
                conn_id: {
                    "subscriptions": list(conn.subscriptions),
                    "metadata": conn.metadata
                }
                for conn_id, conn in self._connections.items()
            }
        }


# Global WebSocket manager
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


# WebSocket endpoint handler
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    manager = get_websocket_manager()
    
    # Accept connection
    connection = await manager.connect(websocket)
    
    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        await manager.disconnect(connection.connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(connection.connection_id)