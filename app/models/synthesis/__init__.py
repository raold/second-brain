"""
Synthesis Models - v2.8.2

This module contains data models for the synthesis features including:
- Report generation models
- Spaced repetition models
- WebSocket event models
"""

from .report_models import (
    ReportType,
    ReportFormat,
    ReportConfig,
    ReportRequest,
    ReportResponse,
    ReportSchedule,
    ReportTemplate,
    ReportFilter,
)

from .repetition_models import (
    RepetitionAlgorithm,
    ReviewDifficulty,
    ReviewStatus,
    MemoryStrength,
    ReviewSchedule,
    RepetitionConfig,
    ReviewSession,
    LearningStatistics,
    BulkReviewRequest,
)

from .websocket_models import (
    EventType,
    WebSocketEvent,
    WebSocketMessage,
    SubscriptionRequest,
    ConnectionStatus,
    EventSubscription,
    WebSocketMetrics,
)

__all__ = [
    # Report models
    "ReportType",
    "ReportFormat",
    "ReportConfig",
    "ReportRequest",
    "ReportResponse",
    "ReportSchedule",
    "ReportTemplate",
    "ReportFilter",
    # Repetition models
    "RepetitionAlgorithm",
    "ReviewDifficulty",
    "ReviewStatus",
    "MemoryStrength",
    "ReviewSchedule",
    "RepetitionConfig",
    "ReviewSession",
    "LearningStatistics",
    "BulkReviewRequest",
    # WebSocket models
    "EventType",
    "WebSocketEvent",
    "WebSocketMessage",
    "SubscriptionRequest",
    "ConnectionStatus",
    "EventSubscription",
    "WebSocketMetrics",
]