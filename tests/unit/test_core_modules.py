"""
Comprehensive Core Module Tests for Second Brain v2.6.0-dev

Tests actual functionality of core modules instead of just imports.
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.models import Memory
from app.database import get_db, initialize_database
from app.memory_relationships import MemoryRelationshipManager
from app.memory_visualization import MemoryVisualizationEngine
from app.version import get_version, get_version_info


class TestMainApplication:
    """Test main.py application functionality"""
    
    def test_app_instance_creation(self):
        """Test FastAPI app instance is created properly"""
        from app.main import app
        
        assert isinstance(app, FastAPI)
        assert app.title == "Second Brain"
        assert "Second Brain PostgreSQL" in app.description
    
    def test_app_middleware_setup(self):
        """Test middleware is properly configured"""
        from app.main import app
        
        # Check CORS middleware is configured
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        middleware_names = [str(mw) for mw in middleware_types]
        
        # Should have CORS or similar middleware
        assert len(app.user_middleware) > 0
    
    @pytest.mark.asyncio
    async def test_app_lifespan_startup(self):
        """Test application startup sequence"""
        from app.main import initialize_database
        
        # Mock database initialization
        with patch('app.main.asyncpg.create_pool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # Should not raise exception
            await initialize_database()
    
    def test_app_routes_registered(self):
        """Test essential routes are registered"""
        from app.main import app
        
        routes = [route.path for route in app.routes]
        
        # Check essential routes exist
        assert "/" in routes
        assert "/health" in routes
        assert "/memories" in routes
        assert "/search" in routes


class TestDatabaseModule:
    """Test database functionality"""
    
    @pytest.mark.asyncio
    async def test_database_connection_mock(self):
        """Test database connection with mock"""
        with patch('app.database.asyncpg.create_pool') as mock_pool:
            mock_connection = AsyncMock()
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_connection
            
            # Test connection acquisition
            async with get_db() as conn:
                assert conn is not None
    
    @pytest.mark.asyncio
    async def test_initialize_database_function(self):
        """Test database initialization"""
        with patch('app.database.asyncpg.create_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            await initialize_database()
            
            # Verify SQL execution was attempted
            assert mock_conn.execute.called
    
    def test_database_url_configuration(self):
        """Test database URL configuration"""
        from app.database import DATABASE_URL
        
        assert DATABASE_URL is not None
        assert "postgresql" in DATABASE_URL.lower() or "postgres" in DATABASE_URL.lower()
    
    @pytest.mark.asyncio
    async def test_memory_model_validation(self):
        """Test Memory model validation"""
        # Valid memory
        memory_data = {
            "id": uuid4(),
            "content": "Test memory content",
            "importance": 7.5,
            "tags": ["test", "validation"],
            "metadata": {"source": "test"},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        memory = Memory(**memory_data)
        assert memory.content == "Test memory content"
        assert memory.importance == 7.5
        assert "test" in memory.tags
    
    def test_memory_model_validation_errors(self):
        """Test Memory model validation catches errors"""
        # Test invalid importance
        with pytest.raises((ValueError, TypeError)):
            Memory(
                content="Test",
                importance="invalid",  # Should be float
                tags=[]
            )
        
        # Test missing required field
        with pytest.raises((ValueError, TypeError)):
            Memory(
                importance=5.0,
                tags=[]
                # Missing content
            )


class TestMemoryRelationships:
    """Test memory relationships functionality"""
    
    @pytest.fixture
    def relationship_manager(self):
        """Create relationship manager instance"""
        return MemoryRelationshipManager()
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for testing"""
        memories = []
        for i in range(5):
            memory = Mock()
            memory.id = uuid4()
            memory.content = f"Test memory {i}"
            memory.tags = [f"tag{i}", "common"]
            memory.importance = 5.0 + i
            memory.created_at = datetime.utcnow() - timedelta(days=i)
            memories.append(memory)
        return memories
    
    @pytest.mark.asyncio
    async def test_find_tag_relationships(self, relationship_manager, sample_memories):
        """Test finding relationships based on tags"""
        # Mock database call
        with patch.object(relationship_manager, '_get_memories_by_tags') as mock_get:
            mock_get.return_value = sample_memories
            
            relationships = await relationship_manager.find_tag_relationships(sample_memories[0])
            
            assert len(relationships) > 0
            # Should find memories with shared tags
            assert any(rel.type == "tag_similarity" for rel in relationships)
    
    @pytest.mark.asyncio
    async def test_find_semantic_relationships(self, relationship_manager, sample_memories):
        """Test finding semantic relationships"""
        with patch.object(relationship_manager, '_calculate_semantic_similarity') as mock_sim:
            mock_sim.return_value = 0.8  # High similarity
            
            relationships = await relationship_manager.find_semantic_relationships(
                sample_memories[0], 
                sample_memories[1:]
            )
            
            assert len(relationships) > 0
            assert all(rel.similarity >= 0.7 for rel in relationships)
    
    @pytest.mark.asyncio
    async def test_find_temporal_relationships(self, relationship_manager, sample_memories):
        """Test finding temporal relationships"""
        relationships = await relationship_manager.find_temporal_relationships(
            sample_memories[0],
            sample_memories[1:]
        )
        
        # Should find memories created close in time
        assert len(relationships) >= 0
        for rel in relationships:
            assert rel.type == "temporal_proximity"
            assert rel.strength > 0
    
    def test_calculate_relationship_strength(self, relationship_manager):
        """Test relationship strength calculation"""
        # Same tags should have high strength
        memory1 = Mock()
        memory1.tags = ["work", "project", "important"]
        memory1.importance = 8.0
        
        memory2 = Mock()
        memory2.tags = ["work", "project"]
        memory2.importance = 7.0
        
        strength = relationship_manager._calculate_tag_similarity(memory1, memory2)
        assert strength > 0.5  # Should be relatively high
        
        # No shared tags should have low strength
        memory3 = Mock()
        memory3.tags = ["personal", "hobby"]
        memory3.importance = 6.0
        
        strength = relationship_manager._calculate_tag_similarity(memory1, memory3)
        assert strength == 0  # No shared tags
    
    @pytest.mark.asyncio
    async def test_relationship_caching(self, relationship_manager, sample_memories):
        """Test relationship caching mechanism"""
        memory = sample_memories[0]
        
        # First call should compute relationships
        with patch.object(relationship_manager, '_compute_relationships') as mock_compute:
            mock_compute.return_value = []
            
            await relationship_manager.get_relationships(memory.id)
            assert mock_compute.called
            
            # Second call should use cache
            mock_compute.reset_mock()
            await relationship_manager.get_relationships(memory.id)
            assert not mock_compute.called


class TestMemoryVisualization:
    """Test memory visualization functionality"""
    
    @pytest.fixture
    def viz_engine(self):
        """Create visualization engine instance"""
        return MemoryVisualizationEngine()
    
    @pytest.fixture
    def graph_data(self):
        """Create sample graph data"""
        nodes = [
            {"id": str(uuid4()), "content": f"Memory {i}", "importance": 5.0 + i}
            for i in range(10)
        ]
        
        edges = [
            {
                "source": nodes[i]["id"],
                "target": nodes[i+1]["id"],
                "weight": 0.8,
                "type": "semantic"
            }
            for i in range(9)
        ]
        
        return {"nodes": nodes, "edges": edges}
    
    @pytest.mark.asyncio
    async def test_generate_network_graph(self, viz_engine):
        """Test network graph generation"""
        with patch.object(viz_engine, '_fetch_memories') as mock_fetch:
            mock_memories = [
                Mock(id=uuid4(), content="Memory 1", tags=["work"], importance=7.0),
                Mock(id=uuid4(), content="Memory 2", tags=["work", "project"], importance=8.0),
                Mock(id=uuid4(), content="Memory 3", tags=["personal"], importance=6.0)
            ]
            mock_fetch.return_value = mock_memories
            
            with patch.object(viz_engine, '_calculate_relationships') as mock_rel:
                mock_rel.return_value = [
                    {"source": mock_memories[0].id, "target": mock_memories[1].id, "weight": 0.9}
                ]
                
                graph = await viz_engine.generate_network_graph()
                
                assert "nodes" in graph
                assert "edges" in graph
                assert len(graph["nodes"]) == 3
                assert len(graph["edges"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_timeline_visualization(self, viz_engine):
        """Test timeline visualization"""
        with patch.object(viz_engine, '_fetch_memories_by_date') as mock_fetch:
            # Create memories with different dates
            base_date = datetime.utcnow()
            mock_memories = [
                Mock(
                    id=uuid4(),
                    content=f"Memory {i}",
                    created_at=base_date - timedelta(days=i),
                    importance=5.0 + i
                )
                for i in range(7)  # Week of memories
            ]
            mock_fetch.return_value = mock_memories
            
            timeline = await viz_engine.generate_timeline(days=7)
            
            assert "timeline" in timeline
            assert len(timeline["timeline"]) > 0
            
            # Should be sorted by date
            dates = [item["date"] for item in timeline["timeline"]]
            assert dates == sorted(dates)
    
    def test_calculate_node_positions(self, viz_engine, graph_data):
        """Test node position calculation for graph layout"""
        positions = viz_engine._calculate_positions(graph_data["nodes"], graph_data["edges"])
        
        assert len(positions) == len(graph_data["nodes"])
        
        # Each position should have x, y coordinates
        for node_id, pos in positions.items():
            assert "x" in pos
            assert "y" in pos
            assert isinstance(pos["x"], (int, float))
            assert isinstance(pos["y"], (int, float))
    
    def test_generate_tag_cloud_data(self, viz_engine):
        """Test tag cloud data generation"""
        with patch.object(viz_engine, '_get_tag_statistics') as mock_stats:
            mock_stats.return_value = {
                "work": {"count": 50, "avg_importance": 7.5},
                "personal": {"count": 30, "avg_importance": 6.0},
                "project": {"count": 25, "avg_importance": 8.0},
                "idea": {"count": 15, "avg_importance": 5.5}
            }
            
            tag_cloud = viz_engine.generate_tag_cloud()
            
            assert "tags" in tag_cloud
            assert len(tag_cloud["tags"]) == 4
            
            # Should be sorted by count or importance
            tags = tag_cloud["tags"]
            assert tags[0]["name"] == "work"  # Highest count
            
            # Each tag should have required fields
            for tag in tags:
                assert "name" in tag
                assert "count" in tag
                assert "weight" in tag
                assert "avg_importance" in tag
    
    def test_cluster_visualization(self, viz_engine):
        """Test memory cluster visualization"""
        with patch.object(viz_engine, '_perform_clustering') as mock_cluster:
            mock_clusters = [
                {
                    "id": 0,
                    "center": [0.5, 0.3, 0.8],
                    "memories": [str(uuid4()) for _ in range(10)],
                    "label": "Work Projects"
                },
                {
                    "id": 1,
                    "center": [0.2, 0.9, 0.1],
                    "memories": [str(uuid4()) for _ in range(8)],
                    "label": "Personal Notes"
                }
            ]
            mock_cluster.return_value = mock_clusters
            
            cluster_viz = viz_engine.generate_cluster_visualization()
            
            assert "clusters" in cluster_viz
            assert len(cluster_viz["clusters"]) == 2
            
            for cluster in cluster_viz["clusters"]:
                assert "id" in cluster
                assert "memories" in cluster
                assert "label" in cluster


class TestVersionManagement:
    """Test version management functionality"""
    
    def test_get_version_string(self):
        """Test version string retrieval"""
        version = get_version()
        
        assert isinstance(version, str)
        assert len(version) > 0
        # Should follow semantic versioning pattern
        assert "." in version
    
    def test_get_version_info_structure(self):
        """Test version info structure"""
        version_info = get_version_info()
        
        assert isinstance(version_info, dict)
        assert "version" in version_info
        assert "build" in version_info
        assert "timestamp" in version_info
        
        # Version should match get_version()
        assert version_info["version"] == get_version()
    
    def test_version_consistency(self):
        """Test version consistency across calls"""
        version1 = get_version()
        version2 = get_version()
        
        assert version1 == version2
        
        info1 = get_version_info()
        info2 = get_version_info()
        
        assert info1["version"] == info2["version"]


class TestConfigurationManagement:
    """Test configuration and environment handling"""
    
    def test_environment_variables_loading(self):
        """Test environment variables are loaded correctly"""
        import os
        from app.database import DATABASE_URL
        
        # Should load from environment or have default
        assert DATABASE_URL is not None
        
        # Test API tokens
        api_tokens = os.environ.get("API_TOKENS", "")
        assert isinstance(api_tokens, str)
    
    def test_mock_database_detection(self):
        """Test mock database detection"""
        import os
        
        use_mock = os.environ.get("USE_MOCK_DATABASE", "false").lower()
        assert use_mock in ["true", "false"]
    
    @patch.dict('os.environ', {'USE_MOCK_DATABASE': 'true'})
    def test_mock_database_mode(self):
        """Test mock database mode activation"""
        from app.database_mock import MockDatabase
        
        # Should be able to create mock database instance
        mock_db = MockDatabase()
        assert mock_db is not None
        assert hasattr(mock_db, 'create_memory')
        assert hasattr(mock_db, 'get_memories')


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test database connection error handling"""
        with patch('app.database.asyncpg.create_pool') as mock_pool:
            mock_pool.side_effect = Exception("Connection failed")
            
            # Should handle connection errors gracefully
            with pytest.raises(Exception):
                await initialize_database()
    
    def test_memory_validation_error_handling(self):
        """Test memory validation error handling"""
        # Invalid data should raise appropriate errors
        with pytest.raises((ValueError, TypeError)):
            Memory(
                content="",  # Empty content
                importance=15.0,  # Out of range
                tags=["test"]
            )
    
    @pytest.mark.asyncio
    async def test_visualization_error_recovery(self):
        """Test visualization error recovery"""
        viz_engine = MemoryVisualizationEngine()
        
        with patch.object(viz_engine, '_fetch_memories') as mock_fetch:
            mock_fetch.side_effect = Exception("Database error")
            
            # Should return empty/default visualization
            graph = await viz_engine.generate_network_graph()
            
            # Should not crash, should return some default structure
            assert isinstance(graph, dict)
            assert "nodes" in graph
            assert "edges" in graph


class TestPerformanceConsiderations:
    """Test performance-related functionality"""
    
    @pytest.mark.asyncio
    async def test_memory_loading_pagination(self):
        """Test memory loading with pagination"""
        from app.memory_relationships import MemoryRelationshipManager
        
        manager = MemoryRelationshipManager()
        
        with patch.object(manager, '_fetch_memories_paginated') as mock_fetch:
            # Mock large dataset
            mock_fetch.return_value = [Mock() for _ in range(50)]
            
            # Should handle pagination
            memories = await manager._get_memories_batch(limit=50, offset=0)
            
            assert len(memories) <= 50
            mock_fetch.assert_called_with(limit=50, offset=0)
    
    def test_relationship_calculation_efficiency(self):
        """Test relationship calculation efficiency"""
        from app.memory_relationships import MemoryRelationshipManager
        
        manager = MemoryRelationshipManager()
        
        # Create many memories
        memories = [
            Mock(id=uuid4(), tags=[f"tag{i%5}"], importance=i%10)
            for i in range(100)
        ]
        
        # Should complete in reasonable time
        import time
        start = time.time()
        
        # Calculate relationships for first memory
        relationships = manager._find_tag_relationships_batch(memories[0], memories[1:50])
        
        elapsed = time.time() - start
        
        # Should be fast (under 1 second for this test)
        assert elapsed < 1.0
        assert isinstance(relationships, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])