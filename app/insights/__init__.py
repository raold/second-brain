"""
AI-powered insights and pattern discovery module for Second Brain v2.5.0

This module provides intelligent analysis of memory patterns, usage statistics,
and personalized insights to help users understand their knowledge evolution.
"""

from .analytics_engine import AnalyticsEngine
from .cluster_analyzer import ClusterAnalyzer
from .gap_detector import KnowledgeGapDetector
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
    KnowledgeGap,
    LearningProgress,
    MemoryCluster,
    Pattern,
    PatternDetectionRequest,
    PatternResponse,
    PatternType,
    TimeFrame,
    UsageStatistics,
)
from .pattern_detector import PatternDetector

__all__ = [
    # Models
    "InsightType",
    "PatternType",
    "TimeFrame",
    "Insight",
    "Pattern",
    "MemoryCluster",
    "KnowledgeGap",
    "UsageStatistics",
    "LearningProgress",
    "InsightRequest",
    "PatternDetectionRequest",
    "ClusteringRequest",
    "GapAnalysisRequest",
    "InsightResponse",
    "PatternResponse",
    "ClusterResponse",
    "GapAnalysisResponse",

    # Core Components
    "PatternDetector",
    "ClusterAnalyzer",
    "KnowledgeGapDetector",
    "InsightGenerator",
    "AnalyticsEngine"
]
