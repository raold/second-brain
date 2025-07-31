"""
Insights module for Second Brain - Advanced analytics and pattern detection
"""

from .analytics_engine import AnalyticsEngine
from .cluster_analyzer import ClusterAnalyzer
from .gap_detector import KnowledgeGapDetector as GapDetector
from .insight_generator import InsightGenerator
from .models import (
    ClusteringRequest,
    ClusterResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
    Insight,
    InsightRequest,
    InsightResponse,
    InsightType,
    LearningProgress,
    PatternDetection,
    PatternDetectionRequest,
    PatternResponse,
    TimeFrame,
    TrendAnalysis,
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
    "ClusterResponse",
    "GapAnalysisRequest",
    "GapAnalysisResponse",
    "LearningProgress",
    "PatternDetectionRequest",
    "PatternResponse",
    "TimeFrame",
    "PatternDetector",
]
