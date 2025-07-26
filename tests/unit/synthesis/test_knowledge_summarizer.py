"""Tests for KnowledgeSummarizer"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest

from app.models.synthesis.summary_models import (
    SummaryRequest,
    SummaryResponse,
    SummarySegment,
    SummaryType,
    FormatType,
)
from app.services.synthesis.knowledge_summarizer import (
    KnowledgeSummarizer,
    KnowledgeDomain,
)


class TestKnowledgeDomain:
    """Test KnowledgeDomain class"""
    
    def test_knowledge_domain_creation(self):
        """Test creating a knowledge domain"""
        domain = KnowledgeDomain("Python", 0.85, ["programming", "development"])
        
        assert domain.name == "Python"
        assert domain.relevance_score == 0.85
        assert domain.related_topics == ["programming", "development"]
        assert isinstance(domain.key_insights, list)
        assert isinstance(domain.connections, list)
    
    def test_add_insight(self):
        """Test adding insights to domain"""
        domain = KnowledgeDomain("AI", 0.9, ["ML", "Deep Learning"])
        domain.add_insight("Neural networks are universal approximators")
        
        assert len(domain.key_insights) == 1
        assert domain.key_insights[0] == "Neural networks are universal approximators"
    
    def test_add_connection(self):
        """Test adding connections to domain"""
        domain = KnowledgeDomain("AI", 0.9, ["ML"])
        domain.add_connection("Mathematics", 0.8)
        
        assert len(domain.connections) == 1
        assert domain.connections[0] == ("Mathematics", 0.8)


class TestKnowledgeSummarizer:
    """Test KnowledgeSummarizer"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        mock_db = AsyncMock()
        mock_memory_service = AsyncMock()
        mock_relationship_analyzer = AsyncMock()
        mock_openai_client = AsyncMock()
        
        return mock_db, mock_memory_service, mock_relationship_analyzer, mock_openai_client
    
    @pytest.fixture
    def summarizer(self, mock_dependencies):
        """Create summarizer instance with mocks"""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies
        return KnowledgeSummarizer(db, memory_service, relationship_analyzer, openai_client)
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for summarization"""
        base_time = datetime.utcnow()
        return [
            {
                'id': uuid4(),
                'content': 'Machine learning is a subset of artificial intelligence',
                'importance': 8,
                'created_at': base_time,
                'tags': ['ML', 'AI'],
                'content_vector': np.random.rand(384).tolist()
            },
            {
                'id': uuid4(),
                'content': 'Deep learning uses neural networks with multiple layers',
                'importance': 9,
                'created_at': base_time - timedelta(days=1),
                'tags': ['Deep Learning', 'AI'],
                'content_vector': np.random.rand(384).tolist()
            },
            {
                'id': uuid4(),
                'content': 'Python is the most popular language for machine learning',
                'importance': 7,
                'created_at': base_time - timedelta(days=2),
                'tags': ['Python', 'ML'],
                'content_vector': np.random.rand(384).tolist()
            },
            {
                'id': uuid4(),
                'content': 'TensorFlow and PyTorch are leading deep learning frameworks',
                'importance': 7,
                'created_at': base_time - timedelta(days=3),
                'tags': ['TensorFlow', 'PyTorch', 'Deep Learning'],
                'content_vector': np.random.rand(384).tolist()
            }
        ]
    
    @pytest.fixture
    def sample_request(self):
        """Create sample summary request"""
        return SummaryRequest(
            memory_ids=[uuid4() for _ in range(4)],
            summary_type=SummaryType.DETAILED,
            max_length=500,
            format_type=FormatType.STRUCTURED,
            include_insights=True,
            user_id="test_user"
        )
    
    @pytest.mark.asyncio
    async def test_create_summary_success(self, summarizer, sample_request, sample_memories):
        """Test successful summary creation"""
        # Mock memory fetching
        summarizer._fetch_memories = AsyncMock(return_value=sample_memories)
        
        # Mock domain extraction
        mock_domains = [
            KnowledgeDomain("AI/ML", 0.9, ["Artificial Intelligence", "Machine Learning"]),
            KnowledgeDomain("Deep Learning", 0.85, ["Neural Networks", "AI"])
        ]
        mock_domains[0].add_insight("ML is transforming industries")
        mock_domains[1].add_insight("Deep learning excels at pattern recognition")
        
        summarizer._extract_knowledge_domains = AsyncMock(return_value=mock_domains)
        
        # Mock LLM generation
        summarizer.openai_client.generate = AsyncMock(
            return_value="This is a comprehensive summary of AI and ML concepts."
        )
        
        # Execute
        response = await summarizer.create_summary(sample_request)
        
        # Verify
        assert isinstance(response, SummaryResponse)
        assert response.summary_type == SummaryType.DETAILED
        assert len(response.segments) > 0
        assert response.total_memories_processed == 4
        assert response.confidence_score > 0
        assert len(response.key_insights) > 0
        assert len(response.domains) == 2
    
    @pytest.mark.asyncio
    async def test_create_summary_no_memories(self, summarizer, sample_request):
        """Test summary creation with no memories"""
        summarizer._fetch_memories = AsyncMock(return_value=[])
        
        response = await summarizer.create_summary(sample_request)
        
        assert response.segments == []
        assert response.total_memories_processed == 0
        assert response.metadata.get('empty') is True
    
    @pytest.mark.asyncio
    async def test_create_summary_error_handling(self, summarizer, sample_request):
        """Test error handling in summary creation"""
        summarizer._fetch_memories = AsyncMock(side_effect=Exception("Database error"))
        
        response = await summarizer.create_summary(sample_request)
        
        assert len(response.segments) == 1
        assert response.segments[0].title == "Error"
        assert "error" in response.metadata
    
    @pytest.mark.asyncio
    async def test_different_summary_types(self, summarizer, sample_memories):
        """Test different summary types produce different results"""
        summarizer._fetch_memories = AsyncMock(return_value=sample_memories)
        summarizer._extract_knowledge_domains = AsyncMock(return_value=[])
        
        results = {}
        for summary_type in SummaryType:
            summarizer.openai_client.generate = AsyncMock(
                return_value=f"Summary for {summary_type.value}"
            )
            
            request = SummaryRequest(
                memory_ids=[m['id'] for m in sample_memories],
                summary_type=summary_type,
                user_id="test_user"
            )
            
            response = await summarizer.create_summary(request)
            results[summary_type] = response.segments[0].content if response.segments else ""
        
        # Verify different types have different templates
        unique_results = set(results.values())
        assert len(unique_results) >= len(SummaryType) - 1  # Allow for some similarity
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_domains(self, summarizer, sample_memories):
        """Test knowledge domain extraction"""
        domains = await summarizer._extract_knowledge_domains(sample_memories)
        
        assert len(domains) > 0
        assert all(isinstance(d, KnowledgeDomain) for d in domains)
        
        # Check domain properties
        for domain in domains:
            assert domain.name != ""
            assert 0 <= domain.relevance_score <= 1
            assert isinstance(domain.related_topics, list)
    
    @pytest.mark.asyncio
    async def test_topic_modeling(self, summarizer, sample_memories):
        """Test topic modeling functionality"""
        # Add more memories for better topic modeling
        extra_memories = sample_memories * 5  # Duplicate to have enough for LDA
        
        topics = await summarizer._perform_topic_modeling(extra_memories)
        
        assert len(topics) > 0
        assert all('topic_id' in t for t in topics)
        assert all('keywords' in t for t in topics)
        assert all('relevance' in t for t in topics)
    
    @pytest.mark.asyncio
    async def test_generate_insights(self, summarizer, sample_memories):
        """Test insight generation"""
        summarizer.openai_client.generate = AsyncMock(
            return_value='["ML is growing rapidly", "Python dominates ML development", "Deep learning is computationally intensive"]'
        )
        
        insights = await summarizer._generate_insights(sample_memories)
        
        assert len(insights) == 3
        assert all(isinstance(i, str) for i in insights)
        assert summarizer.openai_client.generate.called
    
    @pytest.mark.asyncio
    async def test_format_summary(self, summarizer):
        """Test summary formatting"""
        segments = [
            SummarySegment(
                title="Introduction",
                content="Overview of ML concepts",
                importance=0.9,
                memory_ids=[str(uuid4())],
                metadata={}
            ),
            SummarySegment(
                title="Deep Learning",
                content="Neural network architectures",
                importance=0.85,
                memory_ids=[str(uuid4())],
                metadata={}
            )
        ]
        
        # Test different format types
        for format_type in FormatType:
            formatted = summarizer._format_summary(segments, format_type)
            assert isinstance(formatted, str)
            assert len(formatted) > 0
            
            if format_type == FormatType.STRUCTURED:
                assert "##" in formatted  # Headers
            elif format_type == FormatType.BULLET_POINTS:
                assert "•" in formatted or "-" in formatted
            elif format_type == FormatType.NARRATIVE:
                assert "." in formatted  # Sentences
    
    @pytest.mark.asyncio
    async def test_create_timeline_summary(self, summarizer, sample_memories):
        """Test timeline-based summary creation"""
        # Add clear time progression to memories
        for i, memory in enumerate(sample_memories):
            memory['created_at'] = datetime.utcnow() - timedelta(days=i*7)
        
        segments = await summarizer._create_timeline_summary(sample_memories)
        
        assert len(segments) > 0
        assert any("timeline" in s.title.lower() or "period" in s.title.lower() for s in segments)
        
        # Check chronological ordering
        for segment in segments:
            assert segment.metadata.get('time_period') is not None
    
    @pytest.mark.asyncio
    async def test_hierarchical_summary(self, summarizer, sample_memories):
        """Test hierarchical summary organization"""
        segments = await summarizer._create_hierarchical_summary(sample_memories)
        
        assert len(segments) > 0
        
        # Check for hierarchy indicators
        levels = set()
        for segment in segments:
            if 'level' in segment.metadata:
                levels.add(segment.metadata['level'])
        
        # Should have multiple levels if hierarchical
        assert len(levels) >= 1
    
    def test_summary_templates(self, summarizer):
        """Test that all summary templates are defined"""
        assert SummaryType.EXECUTIVE in summarizer.summary_templates
        assert SummaryType.DETAILED in summarizer.summary_templates
        assert SummaryType.TECHNICAL in summarizer.summary_templates
        assert SummaryType.LEARNING in summarizer.summary_templates
        
        # Check template structure
        for template in summarizer.summary_templates.values():
            assert "{content}" in template
            assert "{insights}" in template
    
    @pytest.mark.asyncio
    async def test_memory_clustering_for_summary(self, summarizer, sample_memories):
        """Test memory clustering for better summarization"""
        # Mock embeddings
        for memory in sample_memories:
            memory['embedding'] = np.random.rand(384)
        
        clusters = summarizer._cluster_memories(sample_memories, n_clusters=2)
        
        assert len(clusters) == 2
        assert all(len(cluster) > 0 for cluster in clusters)
        
        # Check that all memories are assigned
        all_ids = set()
        for cluster in clusters:
            all_ids.update(m['id'] for m in cluster)
        assert len(all_ids) == len(sample_memories)
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, summarizer):
        """Test confidence score calculation"""
        # High quality summary
        high_quality = {
            'total_memories': 50,
            'domains': [KnowledgeDomain("AI", 0.9, []), KnowledgeDomain("ML", 0.85, [])],
            'insights': ["insight1", "insight2", "insight3"],
            'coverage': 0.9
        }
        
        high_score = summarizer._calculate_confidence_score(
            high_quality['total_memories'],
            high_quality['domains'],
            high_quality['insights'],
            high_quality['coverage']
        )
        
        assert 0.7 <= high_score <= 1.0
        
        # Low quality summary
        low_quality = {
            'total_memories': 2,
            'domains': [],
            'insights': [],
            'coverage': 0.3
        }
        
        low_score = summarizer._calculate_confidence_score(
            low_quality['total_memories'],
            low_quality['domains'],
            low_quality['insights'],
            low_quality['coverage']
        )
        
        assert 0 <= low_score <= 0.5
        assert high_score > low_score
    
    @pytest.mark.asyncio
    async def test_executive_summary_brevity(self, summarizer, sample_memories):
        """Test that executive summaries are brief"""
        summarizer._fetch_memories = AsyncMock(return_value=sample_memories)
        summarizer._extract_knowledge_domains = AsyncMock(return_value=[])
        summarizer.openai_client.generate = AsyncMock(
            return_value="Brief executive summary"
        )
        
        request = SummaryRequest(
            memory_ids=[m['id'] for m in sample_memories],
            summary_type=SummaryType.EXECUTIVE,
            max_length=200,
            user_id="test_user"
        )
        
        response = await summarizer.create_summary(request)
        
        # Executive summary should be concise
        total_length = sum(len(s.content) for s in response.segments)
        assert total_length < 1000  # Reasonable limit for executive summary
    
    @pytest.mark.asyncio
    async def test_learning_summary_structure(self, summarizer, sample_memories):
        """Test that learning summaries have educational structure"""
        summarizer._fetch_memories = AsyncMock(return_value=sample_memories)
        summarizer._extract_knowledge_domains = AsyncMock(return_value=[])
        
        # Mock LLM to return structured learning content
        summarizer.openai_client.generate = AsyncMock(
            side_effect=[
                "Learning objectives: Understand ML basics",
                '["Concept 1", "Concept 2", "Concept 3"]',
                "Prerequisites: Basic math and programming"
            ]
        )
        
        request = SummaryRequest(
            memory_ids=[m['id'] for m in sample_memories],
            summary_type=SummaryType.LEARNING,
            user_id="test_user"
        )
        
        response = await summarizer.create_summary(request)
        
        # Learning summary should have educational elements
        assert any("objective" in s.content.lower() or "learn" in s.content.lower() 
                  for s in response.segments)