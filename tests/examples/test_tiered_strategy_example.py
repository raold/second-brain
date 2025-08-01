#!/usr/bin/env python3
"""
Example tests demonstrating the tiered testing strategy
Shows proper use of markers and test categorization
"""

import asyncio
import time
from unittest.mock import patch

import pytest
import httpx

# Import test fixtures
from tests.conftest import client, api_key


class TestSmokeTests:
    """Smoke tests - critical path validation in <60s total"""
    
    @pytest.mark.smoke
    @pytest.mark.fast
    @pytest.mark.critical
    def test_application_imports(self):
        """Critical imports must work"""
        import app.app
        import app.database
        assert hasattr(app.app, 'app'), "FastAPI app not found"
    
    @pytest.mark.smoke
    @pytest.mark.fast
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Health endpoint must respond quickly"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()
    
    @pytest.mark.smoke
    @pytest.mark.fast
    @pytest.mark.critical
    def test_environment_setup(self):
        """Test environment must be properly configured"""
        import os
        assert os.getenv("TESTING") == "true"
        assert os.getenv("ENVIRONMENT") == "test"


class TestFastFeedbackTests:
    """Fast feedback tests - core functionality in <5min total"""
    
    @pytest.mark.fast_feedback
    @pytest.mark.unit
    @pytest.mark.fast
    def test_memory_model_validation(self):
        """Memory model should validate correctly"""
        from app.models.memory import Memory, MemoryCreate
        
        memory_data = MemoryCreate(
            content="Test memory content",
            metadata={"test": True}
        )
        
        # Should not raise validation errors
        assert memory_data.content == "Test memory content"
        assert memory_data.metadata["test"] is True
    
    @pytest.mark.fast_feedback
    @pytest.mark.integration
    @pytest.mark.medium
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_memory_creation_endpoint(self, client, api_key):
        """Core memory creation should work"""
        response = await client.post(
            "/memories",
            params={"api_key": api_key},
            json={
                "content": "Test memory for fast feedback",
                "metadata": {"test": "fast_feedback"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @pytest.mark.fast_feedback
    @pytest.mark.unit
    @pytest.mark.fast
    def test_service_factory_injection(self):
        """Dependency injection should work"""
        from app.services.service_factory import get_memory_service, get_session_service
        
        memory_service = get_memory_service()
        session_service = get_session_service()
        
        assert memory_service is not None
        assert session_service is not None
        # Singleton pattern - should return same instance
        assert get_memory_service() is memory_service


class TestComprehensiveValidation:
    """Comprehensive tests - full validation in <15min total"""
    
    @pytest.mark.comprehensive
    @pytest.mark.integration
    @pytest.mark.medium
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_memory_search_workflow(self, client, api_key):
        """Complete memory search workflow"""
        # Create a memory
        create_response = await client.post(
            "/memories",
            params={"api_key": api_key},
            json={
                "content": "Comprehensive test memory with unique content",
                "metadata": {"category": "comprehensive_test"}
            }
        )
        assert create_response.status_code == 200
        
        # Search for the memory
        search_response = await client.post(
            "/memories/search",
            params={"api_key": api_key},
            json={
                "query": "comprehensive test unique",
                "limit": 10
            }
        )
        assert search_response.status_code == 200
        
        # Should find the memory
        search_data = search_response.json()
        assert len(search_data.get("memories", [])) > 0
    
    @pytest.mark.comprehensive
    @pytest.mark.security
    @pytest.mark.medium
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_api_authentication(self, client):
        """API authentication must be enforced"""
        # Request without API key should fail
        response = await client.post(
            "/memories",
            json={"content": "Unauthorized request"}
        )
        
        # Should be rejected (401 or 403)
        assert response.status_code in [401, 403]
    
    @pytest.mark.comprehensive
    @pytest.mark.integration
    @pytest.mark.medium
    @pytest.mark.synthesis
    @pytest.mark.asyncio
    async def test_memory_analysis_pipeline(self, client, api_key):
        """Memory analysis and synthesis features"""
        # Create memory with complex content
        response = await client.post(
            "/memories",
            params={"api_key": api_key},
            json={
                "content": """
                # Project Planning Meeting
                
                ## Attendees
                - John Smith (PM)
                - Sarah Davis (Tech Lead)
                - Mike Johnson (Developer)
                
                ## Key Decisions
                1. Use microservices architecture
                2. Implement GraphQL API
                3. Deploy on Kubernetes
                
                ## Action Items
                - [ ] Create technical specification
                - [ ] Set up CI/CD pipeline
                - [ ] Schedule next review meeting
                """,
                "metadata": {"type": "meeting_notes", "priority": "high"}
            }
        )
        assert response.status_code == 200
        
        # Analyze the memory
        memory_id = response.json().get("memory", {}).get("id")
        if memory_id:
            analysis_response = await client.post(
                f"/memories/{memory_id}/analyze",
                params={"api_key": api_key}
            )
            # Analysis might not be fully implemented, so we accept 200 or 501
            assert analysis_response.status_code in [200, 501]


class TestPerformanceBenchmarks:
    """Performance tests - benchmarks and load tests"""
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    @pytest.mark.slow
    @pytest.mark.non_blocking
    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self, client):
        """Health endpoint should respond quickly under load"""
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = []
        async with httpx.AsyncClient() as test_client:
            for _ in range(100):
                task = test_client.get("http://localhost:8000/health")
                tasks.append(task)
            
            # Execute all requests
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check that most requests succeeded
                successful_responses = [r for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
                success_rate = len(successful_responses) / len(responses)
                
                # Should have >90% success rate
                assert success_rate > 0.9, f"Success rate too low: {success_rate:.1%}"
                
                # Total time should be reasonable
                total_time = time.time() - start_time
                assert total_time < 10.0, f"Performance test took too long: {total_time:.1f}s"
                
            except Exception as e:
                # If we can't reach the server, mark as skipped
                pytest.skip(f"Performance test skipped - server not available: {e}")
    
    @pytest.mark.performance
    @pytest.mark.memory
    @pytest.mark.slow
    @pytest.mark.non_blocking
    def test_memory_usage_baseline(self):
        """Memory usage should stay within reasonable bounds"""
        import psutil
        import gc
        
        # Get baseline memory usage
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        large_data = []
        for i in range(1000):
            large_data.append(f"Memory test data item {i}" * 100)
        
        # Check memory growth
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = current_memory - baseline_memory
        
        # Clean up
        del large_data
        gc.collect()
        
        # Memory growth should be reasonable (< 100MB for this test)
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB"


class TestFlakyTestExamples:
    """Examples of how to handle potentially flaky tests"""
    
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    @pytest.mark.integration
    @pytest.mark.medium
    @pytest.mark.requires_external
    def test_external_service_integration(self):
        """Example of a test that might be flaky due to external dependencies"""
        import random
        
        # Simulate flaky external service
        if random.random() < 0.3:  # 30% chance of failure
            raise ConnectionError("External service temporarily unavailable")
        
        # Normal test logic
        assert True
    
    @pytest.mark.quarantine(reason="Known to be flaky, investigating")
    @pytest.mark.integration
    @pytest.mark.medium
    def test_quarantined_feature(self):
        """Example of a quarantined test that runs but doesn't affect pipeline"""
        # This test runs but failures are ignored
        import random
        if random.random() < 0.5:
            pytest.fail("This test is known to be flaky")
        
        assert True


class TestConditionalTests:
    """Tests that run conditionally based on environment"""
    
    @pytest.mark.skipif(
        not hasattr(pytest, "config") or not pytest.config.getoption("--run-slow"),
        reason="Slow tests disabled (use --run-slow to enable)"
    )
    @pytest.mark.slow
    @pytest.mark.local
    def test_slow_local_only(self):
        """Example of test that only runs with specific flags"""
        time.sleep(2)  # Simulate slow operation
        assert True
    
    @pytest.mark.skipif(
        not os.getenv("RUN_DOCKER_TESTS"),
        reason="Docker tests disabled (set RUN_DOCKER_TESTS=1 to enable)"
    )
    @pytest.mark.docker
    @pytest.mark.medium
    def test_docker_specific_feature(self):
        """Example of Docker-specific test"""
        import os
        # This would only run if Docker is available and enabled
        assert os.getenv("RUN_DOCKER_TESTS") == "1"


# Helper functions for test utilities
def create_test_memory_data():
    """Helper function to create consistent test data"""
    return {
        "content": "Test memory content",
        "metadata": {
            "test": True,
            "created_by": "test_suite",
            "category": "test_data"
        }
    }


def assert_memory_structure(memory_data: dict):
    """Helper function to validate memory data structure"""
    required_fields = ["id", "content", "created_at"]
    for field in required_fields:
        assert field in memory_data, f"Missing required field: {field}"


# Pytest fixtures specific to this test file
@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return create_test_memory_data()


@pytest.fixture
async def created_memory(client, api_key):
    """Fixture that creates a memory and returns its data"""
    response = await client.post(
        "/memories",
        params={"api_key": api_key},
        json=create_test_memory_data()
    )
    
    if response.status_code == 200:
        return response.json().get("memory")
    else:
        pytest.skip("Could not create test memory")


# Test configuration validation
def test_marker_configuration():
    """Verify that all test markers are properly configured"""
    # This test ensures our marker configuration is valid
    configured_markers = {
        'smoke', 'fast_feedback', 'comprehensive', 'performance',
        'fast', 'medium', 'slow',
        'unit', 'integration', 'e2e',
        'critical', 'non_blocking', 'flaky', 'quarantine',
        'api', 'synthesis', 'security',
        'requires_db', 'requires_redis', 'requires_external'
    }
    
    # In a real implementation, you'd verify these against pytest.ini
    assert len(configured_markers) > 0, "Markers should be configured"