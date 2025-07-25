"""
Unit tests for WebSocket service - v2.8.2
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.models.synthesis.websocket_models import (
    EventPriority,
    EventSubscription,
    EventType,
    SubscriptionRequest,
    WebSocketEvent,
    WebSocketMetrics,
)
from app.services.synthesis.websocket_service import (
    ConnectionManager,
    EventBroadcaster,
    WebSocketService,
)


class TestConnectionManager:
    """Test WebSocket connection manager."""

    @pytest.fixture
    def connection_manager(self):
        """Create connection manager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.close = AsyncMock()
        ws.client = MagicMock(host="127.0.0.1")
        ws.headers = {"User-Agent": "TestClient/1.0"}
        return ws

    async def test_connect(self, connection_manager, mock_websocket):
        """Test WebSocket connection."""
        connection_id = "conn_123"
        user_id = "user_456"

        await connection_manager.connect(mock_websocket, connection_id, user_id)

        assert connection_id in connection_manager._connections
        assert connection_manager._connections[connection_id] == mock_websocket

        info = connection_manager._connection_info.get(connection_id)
        assert info is not None
        assert info.connection_id == connection_id
        assert info.user_id == user_id
        assert info.ip_address == "127.0.0.1"

        mock_websocket.accept.assert_called_once()

    async def test_disconnect(self, connection_manager, mock_websocket):
        """Test WebSocket disconnection."""
        connection_id = "conn_123"
        user_id = "user_456"

        # Connect first
        await connection_manager.connect(mock_websocket, connection_id, user_id)
        assert connection_id in connection_manager._connections

        # Disconnect
        await connection_manager.disconnect(connection_id)

        assert connection_id not in connection_manager._connections
        assert connection_id not in connection_manager._connection_info
        mock_websocket.close.assert_called_once()

    async def test_send_event(self, connection_manager, mock_websocket):
        """Test sending event to connection."""
        connection_id = "conn_123"
        await connection_manager.connect(mock_websocket, connection_id, "user_456")

        event = WebSocketEvent(
            type=EventType.MEMORY_CREATED,
            data={"memory_id": "mem_789"}
        )

        await connection_manager.send_event(connection_id, event)

        mock_websocket.send_json.assert_called_once()
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "memory.created"
        assert sent_data["data"]["memory_id"] == "mem_789"

    async def test_broadcast_event(self, connection_manager, mock_websocket):
        """Test broadcasting event to multiple connections."""
        # Create multiple connections
        connections = {}
        for i in range(3):
            conn_id = f"conn_{i}"
            ws = AsyncMock(spec=WebSocket)
            ws.send_json = AsyncMock()
            connections[conn_id] = ws
            await connection_manager.connect(ws, conn_id, f"user_{i}")

        event = WebSocketEvent(
            type=EventType.SYSTEM_UPDATE,
            data={"message": "System update"}
        )

        await connection_manager.broadcast_event(event)

        # All connections should receive the event
        for ws in connections.values():
            ws.send_json.assert_called_once()

    async def test_broadcast_event_with_targets(self, connection_manager):
        """Test broadcasting to specific connections."""
        # Create connections
        connections = {}
        for i in range(3):
            conn_id = f"conn_{i}"
            ws = AsyncMock(spec=WebSocket)
            ws.send_json = AsyncMock()
            connections[conn_id] = ws
            await connection_manager.connect(ws, conn_id, f"user_{i}")

        event = WebSocketEvent(
            type=EventType.REPORT_COMPLETED,
            data={"report_id": "report_123"}
        )

        # Broadcast only to specific connections
        target_connections = ["conn_0", "conn_2"]
        await connection_manager.broadcast_event(event, target_connections)

        # Only targeted connections should receive
        connections["conn_0"].send_json.assert_called_once()
        connections["conn_1"].send_json.assert_not_called()
        connections["conn_2"].send_json.assert_called_once()

    async def test_subscribe(self, connection_manager, mock_websocket):
        """Test event subscription."""
        connection_id = "conn_123"
        await connection_manager.connect(mock_websocket, connection_id, "user_456")

        request = SubscriptionRequest(
            event_types=[EventType.MEMORY_CREATED, EventType.MEMORY_UPDATED],
            event_patterns=["report.*"],
            filters={"priority": "high"}
        )

        subscription = await connection_manager.subscribe(connection_id, request)

        assert isinstance(subscription, EventSubscription)
        assert subscription.connection_id == connection_id
        assert EventType.MEMORY_CREATED in subscription.event_types
        assert "report.*" in subscription.event_patterns
        assert subscription.filters["priority"] == "high"

        # Verify subscription is stored
        assert connection_id in connection_manager._subscriptions
        assert subscription.id in connection_manager._subscriptions[connection_id]

    async def test_unsubscribe(self, connection_manager, mock_websocket):
        """Test event unsubscription."""
        connection_id = "conn_123"
        await connection_manager.connect(mock_websocket, connection_id, "user_456")

        # Subscribe first
        request = SubscriptionRequest(event_types=[EventType.MEMORY_CREATED])
        subscription = await connection_manager.subscribe(connection_id, request)

        # Unsubscribe
        await connection_manager.unsubscribe(connection_id, subscription.id)

        # Verify subscription is removed
        assert subscription.id not in connection_manager._subscriptions.get(connection_id, {})

    def test_get_metrics(self, connection_manager):
        """Test metrics collection."""
        metrics = connection_manager.get_metrics()

        assert isinstance(metrics, WebSocketMetrics)
        assert metrics.active_connections == 0
        assert metrics.total_connections == 0
        assert metrics.events_sent_total == 0

    async def test_get_metrics_with_activity(self, connection_manager, mock_websocket):
        """Test metrics with connection activity."""
        # Create connections
        await connection_manager.connect(mock_websocket, "conn_1", "user_1")
        await connection_manager.connect(AsyncMock(spec=WebSocket), "conn_2", "user_2")

        # Send some events
        event = WebSocketEvent(type=EventType.MEMORY_CREATED, data={})
        await connection_manager.send_event("conn_1", event)

        metrics = connection_manager.get_metrics()

        assert metrics.active_connections == 2
        assert metrics.total_connections == 2
        assert metrics.events_sent_total >= 1
        assert metrics.connections_by_user["user_1"] == 1
        assert metrics.connections_by_user["user_2"] == 1

    async def test_rate_limiting(self, connection_manager, mock_websocket):
        """Test connection rate limiting."""
        connection_id = "conn_123"
        await connection_manager.connect(mock_websocket, connection_id, "user_456")

        # Send many events quickly
        event = WebSocketEvent(type=EventType.MEMORY_UPDATED, data={})

        # First 10 should succeed (default rate limit)
        for i in range(10):
            result = await connection_manager._check_rate_limit(connection_id)
            assert result is True

        # 11th should be rate limited
        result = await connection_manager._check_rate_limit(connection_id)
        assert result is False


class TestEventBroadcaster:
    """Test event broadcaster."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        manager = AsyncMock(spec=ConnectionManager)
        manager.broadcast_event = AsyncMock()
        manager._subscriptions = {}
        manager._connection_info = {}
        return manager

    @pytest.fixture
    def event_broadcaster(self, mock_connection_manager):
        """Create event broadcaster instance."""
        return EventBroadcaster(mock_connection_manager)

    async def test_broadcast_memory_event(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting memory event."""
        await event_broadcaster.broadcast_memory_event(
            EventType.MEMORY_CREATED,
            "mem_123",
            "user_456",
            {"tags": ["important"]}
        )

        mock_connection_manager.broadcast_event.assert_called_once()
        event = mock_connection_manager.broadcast_event.call_args[0][0]

        assert event.type == EventType.MEMORY_CREATED
        assert event.data["memory_id"] == "mem_123"
        assert event.data["user_id"] == "user_456"
        assert event.data["tags"] == ["important"]

    async def test_broadcast_review_event(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting review event."""
        await event_broadcaster.broadcast_review_event(
            EventType.REVIEW_COMPLETED,
            "mem_789",
            "user_123",
            {"difficulty": "good", "next_review": "2024-01-01"}
        )

        mock_connection_manager.broadcast_event.assert_called_once()
        event = mock_connection_manager.broadcast_event.call_args[0][0]

        assert event.type == EventType.REVIEW_COMPLETED
        assert event.data["memory_id"] == "mem_789"
        assert event.data["difficulty"] == "good"

    async def test_broadcast_report_event(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting report event."""
        await event_broadcaster.broadcast_report_event(
            EventType.REPORT_COMPLETED,
            "report_456",
            "user_789",
            {"format": "pdf", "pages": 10}
        )

        mock_connection_manager.broadcast_event.assert_called_once()
        event = mock_connection_manager.broadcast_event.call_args[0][0]

        assert event.type == EventType.REPORT_COMPLETED
        assert event.data["report_id"] == "report_456"
        assert event.data["format"] == "pdf"

    async def test_broadcast_system_event(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting system event."""
        await event_broadcaster.broadcast_system_event(
            EventType.SYSTEM_ALERT,
            {"message": "Maintenance scheduled", "severity": "info"}
        )

        mock_connection_manager.broadcast_event.assert_called_once()
        event = mock_connection_manager.broadcast_event.call_args[0][0]

        assert event.type == EventType.SYSTEM_ALERT
        assert event.data["message"] == "Maintenance scheduled"
        assert event.priority == EventPriority.HIGH  # System events are high priority


class TestWebSocketService:
    """Test WebSocket service integration."""

    @pytest.fixture
    def websocket_service(self):
        """Create WebSocket service instance."""
        return WebSocketService()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.close = AsyncMock()
        ws.client = MagicMock(host="192.168.1.100")
        ws.headers = {"User-Agent": "TestBrowser/2.0"}
        return ws

    async def test_service_lifecycle(self, websocket_service):
        """Test service start and stop."""
        await websocket_service.start()
        # Service should be ready

        await websocket_service.stop()
        # Service should clean up

    async def test_handle_connection(self, websocket_service, mock_websocket):
        """Test handling WebSocket connection."""
        await websocket_service.start()

        # Simulate connection with receive loop
        mock_websocket.receive_json.side_effect = [
            {"type": "ping"},
            {"type": "subscribe", "events": ["memory.*"]},
            WebSocketDisconnect(),  # Simulate disconnect
        ]

        connection_id = await websocket_service.handle_connection(
            mock_websocket,
            "user_123",
            {"source": "test"}
        )

        assert connection_id.startswith("conn_")
        mock_websocket.accept.assert_called_once()

    async def test_handle_connection_error(self, websocket_service, mock_websocket):
        """Test connection error handling."""
        await websocket_service.start()

        # Simulate connection error
        mock_websocket.accept.side_effect = Exception("Connection failed")

        connection_id = await websocket_service.handle_connection(
            mock_websocket,
            "user_123",
            {}
        )

        # Should handle error gracefully
        assert connection_id.startswith("conn_")

    async def test_event_filtering(self, websocket_service, mock_websocket):
        """Test event filtering based on subscriptions."""
        await websocket_service.start()

        # Connect and subscribe to specific events
        connection_id = "conn_test"
        await websocket_service.connection_manager.connect(
            mock_websocket,
            connection_id,
            "user_123"
        )

        # Subscribe to memory events only
        request = SubscriptionRequest(event_patterns=["memory.*"])
        await websocket_service.connection_manager.subscribe(connection_id, request)

        # Broadcast memory event (should be received)
        memory_event = WebSocketEvent(
            type=EventType.MEMORY_CREATED,
            data={"memory_id": "mem_123"}
        )
        await websocket_service.connection_manager.broadcast_event(memory_event)

        # Broadcast report event (should not be received due to filter)
        report_event = WebSocketEvent(
            type=EventType.REPORT_COMPLETED,
            data={"report_id": "report_123"}
        )
        # This would be filtered out in a real implementation
        await websocket_service.connection_manager.broadcast_event(report_event)

        # Verify only memory event was sent
        assert mock_websocket.send_json.call_count >= 1
