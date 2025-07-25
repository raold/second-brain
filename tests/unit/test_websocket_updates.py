"""
Comprehensive tests for WebSocket real-time updates
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.websockets import WebSocketState

from app.models.synthesis.websocket_models import (
    BroadcastMessage,
    EventType,
    SubscriptionRequest,
    SubscriptionType,
    SystemNotification,
)
from app.services.synthesis.websocket_service import WebSocketService


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages_sent = []
        self.state = WebSocketState.CONNECTED
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        self.messages_sent.append(data)

    async def receive_json(self):
        # Simulate receiving messages
        return {"type": "ping", "sequence": 1}

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.state = WebSocketState.DISCONNECTED


@pytest.fixture
async def websocket_service():
    """Create a WebSocket service instance with mocked database."""
    mock_db = AsyncMock()
    service = WebSocketService(mock_db)
    return service, mock_db


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    return MockWebSocket()


class TestConnectionManager:
    """Test suite for WebSocket connection management."""

    async def test_connection_lifecycle(self, websocket_service, mock_websocket):
        """Test WebSocket connection lifecycle."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        # Test connection
        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        assert connection_id in service.connection_manager.active_connections
        assert user_id in service.connection_manager.user_connections
        assert connection_id in service.connection_manager.user_connections[user_id]

        # Test disconnection
        await service.connection_manager.disconnect(connection_id)

        assert connection_id not in service.connection_manager.active_connections
        assert connection_id not in service.connection_manager.user_connections.get(user_id, set())

    async def test_multiple_connections_per_user(self, websocket_service):
        """Test handling multiple connections per user."""
        service, mock_db = websocket_service
        user_id = "test_user"

        # Create multiple connections
        connections = []
        for i in range(3):
            ws = MockWebSocket()
            conn_id = f"conn_{i}"
            await service.connection_manager.connect(ws, user_id, conn_id)
            connections.append((ws, conn_id))

        # Verify all connections are tracked
        assert len(service.connection_manager.user_connections[user_id]) == 3

        # Test broadcasting to user
        message = BroadcastMessage(
            event_type=EventType.MEMORY_CREATED,
            data={"test": "data"},
            user_ids=[user_id]
        )

        await service.connection_manager.broadcast(message)

        # All connections should receive the message
        for ws, _ in connections:
            assert len(ws.messages_sent) == 1
            assert ws.messages_sent[0]["type"] == EventType.MEMORY_CREATED.value

    async def test_subscription_management(self, websocket_service, mock_websocket):
        """Test event subscription management."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.MEMORIES, SubscriptionType.METRICS]
        )

        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        conn_info = service.connection_manager.active_connections[connection_id]
        assert SubscriptionType.MEMORIES in conn_info.subscriptions
        assert SubscriptionType.METRICS in conn_info.subscriptions

        # Unsubscribe from one type
        unsub_request = SubscriptionRequest(
            action="unsubscribe",
            subscription_types=[SubscriptionType.METRICS]
        )

        await service.connection_manager.update_subscriptions(connection_id, unsub_request)

        assert SubscriptionType.MEMORIES in conn_info.subscriptions
        assert SubscriptionType.METRICS not in conn_info.subscriptions

    async def test_targeted_broadcasting(self, websocket_service):
        """Test targeted message broadcasting."""
        service, mock_db = websocket_service

        # Setup multiple users with different subscriptions
        users = [
            ("user1", "conn1", [SubscriptionType.MEMORIES]),
            ("user2", "conn2", [SubscriptionType.REVIEWS]),
            ("user3", "conn3", [SubscriptionType.MEMORIES, SubscriptionType.REVIEWS])
        ]

        for user_id, conn_id, subs in users:
            ws = MockWebSocket()
            await service.connection_manager.connect(ws, user_id, conn_id)

            sub_request = SubscriptionRequest(
                action="subscribe",
                subscription_types=subs
            )
            await service.connection_manager.update_subscriptions(conn_id, sub_request)

        # Broadcast memory event
        memory_message = BroadcastMessage(
            event_type=EventType.MEMORY_CREATED,
            data={"memory": "data"},
            subscription_type=SubscriptionType.MEMORIES
        )

        await service.connection_manager.broadcast(memory_message)

        # Only users subscribed to memories should receive it
        conn1 = service.connection_manager.active_connections["conn1"]
        conn2 = service.connection_manager.active_connections["conn2"]
        conn3 = service.connection_manager.active_connections["conn3"]

        assert len(conn1.websocket.messages_sent) == 1
        assert len(conn2.websocket.messages_sent) == 0
        assert len(conn3.websocket.messages_sent) == 1

    async def test_heartbeat_mechanism(self, websocket_service, mock_websocket):
        """Test WebSocket heartbeat mechanism."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Send ping
        ping_message = {"type": "ping", "sequence": 123}
        response = await service.connection_manager.handle_heartbeat(connection_id, ping_message)

        assert response["type"] == "pong"
        assert response["sequence"] == 123

        # Update last activity
        conn_info = service.connection_manager.active_connections[connection_id]
        assert conn_info.last_activity > conn_info.connected_at

    async def test_connection_cleanup(self, websocket_service):
        """Test automatic connection cleanup."""
        service, mock_db = websocket_service

        # Create stale connection
        stale_ws = MockWebSocket()
        stale_id = "stale_conn"
        await service.connection_manager.connect(stale_ws, "user1", stale_id)

        # Manually set last activity to old time
        conn_info = service.connection_manager.active_connections[stale_id]
        conn_info.last_activity = datetime.utcnow().timestamp() - 3600  # 1 hour ago

        # Run cleanup
        await service.connection_manager.cleanup_stale_connections()

        assert stale_id not in service.connection_manager.active_connections
        assert stale_ws.closed


class TestWebSocketEvents:
    """Test suite for WebSocket event handling."""

    async def test_memory_events(self, websocket_service, mock_websocket):
        """Test memory-related WebSocket events."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to memory events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.MEMORIES]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Test memory created event
        memory_id = uuid4()
        await service.emit_memory_event(
            user_id=user_id,
            memory_id=memory_id,
            action="created",
            memory_data={"title": "Test Memory", "content": "Test content"}
        )

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.MEMORY_CREATED.value
        assert message["data"]["memory_id"] == str(memory_id)

    async def test_review_events(self, websocket_service, mock_websocket):
        """Test review-related WebSocket events."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to review events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.REVIEWS]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Test review due event
        await service.emit_review_event(
            user_id=user_id,
            memory_id=uuid4(),
            memory_title="Test Memory",
            action="due",
            review_id=uuid4(),
            next_review=datetime.utcnow()
        )

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.REVIEW_DUE.value
        assert "memory_title" in message["data"]

    async def test_metrics_events(self, websocket_service, mock_websocket):
        """Test metrics-related WebSocket events."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to metrics events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.METRICS]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Test metrics update event
        await service.emit_metrics_event(
            user_id=user_id,
            metrics_type="graph_density",
            current_value=0.65,
            previous_value=0.60,
            change_percentage=8.33
        )

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.METRICS_UPDATED.value
        assert message["data"]["current_value"] == 0.65

    async def test_synthesis_events(self, websocket_service, mock_websocket):
        """Test synthesis-related WebSocket events."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to synthesis events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.SYNTHESIS]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Test consolidation suggested event
        await service.emit_synthesis_event(
            user_id=user_id,
            synthesis_type="consolidation",
            resource_id=uuid4(),
            title="Related Memories Found",
            preview="5 memories about Python found...",
            action_url="/consolidate/123"
        )

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.CONSOLIDATION_SUGGESTED.value
        assert message["data"]["title"] == "Related Memories Found"

    async def test_system_notifications(self, websocket_service, mock_websocket):
        """Test system notification events."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # System notifications are always sent
        notification = SystemNotification(
            level="info",
            title="System Update",
            message="New features available",
            action_label="Learn More",
            action_url="/updates"
        )

        await service.broadcast_system_notification(notification, [user_id])

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.SYSTEM_NOTIFICATION.value
        assert message["data"]["title"] == "System Update"


class TestWebSocketPerformance:
    """Test suite for WebSocket performance and scalability."""

    async def test_concurrent_connections(self, websocket_service):
        """Test handling many concurrent connections."""
        service, mock_db = websocket_service
        num_connections = 100

        # Create many connections
        tasks = []
        for i in range(num_connections):
            ws = MockWebSocket()
            user_id = f"user_{i % 10}"  # 10 users, multiple connections each
            conn_id = f"conn_{i}"
            tasks.append(service.connection_manager.connect(ws, user_id, conn_id))

        await asyncio.gather(*tasks)

        # Verify all connections
        assert len(service.connection_manager.active_connections) == num_connections
        assert len(service.connection_manager.user_connections) == 10

        # Test broadcasting to all
        message = BroadcastMessage(
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={"message": "Global notification"}
        )

        await service.connection_manager.broadcast(message)

        # All connections should receive the message
        total_messages = sum(
            len(conn.websocket.messages_sent)
            for conn in service.connection_manager.active_connections.values()
        )
        assert total_messages == num_connections

    async def test_message_queue_handling(self, websocket_service):
        """Test message queue handling under load."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        ws = MockWebSocket()
        await service.connection_manager.connect(ws, user_id, connection_id)

        # Send many messages rapidly
        messages_to_send = 50
        tasks = []

        for i in range(messages_to_send):
            message = BroadcastMessage(
                event_type=EventType.MEMORY_UPDATED,
                data={"update": i},
                user_ids=[user_id]
            )
            tasks.append(service.connection_manager.broadcast(message))

        await asyncio.gather(*tasks)

        # All messages should be delivered
        assert len(ws.messages_sent) == messages_to_send

    async def test_connection_pool_limits(self, websocket_service):
        """Test connection pool limits and behavior."""
        service, mock_db = websocket_service

        # Set connection limit
        service.connection_manager.max_connections_per_user = 3

        user_id = "test_user"
        connections = []

        # Create connections up to limit
        for i in range(3):
            ws = MockWebSocket()
            conn_id = f"conn_{i}"
            await service.connection_manager.connect(ws, user_id, conn_id)
            connections.append(conn_id)

        # Try to create one more
        ws_extra = MockWebSocket()
        conn_extra = "conn_extra"

        # Should disconnect oldest connection
        await service.connection_manager.connect(ws_extra, user_id, conn_extra)

        # Verify oldest was disconnected
        assert connections[0] not in service.connection_manager.active_connections
        assert conn_extra in service.connection_manager.active_connections


class TestWebSocketAPI:
    """Test suite for WebSocket API endpoints."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_client):
        """Test WebSocket connection endpoint."""
        # WebSocket testing requires special handling
        # This is a placeholder for WebSocket endpoint testing
        pass

    @pytest.mark.asyncio
    async def test_websocket_status_endpoint(self, test_client):
        """Test WebSocket status endpoint."""
        response = await test_client.get(
            "/ws/status",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        status = response.json()
        assert "status" in status
        assert "statistics" in status
        assert status["status"] == "active"


class TestWebSocketIntegration:
    """Test suite for WebSocket integration with other features."""

    async def test_memory_creation_notification(self, websocket_service, mock_websocket):
        """Test real-time notification on memory creation."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to all events
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.ALL]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Simulate memory creation
        memory_data = {
            "id": str(uuid4()),
            "title": "New Memory",
            "content": "This is a new memory",
            "created_at": datetime.utcnow().isoformat()
        }

        await service.emit_memory_event(
            user_id=user_id,
            memory_id=UUID(memory_data["id"]),
            action="created",
            memory_data=memory_data
        )

        # Check notification
        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.MEMORY_CREATED.value
        assert message["data"]["memory_data"]["title"] == "New Memory"

    async def test_review_completion_streak_update(self, websocket_service, mock_websocket):
        """Test streak update notification on review completion."""
        service, mock_db = websocket_service
        user_id = "test_user"
        connection_id = str(uuid4())

        await service.connection_manager.connect(mock_websocket, user_id, connection_id)

        # Subscribe to reviews
        sub_request = SubscriptionRequest(
            action="subscribe",
            subscription_types=[SubscriptionType.REVIEWS]
        )
        await service.connection_manager.update_subscriptions(connection_id, sub_request)

        # Complete a review with streak info
        await service.emit_review_event(
            user_id=user_id,
            memory_id=uuid4(),
            memory_title="Test Memory",
            action="completed",
            review_id=uuid4(),
            next_review=datetime.utcnow() + timedelta(days=2),
            performance="good",
            streak_info={"current_streak": 10, "longest_streak": 15}
        )

        assert len(mock_websocket.messages_sent) == 1
        message = mock_websocket.messages_sent[0]
        assert message["type"] == EventType.REVIEW_COMPLETED.value
        assert message["data"]["streak_info"]["current_streak"] == 10
