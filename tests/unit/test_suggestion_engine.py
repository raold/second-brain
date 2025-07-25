"""
Tests for Smart Suggestion Engine
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.synthesis.suggestion_models import (
    ConnectionSuggestion,
    GapSuggestion,
    MemorySuggestion,
    QuestionSuggestion,
    ReviewSuggestion,
    SuggestionBatch,
    SuggestionContext,
    SuggestionType,
)
from app.services.synthesis.suggestion_engine import SmartSuggestionEngine


class MockMemory:
    """Mock Memory object for testing"""
    def __init__(self, id: UUID, title: str, content: str, importance: float = 0.5,
                 created_at: datetime = None, last_accessed: datetime = None,
                 access_count: int = 0, memory_type: str = "episodic"):
        self.id = id
        self.title = title
        self.content = content
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.last_accessed = last_accessed
        self.access_count = access_count
        self.memory_type = memory_type
        self.user_id = "test_user"
        self.updated_at = self.created_at


class MockOpenAIClient:
    """Mock OpenAI client for testing"""
    async def create(self, **kwargs):
        messages = kwargs.get('messages', [])

        if "relationship between" in str(messages):
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''
                        {
                            "should_connect": true,
                            "relationship_type": "related_to",
                            "evidence": [
                                "Both discuss machine learning concepts",
                                "Share common terminology"
                            ],
                            "insights": [
                                "Connecting these would create a knowledge cluster"
                            ],
                            "confidence": 0.85,
                            "description": "These memories are strongly related"
                        }
                        '''
                    })()
                })]
            })()
        elif "follow-up questions" in str(messages):
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''
                        {
                            "questions": [
                                {
                                    "question": "How does this concept apply to real-world scenarios?",
                                    "reason": "Practical application deepens understanding",
                                    "answer_type": "exploratory",
                                    "topics": ["application", "practice"],
                                    "paths": [{"path": "Explore use cases", "description": "Look at industry applications"}],
                                    "confidence": 0.8,
                                    "priority": 0.9
                                },
                                {
                                    "question": "What are the limitations of this approach?",
                                    "reason": "Understanding limitations provides balanced perspective",
                                    "answer_type": "analytical",
                                    "topics": ["limitations", "analysis"],
                                    "paths": [{"path": "Research alternatives", "description": "Compare with other methods"}],
                                    "confidence": 0.7,
                                    "priority": 0.8
                                }
                            ]
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


class MockDatabase:
    """Mock database for testing"""
    def __init__(self):
        self.memories = []

    async def execute(self, query, params=None):
        query_str = str(query)

        if "similarity" in query_str and "current_id" in str(params):
            # Mock similar memories query
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'id': self.memories[1].id if len(self.memories) > 1 else uuid4(),
                        'title': self.memories[1].title if len(self.memories) > 1 else "Related Memory",
                        'content': self.memories[1].content if len(self.memories) > 1 else "Related content",
                        'importance': 0.8,
                        'similarity': 0.85
                    })(),
                    type('obj', (object,), {
                        'id': self.memories[2].id if len(self.memories) > 2 else uuid4(),
                        'title': self.memories[2].title if len(self.memories) > 2 else "Another Related",
                        'content': self.memories[2].content if len(self.memories) > 2 else "More content",
                        'importance': 0.7,
                        'similarity': 0.75
                    })()
                ]
            })()
        elif "potential_connections" in query_str:
            # Mock potential connections query
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'id': uuid4(),
                        'title': "Potentially Connected Memory",
                        'content': "This could be connected",
                        'similarity': 0.8
                    })()
                ]
            })()
        elif "forgetting_curve" in query_str or "review" in query_str:
            # Mock memories needing review
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'id': uuid4(),
                        'title': "Old Important Memory",
                        'content': "This hasn't been reviewed in a while",
                        'importance': 0.9,
                        'created_at': datetime.utcnow() - timedelta(days=30),
                        'updated_at': datetime.utcnow() - timedelta(days=30),
                        'last_accessed': datetime.utcnow() - timedelta(days=20),
                        'access_count': 3,
                        'days_since_access': 20
                    })()
                ]
            })()
        else:
            return type('obj', (object,), {
                'fetchall': lambda: [],
                'fetchone': lambda: None
            })()


@pytest.fixture
async def mock_db():
    """Create mock database session"""
    db = MockDatabase()

    # Add test memories
    db.memories = [
        MockMemory(
            id=uuid4(),
            title="Machine Learning Basics",
            content="Introduction to supervised and unsupervised learning",
            importance=0.8,
            created_at=datetime.utcnow() - timedelta(days=10),
            last_accessed=datetime.utcnow() - timedelta(days=2)
        ),
        MockMemory(
            id=uuid4(),
            title="Deep Learning Fundamentals",
            content="Neural networks and backpropagation explained",
            importance=0.9,
            created_at=datetime.utcnow() - timedelta(days=5)
        ),
        MockMemory(
            id=uuid4(),
            title="Computer Vision Applications",
            content="Using CNNs for image recognition tasks",
            importance=0.7,
            created_at=datetime.utcnow() - timedelta(days=1)
        )
    ]

    return db


@pytest.fixture
async def mock_memory_service(mock_db):
    """Create mock memory service"""
    service = MockMemoryService()

    # Copy memories from mock_db
    for memory in mock_db.memories:
        service.memories[memory.id] = memory

    return service


@pytest.fixture
async def suggestion_engine(mock_db, mock_memory_service):
    """Create suggestion engine with mocks"""
    engine = SmartSuggestionEngine(mock_db)
    engine.memory_service = mock_memory_service
    engine.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()
    return engine


@pytest.fixture
def sample_context():
    """Create sample suggestion context"""
    return SuggestionContext(
        current_memory_id=uuid4(),
        recent_memory_ids=[uuid4(), uuid4()],
        current_topics=["machine learning", "deep learning"],
        current_entities=["neural network", "CNN"],
        user_goals=["learn AI", "build projects"],
        time_of_day="afternoon",
        activity_level="medium"
    )


class TestSmartSuggestionEngine:
    """Test Smart Suggestion Engine"""

    async def test_generate_suggestions(self, suggestion_engine, sample_context):
        """Test generating mixed suggestions"""
        batch = await suggestion_engine.generate_suggestions(
            user_id="test_user",
            context=sample_context,
            max_suggestions=10
        )

        assert isinstance(batch, SuggestionBatch)
        assert len(batch.suggestions) > 0
        assert len(batch.suggestions) <= 10
        assert batch.total_available >= len(batch.suggestions)
        assert batch.generation_time_ms > 0
        assert batch.algorithm_version == "1.0.0"
        assert len(batch.filtering_applied) > 0

    async def test_related_memory_suggestions(self, suggestion_engine, sample_context, mock_db):
        """Test related memory suggestions"""
        # Set current memory to first in list
        sample_context.current_memory_id = mock_db.memories[0].id

        suggestions = await suggestion_engine._generate_related_memory_suggestions(
            user_id="test_user",
            context=sample_context
        )

        assert isinstance(suggestions, list)
        assert all(isinstance(s, MemorySuggestion) for s in suggestions)

        if suggestions:
            suggestion = suggestions[0]
            assert suggestion.type == SuggestionType.RELATED_MEMORY
            assert suggestion.memory_id is not None
            assert suggestion.relevance_score > 0
            assert len(suggestion.memory_preview) > 0

    async def test_connection_suggestions(self, suggestion_engine, sample_context, mock_db):
        """Test connection suggestions"""
        sample_context.current_memory_id = mock_db.memories[0].id

        suggestions = await suggestion_engine._generate_connection_suggestions(
            user_id="test_user",
            context=sample_context
        )

        assert isinstance(suggestions, list)
        assert all(isinstance(s, ConnectionSuggestion) for s in suggestions)

        if suggestions:
            suggestion = suggestions[0]
            assert suggestion.type == SuggestionType.MISSING_CONNECTION
            assert suggestion.source_memory_id == sample_context.current_memory_id
            assert suggestion.target_memory_id is not None
            assert suggestion.suggested_relationship in ["related_to", "follows_from", "supports"]
            assert len(suggestion.supporting_evidence) > 0

    async def test_question_suggestions(self, suggestion_engine, sample_context, mock_memory_service):
        """Test question suggestions"""
        # Add current memory to service
        current_memory = MockMemory(
            id=sample_context.current_memory_id,
            title="Test Memory",
            content="This is a test memory about machine learning"
        )
        mock_memory_service.memories[current_memory.id] = current_memory

        suggestions = await suggestion_engine._generate_question_suggestions(
            user_id="test_user",
            context=sample_context
        )

        assert isinstance(suggestions, list)
        assert all(isinstance(s, QuestionSuggestion) for s in suggestions)

        if suggestions:
            suggestion = suggestions[0]
            assert suggestion.type == SuggestionType.FOLLOW_UP_QUESTION
            assert len(suggestion.question) > 0
            assert suggestion.expected_answer_type in ["factual", "exploratory", "analytical", "creative"]
            assert len(suggestion.related_topics) > 0

    async def test_gap_suggestions(self, suggestion_engine, sample_context):
        """Test knowledge gap suggestions"""
        suggestions = await suggestion_engine._generate_gap_suggestions(
            user_id="test_user",
            context=sample_context
        )

        assert isinstance(suggestions, list)
        assert all(isinstance(s, GapSuggestion) for s in suggestions)

        # Gap detection is simplified in mock, so may be empty
        for suggestion in suggestions:
            assert suggestion.type == SuggestionType.KNOWLEDGE_GAP
            assert suggestion.gap_type in ["missing_topic", "incomplete_entity", "time_gap", "detail_gap"]
            assert len(suggestion.filling_strategies) > 0

    async def test_review_suggestions(self, suggestion_engine, sample_context):
        """Test review reminder suggestions"""
        suggestions = await suggestion_engine._generate_review_suggestions(
            user_id="test_user",
            context=sample_context
        )

        assert isinstance(suggestions, list)
        assert all(isinstance(s, ReviewSuggestion) for s in suggestions)

        if suggestions:
            suggestion = suggestions[0]
            assert suggestion.type == SuggestionType.REVIEW_REMINDER
            assert suggestion.memory_id is not None
            assert suggestion.review_reason in ["forgetting_curve", "importance_decay", "update_needed", "quality_check"]
            assert len(suggestion.suggested_actions) > 0
            assert suggestion.review_interval_days > 0

    async def test_suggestion_ranking(self, suggestion_engine, sample_context):
        """Test suggestion ranking and filtering"""
        # Create diverse suggestions
        suggestions = [
            MemorySuggestion(
                type=SuggestionType.RELATED_MEMORY,
                title="High Priority",
                description="Important suggestion",
                reason="High relevance",
                confidence=0.9,
                priority=0.9,
                memory_id=uuid4(),
                memory_title="Important Memory",
                memory_preview="Preview",
                relevance_score=0.9,
                common_topics=["machine learning"]
            ),
            MemorySuggestion(
                type=SuggestionType.RELATED_MEMORY,
                title="Low Priority",
                description="Less important",
                reason="Lower relevance",
                confidence=0.3,
                priority=0.3,
                memory_id=uuid4(),
                memory_title="Less Important",
                memory_preview="Preview",
                relevance_score=0.3
            ),
            ConnectionSuggestion(
                type=SuggestionType.MISSING_CONNECTION,
                title="Connection",
                description="Connect memories",
                reason="High similarity",
                confidence=0.8,
                priority=0.7,
                source_memory_id=uuid4(),
                target_memory_id=uuid4(),
                source_title="Source",
                target_title="Target",
                suggested_relationship="related_to",
                supporting_evidence=["Evidence"]
            )
        ]

        ranked = await suggestion_engine._rank_suggestions(
            suggestions,
            sample_context,
            max_count=2
        )

        assert len(ranked) == 2
        # First should be the high priority one
        assert ranked[0].confidence == 0.9
        # Should have diversity (no more than 2 of same type)
        types = [s.type for s in ranked]
        assert len(types) == len(set(types)) or types.count(SuggestionType.RELATED_MEMORY) <= 2

    async def test_time_multipliers(self, suggestion_engine):
        """Test time-based suggestion adjustments"""
        multipliers = {
            "morning": suggestion_engine._get_time_multiplier("morning"),
            "afternoon": suggestion_engine._get_time_multiplier("afternoon"),
            "evening": suggestion_engine._get_time_multiplier("evening"),
            "night": suggestion_engine._get_time_multiplier("night")
        }

        assert multipliers["morning"] == 1.0
        assert multipliers["afternoon"] == 0.9
        assert multipliers["evening"] == 0.8
        assert multipliers["night"] == 0.7

    async def test_specific_suggestion_types(self, suggestion_engine, sample_context):
        """Test requesting specific suggestion types"""
        # Only memory suggestions
        batch = await suggestion_engine.generate_suggestions(
            user_id="test_user",
            context=sample_context,
            max_suggestions=5,
            suggestion_types=[SuggestionType.RELATED_MEMORY]
        )

        assert all(
            s.type == SuggestionType.RELATED_MEMORY
            for s in batch.suggestions
            if isinstance(s, MemorySuggestion)
        )

        # Only review suggestions
        batch = await suggestion_engine.generate_suggestions(
            user_id="test_user",
            context=sample_context,
            max_suggestions=5,
            suggestion_types=[SuggestionType.REVIEW_REMINDER]
        )

        assert all(
            s.type == SuggestionType.REVIEW_REMINDER
            for s in batch.suggestions
            if isinstance(s, ReviewSuggestion)
        )

    async def test_empty_context(self, suggestion_engine):
        """Test with minimal context"""
        empty_context = SuggestionContext(
            time_of_day="afternoon",
            activity_level="medium"
        )

        batch = await suggestion_engine.generate_suggestions(
            user_id="test_user",
            context=empty_context,
            max_suggestions=5
        )

        assert isinstance(batch, SuggestionBatch)
        # Should still generate some suggestions (like reviews)

    async def test_review_determination(self, suggestion_engine):
        """Test review need determination logic"""
        # Test forgetting curve
        memory = type('obj', (object,), {
            'days_since_access': 30,
            'access_count': 2,
            'importance': 0.8,
            'created_at': datetime.utcnow() - timedelta(days=60),
            'updated_at': datetime.utcnow() - timedelta(days=60)
        })()

        review_info = suggestion_engine._determine_review_needs(memory)

        assert review_info['review_type'] in ['forgetting_curve', 'importance_decay', 'update_needed', 'quality_check']
        assert review_info['urgency'] > 0
        assert len(review_info['actions']) > 0
        assert review_info['interval'] > 0

        # Test old memory needing update
        old_memory = type('obj', (object,), {
            'days_since_access': 5,
            'access_count': 10,
            'importance': 0.5,
            'created_at': datetime.utcnow() - timedelta(days=120),
            'updated_at': datetime.utcnow() - timedelta(days=120)
        })()

        review_info = suggestion_engine._determine_review_needs(old_memory)
        assert review_info['review_type'] == 'update_needed'


@pytest.mark.asyncio
async def test_suggestion_engine_lifecycle():
    """Test complete suggestion engine lifecycle"""
    # Create all mocks
    db = MockDatabase()
    memory_service = MockMemoryService()

    # Add diverse memories
    test_memories = [
        MockMemory(
            id=uuid4(),
            title="Recent Important Memory",
            content="This is very important and recent",
            importance=0.95,
            created_at=datetime.utcnow() - timedelta(hours=2),
            last_accessed=datetime.utcnow() - timedelta(hours=1),
            access_count=5
        ),
        MockMemory(
            id=uuid4(),
            title="Old Forgotten Memory",
            content="This was important but hasn't been accessed",
            importance=0.8,
            created_at=datetime.utcnow() - timedelta(days=60),
            last_accessed=datetime.utcnow() - timedelta(days=45),
            access_count=2
        ),
        MockMemory(
            id=uuid4(),
            title="Frequently Accessed Memory",
            content="This is accessed often",
            importance=0.7,
            created_at=datetime.utcnow() - timedelta(days=30),
            last_accessed=datetime.utcnow() - timedelta(hours=12),
            access_count=50
        )
    ]

    db.memories = test_memories
    for memory in test_memories:
        memory_service.memories[memory.id] = memory

    # Create engine
    engine = SmartSuggestionEngine(db)
    engine.memory_service = memory_service
    engine.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()

    # Create rich context
    context = SuggestionContext(
        current_memory_id=test_memories[0].id,
        recent_memory_ids=[m.id for m in test_memories[:2]],
        current_topics=["ai", "machine learning"],
        current_entities=["neural networks"],
        user_goals=["master AI"],
        time_of_day="morning",
        activity_level="high"
    )

    # Generate suggestions
    batch = await engine.generate_suggestions(
        user_id="test_user",
        context=context,
        max_suggestions=10
    )

    assert batch is not None
    assert len(batch.suggestions) > 0
    assert batch.generation_time_ms > 0

    # Verify variety
    suggestion_types = set(s.type for s in batch.suggestions)
    assert len(suggestion_types) > 1  # Should have multiple types
