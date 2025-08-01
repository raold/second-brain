"""
Unit tests for WebSocket functionality
Tests WebSocket connection handling, message broadcasting, and real-time updates
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from app.models.synthesis.websocket_models import (
    BroadcastMessage,
    ConnectionInfo,
    ConnectionState,
    ConnectionStatus,
    EventPriority,
    EventSubscription,
    EventType,
    SubscriptionRequest,
    WebSocketEvent,
    WebSocketMessage,
    WebSocketMetrics,
)
from app.services.synthesis.websocket_service import (
    ConnectionManager,
    EventBroadcaster,
    WebSocketService,
    get_websocket_service,
)


class TestWebSocketModels:
    """Test WebSocket data models"""

    def test_broadcast_message_model(self):
        """Test BroadcastMessage model"""
        message = BroadcastMessage(
            event_type="test.event",
            payload={"key": "value"},
            priority=EventPriority.HIGH
        )
        
        assert message.event_type == "test.event"
        assert message.payload == {"key": "value"}
        assert message.priority == EventPriority.HIGH
        assert isinstance(message.timestamp, datetime)

    def test_broadcast_message_with_data_field(self):
        """Test BroadcastMessage model with data field (compatibility)"""
        message = BroadcastMessage(
            event_type="test.event",
            data={"key": "value"}
        )
        
        assert message.event_type == "test.event"
        assert message.data == {"key": "value"}

    def test_websocket_event_model(self):
        """Test WebSocketEvent model"""
        event = WebSocketEvent(
            id="event-123",
            type="memory.created",
            resource_type="memory",
            resource_id="mem-456",
            user_id="user-789",
            data={"content": "test memory"},
            broadcast=True
        )
        
        assert event.id == "event-123"
        assert event.type == "memory.created"
        assert event.resource_type == "memory"
        assert event.resource_id == "mem-456"
        assert event.user_id == "user-789"
        assert event.data == {"content": "test memory"}
        assert event.broadcast is True

    def test_websocket_message_model(self):
        """Test WebSocketMessage model"""
        event = WebSocketEvent(id="event-123", type="test.event")
        message = WebSocketMessage(
            type="event",
            event=event,
            success=True
        )
        
        assert message.type == "event"
        assert message.event.id == "event-123"
        assert message.success is True
        assert isinstance(message.timestamp, datetime)

    def test_subscription_request_model(self):
        """Test SubscriptionRequest model"""
        request = SubscriptionRequest(
            client_id="client-123",
            event_types=["memory.created", "memory.updated"],
            action="subscribe",
            channels=["user.channel"],
            include_historical=True
        )
        
        assert request.client_id == "client-123"
        assert "memory.created" in request.event_types
        assert request.action == "subscribe"
        assert "user.channel" in request.channels
        assert request.include_historical is True

    def test_subscription_request_validation(self):
        """Test SubscriptionRequest validation"""
        with pytest.raises(ValueError):
            SubscriptionRequest(
                event_types=["test.event"],
                action="invalid_action"  # Should fail validation
            )

    def test_event_subscription_model(self):
        """Test EventSubscription model"""
        subscription = EventSubscription(
            id="sub-123",
            user_id="user-456",
            connection_id="conn-789",
            event_types=[EventType.MEMORY_CREATED, EventType.MEMORY_UPDATED]
        )
        
        assert subscription.id == "sub-123"
        assert subscription.user_id == "user-456"
        assert subscription.connection_id == "conn-789"
        assert EventType.MEMORY_CREATED in subscription.event_types
        assert subscription.active is True

    def test_connection_info_model(self):
        """Test ConnectionInfo model"""
        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id="user-456",
            status=ConnectionState.CONNECTED,
            client_version="1.0.0"
        )
        
        assert connection.connection_id == "conn-123"
        assert connection.user_id == "user-456"
        assert connection.status == ConnectionState.CONNECTED
        assert connection.client_version == "1.0.0"
        assert isinstance(connection.connected_at, datetime)

    def test_websocket_metrics_model(self):
        """Test WebSocketMetrics model"""
        metrics = WebSocketMetrics(
            total_connections=10,
            authenticated_connections=8,
            messages_per_second=5.2,
            average_latency_ms=150.0
        )
        
        assert metrics.total_connections == 10
        assert metrics.authenticated_connections == 8
        assert metrics.messages_per_second == 5.2
        assert metrics.average_latency_ms == 150.0

    def test_connection_status_model(self):
        """Test ConnectionStatus model (test compatibility)"""
        status = ConnectionStatus(
            client_id="client-123",
            connected=True,
            subscriptions=["memory.created", "system.status"]
        )
        
        assert status.client_id == "client-123"
        assert status.connected is True
        assert "memory.created" in status.subscriptions


class TestConnectionManager:
    """Test the WebSocket connection manager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_websocket(self):
        """Test connecting a WebSocket"""
        mock_websocket = AsyncMock()
        connection_id = "conn-123"
        user_id = "user-456"
        
        await self.manager.connect(mock_websocket, connection_id, user_id)
        
        mock_websocket.accept.assert_called_once()
        assert connection_id in self.manager.active_connections
        assert self.manager.active_connections[connection_id] == mock_websocket
        assert user_id in self.manager.user_connections
        assert connection_id in self.manager.user_connections[user_id]

    def test_disconnect_websocket(self):
        """Test disconnecting a WebSocket"""
        connection_id = "conn-123"
        user_id = "user-456"
        mock_websocket = MagicMock()
        
        # Set up connection
        self.manager.active_connections[connection_id] = mock_websocket
        self.manager.user_connections[user_id] = {connection_id}
        
        self.manager.disconnect(connection_id)
        
        assert connection_id not in self.manager.active_connections
        assert connection_id not in self.manager.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_send_message_to_connection(self):
        """Test sending a message to a specific connection"""
        connection_id = "conn-123"
        mock_websocket = AsyncMock()
        self.manager.active_connections[connection_id] = mock_websocket
        
        test_message = "Test message"
        await self.manager.send_message(connection_id, test_message)
        
        mock_websocket.send_text.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_connection(self):
        """Test sending a message to a nonexistent connection"""
        # Should not raise an error
        await self.manager.send_message("nonexistent", "message")

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting a message to all connections"""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        self.manager.active_connections = {
            "conn-1": mock_ws1,
            "conn-2": mock_ws2
        }
        
        test_message = "Broadcast message"
        await self.manager.broadcast(test_message)
        
        mock_ws1.send_text.assert_called_once_with(test_message)
        mock_ws2.send_text.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_broadcast_with_failed_connection(self):
        """Test broadcasting handles failed connections"""
        mock_ws_good = AsyncMock()
        mock_ws_bad = AsyncMock()
        mock_ws_bad.send_text.side_effect = Exception("Connection failed")
        
        self.manager.active_connections = {
            "conn-good": mock_ws_good,
            "conn-bad": mock_ws_bad
        }
        
        await self.manager.broadcast("test message")
        
        mock_ws_good.send_text.assert_called_once()
        mock_ws_bad.send_text.assert_called_once()
        # Should log error but continue


class TestEventBroadcaster:
    """Test the event broadcaster"""

    def setup_method(self):
        """Set up test fixtures"""
        self.connection_manager = ConnectionManager()
        self.broadcaster = EventBroadcaster(self.connection_manager)

    @pytest.mark.asyncio
    async def test_broadcast_event(self):
        """Test broadcasting an event"""
        mock_websocket = AsyncMock()
        self.connection_manager.active_connections = {"conn-1": mock_websocket}
        
        event_type = "memory.created"
        event_data = {"memory_id": "mem-123", "content": "test"}
        
        await self.broadcaster.broadcast_event(event_type, event_data)
        
        mock_websocket.send_text.assert_called_once()
        # Verify the message format
        call_args = mock_websocket.send_text.call_args[0][0]
        assert event_type in call_args
        assert "mem-123" in call_args


class TestWebSocketService:
    """Test the main WebSocket service"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = WebSocketService()

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test WebSocket service initialization"""
        assert isinstance(self.service.connection_manager, ConnectionManager)
        assert isinstance(self.service.event_broadcaster, EventBroadcaster)
        assert isinstance(self.service.active_subscriptions, dict)

    @pytest.mark.asyncio
    async def test_handle_connection_success(self):
        """Test handling a successful WebSocket connection"""
        mock_websocket = AsyncMock()
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()
        
        connection_id = "conn-123"
        user_id = "user-456"
        
        # This should not raise an exception
        await self.service.handle_connection(mock_websocket, connection_id, user_id)
        
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_connection_with_messages(self):
        """Test handling connection with incoming messages"""
        mock_websocket = AsyncMock()
        # Simulate receiving a message then disconnecting
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            WebSocketDisconnect()
        ]
        
        connection_id = "conn-123"
        
        await self.service.handle_connection(mock_websocket, connection_id)
        
        mock_websocket.accept.assert_called_once()
        assert mock_websocket.receive_text.call_count == 2

    @pytest.mark.asyncio
    async def test_send_notification_to_user(self):
        """Test sending notification to a specific user"""
        # Set up a user connection
        user_id = "user-123"
        connection_id = "conn-456"
        mock_websocket = AsyncMock()
        
        self.service.connection_manager.active_connections[connection_id] = mock_websocket
        self.service.connection_manager.user_connections[user_id] = {connection_id}
        
        notification = {"type": "notification", "message": "Test notification"}
        
        await self.service.send_notification(user_id, notification)
        
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_to_nonexistent_user(self):
        """Test sending notification to a user with no connections"""
        notification = {"type": "notification", "message": "Test"}
        
        # Should not raise an error
        await self.service.send_notification("nonexistent-user", notification)

    def test_get_metrics(self):
        """Test getting WebSocket service metrics"""
        # Add some mock connections
        self.service.connection_manager.active_connections = {
            "conn-1": MagicMock(),
            "conn-2": MagicMock()
        }
        self.service.connection_manager.user_connections = {
            "user-1": {"conn-1"},
            "user-2": {"conn-2"}
        }
        
        metrics = self.service.get_metrics()
        
        assert metrics["active_connections"] == 2
        assert metrics["users_connected"] == 2
        assert "subscriptions" in metrics

    def test_singleton_service(self):
        """Test that get_websocket_service returns singleton"""
        service1 = get_websocket_service()
        service2 = get_websocket_service()
        
        assert service1 is service2


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""

    @pytest.mark.asyncio
    async def test_complete_websocket_flow(self):
        """Test complete WebSocket connection and message flow"""
        service = WebSocketService()
        mock_websocket = AsyncMock()
        
        # Mock receive_text to simulate client messages
        mock_websocket.receive_text.side_effect = [
            '{"type": "subscribe", "event_types": ["memory.created"]}',
            '{"type": "ping"}',
            WebSocketDisconnect()
        ]
        
        connection_id = "conn-123"
        user_id = "user-456"
        
        # Handle the connection
        await service.handle_connection(mock_websocket, connection_id, user_id)
        
        # Verify connection was established
        mock_websocket.accept.assert_called_once()
        
        # Verify messages were received
        assert mock_websocket.receive_text.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_connections(self):
        """Test broadcasting to multiple WebSocket connections"""
        service = WebSocketService()
        
        # Set up multiple connections
        connections = {}
        for i in range(3):
            conn_id = f"conn-{i}"
            mock_ws = AsyncMock()
            connections[conn_id] = mock_ws
            service.connection_manager.active_connections[conn_id] = mock_ws
        
        # Broadcast an event
        await service.event_broadcaster.broadcast_event(
            "memory.created",
            {"memory_id": "mem-123"}
        )
        
        # Verify all connections received the message
        for mock_ws in connections.values():
            mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_specific_notifications(self):
        """Test sending notifications to specific users"""
        service = WebSocketService()
        
        # Set up connections for two users
        user1_conn = AsyncMock()
        user2_conn = AsyncMock()
        
        service.connection_manager.active_connections = {
            "conn-1": user1_conn,
            "conn-2": user2_conn
        }
        service.connection_manager.user_connections = {
            "user-1": {"conn-1"},
            "user-2": {"conn-2"}
        }
        
        # Send notification to user-1 only
        notification = {"type": "user_notification", "message": "Hello User 1"}
        await service.send_notification("user-1", notification)
        
        # Only user-1's connection should receive the message
        user1_conn.send_text.assert_called_once()
        user2_conn.send_text.assert_not_called()


class TestWebSocketEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_connection_manager_with_duplicate_connections(self):
        """Test handling duplicate connection IDs"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        connection_id = "conn-123"
        
        # Connect first WebSocket
        await manager.connect(mock_ws1, connection_id, "user-1")
        
        # Connect second WebSocket with same ID (should replace)
        await manager.connect(mock_ws2, connection_id, "user-2")
        
        assert manager.active_connections[connection_id] == mock_ws2

    @pytest.mark.asyncio
    async def test_websocket_with_malformed_json(self):
        """Test handling malformed JSON messages"""
        service = WebSocketService()
        mock_websocket = AsyncMock()
        
        # Mock malformed JSON message
        mock_websocket.receive_text.side_effect = [
            '{"type": "invalid json"',  # Malformed JSON
            WebSocketDisconnect()
        ]
        
        # Should handle gracefully without crashing
        await service.handle_connection(mock_websocket, "conn-123")
        
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_connection_timeout(self):
        """Test WebSocket connection timeout handling"""
        service = WebSocketService()
        mock_websocket = AsyncMock()
        
        # Mock timeout exception
        mock_websocket.receive_text.side_effect = asyncio.TimeoutError()
        
        # Should handle timeout gracefully
        await service.handle_connection(mock_websocket, "conn-123")
        
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_with_all_failed_connections(self):
        """Test broadcasting when all connections fail"""
        manager = ConnectionManager()
        
        # Set up connections that will all fail
        failed_connections = {}
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.send_text.side_effect = Exception(f"Connection {i} failed")
            failed_connections[f"conn-{i}"] = mock_ws
        
        manager.active_connections = failed_connections
        
        # Should handle all failures gracefully
        await manager.broadcast("test message")
        
        # All connections should have been called (and failed)
        for mock_ws in failed_connections.values():
            mock_ws.send_text.assert_called_once()

    def test_websocket_metrics_calculation(self):
        """Test WebSocket metrics calculation edge cases"""
        service = WebSocketService()
        
        # Test with no connections
        metrics = service.get_metrics()
        assert metrics["active_connections"] == 0
        assert metrics["users_connected"] == 0
        
        # Test with connections but no users
        service.connection_manager.active_connections = {"conn-1": MagicMock()}
        metrics = service.get_metrics()
        assert metrics["active_connections"] == 1
        assert metrics["users_connected"] == 0

    @pytest.mark.asyncio
    async def test_memory_usage_with_many_connections(self):
        """Test memory usage doesn't explode with many connections"""
        service = WebSocketService()
        
        # Simulate many connections
        for i in range(1000):
            conn_id = f"conn-{i}"
            user_id = f"user-{i}"
            mock_ws = MagicMock()
            
            service.connection_manager.active_connections[conn_id] = mock_ws
            if user_id not in service.connection_manager.user_connections:
                service.connection_manager.user_connections[user_id] = set()
            service.connection_manager.user_connections[user_id].add(conn_id)
        
        # Should handle large numbers of connections
        metrics = service.get_metrics()
        assert metrics["active_connections"] == 1000
        assert metrics["users_connected"] == 1000

    def test_event_priority_enum(self):
        """Test EventPriority enum functionality"""
        assert EventPriority.LOW == 1
        assert EventPriority.MEDIUM == 2
        assert EventPriority.HIGH == 3
        assert EventPriority.CRITICAL == 4
        
        # Test string representation
        assert EventPriority.HIGH.value_str == "high"
        assert EventPriority.CRITICAL.value_str == "critical"

    def test_event_type_enum_values(self):
        """Test EventType enum has expected values"""
        # Test memory events
        assert EventType.MEMORY_CREATED == "memory.created"
        assert EventType.MEMORY_UPDATED == "memory.updated"
        assert EventType.MEMORY_DELETED == "memory.deleted"
        
        # Test system events
        assert EventType.SYSTEM_STATUS == "system.status"
        assert EventType.USER_CONNECTED == "user.connected"
        
        # Test metrics events
        assert EventType.METRICS_UPDATE == "metrics.update"


class TestWebSocketSecurity:
    """Test WebSocket security features"""

    @pytest.mark.asyncio
    async def test_connection_isolation(self):
        """Test that connections are properly isolated"""
        service = WebSocketService()
        
        # Set up connections for different users
        user1_ws = AsyncMock()
        user2_ws = AsyncMock()
        
        await service.connection_manager.connect(user1_ws, "conn-1", "user-1")
        await service.connection_manager.connect(user2_ws, "conn-2", "user-2")
        
        # Send notification to user-1
        notification = {"type": "private", "data": "secret"}
        await service.send_notification("user-1", notification)
        
        # Only user-1 should receive the message
        user1_ws.send_text.assert_called_once()
        user2_ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_input_sanitization(self):
        """Test that WebSocket input is sanitized"""
        service = WebSocketService()
        mock_websocket = AsyncMock()
        
        # Mock potentially malicious message
        malicious_message = '{"type": "<script>alert(\\'xss\\')</script>"}'
        mock_websocket.receive_text.side_effect = [
            malicious_message,
            WebSocketDisconnect()
        ]
        
        # Should handle malicious input safely
        await service.handle_connection(mock_websocket, "conn-123")
        
        # Connection should be established despite malicious input
        mock_websocket.accept.assert_called_once()

    def test_subscription_validation(self):
        """Test subscription request validation"""
        # Valid subscription
        valid_sub = SubscriptionRequest(
            event_types=["memory.created"],
            action="subscribe"
        )
        assert valid_sub.action == "subscribe"
        
        # Invalid action should raise validation error
        with pytest.raises(ValueError):
            SubscriptionRequest(
                event_types=["memory.created"],
                action="invalid"
            )

    @pytest.mark.asyncio
    async def test_connection_limits(self):
        """Test connection limit handling (conceptual)"""
        service = WebSocketService()
        
        # This test verifies the service can handle connection tracking
        # In production, you might implement connection limits
        connections_count = len(service.connection_manager.active_connections)
        assert connections_count == 0  # Should start with no connections
        
        # Add mock connection
        mock_ws = AsyncMock()
        await service.connection_manager.connect(mock_ws, "conn-1", "user-1")
        
        connections_count = len(service.connection_manager.active_connections)
        assert connections_count == 1