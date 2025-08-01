"""
Example test file demonstrating CI-ready testing best practices.
This file serves as a template for creating robust, reliable tests.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytest


@pytest.mark.unit
class TestBestPracticesBasicPattern:
    """Demonstrates basic test patterns with proper mocking."""

    @pytest.mark.asyncio 
    async def test_async_operation_with_timeout(self, timeout_config):
        """Test async operations with configurable timeouts."""
        timeout = timeout_config["short_timeout"]
        
        # Simulate async operation
        async def mock_operation():
            await asyncio.sleep(0.1)  # Short delay
            return {"status": "success"}
        
        # Test with timeout
        try:
            result = await asyncio.wait_for(mock_operation(), timeout=timeout)
            assert result["status"] == "success"
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout}s")

    @pytest.mark.asyncio
    async def test_retry_logic_with_backoff(self, retry_config):
        """Test retry logic with exponential backoff."""
        max_retries = retry_config["max_retries"]
        backoff_factor = retry_config["backoff_factor"]
        
        attempt_count = 0
        
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Simulated failure")
            return {"attempt": attempt_count, "status": "success"}
        
        # Retry logic
        for attempt in range(max_retries):
            try:
                result = await flaky_operation()
                assert result["status"] == "success"
                assert result["attempt"] == 3
                break
            except ConnectionError:
                if attempt == max_retries - 1:
                    pytest.fail("Max retries exceeded")
                await asyncio.sleep(backoff_factor * (2 ** attempt))

    def test_performance_measurement(self, performance_metrics):
        """Test performance measurement and validation."""
        start_time = performance_metrics["start_time"]
        
        # Simulate some work
        time.sleep(0.1)
        
        elapsed = performance_metrics["get_elapsed"]()
        assert elapsed >= 0.1
        assert elapsed < 1.0  # Should not take too long

    def test_ci_environment_adaptation(self, ci_environment_check):
        """Test adapts behavior based on CI environment."""
        if ci_environment_check["is_ci"]:
            # In CI: use longer timeouts, skip certain tests
            timeout_multiplier = ci_environment_check["timeout_multiplier"]
            assert timeout_multiplier >= 1.0
            
            # Skip resource-intensive tests in CI
            if ci_environment_check["should_skip_integration"]:
                pytest.skip("Integration test skipped in CI")
        else:
            # Local development: full test suite
            assert ci_environment_check["timeout_multiplier"] == 1.0


@pytest.mark.unit
class TestMockingBestPractices:
    """Demonstrates comprehensive mocking patterns."""

    @pytest.mark.asyncio
    async def test_database_operations_fully_mocked(self, mock_database, sample_memory_data):
        """Test database operations with comprehensive mocking."""
        # Setup mock responses
        memory_id = "test-memory-123"
        expected_memory = {**sample_memory_data, "id": memory_id}
        
        mock_database.create_memory.return_value = expected_memory
        mock_database.get_memory.return_value = expected_memory
        mock_database.list_memories.return_value = [expected_memory]
        
        # Test create
        created = await mock_database.create_memory(sample_memory_data)
        assert created["id"] == memory_id
        assert created["title"] == sample_memory_data["title"]
        
        # Test get
        retrieved = await mock_database.get_memory(memory_id)
        assert retrieved["id"] == memory_id
        
        # Test list
        memories = await mock_database.list_memories()
        assert len(memories) == 1
        assert memories[0]["id"] == memory_id
        
        # Verify all mocks were called
        mock_database.create_memory.assert_called_once_with(sample_memory_data)
        mock_database.get_memory.assert_called_once_with(memory_id)
        mock_database.list_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_external_api_integration_mocked(self, mock_openai_client):
        """Test external API integration with proper mocking."""
        # Setup mock embedding response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        
        # Test embedding generation
        response = await mock_openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input="test text for embedding"
        )
        
        assert len(response.data) == 1
        assert len(response.data[0].embedding) == 1536
        assert response.data[0].embedding[0] == 0.1
        
        # Verify API was called with correct parameters
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-ada-002",
            input="test text for embedding"
        )

    @pytest.mark.asyncio
    async def test_redis_caching_pattern_mocked(self, mock_redis):
        """Test Redis caching patterns with proper mocking."""
        cache_key = "test:cache:key"
        cache_value = "cached_data"
        
        # Setup mock responses
        mock_redis.get.return_value = None  # Cache miss initially
        mock_redis.set.return_value = True
        mock_redis.expire.return_value = True
        
        # Test cache miss scenario
        cached_data = await mock_redis.get(cache_key)
        assert cached_data is None
        
        # Test cache set
        set_result = await mock_redis.set(cache_key, cache_value)
        assert set_result is True
        
        # Test cache expiration
        expire_result = await mock_redis.expire(cache_key, 3600)
        assert expire_result is True
        
        # Verify all operations were called
        mock_redis.get.assert_called_once_with(cache_key)
        mock_redis.set.assert_called_once_with(cache_key, cache_value)
        mock_redis.expire.assert_called_once_with(cache_key, 3600)


@pytest.mark.integration
class TestIntegrationPatterns:
    """Demonstrates integration testing patterns that work in CI."""

    @pytest.mark.asyncio
    async def test_service_integration_with_mocks(
        self, 
        mock_database, 
        mock_openai_client, 
        mock_redis,
        sample_memory_data
    ):
        """Test service integration using all mocked dependencies."""
        # Setup integrated workflow
        memory_id = "integration-test-id"
        embedding = [0.1] * 1536
        
        # Mock the full workflow
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=embedding)]
        )
        mock_database.create_memory.return_value = {
            **sample_memory_data,
            "id": memory_id,
            "embedding": embedding
        }
        mock_redis.set.return_value = True
        
        # Simulate integrated workflow
        # 1. Generate embedding
        embedding_response = await mock_openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=sample_memory_data["content"]
        )
        
        # 2. Store in database with embedding
        memory_with_embedding = {
            **sample_memory_data,
            "embedding": embedding_response.data[0].embedding
        }
        created_memory = await mock_database.create_memory(memory_with_embedding)
        
        # 3. Cache the result
        cache_key = f"memory:{created_memory['id']}"
        await mock_redis.set(cache_key, str(created_memory))
        
        # Verify the integration
        assert created_memory["id"] == memory_id
        assert created_memory["embedding"] == embedding
        
        # Verify all services were called
        mock_openai_client.embeddings.create.assert_called_once()
        mock_database.create_memory.assert_called_once()
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_across_services(
        self, 
        mock_database, 
        mock_openai_client,
        sample_memory_data
    ):
        """Test error propagation across integrated services."""
        # Setup failure scenario
        mock_openai_client.embeddings.create.side_effect = Exception("OpenAI API error")
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            await mock_openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=sample_memory_data["content"]
            )
        
        assert "OpenAI API error" in str(exc_info.value)
        
        # Verify database was not called due to early failure
        mock_database.create_memory.assert_not_called()


@pytest.mark.validation
class TestValidationPatterns:
    """Demonstrates validation testing patterns for CI reliability."""

    def test_environment_validation(self):
        """Test environment is properly configured for testing."""
        import os
        
        # Critical environment variables
        required_vars = [
            "ENVIRONMENT",
            "API_TOKENS", 
            "OPENAI_API_KEY",
            "DISABLE_EXTERNAL_SERVICES"
        ]
        
        for var in required_vars:
            assert os.getenv(var) is not None, f"Missing required env var: {var}"
        
        # Test environment specific settings
        assert os.getenv("ENVIRONMENT") == "test"
        assert os.getenv("DISABLE_EXTERNAL_SERVICES") == "true"

    def test_dependency_imports(self):
        """Test all critical dependencies can be imported."""
        try:
            import fastapi
            import pydantic
            import asyncpg
            import redis
            import openai
            import httpx
            assert True  # All imports successful
        except ImportError as e:
            pytest.fail(f"Critical dependency import failed: {e}")

    @pytest.mark.asyncio
    async def test_mock_fixtures_are_working(
        self, 
        mock_database, 
        mock_openai_client, 
        mock_redis
    ):
        """Test all mock fixtures are properly configured."""
        # Test database mock
        assert mock_database is not None
        assert hasattr(mock_database, 'create_memory')
        
        # Test OpenAI mock
        assert mock_openai_client is not None
        assert hasattr(mock_openai_client, 'embeddings')
        
        # Test Redis mock
        assert mock_redis is not None
        assert hasattr(mock_redis, 'get')
        assert hasattr(mock_redis, 'set')

    def test_test_data_fixtures(self, sample_memory_data, sample_user_data):
        """Test sample data fixtures are properly structured."""
        # Validate memory data
        required_memory_fields = ["title", "content", "memory_type"]
        for field in required_memory_fields:
            assert field in sample_memory_data, f"Missing field: {field}"
        
        # Validate user data
        required_user_fields = ["username", "email", "full_name"]
        for field in required_user_fields:
            assert field in sample_user_data, f"Missing field: {field}"
        
        # Validate data types
        assert isinstance(sample_memory_data["title"], str)
        assert isinstance(sample_memory_data["tags"], list)
        assert "@" in sample_user_data["email"]


@pytest.mark.slow
class TestPerformancePatterns:
    """Demonstrates performance testing patterns suitable for CI."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_database):
        """Test concurrent operations with proper mocking."""
        # Setup mock for concurrent operations
        mock_database.create_memory.return_value = {"id": "concurrent-test"}
        
        # Create multiple concurrent operations
        async def create_memory(index):
            await asyncio.sleep(0.01)  # Simulate small delay
            return await mock_database.create_memory({"title": f"Memory {index}"})
        
        # Run concurrent operations
        start_time = time.time()
        tasks = [create_memory(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify results
        assert len(results) == 10
        assert all(r["id"] == "concurrent-test" for r in results)
        
        # Verify performance (should be faster than sequential)
        assert end_time - start_time < 1.0  # Should complete quickly
        assert mock_database.create_memory.call_count == 10

    def test_memory_usage_patterns(self, sample_memory_data):
        """Test memory usage stays within reasonable bounds."""
        import sys
        
        # Get initial memory usage
        initial_size = sys.getsizeof(sample_memory_data)
        
        # Create multiple copies (simulating bulk operations)
        data_copies = [dict(sample_memory_data) for _ in range(100)]
        
        # Verify memory usage is reasonable
        total_size = sum(sys.getsizeof(copy) for copy in data_copies)
        average_size = total_size / len(data_copies)
        
        assert average_size <= initial_size * 2  # Should not grow too much
        assert len(data_copies) == 100

    @pytest.mark.asyncio
    async def test_timeout_handling(self, timeout_config, mock_database):
        """Test proper timeout handling in operations."""
        timeout = timeout_config["short_timeout"]
        
        # Setup slow mock operation
        async def slow_operation():
            await asyncio.sleep(timeout + 1)  # Exceeds timeout
            return {"status": "too_slow"}
        
        mock_database.slow_operation = slow_operation
        
        # Test timeout handling
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_database.slow_operation(), 
                timeout=timeout
            )


if __name__ == "__main__":
    # Example of running specific test categories
    pytest.main([
        __file__,
        "-v",
        "-m", "unit",  # Run only unit tests
        "--tb=short"   # Short traceback format
    ])