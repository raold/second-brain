"""
Synthesis services for v2.8.2
Knowledge consolidation, summarization, and intelligent automation
"""

from app.services.synthesis.consolidation_engine import MemoryConsolidationEngine
from app.services.synthesis.graph_cache import GraphCacheService, get_cache_service
from app.services.synthesis.graph_metrics_service import GraphMetricsService
from app.services.synthesis.knowledge_summarizer import KnowledgeSummarizer
from app.services.synthesis.suggestion_engine import SmartSuggestionEngine

__all__ = [
    "MemoryConsolidationEngine",
    "KnowledgeSummarizer",
    "SmartSuggestionEngine",
    "GraphMetricsService",
    "GraphCacheService",
    "get_cache_service"
]
