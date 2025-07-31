"""
Synthesis Models - v2.8.2

This module contains data models for the synthesis features including:
- Report generation models
- Spaced repetition models
- WebSocket event models
"""

from .advanced_models import (
    SynthesisStrategy,
    ExportFormat,
    SynthesisRequest,
    SynthesisResult,
    AdvancedSynthesisRequest,
    AdvancedSynthesisResult,
    SynthesisOptions,
    ThemeAnalysis,
)
from .consolidation_models import (
    ConsolidationStrategy,
    MergeStrategy,
    ConsolidationRequest,
    ConsolidationResult,
    ConsolidationStatus,
    ConsolidatedMemory,
    ConsolidationCandidate,
    ConsolidationPreview,
    QualityAssessment,
    DuplicateGroup,
)
from .summary_models import (
    SummaryType,
    FormatType,
    SummaryRequest,
    SummarySegment,
    SummaryResponse,
    SummaryResult,
    TopicSummary,
    DomainOverview,
    KeyInsight,
)
from .suggestion_models import (
    SuggestionType,
    ActionType,
    Suggestion,
    LearningPathSuggestion,
    ContentSuggestion,
    OrganizationSuggestion,
    SuggestionRequest,
    SuggestionResponse,
)
from .metrics_models import (
    GraphMetrics,
    NodeMetrics,
    MetricsRequest,
    ClusterMetrics,
    ConnectivityMetrics,
    TemporalMetrics,
    KnowledgeCluster,
)
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
    # Advanced synthesis models
    "SynthesisStrategy",
    "ExportFormat",
    "SynthesisRequest",
    "SynthesisResult",
    "AdvancedSynthesisRequest",
    "AdvancedSynthesisResult",
    "SynthesisOptions",
    "ThemeAnalysis",
    # Consolidation models
    "ConsolidationStrategy",
    "MergeStrategy",
    "ConsolidationRequest",
    "ConsolidationResult",
    "ConsolidationStatus",
    "ConsolidatedMemory",
    "ConsolidationCandidate",
    "ConsolidationPreview",
    "QualityAssessment",
    "DuplicateGroup",
    # Summary models
    "SummaryType",
    "FormatType",
    "SummaryRequest",
    "SummarySegment",
    "SummaryResponse",
    "SummaryResult",
    "TopicSummary",
    "DomainOverview",
    "KeyInsight",
    # Suggestion models
    "SuggestionType",
    "ActionType",
    "Suggestion",
    "LearningPathSuggestion",
    "ContentSuggestion",
    "OrganizationSuggestion",
    "SuggestionRequest",
    "SuggestionResponse",
    # Metrics models
    "GraphMetrics",
    "NodeMetrics",
    "MetricsRequest",
    "ClusterMetrics",
    "ConnectivityMetrics",
    "TemporalMetrics",
    "KnowledgeCluster",
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
