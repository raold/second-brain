"""
Test utilities and helpers for consistent testing patterns.
Provides reusable components for robust CI testing.
"""

import asyncio
import time
import json
from typing import Any, Dict, List, Optional, Callable, Awaitable
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
import pytest


class MockResponseBuilder:
    """Builder pattern for creating consistent mock responses."""
    
    def __init__(self):
        self.response_data = {}
    
    def with_id(self, id_value: str) -> 'MockResponseBuilder':
        """Add ID to response."""
        self.response_data["id"] = id_value
        return self
    
    def with_status(self, status: str) -> 'MockResponseBuilder':
        """Add status to response."""
        self.response_data["status"] = status
        return self
    
    def with_data(self, **kwargs) -> 'MockResponseBuilder':
        """Add arbitrary data to response."""
        self.response_data.update(kwargs)
        return self
    
    def with_timestamp(self) -> 'MockResponseBuilder':
        """Add current timestamp."""
        from datetime import datetime
        self.response_data["created_at"] = datetime.utcnow().isoformat()
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the response dictionary."""
        return self.response_data.copy()
    
    def build_mock(self) -> MagicMock:
        """Build as a MagicMock object."""
        mock = MagicMock()
        for key, value in self.response_data.items():
            setattr(mock, key, value)
        return mock


class AsyncTestHelper:
    """Helper for async test operations."""
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)
        return False
    
    @staticmethod
    async def simulate_delay(delay: float = 0.1) -> None:
        """Simulate async operation delay."""
        await asyncio.sleep(delay)
    
    @staticmethod
    @asynccontextmanager
    async def timeout_context(timeout: float):
        """Context manager for timeout operations."""
        try:
            async with asyncio.timeout(timeout):
                yield
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout}s")


class RetryTestHelper:
    """Helper for testing retry logic."""
    
    @staticmethod
    async def flaky_operation(
        success_after_attempts: int = 3,
        error_message: str = "Simulated failure"
    ) -> Callable[[], Awaitable[Dict[str, Any]]]:
        """Create a flaky operation that succeeds after N attempts."""
        attempt_count = 0
        
        async def operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < success_after_attempts:
                raise ConnectionError(error_message)
            return {"attempt": attempt_count, "status": "success"}
        
        return operation
    
    @staticmethod
    async def retry_with_backoff(
        operation: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        exceptions: tuple = (ConnectionError, TimeoutError)
    ) -> Any:
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except exceptions as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(backoff_factor * (2 ** attempt))


class DatabaseTestHelper:
    """Helper for database testing patterns."""
    
    @staticmethod
    def create_mock_database() -> AsyncMock:
        """Create a fully configured database mock."""
        mock_db = AsyncMock()
        
        # Setup common methods
        mock_db.initialize = AsyncMock()
        mock_db.close = AsyncMock()
        mock_db.create_memory = AsyncMock()
        mock_db.get_memory = AsyncMock()
        mock_db.update_memory = AsyncMock()
        mock_db.delete_memory = AsyncMock()
        mock_db.list_memories = AsyncMock(return_value=[])
        mock_db.search_memories = AsyncMock(return_value=[])
        
        # Setup connection pool
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_connection
        mock_db.pool = mock_pool
        
        return mock_db
    
    @staticmethod
    def create_sample_memory(
        memory_id: str = "test-memory-id",
        title: str = "Test Memory",
        content: str = "Test content"
    ) -> Dict[str, Any]:
        """Create sample memory data."""
        return {
            "id": memory_id,
            "title": title,
            "content": content,
            "memory_type": "note",
            "tags": ["test"],
            "importance_score": 0.5,
            "created_at": time.time(),
            "metadata": {"source": "test"}
        }


class APITestHelper:
    """Helper for API testing patterns."""
    
    @staticmethod
    def create_test_headers(api_key: Optional[str] = None) -> Dict[str, str]:
        """Create standard test headers."""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers
    
    @staticmethod
    def assert_api_response(
        response: Dict[str, Any],
        expected_status: str = "success",
        required_fields: Optional[List[str]] = None
    ) -> None:
        """Assert API response structure."""
        assert "status" in response
        assert response["status"] == expected_status
        
        if required_fields:
            for field in required_fields:
                assert field in response, f"Missing required field: {field}"
    
    @staticmethod
    def create_mock_http_response(
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """Create mock HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {"status": "mocked"}
        return mock_response


class PerformanceTestHelper:
    """Helper for performance testing."""
    
    @staticmethod
    @asynccontextmanager
    async def measure_time():
        """Context manager to measure execution time."""
        start_time = time.time()
        yield lambda: time.time() - start_time
    
    @staticmethod
    def assert_performance(
        elapsed_time: float,
        max_time: float,
        operation_name: str = "Operation"
    ) -> None:
        """Assert operation completed within time limit."""
        assert elapsed_time <= max_time, \
            f"{operation_name} took {elapsed_time:.3f}s (max: {max_time}s)"
    
    @staticmethod
    async def concurrent_operations(
        operation: Callable[[], Awaitable[Any]],
        count: int = 10
    ) -> List[Any]:
        """Run multiple operations concurrently."""
        tasks = [operation() for _ in range(count)]
        return await asyncio.gather(*tasks)


class ValidationTestHelper:
    """Helper for validation testing."""
    
    @staticmethod
    def validate_environment_vars(required_vars: List[str]) -> None:
        """Validate required environment variables exist."""
        import os
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.fail(f"Missing environment variables: {missing_vars}")
    
    @staticmethod
    def validate_imports(modules: List[str]) -> None:
        """Validate required modules can be imported."""
        failed_imports = []
        for module in modules:
            try:
                __import__(module)
            except ImportError:
                failed_imports.append(module)
        
        if failed_imports:
            pytest.fail(f"Failed to import modules: {failed_imports}")
    
    @staticmethod
    def validate_test_data(
        data: Dict[str, Any],
        required_fields: List[str],
        data_name: str = "test data"
    ) -> None:
        """Validate test data structure."""
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            pytest.fail(f"Missing fields in {data_name}: {missing_fields}")


class CITestHelper:
    """Helper for CI-specific testing patterns."""
    
    @staticmethod
    def is_ci_environment() -> bool:
        """Check if running in CI environment."""
        import os
        return os.getenv('CI', '').lower() in ('true', '1', 'yes')
    
    @staticmethod
    def get_timeout_multiplier() -> float:
        """Get timeout multiplier for CI environment."""
        return 2.0 if CITestHelper.is_ci_environment() else 1.0
    
    @staticmethod
    def skip_if_ci(reason: str = "Skipped in CI environment"):
        """Decorator to skip tests in CI."""
        return pytest.mark.skipif(
            CITestHelper.is_ci_environment(),
            reason=reason
        )
    
    @staticmethod
    def slow_test_timeout() -> float:
        """Get appropriate timeout for slow tests."""
        base_timeout = 30.0
        return base_timeout * CITestHelper.get_timeout_multiplier()


class MockServiceFactory:
    """Factory for creating consistently configured mock services."""
    
    @staticmethod
    def create_openai_mock() -> AsyncMock:
        """Create OpenAI client mock."""
        mock_client = AsyncMock()
        
        # Mock embeddings
        mock_embeddings = AsyncMock()
        mock_embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        ))
        mock_client.embeddings = mock_embeddings
        
        # Mock chat completions
        mock_chat = AsyncMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(
            message=MagicMock(content="Test response")
        )]
        mock_chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_client.chat = mock_chat
        
        return mock_client
    
    @staticmethod
    def create_redis_mock() -> AsyncMock:
        """Create Redis client mock."""
        mock_redis = AsyncMock()
        
        # Setup common operations
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=False)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()
        
        return mock_redis
    
    @staticmethod
    def create_http_client_mock() -> MagicMock:
        """Create HTTP client mock."""
        mock_client = MagicMock()
        mock_response = APITestHelper.create_mock_http_response()
        
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client.put.return_value = mock_response
        mock_client.delete.return_value = mock_response
        
        return mock_client


# Convenience functions for common patterns
async def assert_async_operation_succeeds(
    operation: Callable[[], Awaitable[Any]],
    timeout: float = 5.0
) -> Any:
    """Assert async operation succeeds within timeout."""
    try:
        return await asyncio.wait_for(operation(), timeout=timeout)
    except asyncio.TimeoutError:
        pytest.fail(f"Operation timed out after {timeout}s")


def create_test_scenario(
    name: str,
    setup_data: Dict[str, Any],
    expected_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a test scenario dictionary."""
    return {
        "name": name,
        "setup": setup_data,
        "expected": expected_result,
        "timestamp": time.time()
    }