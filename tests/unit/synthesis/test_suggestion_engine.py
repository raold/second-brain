"""Tests for SuggestionEngine"""

import json
from collections import Counter
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.synthesis.suggestion_models import (
    ActionType,
    ContentSuggestion,
    LearningPathSuggestion,
    OrganizationSuggestion,
    Suggestion,
    SuggestionRequest,
    SuggestionResponse,
    SuggestionType,
)
from app.services.synthesis.suggestion_engine import (
    SuggestionEngine,
    UserBehaviorProfile,
)


class TestUserBehaviorProfile:
    """Test UserBehaviorProfile class"""

    def test_user_behavior_profile_creation(self):
        """Test creating user behavior profile"""
        profile = UserBehaviorProfile("user123")

        assert profile.user_id == "user123"
        assert isinstance(profile.access_patterns, dict)
        assert isinstance(profile.topic_interests, dict)
        assert isinstance(profile.creation_patterns, dict)
        assert profile.learning_velocity == 0.0
        assert profile.exploration_score == 0.0

        # Check creation patterns structure
        assert 'peak_hours' in profile.creation_patterns
        assert 'active_days' in profile.creation_patterns
        assert 'avg_content_length' in profile.creation_patterns
        assert isinstance(profile.creation_patterns['preferred_tags'], Counter)


class TestSuggestionEngine:
    """Test SuggestionEngine"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        mock_db = AsyncMock()
        mock_memory_service = AsyncMock()
        mock_openai_client = AsyncMock()
        mock_analytics_engine = AsyncMock()

        return mock_db, mock_memory_service, mock_openai_client, mock_analytics_engine

    @pytest.fixture
    def engine(self, mock_dependencies):
        """Create engine instance with mocks"""
        db, memory_service, openai_client, analytics_engine = mock_dependencies
        return SuggestionEngine(db, memory_service, openai_client, analytics_engine)

    @pytest.fixture
    def sample_request(self):
        """Create sample suggestion request"""
        return SuggestionRequest(
            user_id="test_user",
            context_memory_ids=[uuid4(), uuid4()],
            suggestion_types=[SuggestionType.EXPLORE, SuggestionType.CONNECT],
            limit=10
        )

    @pytest.fixture
    def sample_access_logs(self):
        """Create sample access logs"""
        memory_ids = [uuid4() for _ in range(5)]
        return [
            {'memory_id': memory_ids[0], 'access_count': 10, 'last_access': datetime.utcnow()},
            {'memory_id': memory_ids[1], 'access_count': 8, 'last_access': datetime.utcnow()},
            {'memory_id': memory_ids[2], 'access_count': 5, 'last_access': datetime.utcnow()},
        ]

    @pytest.fixture
    def sample_recent_memories(self):
        """Create sample recent memories"""
        base_time = datetime.utcnow()
        return [
            {
                'id': uuid4(),
                'content': 'Python programming is versatile',
                'tags': ['Python', 'Programming'],
                'importance': 8,
                'created_at': base_time - timedelta(hours=i),
                'updated_at': base_time - timedelta(hours=i)
            }
            for i in range(10)
        ]

    @pytest.mark.asyncio
    async def test_generate_suggestions_success(self, engine, sample_request):
        """Test successful suggestion generation"""
        # Mock profile building
        mock_profile = UserBehaviorProfile("test_user")
        mock_profile.topic_interests = {'Python': 0.9, 'ML': 0.7}
        mock_profile.learning_velocity = 1.5
        engine._build_user_profile = AsyncMock(return_value=mock_profile)

        # Mock knowledge state
        mock_knowledge_state = {
            'total_memories': 100,
            'unique_topics': 20,
            'coverage_score': 0.7,
            'knowledge_gaps': [],
            'clusters': []
        }
        engine._analyze_knowledge_state = AsyncMock(return_value=mock_knowledge_state)

        # Mock suggestion generation methods
        engine._generate_exploration_suggestions = AsyncMock(return_value=[
            Suggestion(
                id="explore_1",
                type=SuggestionType.EXPLORE,
                title="Explore Advanced Python",
                description="Deepen your Python knowledge",
                action=ActionType.CREATE,
                priority=0.8
            )
        ])

        engine._generate_connection_suggestions = AsyncMock(return_value=[
            Suggestion(
                id="connect_1",
                type=SuggestionType.CONNECT,
                title="Connect Python and ML",
                description="Bridge your interests",
                action=ActionType.LINK,
                priority=0.7
            )
        ])

        engine._generate_learning_paths = AsyncMock(return_value=[])
        engine._generate_content_suggestions = AsyncMock(return_value=[])
        engine._generate_organization_tips = AsyncMock(return_value=[])

        # Execute
        response = await engine.generate_suggestions(sample_request)

        # Verify
        assert isinstance(response, SuggestionResponse)
        assert len(response.suggestions) == 2
        assert response.suggestions[0].priority > response.suggestions[1].priority  # Sorted by priority
        assert 'profile_completeness' in response.metadata
        assert 'knowledge_coverage' in response.metadata

    @pytest.mark.asyncio
    async def test_generate_suggestions_error_handling(self, engine, sample_request):
        """Test error handling in suggestion generation"""
        engine._build_user_profile = AsyncMock(side_effect=Exception("Database error"))

        response = await engine.generate_suggestions(sample_request)

        assert response.suggestions == []
        assert 'error' in response.metadata

    @pytest.mark.asyncio
    async def test_build_user_profile(self, engine, sample_access_logs, sample_recent_memories):
        """Test user profile building"""
        # Mock database queries
        engine.db.fetch_all = AsyncMock(side_effect=[
            sample_access_logs,  # Access logs
            sample_recent_memories  # Recent memories
        ])

        # Mock memory service
        mock_memory = MagicMock()
        mock_memory.tags = ['Python', 'Programming']
        engine.memory_service.get_memory = AsyncMock(return_value=mock_memory)

        # Execute
        profile = await engine._build_user_profile("test_user")

        # Verify
        assert isinstance(profile, UserBehaviorProfile)
        assert profile.user_id == "test_user"
        assert len(profile.access_patterns) > 0
        assert profile.learning_velocity > 0
        assert profile.exploration_score > 0
        assert len(profile.topic_interests) > 0
        assert len(profile.creation_patterns['preferred_tags']) > 0

    @pytest.mark.asyncio
    async def test_analyze_knowledge_state(self, engine):
        """Test knowledge state analysis"""
        # Mock analytics engine responses
        from uuid import uuid4

        from app.insights.models import Insight, InsightResponse, InsightType, TimeFrame, UsageStatistics
        mock_insights = InsightResponse(
            insights=[Insight(
                id=uuid4(),
                type=InsightType.KNOWLEDGE_GROWTH,
                title="Rapid growth",
                description="Your knowledge is growing",
                confidence=0.8,
                impact_score=7.5,
                data={},
                created_at=datetime.utcnow(),
                time_frame=TimeFrame.WEEKLY
            )],
            total=1,
            time_frame=TimeFrame.WEEKLY,
            generated_at=datetime.utcnow(),
            statistics=UsageStatistics(
                time_frame=TimeFrame.WEEKLY,
                total_memories=100,
                total_accesses=150,
                unique_accessed=50,
                average_importance=0.7,
                most_accessed_memories=[],
                access_frequency={"Monday": 20, "Tuesday": 30},
                peak_usage_times=["14:00", "20:00"],
                growth_rate=0.15
            )
        )

        # Mock cluster and gap analysis
        mock_clusters = MagicMock()
        mock_clusters.clusters = [
            MagicMock(cluster_theme="Python", size=20),
            MagicMock(cluster_theme="ML", size=15)
        ]

        mock_gaps = MagicMock()
        mock_gaps.gaps = [
            MagicMock(area="Deep Learning", suggested_topics=["Neural Networks", "CNNs"])
        ]
        mock_gaps.coverage_score = 0.75

        engine.analytics_engine.generate_insights = AsyncMock(return_value=mock_insights)
        engine.analytics_engine.analyze_clusters = AsyncMock(return_value=mock_clusters)
        engine.analytics_engine.analyze_knowledge_gaps = AsyncMock(return_value=mock_gaps)

        # Mock database stats
        engine.db.fetch_one = AsyncMock(return_value={
            'total_memories': 150,
            'unique_tags': 25,
            'avg_importance': 7.5,
            'last_activity': datetime.utcnow()
        })

        # Execute
        state = await engine._analyze_knowledge_state("test_user")

        # Verify
        assert state['total_memories'] == 150
        assert state['unique_topics'] == 25
        assert state['coverage_score'] == 0.75
        assert len(state['insights']) == 1
        assert len(state['clusters']) == 2
        assert len(state['knowledge_gaps']) == 1

    @pytest.mark.asyncio
    async def test_generate_exploration_suggestions(self, engine):
        """Test exploration suggestion generation"""
        profile = UserBehaviorProfile("test_user")
        profile.topic_interests = {'Python': 0.9, 'ML': 0.8, 'Web': 0.6}
        profile.creation_patterns['preferred_tags'] = Counter(['Python', 'ML', 'Django'])

        knowledge_state = {
            'knowledge_gaps': [
                MagicMock(area="Cloud Computing", suggested_topics=["AWS", "Docker"])
            ]
        }

        # Mock LLM response
        engine.openai_client.generate = AsyncMock(
            return_value=json.dumps([
                {
                    'topic': 'Kubernetes',
                    'reason': 'Natural progression from Docker',
                    'starting_point': 'Container orchestration basics'
                }
            ])
        )

        suggestions = await engine._generate_exploration_suggestions(profile, knowledge_state)

        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.EXPLORE
        assert suggestions[0].action == ActionType.CREATE
        assert 'topic' in suggestions[0].metadata

    @pytest.mark.asyncio
    async def test_generate_connection_suggestions(self, engine):
        """Test connection suggestion generation"""
        profile = UserBehaviorProfile("test_user")

        # Mock disconnected clusters
        cluster1 = MagicMock(
            cluster_id="c1",
            cluster_theme="Python",
            member_nodes=["n1", "n2"]
        )
        cluster2 = MagicMock(
            cluster_id="c2",
            cluster_theme="JavaScript",
            member_nodes=["n3", "n4"]
        )

        knowledge_state = {'clusters': [cluster1, cluster2]}

        # Mock database for isolated memories
        engine.db.fetch_all = AsyncMock(return_value=[
            {
                'id': uuid4(),
                'content': 'Important isolated knowledge',
                'tags': ['Isolated'],
                'importance': 8
            }
        ])

        # Mock LLM for connection suggestions
        engine.openai_client.generate = AsyncMock(
            return_value="Connect through web development patterns"
        )

        suggestions = await engine._generate_connection_suggestions(profile, knowledge_state)

        assert len(suggestions) > 0
        assert any(s.type == SuggestionType.CONNECT for s in suggestions)
        assert any(s.action == ActionType.LINK for s in suggestions)

    @pytest.mark.asyncio
    async def test_generate_review_suggestions(self, engine):
        """Test review suggestion generation"""
        profile = UserBehaviorProfile("test_user")

        # Mock memories needing review
        old_access = datetime.utcnow() - timedelta(days=20)
        engine.db.fetch_all = AsyncMock(side_effect=[
            # Memories not accessed recently
            [
                {
                    'id': uuid4(),
                    'content': 'Important concept to review',
                    'importance': 8,
                    'created_at': datetime.utcnow() - timedelta(days=30),
                    'last_accessed': old_access
                }
            ],
            # Topics with many memories
            [
                {'tags': 'Python', 'memory_count': 25, 'avg_importance': 7.5}
            ]
        ])

        knowledge_state = {}

        suggestions = await engine._generate_review_suggestions(profile, knowledge_state)

        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.REVIEW
        assert suggestions[0].action == ActionType.REVIEW
        assert 'days_since_access' in suggestions[0].metadata

    @pytest.mark.asyncio
    async def test_generate_organization_suggestions(self, engine):
        """Test organization suggestion generation"""
        profile = UserBehaviorProfile("test_user")
        profile.creation_patterns['preferred_tags'] = Counter({
            'Python': 20, 'ML': 15, 'Web': 10, 'Data': 8
        })

        # Mock untagged memories
        engine.db.fetch_all = AsyncMock(return_value=[
            {'id': uuid4(), 'content': 'Untagged memory 1', 'importance': 7},
            {'id': uuid4(), 'content': 'Untagged memory 2', 'importance': 6},
            {'id': uuid4(), 'content': 'Untagged memory 3', 'importance': 8},
        ])

        knowledge_state = {'total_memories': 100}

        suggestions = await engine._generate_organization_suggestions(profile, knowledge_state)

        assert len(suggestions) > 0
        assert any(s.type == SuggestionType.ORGANIZE for s in suggestions)
        assert any(s.action == ActionType.TAG for s in suggestions)
        assert any(s.action == ActionType.CONSOLIDATE for s in suggestions)

    @pytest.mark.asyncio
    async def test_generate_learning_paths(self, engine):
        """Test learning path generation"""
        profile = UserBehaviorProfile("test_user")
        profile.topic_interests = {'Python': 0.9, 'ML': 0.7}

        knowledge_state = {
            'knowledge_gaps': [
                MagicMock(
                    area="Deep Learning",
                    suggested_topics=["Neural Networks", "CNNs", "RNNs"]
                )
            ]
        }

        request = SuggestionRequest(user_id="test_user")

        paths = await engine._generate_learning_paths(profile, knowledge_state, request)

        assert len(paths) > 0
        assert isinstance(paths[0], LearningPathSuggestion)
        assert len(paths[0].steps) > 0
        assert paths[0].estimated_duration_days > 0
        assert paths[0].difficulty_level in ["beginner", "intermediate", "advanced"]

    @pytest.mark.asyncio
    async def test_generate_content_suggestions(self, engine):
        """Test content suggestion generation"""
        profile = UserBehaviorProfile("test_user")
        profile.learning_velocity = 2.0  # High velocity
        profile.topic_interests = {'Python': 0.8, 'ML': 0.9}

        knowledge_state = {'total_memories': 120}

        suggestions = await engine._generate_content_suggestions(profile, knowledge_state)

        assert len(suggestions) > 0
        assert isinstance(suggestions[0], ContentSuggestion)
        assert suggestions[0].content_type in ["synthesis", "deep_dive", "reflection"]
        assert len(suggestions[0].prompts) > 0
        assert 0 <= suggestions[0].estimated_value <= 1

    @pytest.mark.asyncio
    async def test_generate_organization_tips(self, engine):
        """Test organization tips generation"""
        profile = UserBehaviorProfile("test_user")
        profile.creation_patterns['preferred_tags'] = Counter({
            f'tag_{i}': i for i in range(25)  # Many different tags
        })

        knowledge_state = {'total_memories': 75}

        tips = await engine._generate_organization_tips(profile, knowledge_state)

        assert len(tips) > 0
        assert isinstance(tips[0], OrganizationSuggestion)
        assert tips[0].organization_type in ["tagging", "structure", "maintenance"]
        assert len(tips[0].implementation_steps) > 0
        assert tips[0].estimated_effort in ["low", "medium", "high"]

    def test_find_peak_hours(self, engine):
        """Test peak hour detection"""
        times = [
            datetime.utcnow().replace(hour=9) for _ in range(10)
        ] + [
            datetime.utcnow().replace(hour=14) for _ in range(8)
        ] + [
            datetime.utcnow().replace(hour=20) for _ in range(5)
        ]

        peak_hours = engine._find_peak_hours(times)

        assert len(peak_hours) <= 3
        assert 9 in peak_hours  # Most common hour
        assert all(0 <= h <= 23 for h in peak_hours)

    def test_find_active_days(self, engine):
        """Test active days detection"""
        # Create times for specific weekdays
        times = []
        base = datetime.utcnow()

        # Add many Mondays
        monday = base - timedelta(days=base.weekday())
        for i in range(5):
            times.append(monday - timedelta(weeks=i))

        # Add some Fridays
        friday = monday + timedelta(days=4)
        for i in range(3):
            times.append(friday - timedelta(weeks=i))

        active_days = engine._find_active_days(times)

        assert len(active_days) <= 2
        assert "Monday" in active_days

    def test_calculate_profile_completeness(self, engine):
        """Test profile completeness calculation"""
        # Complete profile
        complete_profile = UserBehaviorProfile("user1")
        complete_profile.access_patterns = {f'tag_{i}': i for i in range(10)}
        complete_profile.topic_interests = {f'topic_{i}': 0.5 for i in range(5)}
        complete_profile.creation_patterns['peak_hours'] = [9, 14, 20]
        complete_profile.learning_velocity = 0.8

        completeness = engine._calculate_profile_completeness(complete_profile)
        assert 0.8 <= completeness <= 1.0

        # Incomplete profile
        incomplete_profile = UserBehaviorProfile("user2")
        incomplete_profile.learning_velocity = 0.1

        incompleteness = engine._calculate_profile_completeness(incomplete_profile)
        assert 0 <= incompleteness <= 0.5

    def test_calculate_suggestion_confidence(self, engine):
        """Test suggestion confidence calculation"""
        # High confidence suggestions
        high_priority_suggestions = [
            Suggestion(
                id=f"s{i}",
                type=SuggestionType.EXPLORE,
                title=f"Suggestion {i}",
                description="High priority",
                action=ActionType.CREATE,
                priority=0.9
            )
            for i in range(4)
        ]

        high_confidence = engine._calculate_suggestion_confidence(high_priority_suggestions)
        assert 0.7 <= high_confidence <= 1.0

        # Low confidence
        low_priority_suggestions = [
            Suggestion(
                id="s1",
                type=SuggestionType.REVIEW,
                title="Low priority",
                description="Not important",
                action=ActionType.REVIEW,
                priority=0.3
            )
        ]

        low_confidence = engine._calculate_suggestion_confidence(low_priority_suggestions)
        assert low_confidence < 0.6

    def test_clusters_disconnected(self, engine):
        """Test cluster disconnection check"""
        # Disconnected clusters
        cluster1 = MagicMock(member_nodes=["n1", "n2", "n3"])
        cluster2 = MagicMock(member_nodes=["n4", "n5", "n6"])

        assert engine._clusters_disconnected(cluster1, cluster2) is True

        # Connected clusters (share a node)
        cluster3 = MagicMock(member_nodes=["n1", "n2", "n3"])
        cluster4 = MagicMock(member_nodes=["n3", "n4", "n5"])

        assert engine._clusters_disconnected(cluster3, cluster4) is False

    @pytest.mark.asyncio
    async def test_suggestion_limit(self, engine, sample_request):
        """Test that suggestion limit is respected"""
        sample_request.limit = 3

        # Create many suggestions
        many_suggestions = [
            Suggestion(
                id=f"s{i}",
                type=SuggestionType.EXPLORE,
                title=f"Suggestion {i}",
                description="Test",
                action=ActionType.CREATE,
                priority=min(0.5 + i * 0.05, 1.0)  # Ensure priority doesn't exceed 1.0
            )
            for i in range(10)
        ]

        # Mock methods to return many suggestions
        engine._build_user_profile = AsyncMock(return_value=UserBehaviorProfile("test"))
        engine._analyze_knowledge_state = AsyncMock(return_value={})
        engine._generate_exploration_suggestions = AsyncMock(return_value=many_suggestions[:5])
        engine._generate_connection_suggestions = AsyncMock(return_value=many_suggestions[5:])
        engine._generate_learning_paths = AsyncMock(return_value=[])
        engine._generate_content_suggestions = AsyncMock(return_value=[])
        engine._generate_organization_tips = AsyncMock(return_value=[])

        response = await engine.generate_suggestions(sample_request)

        assert len(response.suggestions) == 3  # Respects limit
        # Check they're the highest priority ones
        assert all(response.suggestions[i].priority >= response.suggestions[i+1].priority
                  for i in range(len(response.suggestions)-1))
