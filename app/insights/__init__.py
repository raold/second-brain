"""
Insights module for Second Brain - Advanced analytics and pattern detection
"""

from .analytics_engine import AnalyticsEngine
from .cluster_analyzer import ClusterAnalyzer
from .gap_detector import KnowledgeGapDetector as GapDetector
from .insight_generator import InsightGenerator
from .models import (
    Insight,
    InsightType,
    InsightRequest,
    InsightResponse,
    TrendAnalysis,
    PatternDetection,
    ClusteringRequest
)
from .pattern_detector import PatternDetector

__all__ = [
    "AnalyticsEngine",
    "ClusterAnalyzer", 
    "GapDetector",
    "InsightGenerator",
    "Insight",
    "InsightType",
    "InsightRequest",
    "InsightResponse",
    "TrendAnalysis",
    "PatternDetection",
    "ClusteringRequest",
    "PatternDetector",
]