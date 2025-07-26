"""Tests for GraphMetricsService"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import networkx as nx
import numpy as np
import pytest

from app.models.synthesis.metrics_models import (
    ConnectivityMetrics,
    GraphMetrics,
    MetricsRequest,
    NodeMetrics,
    TemporalMetrics,
)
from app.services.synthesis.graph_metrics_service import GraphMetricsService, GraphNode


class TestGraphNode:
    """Test GraphNode class"""
    
    def test_graph_node_creation(self):
        """Test creating a graph node"""
        node_id = uuid4()
        node = GraphNode(
            node_id,
            "Test content",
            8.5,
            datetime.utcnow()
        )
        
        assert node.id == node_id
        assert node.content == "Test content"
        assert node.importance == 8.5
        assert isinstance(node.created_at, datetime)
        assert isinstance(node.connections, set)
        assert isinstance(node.tags, set)
        assert isinstance(node.metadata, dict)


class TestGraphMetricsService:
    """Test GraphMetricsService"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        mock_db = AsyncMock()
        mock_memory_service = AsyncMock()
        mock_relationship_analyzer = AsyncMock()
        
        return mock_db, mock_memory_service, mock_relationship_analyzer
    
    @pytest.fixture
    def service(self, mock_dependencies):
        """Create service instance with mocks"""
        db, memory_service, relationship_analyzer = mock_dependencies
        return GraphMetricsService(db, memory_service, relationship_analyzer)
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for graph"""
        base_time = datetime.utcnow()
        return [
            {
                'id': uuid4(),
                'content': 'Python programming basics',
                'importance': 8,
                'created_at': base_time,
                'tags': ['Python', 'Programming'],
                'metadata': {}
            },
            {
                'id': uuid4(),
                'content': 'Advanced Python concepts',
                'importance': 9,
                'created_at': base_time - timedelta(days=5),
                'tags': ['Python', 'Advanced'],
                'metadata': {}
            },
            {
                'id': uuid4(),
                'content': 'Machine Learning with Python',
                'importance': 9,
                'created_at': base_time - timedelta(days=10),
                'tags': ['Python', 'ML'],
                'metadata': {}
            },
            {
                'id': uuid4(),
                'content': 'JavaScript basics',
                'importance': 7,
                'created_at': base_time - timedelta(days=15),
                'tags': ['JavaScript'],
                'metadata': {}
            }
        ]
    
    @pytest.fixture
    def sample_relationships(self, sample_memories):
        """Create sample relationships"""
        return [
            {
                'source_id': sample_memories[0]['id'],
                'target_id': sample_memories[1]['id'],
                'relationship_type': 'related_to',
                'strength': 0.8,
                'created_at': datetime.utcnow()
            },
            {
                'source_id': sample_memories[1]['id'],
                'target_id': sample_memories[2]['id'],
                'relationship_type': 'prerequisite_for',
                'strength': 0.9,
                'created_at': datetime.utcnow()
            }
        ]
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_success(self, service, sample_memories, sample_relationships):
        """Test successful metrics calculation"""
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=sample_relationships)
        
        request = MetricsRequest(include_relationships=True)
        metrics = await service.calculate_metrics(request)
        
        assert isinstance(metrics, GraphMetrics)
        assert metrics.total_nodes == 4
        assert metrics.total_edges == 2
        assert 0 <= metrics.graph_density <= 1
        assert metrics.average_degree > 0
        assert 0 <= metrics.clustering_coefficient <= 1
        assert isinstance(metrics.node_metrics, dict)
        assert isinstance(metrics.connectivity_metrics, ConnectivityMetrics)
        assert isinstance(metrics.temporal_metrics, TemporalMetrics)
        assert 0 <= metrics.health_score <= 1
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_empty_graph(self, service):
        """Test metrics calculation with empty graph"""
        service._fetch_graph_memories = AsyncMock(return_value=[])
        service._fetch_relationships = AsyncMock(return_value=[])
        
        request = MetricsRequest()
        metrics = await service.calculate_metrics(request)
        
        assert metrics.total_nodes == 0
        assert metrics.total_edges == 0
        assert metrics.graph_density == 0
        assert metrics.metadata.get('empty') is True
    
    @pytest.mark.asyncio
    async def test_analyze_node_importance(self, service, sample_memories, sample_relationships):
        """Test node importance analysis"""
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=sample_relationships)
        
        # Clear cache to force rebuild
        service._graph_cache = None
        
        node_id = sample_memories[1]['id']  # Node with connections
        node_metrics = await service.analyze_node_importance(node_id)
        
        assert isinstance(node_metrics, NodeMetrics)
        assert node_metrics.node_id == node_id
        assert node_metrics.degree >= 2  # Has at least 2 connections
        assert 0 <= node_metrics.betweenness_centrality <= 1
        assert 0 <= node_metrics.closeness_centrality <= 1
        assert node_metrics.pagerank_score > 0
        assert 0 <= node_metrics.clustering_coefficient <= 1
    
    @pytest.mark.asyncio
    async def test_analyze_node_importance_not_found(self, service):
        """Test node importance analysis for non-existent node"""
        service._fetch_graph_memories = AsyncMock(return_value=[])
        service._fetch_relationships = AsyncMock(return_value=[])
        
        with pytest.raises(ValueError, match="not found in graph"):
            await service.analyze_node_importance(uuid4())
    
    @pytest.mark.asyncio
    async def test_find_knowledge_clusters(self, service, sample_memories, sample_relationships):
        """Test knowledge cluster finding"""
        # Create a graph with clear clusters
        cluster1_memories = sample_memories[:3]  # Python cluster
        cluster2_memories = [sample_memories[3]]  # JavaScript cluster
        
        # Add more memories to make clusters significant
        for i in range(3):
            cluster1_memories.append({
                'id': uuid4(),
                'content': f'Python topic {i}',
                'importance': 7,
                'created_at': datetime.utcnow(),
                'tags': ['Python'],
                'metadata': {}
            })
        
        all_memories = cluster1_memories + cluster2_memories
        
        # Create relationships within cluster 1
        cluster1_relationships = []
        for i in range(len(cluster1_memories) - 1):
            cluster1_relationships.append({
                'source_id': cluster1_memories[i]['id'],
                'target_id': cluster1_memories[i + 1]['id'],
                'relationship_type': 'related_to',
                'strength': 0.8,
                'created_at': datetime.utcnow()
            })
        
        service._fetch_graph_memories = AsyncMock(return_value=all_memories)
        service._fetch_relationships = AsyncMock(return_value=cluster1_relationships)
        
        clusters = await service.find_knowledge_clusters(min_cluster_size=3)
        
        assert isinstance(clusters, list)
        assert len(clusters) >= 1  # At least one significant cluster
        assert clusters[0].size >= 3
        assert 0 <= clusters[0].density <= 1
        assert len(clusters[0].central_nodes) > 0
        assert clusters[0].cluster_theme != ""
    
    @pytest.mark.asyncio
    async def test_build_knowledge_graph(self, service, sample_memories, sample_relationships):
        """Test knowledge graph building"""
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=sample_relationships)
        
        graph = await service._build_knowledge_graph()
        
        assert isinstance(graph, nx.Graph)
        assert graph.number_of_nodes() == len(sample_memories)
        assert graph.number_of_edges() == len(sample_relationships)
        
        # Check node attributes
        node_id = sample_memories[0]['id']
        assert graph.nodes[node_id]['content'] == sample_memories[0]['content']
        assert graph.nodes[node_id]['importance'] == sample_memories[0]['importance']
        
        # Check edge attributes
        edge = (sample_relationships[0]['source_id'], sample_relationships[0]['target_id'])
        assert graph.has_edge(*edge)
        assert graph.edges[edge]['relationship_type'] == 'related_to'
    
    @pytest.mark.asyncio
    async def test_graph_caching(self, service, sample_memories, sample_relationships):
        """Test graph caching mechanism"""
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=sample_relationships)
        
        # First call should build graph
        graph1 = await service._build_knowledge_graph()
        fetch_count1 = service._fetch_graph_memories.call_count
        
        # Second call should use cache
        graph2 = await service._build_knowledge_graph()
        fetch_count2 = service._fetch_graph_memories.call_count
        
        assert fetch_count2 == fetch_count1  # No additional fetches
        assert graph1 is graph2  # Same instance
        
        # Call with specific memory IDs should bypass cache
        graph3 = await service._build_knowledge_graph([uuid4()])
        fetch_count3 = service._fetch_graph_memories.call_count
        
        assert fetch_count3 > fetch_count2  # Additional fetch
        assert graph3 is not graph2  # Different instance
    
    @pytest.mark.asyncio
    async def test_calculate_connectivity_metrics(self, service, sample_memories, sample_relationships):
        """Test connectivity metrics calculation"""
        # Create a connected graph
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=sample_relationships)
        
        graph = await service._build_knowledge_graph()
        metrics = await service._calculate_connectivity_metrics(graph)
        
        assert isinstance(metrics, ConnectivityMetrics)
        assert isinstance(metrics.is_connected, bool)
        assert metrics.num_connected_components >= 1
        assert metrics.largest_component_size >= 1
        assert metrics.average_path_length >= 0
        assert metrics.diameter >= 0
        assert metrics.edge_connectivity >= 0
        assert metrics.node_connectivity >= 0
        assert metrics.num_bridges >= 0
        assert metrics.num_articulation_points >= 0
    
    @pytest.mark.asyncio
    async def test_calculate_temporal_metrics(self, service, sample_memories):
        """Test temporal metrics calculation"""
        service._fetch_graph_memories = AsyncMock(return_value=sample_memories)
        service._fetch_relationships = AsyncMock(return_value=[])
        
        graph = await service._build_knowledge_graph()
        metrics = await service._calculate_temporal_metrics(graph)
        
        assert isinstance(metrics, TemporalMetrics)
        assert metrics.growth_rate > 0  # Memories per day
        assert 0 <= metrics.recent_activity_score <= 1
        assert isinstance(metrics.temporal_clusters, list)
        assert isinstance(metrics.activity_periods, list)
        assert 'total_time_span_days' in metrics.metadata
        assert 'first_memory' in metrics.metadata
        assert 'last_memory' in metrics.metadata
    
    def test_find_temporal_clusters(self, service):
        """Test temporal cluster detection"""
        # Create times with clear clusters
        base_time = datetime.utcnow()
        times = [
            # Cluster 1: rapid succession
            base_time,
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=3),
            # Gap
            base_time + timedelta(days=5),
            # Cluster 2: another burst
            base_time + timedelta(days=5, hours=1),
            base_time + timedelta(days=5, hours=2),
            base_time + timedelta(days=5, hours=3),
        ]
        
        clusters = service._find_temporal_clusters(times)
        
        assert len(clusters) >= 1  # At least one cluster
        assert clusters[0]['size'] >= 3
        assert 'start_time' in clusters[0]
        assert 'end_time' in clusters[0]
        assert 'duration_hours' in clusters[0]
    
    def test_identify_activity_periods(self, service):
        """Test activity period identification"""
        # Create times with clear patterns
        times = []
        for day in range(30):
            base = datetime.utcnow() - timedelta(days=day)
            # Most activity at 9am and 3pm
            times.append(base.replace(hour=9))
            times.append(base.replace(hour=9))
            times.append(base.replace(hour=15))
        
        periods = service._identify_activity_periods(times)
        
        assert len(periods) > 0
        assert any("Peak activity hours" in p for p in periods)
    
    def test_calculate_graph_health(self, service):
        """Test graph health score calculation"""
        node_metrics = {
            'avg_clustering': 0.7,
            'degree_distribution': {'mean': 5},
            'isolated_nodes': ['node1', 'node2']
        }
        
        cluster_metrics = {
            'modularity': 0.6
        }
        
        connectivity_metrics = ConnectivityMetrics(
            is_connected=True,
            num_connected_components=1,
            largest_component_size=100,
            average_path_length=3.5,
            diameter=7,
            edge_connectivity=2,
            node_connectivity=2,
            num_bridges=5,
            num_articulation_points=3,
            metadata={}
        )
        
        health_score = service._calculate_graph_health(
            node_metrics,
            cluster_metrics,
            connectivity_metrics
        )
        
        assert 0 <= health_score <= 1
        # Connected graph with good clustering should have decent health
        assert health_score > 0.5
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling in metrics calculation"""
        service._fetch_graph_memories = AsyncMock(side_effect=Exception("Database error"))
        
        request = MetricsRequest()
        metrics = await service.calculate_metrics(request)
        
        # Should return empty metrics on error
        assert metrics.total_nodes == 0
        assert metrics.metadata.get('empty') is True
    
    def test_calculate_cluster_modularity(self, service):
        """Test cluster modularity calculation"""
        # Create a simple graph
        graph = nx.Graph()
        graph.add_edges_from([(1, 2), (2, 3), (3, 1), (4, 5), (5, 6)])
        
        # Cluster 1: nodes 1, 2, 3
        cluster_nodes = {1, 2, 3}
        
        modularity = service._calculate_cluster_modularity(graph, cluster_nodes)
        
        assert 0 <= modularity <= 1
        # This cluster has all internal edges, so high modularity
        assert modularity > 0.5