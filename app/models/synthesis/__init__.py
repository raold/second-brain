"""
Synthesis Models - v2.8.2

This module contains data models for the synthesis features including:
- Report generation models
- Spaced repetition models
- WebSocket event models
"""

from .repetition_models import (
    BulkReviewRequest,
    LearningStatistics,
    MemoryStrength,
    RepetitionAlgorithm,
    RepetitionConfig,
    ReviewDifficulty,
    ReviewSchedule,
    ReviewSession,
    ReviewStatus,
)
from .report_models import (
    ReportConfig,
    ReportFilter,
    ReportFormat,
    ReportRequest,
    ReportResponse,
    ReportSchedule,
    ReportTemplate,
    ReportType,
)
from .websocket_models import (
    ConnectionStatus,
    EventSubscription,
    EventType,
    SubscriptionRequest,
    WebSocketEvent,
    WebSocketMessage,
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
