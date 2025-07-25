"""
WebSocket Service - v2.8.2

Service for managing real-time WebSocket connections, event broadcasting,
and subscription management.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.models.synthesis.websocket_models import (
    BroadcastRequest,
    ConnectionInfo,
    ConnectionStatus,
    EventBatch,
    EventSubscription,
    EventType,
    SubscriptionRequest,
    WebSocketEvent,
    WebSocketMessage,
    WebSocketMetrics,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""

    def __init__(self):
        # Connection tracking
        self._connections: dict[str, WebSocket] = {}
        self._connection_info: dict[str, ConnectionInfo] = {}
        self._user_connections: dict[str, set[str]] = defaultdict(set)

        # Subscription tracking
        self._subscriptions: dict[str, EventSubscription] = {}
        self._event_subscribers: dict[EventType, set[str]] = defaultdict(set)
        self._channel_subscribers: dict[str, set[str]] = defaultdict(set)

        # Metrics
        self._metrics = WebSocketMetrics()
        self._message_count = 0
        self._event_count = 0

        # Rate limiting
        self._rate_limits: dict[str, dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        client_info: Optional[dict[str, str]] = None,
    ) -> ConnectionInfo:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        # Store connection
        self._connections[connection_id] = websocket
        self._user_connections[user_id].add(connection_id)

        # Create connection info
        info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            status=ConnectionStatus.CONNECTED,
            client_version=client_info.get("version") if client_info else None,
            user_agent=client_info.get("user_agent") if client_info else None,
            ip_address=client_info.get("ip_address") if client_info else None,
        )

        self._connection_info[connection_id] = info

        # Update metrics
        self._metrics.total_connections = len(self._connections)

        # Send connection confirmation
        await self.send_message(
            connection_id,
            WebSocketMessage(
                type="event",
                event=WebSocketEvent(
                    id=f"evt_{datetime.utcnow().timestamp()}",
                    type=EventType.USER_CONNECTED,
                    data={"connection_id": connection_id, "status": "connected"},
                ),
            ),
        )

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        return info

    def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        if connection_id not in self._connections:
            return

        # Get connection info
        info = self._connection_info.get(connection_id)
        if info:
            # Remove from user connections
            self._user_connections[info.user_id].discard(connection_id)
            if not self._user_connections[info.user_id]:
                del self._user_connections[info.user_id]

            # Update status
            info.status = ConnectionStatus.DISCONNECTED

        # Remove connection
        del self._connections[connection_id]
        if connection_id in self._connection_info:
            del self._connection_info[connection_id]

        # Clean up subscriptions
        self._cleanup_subscriptions(connection_id)

        # Update metrics
        self._metrics.total_connections = len(self._connections)

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(
        self,
        connection_id: str,
        request: SubscriptionRequest,
    ) -> EventSubscription:
        """Subscribe connection to events."""
        if connection_id not in self._connections:
            raise ValueError(f"Connection {connection_id} not found")

        info = self._connection_info[connection_id]

        # Create subscription
        subscription = EventSubscription(
            id=f"sub_{datetime.utcnow().timestamp()}",
            user_id=info.user_id,
            connection_id=connection_id,
            event_types=request.event_types,
            channels=request.channels,
            filters={
                "resource_types": request.resource_types,
                "resource_ids": request.resource_ids,
            },
        )

        # Store subscription
        self._subscriptions[subscription.id] = subscription
        info.subscriptions.append(subscription)

        # Update indexes
        for event_type in request.event_types:
            self._event_subscribers[event_type].add(connection_id)

        for channel in request.channels:
            self._channel_subscribers[channel].add(connection_id)

        # Send historical events if requested
        if request.include_historical:
            await self._send_historical_events(
                connection_id,
                request.event_types,
                request.historical_limit,
            )

        logger.info(f"Subscription created: {subscription.id} for connection {connection_id}")
        return subscription

    async def unsubscribe(
        self,
        connection_id: str,
        subscription_id: str,
    ):
        """Unsubscribe from events."""
        if subscription_id not in self._subscriptions:
            return

        subscription = self._subscriptions[subscription_id]

        # Remove from indexes
        for event_type in subscription.event_types:
            self._event_subscribers[event_type].discard(connection_id)

        for channel in subscription.channels:
            self._channel_subscribers[channel].discard(connection_id)

        # Remove subscription
        del self._subscriptions[subscription_id]

        # Update connection info
        info = self._connection_info.get(connection_id)
        if info:
            info.subscriptions = [
                s for s in info.subscriptions if s.id != subscription_id
            ]

        logger.info(f"Subscription removed: {subscription_id}")

    async def send_message(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """Send message to specific connection."""
        websocket = self._connections.get(connection_id)
        if not websocket:
            return False

        try:
            # Check connection state
            if websocket.client_state != WebSocketState.CONNECTED:
                self.disconnect(connection_id)
                return False

            # Check rate limit
            if not self._check_rate_limit(connection_id):
                await self._send_rate_limit_error(connection_id)
                return False

            # Send message
            await websocket.send_json(message.dict(exclude_none=True))

            # Update metrics
            self._message_count += 1
            info = self._connection_info.get(connection_id)
            if info:
                info.messages_sent += 1
                info.bytes_sent += len(json.dumps(message.dict()))

            return True

        except WebSocketDisconnect:
            self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False

    async def broadcast_event(
        self,
        event: WebSocketEvent,
        target_connections: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Broadcast event to multiple connections."""
        if target_connections is None:
            # Determine target connections based on event type and subscriptions
            target_connections = self._get_event_subscribers(event)

        # Create batch
        batch = EventBatch(
            events=[event],
            batch_id=f"batch_{datetime.utcnow().timestamp()}",
            target_connections=target_connections,
        )

        # Send to each connection
        tasks = []
        for conn_id in target_connections:
            message = WebSocketMessage(type="event", event=event)
            tasks.append(self.send_message(conn_id, message))

        # Wait for all sends
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Track delivery
        for i, (conn_id, result) in enumerate(zip(target_connections, results)):
            if isinstance(result, Exception):
                batch.failed_deliveries[conn_id] = str(result)
            elif result:
                batch.delivered_to.append(conn_id)
            else:
                batch.failed_deliveries[conn_id] = "Connection not found or disconnected"

        # Update metrics
        self._event_count += 1
        self._metrics.events_per_second = self._calculate_rate(self._event_count)

        return {
            "batch_id": batch.batch_id,
            "total_targets": len(target_connections),
            "delivered": len(batch.delivered_to),
            "failed": len(batch.failed_deliveries),
        }

    async def handle_message(
        self,
        connection_id: str,
        data: dict[str, Any],
    ):
        """Handle incoming WebSocket message."""
        try:
            # Parse message
            message = WebSocketMessage(**data)

            # Update metrics
            info = self._connection_info.get(connection_id)
            if info:
                info.messages_received += 1
                info.bytes_received += len(json.dumps(data))
                info.last_ping = datetime.utcnow()

            # Handle based on type
            if message.type == "request":
                await self._handle_request(connection_id, message)
            elif message.type == "ping":
                await self._handle_ping(connection_id)
            else:
                logger.warning(f"Unknown message type: {message.type}")

        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            await self._send_error(connection_id, str(e))

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get information about a connection."""
        return self._connection_info.get(connection_id)

    def get_user_connections(self, user_id: str) -> list[str]:
        """Get all connections for a user."""
        return list(self._user_connections.get(user_id, set()))

    def get_metrics(self) -> WebSocketMetrics:
        """Get current metrics."""
        # Update real-time metrics
        self._metrics.total_connections = len(self._connections)
        self._metrics.authenticated_connections = sum(
            1 for info in self._connection_info.values()
            if info.status == ConnectionStatus.AUTHENTICATED
        )
        self._metrics.messages_per_second = self._calculate_rate(self._message_count)
        self._metrics.events_per_second = self._calculate_rate(self._event_count)

        return self._metrics

    def _get_event_subscribers(self, event: WebSocketEvent) -> list[str]:
        """Get connections subscribed to an event."""
        subscribers = set()

        # Get by event type
        if event.type in self._event_subscribers:
            subscribers.update(self._event_subscribers[event.type])

        # Get by channel
        if event.channel:
            subscribers.update(self._channel_subscribers.get(event.channel, set()))

        # Filter by subscription filters
        filtered = []
        for conn_id in subscribers:
            if self._matches_filters(conn_id, event):
                filtered.append(conn_id)

        # Add specific target users
        for user_id in event.target_users:
            filtered.extend(self._user_connections.get(user_id, []))

        return list(set(filtered))

    def _matches_filters(self, connection_id: str, event: WebSocketEvent) -> bool:
        """Check if event matches connection's subscription filters."""
        # Get all subscriptions for connection
        info = self._connection_info.get(connection_id)
        if not info:
            return False

        for subscription in info.subscriptions:
            # Check event type
            if event.type not in subscription.event_types:
                continue

            # Check resource type filter
            if subscription.filters.get("resource_types"):
                if event.resource_type not in subscription.filters["resource_types"]:
                    continue

            # Check resource ID filter
            if subscription.filters.get("resource_ids"):
                if event.resource_id not in subscription.filters["resource_ids"]:
                    continue

            # Matched a subscription
            return True

        return False

    def _cleanup_subscriptions(self, connection_id: str):
        """Clean up subscriptions for disconnected connection."""
        # Remove from event subscribers
        for subscribers in self._event_subscribers.values():
            subscribers.discard(connection_id)

        # Remove from channel subscribers
        for subscribers in self._channel_subscribers.values():
            subscribers.discard(connection_id)

        # Remove subscriptions
        to_remove = []
        for sub_id, subscription in self._subscriptions.items():
            if subscription.connection_id == connection_id:
                to_remove.append(sub_id)

        for sub_id in to_remove:
            del self._subscriptions[sub_id]

    def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection has exceeded rate limit."""
        # Simple rate limiting - 100 messages per minute
        now = datetime.utcnow()

        if connection_id not in self._rate_limits:
            self._rate_limits[connection_id] = {
                "count": 0,
                "window_start": now,
            }

        rate_info = self._rate_limits[connection_id]

        # Reset window if needed
        if (now - rate_info["window_start"]).seconds >= 60:
            rate_info["count"] = 0
            rate_info["window_start"] = now

        # Check limit
        rate_info["count"] += 1
        return rate_info["count"] <= 100

    async def _send_rate_limit_error(self, connection_id: str):
        """Send rate limit error to connection."""
        message = WebSocketMessage(
            type="error",
            error="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
        )
        await self.send_message(connection_id, message)

    async def _send_error(self, connection_id: str, error: str, code: str = "ERROR"):
        """Send error message to connection."""
        message = WebSocketMessage(
            type="error",
            error=error,
            error_code=code,
        )
        await self.send_message(connection_id, message)

    async def _handle_request(self, connection_id: str, message: WebSocketMessage):
        """Handle request message."""
        if message.action == "subscribe":
            request = SubscriptionRequest(**message.payload)
            subscription = await self.subscribe(connection_id, request)

            # Send response
            response = WebSocketMessage(
                type="response",
                id=message.id,
                success=True,
                payload=subscription.dict(),
            )
            await self.send_message(connection_id, response)

        elif message.action == "unsubscribe":
            subscription_id = message.payload.get("subscription_id")
            await self.unsubscribe(connection_id, subscription_id)

            # Send response
            response = WebSocketMessage(
                type="response",
                id=message.id,
                success=True,
            )
            await self.send_message(connection_id, response)

        else:
            await self._send_error(
                connection_id,
                f"Unknown action: {message.action}",
                "UNKNOWN_ACTION",
            )

    async def _handle_ping(self, connection_id: str):
        """Handle ping message."""
        # Send pong
        message = WebSocketMessage(type="pong")
        await self.send_message(connection_id, message)

    async def _send_historical_events(
        self,
        connection_id: str,
        event_types: list[EventType],
        limit: int,
    ):
        """Send recent historical events to new subscriber."""
        # In production, would query from event store
        # For now, send mock historical events
        historical_events = [
            WebSocketEvent(
                id=f"hist_{i}",
                type=EventType.MEMORY_CREATED,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                resource_type="memory",
                resource_id=f"mem_{i}",
                data={"content": f"Historical memory {i}"},
            )
            for i in range(min(limit, 5))
        ]

        for event in historical_events:
            if event.type in event_types:
                message = WebSocketMessage(type="event", event=event)
                await self.send_message(connection_id, message)

    def _calculate_rate(self, count: int, window_seconds: int = 60) -> float:
        """Calculate rate per second."""
        # Simple rate calculation - in production would use sliding window
        return count / window_seconds


class EventBroadcaster:
    """Service for broadcasting events to WebSocket connections."""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the broadcast worker."""
        self._broadcast_task = asyncio.create_task(self._broadcast_worker())
        logger.info("Event broadcaster started")

    async def stop(self):
        """Stop the broadcast worker."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("Event broadcaster stopped")

    async def queue_broadcast(self, request: BroadcastRequest):
        """Queue an event for broadcasting."""
        await self._broadcast_queue.put(request)

    async def broadcast_memory_event(
        self,
        event_type: EventType,
        memory_id: str,
        user_id: str,
        data: dict[str, Any],
    ):
        """Broadcast a memory-related event."""
        event = WebSocketEvent(
            id=f"evt_{datetime.utcnow().timestamp()}",
            type=event_type,
            resource_type="memory",
            resource_id=memory_id,
            user_id=user_id,
            data=data,
        )

        request = BroadcastRequest(
            event=event,
            broadcast_type="users",
            user_ids=[user_id],
        )

        await self.queue_broadcast(request)

    async def broadcast_report_event(
        self,
        event_type: EventType,
        report_id: str,
        user_id: str,
        data: dict[str, Any],
    ):
        """Broadcast a report-related event."""
        event = WebSocketEvent(
            id=f"evt_{datetime.utcnow().timestamp()}",
            type=event_type,
            resource_type="report",
            resource_id=report_id,
            user_id=user_id,
            data=data,
        )

        request = BroadcastRequest(
            event=event,
            broadcast_type="users",
            user_ids=[user_id],
        )

        await self.queue_broadcast(request)

    async def broadcast_system_event(
        self,
        event_type: EventType,
        data: dict[str, Any],
        channel: Optional[str] = None,
    ):
        """Broadcast a system-wide event."""
        event = WebSocketEvent(
            id=f"evt_{datetime.utcnow().timestamp()}",
            type=event_type,
            resource_type="system",
            data=data,
            channel=channel,
            broadcast=True,
        )

        request = BroadcastRequest(
            event=event,
            broadcast_type="all" if not channel else "channel",
            channels=[channel] if channel else [],
        )

        await self.queue_broadcast(request)

    async def _broadcast_worker(self):
        """Worker to process broadcast queue."""
        while True:
            try:
                # Get next broadcast request
                request = await self._broadcast_queue.get()

                # Determine target connections
                if request.broadcast_type == "all":
                    target_connections = None  # Will broadcast to all subscribers
                elif request.broadcast_type == "channel":
                    target_connections = []
                    for channel in request.channels:
                        conns = self.connection_manager._channel_subscribers.get(channel, set())
                        target_connections.extend(conns)
                elif request.broadcast_type == "users":
                    target_connections = []
                    for user_id in request.user_ids:
                        conns = self.connection_manager.get_user_connections(user_id)
                        target_connections.extend(conns)
                else:
                    # Filter based on criteria
                    target_connections = self._filter_connections(request.connection_filters)

                # Broadcast event
                result = await self.connection_manager.broadcast_event(
                    request.event,
                    target_connections,
                )

                logger.info(f"Broadcast complete: {result}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")

    def _filter_connections(self, filters: dict[str, Any]) -> list[str]:
        """Filter connections based on criteria."""
        connections = []

        for conn_id, info in self.connection_manager._connection_info.items():
            # Apply filters
            if filters.get("status") and info.status != filters["status"]:
                continue

            if filters.get("client_version") and info.client_version != filters["client_version"]:
                continue

            connections.append(conn_id)

        return connections


class WebSocketService:
    """Main service for WebSocket functionality."""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.event_broadcaster = EventBroadcaster(self.connection_manager)

    async def start(self):
        """Start the WebSocket service."""
        await self.event_broadcaster.start()
        logger.info("WebSocket service started")

    async def stop(self):
        """Stop the WebSocket service."""
        await self.event_broadcaster.stop()

        # Disconnect all connections
        for conn_id in list(self.connection_manager._connections.keys()):
            self.connection_manager.disconnect(conn_id)

        logger.info("WebSocket service stopped")

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        client_info: Optional[dict[str, str]] = None,
    ) -> str:
        """Handle a new WebSocket connection."""
        connection_id = f"conn_{user_id}_{datetime.utcnow().timestamp()}"

        try:
            # Connect
            await self.connection_manager.connect(
                websocket,
                connection_id,
                user_id,
                client_info,
            )

            # Handle messages
            while True:
                data = await websocket.receive_json()
                await self.connection_manager.handle_message(connection_id, data)

        except WebSocketDisconnect:
            self.connection_manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
            self.connection_manager.disconnect(connection_id)

        return connection_id
