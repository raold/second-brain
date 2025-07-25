"""
WebSocket service for real-time updates
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.synthesis.websocket_models import (
    BroadcastMessage,
    ConnectionInfo,
    ErrorMessage,
    EventType,
    HeartbeatMessage,
    HeartbeatResponse,
    MemoryEvent,
    MetricsEvent,
    MetricsSnapshot,
    ProgressUpdate,
    ReviewEvent,
    SubscriptionRequest,
    SubscriptionResponse,
    SubscriptionType,
    SynthesisEvent,
    SystemNotification,
    WebSocketMessage,
)
from app.services.synthesis.graph_cache import get_cache_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # Active connections: user_id -> Set[WebSocket]
        self.active_connections: dict[str, set[WebSocket]] = {}

        # Connection metadata: WebSocket -> ConnectionInfo
        self.connection_info: dict[WebSocket, ConnectionInfo] = {}

        # Subscription mapping: SubscriptionType -> Set[WebSocket]
        self.subscriptions: dict[SubscriptionType, set[WebSocket]] = {
            sub_type: set() for sub_type in SubscriptionType
        }

        # Heartbeat tracking
        self.heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str
    ) -> ConnectionInfo:
        """Accept a new WebSocket connection"""
        await websocket.accept()

        # Create connection info
        info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=datetime.utcnow(),
            client_info={
                "user_agent": websocket.headers.get("user-agent", "unknown"),
                "origin": websocket.headers.get("origin", "unknown")
            }
        )

        # Store connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        self.connection_info[websocket] = info

        # Subscribe to ALL events by default
        self.subscriptions[SubscriptionType.ALL].add(websocket)

        # Start heartbeat monitoring
        self.heartbeat_tasks[websocket] = asyncio.create_task(
            self._monitor_heartbeat(websocket)
        )

        # Send connection confirmation
        await self.send_personal_message(
            websocket,
            WebSocketMessage(
                type=EventType.USER_CONNECTED,
                user_id=user_id,
                data={
                    "connection_id": connection_id,
                    "subscriptions": [SubscriptionType.ALL.value],
                    "server_time": datetime.utcnow().isoformat()
                }
            )
        )

        logger.info(f"User {user_id} connected via WebSocket {connection_id}")

        return info

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        info = self.connection_info.get(websocket)

        if not info:
            return

        # Cancel heartbeat task
        if websocket in self.heartbeat_tasks:
            self.heartbeat_tasks[websocket].cancel()
            del self.heartbeat_tasks[websocket]

        # Remove from active connections
        if info.user_id in self.active_connections:
            self.active_connections[info.user_id].discard(websocket)

            # Clean up empty user entries
            if not self.active_connections[info.user_id]:
                del self.active_connections[info.user_id]

        # Remove from subscriptions
        for sub_type in SubscriptionType:
            self.subscriptions[sub_type].discard(websocket)

        # Remove connection info
        del self.connection_info[websocket]

        logger.info(f"User {info.user_id} disconnected from WebSocket {info.connection_id}")

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: WebSocketMessage
    ):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_json(message.dict())
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            await self.disconnect(websocket)

    async def send_user_message(
        self,
        user_id: str,
        message: WebSocketMessage
    ):
        """Send a message to all connections of a user"""
        if user_id not in self.active_connections:
            return

        # Send to all user's connections
        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message.dict())
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast(
        self,
        message: BroadcastMessage
    ):
        """Broadcast a message to multiple users"""
        # Determine target websockets
        target_websockets = set()

        if message.user_ids:
            # Specific users
            for user_id in message.user_ids:
                if user_id in self.active_connections:
                    target_websockets.update(self.active_connections[user_id])
        else:
            # All users
            for user_sockets in self.active_connections.values():
                target_websockets.update(user_sockets)

        # Filter by subscription type
        filtered_websockets = set()
        for websocket in target_websockets:
            info = self.connection_info.get(websocket)
            if info and info.user_id not in message.exclude_user_ids:
                # Check if subscribed to any of the target types
                for sub_type in message.subscriptions:
                    if websocket in self.subscriptions[sub_type]:
                        filtered_websockets.add(websocket)
                        break

        # Send to filtered websockets
        disconnected = []
        for websocket in filtered_websockets:
            try:
                await websocket.send_json(message.message.dict())
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def handle_subscription(
        self,
        websocket: WebSocket,
        request: SubscriptionRequest
    ) -> SubscriptionResponse:
        """Handle subscription/unsubscription requests"""
        info = self.connection_info.get(websocket)
        if not info:
            return SubscriptionResponse(
                success=False,
                active_subscriptions=[],
                message="Connection not found"
            )

        try:
            if request.action == "subscribe":
                for sub_type in request.subscription_types:
                    self.subscriptions[sub_type].add(websocket)
                    if sub_type not in info.subscriptions:
                        info.subscriptions.append(sub_type)
            else:  # unsubscribe
                for sub_type in request.subscription_types:
                    self.subscriptions[sub_type].discard(websocket)
                    if sub_type in info.subscriptions:
                        info.subscriptions.remove(sub_type)

            return SubscriptionResponse(
                success=True,
                active_subscriptions=info.subscriptions,
                message=f"Successfully {request.action}d"
            )

        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
            return SubscriptionResponse(
                success=False,
                active_subscriptions=info.subscriptions,
                message=str(e)
            )

    async def _monitor_heartbeat(self, websocket: WebSocket):
        """Monitor connection heartbeat"""
        try:
            sequence = 0
            while True:
                # Wait for heartbeat interval
                await asyncio.sleep(30)  # 30 seconds

                # Send ping
                ping = HeartbeatMessage(sequence=sequence)
                await websocket.send_json(ping.dict())

                sequence += 1

                # Check last ping time
                info = self.connection_info.get(websocket)
                if info and (datetime.utcnow() - info.last_ping) > timedelta(minutes=2):
                    logger.warning(f"Connection {info.connection_id} heartbeat timeout")
                    await self.disconnect(websocket)
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat monitoring error: {e}")
            await self.disconnect(websocket)

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection statistics"""
        total_connections = sum(len(sockets) for sockets in self.active_connections.values())

        subscription_stats = {
            sub_type.value: len(sockets)
            for sub_type, sockets in self.subscriptions.items()
        }

        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "connections_per_user": {
                user_id: len(sockets)
                for user_id, sockets in self.active_connections.items()
            },
            "subscription_stats": subscription_stats
        }


class WebSocketService:
    """Service for WebSocket real-time updates"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.connection_manager = ConnectionManager()
        self.cache_service = None
        self._initialize_task = None

    async def initialize(self):
        """Initialize the service"""
        if not self.cache_service:
            self.cache_service = await get_cache_service()

        # Start background tasks
        self._initialize_task = asyncio.create_task(self._background_metrics_updates())

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str
    ):
        """Handle a WebSocket connection"""
        # Connect
        info = await self.connection_manager.connect(websocket, user_id, connection_id)

        try:
            while True:
                # Receive message
                data = await websocket.receive_json()

                # Handle different message types
                if data.get("type") == "ping":
                    # Handle heartbeat
                    await self._handle_heartbeat(websocket, data)
                elif data.get("type") == "subscribe":
                    # Handle subscription
                    request = SubscriptionRequest(**data)
                    response = await self.connection_manager.handle_subscription(
                        websocket, request
                    )
                    await websocket.send_json(response.dict())
                elif data.get("type") == "unsubscribe":
                    # Handle unsubscription
                    request = SubscriptionRequest(**data)
                    response = await self.connection_manager.handle_subscription(
                        websocket, request
                    )
                    await websocket.send_json(response.dict())
                else:
                    # Unknown message type
                    error = ErrorMessage(
                        error_code="UNKNOWN_MESSAGE_TYPE",
                        error_message=f"Unknown message type: {data.get('type')}",
                        recoverable=True
                    )
                    await websocket.send_json(error.dict())

        except WebSocketDisconnect:
            await self.connection_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

            # Send error message
            error = ErrorMessage(
                error_code="INTERNAL_ERROR",
                error_message="An internal error occurred",
                details={"error": str(e)},
                recoverable=False,
                suggested_action="Reconnect"
            )

            try:
                await websocket.send_json(error.dict())
            except:
                pass

            await self.connection_manager.disconnect(websocket)

    async def _handle_heartbeat(self, websocket: WebSocket, data: dict[str, Any]):
        """Handle heartbeat message"""
        info = self.connection_manager.connection_info.get(websocket)
        if info:
            info.last_ping = datetime.utcnow()

        # Send pong response
        pong = HeartbeatResponse(
            sequence=data.get("sequence", 0),
            server_time=datetime.utcnow()
        )
        await websocket.send_json(pong.dict())

    # Event emission methods

    async def emit_memory_event(
        self,
        user_id: str,
        memory_id: UUID,
        memory_title: str,
        action: str,
        changes: Optional[dict[str, Any]] = None,
        related_memories: Optional[list[UUID]] = None
    ):
        """Emit a memory-related event"""
        event_type_map = {
            "create": EventType.MEMORY_CREATED,
            "update": EventType.MEMORY_UPDATED,
            "delete": EventType.MEMORY_DELETED,
            "consolidate": EventType.MEMORY_CONSOLIDATED
        }

        event = MemoryEvent(
            type=event_type_map.get(action, EventType.MEMORY_UPDATED),
            user_id=user_id,
            memory_id=memory_id,
            memory_title=memory_title,
            action=action,
            changes=changes,
            related_memories=related_memories or [],
            data={
                "memory_id": str(memory_id),
                "title": memory_title,
                "action": action
            }
        )

        await self.connection_manager.send_user_message(user_id, event)

    async def emit_metrics_event(
        self,
        metric_name: str,
        current_value: float,
        previous_value: Optional[float] = None,
        threshold_crossed: Optional[str] = None,
        graph_id: str = "main"
    ):
        """Emit a metrics update event"""
        change_percentage = None
        if previous_value is not None and previous_value != 0:
            change_percentage = ((current_value - previous_value) / previous_value) * 100

        event = MetricsEvent(
            type=EventType.METRICS_UPDATED,
            user_id="system",  # Metrics are system-wide
            metric_name=metric_name,
            current_value=current_value,
            previous_value=previous_value,
            change_percentage=change_percentage,
            threshold_crossed=threshold_crossed,
            graph_id=graph_id,
            data={
                "metric": metric_name,
                "value": current_value,
                "change": change_percentage
            }
        )

        # Broadcast to all users subscribed to metrics
        await self.connection_manager.broadcast(
            BroadcastMessage(
                subscriptions=[SubscriptionType.METRICS],
                message=event
            )
        )

    async def emit_review_event(
        self,
        user_id: str,
        memory_id: UUID,
        memory_title: str,
        action: str,
        review_id: Optional[UUID] = None,
        next_review: Optional[datetime] = None,
        performance: Optional[str] = None,
        streak_info: Optional[dict[str, int]] = None
    ):
        """Emit a review-related event"""
        event_type_map = {
            "due": EventType.REVIEW_DUE,
            "completed": EventType.REVIEW_COMPLETED,
            "overdue": EventType.REVIEW_DUE
        }

        # Special handling for streaks
        if action == "completed" and streak_info and streak_info.get("current_streak", 0) > 0:
            event_type = EventType.REVIEW_STREAK
        else:
            event_type = event_type_map.get(action, EventType.REVIEW_DUE)

        event = ReviewEvent(
            type=event_type,
            user_id=user_id,
            review_id=review_id,
            memory_id=memory_id,
            memory_title=memory_title,
            action=action,
            next_review=next_review,
            performance=performance,
            streak_info=streak_info,
            data={
                "memory_id": str(memory_id),
                "title": memory_title,
                "action": action
            }
        )

        await self.connection_manager.send_user_message(user_id, event)

    async def emit_synthesis_event(
        self,
        user_id: str,
        synthesis_type: str,
        resource_id: UUID,
        title: str,
        preview: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: float = 0.5
    ):
        """Emit a synthesis-related event"""
        event_type_map = {
            "consolidation": EventType.CONSOLIDATION_SUGGESTED,
            "summary": EventType.SUMMARY_GENERATED,
            "suggestion": EventType.SUGGESTION_AVAILABLE,
            "report": EventType.REPORT_READY
        }

        event = SynthesisEvent(
            type=event_type_map.get(synthesis_type, EventType.SUGGESTION_AVAILABLE),
            user_id=user_id,
            synthesis_type=synthesis_type,
            resource_id=resource_id,
            title=title,
            preview=preview,
            action_url=action_url,
            priority=priority,
            data={
                "type": synthesis_type,
                "resource_id": str(resource_id),
                "title": title
            }
        )

        await self.connection_manager.send_user_message(user_id, event)

    async def send_notification(
        self,
        user_id: str,
        severity: str,
        title: str,
        message: str,
        action_label: Optional[str] = None,
        action_url: Optional[str] = None,
        auto_dismiss: bool = True,
        dismiss_after_seconds: int = 5
    ):
        """Send a system notification to a user"""
        notification = SystemNotification(
            type=EventType.SYSTEM_NOTIFICATION,
            user_id=user_id,
            severity=severity,
            title=title,
            message=message,
            action_label=action_label,
            action_url=action_url,
            auto_dismiss=auto_dismiss,
            dismiss_after_seconds=dismiss_after_seconds,
            data={
                "severity": severity,
                "title": title,
                "message": message
            }
        )

        await self.connection_manager.send_user_message(user_id, notification)

    async def send_progress_update(
        self,
        user_id: str,
        operation_id: UUID,
        operation_type: str,
        current_step: int,
        total_steps: int,
        current_step_name: str,
        percentage_complete: float,
        estimated_time_remaining: Optional[int] = None,
        can_cancel: bool = False
    ):
        """Send progress update for long-running operations"""
        update = ProgressUpdate(
            operation_id=operation_id,
            operation_type=operation_type,
            current_step=current_step,
            total_steps=total_steps,
            current_step_name=current_step_name,
            percentage_complete=percentage_complete,
            estimated_time_remaining_seconds=estimated_time_remaining,
            can_cancel=can_cancel
        )

        message = WebSocketMessage(
            type=EventType.SYSTEM_NOTIFICATION,
            user_id=user_id,
            data=update.dict()
        )

        await self.connection_manager.send_user_message(user_id, message)

    async def broadcast_metrics_snapshot(self, snapshot: MetricsSnapshot):
        """Broadcast metrics snapshot to all subscribed users"""
        message = WebSocketMessage(
            type=EventType.METRICS_UPDATED,
            user_id="system",
            data=snapshot.dict()
        )

        await self.connection_manager.broadcast(
            BroadcastMessage(
                subscriptions=[SubscriptionType.METRICS],
                message=message
            )
        )

    async def _background_metrics_updates(self):
        """Background task to send periodic metrics updates"""
        try:
            while True:
                await asyncio.sleep(60)  # Update every minute

                # Get current metrics from cache
                if self.cache_service:
                    # This would fetch real metrics in production
                    snapshot = MetricsSnapshot(
                        metrics={
                            "total_memories": 1523,
                            "total_connections": 3847,
                            "active_users": len(self.connection_manager.active_connections)
                        },
                        trends={
                            "memories": "increasing",
                            "connections": "stable",
                            "users": "stable"
                        },
                        alerts=[]
                    )

                    await self.broadcast_metrics_snapshot(snapshot)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Background metrics update error: {e}")

    async def shutdown(self):
        """Shutdown the service"""
        # Cancel background tasks
        if self._initialize_task:
            self._initialize_task.cancel()

        # Disconnect all websockets
        all_websockets = []
        for user_sockets in self.connection_manager.active_connections.values():
            all_websockets.extend(user_sockets)

        for websocket in all_websockets:
            await self.connection_manager.disconnect(websocket)


# Global WebSocket service instance
_websocket_service = None


async def get_websocket_service(db: AsyncSession) -> WebSocketService:
    """Get or create WebSocket service instance"""
    global _websocket_service

    if _websocket_service is None:
        _websocket_service = WebSocketService(db)
        await _websocket_service.initialize()

    return _websocket_service
