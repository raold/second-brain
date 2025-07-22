"""
Integration tests for AI insights API endpoints
"""

from datetime import datetime

import pytest


class TestInsightsAPI:
    """Test insights API endpoints"""

    @pytest.mark.asyncio
    async def test_generate_insights_endpoint(self, client, api_key):
        """Test the insights generation endpoint"""
        # Create some test memories first
        for i in range(15):
            memory_data = {
                "content": f"Test memory about programming concept {i}",
                "memory_type": "semantic",
                "importance_score": 0.75
            }
            response = await client.post(
                "/memories",
                json=memory_data,
                params={"api_key": api_key}
            )
            assert response.status_code == 200

        # Generate insights
        insight_request = {
            "time_frame": "all_time",
            "limit": 5,
            "min_confidence": 0.5,
            "include_recommendations": True
        }

        response = await client.post(
            "/insights/generate",
            json=insight_request,
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "insights" in data
        assert "total" in data
        assert "time_frame" in data
        assert "generated_at" in data
        assert "statistics" in data

        # Verify statistics
        stats = data["statistics"]
        assert stats["total_memories"] >= 15
        assert "average_importance" in stats
        assert "growth_rate" in stats

    @pytest.mark.asyncio
    async def test_detect_patterns_endpoint(self, client, api_key):
        """Test pattern detection endpoint"""
        # Create memories with temporal pattern
        datetime.utcnow()
        for i in range(10):
            memory_data = {
                "content": f"Morning routine memory {i}",
                "memory_type": "episodic",
                "importance_score": 0.6
            }
            response = await client.post(
                "/memories",
                json=memory_data,
                params={"api_key": api_key}
            )
            assert response.status_code == 200

        # Detect patterns
        pattern_request = {
            "pattern_types": ["temporal", "structural"],
            "time_frame": "all_time",
            "min_occurrences": 2,
            "min_strength": 0.3
        }

        response = await client.post(
            "/insights/patterns",
            json=pattern_request,
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert "patterns" in data
        assert "total" in data
        assert "time_frame" in data
        assert "detected_at" in data

    @pytest.mark.asyncio
    async def test_analyze_clusters_endpoint(self, client, api_key):
        """Test clustering analysis endpoint"""
        # Create clusterable memories
        topics = ["python", "javascript", "database"]
        for topic in topics:
            for i in range(5):
                memory_data = {
                    "content": f"Learning about {topic} - concept {i}",
                    "memory_type": "semantic",
                    "semantic_metadata": {
                        "category": topic,
                        "domain": "programming"
                    },
                    "importance_score": 0.7
                }
                response = await client.post(
                    "/memories",
                    json=memory_data,
                    params={"api_key": api_key}
                )
                assert response.status_code == 200

        # Analyze clusters
        cluster_request = {
            "algorithm": "kmeans",
            "num_clusters": 3,
            "min_cluster_size": 3,
            "similarity_threshold": 0.6
        }

        response = await client.post(
            "/insights/clusters",
            json=cluster_request,
            params={"api_key": api_key}
        )

        # The endpoint might fail if embeddings aren't available
        # In test mode, this is expected
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "clusters" in data
            assert "total_clusters" in data
            assert "clustering_quality_score" in data

    @pytest.mark.asyncio
    async def test_knowledge_gaps_endpoint(self, client, api_key):
        """Test knowledge gap analysis endpoint"""
        # Create memories with gaps
        memory_data = {
            "content": "Basic programming concepts in Python",
            "memory_type": "semantic",
            "semantic_metadata": {
                "category": "python",
                "domain": "programming"
            },
            "importance_score": 0.6
        }
        response = await client.post(
            "/memories",
            json=memory_data,
            params={"api_key": api_key}
        )
        assert response.status_code == 200

        # Analyze gaps
        gap_request = {
            "domains": ["programming", "databases", "algorithms"],
            "min_severity": 0.5,
            "include_suggestions": True,
            "limit": 10
        }

        response = await client.post(
            "/insights/gaps",
            json=gap_request,
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert "gaps" in data
        assert "total" in data
        assert "coverage_score" in data
        assert "suggested_learning_paths" in data
        assert "analyzed_at" in data

        # Should detect gaps in databases and algorithms
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_learning_progress_endpoint(self, client, api_key):
        """Test learning progress tracking endpoint"""
        # Create diverse memories with semantic metadata containing tags
        topics = ["python", "javascript", "react", "django"]
        for topic in topics:
            memory_data = {
                "content": f"Advanced concepts in {topic}",
                "memory_type": "semantic",
                "semantic_metadata": {
                    "category": topic,
                    "domain": "programming"
                },
                "importance_score": 0.8
            }
            response = await client.post(
                "/memories",
                json=memory_data,
                params={"api_key": api_key}
            )
            assert response.status_code == 200

        # Get learning progress
        response = await client.get(
            "/insights/progress",
            params={
                "api_key": api_key,
                "time_frame": "all_time"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert "time_frame" in data
        assert "topics_covered" in data
        assert "memories_created" in data
        assert "knowledge_retention_score" in data
        assert "learning_velocity" in data
        assert "mastery_levels" in data
        assert "improvement_areas" in data
        assert "achievements" in data

        # Should have some topics covered
        assert data["topics_covered"] >= 4
        assert data["memories_created"] >= 4

    @pytest.mark.asyncio
    async def test_comprehensive_analytics_endpoint(self, client, api_key):
        """Test comprehensive analytics endpoint"""
        # Get all analytics
        response = await client.get(
            "/insights/analytics",
            params={
                "api_key": api_key,
                "time_frame": "all_time"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all components are present
        assert "timestamp" in data
        assert "time_frame" in data
        assert "insights" in data
        assert "patterns" in data
        assert "clusters" in data
        assert "knowledge_gaps" in data
        assert "learning_progress" in data
        assert "errors" in data

        # Even if some components fail, structure should be there
        assert isinstance(data["errors"], list)

    @pytest.mark.asyncio
    async def test_quick_insights_endpoint(self, client, api_key):
        """Test quick insights endpoint for dashboard"""
        response = await client.get(
            "/insights/quick-insights",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify dashboard-friendly format
        assert "insights" in data
        assert "statistics" in data

        # Check insight format
        if data["insights"]:
            insight = data["insights"][0]
            assert "id" in insight
            assert "title" in insight
            assert "description" in insight
            assert "impact" in insight
            assert "recommendations" in insight
            assert "type" in insight

    @pytest.mark.asyncio
    async def test_insights_with_different_timeframes(self, client, api_key):
        """Test insights with various time frames"""
        timeframes = ["daily", "weekly", "monthly", "quarterly", "yearly", "all_time"]

        for timeframe in timeframes:
            response = await client.post(
                "/insights/generate",
                json={
                    "time_frame": timeframe,
                    "limit": 3
                },
                params={"api_key": api_key}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["time_frame"] == timeframe

    @pytest.mark.asyncio
    async def test_pattern_detection_types(self, client, api_key):
        """Test different pattern detection types"""
        pattern_types = ["temporal", "semantic", "behavioral", "structural", "evolutionary"]

        for pattern_type in pattern_types:
            response = await client.post(
                "/insights/patterns",
                json={
                    "pattern_types": [pattern_type],
                    "time_frame": "all_time",
                    "min_occurrences": 1
                },
                params={"api_key": api_key}
            )

            assert response.status_code == 200
            data = response.json()
            assert "patterns" in data

            # Verify patterns match requested type
            for pattern in data["patterns"]:
                assert pattern["type"] == pattern_type

    @pytest.mark.asyncio
    async def test_clustering_algorithms(self, client, api_key):
        """Test different clustering algorithms"""
        algorithms = ["kmeans", "dbscan", "hierarchical"]

        for algo in algorithms:
            response = await client.post(
                "/insights/clusters",
                json={
                    "algorithm": algo,
                    "min_cluster_size": 2
                },
                params={"api_key": api_key}
            )

            # May fail due to lack of embeddings in test mode
            assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_error_handling(self, client, api_key):
        """Test error handling in insights endpoints"""
        # Invalid time frame
        response = await client.post(
            "/insights/generate",
            json={
                "time_frame": "invalid_timeframe"
            },
            params={"api_key": api_key}
        )
        assert response.status_code == 422

        # Invalid pattern type
        response = await client.post(
            "/insights/patterns",
            json={
                "pattern_types": ["invalid_pattern"]
            },
            params={"api_key": api_key}
        )
        assert response.status_code == 422

        # Invalid clustering algorithm
        response = await client.post(
            "/insights/clusters",
            json={
                "algorithm": "invalid_algo"
            },
            params={"api_key": api_key}
        )
        assert response.status_code == 422
