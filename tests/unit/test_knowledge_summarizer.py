"""
Tests for Knowledge Summarizer Service
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.synthesis.summary_models import (
    ExecutiveSummary,
    PeriodSummary,
    SummaryRequest,
    TopicSummary,
)
from app.services.synthesis.knowledge_summarizer import KnowledgeSummarizer


class MockMemory:
    """Mock Memory object for testing"""
    def __init__(self, id: UUID, title: str, content: str, importance: float = 0.5,
                 created_at: datetime = None, memory_type: str = "episodic",
                 topics: list[str] = None):
        self.id = id
        self.title = title
        self.content = content
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.memory_type = memory_type
        self.user_id = "test_user"
        self.topics = topics or []


class MockOpenAIClient:
    """Mock OpenAI client for testing"""
    async def create(self, **kwargs):
        messages = kwargs.get('messages', [])

        # Check what type of summary is being requested
        if "topic summary" in str(messages):
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''
                        {
                            "summary": "This topic covers the fundamentals of machine learning, including supervised and unsupervised learning approaches.",
                            "key_insights": [
                                "Machine learning enables systems to learn from data",
                                "Deep learning is a subset of machine learning",
                                "Neural networks are inspired by biological systems"
                            ],
                            "related_entities": [
                                {"name": "TensorFlow", "type": "technology", "relevance": 0.9},
                                {"name": "PyTorch", "type": "technology", "relevance": 0.8}
                            ],
                            "related_topics": ["artificial intelligence", "deep learning", "neural networks"],
                            "confidence": 0.9
                        }
                        '''
                    })()
                })]
            })()
        elif "time period" in str(messages):
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''
                        {
                            "summary": "This week focused on machine learning fundamentals and practical implementations.",
                            "highlights": [
                                "Completed neural network implementation",
                                "Studied backpropagation algorithm",
                                "Explored CNN architectures"
                            ],
                            "new_topics": ["transformers", "attention mechanisms"],
                            "new_entities": ["BERT", "GPT"],
                            "trends": [
                                {"trend": "Increased focus on deep learning", "strength": 0.8}
                            ]
                        }
                        '''
                    })()
                })]
            })()
        else:  # Executive summary
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '''
                        {
                            "title": "Machine Learning Knowledge Overview",
                            "summary": "Comprehensive analysis of machine learning concepts and implementations.",
                            "key_points": [
                                "Strong foundation in ML fundamentals",
                                "Practical experience with neural networks",
                                "Growing expertise in deep learning"
                            ],
                            "action_items": [
                                "Explore transformer architectures",
                                "Implement attention mechanisms"
                            ],
                            "questions_raised": [
                                "How do transformers compare to RNNs?",
                                "What are the latest advances in NLP?"
                            ],
                            "opportunities": [
                                "Apply ML to real-world projects",
                                "Contribute to open-source ML libraries"
                            ],
                            "risks": [
                                "Need to stay updated with rapid advances"
                            ],
                            "confidence": 0.85
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

    async def search_memories(self, user_id: str, query: str = None, filters: dict = None):
        # Simple topic-based search
        if filters and 'topics' in filters:
            topic = filters['topics'][0] if isinstance(filters['topics'], list) else filters['topics']
            return [m for m in self.memories.values() if topic in m.topics]
        return list(self.memories.values())


class MockDatabase:
    """Mock database for testing"""
    def __init__(self):
        self.memories = []

    async def execute(self, query, params=None):
        query_str = str(query)

        if "extract_topics" in query_str:
            # Mock topic extraction
            return type('obj', (object,), {
                'fetchall': lambda: [
                    ('machine learning', 5),
                    ('deep learning', 3),
                    ('neural networks', 4)
                ]
            })()
        elif "SELECT m.* FROM memories" in query_str:
            # Mock memory search by date range
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'id': m.id,
                        'title': m.title,
                        'content': m.content,
                        'importance': m.importance,
                        'created_at': m.created_at,
                        'memory_type': m.memory_type
                    })() for m in self.memories
                ]
            })()
        elif "graph_visualization" in query_str:
            # Mock graph data
            return type('obj', (object,), {
                'fetchall': lambda: [
                    type('obj', (object,), {
                        'nodes': [
                            {"id": str(uuid4()), "label": "ML Basics", "importance": 0.8},
                            {"id": str(uuid4()), "label": "Deep Learning", "importance": 0.9}
                        ],
                        'edges': [
                            {"source": 0, "target": 1, "weight": 0.7}
                        ]
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
            title="Introduction to Machine Learning",
            content="Machine learning is a method of data analysis that automates analytical model building.",
            importance=0.8,
            created_at=datetime.utcnow() - timedelta(days=7),
            topics=["machine learning", "ai"]
        ),
        MockMemory(
            id=uuid4(),
            title="Deep Learning Fundamentals",
            content="Deep learning is part of a broader family of machine learning methods based on artificial neural networks.",
            importance=0.9,
            created_at=datetime.utcnow() - timedelta(days=3),
            topics=["deep learning", "neural networks"]
        ),
        MockMemory(
            id=uuid4(),
            title="Neural Network Architecture",
            content="A neural network is a series of algorithms that endeavors to recognize underlying relationships in data.",
            importance=0.85,
            created_at=datetime.utcnow() - timedelta(days=1),
            topics=["neural networks", "architecture"]
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
async def summarizer(mock_db, mock_memory_service):
    """Create knowledge summarizer with mocks"""
    summarizer = KnowledgeSummarizer(mock_db)
    summarizer.memory_service = mock_memory_service
    summarizer.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()
    return summarizer


class TestKnowledgeSummarizer:
    """Test Knowledge Summarizer Service"""

    async def test_summarize_topic(self, summarizer):
        """Test topic summarization"""
        summary = await summarizer.summarize_topic(
            user_id="test_user",
            topic="machine learning",
            max_memories=10,
            min_importance=0.5
        )

        assert isinstance(summary, TopicSummary)
        assert summary.topic == "machine learning"
        assert len(summary.summary) > 0
        assert len(summary.key_insights) == 3
        assert len(summary.related_entities) == 2
        assert len(summary.related_topics) == 3
        assert summary.confidence_score == 0.9
        assert summary.memory_count > 0

    async def test_summarize_time_period(self, summarizer):
        """Test time period summarization"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        summary = await summarizer.summarize_time_period(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date,
            period_type="weekly"
        )

        assert isinstance(summary, PeriodSummary)
        assert summary.start_date == start_date
        assert summary.end_date == end_date
        assert summary.period_type == "weekly"
        assert len(summary.summary) > 0
        assert len(summary.highlights) == 3
        assert len(summary.new_topics) == 2
        assert len(summary.new_entities) == 2
        assert len(summary.trends) == 1

    async def test_generate_executive_summary(self, summarizer, mock_memory_service):
        """Test executive summary generation"""
        memory_ids = list(mock_memory_service.memories.keys())

        summary = await summarizer.generate_executive_summary(
            user_id="test_user",
            memory_ids=memory_ids,
            include_graph=True,
            style="professional"
        )

        assert isinstance(summary, ExecutiveSummary)
        assert summary.title == "Machine Learning Knowledge Overview"
        assert len(summary.summary) > 0
        assert len(summary.key_points) == 3
        assert len(summary.action_items) == 2
        assert len(summary.questions_raised) == 2
        assert len(summary.opportunities) == 2
        assert len(summary.risks) == 1
        assert summary.confidence_score == 0.85
        assert summary.graph_visualization is not None

    async def test_process_summary_request(self, summarizer, mock_memory_service):
        """Test processing summary requests"""
        # Topic summary request
        request = SummaryRequest(
            summary_type="topic",
            target="machine learning",
            max_memories=20,
            include_graph=True,
            style="professional"
        )

        result = await summarizer.process_summary_request(
            user_id="test_user",
            request=request
        )

        assert result is not None
        assert isinstance(result, (TopicSummary, PeriodSummary, ExecutiveSummary))

        # Period summary request
        request = SummaryRequest(
            summary_type="period",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            include_metrics=True
        )

        result = await summarizer.process_summary_request(
            user_id="test_user",
            request=request
        )

        assert result is not None
        assert isinstance(result, PeriodSummary)

        # Executive summary request
        memory_ids = list(mock_memory_service.memories.keys())
        request = SummaryRequest(
            summary_type="executive",
            memory_ids=memory_ids,
            include_graph=True,
            focus_areas=["implementation", "theory"]
        )

        result = await summarizer.process_summary_request(
            user_id="test_user",
            request=request
        )

        assert result is not None
        assert isinstance(result, ExecutiveSummary)

    async def test_fallback_methods(self, summarizer):
        """Test fallback summarization methods"""
        memories = summarizer.memory_service.memories.values()

        # Test topic summary fallback
        summary = await summarizer._fallback_topic_summary(
            "test topic",
            list(memories)
        )

        assert "test topic" in summary
        assert len(summary) > 0

        # Test period summary fallback
        summary = await summarizer._fallback_period_summary(
            list(memories),
            "daily"
        )

        assert "daily" in summary.lower()
        assert len(summary) > 0

        # Test executive summary fallback
        summary = await summarizer._fallback_executive_summary(
            list(memories)
        )

        assert "executive summary" in summary.lower()
        assert len(summary) > 0

    async def test_extract_key_points(self, summarizer):
        """Test key points extraction"""
        text = """
        Machine learning is revolutionizing how we process data.
        Deep learning models achieve state-of-the-art results.
        Neural networks can learn complex patterns.
        Transfer learning reduces training time significantly.
        """

        key_points = await summarizer._extract_key_points(text, max_points=3)

        assert isinstance(key_points, list)
        assert len(key_points) <= 3
        assert all(isinstance(point, str) for point in key_points)
        assert all(len(point) > 0 for point in key_points)

    async def test_identify_entities(self, summarizer):
        """Test entity identification"""
        memories = list(summarizer.memory_service.memories.values())

        entities = await summarizer._identify_entities(memories)

        assert isinstance(entities, list)
        # Should find some entities in the test data
        assert any("learning" in str(e).lower() for e in entities)

    async def test_edge_cases(self, summarizer):
        """Test edge cases"""
        # Empty topic
        summary = await summarizer.summarize_topic(
            user_id="test_user",
            topic="nonexistent_topic",
            max_memories=10
        )

        assert summary.memory_count == 0
        assert "No memories found" in summary.summary

        # Future date range
        future_start = datetime.utcnow() + timedelta(days=30)
        future_end = future_start + timedelta(days=7)

        summary = await summarizer.summarize_time_period(
            user_id="test_user",
            start_date=future_start,
            end_date=future_end,
            period_type="weekly"
        )

        assert len(summary.highlights) == 0 or "No memories found" in summary.summary

        # Empty memory list for executive summary
        summary = await summarizer.generate_executive_summary(
            user_id="test_user",
            memory_ids=[],
            include_graph=False
        )

        # Should handle gracefully, possibly with a message about no memories
        assert summary is not None

    async def test_different_styles(self, summarizer, mock_memory_service):
        """Test different summary styles"""
        memory_ids = list(mock_memory_service.memories.keys())

        styles = ["professional", "casual", "technical", "academic"]

        for style in styles:
            summary = await summarizer.generate_executive_summary(
                user_id="test_user",
                memory_ids=memory_ids,
                style=style
            )

            assert isinstance(summary, ExecutiveSummary)
            # Style would affect the tone of the summary in real implementation


@pytest.mark.asyncio
async def test_summarizer_lifecycle():
    """Test complete summarizer lifecycle"""
    # Create all mocks
    db = MockDatabase()
    memory_service = MockMemoryService()

    # Add diverse test memories
    test_memories = [
        MockMemory(
            id=uuid4(),
            title="Python Programming Basics",
            content="Python is a high-level programming language known for its simplicity.",
            importance=0.7,
            created_at=datetime.utcnow() - timedelta(days=10),
            topics=["python", "programming"]
        ),
        MockMemory(
            id=uuid4(),
            title="Advanced Python Techniques",
            content="Decorators, generators, and context managers are powerful Python features.",
            importance=0.8,
            created_at=datetime.utcnow() - timedelta(days=5),
            topics=["python", "advanced"]
        ),
        MockMemory(
            id=uuid4(),
            title="Machine Learning with Python",
            content="Python is the dominant language for machine learning and data science.",
            importance=0.9,
            created_at=datetime.utcnow() - timedelta(days=2),
            topics=["python", "machine learning"]
        )
    ]

    db.memories = test_memories
    for memory in test_memories:
        memory_service.memories[memory.id] = memory

    # Create summarizer
    summarizer = KnowledgeSummarizer(db)
    summarizer.memory_service = memory_service
    summarizer.openai_client = type('obj', (object,), {
        'chat': type('obj', (object,), {
            'completions': MockOpenAIClient()
        })()
    })()

    # Test topic summary
    topic_summary = await summarizer.summarize_topic(
        user_id="test_user",
        topic="python",
        max_memories=10
    )

    assert topic_summary.topic == "python"
    assert topic_summary.memory_count > 0

    # Test period summary
    period_summary = await summarizer.summarize_time_period(
        user_id="test_user",
        start_date=datetime.utcnow() - timedelta(days=14),
        end_date=datetime.utcnow(),
        period_type="weekly"
    )

    assert period_summary.period_type == "weekly"
    assert len(period_summary.highlights) > 0

    # Test executive summary
    memory_ids = list(memory_service.memories.keys())
    exec_summary = await summarizer.generate_executive_summary(
        user_id="test_user",
        memory_ids=memory_ids,
        include_graph=True
    )

    assert exec_summary.title is not None
    assert len(exec_summary.key_points) > 0
    assert exec_summary.confidence_score > 0
