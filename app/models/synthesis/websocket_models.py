"""WebSocket models for real-time communication"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types"""
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    SYSTEM_NOTIFICATION = "system.notification"
    SYSTEM_STATUS = "system.status"
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_CLOSED = "connection.closed"
    USER_MESSAGE = "user.message"
    ERROR = "error"


class EventPriority(str, Enum):
    """Event priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectionState(str, Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """Base WebSocket message model"""
    type: str
    payload: Dict[str, Any] = {}
    data: Optional[Dict[str, Any]] = None  # Additional data field
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BroadcastMessage(BaseModel):
    """Message for broadcasting to multiple connections"""
    event_type: str
    payload: Dict[str, Any] = {}
    data: Optional[Dict[str, Any]] = None  # Additional data field for compatibility
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    targets: Optional[List[str]] = None  # Specific user IDs to target


class ConnectionInfo(BaseModel):
    """WebSocket connection information"""
    connection_id: str
    user_id: Optional[str] = None
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class ConnectionStatus(BaseModel):
    """Connection status response"""
    is_connected: bool
    connection_id: Optional[str] = None
    state: ConnectionState
    connected_since: Optional[datetime] = None
    message_count: int = 0


class EventSubscription(BaseModel):
    """Event subscription configuration"""
    event_types: List[EventType]
    user_id: Optional[str] = None
    filters: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubscriptionRequest(BaseModel):
    """Request to subscribe to events"""
    event_types: List[str]
    filters: Optional[Dict[str, Any]] = {}
    subscribe: bool = True  # Whether to subscribe or unsubscribe
    metadata: Optional[Dict[str, Any]] = None


class WebSocketEvent(BaseModel):
    """WebSocket event model"""
    event_type: EventType
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None
    target_users: Optional[List[str]] = None


class WebSocketMetrics(BaseModel):
    """WebSocket metrics"""
    total_connections: int = 0
    active_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    uptime_seconds: float = 0
    last_activity: Optional[datetime] = None