"""
Concrete event handlers for various domain events.

These handlers implement cross-cutting concerns like analytics,
notifications, and system monitoring triggered by domain events.
"""

from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class ImportanceTrackingHandler(EventHandler):
    """
    Handler for tracking and updating memory importance based on access patterns.

    Implements adaptive importance scoring that learns from user behavior.
    """

    def __init__(self, memory_repository=None):
        """
        Initialize the importance tracking handler.

        Args:
            memory_repository: Repository for updating memory importance scores
        """
        self.memory_repository = memory_repository
        self.access_patterns: dict[str, list] = {}  # memory_id -> [access_times]
        self.importance_cache: dict[str, float] = {}

        # Configuration
        self.decay_factor = 0.95  # Daily decay for importance
        self.access_weight = 0.1  # Weight of each access
        self.recency_bonus = 0.2  # Bonus for recent access
        self.max_access_history = 50  # Max access events to track per memory

    async def handle(self, event: DomainEvent) -> None:
        """Handle events that affect memory importance."""
        if isinstance(event, MemoryAccessedEvent):
            await self._handle_memory_accessed(event)
        elif isinstance(event, MemoryCreatedEvent):
            await self._handle_memory_created(event)
        elif isinstance(event, SearchPerformedEvent):
            await self._handle_search_performed(event)

    async def can_handle(self, event: DomainEvent) -> bool:
        """Only handle memory and search related events."""
        return isinstance(event, (MemoryAccessedEvent, MemoryCreatedEvent, SearchPerformedEvent))

    async def _handle_memory_accessed(self, event: MemoryAccessedEvent) -> None:
        """Handle memory access events to update importance."""
        memory_id = event.memory_id

        # Track access pattern
        if memory_id not in self.access_patterns:
            self.access_patterns[memory_id] = []

        self.access_patterns[memory_id].append(event.occurred_at)

        # Limit history size
        if len(self.access_patterns[memory_id]) > self.max_access_history:
            self.access_patterns[memory_id] = self.access_patterns[memory_id][-self.max_access_history:]

        # Calculate new importance score
        new_score = await self._calculate_importance_score(memory_id, event.access_type)

        # Update if significantly changed
        current_score = self.importance_cache.get(memory_id, 0.5)
        if abs(new_score - current_score) > 0.05:  # 5% threshold
            self.importance_cache[memory_id] = new_score

            if self.memory_repository:
                try:
                    await self.memory_repository.update_importance_score(memory_id, new_score)
                    logger.debug(f"Updated importance for memory {memory_id}: {current_score:.3f} -> {new_score:.3f}")
                except Exception as e:
                    logger.error(f"Failed to update importance for memory {memory_id}: {e}")

    async def _handle_memory_created(self, event: MemoryCreatedEvent) -> None:
        """Handle new memory creation."""
        # Initialize importance tracking for new memory
        self.importance_cache[event.memory_id] = event.importance_score
        self.access_patterns[event.memory_id] = []

        logger.debug(f"Initialized importance tracking for memory {event.memory_id}")

    async def _handle_search_performed(self, event: SearchPerformedEvent) -> None:
        """Handle search events to boost importance of search terms."""
        # This could be enhanced to boost importance of memories that match search terms
        # For now, just log for analytics
        logger.debug(f"Search performed: '{event.search_query}' with {event.results_count} results")

    async def _calculate_importance_score(self, memory_id: str, access_type: str) -> float:
        """
        Calculate new importance score based on access patterns.

        Args:
            memory_id: ID of the memory
            access_type: Type of access (view, search_result, etc.)

        Returns:
            New importance score (0.0 to 1.0)
        """
        current_score = self.importance_cache.get(memory_id, 0.5)
        access_times = self.access_patterns.get(memory_id, [])

        if not access_times:
            return current_score

        # Calculate access frequency (accesses per day)
        now = datetime.utcnow()
        recent_accesses = [t for t in access_times if (now - t).days <= 7]
        access_frequency = len(recent_accesses) / 7.0

        # Calculate recency bonus
        latest_access = max(access_times)
        hours_since_access = (now - latest_access).total_seconds() / 3600
        recency_bonus = max(0, self.recency_bonus * (1 - hours_since_access / 168))  # 7 days decay

        # Access type weights
        type_weights = {
            'view': 1.0,
            'search_result': 0.8,
            'related_fetch': 0.6
        }
        access_weight = type_weights.get(access_type, 0.5)

        # Calculate boost
        importance_boost = (
            (access_frequency * 0.1) +  # Frequency component
            recency_bonus +             # Recency component
            (access_weight * 0.05)      # Access type component
        )

        # Apply boost with ceiling
        new_score = min(1.0, current_score + importance_boost)

        return new_score


class SearchAnalyticsHandler(EventHandler):
    """
    Handler for collecting and analyzing search analytics.

    Tracks search patterns, performance, and user behavior for optimization.
    """

    def __init__(self):
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'empty_result_searches': 0,
            'slow_searches': 0,
            'popular_terms': {},
            'performance_samples': []
        }
        self.recent_searches: list = []
        self.max_recent_searches = 1000

    async def handle(self, event: DomainEvent) -> None:
        """Handle search-related events."""
        if isinstance(event, SearchPerformedEvent):
            await self._handle_search_performed(event)

    async def can_handle(self, event: DomainEvent) -> bool:
        """Only handle search events."""
        return isinstance(event, SearchPerformedEvent)

    async def _handle_search_performed(self, event: SearchPerformedEvent) -> None:
        """Analyze search performance and patterns."""
        # Update basic stats
        self.search_stats['total_searches'] += 1

        if event.results_count > 0:
            self.search_stats['successful_searches'] += 1
        else:
            self.search_stats['empty_result_searches'] += 1

        if event.execution_time_ms > 1000:  # > 1 second
            self.search_stats['slow_searches'] += 1

        # Track popular search terms
        query_lower = event.search_query.lower().strip()
        if len(query_lower) > 2:  # Ignore very short queries
            self.search_stats['popular_terms'][query_lower] = (
                self.search_stats['popular_terms'].get(query_lower, 0) + 1
            )

        # Sample performance data
        self.search_stats['performance_samples'].append({
            'timestamp': event.occurred_at,
            'execution_time_ms': event.execution_time_ms,
            'results_count': event.results_count,
            'query_length': len(event.search_query)
        })

        # Limit performance samples
        if len(self.search_stats['performance_samples']) > 1000:
            self.search_stats['performance_samples'] = self.search_stats['performance_samples'][-1000:]

        # Track recent searches for pattern analysis
        self.recent_searches.append({
            'query': event.search_query,
            'timestamp': event.occurred_at,
            'user_id': event.user_id,
            'results_count': event.results_count
        })

        if len(self.recent_searches) > self.max_recent_searches:
            self.recent_searches = self.recent_searches[-self.max_recent_searches:]

        # Log analytics
        logger.info(
            "Search analytics",
            extra={
                'query': event.search_query,
                'results_count': event.results_count,
                'execution_time_ms': event.execution_time_ms,
                'user_id': event.user_id,
                'search_type': event.search_type
            }
        )

    def get_analytics_summary(self) -> dict[str, Any]:
        """Get search analytics summary."""
        total = self.search_stats['total_searches']
        if total == 0:
            return {'message': 'No search data available'}

        success_rate = self.search_stats['successful_searches'] / total
        empty_rate = self.search_stats['empty_result_searches'] / total
        slow_rate = self.search_stats['slow_searches'] / total

        # Top search terms
        top_terms = sorted(
            self.search_stats['popular_terms'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Average performance
        perf_samples = self.search_stats['performance_samples']
        if perf_samples:
            avg_time = sum(s['execution_time_ms'] for s in perf_samples) / len(perf_samples)
            avg_results = sum(s['results_count'] for s in perf_samples) / len(perf_samples)
        else:
            avg_time = avg_results = 0

        return {
            'total_searches': total,
            'success_rate': success_rate,
            'empty_result_rate': empty_rate,
            'slow_search_rate': slow_rate,
            'avg_execution_time_ms': avg_time,
            'avg_results_count': avg_results,
            'top_search_terms': top_terms,
            'recent_search_count': len(self.recent_searches)
        }


class SystemMonitoringHandler(EventHandler):
    """
    Handler for system monitoring and health tracking.

    Collects metrics and detects system health issues.
    """

    def __init__(self):
        self.health_history: dict[str, list] = {}
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5% error rate threshold
            'response_time': 2000,  # 2 seconds
            'memory_usage': 0.85  # 85% memory usage
        }
        self.max_history_size = 100

    async def handle(self, event: DomainEvent) -> None:
        """Handle system monitoring events."""
        if isinstance(event, SystemHealthEvent):
            await self._handle_system_health(event)
        elif isinstance(event, ErrorOccurredEvent):
            await self._handle_error_occurred(event)
        elif hasattr(event, 'execution_time_ms'):
            await self._handle_performance_event(event)

    async def _handle_system_health(self, event: SystemHealthEvent) -> None:
        """Track system health status changes."""
        component = event.component

        if component not in self.health_history:
            self.health_history[component] = []

        health_record = {
            'timestamp': event.occurred_at,
            'status': event.health_status,
            'metrics': event.metrics,
            'previous_status': event.previous_status
        }

        self.health_history[component].append(health_record)

        # Limit history size
        if len(self.health_history[component]) > self.max_history_size:
            self.health_history[component] = self.health_history[component][-self.max_history_size:]

        # Check for alerts
        if event.health_status in ['degraded', 'unhealthy']:
            await self._trigger_health_alert(event)

        logger.info(
            f"System health update: {component} -> {event.health_status}",
            extra={
                'component': component,
                'status': event.health_status,
                'previous_status': event.previous_status,
                'metrics': event.metrics
            }
        )

    async def _handle_error_occurred(self, event: ErrorOccurredEvent) -> None:
        """Track error occurrences for alerting."""
        logger.error(
            f"System error in {event.component}: {event.error_message}",
            extra={
                'component': event.component,
                'error_type': event.error_type,
                'user_id': event.user_id,
                'request_id': event.request_id,
                'severity': event.metadata.get('error_severity')
            }
        )

        # Could trigger alerts based on error frequency/severity
        if event.metadata.get('error_severity') == 'critical':
            await self._trigger_error_alert(event)

    async def _handle_performance_event(self, event: DomainEvent) -> None:
        """Monitor performance metrics from events."""
        if hasattr(event, 'execution_time_ms'):
            execution_time = event.execution_time_ms

            # Log slow operations
            if execution_time > self.alert_thresholds['response_time']:
                logger.warning(
                    f"Slow operation detected: {event.event_type} took {execution_time:.1f}ms",
                    extra={
                        'event_type': event.event_type,
                        'execution_time_ms': execution_time,
                        'event_id': event.event_id
                    }
                )

    async def _trigger_health_alert(self, event: SystemHealthEvent) -> None:
        """Trigger health alert for degraded/unhealthy components."""
        # In a real system, this would send notifications, create tickets, etc.
        logger.warning(
            f"HEALTH ALERT: {event.component} status changed to {event.health_status}",
            extra={
                'alert_type': 'health',
                'component': event.component,
                'status': event.health_status,
                'metrics': event.metrics
            }
        )

    async def _trigger_error_alert(self, event: ErrorOccurredEvent) -> None:
        """Trigger alert for critical errors."""
        logger.critical(
            f"CRITICAL ERROR ALERT: {event.error_type} in {event.component}",
            extra={
                'alert_type': 'critical_error',
                'component': event.component,
                'error_type': event.error_type,
                'error_message': event.error_message
            }
        )

    def get_health_summary(self) -> dict[str, Any]:
        """Get system health summary."""
        summary = {}

        for component, history in self.health_history.items():
            if history:
                latest = history[-1]
                summary[component] = {
                    'current_status': latest['status'],
                    'last_update': latest['timestamp'],
                    'recent_changes': len([h for h in history[-10:] if h['status'] != latest['status']]),
                    'metrics': latest.get('metrics', {})
                }

        return summary


class NotificationHandler(EventHandler):
    """
    Handler for sending notifications based on events.

    Manages user notifications for important system events.
    """

    def __init__(self):
        self.notification_queue: list = []
        self.user_preferences: dict[str, dict[str, bool]] = {}

    async def handle(self, event: DomainEvent) -> None:
        """Handle events that should trigger notifications."""
        # Check if event warrants notification
        if await self._should_notify(event):
            notification = await self._create_notification(event)
            if notification:
                self.notification_queue.append(notification)
                await self._send_notification(notification)

    async def _should_notify(self, event: DomainEvent) -> bool:
        """Determine if event should trigger a notification."""
        # Define notification triggers
        notification_events = {
            ImportanceUpdatedEvent: lambda e: e.metadata.get('significant_change', False),
            SystemHealthEvent: lambda e: e.health_status in ['degraded', 'unhealthy'],
            ErrorOccurredEvent: lambda e: e.metadata.get('error_severity') in ['critical', 'high']
        }

        event_type = type(event)
        if event_type in notification_events:
            return notification_events[event_type](event)

        return False

    async def _create_notification(self, event: DomainEvent) -> Optional[dict[str, Any]]:
        """Create notification from event."""
        notification_templates = {
            ImportanceUpdatedEvent: {
                'title': 'Memory Importance Updated',
                'message': 'Memory importance changed significantly',
                'category': 'memory_update'
            },
            SystemHealthEvent: {
                'title': 'System Health Alert',
                'message': f'Component {getattr(event, "component", "unknown")} is {getattr(event, "health_status", "unknown")}',
                'category': 'system_health'
            },
            ErrorOccurredEvent: {
                'title': 'System Error',
                'message': f'Critical error in {getattr(event, "component", "unknown")}',
                'category': 'system_error'
            }
        }

        template = notification_templates.get(type(event))
        if not template:
            return None

        return {
            'id': f"notif_{event.event_id}",
            'event_id': event.event_id,
            'user_id': getattr(event, 'user_id', None),
            'title': template['title'],
            'message': template['message'],
            'category': template['category'],
            'created_at': event.occurred_at,
            'read': False
        }

    async def _send_notification(self, notification: dict[str, Any]) -> None:
        """Send notification to user."""
        # In a real system, this would:
        # - Send email/SMS/push notification
        # - Store in notification table
        # - Send via WebSocket for real-time updates

        logger.info(
            f"Notification: {notification['title']}",
            extra={
                'notification_id': notification['id'],
                'user_id': notification.get('user_id'),
                'category': notification['category'],
                'message': notification['message']
            }
        )

    def get_notifications(self, user_id: str, limit: int = 10) -> list:
        """Get recent notifications for a user."""
        user_notifications = [
            n for n in self.notification_queue
            if n.get('user_id') == user_id or n.get('user_id') is None
        ]

        # Sort by creation time, most recent first
        user_notifications.sort(key=lambda x: x['created_at'], reverse=True)

        return user_notifications[:limit]
