"""
Tests for Graph Metrics Service
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.synthesis.metrics_models import (
    GraphMetrics,
    MetricsAlert,
    MetricsDashboard,
    MetricsSnapshot,
    MetricsTrend,
)
from app.services.synthesis.graph_metrics_service import AnomalyDetector, GraphMetricsService


class MockMemory:
    """Mock Memory object for testing"""
    def __init__(self, id: UUID, title: str, user_id: str = "test_user",
                 importance: float = 0.5, created_at: datetime = None,
                 memory_type: str = "episodic"):
        self.id = id
        self.title = title
        self.user_id = user_id
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.memory_type = memory_type
        self.deleted_at = None


class MockCacheService:
    """Mock cache service for testing"""
    def __init__(self):
        self.cache = {}

    async def get_metrics(self, user_id: str, graph_id: str):
        key = f"{user_id}:{graph_id}"
        return self.cache.get(key)

    async def set_metrics(self, user_id: str, graph_id: str, metrics: GraphMetrics):
        key = f"{user_id}:{graph_id}"
        self.cache[key] = metrics


class MockDatabase:
    """Mock database for testing"""
    def __init__(self):
        self.memories = []
        self.relationships = []

    async def execute(self, query, params=None):
        query_str = str(query)

        if "FROM memories" in query_str and "deleted_at IS NULL" in query_str:
            # Return memories
            return type('obj', (object,), {
                'scalars': lambda: type('obj', (object,), {
                    'all': lambda: self.memories
                })()
            })()
        elif "FROM memory_relationships" in query_str:
            # Return relationships
            return type('obj', (object,), {
                'fetchall': lambda: self.relationships
            })()
        elif "daily_stats" in query_str:
            # Return growth stats
            return type('obj', (object,), {
                'fetchone': lambda: type('obj', (object,), {
                    'avg_nodes_per_day': 2.5,
                    'avg_edges_per_day': 3.2
                })()
            })()
        elif "last hour" in query_str:
            # Return hourly stats
            return type('obj', (object,), {
                'fetchone': lambda: type('obj', (object,), {
                    'new_nodes_last_hour': 1,
                    'new_edges_last_hour': 2
                })()
            })()
        else:
            return type('obj', (object,), {
                'fetchall': lambda: [],
                'fetchone': lambda: None,
                'scalars': lambda: type('obj', (object,), {
                    'all': lambda: []
                })()
            })()


@pytest.fixture
async def mock_db():
    """Create mock database with test data"""
    db = MockDatabase()

    # Add test memories
    memories = [
        MockMemory(uuid4(), "Memory 1", importance=0.8),
        MockMemory(uuid4(), "Memory 2", importance=0.7),
        MockMemory(uuid4(), "Memory 3", importance=0.9),
        MockMemory(uuid4(), "Memory 4", importance=0.6),
        MockMemory(uuid4(), "Memory 5", importance=0.5),
    ]
    db.memories = memories

    # Add test relationships
    db.relationships = [
        type('obj', (object,), {
            'source_id': memories[0].id,
            'target_id': memories[1].id,
            'relationship_type': 'related_to',
            'strength': 0.8
        })(),
        type('obj', (object,), {
            'source_id': memories[1].id,
            'target_id': memories[2].id,
            'relationship_type': 'follows_from',
            'strength': 0.7
        })(),
        type('obj', (object,), {
            'source_id': memories[0].id,
            'target_id': memories[2].id,
            'relationship_type': 'supports',
            'strength': 0.6
        })(),
    ]

    return db


@pytest.fixture
async def mock_cache_service():
    """Create mock cache service"""
    return MockCacheService()


@pytest.fixture
async def metrics_service(mock_db, mock_cache_service):
    """Create graph metrics service with mocks"""
    service = GraphMetricsService(mock_db)
    service.cache_service = mock_cache_service
    return service


class TestGraphMetricsService:
    """Test Graph Metrics Service"""

    async def test_calculate_metrics(self, metrics_service):
        """Test basic metrics calculation"""
        metrics = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=False
        )

        assert isinstance(metrics, GraphMetrics)
        assert metrics.node_count == 5  # 5 test memories
        assert metrics.edge_count == 3  # 3 test relationships
        assert metrics.density > 0
        assert metrics.average_degree > 0
        assert metrics.calculation_time_ms > 0
        assert metrics.cache_hit == False

    async def test_metrics_caching(self, metrics_service):
        """Test metrics caching"""
        # First call - no cache
        metrics1 = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=True
        )
        assert metrics1.cache_hit == False

        # Second call - should hit cache
        metrics2 = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=True
        )
        assert metrics2.cache_hit == True
        assert metrics2.node_count == metrics1.node_count

    async def test_structural_metrics(self, metrics_service):
        """Test structural metrics calculation"""
        metrics = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=False
        )

        assert hasattr(metrics, 'clustering_coefficient')
        assert hasattr(metrics, 'connected_components')
        assert hasattr(metrics, 'largest_component_size')
        assert hasattr(metrics, 'diameter')
        assert hasattr(metrics, 'average_path_length')

        assert 0 <= metrics.clustering_coefficient <= 1
        assert metrics.connected_components >= 1
        assert metrics.largest_component_size <= metrics.node_count

    async def test_centrality_metrics(self, metrics_service):
        """Test centrality metrics calculation"""
        metrics = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=False
        )

        assert isinstance(metrics.degree_centrality, dict)
        assert isinstance(metrics.betweenness_centrality, dict)
        assert isinstance(metrics.closeness_centrality, dict)
        assert isinstance(metrics.eigenvector_centrality, dict)

        # Should have top nodes
        assert len(metrics.degree_centrality) <= 10

        # Centrality values should be normalized
        for centrality in metrics.degree_centrality.values():
            assert 0 <= centrality <= 1

    async def test_growth_metrics(self, metrics_service):
        """Test growth metrics calculation"""
        metrics = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="main",
            use_cache=False
        )

        assert metrics.growth_rate_nodes_per_day >= 0
        assert metrics.growth_rate_edges_per_day >= 0
        assert metrics.new_nodes_last_hour >= 0
        assert metrics.new_edges_last_hour >= 0

    async def test_metrics_dashboard(self, metrics_service):
        """Test comprehensive metrics dashboard"""
        dashboard = await metrics_service.get_metrics_dashboard(
            user_id="test_user",
            time_range_days=7,
            graph_id="main"
        )

        assert isinstance(dashboard, MetricsDashboard)
        assert dashboard.current_metrics is not None
        assert len(dashboard.historical_metrics) >= 1
        assert isinstance(dashboard.trends, dict)
        assert isinstance(dashboard.insights, list)
        assert isinstance(dashboard.recommendations, list)
        assert isinstance(dashboard.predictions, dict)
        assert isinstance(dashboard.summary, dict)
        assert dashboard.time_range_days == 7
        assert dashboard.generation_time_ms > 0

    async def test_trend_calculation(self, metrics_service):
        """Test trend calculation"""
        # Create historical metrics
        historical = []
        for i in range(5):
            metrics = GraphMetrics(
                graph_id="main",
                timestamp=datetime.utcnow() - timedelta(days=4-i),
                node_count=10 + i*2,  # Increasing trend
                edge_count=15 + i*3,
                density=0.1 + i*0.01,
                average_degree=3.0 + i*0.2,
                clustering_coefficient=0.3,
                connected_components=1,
                largest_component_size=10 + i*2,
                diameter=3,
                average_path_length=2.5,
                growth_rate_nodes_per_day=2.0,
                growth_rate_edges_per_day=3.0,
                calculation_time_ms=100
            )
            historical.append(metrics)

        trends = await metrics_service._calculate_trends(historical)

        assert "node_count" in trends
        assert "edge_count" in trends

        node_trend = trends["node_count"]
        assert isinstance(node_trend, MetricsTrend)
        assert node_trend.trend_direction == "increasing"
        assert node_trend.trend_strength > 0.5
        assert node_trend.average_value > 0
        assert node_trend.forecast_next_value is not None

    async def test_anomaly_detection(self, metrics_service):
        """Test anomaly detection"""
        detector = AnomalyDetector()

        # Create normal historical metrics
        historical = []
        for i in range(10):
            metrics = GraphMetrics(
                graph_id="main",
                timestamp=datetime.utcnow() - timedelta(days=9-i),
                node_count=100,
                edge_count=200,
                density=0.02,
                average_degree=4.0,
                clustering_coefficient=0.3,
                connected_components=1,
                largest_component_size=100,
                diameter=5,
                average_path_length=2.5,
                growth_rate_nodes_per_day=2.0,
                growth_rate_edges_per_day=4.0,
                calculation_time_ms=100
            )
            historical.append(metrics)

        # Create anomalous current metrics
        current = GraphMetrics(
            graph_id="main",
            timestamp=datetime.utcnow(),
            node_count=200,  # Anomaly: doubled
            edge_count=600,  # Anomaly: tripled
            density=0.015,
            average_degree=6.0,
            clustering_coefficient=0.3,
            connected_components=1,
            largest_component_size=200,
            diameter=5,
            average_path_length=2.5,
            growth_rate_nodes_per_day=100.0,  # Anomaly: huge spike
            growth_rate_edges_per_day=200.0,
            calculation_time_ms=150
        )

        anomalies = detector.detect(current, historical)

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0

        # Check node count anomaly
        node_anomaly = next((a for a in anomalies if a.metric_name == "node_count"), None)
        assert node_anomaly is not None
        assert node_anomaly.anomaly_type == "spike"
        assert node_anomaly.severity in ["medium", "high", "critical"]
        assert node_anomaly.current_value == 200
        assert node_anomaly.expected_value == 100
        assert len(node_anomaly.suggested_investigation) > 0

    async def test_create_snapshot(self, metrics_service):
        """Test metrics snapshot creation"""
        snapshot = await metrics_service.create_snapshot(
            user_id="test_user",
            name="Test Snapshot",
            description="Testing snapshot functionality",
            tags=["test", "metrics"]
        )

        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.name == "Test Snapshot"
        assert snapshot.description == "Testing snapshot functionality"
        assert snapshot.metrics is not None
        assert len(snapshot.tags) == 2
        assert snapshot.created_by == "test_user"
        assert len(snapshot.notable_nodes) > 0

    async def test_check_alerts(self, metrics_service):
        """Test alert checking"""
        # Create test alerts
        alerts = [
            MetricsAlert(
                name="High Node Count",
                metric_name="node_count",
                condition="greater_than",
                threshold=100,
                enabled=True
            ),
            MetricsAlert(
                name="Low Density",
                metric_name="density",
                condition="less_than",
                threshold=0.5,
                enabled=True
            ),
            MetricsAlert(
                name="Disabled Alert",
                metric_name="edge_count",
                condition="equals",
                threshold=999,
                enabled=False
            )
        ]

        results = await metrics_service.check_alerts(
            user_id="test_user",
            alerts=alerts
        )

        assert len(results) == 3

        # Check each alert result
        for alert, triggered in results:
            if alert.name == "High Node Count":
                assert triggered == False  # 5 nodes < 100
            elif alert.name == "Low Density":
                assert triggered == True  # Density should be < 0.5
            elif alert.name == "Disabled Alert":
                assert triggered == False  # Disabled alerts never trigger

    async def test_empty_graph(self, metrics_service, mock_db):
        """Test metrics with empty graph"""
        # Clear memories and relationships
        mock_db.memories = []
        mock_db.relationships = []

        metrics = await metrics_service.calculate_metrics(
            user_id="test_user",
            graph_id="empty",
            use_cache=False
        )

        assert metrics.node_count == 0
        assert metrics.edge_count == 0
        assert metrics.density == 0.0
        assert metrics.average_degree == 0.0
        assert metrics.clustering_coefficient == 0.0
        assert metrics.connected_components == 0

    async def test_insights_generation(self, metrics_service):
        """Test insights generation"""
        current_metrics = GraphMetrics(
            graph_id="main",
            timestamp=datetime.utcnow(),
            node_count=100,
            edge_count=50,
            density=0.01,  # Very sparse
            average_degree=1.0,
            clustering_coefficient=0.7,  # High clustering
            connected_components=10,  # Many components
            largest_component_size=20,
            diameter=5,
            average_path_length=2.5,
            growth_rate_nodes_per_day=15,  # High growth
            growth_rate_edges_per_day=5,
            calculation_time_ms=100
        )

        insights = await metrics_service._generate_insights(
            current_metrics,
            {},  # Empty trends
            []   # No anomalies
        )

        assert isinstance(insights, list)
        assert len(insights) > 0

        # Should detect sparse graph
        assert any("sparse" in insight.lower() for insight in insights)

        # Should detect high clustering
        assert any("clustering" in insight.lower() for insight in insights)

        # Should detect multiple components
        assert any("component" in insight.lower() for insight in insights)

    async def test_recommendations_generation(self, metrics_service):
        """Test recommendations generation"""
        current_metrics = GraphMetrics(
            graph_id="main",
            timestamp=datetime.utcnow(),
            node_count=1000,
            edge_count=500,
            density=0.001,  # Very sparse
            average_degree=1.0,
            clustering_coefficient=0.1,
            connected_components=5,
            largest_component_size=800,  # 200 isolated nodes
            diameter=10,
            average_path_length=5.0,
            growth_rate_nodes_per_day=30,  # High growth
            growth_rate_edges_per_day=10,
            calculation_time_ms=2000  # Slow calculation
        )

        recommendations = await metrics_service._generate_recommendations(
            current_metrics,
            {},  # Empty trends
            []   # No anomalies
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Should recommend creating connections
        assert any("connection" in rec.lower() for rec in recommendations)

        # Should recommend consolidation due to high growth
        assert any("consolidation" in rec.lower() for rec in recommendations)

        # Should recommend caching due to slow calculation
        assert any("caching" in rec.lower() for rec in recommendations)


@pytest.mark.asyncio
async def test_metrics_service_lifecycle():
    """Test complete metrics service lifecycle"""
    # Create mock database with rich data
    db = MockDatabase()

    # Create a more complex graph
    memories = []
    for i in range(20):
        memories.append(
            MockMemory(
                uuid4(),
                f"Memory {i}",
                importance=0.5 + (i % 5) * 0.1,
                created_at=datetime.utcnow() - timedelta(days=20-i)
            )
        )
    db.memories = memories

    # Create relationships forming clusters
    relationships = []
    # Cluster 1: memories 0-4
    for i in range(4):
        relationships.append(type('obj', (object,), {
            'source_id': memories[i].id,
            'target_id': memories[i+1].id,
            'relationship_type': 'related_to',
            'strength': 0.8
        })())

    # Cluster 2: memories 10-14
    for i in range(10, 14):
        relationships.append(type('obj', (object,), {
            'source_id': memories[i].id,
            'target_id': memories[i+1].id,
            'relationship_type': 'follows_from',
            'strength': 0.7
        })())

    # Bridge between clusters
    relationships.append(type('obj', (object,), {
        'source_id': memories[4].id,
        'target_id': memories[10].id,
        'relationship_type': 'related_to',
        'strength': 0.5
    })())

    db.relationships = relationships

    # Create service
    cache_service = MockCacheService()
    service = GraphMetricsService(db)
    service.cache_service = cache_service

    # Calculate initial metrics
    metrics = await service.calculate_metrics(
        user_id="test_user",
        graph_id="complex",
        use_cache=False
    )

    assert metrics.node_count == 20
    assert metrics.edge_count == len(relationships)
    assert metrics.connected_components >= 2  # At least 2 main clusters

    # Generate full dashboard
    dashboard = await service.get_metrics_dashboard(
        user_id="test_user",
        time_range_days=7,
        graph_id="complex"
    )

    assert dashboard is not None
    assert len(dashboard.insights) > 0
    assert len(dashboard.recommendations) > 0

    # Create snapshot
    snapshot = await service.create_snapshot(
        user_id="test_user",
        name="Complex Graph Snapshot",
        description="Snapshot of multi-cluster graph"
    )

    assert snapshot is not None
    assert len(snapshot.notable_nodes) > 0
