"""
Data models for WebSocket real-time updates
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of real-time events"""
    # Memory events
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # Connection events
    CONNECTION_CREATED = "connection.created"
    CONNECTION_DELETED = "connection.deleted"

    # Metrics events
    METRICS_UPDATED = "metrics.updated"
    METRICS_ANOMALY = "metrics.anomaly"
    METRICS_MILESTONE = "metrics.milestone"

    # Review events
    REVIEW_DUE = "review.due"
    REVIEW_COMPLETED = "review.completed"
    REVIEW_STREAK = "review.streak"

    # Synthesis events
    CONSOLIDATION_SUGGESTED = "consolidation.suggested"
    SUMMARY_GENERATED = "summary.generated"
    SUGGESTION_AVAILABLE = "suggestion.available"
    REPORT_READY = "report.ready"

    # System events
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"
    SYSTEM_NOTIFICATION = "system.notification"


class SubscriptionType(str, Enum):
    """Types of subscriptions"""
    ALL = "all"
    MEMORIES = "memories"
    METRICS = "metrics"
    REVIEWS = "reviews"
    SYNTHESIS = "synthesis"
    SYSTEM = "system"


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    id: UUID = Field(default_factory=UUID)
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    data: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectionInfo(BaseModel):
    """WebSocket connection information"""
    connection_id: str
    user_id: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping: datetime = Field(default_factory=datetime.utcnow)
    subscriptions: list[SubscriptionType] = Field(default=[SubscriptionType.ALL])
    client_info: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class MemoryEvent(WebSocketMessage):
    """Memory-related event"""
    memory_id: UUID
    memory_title: str
    action: str  # "create", "update", "delete", "consolidate"
    changes: Optional[dict[str, Any]] = None
    related_memories: list[UUID] = Field(default_factory=list)


class MetricsEvent(WebSocketMessage):
    """Metrics-related event"""
    metric_name: str
    current_value: float
    previous_value: Optional[float] = None
    change_percentage: Optional[float] = None
    threshold_crossed: Optional[str] = None  # "upper", "lower"
    graph_id: str = "main"


class ReviewEvent(WebSocketMessage):
    """Review-related event"""
    review_id: Optional[UUID] = None
    memory_id: UUID
    memory_title: str
    action: str  # "due", "completed", "overdue"
    next_review: Optional[datetime] = None
    performance: Optional[str] = None  # ReviewDifficulty value
    streak_info: Optional[dict[str, int]] = None


class SynthesisEvent(WebSocketMessage):
    """Synthesis-related event"""
    synthesis_type: str  # "consolidation", "summary", "suggestion", "report"
    resource_id: UUID
    title: str
    preview: Optional[str] = None
    action_url: Optional[str] = None
    priority: float = Field(default=0.5, ge=0.0, le=1.0)


class SystemNotification(WebSocketMessage):
    """System notification"""
    severity: str = Field(..., pattern="^(info|warning|error|success)$")
    title: str
    message: str
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    auto_dismiss: bool = True
    dismiss_after_seconds: int = Field(default=5, ge=1)


class BroadcastMessage(BaseModel):
    """Message to broadcast to multiple users"""
    user_ids: list[str] = Field(default_factory=list)  # Empty = all users
    subscriptions: list[SubscriptionType] = Field(default=[SubscriptionType.ALL])
    message: WebSocketMessage
    exclude_user_ids: list[str] = Field(default_factory=list)


class MetricsSnapshot(BaseModel):
    """Real-time metrics snapshot"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: dict[str, float]
    trends: dict[str, str]  # "increasing", "decreasing", "stable"
    alerts: list[str] = Field(default_factory=list)
    graph_id: str = "main"


class ProgressUpdate(BaseModel):
    """Progress update for long-running operations"""
    operation_id: UUID
    operation_type: str  # "consolidation", "report_generation", "bulk_import"
    current_step: int
    total_steps: int
    current_step_name: str
    percentage_complete: float = Field(..., ge=0.0, le=100.0)
    estimated_time_remaining_seconds: Optional[int] = None
    can_cancel: bool = False


class CollaborationEvent(BaseModel):
    """Collaboration event (future feature)"""
    collaboration_id: UUID
    action: str  # "user_joined", "user_left", "memory_shared", "edit_started"
    actor_id: str
    actor_name: str
    affected_resources: list[dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None


class SubscriptionRequest(BaseModel):
    """Request to subscribe/unsubscribe from events"""
    action: str = Field(..., pattern="^(subscribe|unsubscribe)$")
    subscription_types: list[SubscriptionType]
    filters: Optional[dict[str, Any]] = None  # e.g., {"memory_types": ["semantic"]}


class SubscriptionResponse(BaseModel):
    """Response to subscription request"""
    success: bool
    active_subscriptions: list[SubscriptionType]
    message: Optional[str] = None


class HeartbeatMessage(BaseModel):
    """Heartbeat/ping message"""
    type: str = Field(default="ping")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: int = Field(..., ge=0)


class HeartbeatResponse(BaseModel):
    """Heartbeat/pong response"""
    type: str = Field(default="pong")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: int
    server_time: datetime = Field(default_factory=datetime.utcnow)


class ErrorMessage(BaseModel):
    """WebSocket error message"""
    error_code: str
    error_message: str
    details: Optional[dict[str, Any]] = None
    recoverable: bool = True
    suggested_action: Optional[str] = None
