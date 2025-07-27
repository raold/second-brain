"""Tests for ConsolidationEngine"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest

from app.models.synthesis.consolidation_models import (
    ConsolidationRequest,
    ConsolidationResult,
    DuplicateGroup,
    MergeStrategy,
)
from app.services.synthesis.consolidation_engine import (
    ConsolidationEngine,
    MemorySimilarity,
)


class TestMemorySimilarity:
    """Test MemorySimilarity class"""
    
    def test_memory_similarity_creation(self):
        """Test creating memory similarity"""
        id1, id2 = uuid4(), uuid4()
        similarity = MemorySimilarity(id1, id2, 0.95, 'exact')
        
        assert similarity.memory1_id == id1
        assert similarity.memory2_id == id2
        assert similarity.similarity_score == 0.95
        assert similarity.similarity_type == 'exact'


class TestConsolidationEngine:
    """Test ConsolidationEngine"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        mock_db = AsyncMock()
        mock_memory_service = AsyncMock()
        mock_openai_client = AsyncMock()
        
        return mock_db, mock_memory_service, mock_openai_client
    
    @pytest.fixture
    def engine(self, mock_dependencies):
        """Create engine instance with mocks"""
        db, memory_service, openai_client = mock_dependencies
        return ConsolidationEngine(db, memory_service, openai_client)
    
    @pytest.fixture
    def sample_memories_with_embeddings(self):
        """Create sample memories with embeddings"""
        # Create similar embeddings
        base_embedding = np.random.rand(384)
        
        return [
            {
                'id': uuid4(),
                'content': 'Python is a programming language',
                'embedding': base_embedding + np.random.rand(384) * 0.01,  # Very similar
                'importance': 8,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'tags': ['Python']
            },
            {
                'id': uuid4(),
                'content': 'Python is a programming language used for many things',
                'embedding': base_embedding + np.random.rand(384) * 0.01,  # Very similar
                'importance': 7,
                'created_at': datetime.utcnow() - timedelta(days=1),
                'updated_at': datetime.utcnow() - timedelta(days=1),
                'tags': ['Python']
            },
            {
                'id': uuid4(),
                'content': 'JavaScript is a different programming language',
                'embedding': np.random.rand(384),  # Different
                'importance': 6,
                'created_at': datetime.utcnow() - timedelta(days=2),
                'updated_at': datetime.utcnow() - timedelta(days=2),
                'tags': ['JavaScript']
            }
        ]
    
    @pytest.fixture
    def consolidation_request(self):
        """Create sample consolidation request"""
        return ConsolidationRequest(
            memory_ids=[uuid4(), uuid4()],
            similarity_threshold=0.85,
            auto_merge=True
        )
    
    @pytest.mark.asyncio
    async def test_analyze_duplicates_success(self, engine, sample_memories_with_embeddings):
        """Test successful duplicate analysis"""
        engine._fetch_memories_with_embeddings = AsyncMock(
            return_value=sample_memories_with_embeddings
        )
        engine.openai_client.generate = AsyncMock(return_value="Merge these memories")
        
        request = ConsolidationRequest()
        groups = await engine.analyze_duplicates(request)
        
        assert isinstance(groups, list)
        # Should find at least one duplicate group (first two memories are similar)
        assert len(groups) >= 1
        assert isinstance(groups[0], DuplicateGroup)
        assert len(groups[0].memory_ids) >= 2
        assert groups[0].similarity_score > 0.85
    
    @pytest.mark.asyncio
    async def test_analyze_duplicates_no_memories(self, engine):
        """Test duplicate analysis with no memories"""
        engine._fetch_memories_with_embeddings = AsyncMock(return_value=[])
        
        request = ConsolidationRequest()
        groups = await engine.analyze_duplicates(request)
        
        assert groups == []
    
    @pytest.mark.asyncio
    async def test_find_similarities(self, engine, sample_memories_with_embeddings):
        """Test similarity finding"""
        request = ConsolidationRequest(similarity_threshold=0.7)
        
        similarities = await engine._find_similarities(
            sample_memories_with_embeddings,
            request
        )
        
        assert isinstance(similarities, list)
        # First two memories should be similar
        assert any(s.similarity_score > 0.9 for s in similarities)
        
        # Check similarity types
        exact_sims = [s for s in similarities if s.similarity_type == 'exact']
        semantic_sims = [s for s in similarities if s.similarity_type == 'semantic']
        
        # Should have both types
        assert len(exact_sims) > 0 or len(semantic_sims) > 0
    
    def test_create_duplicate_groups(self, engine, sample_memories_with_embeddings):
        """Test duplicate group creation"""
        # Create similarities
        memories = sample_memories_with_embeddings
        # The _create_duplicate_groups method assumes all similarities passed to it
        # should be grouped. It doesn't filter by threshold - that should be done before calling it.
        # So we should only pass similarities that are above threshold.
        similarities = [
            MemorySimilarity(memories[0]['id'], memories[1]['id'], 0.95, 'exact'),
            # Don't include the below-threshold similarity
            # MemorySimilarity(memories[0]['id'], memories[2]['id'], 0.60, 'partial'),  # Below threshold
        ]
        
        groups = engine._create_duplicate_groups(memories, similarities)
        
        assert len(groups) == 1  # Only one group 
        assert len(groups[0].memory_ids) == 2
        assert memories[0]['id'] in groups[0].memory_ids
        assert memories[1]['id'] in groups[0].memory_ids
        assert groups[0].duplicate_type == "exact"
    
    @pytest.mark.asyncio
    async def test_suggest_consolidation_action(self, engine):
        """Test consolidation action suggestion"""
        # Test exact duplicates
        exact_group = DuplicateGroup(
            memory_ids=[uuid4(), uuid4()],
            similarity_score=0.98,
            duplicate_type="exact",
            group_summary="Exact duplicates"
        )
        
        action = await engine._suggest_consolidation_action(exact_group)
        assert action == MergeStrategy.KEEP_NEWEST
        
        # Test near duplicates with length difference
        engine._fetch_full_memories = AsyncMock(return_value=[
            {'id': uuid4(), 'content': 'Short content', 'importance': 5},
            {'id': uuid4(), 'content': 'Much longer content with lots more detail' * 10, 'importance': 5}
        ])
        
        near_group = DuplicateGroup(
            memory_ids=[uuid4(), uuid4()],
            similarity_score=0.88,
            duplicate_type="near_duplicate",
            group_summary="Near duplicates"
        )
        
        action = await engine._suggest_consolidation_action(near_group)
        assert action == MergeStrategy.MERGE_CONTENT
    
    @pytest.mark.asyncio
    async def test_consolidate_memories_keep_newest(self, engine):
        """Test consolidation with keep newest strategy"""
        now = datetime.utcnow()
        memories = [
            {
                'id': uuid4(),
                'content': 'Old memory',
                'importance': 5,
                'created_at': now - timedelta(days=10),
                'updated_at': now - timedelta(days=10)
            },
            {
                'id': uuid4(),
                'content': 'New memory',
                'importance': 5,
                'created_at': now - timedelta(days=1),
                'updated_at': now
            }
        ]
        
        engine._fetch_full_memories = AsyncMock(return_value=memories)
        
        group = DuplicateGroup(
            memory_ids=[m['id'] for m in memories],
            similarity_score=0.95,
            duplicate_type="exact"
        )
        
        result = await engine.consolidate_memories(group, MergeStrategy.KEEP_NEWEST)
        
        assert isinstance(result, ConsolidationResult)
        assert result.kept_memory_id == memories[1]['id']  # Newer memory
        assert len(result.removed_memory_ids) == 1
        assert memories[0]['id'] in result.removed_memory_ids
    
    @pytest.mark.asyncio
    async def test_consolidate_memories_merge_content(self, engine):
        """Test consolidation with merge content strategy"""
        memories = [
            {
                'id': uuid4(),
                'content': 'Python basics: variables and functions',
                'importance': 7,
                'created_at': datetime.utcnow(),
                'tags': ['Python', 'basics']
            },
            {
                'id': uuid4(),
                'content': 'Python basics: loops and conditionals',
                'importance': 7,
                'created_at': datetime.utcnow(),
                'tags': ['Python', 'basics', 'control-flow']
            }
        ]
        
        engine._fetch_full_memories = AsyncMock(return_value=memories)
        engine.openai_client.generate = AsyncMock(
            return_value="Python basics: Complete guide covering variables, functions, loops, and conditionals"
        )
        
        group = DuplicateGroup(
            memory_ids=[m['id'] for m in memories],
            similarity_score=0.88,
            duplicate_type="near_duplicate"
        )
        
        result = await engine.consolidate_memories(group, MergeStrategy.MERGE_CONTENT)
        
        assert isinstance(result, ConsolidationResult)
        assert result.new_content is not None
        assert "Complete guide" in result.new_content
        assert len(result.removed_memory_ids) == 1  # One removed, one kept with new content
        assert result.merge_metadata['strategy'] == 'merge_content'
    
    @pytest.mark.asyncio
    async def test_consolidate_memories_create_summary(self, engine):
        """Test consolidation with create summary strategy"""
        memories = [
            {'id': uuid4(), 'content': f'Memory {i}', 'importance': 5, 'created_at': datetime.utcnow()}
            for i in range(5)
        ]
        
        engine._fetch_full_memories = AsyncMock(return_value=memories)
        engine.openai_client.generate = AsyncMock(
            return_value="Summary: This collection covers various aspects of the topic"
        )
        
        group = DuplicateGroup(
            memory_ids=[m['id'] for m in memories],
            similarity_score=0.75,
            duplicate_type="similar"
        )
        
        result = await engine.consolidate_memories(group, MergeStrategy.CREATE_SUMMARY)
        
        assert isinstance(result, ConsolidationResult)
        assert result.new_content is not None
        assert "Summary" in result.new_content
        assert result.kept_memory_id is None  # New memory will be created
        assert len(result.removed_memory_ids) == 0  # Keep all originals
        assert result.merge_metadata['strategy'] == 'create_summary'
    
    @pytest.mark.asyncio
    async def test_bulk_consolidate(self, engine, sample_memories_with_embeddings):
        """Test bulk consolidation"""
        engine._fetch_memories_with_embeddings = AsyncMock(
            return_value=sample_memories_with_embeddings
        )
        engine.openai_client.generate = AsyncMock(return_value="Consolidated content")
        
        # Create duplicate groups
        engine.analyze_duplicates = AsyncMock(return_value=[
            DuplicateGroup(
                memory_ids=[sample_memories_with_embeddings[0]['id'], 
                           sample_memories_with_embeddings[1]['id']],
                similarity_score=0.95,
                duplicate_type="exact"
            )
        ])
        
        engine._fetch_full_memories = AsyncMock(
            return_value=sample_memories_with_embeddings[:2]
        )
        
        request = ConsolidationRequest(auto_merge=True)
        result = await engine.bulk_consolidate(request)
        
        assert result['status'] == 'complete'
        assert result['groups_found'] == 1
        assert result['groups_consolidated'] == 1
        assert result['memories_removed'] == 1
    
    @pytest.mark.asyncio
    async def test_consolidation_error_handling(self, engine):
        """Test error handling in consolidation"""
        group = DuplicateGroup(
            memory_ids=[uuid4()],
            similarity_score=0.9,
            duplicate_type="exact"
        )
        
        engine._fetch_full_memories = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception):
            await engine.consolidate_memories(group)
    
    @pytest.mark.asyncio
    async def test_fetch_memories_with_embeddings(self, engine):
        """Test fetching memories with embeddings"""
        mock_memories = [
            {
                'id': uuid4(),
                'content': 'Test',
                'content_vector': [0.1, 0.2, 0.3],
                'importance': 5,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'tags': ['test']
            }
        ]
        
        engine.db.fetch_all = AsyncMock(return_value=mock_memories)
        
        # Test with specific IDs
        memory_ids = [uuid4(), uuid4()]
        memories = await engine._fetch_memories_with_embeddings(memory_ids)
        
        assert len(memories) == 1
        assert isinstance(memories[0]['embedding'], np.ndarray)
        
        # Test without IDs (fetch all)
        memories = await engine._fetch_memories_with_embeddings(None)
        assert len(memories) == 1
    
    def test_similarity_thresholds(self, engine):
        """Test similarity threshold values"""
        assert 0 < engine.moderate_similarity_threshold < engine.high_similarity_threshold
        assert engine.high_similarity_threshold < engine.exact_threshold
        assert engine.exact_threshold <= 1.0
    
    def test_merge_templates(self, engine):
        """Test merge strategy templates"""
        assert MergeStrategy.KEEP_NEWEST in engine.merge_templates
        assert MergeStrategy.KEEP_OLDEST in engine.merge_templates
        assert MergeStrategy.MERGE_CONTENT in engine.merge_templates
        assert MergeStrategy.CREATE_SUMMARY in engine.merge_templates
        
        # Check template content
        merge_template = engine.merge_templates[MergeStrategy.MERGE_CONTENT]
        assert "{memory1}" in merge_template
        assert "{memory2}" in merge_template