"""
API routes for AI-powered insights and analytics
"""


from fastapi import APIRouter, Depends, HTTPException, Query

from app.insights import (
    AnalyticsEngine,
    ClusteringRequest,
    ClusterResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
    InsightRequest,
    InsightResponse,
    LearningProgress,
    PatternDetectionRequest,
    PatternResponse,
    TimeFrame,
)
from app.shared import verify_api_key
from app.dependencies import get_current_user, get_db_instance

router = APIRouter(
    prefix="/insights",
    tags=["Insights & Analytics"],
    dependencies=[Depends(verify_api_key)]
)


@router.post(
    "/generate",
    response_model=InsightResponse,
    summary="Generate AI-powered insights",
    description="Generate personalized insights from memory patterns and usage statistics"
)
async def generate_insights(
    request: InsightRequest,
    db=Depends(get_db_instance)
):
    """Generate AI-powered insights based on memory analysis"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.generate_insights(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.post(
    "/patterns",
    response_model=PatternResponse,
    summary="Detect patterns",
    description="Detect patterns in memory usage, content, and behavior"
)
async def detect_patterns(
    request: PatternDetectionRequest,
    db=Depends(get_db_instance)
):
    """Detect various patterns in memory data"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.detect_patterns(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect patterns: {str(e)}"
        )


@router.post(
    "/clusters",
    response_model=ClusterResponse,
    summary="Analyze memory clusters",
    description="Group memories into semantic clusters for better organization"
)
async def analyze_clusters(
    request: ClusteringRequest,
    db=Depends(get_db_instance)
):
    """Perform clustering analysis on memories"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.analyze_clusters(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze clusters: {str(e)}"
        )


@router.post(
    "/gaps",
    response_model=GapAnalysisResponse,
    summary="Analyze knowledge gaps",
    description="Identify gaps in knowledge coverage and suggest improvements"
)
async def analyze_knowledge_gaps(
    request: GapAnalysisRequest,
    db=Depends(get_db_instance)
):
    """Analyze knowledge gaps and suggest learning paths"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.analyze_knowledge_gaps(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze knowledge gaps: {str(e)}"
        )


@router.get(
    "/progress",
    response_model=LearningProgress,
    summary="Get learning progress",
    description="Track learning progress and achievement metrics"
)
async def get_learning_progress(
    time_frame: TimeFrame = Query(
        default=TimeFrame.MONTHLY,
        description="Time frame for progress calculation"
    ),
    db=Depends(get_db_instance)
):
    """Get learning progress metrics"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.get_learning_progress(time_frame)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get learning progress: {str(e)}"
        )


@router.get(
    "/analytics",
    summary="Get comprehensive analytics",
    description="Get all analytics data in one call (insights, patterns, clusters, gaps, progress)"
)
async def get_comprehensive_analytics(
    time_frame: TimeFrame = Query(
        default=TimeFrame.MONTHLY,
        description="Time frame for analytics"
    ),
    db=Depends(get_db_instance)
):
    """Get comprehensive analytics dashboard data"""
    try:
        engine = AnalyticsEngine(db)
        return await engine.get_comprehensive_analytics(time_frame)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get comprehensive analytics: {str(e)}"
        )


@router.get(
    "/quick-insights",
    summary="Get quick insights",
    description="Get top 5 most impactful insights quickly"
)
async def get_quick_insights(
    db=Depends(get_db_instance)
):
    """Get quick insights for dashboard display"""
    try:
        engine = AnalyticsEngine(db)
        request = InsightRequest(
            time_frame=TimeFrame.WEEKLY,
            limit=5,
            min_confidence=0.7,
            include_recommendations=True
        )
        response = await engine.generate_insights(request)

        # Format for dashboard
        return {
            "insights": [
                {
                    "id": str(insight.id),
                    "title": insight.title,
                    "description": insight.description,
                    "impact": insight.impact_score,
                    "recommendations": insight.recommendations,
                    "type": insight.type.value
                }
                for insight in response.insights
            ],
            "statistics": {
                "total_memories": response.statistics.total_memories,
                "growth_rate": response.statistics.growth_rate,
                "avg_importance": response.statistics.average_importance
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quick insights: {str(e)}"
        )
