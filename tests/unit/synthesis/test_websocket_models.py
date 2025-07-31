"""
Test websocket models for synthesis features
"""

from datetime import datetime

from app.models.synthesis.websocket_models import (
    BroadcastMessage,
    ConnectionStatus,
    EventPriority,
    SubscriptionRequest,
    WebSocketEvent,
)


class TestWebSocketModels:
    """Test synthesis websocket models"""

    def test_broadcast_message_creation(self):
        """Test creating a broadcast message"""
        message = BroadcastMessage(
            event_type="memory_update",
            priority=EventPriority.HIGH,
            data={"memory_id": "mem-123", "action": "created"},
            broadcast_to=["user-456", "user-789"],
            timestamp=datetime.utcnow()
        )

        assert message.event_type == "memory_update"
        assert message.priority == EventPriority.HIGH
        assert message.data["memory_id"] == "mem-123"
        assert len(message.broadcast_to) == 2
        assert message.timestamp is not None

    def test_websocket_event_creation(self):
        """Test creating a websocket event"""
        event = WebSocketEvent(
            id="event-123",
            type="synthesis_complete",
            payload={
                "synthesis_id": "syn-456",
                "result": "success",
                "insights_count": 5
            },
            created_at=datetime.utcnow()
        )

        assert event.id == "event-123"
        assert event.type == "synthesis_complete"
        assert event.payload["synthesis_id"] == "syn-456"
        assert event.payload["insights_count"] == 5
        assert event.created_at is not None

    def test_connection_status(self):
        """Test connection status tracking"""
        status = ConnectionStatus(
            client_id="client-789",
            connected=True,
            connected_at=datetime.utcnow(),
            last_ping=datetime.utcnow(),
            subscriptions=["memory_updates", "synthesis_results"]
        )

        assert status.client_id == "client-789"
        assert status.connected is True
        assert status.connected_at is not None
        assert status.last_ping is not None
        assert len(status.subscriptions) == 2
        assert "memory_updates" in status.subscriptions

    def test_subscription_request(self):
        """Test subscription request"""
        request = SubscriptionRequest(
            client_id="client-999",
            event_types=["memory_created", "memory_updated", "synthesis_complete"],
            filters={
                "user_id": "user-123",
                "memory_types": ["semantic", "episodic"]
            }
        )

        assert request.client_id == "client-999"
        assert len(request.event_types) == 3
        assert "synthesis_complete" in request.event_types
        assert request.filters["user_id"] == "user-123"
        assert len(request.filters["memory_types"]) == 2

    def test_event_priority_ordering(self):
        """Test event priority ordering"""
        # Verify priority levels exist and are ordered correctly
        assert EventPriority.LOW < EventPriority.MEDIUM
        assert EventPriority.MEDIUM < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL
