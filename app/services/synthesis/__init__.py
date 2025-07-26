"""
Synthesis Services - v3.0.0

This module contains service implementations for synthesis features including:
- Advanced synthesis engine with hierarchical processing
- Consolidation engine for deduplication
- Graph metrics service for knowledge graph analysis
- Knowledge summarizer with LLM integration
- Suggestion engine for smart recommendations
- Report generation service
- Spaced repetition scheduler
- WebSocket event service
"""

# Core synthesis services
from .advanced_synthesis import AdvancedSynthesisEngine, ThemeCluster
from .consolidation_engine import ConsolidationEngine, MemorySimilarity
from .graph_metrics_service import GraphMetricsService, GraphNode
from .knowledge_summarizer import KnowledgeSummarizer, KnowledgeDomain
from .suggestion_engine import SuggestionEngine, UserBehaviorProfile

# Legacy services (kept for compatibility)
try:
    from .repetition_scheduler import RepetitionScheduler, SpacedRepetitionEngine
except ImportError:
    RepetitionScheduler = None
    SpacedRepetitionEngine = None

try:
    from .report_generator import ReportGenerator, ReportGeneratorConfig
except ImportError:
    ReportGenerator = None
    ReportGeneratorConfig = None

try:
    from .websocket_service import ConnectionManager, EventBroadcaster, WebSocketService
except ImportError:
    ConnectionManager = None
    EventBroadcaster = None
    WebSocketService = None

__all__ = [
    # Core synthesis services
    "AdvancedSynthesisEngine",
    "ThemeCluster",
    "ConsolidationEngine",
    "MemorySimilarity",
    "GraphMetricsService",
    "GraphNode",
    "KnowledgeSummarizer",
    "KnowledgeDomain",
    "SuggestionEngine",
    "UserBehaviorProfile",
    # Legacy services (if available)
    "ReportGenerator",
    "ReportGeneratorConfig",
    "RepetitionScheduler",
    "SpacedRepetitionEngine",
    "WebSocketService",
    "ConnectionManager",
    "EventBroadcaster",
]
