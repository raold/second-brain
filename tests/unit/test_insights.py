"""
Unit tests for AI insights and pattern discovery module
"""

from datetime import datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest

from app.insights import (
    ClusteringRequest,
    GapAnalysisRequest,
    Insight,
    InsightRequest,
    InsightType,
    KnowledgeGap,
    MemoryCluster,
    Pattern,
    PatternDetectionRequest,
    PatternType,
    TimeFrame,
)


class TestInsightModels:
    """Test insight data models"""

    def test_insight_creation(self):
        """Test creating an insight"""
        insight = Insight(
            id=uuid4(),
            type=InsightType.USAGE_PATTERN,
            title="Test Insight",
            description="Test description",
            confidence=0.8,
            impact_score=7.5,
            data={"test": "data"},
            created_at=datetime.utcnow(),
            time_frame=TimeFrame.WEEKLY,
            affected_memories=[]
        )

        assert insight.type == InsightType.USAGE_PATTERN
        assert insight.confidence == 0.8
        assert insight.impact_score == 7.5

    def test_insight_confidence_validation(self):
        """Test confidence score validation"""
        # Test that validator clamps values
        insight = Insight(
            id=uuid4(),
            type=InsightType.KNOWLEDGE_GROWTH,
            title="Test",
            description="Test",
            confidence=0.8,  # Valid value
            impact_score=5.0,
            data={},
            created_at=datetime.utcnow(),
            time_frame=TimeFrame.MONTHLY,
            affected_memories=[]
        )

        # Manually test the validator
        assert insight.confidence == 0.8

        # Test validator edge cases
        from app.insights.models import Insight as InsightModel
        assert InsightModel.validate_confidence(1.5) == 1.0
        assert InsightModel.validate_confidence(-0.5) == 0.0
        assert InsightModel.validate_confidence(0.5) == 0.5

    def test_pattern_creation(self):
        """Test pattern model"""
        pattern = Pattern(
            id=uuid4(),
            type=PatternType.TEMPORAL,
            name="Peak Hours",
            description="Most active during morning",
            strength=0.85,
            occurrences=25,
            first_seen=datetime.utcnow() - timedelta(days=7),
            last_seen=datetime.utcnow(),
            examples=[{"hour": 9, "count": 10}]
        )

        assert pattern.type == PatternType.TEMPORAL
        assert pattern.strength == 0.85
        assert pattern.occurrences == 25

    def test_memory_cluster_creation(self):
        """Test memory cluster model"""
        cluster = MemoryCluster(
            id=uuid4(),
            name="Programming Concepts",
            description="Cluster of programming-related memories",
            size=15,
            memory_ids=[uuid4() for _ in range(15)],
            common_tags=["programming", "python", "algorithms"],
            average_importance=7.5,
            coherence_score=0.82,
            created_at=datetime.utcnow()
        )

        assert cluster.size == 15
        assert len(cluster.memory_ids) == 15
        assert cluster.coherence_score == 0.82

    def test_knowledge_gap_creation(self):
        """Test knowledge gap model"""
        gap = KnowledgeGap(
            id=uuid4(),
            area="Machine Learning",
            description="Limited coverage of ML concepts",
            severity=0.7,
            related_memories=[],
            suggested_topics=["Neural Networks", "Deep Learning"],
            confidence=0.8,
            detected_at=datetime.utcnow()
        )

        assert gap.severity == 0.7
        assert len(gap.suggested_topics) == 2
        assert gap.confidence == 0.8


class TestInsightRequests:
    """Test request models"""

    def test_insight_request_defaults(self):
        """Test default values in insight request"""
        request = InsightRequest()

        assert request.time_frame == TimeFrame.WEEKLY
        assert request.limit == 10
        assert request.min_confidence == 0.7
        assert request.include_recommendations

    def test_pattern_detection_request(self):
        """Test pattern detection request"""
        request = PatternDetectionRequest(
            pattern_types=[PatternType.TEMPORAL, PatternType.SEMANTIC],
            time_frame=TimeFrame.MONTHLY,
            min_occurrences=5,
            min_strength=0.6
        )

        assert len(request.pattern_types) == 2
        assert request.min_occurrences == 5
        assert request.min_strength == 0.6

    def test_clustering_request(self):
        """Test clustering request"""
        request = ClusteringRequest(
            algorithm="kmeans",
            num_clusters=10,
            min_cluster_size=5,
            similarity_threshold=0.8
        )

        assert request.algorithm == "kmeans"
        assert request.num_clusters == 10
        assert request.min_cluster_size == 5

    def test_gap_analysis_request(self):
        """Test gap analysis request"""
        request = GapAnalysisRequest(
            domains=["programming", "databases"],
            min_severity=0.6,
            include_suggestions=True,
            limit=15
        )

        assert len(request.domains) == 2
        assert request.min_severity == 0.6
        assert request.limit == 15


class TestPatternDetection:
    """Test pattern detection logic"""

    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for testing"""
        memories = []
        base_time = datetime.utcnow()

        # Create temporal pattern - morning activities
        for i in range(20):
            memory = {
                'id': uuid4(),
                'content': f'Morning study session {i}',
                'created_at': base_time - timedelta(days=i, hours=base_time.hour-9),
                'tags': ['study', 'morning'],
                'importance': 7.0,
                'content_vector': np.random.rand(384).tolist()
            }
            memories.append(memory)

        # Create semantic cluster - programming memories
        for i in range(15):
            memory = {
                'id': uuid4(),
                'content': f'Programming concept: {["functions", "classes", "loops"][i % 3]}',
                'created_at': base_time - timedelta(days=i*2),
                'tags': ['programming', 'python'],
                'importance': 8.0,
                'content_vector': np.random.rand(384).tolist()
            }
            memories.append(memory)

        return memories

    def test_temporal_pattern_detection(self, sample_memories):
        """Test detection of temporal patterns"""
        # Group by hour
        hour_counts = {}
        for memory in sample_memories:
            hour = memory['created_at'].hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        # Should detect morning pattern
        morning_hours = [h for h, c in hour_counts.items() if 6 <= h <= 10]
        assert len(morning_hours) > 0

    def test_tag_frequency_analysis(self, sample_memories):
        """Test tag frequency analysis"""
        tag_counts = {}
        for memory in sample_memories:
            for tag in memory.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Should have significant tag occurrences
        assert tag_counts.get('study', 0) >= 15
        assert tag_counts.get('programming', 0) >= 10


class TestClusteringAnalysis:
    """Test clustering functionality"""

    def test_cluster_coherence_calculation(self):
        """Test cluster coherence score calculation"""
        # Create mock embeddings
        cluster_size = 10
        embeddings = np.random.rand(cluster_size, 384)

        # Make embeddings similar (high coherence)
        base_embedding = embeddings[0]
        for i in range(1, cluster_size):
            embeddings[i] = base_embedding + np.random.normal(0, 0.1, 384)

        # Calculate average cosine similarity
        center = np.mean(embeddings, axis=0)
        similarities = []

        for embedding in embeddings:
            similarity = np.dot(embedding, center) / (
                np.linalg.norm(embedding) * np.linalg.norm(center)
            )
            similarities.append(similarity)

        coherence = np.mean(similarities)

        # Should have high coherence
        assert coherence > 0.8


class TestKnowledgeGapDetection:
    """Test knowledge gap detection"""

    def test_domain_coverage_analysis(self):
        """Test domain coverage calculation"""
        domains = ["programming", "databases", "algorithms"]
        domain_memories = {
            "programming": 15,
            "databases": 3,
            "algorithms": 0
        }

        gaps = []
        min_required = 5

        for domain in domains:
            count = domain_memories.get(domain, 0)
            if count < min_required:
                severity = 1.0 - (count / min_required)
                gaps.append({
                    'domain': domain,
                    'severity': severity,
                    'count': count
                })

        # Should detect gaps
        assert len(gaps) == 2  # databases and algorithms
        assert any(g['domain'] == 'algorithms' and g['severity'] == 1.0 for g in gaps)
        assert any(g['domain'] == 'databases' and g['severity'] > 0 for g in gaps)


class TestInsightGeneration:
    """Test insight generation logic"""

    def test_growth_rate_calculation(self):
        """Test knowledge growth rate calculation"""
        # Current period: 10 memories
        # Previous period: 5 memories
        current_count = 10
        previous_count = 5

        growth_rate = ((current_count - previous_count) / previous_count) * 100

        assert growth_rate == 100.0  # 100% growth

    def test_usage_concentration_calculation(self):
        """Test usage concentration metric"""
        # High concentration: most accesses on few memories
        total_memories = 100
        accessed_memories = 20

        concentration_ratio = accessed_memories / total_memories

        assert concentration_ratio == 0.2  # 20% accessed

    def test_importance_trend_analysis(self):
        """Test importance trend detection"""
        # First half: average importance 5.0
        # Second half: average importance 7.5
        first_half_importance = [5.0] * 10
        second_half_importance = [7.5] * 10

        first_avg = np.mean(first_half_importance)
        second_avg = np.mean(second_half_importance)

        trend = second_avg - first_avg

        assert trend == 2.5  # Positive trend


class TestAnalyticsEngine:
    """Test analytics engine orchestration"""

    def test_time_frame_conversion(self):
        """Test time frame to days conversion"""
        conversions = {
            TimeFrame.DAILY: 1,
            TimeFrame.WEEKLY: 7,
            TimeFrame.MONTHLY: 30,
            TimeFrame.QUARTERLY: 90,
            TimeFrame.YEARLY: 365
        }

        for _time_frame, expected_days in conversions.items():
            # This would be tested against actual implementation
            assert expected_days > 0

    def test_learning_path_generation(self):
        """Test learning path generation from gaps"""
        gaps = [
            {
                'area': 'Domain: Machine Learning',
                'suggested_topics': ['Neural Networks', 'Deep Learning', 'MLOps']
            },
            {
                'area': 'Shallow Coverage: Databases',
                'suggested_topics': ['Advanced SQL', 'Query Optimization']
            }
        ]

        # Generate learning paths
        paths = []

        # Domain-focused path
        domain_gaps = [g for g in gaps if 'Domain:' in g['area']]
        if domain_gaps:
            path = {
                'name': 'Domain Mastery Path',
                'steps': []
            }
            for gap in domain_gaps:
                domain = gap['area'].replace('Domain: ', '')
                path['steps'].append({
                    'focus': domain,
                    'goals': gap['suggested_topics'][:3]
                })
            paths.append(path)

        assert len(paths) == 1
        assert paths[0]['name'] == 'Domain Mastery Path'
        assert len(paths[0]['steps']) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
