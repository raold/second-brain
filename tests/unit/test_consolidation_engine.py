"""
Tests for Memory Consolidation Engine
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.synthesis.consolidation_models import (
    ConsolidatedMemory,
    ConsolidationCandidate,
    ConsolidationPreview,
    ConsolidationRequest,
    ConsolidationStrategy,
    QualityAssessment,
)
from app.services.synthesis.consolidation_engine import MemoryConsolidationEngine


class MockMemory:
    """Mock Memory object for testing"""
    def __init__(self, id: UUID, title: str, content: str, importance: float = 0.5,
                 created_at: datetime = None, memory_type: str = "episodic"):
        self.id = id
        self.title = title
        self.content = content
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.memory_type = memory_type
        self.user_id = "test_user"
        self.embedding = [0.1] * 1536  # Mock embedding


class MockOpenAIClient:
    """Mock OpenAI client for testing"""
    async def create(self, **kwargs):
        # Return mock consolidation result
        return type('obj', (object,), {
            'choices': [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': '''
                    {
                        "title": "Consolidated Memory",
                        "content": "This is a consolidated memory combining multiple memories.",
                        "key_insights": ["Insight 1", "Insight 2"],
                        "preserved_details": {"memory1": "detail1", "memory2": "detail2"},
                        "metadata": {"topics": ["topic1", "topic2"]}
                    }
                    '''
                })()
            })]
        })()


class MockMemoryService:
    """Mock Memory Service for testing"""
    def __init__(self):
        self.memories = {}

    async def get_memory(self, user_id: str, memory_id: UUID):
        return self.memories.get(memory_id)

    async def get_memories_by_ids(self, user_id: str, memory_ids: list[UUID]):
        return [self.memories.get(mid) for mid in memory_ids if mid in self.memories]

    async def create_memory(self, user_id: str, **kwargs):
        memory_id = uuid4()
        memory = MockMemory(
            id=memory_id,
            title=kwargs.get('title', 'Test Memory'),
            content=kwargs.get('content', 'Test content'),
            importance=kwargs.get('importance', 0.5)
        )
        self.memories[memory_id] = memory
        return memory

    async def update_memory(self, user_id: str, memory_id: UUID, **kwargs):
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            for key, value in kwargs.items():
                setattr(memory, key, value)
        return self.memories.get(memory_id)

    async def delete_memory(self, user_id: str, memory_id: UUID):
        if memory_id in self.memories:
            del self.memories[memory_id]


class MockDatabase:
    """Mock database for testing"""
    def __init__(self):
        self.data = {}
        self.consolidations = []

    async def execute(self, query, params=None):
        # Return mock results based on query
        if "similarity_threshold" in str(query):
            # Mock similar memories query
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'memory_ids': [uuid4(), uuid4()],
                        'similarity_score': 0.9,
                        'common_topics': ['topic1'],
                        'time_span': timedelta(days=5)
                    })(),
                    type('obj', (object,), {
                        'memory_ids': [uuid4(), uuid4(), uuid4()],
                        'similarity_score': 0.85,
                        'common_topics': ['topic2'],
                        'time_span': timedelta(days=10)
                    })()
                ]
            })()
        elif "INSERT INTO memory_consolidations" in str(query):
            # Mock consolidation insert
            consolidation_id = uuid4()
            self.consolidations.append(consolidation_id)
            return type('obj', (object,), {
                'fetchone': lambda: type('obj', (object,), {
                    'id': consolidation_id
                })()
            })()
        else:
            return type('obj', (object,), {
                'fetchall': lambda: [],
                'fetchone': lambda: None
            })()

    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.fixture
async def mock_db():
    """Create mock database session"""
    return MockDatabase()


@pytest.fixture
async def mock_memory_service():
    """Create mock memory service"""
    service = MockMemoryService()

    # Add some test memories
    memory1 = MockMemory(
        id=uuid4(),
        title="Machine Learning Basics",
        content="Machine learning is a subset of AI that enables systems to learn from data.",
        importance=0.8,
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    memory2 = MockMemory(
        id=uuid4(),
        title="AI and Machine Learning",
        content="Artificial intelligence includes machine learning as a key component.",
        importance=0.7,
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    memory3 = MockMemory(
        id=uuid4(),
        title="Deep Learning Introduction",
        content="Deep learning is a subset of machine learning using neural networks.",
        importance=0.9,
        created_at=datetime.utcnow() - timedelta(days=2)
    )

    service.memories[memory1.id] = memory1
    service.memories[memory2.id] = memory2
    service.memories[memory3.id] = memory3

    return service


@pytest.fixture
async def consolidation_engine(mock_db, mock_memory_service):
    """Create consolidation engine with mocks"""
    engine = MemoryConsolidationEngine(mock_db)
    engine.memory_service = mock_memory_service
    engine.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()
    return engine


class TestMemoryConsolidationEngine:
    """Test Memory Consolidation Engine"""

    async def test_find_consolidation_candidates(self, consolidation_engine):
        """Test finding consolidation candidates"""
        candidates = await consolidation_engine.find_consolidation_candidates(
            user_id="test_user",
            similarity_threshold=0.8,
            time_window_days=30,
            max_candidates=10
        )

        assert isinstance(candidates, list)
        assert len(candidates) == 2  # Based on mock data

        # Check first candidate
        candidate = candidates[0]
        assert isinstance(candidate, ConsolidationCandidate)
        assert candidate.similarity_score == 0.9
        assert len(candidate.memory_ids) == 2
        assert candidate.common_topics == ['topic1']
        assert candidate.confidence_score > 0

    async def test_preview_consolidation(self, consolidation_engine, mock_memory_service):
        """Test consolidation preview"""
        memory_ids = list(mock_memory_service.memories.keys())[:2]

        preview = await consolidation_engine.preview_consolidation(
            user_id="test_user",
            memory_ids=memory_ids,
            strategy=ConsolidationStrategy.MERGE_SIMILAR
        )

        assert isinstance(preview, ConsolidationPreview)
        assert preview.proposed_title == "Consolidated Memory"
        assert preview.proposed_content == "This is a consolidated memory combining multiple memories."
        assert len(preview.key_insights) == 2
        assert len(preview.preserved_details) == 2
        assert preview.estimated_quality_score > 0

    async def test_consolidate_memories(self, consolidation_engine, mock_memory_service):
        """Test memory consolidation"""
        memory_ids = list(mock_memory_service.memories.keys())[:2]

        request = ConsolidationRequest(
            memory_ids=memory_ids,
            strategy=ConsolidationStrategy.MERGE_SIMILAR,
            preserve_originals=True,
            custom_title="AI and ML Fundamentals"
        )

        result = await consolidation_engine.consolidate_memories(
            user_id="test_user",
            request=request
        )

        assert isinstance(result, ConsolidatedMemory)
        assert result.new_memory_id is not None
        assert result.title == "AI and ML Fundamentals"
        assert len(result.source_memory_ids) == 2
        assert result.strategy == ConsolidationStrategy.MERGE_SIMILAR
        assert result.preserved_originals == True

    async def test_quality_assessment(self, consolidation_engine, mock_memory_service):
        """Test quality assessment"""
        memory_ids = list(mock_memory_service.memories.keys())
        original_memories = await mock_memory_service.get_memories_by_ids("test_user", memory_ids)

        consolidated = ConsolidatedMemory(
            id=uuid4(),
            new_memory_id=uuid4(),
            source_memory_ids=memory_ids,
            title="Consolidated Memory",
            content="Combined content",
            strategy=ConsolidationStrategy.MERGE_SIMILAR,
            quality_assessment=None,
            preserved_originals=True
        )

        assessment = await consolidation_engine._assess_consolidation_quality(
            original_memories,
            consolidated,
            {"completeness": 0.9, "coherence": 0.85, "accuracy": 0.95}
        )

        assert isinstance(assessment, QualityAssessment)
        assert 0 <= assessment.information_retention <= 1
        assert 0 <= assessment.coherence_score <= 1
        assert 0 <= assessment.semantic_accuracy <= 1
        assert assessment.overall_score > 0
        assert len(assessment.warnings) >= 0

    async def test_different_strategies(self, consolidation_engine, mock_memory_service):
        """Test different consolidation strategies"""
        memory_ids = list(mock_memory_service.memories.keys())

        strategies = [
            ConsolidationStrategy.MERGE_SIMILAR,
            ConsolidationStrategy.CHRONOLOGICAL,
            ConsolidationStrategy.TOPIC_BASED,
            ConsolidationStrategy.ENTITY_FOCUSED,
            ConsolidationStrategy.HIERARCHICAL
        ]

        for strategy in strategies:
            preview = await consolidation_engine.preview_consolidation(
                user_id="test_user",
                memory_ids=memory_ids,
                strategy=strategy
            )

            assert isinstance(preview, ConsolidationPreview)
            assert preview.strategy == strategy
            assert preview.proposed_title is not None
            assert preview.proposed_content is not None

    async def test_edge_cases(self, consolidation_engine):
        """Test edge cases"""
        # Test with single memory
        with pytest.raises(ValueError):
            await consolidation_engine.preview_consolidation(
                user_id="test_user",
                memory_ids=[uuid4()],
                strategy=ConsolidationStrategy.MERGE_SIMILAR
            )

        # Test with too many memories
        many_ids = [uuid4() for _ in range(15)]
        with pytest.raises(ValueError):
            await consolidation_engine.preview_consolidation(
                user_id="test_user",
                memory_ids=many_ids,
                strategy=ConsolidationStrategy.MERGE_SIMILAR
            )

        # Test with empty memory list
        with pytest.raises(ValueError):
            await consolidation_engine.preview_consolidation(
                user_id="test_user",
                memory_ids=[],
                strategy=ConsolidationStrategy.MERGE_SIMILAR
            )

    async def test_batch_consolidation(self, consolidation_engine):
        """Test batch consolidation suggestions"""
        suggestions = await consolidation_engine.suggest_batch_consolidations(
            user_id="test_user",
            max_groups=5,
            min_similarity=0.8
        )

        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, ConsolidationCandidate)
            assert len(suggestion.memory_ids) >= 2
            assert suggestion.similarity_score >= 0.8

    async def test_undo_consolidation(self, consolidation_engine, mock_memory_service):
        """Test undoing a consolidation"""
        # First consolidate
        memory_ids = list(mock_memory_service.memories.keys())[:2]

        request = ConsolidationRequest(
            memory_ids=memory_ids,
            strategy=ConsolidationStrategy.MERGE_SIMILAR,
            preserve_originals=True
        )

        result = await consolidation_engine.consolidate_memories(
            user_id="test_user",
            request=request
        )

        # Then undo
        success = await consolidation_engine.undo_consolidation(
            user_id="test_user",
            consolidation_id=result.id
        )

        assert success == True

    async def test_consolidation_history(self, consolidation_engine, mock_db):
        """Test getting consolidation history"""
        # Add some mock consolidations to history
        mock_db.consolidations = [uuid4(), uuid4(), uuid4()]

        history = await consolidation_engine.get_consolidation_history(
            user_id="test_user",
            limit=10
        )

        assert isinstance(history, list)
        # History would be empty in this mock implementation
        # In real implementation, it would return the consolidations


@pytest.mark.asyncio
async def test_engine_lifecycle():
    """Test complete engine lifecycle"""
    # Create all mocks
    db = MockDatabase()
    memory_service = MockMemoryService()

    # Add test memories
    memory1 = MockMemory(
        id=uuid4(),
        title="Test Memory 1",
        content="Content 1",
        importance=0.8
    )
    memory2 = MockMemory(
        id=uuid4(),
        title="Test Memory 2",
        content="Content 2",
        importance=0.7
    )

    memory_service.memories[memory1.id] = memory1
    memory_service.memories[memory2.id] = memory2

    # Create engine
    engine = MemoryConsolidationEngine(db)
    engine.memory_service = memory_service
    engine.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()

    # Find candidates
    candidates = await engine.find_consolidation_candidates(
        user_id="test_user",
        similarity_threshold=0.7
    )

    assert len(candidates) > 0

    # Preview consolidation
    if candidates:
        preview = await engine.preview_consolidation(
            user_id="test_user",
            memory_ids=[memory1.id, memory2.id],
            strategy=ConsolidationStrategy.MERGE_SIMILAR
        )

        assert preview is not None
        assert preview.proposed_title is not None

    # Perform consolidation
    request = ConsolidationRequest(
        memory_ids=[memory1.id, memory2.id],
        strategy=ConsolidationStrategy.MERGE_SIMILAR,
        preserve_originals=True
    )

    result = await engine.consolidate_memories(
        user_id="test_user",
        request=request
    )

    assert result is not None
    assert result.new_memory_id is not None
    assert len(result.source_memory_ids) == 2
