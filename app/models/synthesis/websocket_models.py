"""WebSocket models for real-time communication"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

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
    payload: dict[str, Any] = {}
    data: dict[str, Any] | None = None  # Additional data field
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_id: str | None = None
    metadata: dict[str, Any] | None = None


class BroadcastMessage(BaseModel):
    """Message for broadcasting to multiple connections"""

    event_type: str
    payload: dict[str, Any] = {}
    data: dict[str, Any] | None = None  # Additional data field for compatibility
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    targets: list[str] | None = None  # Specific user IDs to target


class ConnectionInfo(BaseModel):
    """WebSocket connection information"""

    connection_id: str
    user_id: str | None = None
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime | None = None
    last_activity: datetime | None = None
    metadata: dict[str, Any] = {}


class ConnectionStatus(BaseModel):
    """Connection status response"""

    is_connected: bool
    connection_id: str | None = None
    state: ConnectionState
    connected_since: datetime | None = None
    message_count: int = 0


class EventSubscription(BaseModel):
    """Event subscription configuration"""

    event_types: list[EventType]
    user_id: str | None = None
    filters: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubscriptionRequest(BaseModel):
    """Request to subscribe to events"""

    event_types: list[str]
    filters: dict[str, Any] | None = {}
    subscribe: bool = True  # Whether to subscribe or unsubscribe
    metadata: dict[str, Any] | None = None


class WebSocketEvent(BaseModel):
    """WebSocket event model"""

    event_type: EventType
    payload: dict[str, Any]
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str | None = None
    target_users: list[str] | None = None


class WebSocketMetrics(BaseModel):
    """WebSocket metrics"""

    total_connections: int = 0
    active_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    uptime_seconds: float = 0
    last_activity: datetime | None = None
