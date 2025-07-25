"""
Unit tests for WebSocket models - v2.8.2
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.synthesis.websocket_models import (
    ConnectionInfo,
    ConnectionStatus,
    EventPriority,
    EventSubscription,
    EventType,
    SubscriptionRequest,
    WebSocketEvent,
    WebSocketMetrics,
)


class TestWebSocketModels:
    """Test WebSocket event models."""

    def test_event_type_enum(self):
        """Test EventType enum values."""
        # Memory events
        assert EventType.MEMORY_CREATED.value == "memory.created"
        assert EventType.MEMORY_UPDATED.value == "memory.updated"
        assert EventType.MEMORY_DELETED.value == "memory.deleted"
        assert EventType.MEMORY_ARCHIVED.value == "memory.archived"

        # Review events
        assert EventType.REVIEW_SCHEDULED.value == "review.scheduled"
        assert EventType.REVIEW_DUE.value == "review.due"
        assert EventType.REVIEW_COMPLETED.value == "review.completed"
        assert EventType.REVIEW_SKIPPED.value == "review.skipped"

        # Report events
        assert EventType.REPORT_STARTED.value == "report.started"
        assert EventType.REPORT_PROGRESS.value == "report.progress"
        assert EventType.REPORT_COMPLETED.value == "report.completed"
        assert EventType.REPORT_FAILED.value == "report.failed"

        # System events
        assert EventType.SYSTEM_ALERT.value == "system.alert"
        assert EventType.SYSTEM_UPDATE.value == "system.update"
        assert EventType.CONNECTION_STATUS.value == "connection.status"

    def test_event_priority_enum(self):
        """Test EventPriority enum values."""
        assert EventPriority.LOW.value == "low"
        assert EventPriority.NORMAL.value == "normal"
        assert EventPriority.HIGH.value == "high"
        assert EventPriority.URGENT.value == "urgent"

    def test_websocket_event_model(self):
        """Test WebSocketEvent model."""
        event = WebSocketEvent(
            id="evt_123",
            type=EventType.MEMORY_CREATED,
            priority=EventPriority.HIGH,
            data={
                "memory_id": "mem_456",
                "content": "Test memory"
            },
            user_id="user_789",
            connection_id="conn_abc",
            retry_count=0
        )

        assert event.id == "evt_123"
        assert event.type == EventType.MEMORY_CREATED
        assert event.priority == EventPriority.HIGH
        assert event.data["memory_id"] == "mem_456"
        assert event.user_id == "user_789"
        assert event.connection_id == "conn_abc"
        assert event.retry_count == 0
        assert isinstance(event.timestamp, datetime)

    def test_websocket_event_defaults(self):
        """Test WebSocketEvent default values."""
        event = WebSocketEvent(
            type=EventType.SYSTEM_UPDATE,
            data={"message": "Update available"}
        )

        assert event.id.startswith("evt_")  # Auto-generated
        assert event.priority == EventPriority.NORMAL
        assert event.user_id is None
        assert event.connection_id is None
        assert event.retry_count == 0

    def test_connection_info_model(self):
        """Test ConnectionInfo model."""
        info = ConnectionInfo(
            connection_id="conn_123",
            user_id="user_456",
            connected_at=datetime.utcnow(),
            last_ping=datetime.utcnow(),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            subscriptions=["memory.*", "report.completed"],
            metadata={"client_version": "2.0"}
        )

        assert info.connection_id == "conn_123"
        assert info.user_id == "user_456"
        assert isinstance(info.connected_at, datetime)
        assert isinstance(info.last_ping, datetime)
        assert info.ip_address == "192.168.1.1"
        assert len(info.subscriptions) == 2
        assert info.metadata["client_version"] == "2.0"

    def test_event_subscription_model(self):
        """Test EventSubscription model."""
        subscription = EventSubscription(
            id="sub_123",
            connection_id="conn_456",
            event_types=[EventType.MEMORY_CREATED, EventType.MEMORY_UPDATED],
            event_patterns=["memory.*", "review.due"],
            filters={
                "user_id": "user_789",
                "importance_min": 0.7
            },
            active=True
        )

        assert subscription.id == "sub_123"
        assert subscription.connection_id == "conn_456"
        assert len(subscription.event_types) == 2
        assert EventType.MEMORY_CREATED in subscription.event_types
        assert len(subscription.event_patterns) == 2
        assert subscription.filters["importance_min"] == 0.7
        assert subscription.active is True
        assert isinstance(subscription.created_at, datetime)

    def test_subscription_request_model(self):
        """Test SubscriptionRequest model."""
        request = SubscriptionRequest(
            event_types=[EventType.REPORT_COMPLETED, EventType.REVIEW_DUE],
            event_patterns=["system.*"],
            filters={"priority": "high"}
        )

        assert len(request.event_types) == 2
        assert EventType.REPORT_COMPLETED in request.event_types
        assert len(request.event_patterns) == 1
        assert request.filters["priority"] == "high"

    def test_subscription_request_validation(self):
        """Test SubscriptionRequest validation."""
        # Empty request should be invalid
        with pytest.raises(ValidationError):
            SubscriptionRequest()

        # At least one subscription method required
        SubscriptionRequest(event_types=[EventType.MEMORY_CREATED])  # Valid
        SubscriptionRequest(event_patterns=["memory.*"])  # Valid

        # Both methods work together
        request = SubscriptionRequest(
            event_types=[EventType.MEMORY_CREATED],
            event_patterns=["review.*"]
        )
        assert len(request.event_types) == 1
        assert len(request.event_patterns) == 1

    def test_connection_status_model(self):
        """Test ConnectionStatus model."""
        status = ConnectionStatus(
            connection_id="conn_123",
            is_connected=True,
            last_activity=datetime.utcnow(),
            subscriptions_count=5,
            events_received=100,
            events_sent=95,
            errors_count=2,
            average_latency_ms=15.5
        )

        assert status.connection_id == "conn_123"
        assert status.is_connected is True
        assert isinstance(status.last_activity, datetime)
        assert status.subscriptions_count == 5
        assert status.events_received == 100
        assert status.events_sent == 95
        assert status.errors_count == 2
        assert status.average_latency_ms == 15.5

    def test_websocket_metrics_model(self):
        """Test WebSocketMetrics model."""
        metrics = WebSocketMetrics(
            active_connections=10,
            total_connections=50,
            events_sent_total=1000,
            events_received_total=800,
            errors_total=5,
            average_latency_ms=12.3,
            subscriptions_total=25,
            connection_duration_avg_seconds=300.5,
            events_by_type={
                EventType.MEMORY_CREATED.value: 200,
                EventType.REVIEW_COMPLETED.value: 150,
                EventType.REPORT_COMPLETED.value: 50
            },
            connections_by_user={"user_1": 3, "user_2": 2, "user_3": 5}
        )

        assert metrics.active_connections == 10
        assert metrics.total_connections == 50
        assert metrics.events_sent_total == 1000
        assert metrics.events_received_total == 800
        assert metrics.errors_total == 5
        assert metrics.average_latency_ms == 12.3
        assert metrics.subscriptions_total == 25
        assert metrics.connection_duration_avg_seconds == 300.5
        assert len(metrics.events_by_type) == 3
        assert metrics.events_by_type[EventType.MEMORY_CREATED.value] == 200
        assert sum(metrics.connections_by_user.values()) == 10


class TestWebSocketModelSerialization:
    """Test model serialization and deserialization."""

    def test_websocket_event_serialization(self):
        """Test WebSocketEvent serialization."""
        event = WebSocketEvent(
            type=EventType.MEMORY_UPDATED,
            priority=EventPriority.HIGH,
            data={"memory_id": "test_123", "changes": ["content", "tags"]},
            user_id="user_456"
        )

        # Serialize
        data = event.dict()
        assert data["type"] == "memory.updated"
        assert data["priority"] == "high"
        assert data["data"]["memory_id"] == "test_123"
        assert len(data["data"]["changes"]) == 2

        # Deserialize
        event2 = WebSocketEvent(**data)
        assert event2.type == EventType.MEMORY_UPDATED
        assert event2.priority == EventPriority.HIGH

    def test_event_subscription_json_serialization(self):
        """Test EventSubscription JSON serialization."""
        subscription = EventSubscription(
            id="sub_test",
            connection_id="conn_test",
            event_types=[EventType.REPORT_STARTED, EventType.REPORT_COMPLETED],
            event_patterns=["memory.*"],
            filters={"user_id": "test_user"},
            active=True
        )

        # Serialize to JSON
        json_data = subscription.json()
        assert "sub_test" in json_data
        assert "report.started" in json_data
        assert "report.completed" in json_data

        # Parse back
        import json
        data = json.loads(json_data)
        assert data["id"] == "sub_test"
        assert len(data["event_types"]) == 2
        assert data["active"] is True

    def test_websocket_metrics_serialization(self):
        """Test WebSocketMetrics serialization."""
        metrics = WebSocketMetrics(
            active_connections=5,
            total_connections=20,
            events_sent_total=500,
            events_by_type={
                EventType.MEMORY_CREATED.value: 100,
                EventType.REVIEW_DUE.value: 50
            }
        )

        # Serialize
        data = metrics.dict()
        assert data["active_connections"] == 5
        assert data["total_connections"] == 20
        assert data["events_sent_total"] == 500
        assert len(data["events_by_type"]) == 2

        # Deserialize
        metrics2 = WebSocketMetrics(**data)
        assert metrics2.active_connections == 5
        assert metrics2.events_by_type["memory.created"] == 100

    def test_event_patterns_validation(self):
        """Test event pattern validation in subscriptions."""
        # Valid patterns
        valid_patterns = [
            "memory.*",
            "review.*",
            "report.completed",
            "system.alert",
            "*"  # Subscribe to all
        ]

        for pattern in valid_patterns:
            subscription = EventSubscription(
                id="test",
                connection_id="test",
                event_patterns=[pattern]
            )
            assert pattern in subscription.event_patterns

    def test_connection_info_with_datetime(self):
        """Test ConnectionInfo with datetime handling."""
        now = datetime.utcnow()
        info = ConnectionInfo(
            connection_id="test",
            user_id="user",
            connected_at=now,
            last_ping=now
        )

        # Serialize and deserialize
        data = info.dict()
        info2 = ConnectionInfo(**data)

        # Datetimes should be preserved
        assert info2.connected_at == info.connected_at
        assert info2.last_ping == info.last_ping
