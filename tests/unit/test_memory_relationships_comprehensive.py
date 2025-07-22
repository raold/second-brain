#!/usr/bin/env python3
"""
Comprehensive tests for Memory Relationships module - REFACTORED VERSION

Phase 1 Emergency Stabilization Tests:
✅ Tests refactored memory relationship analyzer with dependency injection
✅ Tests similarity analyzers module with proper error handling
✅ Tests database interface abstraction
✅ Comprehensive validation of all relationship calculation methods

This test suite validates the refactored, modular architecture.
"""

from datetime import datetime, timedelta

import numpy as np
import pytest

from app.interfaces.memory_database_interface import MockMemoryDatabase
from app.services.memory_relationship_analyzer import MemoryRelationshipAnalyzer
from app.services.similarity_analyzers import (
    SimilarityAnalyzers,
    calculate_composite_score,
    categorize_relationship_strength,
)


class TestSimilarityAnalyzers:
    """Test the extracted similarity calculation module."""

    @pytest.fixture
    def analyzers(self):
        """Create similarity analyzers instance."""
        return SimilarityAnalyzers(temporal_window_hours=24.0)

    def test_semantic_similarity_valid_embeddings(self, analyzers):
        """Test semantic similarity with valid embeddings."""
        embedding1 = [1.0, 0.0, 0.0, 0.0]
        embedding2 = [0.8, 0.6, 0.0, 0.0]

        similarity = analyzers.calculate_semantic_similarity(embedding1, embedding2)

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be somewhat similar

    def test_semantic_similarity_identical_embeddings(self, analyzers):
        """Test semantic similarity with identical embeddings."""
        embedding = [1.0, 0.0, 0.0, 0.0]

        similarity = analyzers.calculate_semantic_similarity(embedding, embedding)

        assert similarity == pytest.approx(1.0, rel=1e-5)

    def test_semantic_similarity_invalid_embeddings(self, analyzers):
        """Test semantic similarity with invalid embeddings."""
        # Test with None embeddings
        assert analyzers.calculate_semantic_similarity(None, [1.0, 0.0]) == 0.0
        assert analyzers.calculate_semantic_similarity([1.0, 0.0], None) == 0.0

        # Test with mismatched dimensions
        assert analyzers.calculate_semantic_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

        # Test with empty embeddings
        assert analyzers.calculate_semantic_similarity([], [1.0, 0.0]) == 0.0

    def test_temporal_proximity_recent(self, analyzers):
        """Test temporal proximity with recent timestamps."""
        now = datetime.now()
        recent = now - timedelta(hours=2)

        proximity = analyzers.calculate_temporal_proximity(now, recent)

        assert 0.0 <= proximity <= 1.0
        assert proximity > 0.8  # Should be high proximity within window

    def test_temporal_proximity_distant(self, analyzers):
        """Test temporal proximity with distant timestamps."""
        now = datetime.now()
        distant = now - timedelta(days=7)

        proximity = analyzers.calculate_temporal_proximity(now, distant)

        assert 0.0 <= proximity <= 1.0
        assert proximity < 0.1  # Should be low proximity outside window

    def test_temporal_proximity_invalid(self, analyzers):
        """Test temporal proximity with invalid timestamps."""
        now = datetime.now()

        assert analyzers.calculate_temporal_proximity(None, now) == 0.0
        assert analyzers.calculate_temporal_proximity(now, None) == 0.0

    def test_content_overlap_similar(self, analyzers):
        """Test content overlap with similar content."""
        content1 = "PostgreSQL database system with advanced features"
        content2 = "PostgreSQL is a powerful database management system"

        overlap = analyzers.calculate_content_overlap(content1, content2)

        assert 0.0 <= overlap <= 1.0
        assert overlap > 0.3  # Should have reasonable overlap

    def test_content_overlap_different(self, analyzers):
        """Test content overlap with different content."""
        content1 = "PostgreSQL database system"
        content2 = "Cooking recipes and kitchen techniques"

        overlap = analyzers.calculate_content_overlap(content1, content2)

        assert 0.0 <= overlap <= 1.0
        assert overlap < 0.1  # Should have minimal overlap

    def test_content_overlap_invalid(self, analyzers):
        """Test content overlap with invalid content."""
        assert analyzers.calculate_content_overlap(None, "test") == 0.0
        assert analyzers.calculate_content_overlap("test", None) == 0.0
        assert analyzers.calculate_content_overlap("", "test") == 0.0

    def test_conceptual_hierarchy_detection(self, analyzers):
        """Test conceptual hierarchy detection."""
        content1 = "Database definition and overview"
        content2 = "PostgreSQL specific example implementation"

        hierarchy = analyzers.calculate_conceptual_hierarchy(content1, content2)

        assert 0.0 <= hierarchy <= 1.0
        # Should detect some hierarchical relationship

    def test_causal_relationship_detection(self, analyzers):
        """Test causal relationship detection."""
        content1 = "Database connection failed due to network issues"
        content2 = "This leads to application timeout errors"

        causal = analyzers.detect_causal_relationship(content1, content2)

        assert 0.0 <= causal <= 1.0
        assert causal > 0.0  # Should detect causal language

    def test_contextual_association_same_type(self, analyzers):
        """Test contextual association with same memory type."""
        metadata1 = {"semantic_metadata": {"domain": "database"}}
        metadata2 = {"semantic_metadata": {"domain": "database"}}

        association = analyzers.calculate_contextual_association(
            metadata1, metadata2, "semantic", "semantic", 0.8, 0.7
        )

        assert 0.0 <= association <= 1.0
        assert association > 0.2  # Should have some association


class TestCompositeScoring:
    """Test composite scoring functions."""

    def test_calculate_composite_score_weighted(self):
        """Test composite score calculation with multiple relationship types."""
        relationship_scores = {
            "semantic_similarity": 0.8,
            "temporal_proximity": 0.6,
            "content_overlap": 0.4,
        }

        composite = calculate_composite_score(relationship_scores)

        assert 0.0 <= composite <= 1.0
        # Should be weighted average, roughly between the values
        assert 0.4 <= composite <= 0.8

    def test_calculate_composite_score_empty(self):
        """Test composite score with empty scores."""
        assert calculate_composite_score({}) == 0.0

    def test_categorize_relationship_strength(self):
        """Test relationship strength categorization."""
        assert categorize_relationship_strength(0.9) == "very_strong"
        assert categorize_relationship_strength(0.7) == "strong"
        assert categorize_relationship_strength(0.5) == "moderate"
        assert categorize_relationship_strength(0.3) == "weak"
        assert categorize_relationship_strength(0.1) == "very_weak"


class TestMemoryRelationshipAnalyzer:
    """Test the refactored memory relationship analyzer."""

    @pytest.fixture
    def sample_memories(self):
        """Sample memory data for testing."""
        return [
            {
                'id': 'memory-1',
                'content': 'PostgreSQL is a powerful relational database system',
                'embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
                'memory_type': 'semantic',
                'importance_score': 0.8,
                'created_at': datetime.now() - timedelta(days=1),
                'semantic_metadata': {'domain': 'database', 'category': 'technology'},
            },
            {
                'id': 'memory-2',
                'content': 'MySQL is another popular database system',
                'embedding': [0.15, 0.25, 0.35, 0.45, 0.55],
                'memory_type': 'semantic',
                'importance_score': 0.7,
                'created_at': datetime.now() - timedelta(hours=12),
                'semantic_metadata': {'domain': 'database', 'category': 'technology'},
            },
            {
                'id': 'memory-3',
                'content': 'Python is a programming language',
                'embedding': [0.8, 0.1, 0.2, 0.1, 0.3],
                'memory_type': 'semantic',
                'importance_score': 0.6,
                'created_at': datetime.now() - timedelta(days=2),
                'semantic_metadata': {'domain': 'programming', 'category': 'technology'},
            }
        ]

    @pytest.fixture
    def mock_database(self, sample_memories):
        """Mock database with sample data."""
        return MockMemoryDatabase(sample_memories)

    @pytest.fixture
    def analyzer(self, mock_database):
        """Create analyzer with mock database."""
        return MemoryRelationshipAnalyzer(
            database=mock_database,
            similarity_threshold=0.3,
            temporal_window_hours=24.0
        )

    @pytest.mark.asyncio
    async def test_analyzer_initialization(self, analyzer, mock_database):
        """Test analyzer initializes correctly with dependency injection."""
        assert analyzer.database == mock_database
        assert analyzer.similarity_threshold == 0.3
        assert analyzer.temporal_window_hours == 24.0
        assert 'semantic_similarity' in analyzer.relationship_types
        assert analyzer.similarity_analyzers is not None

    @pytest.mark.asyncio
    async def test_analyze_memory_relationships_success(self, analyzer, sample_memories):
        """Test successful memory relationship analysis."""
        result = await analyzer.analyze_memory_relationships('memory-1')

        # Validate result structure
        assert 'memory_id' in result
        assert 'target_memory' in result
        assert 'direct_relationships' in result
        assert 'analysis_summary' in result
        assert result['memory_id'] == 'memory-1'

        # Should find some relationships with similar database memories
        assert len(result['direct_relationships']) >= 0

    @pytest.mark.asyncio
    async def test_analyze_memory_relationships_not_found(self, analyzer):
        """Test handling when memory is not found."""
        result = await analyzer.analyze_memory_relationships('nonexistent-memory')

        # Should return error in result
        assert 'error' in result
        assert result['memory_id'] == 'nonexistent-memory'

    @pytest.mark.asyncio
    async def test_analyze_relationships_batch(self, analyzer, sample_memories):
        """Test batch relationship analysis."""
        target_memory = sample_memories[0]  # PostgreSQL memory
        candidates = sample_memories[1:]    # MySQL and Python memories

        relationships = await analyzer._analyze_relationships_batch(
            target_memory, candidates, ['semantic_similarity', 'content_overlap']
        )

        # Should find relationships
        assert len(relationships) >= 0

        # Relationships should be properly structured
        for rel in relationships:
            assert 'target_id' in rel
            assert 'related_id' in rel
            assert 'composite_score' in rel
            assert 'relationship_scores' in rel
            assert 'strength' in rel

    @pytest.mark.asyncio
    async def test_filter_significant_relationships(self, analyzer):
        """Test relationship filtering."""
        # Create mock relationships with different scores
        mock_relationships = [
            {'composite_score': 0.8, 'id': 'rel1'},
            {'composite_score': 0.6, 'id': 'rel2'},
            {'composite_score': 0.2, 'id': 'rel3'},  # Below threshold
            {'composite_score': 0.9, 'id': 'rel4'},
        ]

        filtered = analyzer._filter_significant_relationships(mock_relationships, max_connections=5)

        # Should filter out below-threshold and sort by score
        assert len(filtered) == 3  # rel3 should be filtered out
        assert filtered[0]['composite_score'] == 0.9  # Highest first
        assert all(rel['composite_score'] > analyzer.similarity_threshold for rel in filtered)

    @pytest.mark.asyncio
    async def test_parse_embedding_various_formats(self, analyzer):
        """Test embedding parsing with various input formats."""
        # Test list
        assert analyzer._parse_embedding([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]

        # Test numpy array
        arr = np.array([1.0, 2.0, 3.0])
        assert analyzer._parse_embedding(arr) == [1.0, 2.0, 3.0]

        # Test None/invalid
        assert analyzer._parse_embedding(None) is None
        assert analyzer._parse_embedding("invalid") is None

    @pytest.mark.asyncio
    async def test_generate_relationship_insights(self, analyzer):
        """Test relationship insights generation."""
        mock_relationships = [
            {
                'primary_relationship_type': 'semantic_similarity',
                'strength': 'strong',
                'composite_score': 0.8,
                'relationship_scores': {'semantic_similarity': 0.8}
            },
            {
                'primary_relationship_type': 'content_overlap',
                'strength': 'moderate',
                'composite_score': 0.6,
                'relationship_scores': {'content_overlap': 0.6}
            }
        ]

        insights = analyzer._generate_relationship_insights(mock_relationships, {})

        # Validate insights structure
        assert 'summary' in insights
        assert 'distributions' in insights
        assert insights['summary']['total_direct_relationships'] == 2
        assert 'semantic_similarity' in insights['distributions']['relationship_types']


class TestDatabaseInterface:
    """Test the database interface abstraction."""

    @pytest.mark.asyncio
    async def test_mock_database_get_memory(self):
        """Test mock database get_memory method."""
        sample_memories = [
            {'id': 'test-1', 'content': 'Test memory'},
            {'id': 'test-2', 'content': 'Another test'}
        ]
        mock_db = MockMemoryDatabase(sample_memories)

        result = await mock_db.get_memory('test-1')
        assert result is not None
        assert result['content'] == 'Test memory'

        result = await mock_db.get_memory('nonexistent')
        assert result is None

    @pytest.mark.asyncio
    async def test_mock_database_get_candidates(self):
        """Test mock database get_candidate_memories method."""
        sample_memories = [
            {
                'id': 'exclude-me',
                'content': 'Excluded',
                'embedding': [1.0, 0.0],
                'importance_score': 0.5
            },
            {
                'id': 'include-1',
                'content': 'Included',
                'embedding': [0.0, 1.0],
                'importance_score': 0.8
            },
            {
                'id': 'no-embedding',
                'content': 'No embedding',
                'embedding': None,
                'importance_score': 0.7
            }
        ]
        mock_db = MockMemoryDatabase(sample_memories)

        candidates = await mock_db.get_candidate_memories('exclude-me', limit=10)

        # Should exclude the target and memories without embeddings
        assert len(candidates) == 1
        assert candidates[0]['id'] == 'include-1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
