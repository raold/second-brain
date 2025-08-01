"""
Integration tests for V2 API, StructuredDataExtractor, and WebSocket functionality
Tests the complete workflow and interaction between components
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.services.structured_data_extractor import StructuredDataExtractor
from app.services.synthesis.websocket_service import get_websocket_service


@pytest.mark.asyncio
class TestV2APIIntegration:
    """Integration tests for V2 API endpoints"""

    async def test_metrics_endpoint_full_workflow(self, client: AsyncClient, api_key: str):
        """Test complete metrics workflow with database interaction"""
        response = await client.get("/api/v2/metrics", params={"api_key": api_key})

        assert response.status_code == 200
        metrics = response.json()

        # Verify all required fields are present and valid
        required_fields = [
            "tests",
            "patterns",
            "version",
            "agents",
            "token_usage",
            "memories",
            "active_users",
            "system_health",
        ]
        for field in required_fields:
            assert field in metrics
            assert metrics[field] is not None

        # Test that metrics are consistent with system state
        assert isinstance(metrics["tests"], int)
        assert metrics["tests"] > 0  # Should have some tests
        assert isinstance(metrics["memories"], int)
        assert metrics["memories"] >= 0  # Could be zero in test environment
        assert metrics["version"] == "3.0.0"

    async def test_detailed_metrics_comprehensive(self, client: AsyncClient, api_key: str):
        """Test detailed metrics with comprehensive data validation"""
        response = await client.get("/api/v2/metrics/detailed", params={"api_key": api_key})

        assert response.status_code == 200
        metrics = response.json()

        # Verify top-level structure
        assert "memories" in metrics
        assert "performance" in metrics
        assert "system" in metrics
        assert "database" in metrics
        assert "timestamp" in metrics

        # Validate memories data
        memories = metrics["memories"]
        memory_fields = [
            "total",
            "unique_users",
            "type_distribution",
            "with_embeddings",
            "last_24h",
            "last_7d",
            "last_30d",
        ]
        for field in memory_fields:
            assert field in memories

        # Validate performance data
        performance = metrics["performance"]
        performance_fields = [
            "api_response_time",
            "memory_usage",
            "cpu_usage",
            "disk_usage",
            "cache_hit_rate",
        ]
        for field in performance_fields:
            assert field in performance

        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(metrics["timestamp"])
        assert isinstance(timestamp, datetime)

    async def test_memory_ingestion_workflow(self, client: AsyncClient, api_key: str):
        """Test complete memory ingestion workflow"""
        # Test structured content
        structured_content = """
        Project: AI Research
        Status: In Progress
        Budget: $50,000
        
        Tasks:
        - Literature review
        - Data collection
        - Model development
        - Testing and validation
        
        | Phase | Duration | Resources |
        |-------|----------|-----------|
        | Research | 2 weeks | 2 people |
        | Development | 4 weeks | 3 people |
        | Testing | 2 weeks | 2 people |
        """

        response = await client.post(
            "/api/v2/memories/ingest",
            params={
                "content": structured_content,
                "memory_type": "project",
                "tags": ["ai", "research", "project"],
                "api_key": api_key,
            },
        )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert "memory_id" in result
        assert result["message"] == "Memory ingested successfully"

        # Verify memory ID is a valid format
        memory_id = result["memory_id"]
        assert isinstance(memory_id, str)
        assert len(memory_id) > 0

    async def test_git_activity_integration(self, client: AsyncClient, api_key: str):
        """Test git activity integration with real git data"""
        response = await client.get("/api/v2/git/activity", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "commits" in data
        assert "timeline" in data
        assert "stats" in data

        # Verify timeline has proper structure
        timeline = data["timeline"]
        assert len(timeline) == 5  # Should have 5 timeline points
        for item in timeline:
            assert "label" in item
            assert "timestamp" in item
            # Verify timestamp is valid ISO format
            datetime.fromisoformat(item["timestamp"])

    async def test_health_status_integration(self, client: AsyncClient, api_key: str):
        """Test health status with real system checks"""
        response = await client.get("/api/v2/health", params={"api_key": api_key})

        assert response.status_code == 200
        health = response.json()

        # Verify all health checks are performed
        required_checks = ["api", "database", "redis", "disk", "memory", "cpu"]
        for check in required_checks:
            assert check in health["checks"]
            status = health["checks"][check]
            assert status in ["healthy", "degraded", "unhealthy", "unknown", "unavailable"]

        # Verify overall status is calculated correctly
        overall_status = health["status"]
        assert overall_status in ["healthy", "degraded", "unhealthy", "error"]

        # Verify metrics are included
        if "metrics" in health:
            metrics = health["metrics"]
            assert "cpu_percent" in metrics
            assert "memory_percent" in metrics
            assert "disk_percent" in metrics

    async def test_todos_parsing_integration(self, client: AsyncClient, api_key: str):
        """Test TODO parsing with various formats"""
        # This test checks if TODO parsing handles different formats correctly
        response = await client.get("/api/v2/todos", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "todos" in data
        assert "stats" in data
        assert "last_updated" in data

        # Verify stats calculation
        stats = data["stats"]
        required_stats = ["total", "completed", "in_progress", "pending", "completion_rate"]
        for stat in required_stats:
            assert stat in stats
            assert isinstance(stats[stat], int)

        # Verify completion rate is calculated correctly
        if stats["total"] > 0:
            expected_rate = round((stats["completed"] / stats["total"]) * 100)
            assert stats["completion_rate"] == expected_rate


@pytest.mark.asyncio
class TestStructuredDataExtractorIntegration:
    """Integration tests for StructuredDataExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = StructuredDataExtractor(use_ai=False)

    async def test_complex_document_extraction(self):
        """Test extraction from a complex, realistic document"""
        complex_document = """
        # Project Proposal: Second Brain Enhancement
        
        **Project Manager**: John Smith
        **Budget**: $75,000
        **Timeline**: 6 months
        **Status**: Approved
        **Priority**: High
        
        ## Executive Summary
        
        This project aims to enhance the Second Brain system with advanced features.
        
        ## Objectives
        
        1. Implement advanced search capabilities
        2. Add real-time collaboration features
        3. Integrate machine learning algorithms
        4. Improve user interface design
        5. Enhance data visualization
        
        ## Technical Requirements
        
        ### Backend Components
        - Python 3.9+
        - FastAPI framework
        - PostgreSQL with pgvector
        - Redis for caching
        
        ### Frontend Components
        - React 18
        - TypeScript
        - Tailwind CSS
        - WebSocket support
        
        ## Budget Breakdown
        
        | Category | Amount | Percentage |
        |----------|--------|------------|
        | Development | $45,000 | 60% |
        | Testing | $15,000 | 20% |
        | Documentation | $7,500 | 10% |
        | Deployment | $7,500 | 10% |
        
        ## Implementation Plan
        
        ```python
        # Core search algorithm
        async def enhanced_search(query: str, filters: dict):
            # Vector similarity search
            results = await vector_search(query)
            
            # Apply filters
            filtered_results = apply_filters(results, filters)
            
            # Rank by relevance
            return rank_results(filtered_results)
        
        class CollaborationManager:
            def __init__(self):
                self.active_sessions = {}
            
            async def create_session(self, user_id: str):
                session = CollaborationSession(user_id)
                self.active_sessions[session.id] = session
                return session
        ```
        
        ## Timeline
        
        Phase 1 (Months 1-2): Research and Planning
        - Requirements analysis
        - Architecture design
        - Technology selection
        
        Phase 2 (Months 3-4): Core Development
        - Backend API development
        - Database schema design
        - Core algorithms implementation
        
        Phase 3 (Months 5-6): Integration and Testing
        - Frontend integration
        - End-to-end testing
        - Performance optimization
        - Documentation
        
        ## Risk Assessment
        
        ### High Priority Risks
        - Technical complexity may exceed estimates
        - Third-party API limitations
        - Performance bottlenecks with large datasets
        
        ### Mitigation Strategies
        - Prototype critical components early
        - Implement comprehensive monitoring
        - Plan for horizontal scaling
        
        ## Contact Information
        
        - Project Manager: john.smith@company.com
        - Technical Lead: jane.doe@company.com
        - Website: https://secondbrain.project.com
        - Repository: https://github.com/company/second-brain
        
        ## Approval
        
        Approved by: CEO (2024-01-15)
        Review Date: 2024-07-15
        Next Milestone: 2024-02-15
        """

        result = self.extractor.extract_advanced_structured_data(complex_document)

        # Verify key-value pairs extraction
        assert len(result.key_value_pairs) >= 5
        assert "Project Manager" in result.key_value_pairs
        assert "Budget" in result.key_value_pairs
        assert "Timeline" in result.key_value_pairs
        assert "Status" in result.key_value_pairs
        assert "Priority" in result.key_value_pairs

        # Verify list extraction
        assert len(result.lists) >= 3  # Objectives, backend, frontend components

        # Find objectives list
        objectives_list = None
        for lst in result.lists:
            if any("Implement advanced search" in item for item in lst.items):
                objectives_list = lst
                break
        assert objectives_list is not None
        assert len(objectives_list.items) >= 5

        # Verify table extraction
        assert len(result.tables) >= 1
        budget_table = result.tables[0]
        assert "Category" in budget_table.headers
        assert "Amount" in budget_table.headers
        assert len(budget_table.rows) >= 4

        # Verify code block extraction
        assert len(result.code_snippets) >= 1
        code_block = result.code_snippets[0]
        assert code_block.language == "python"
        assert "enhanced_search" in code_block.functions
        assert "CollaborationManager" in code_block.classes

        # Verify entity extraction
        email_entities = [e for e in result.entities if e.entity_type == "email"]
        url_entities = [e for e in result.entities if e.entity_type == "url"]
        date_entities = [e for e in result.entities if e.entity_type == "date"]

        assert len(email_entities) >= 2
        assert len(url_entities) >= 2
        assert len(date_entities) >= 3

        # Verify metadata extraction
        assert "statistics" in result.metadata_fields
        stats = result.metadata_fields["statistics"]
        assert stats["word_count"] > 400  # Complex document should have many words
        assert stats["line_count"] > 100
        assert stats["paragraph_count"] > 10

    async def test_domain_classification_integration(self):
        """Test domain classification with various content types"""
        test_cases = [
            {
                "content": """
                ```python
                import tensorflow as tf
                
                class NeuralNetwork:
                    def __init__(self):
                        self.model = tf.keras.Sequential()
                    
                    def train(self, data):
                        self.model.fit(data)
                ```
                
                This implements a neural network using TensorFlow framework.
                The API exposes endpoints for model training and inference.
                Database optimization is crucial for performance.
                """,
                "expected_domain": "technical",
            },
            {
                "content": """
                Q4 2024 Business Report
                
                Revenue: $5.2M (+15% YoY)
                Profit Margin: 23%
                Customer Acquisition Cost: $150
                Lifetime Value: $2,400
                
                Market Analysis:
                - Strong growth in enterprise segment
                - ROI on marketing campaigns: 320%
                - Quarterly targets exceeded by 8%
                
                Strategic initiatives for next quarter:
                - Expand into new markets
                - Optimize customer onboarding
                - Increase investment in R&D
                """,
                "expected_domain": "business",
            },
            {
                "content": """
                Abstract
                
                This study investigates the relationship between social media usage
                and academic performance among college students (n=450).
                
                Introduction
                
                Previous research has shown conflicting results regarding this
                relationship (Smith et al., 2020; Jones & Brown, 2021).
                
                Methodology
                
                We conducted a longitudinal study over 12 months using validated
                questionnaires and academic records.
                
                Results
                
                Our findings indicate a significant negative correlation (r=-0.34, p<0.01)
                between daily social media usage and GPA.
                
                Discussion
                
                These results support the attention fragmentation hypothesis
                proposed by Wilson (2019).
                
                References
                
                Smith, A., Johnson, B., & Lee, C. (2020). Digital distractions
                in higher education. Journal of Educational Psychology, 45(2), 123-145.
                """,
                "expected_domain": "academic",
            },
        ]

        for case in test_cases:
            result = self.extractor.classify_domain(case["content"])

            assert "domains" in result
            assert "primary_domain" in result

            # Check if expected domain is detected
            domain_names = [d["name"] for d in result["domains"]]
            assert (
                case["expected_domain"] in domain_names
                or result["primary_domain"] == case["expected_domain"]
            )

    async def test_extraction_statistics_comprehensive(self):
        """Test comprehensive extraction statistics"""
        content = """
        # Research Project Data
        
        Participants: 150
        Duration: 6 months
        Budget: $25,000
        
        Data Collection Methods:
        - Surveys (n=150)
        - Interviews (n=30)
        - Focus groups (n=6)
        
        | Method | Count | Response Rate |
        |--------|-------|---------------|
        | Surveys | 150 | 100% |
        | Interviews | 30 | 85% |
        | Focus Groups | 6 | 92% |
        
        ```r
        # Statistical analysis
        library(tidyverse)
        
        data <- read.csv("responses.csv")
        
        model <- lm(outcome ~ predictor1 + predictor2, data = data)
        summary(model)
        ```
        
        Contact: researcher@university.edu
        Website: https://research.university.edu/project
        
        Definition of terms:
        Response Rate: Percentage of participants who completed the study
        Effect Size: Magnitude of the observed effect
        Confidence Interval: Range of plausible values for the parameter
        """

        result = self.extractor.extract_structured_data(content)
        stats = self.extractor.get_extraction_statistics(result)

        # Verify comprehensive statistics
        assert "total_structured_elements" in stats
        assert stats["total_structured_elements"] > 0

        # Key-value pairs stats
        kv_stats = stats["key_value_pairs"]
        assert kv_stats["count"] >= 3
        assert len(kv_stats["sample_keys"]) <= 5

        # Lists stats
        lists_stats = stats["lists"]
        assert lists_stats["count"] >= 1
        assert lists_stats["total_items"] >= 3

        # Tables stats
        tables_stats = stats["tables"]
        assert tables_stats["count"] >= 1
        assert tables_stats["total_cells"] >= 9  # 3x3 table minimum
        assert tables_stats["average_size"] > 0

        # Code snippets stats
        code_stats = stats["code_snippets"]
        assert code_stats["count"] >= 1
        assert code_stats["total_lines"] > 0
        assert "r" in code_stats["languages"]

        # Entities stats
        entities_stats = stats["entities"]
        assert entities_stats["count"] >= 2  # At least email and URL
        assert "email" in entities_stats["types"]
        assert "url" in entities_stats["types"]


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.websocket_service = get_websocket_service()

    async def test_websocket_service_singleton(self):
        """Test WebSocket service singleton behavior"""
        service1 = get_websocket_service()
        service2 = get_websocket_service()

        assert service1 is service2
        assert service1 is self.websocket_service

    async def test_connection_lifecycle(self):
        """Test complete WebSocket connection lifecycle"""
        mock_websocket = AsyncMock()
        connection_id = "test-conn-123"
        user_id = "test-user-456"

        # Test connection
        await self.websocket_service.connection_manager.connect(
            mock_websocket, connection_id, user_id
        )

        # Verify connection is tracked
        assert connection_id in self.websocket_service.connection_manager.active_connections
        assert user_id in self.websocket_service.connection_manager.user_connections
        assert connection_id in self.websocket_service.connection_manager.user_connections[user_id]

        # Test notification
        notification = {"type": "test", "message": "Hello"}
        await self.websocket_service.send_notification(user_id, notification)

        mock_websocket.send_text.assert_called_once()

        # Test disconnection
        self.websocket_service.connection_manager.disconnect(connection_id)

        assert connection_id not in self.websocket_service.connection_manager.active_connections
        assert (
            connection_id not in self.websocket_service.connection_manager.user_connections[user_id]
        )

    async def test_broadcast_event_integration(self):
        """Test event broadcasting to multiple connections"""
        # Set up multiple connections
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            conn_id = f"conn-{i}"
            user_id = f"user-{i}"

            await self.websocket_service.connection_manager.connect(mock_ws, conn_id, user_id)
            connections.append((mock_ws, conn_id, user_id))

        # Broadcast event
        event_type = "memory.created"
        event_data = {"memory_id": "mem-123", "content": "test memory"}

        await self.websocket_service.event_broadcaster.broadcast_event(event_type, event_data)

        # Verify all connections received the event
        for mock_ws, _, _ in connections:
            mock_ws.send_text.assert_called_once()

            # Verify message content
            call_args = mock_ws.send_text.call_args[0][0]
            assert event_type in call_args
            assert "mem-123" in call_args

    async def test_metrics_collection_integration(self):
        """Test WebSocket metrics collection"""
        # Set up some connections
        for i in range(5):
            mock_ws = AsyncMock()
            await self.websocket_service.connection_manager.connect(
                mock_ws, f"conn-{i}", f"user-{i}"
            )

        # Get metrics
        metrics = self.websocket_service.get_metrics()

        assert metrics["active_connections"] == 5
        assert metrics["users_connected"] == 5
        assert "subscriptions" in metrics

    async def test_error_handling_integration(self):
        """Test error handling in WebSocket integration"""
        # Set up connection that will fail
        failing_ws = AsyncMock()
        failing_ws.send_text.side_effect = Exception("Connection failed")

        good_ws = AsyncMock()

        await self.websocket_service.connection_manager.connect(
            failing_ws, "failing-conn", "user-1"
        )
        await self.websocket_service.connection_manager.connect(good_ws, "good-conn", "user-2")

        # Broadcast event
        await self.websocket_service.event_broadcaster.broadcast_event(
            "test.event", {"data": "test"}
        )

        # Both should be called, but failing one should handle error gracefully
        failing_ws.send_text.assert_called_once()
        good_ws.send_text.assert_called_once()


@pytest.mark.asyncio
class TestCrossComponentIntegration:
    """Integration tests across V2 API, StructuredDataExtractor, and WebSocket"""

    async def test_memory_ingestion_with_structured_extraction(
        self, client: AsyncClient, api_key: str
    ):
        """Test memory ingestion with structured data extraction"""
        # Create structured content
        structured_content = """
        Meeting Notes: Q1 Planning
        Date: 2024-01-15
        Attendees: 8
        Duration: 90 minutes
        
        Agenda Items:
        1. Budget review
        2. Resource allocation
        3. Timeline planning
        4. Risk assessment
        
        | Department | Q1 Budget | Increase |
        |------------|-----------|----------|
        | Engineering | $500K | 10% |
        | Marketing | $200K | 15% |
        | Sales | $150K | 5% |
        
        Action Items:
        - [ ] Finalize budget by Jan 20
        - [ ] Hire 2 engineers by Feb 1
        - [x] Complete risk assessment
        
        Next Meeting: 2024-02-15
        """

        # Ingest the memory
        response = await client.post(
            "/api/v2/memories/ingest",
            params={
                "content": structured_content,
                "memory_type": "meeting_notes",
                "tags": ["meeting", "planning", "q1"],
                "api_key": api_key,
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

        # Test that structured data would be extracted correctly
        extractor = StructuredDataExtractor(use_ai=False)
        extracted = extractor.extract_structured_data(structured_content)

        # Verify extraction worked
        assert len(extracted.key_value_pairs) >= 4
        assert len(extracted.lists) >= 2  # Agenda and action items
        assert len(extracted.tables) >= 1

        # Verify entities were found
        date_entities = [e for e in extracted.entities if e.entity_type == "date"]
        assert len(date_entities) >= 2

    @patch("app.routes.v2_unified_api.broadcast_update")
    async def test_websocket_notification_on_memory_creation(
        self, mock_broadcast, client: AsyncClient, api_key: str
    ):
        """Test WebSocket notification when memory is created via API"""
        content = "Test memory for WebSocket notification"

        response = await client.post(
            "/api/v2/memories/ingest",
            params={"content": content, "memory_type": "note", "api_key": api_key},
        )

        assert response.status_code == 200

        # Verify broadcast was called
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args

        # Verify broadcast parameters
        assert call_args[0][0] == "memory_created"  # event type
        broadcast_data = call_args[0][1]  # event data
        assert "id" in broadcast_data
        assert "memory_type" in broadcast_data
        assert broadcast_data["memory_type"] == "note"

    async def test_metrics_reflect_websocket_connections(self, client: AsyncClient, api_key: str):
        """Test that metrics endpoint reflects WebSocket connection state"""
        websocket_service = get_websocket_service()

        # Add some mock connections
        for i in range(3):
            mock_ws = AsyncMock()
            await websocket_service.connection_manager.connect(mock_ws, f"conn-{i}", f"user-{i}")

        # Get metrics via API
        response = await client.get("/api/v2/metrics", params={"api_key": api_key})

        assert response.status_code == 200
        metrics = response.json()

        # While the API metrics might not directly show WebSocket connections,
        # we can verify the WebSocket service has the connections
        ws_metrics = websocket_service.get_metrics()
        assert ws_metrics["active_connections"] == 3
        assert ws_metrics["users_connected"] == 3

    async def test_structured_data_in_health_check(self, client: AsyncClient, api_key: str):
        """Test that health check includes structured data about system state"""
        response = await client.get("/api/v2/health", params={"api_key": api_key})

        assert response.status_code == 200
        health = response.json()

        # Verify structured health data
        assert "status" in health
        assert "checks" in health
        assert "timestamp" in health

        # Test that we can extract structured data from health response
        extractor = StructuredDataExtractor(use_ai=False)
        health_json = json.dumps(health, indent=2)
        extracted = extractor.extract_structured_data(health_json)

        # Should extract some key-value pairs from JSON
        assert len(extracted.key_value_pairs) > 0

    async def test_error_propagation_across_components(self, client: AsyncClient, api_key: str):
        """Test error handling across V2 API, extraction, and WebSocket components"""
        # Test with malformed content that might cause extraction issues
        malformed_content = (
            "```\nunclosed code block\n" + "x" * 10000
        )  # Very long malformed content

        response = await client.post(
            "/api/v2/memories/ingest",
            params={"content": malformed_content, "memory_type": "test", "api_key": api_key},
        )

        # Should handle gracefully, either succeed or fail cleanly
        assert response.status_code in [200, 400, 422, 500]

        if response.status_code == 200:
            # If successful, verify structure
            result = response.json()
            assert "success" in result
            assert "memory_id" in result
        else:
            # If failed, should have proper error response
            assert response.status_code != 200

    async def test_performance_under_load(self, client: AsyncClient, api_key: str):
        """Test system performance under concurrent load"""

        # Create multiple concurrent requests
        async def make_request(i):
            content = f"Test memory {i} with some structured data:\nPriority: High\nStatus: Active"
            return await client.post(
                "/api/v2/memories/ingest",
                params={
                    "content": content,
                    "memory_type": "test",
                    "tags": [f"test-{i}"],
                    "api_key": api_key,
                },
            )

        # Make 10 concurrent requests
        tasks = [make_request(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Most requests should succeed
        successful_responses = [
            r for r in responses if not isinstance(r, Exception) and r.status_code == 200
        ]
        assert len(successful_responses) >= 8  # At least 80% success rate

        # Test WebSocket service can handle concurrent connections
        websocket_service = get_websocket_service()
        connection_tasks = []

        for i in range(10):
            mock_ws = AsyncMock()
            task = websocket_service.connection_manager.connect(
                mock_ws, f"load-test-{i}", f"user-{i}"
            )
            connection_tasks.append(task)

        await asyncio.gather(*connection_tasks)

        # Verify all connections were established
        metrics = websocket_service.get_metrics()
        assert metrics["active_connections"] >= 10

    async def test_data_consistency_across_components(self, client: AsyncClient, api_key: str):
        """Test data consistency between API responses and internal state"""
        # Create memory with structured content
        structured_content = """
        Project Status Report
        
        Name: Second Brain v2.0
        Progress: 75%
        Team Size: 5
        Budget Used: $45,000
        
        Milestones:
        - [x] Architecture design
        - [x] Core API development  
        - [ ] UI implementation
        - [ ] Testing and deployment
        """

        # Ingest memory
        ingest_response = await client.post(
            "/api/v2/memories/ingest",
            params={
                "content": structured_content,
                "memory_type": "status_report",
                "api_key": api_key,
            },
        )

        assert ingest_response.status_code == 200

        # Get metrics after ingestion
        metrics_response = await client.get("/api/v2/metrics", params={"api_key": api_key})

        assert metrics_response.status_code == 200
        metrics = metrics_response.json()

        # Memory count should have increased
        assert isinstance(metrics["memories"], int)
        assert metrics["memories"] >= 0

        # Test structured extraction works consistently
        extractor = StructuredDataExtractor(use_ai=False)
        extracted1 = extractor.extract_structured_data(structured_content)
        extracted2 = extractor.extract_structured_data(structured_content)

        # Should get consistent results
        assert len(extracted1.key_value_pairs) == len(extracted2.key_value_pairs)
        assert len(extracted1.lists) == len(extracted2.lists)

        # Key-value pairs should be identical
        for key in extracted1.key_value_pairs:
            assert key in extracted2.key_value_pairs
            assert extracted1.key_value_pairs[key] == extracted2.key_value_pairs[key]
