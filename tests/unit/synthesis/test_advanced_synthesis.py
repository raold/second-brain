"""Tests for AdvancedSynthesisEngine"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.synthesis.advanced_models import (
    SynthesisRequest,
    SynthesisResult,
    SynthesisStrategy,
)
from app.services.synthesis.advanced_synthesis import (
    AdvancedSynthesisEngine,
    ThemeCluster,
)


class TestThemeCluster:
    """Test ThemeCluster class"""
    
    def test_theme_cluster_creation(self):
        """Test creating a theme cluster"""
        memories = [
            {'id': uuid4(), 'content': 'Test 1', 'importance': 8, 'created_at': datetime.utcnow()},
            {'id': uuid4(), 'content': 'Test 2', 'importance': 6, 'created_at': datetime.utcnow()},
        ]
        
        cluster = ThemeCluster("Python", memories)
        
        assert cluster.theme == "Python"
        assert len(cluster.memories) == 2
        assert cluster.sub_themes == []
        assert 0 <= cluster.importance_score <= 1
    
    def test_importance_calculation(self):
        """Test cluster importance calculation"""
        # High importance, recent memories
        recent_memories = [
            {'id': uuid4(), 'content': 'Important', 'importance': 9, 'created_at': datetime.utcnow()},
            {'id': uuid4(), 'content': 'Also important', 'importance': 8, 'created_at': datetime.utcnow()},
        ]
        
        high_cluster = ThemeCluster("Important Topic", recent_memories)
        # With importance 8.5 avg, recent date, and 2 memories:
        # score = (8.5/10) * 0.5 + (2/10) * 0.3 + 1.0 * 0.2 = 0.425 + 0.06 + 0.2 = 0.685
        assert high_cluster.importance_score == pytest.approx(0.685, rel=0.01)
        
        # Low importance, old memories
        from datetime import timedelta
        old_memories = [
            {'id': uuid4(), 'content': 'Old', 'importance': 3, 
             'created_at': datetime.utcnow() - timedelta(days=400)},
        ]
        
        low_cluster = ThemeCluster("Old Topic", old_memories)
        assert low_cluster.importance_score < 0.3
    
    def test_add_sub_theme(self):
        """Test adding sub-themes"""
        main_cluster = ThemeCluster("Programming", [])
        sub_cluster = ThemeCluster("Python", [])
        
        main_cluster.add_sub_theme(sub_cluster)
        
        assert len(main_cluster.sub_themes) == 1
        assert main_cluster.sub_themes[0].theme == "Python"


class TestAdvancedSynthesisEngine:
    """Test AdvancedSynthesisEngine"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        mock_db = MagicMock()
        mock_memory_service = AsyncMock()
        mock_relationship_analyzer = AsyncMock()
        mock_openai_client = AsyncMock()
        
        return mock_db, mock_memory_service, mock_relationship_analyzer, mock_openai_client
    
    @pytest.fixture
    def engine(self, mock_dependencies):
        """Create engine instance with mocks"""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies
        return AdvancedSynthesisEngine(db, memory_service, relationship_analyzer, openai_client)
    
    @pytest.fixture
    def sample_request(self):
        """Create sample synthesis request"""
        return SynthesisRequest(
            memory_ids=[uuid4(), uuid4(), uuid4()],
            strategy=SynthesisStrategy.SUMMARY,
            max_tokens=1000,
            temperature=0.7,
            include_references=True,
            user_id="test_user"
        )
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories"""
        return [
            {
                'id': uuid4(),
                'content': 'Python is a versatile programming language',
                'importance': 8,
                'created_at': datetime.utcnow(),
                'tags': ['Python', 'Programming'],
                'metadata': {}
            },
            {
                'id': uuid4(),
                'content': 'Machine learning with Python is powerful',
                'importance': 9,
                'created_at': datetime.utcnow(),
                'tags': ['Python', 'ML'],
                'metadata': {}
            },
            {
                'id': uuid4(),
                'content': 'Django is a Python web framework',
                'importance': 7,
                'created_at': datetime.utcnow(),
                'tags': ['Python', 'Web'],
                'metadata': {}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_synthesize_memories_success(self, engine, sample_request, sample_memories):
        """Test successful memory synthesis"""
        # Mock memory fetching
        engine._fetch_memories = AsyncMock(return_value=sample_memories)
        
        # Mock theme extraction
        mock_clusters = [
            ThemeCluster("Python", sample_memories[:2]),
            ThemeCluster("Web Development", [sample_memories[2]])
        ]
        engine._extract_themes_and_cluster = AsyncMock(return_value=mock_clusters)
        
        # Mock hierarchy building
        mock_hierarchy = ThemeCluster("Knowledge Synthesis", sample_memories)
        mock_hierarchy.sub_themes = mock_clusters
        engine._build_hierarchy = AsyncMock(return_value=mock_hierarchy)
        
        # Mock synthesis
        engine.openai_client.generate = AsyncMock(
            return_value="This is a comprehensive summary of Python programming concepts."
        )
        
        # Execute
        results = await engine.synthesize_memories(sample_request)
        
        # Verify
        assert len(results) > 0
        assert isinstance(results[0], SynthesisResult)
        assert results[0].synthesis_type == SynthesisStrategy.SUMMARY.value
        assert results[0].content
        assert len(results[0].source_memory_ids) == 3
        assert results[0].confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_memories_no_memories(self, engine, sample_request):
        """Test synthesis with no memories"""
        engine._fetch_memories = AsyncMock(return_value=[])
        
        results = await engine.synthesize_memories(sample_request)
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_synthesize_memories_error_handling(self, engine, sample_request):
        """Test error handling in synthesis"""
        engine._fetch_memories = AsyncMock(side_effect=Exception("Database error"))
        
        results = await engine.synthesize_memories(sample_request)
        
        assert len(results) == 1
        assert results[0].metadata.get('fallback') is True
    
    @pytest.mark.asyncio
    async def test_extract_themes_and_cluster(self, engine, sample_memories):
        """Test theme extraction and clustering"""
        clusters = await engine._extract_themes_and_cluster(sample_memories)
        
        assert len(clusters) > 0
        assert all(isinstance(c, ThemeCluster) for c in clusters)
        
        # Check that memories are assigned to clusters
        total_memories = sum(len(c.memories) for c in clusters)
        assert total_memories >= len(sample_memories)
    
    @pytest.mark.asyncio
    async def test_extract_implicit_themes(self, engine):
        """Test implicit theme extraction using LLM"""
        untagged_memories = [
            {'id': uuid4(), 'content': 'Neural networks are fascinating', 'importance': 8},
            {'id': uuid4(), 'content': 'Deep learning revolutionizes AI', 'importance': 9},
        ]
        
        # Mock LLM response
        engine.openai_client.generate = AsyncMock(
            return_value='["Machine Learning", "Artificial Intelligence"]'
        )
        
        clusters = await engine._extract_implicit_themes(untagged_memories)
        
        assert len(clusters) > 0
        assert engine.openai_client.generate.called
    
    @pytest.mark.asyncio
    async def test_timeline_synthesis(self, engine, sample_memories):
        """Test timeline-based synthesis"""
        request = SynthesisRequest(
            memory_ids=[m['id'] for m in sample_memories],
            strategy=SynthesisStrategy.TIMELINE,
            user_id="test_user"
        )
        
        # Add different dates to memories
        from datetime import timedelta
        for i, memory in enumerate(sample_memories):
            memory['created_at'] = datetime.utcnow() - timedelta(days=i*30)
        
        engine._fetch_memories = AsyncMock(return_value=sample_memories)
        engine.openai_client.generate = AsyncMock(
            return_value="Timeline narrative of knowledge evolution"
        )
        
        mock_clusters = [ThemeCluster("Python", sample_memories)]
        engine._extract_themes_and_cluster = AsyncMock(return_value=mock_clusters)
        
        mock_hierarchy = ThemeCluster("Knowledge", sample_memories)
        engine._build_hierarchy = AsyncMock(return_value=mock_hierarchy)
        
        results = await engine.synthesize_memories(request)
        
        assert len(results) > 0
        assert results[0].synthesis_type == SynthesisStrategy.TIMELINE.value
        assert "Timeline" in results[0].content
    
    @pytest.mark.asyncio
    async def test_hierarchical_synthesis(self, engine, sample_request, sample_memories):
        """Test hierarchical synthesis with sub-themes"""
        # Setup
        engine._fetch_memories = AsyncMock(return_value=sample_memories)
        
        # Create hierarchy with sub-themes
        sub_cluster1 = ThemeCluster("Python Basics", sample_memories[:1])
        sub_cluster2 = ThemeCluster("Python Applications", sample_memories[1:])
        main_cluster = ThemeCluster("Python Programming", sample_memories)
        main_cluster.sub_themes = [sub_cluster1, sub_cluster2]
        
        engine._extract_themes_and_cluster = AsyncMock(return_value=[sub_cluster1, sub_cluster2])
        engine._build_hierarchy = AsyncMock(return_value=main_cluster)
        engine.openai_client.generate = AsyncMock(return_value="Synthesized content")
        
        # Include sub-themes in options
        sample_request.options['include_sub_themes'] = True
        
        results = await engine.synthesize_memories(sample_request)
        
        # Should have main synthesis + sub-theme syntheses
        assert len(results) >= 2
        assert any(r.metadata.get('is_sub_theme') for r in results)
    
    def test_synthesis_templates(self, engine):
        """Test that all synthesis templates are defined"""
        assert SynthesisStrategy.SUMMARY in engine.synthesis_templates
        assert SynthesisStrategy.ANALYSIS in engine.synthesis_templates
        assert SynthesisStrategy.REPORT in engine.synthesis_templates
        assert SynthesisStrategy.TIMELINE in engine.synthesis_templates
        
        # Check template structure
        for template in engine.synthesis_templates.values():
            assert "{memories}" in template
            assert len(template) > 100  # Reasonable template length
    
    @pytest.mark.asyncio
    async def test_fallback_synthesis(self, engine, sample_request, sample_memories):
        """Test fallback synthesis creation"""
        result = await engine._create_fallback_synthesis(sample_request, sample_memories)
        
        assert isinstance(result, SynthesisResult)
        assert result.metadata.get('fallback') is True
        assert result.confidence_score == 0.5
        assert len(result.source_memory_ids) == len(sample_request.memory_ids)
    
    def test_format_references(self, engine, sample_memories):
        """Test reference formatting"""
        references = engine._format_references(sample_memories)
        
        assert isinstance(references, str)
        assert "Memory" in references
        assert "Created:" in references
    
    @pytest.mark.asyncio
    async def test_different_synthesis_strategies(self, engine, sample_memories):
        """Test different synthesis strategies produce different results"""
        engine._fetch_memories = AsyncMock(return_value=sample_memories)
        mock_cluster = ThemeCluster("Test", sample_memories)
        engine._extract_themes_and_cluster = AsyncMock(return_value=[mock_cluster])
        engine._build_hierarchy = AsyncMock(return_value=mock_cluster)
        
        results = {}
        for strategy in SynthesisStrategy:
            engine.openai_client.generate = AsyncMock(
                return_value=f"Content for {strategy.value}"
            )
            
            request = SynthesisRequest(
                memory_ids=[m['id'] for m in sample_memories],
                strategy=strategy,
                user_id="test_user"
            )
            
            result = await engine.synthesize_memories(request)
            results[strategy] = result[0].content
        
        # Verify different strategies called with different prompts
        assert len(set(results.values())) == len(SynthesisStrategy)
    
    @pytest.mark.asyncio
    async def test_memory_fetch_error_handling(self, engine, sample_request):
        """Test handling of memory fetch errors"""
        # Simulate partial fetch failure
        async def mock_get_memory(memory_id):
            if memory_id == str(sample_request.memory_ids[0]):
                raise Exception("Memory not found")
            return MagicMock(
                content="Test content",
                importance_score=5,
                created_at=datetime.utcnow()
            )
        
        engine.memory_service.get_memory = mock_get_memory
        
        memories = await engine._fetch_memories(sample_request.memory_ids)
        
        # Should still return successfully fetched memories
        assert len(memories) == 2  # 1 failed, 2 succeeded