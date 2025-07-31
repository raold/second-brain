"""
WebSocket Event Models - v2.8.2

Data models for real-time WebSocket communication including events,
subscriptions, and connection management.
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from typing import List
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


class EventPriority(IntEnum):
    """Priority levels for websocket events"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    
    @property
    def value_str(self):
        """Get string representation for backwards compatibility"""
        return self.name.lower()


class BroadcastMessage(BaseModel):
    """Message to broadcast via websocket"""
    event_type: str
    
    # Support both field names for compatibility
    payload: Optional[Any] = None
    data: Optional[Any] = None
    
    broadcast_to: Optional[List[str]] = Field(None, description="List of user IDs to broadcast to")
    priority: EventPriority = Field(default=EventPriority.MEDIUM)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('data', mode='before')
    def set_payload_from_data(cls, v, info):
        """Support data field as alias for payload"""
        if v is not None and info.data.get('payload') is None:
            info.data['payload'] = v
        return v


class ConnectionState(str, Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SubscriptionType(str, Enum):
    """Types of subscriptions for websocket updates"""
    ALL = "all"
    MEMORY = "memory"
    SYNTHESIS = "synthesis"
    REPORT = "report"
    USER = "user"
    SYSTEM = "system"


class EventType(str, Enum):
    """Types of events that can be broadcast."""

    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_REVIEWED = "memory.reviewed"

    # Review events
    REVIEW_SCHEDULED = "review.scheduled"
    REVIEW_COMPLETED = "review.completed"
    REVIEW_DUE = "review.due"

    # Report events
    REPORT_STARTED = "report.started"
    REPORT_PROGRESS = "report.progress"
    REPORT_COMPLETED = "report.completed"
    REPORT_FAILED = "report.failed"

    # Analysis events
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    INSIGHT_DISCOVERED = "insight.discovered"

    # System events
    SYSTEM_STATUS = "system.status"
    SYSTEM_NOTIFICATION = "system.notification"
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"

    # Metrics events
    METRICS_UPDATE = "metrics.update"
    STATISTICS_CHANGED = "statistics.changed"

    # Synthesis events
    SYNTHESIS_STARTED = "synthesis.started"
    SYNTHESIS_COMPLETED = "synthesis.completed"
    SYNTHESIS_ERROR = "synthesis.error"


class ConnectionStatusEnum(str, Enum):
    """WebSocket connection status."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketEvent(BaseModel):
    """Base event model for WebSocket messages."""

    id: str = Field(..., description="Unique event ID")
    type: Optional[str] = Field(None, description="Event type")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Event data
    resource_type: Optional[str] = Field(None, description="Type of resource (memory, report, etc.)")
    resource_id: Optional[str] = Field(None, description="ID of the resource")
    user_id: Optional[str] = Field(None, description="User who triggered the event")

    # Payload
    payload: Optional[dict[str, Any]] = Field(None, description="Event payload for tests")
    data: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Routing
    channel: Optional[str] = Field(None, description="Channel for routing")
    broadcast: bool = Field(False, description="Whether to broadcast to all users")
    target_users: list[str] = Field(default_factory=list, description="Specific users to notify")


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication."""

    type: str = Field(..., description="Message type: event, request, response, error")
    id: Optional[str] = Field(None, description="Message ID for request/response matching")

    # Content
    event: Optional[WebSocketEvent] = Field(None, description="Event data (for event messages)")
    action: Optional[str] = Field(None, description="Action to perform (for requests)")
    payload: Optional[dict[str, Any]] = Field(None, description="Message payload")

    # Response data
    success: Optional[bool] = Field(None, description="Success status (for responses)")
    error: Optional[str] = Field(None, description="Error message (for error messages)")
    error_code: Optional[str] = Field(None, description="Error code")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(None, description="For request/response correlation")


class SubscriptionRequest(BaseModel):
    """Request to subscribe to specific events."""
    
    # Fields expected by tests
    client_id: Optional[str] = Field(None, description="Client ID")
    event_types: list[str] = Field(..., description="Event types to subscribe to")
    filters: Optional[dict[str, Any]] = Field(None, description="Subscription filters")
    
    # Original fields
    action: str = Field("subscribe", description="Action: subscribe or unsubscribe")
    channels: list[str] = Field(default_factory=list, description="Specific channels")
    resource_types: list[str] = Field(default_factory=list, description="Filter by resource type")
    resource_ids: list[str] = Field(default_factory=list, description="Specific resource IDs")
    include_historical: bool = Field(False, description="Include recent historical events")
    historical_limit: int = Field(10, description="Number of historical events")

    @field_validator('action')
    def validate_action(cls, v):
        """Validate subscription action."""
        if v not in ['subscribe', 'unsubscribe']:
            raise ValueError("Action must be 'subscribe' or 'unsubscribe'")
        return v


class EventSubscription(BaseModel):
    """Active event subscription."""

    id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    connection_id: str = Field(..., description="WebSocket connection ID")

    # Subscription details
    event_types: list[EventType] = Field(..., description="Subscribed event types")
    channels: list[str] = Field(default_factory=list, description="Subscribed channels")
    filters: dict[str, Any] = Field(default_factory=dict, description="Active filters")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_event_at: Optional[datetime] = Field(None, description="Last event delivered")
    events_delivered: int = Field(0, description="Total events delivered")

    # Status
    active: bool = Field(True, description="Whether subscription is active")
    paused_at: Optional[datetime] = Field(None, description="When subscription was paused")


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""

    connection_id: str = Field(..., description="Unique connection ID")
    user_id: str = Field(..., description="User ID")

    # Connection details
    status: ConnectionStatusEnum = Field(..., description="Connection status")
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = Field(None, description="Last ping received")

    # Client info
    client_version: Optional[str] = Field(None, description="Client version")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="Client IP address")

    # Subscriptions
    subscriptions: list[EventSubscription] = Field(
        default_factory=list,
        description="Active subscriptions"
    )

    # Metrics
    messages_sent: int = Field(0, description="Messages sent to client")
    messages_received: int = Field(0, description="Messages received from client")
    bytes_sent: int = Field(0, description="Total bytes sent")
    bytes_received: int = Field(0, description="Total bytes received")

    # Rate limiting
    rate_limit_remaining: int = Field(100, description="Remaining rate limit")
    rate_limit_reset: Optional[datetime] = Field(None, description="Rate limit reset time")


class EventBatch(BaseModel):
    """Batch of events for efficient delivery."""

    events: list[WebSocketEvent] = Field(..., description="Events in batch")
    batch_id: str = Field(..., description="Batch ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Delivery tracking
    target_connections: list[str] = Field(..., description="Target connection IDs")
    delivered_to: list[str] = Field(default_factory=list, description="Successfully delivered")
    failed_deliveries: dict[str, str] = Field(
        default_factory=dict,
        description="Failed deliveries with reasons"
    )

    @field_validator('events')
    def validate_batch_size(cls, v):
        """Validate batch size."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 events")
        return v


class BroadcastRequest(BaseModel):
    """Request to broadcast an event."""

    event: WebSocketEvent = Field(..., description="Event to broadcast")

    # Targeting
    broadcast_type: str = Field(
        "all",
        description="Broadcast type: all, channel, users, filters"
    )
    channels: list[str] = Field(default_factory=list, description="Target channels")
    user_ids: list[str] = Field(default_factory=list, description="Target users")

    # Filters
    connection_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filter connections by attributes"
    )

    # Options
    require_acknowledgment: bool = Field(False, description="Require client acknowledgment")
    ttl_seconds: Optional[int] = Field(None, description="Message TTL")
    priority: str = Field("normal", description="Delivery priority: low, normal, high")

    @field_validator('broadcast_type')
    def validate_broadcast_type(cls, v):
        """Validate broadcast type."""
        valid_types = ['all', 'channel', 'users', 'filters']
        if v not in valid_types:
            raise ValueError(f"Invalid broadcast type. Must be one of: {valid_types}")
        return v


class WebSocketMetrics(BaseModel):
    """Metrics for WebSocket connections."""

    # Connection metrics
    total_connections: int = Field(0, description="Total active connections")
    authenticated_connections: int = Field(0, description="Authenticated connections")

    # Message metrics
    messages_per_second: float = Field(0.0, description="Current message rate")
    events_per_second: float = Field(0.0, description="Current event rate")

    # Performance metrics
    average_latency_ms: float = Field(0.0, description="Average message latency")
    p95_latency_ms: float = Field(0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(0.0, description="99th percentile latency")

    # Resource usage
    memory_usage_mb: float = Field(0.0, description="Memory usage in MB")
    cpu_usage_percent: float = Field(0.0, description="CPU usage percentage")

    # Error metrics
    error_rate: float = Field(0.0, description="Error rate percentage")
    failed_deliveries: int = Field(0, description="Failed delivery count")

    # By event type
    events_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Event counts by type"
    )

    # Timestamp
    measured_at: datetime = Field(default_factory=datetime.utcnow)


class SystemNotification(BaseModel):
    """System-wide notification for WebSocket clients"""
    id: str
    title: str
    message: str
    notification_type: str  # "info", "warning", "error", "success"
    priority: EventPriority = Field(default=EventPriority.MEDIUM)
    target_users: Optional[list[str]] = None  # None means all users
    expires_at: Optional[datetime] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Models expected by tests (aliases for backward compatibility)
class ConnectionStatus(BaseModel):
    """Connection status tracking (test compatibility)"""
    client_id: str
    connected: bool
    connected_at: Optional[datetime] = None
    last_ping: Optional[datetime] = None
    subscriptions: List[str] = Field(default_factory=list)
