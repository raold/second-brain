"""
Domain events for the Second Brain application.

Domain events represent significant business occurrences that other
parts of the system might be interested in handling.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """
    Base class for all domain events.

    Domain events represent something significant that happened in the domain
    that domain experts care about and that other bounded contexts might
    want to be informed of.
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    event_version: str = "1.0"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Return the event type name."""
        return self.__class__.__name__


@dataclass
class MemoryCreatedEvent(DomainEvent):
    """
    Event raised when a new memory is created.
    """
    memory_id: str = ""
    user_id: str = ""
    content: str = ""
    memory_type: str = ""
    importance_score: float = 0.5

    def __post_init__(self):
        self.metadata.update({
            'content_length': len(self.content),
            'has_high_importance': self.importance_score > 0.8
        })


@dataclass
class MemoryUpdatedEvent(DomainEvent):
    """
    Event raised when a memory is updated.
    """
    memory_id: str = ""
    user_id: str = ""
    old_content: str = ""
    new_content: str = ""
    old_importance: float = 0.0
    new_importance: float = 0.0
    update_type: str = "content"  # 'content', 'importance', 'metadata'

    def __post_init__(self):
        self.metadata.update({
            'content_changed': self.old_content != self.new_content,
            'importance_changed': self.old_importance != self.new_importance,
            'importance_delta': self.new_importance - self.old_importance
        })


@dataclass
class MemoryAccessedEvent(DomainEvent):
    """
    Event raised when a memory is accessed (viewed, searched, etc.).
    """
    memory_id: str = ""
    user_id: str = ""
    access_type: str = "view"  # 'view', 'search_result', 'related_fetch'
    access_context: Optional[str] = None

    def __post_init__(self):
        self.metadata.update({
            'has_context': self.access_context is not None,
            'is_search_related': self.access_type in ['search_result', 'related_fetch']
        })


@dataclass
class ImportanceUpdatedEvent(DomainEvent):
    """
    Event raised when a memory's importance score is updated.
    """
    memory_id: str = ""
    user_id: str = ""
    old_score: float = 0.0
    new_score: float = 0.0
    reason: str = "manual"  # 'manual', 'access_pattern', 'time_decay', 'algorithm'
    algorithm_version: Optional[str] = None

    def __post_init__(self):
        score_change = self.new_score - self.old_score
        self.metadata.update({
            'score_delta': score_change,
            'score_increased': score_change > 0,
            'significant_change': abs(score_change) > 0.1,
            'crossed_threshold': (self.old_score < 0.8 <= self.new_score) or (self.new_score < 0.8 <= self.old_score)
        })


@dataclass
class SearchPerformedEvent(DomainEvent):
    """
    Event raised when a search is performed.
    """
    user_id: str = ""
    search_query: str = ""
    search_type: str = "content"  # 'content', 'semantic', 'contextual'
    results_count: int = 0
    execution_time_ms: float = 0.0
    filters_applied: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.metadata.update({
            'query_length': len(self.search_query),
            'has_results': self.results_count > 0,
            'has_filters': bool(self.filters_applied),
            'is_slow_query': self.execution_time_ms > 1000,
            'result_quality': 'high' if self.results_count > 5 else 'low' if self.results_count == 0 else 'medium'
        })


@dataclass
class SessionCreatedEvent(DomainEvent):
    """
    Event raised when a new user session is created.
    """
    session_id: str = ""
    user_id: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def __post_init__(self):
        self.metadata.update({
            'has_ip': self.ip_address is not None,
            'has_user_agent': self.user_agent is not None
        })


@dataclass
class SessionExpiredEvent(DomainEvent):
    """
    Event raised when a user session expires.
    """
    session_id: str = ""
    user_id: str = ""
    session_duration_minutes: float = 0.0
    reason: str = "timeout"  # 'timeout', 'manual_logout', 'forced_logout'

    def __post_init__(self):
        self.metadata.update({
            'long_session': self.session_duration_minutes > 120,  # > 2 hours
            'premature_end': self.reason in ['manual_logout', 'forced_logout']
        })


@dataclass
class SystemHealthEvent(DomainEvent):
    """
    Event raised for system health monitoring.
    """
    component: str = ""  # 'database', 'memory_service', 'search_engine', 'api'
    health_status: str = "healthy"  # 'healthy', 'degraded', 'unhealthy'
    metrics: dict[str, float] = field(default_factory=dict)
    previous_status: Optional[str] = None

    def __post_init__(self):
        self.metadata.update({
            'status_changed': self.previous_status and self.previous_status != self.health_status,
            'status_improved': self.previous_status == 'unhealthy' and self.health_status in ['healthy', 'degraded'],
            'status_degraded': self.previous_status == 'healthy' and self.health_status in ['degraded', 'unhealthy'],
            'critical_component': self.component in ['database', 'api'],
            'has_metrics': bool(self.metrics)
        })


@dataclass
class UserAnalyticsEvent(DomainEvent):
    """
    Event for tracking user behavior analytics.
    """
    user_id: str = ""
    action: str = ""  # 'login', 'memory_created', 'search', 'view_dashboard'
    context: dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None

    def __post_init__(self):
        self.metadata.update({
            'has_duration': self.duration_ms is not None,
            'has_context': bool(self.context),
            'action_category': self._categorize_action(self.action)
        })

    def _categorize_action(self, action: str) -> str:
        """Categorize action for analytics purposes."""
        if action in ['login', 'logout', 'session_start']:
            return 'authentication'
        elif action in ['memory_created', 'memory_updated', 'memory_deleted']:
            return 'content_management'
        elif action in ['search', 'browse', 'view']:
            return 'content_consumption'
        elif action in ['view_dashboard', 'view_analytics', 'export']:
            return 'analytics'
        else:
            return 'other'


@dataclass
class ErrorOccurredEvent(DomainEvent):
    """
    Event raised when an error occurs in the system.
    """
    error_type: str = ""
    error_message: str = ""
    component: str = ""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    stack_trace: Optional[str] = None

    def __post_init__(self):
        self.metadata.update({
            'has_user_context': self.user_id is not None,
            'has_request_context': self.request_id is not None,
            'has_stack_trace': self.stack_trace is not None,
            'error_severity': self._determine_severity()
        })

    def _determine_severity(self) -> str:
        """Determine error severity based on type and component."""
        if self.error_type in ['DatabaseError', 'ConnectionError']:
            return 'critical'
        elif self.component in ['database', 'api']:
            return 'high'
        elif 'validation' in self.error_type.lower():
            return 'low'
        else:
            return 'medium'


# Factory functions for common event creation scenarios

def create_memory_event(
    memory_id: str,
    user_id: str,
    event_type: str,
    **kwargs
) -> DomainEvent:
    """Factory function to create memory-related events."""
    event_map = {
        'created': MemoryCreatedEvent,
        'updated': MemoryUpdatedEvent,
        'accessed': MemoryAccessedEvent,
        'importance_updated': ImportanceUpdatedEvent
    }

    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown memory event type: {event_type}")

    return event_class(
        memory_id=memory_id,
        user_id=user_id,
        **kwargs
    )


def create_session_event(
    session_id: str,
    user_id: str,
    event_type: str,
    **kwargs
) -> DomainEvent:
    """Factory function to create session-related events."""
    event_map = {
        'created': SessionCreatedEvent,
        'expired': SessionExpiredEvent
    }

    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown session event type: {event_type}")

    return event_class(
        session_id=session_id,
        user_id=user_id,
        **kwargs
    )


def create_system_event(
    component: str,
    health_status: str,
    **kwargs
) -> SystemHealthEvent:
    """Factory function to create system health events."""
    return SystemHealthEvent(
        component=component,
        health_status=health_status,
        **kwargs
    )
