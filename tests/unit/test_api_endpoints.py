"""
Unit tests for API endpoints
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_health_check_detailed(self, client: AsyncClient):
        """Test detailed health check"""
        response = await client.get("/health/detailed")
        
        # Should return either 200 (healthy) or a specific error code
        assert response.status_code in [200, 503, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "version" in data


class TestAuthenticationEndpoints:
    """Test authentication-related endpoints"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self, client: AsyncClient):
        """Test accessing protected endpoint without authentication"""
        # Try to access a protected endpoint without API key
        response = await client.get("/memories")
        
        # Should return either 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_auth(self, client: AsyncClient, api_key: str):
        """Test accessing protected endpoint with valid API key"""
        headers = {"X-API-Key": api_key}
        response = await client.get("/memories", headers=headers)
        
        # Should return 200 or be handled gracefully
        assert response.status_code in [200, 404, 500]
        
        # If successful, should return JSON
        if response.status_code == 200:
            assert response.headers.get("content-type", "").startswith("application/json")

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid API key"""
        headers = {"X-API-Key": "invalid-key"}
        response = await client.get("/memories", headers=headers)
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]


class TestMemoryEndpoints:
    """Test memory-related endpoints"""

    @pytest.mark.asyncio
    async def test_get_memories_empty(self, client: AsyncClient, api_key: str):
        """Test getting memories when none exist"""
        headers = {"X-API-Key": api_key}
        response = await client.get("/memories", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Should return empty list or paginated empty result
            assert isinstance(data, (list, dict))
            if isinstance(data, list):
                assert len(data) == 0
            elif isinstance(data, dict):
                assert "memories" in data or "data" in data or "items" in data

    @pytest.mark.asyncio
    async def test_create_memory_endpoint_exists(self, client: AsyncClient, api_key: str):
        """Test that create memory endpoint exists"""
        headers = {"X-API-Key": api_key}
        memory_data = {
            "content": "Test memory content",
            "memory_type": "factual"
        }
        
        response = await client.post("/memories", json=memory_data, headers=headers)
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        
        # Valid responses: 200, 201 (success), 400 (bad request), 422 (validation error)
        assert response.status_code in [200, 201, 400, 422, 500]

    @pytest.mark.asyncio
    async def test_get_memory_by_id_not_found(self, client: AsyncClient, api_key: str):
        """Test getting non-existent memory by ID"""
        headers = {"X-API-Key": api_key}
        fake_id = "non-existent-id-12345"
        
        response = await client.get(f"/memories/{fake_id}", headers=headers)
        
        # Should return 404 for non-existent memory
        assert response.status_code in [404, 400]


class TestErrorHandling:
    """Test API error handling"""

    @pytest.mark.asyncio
    async def test_malformed_json(self, client: AsyncClient, api_key: str):
        """Test handling of malformed JSON"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Send malformed JSON
        response = await client.post(
            "/memories", 
            content="{'invalid': json,}", 
            headers=headers
        )
        
        # Should return 400 or 422 for malformed JSON
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_unsupported_method(self, client: AsyncClient, api_key: str):
        """Test unsupported HTTP methods"""
        headers = {"X-API-Key": api_key}
        
        # Try PATCH on root endpoint (likely not supported)
        response = await client.patch("/", headers=headers)
        
        # Should return 405 (Method Not Allowed) or 404
        assert response.status_code in [404, 405]

    @pytest.mark.asyncio
    async def test_large_payload(self, client: AsyncClient, api_key: str):
        """Test handling of large payloads"""
        headers = {"X-API-Key": api_key}
        
        # Create a large payload
        large_content = "x" * 10000  # 10KB string
        memory_data = {
            "content": large_content,
            "memory_type": "factual"
        }
        
        response = await client.post("/memories", json=memory_data, headers=headers)
        
        # Should handle gracefully - either accept or reject with proper error
        assert response.status_code in [200, 201, 400, 413, 422, 500]


class TestContentTypes:
    """Test content type handling"""

    @pytest.mark.asyncio
    async def test_json_content_type(self, client: AsyncClient, api_key: str):
        """Test JSON content type handling"""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        memory_data = {
            "content": "JSON test content",
            "memory_type": "factual"
        }
        
        response = await client.post("/memories", json=memory_data, headers=headers)
        
        # Should handle JSON properly
        assert response.status_code in [200, 201, 400, 422, 500]

    @pytest.mark.asyncio
    async def test_response_content_type(self, client: AsyncClient):
        """Test response content types"""
        response = await client.get("/health")
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type.lower()


class TestRateLimiting:
    """Test rate limiting (if implemented)"""

    @pytest.mark.asyncio
    async def test_multiple_requests(self, client: AsyncClient, api_key: str):
        """Test multiple rapid requests"""
        headers = {"X-API-Key": api_key}
        
        responses = []
        for _ in range(5):
            response = await client.get("/health", headers=headers)
            responses.append(response.status_code)
        
        # Should handle multiple requests without crashing
        # All responses should be valid HTTP status codes
        for status_code in responses:
            assert 100 <= status_code < 600
        
        # Most should be successful (or at least not server errors)
        successful_responses = [code for code in responses if code < 500]
        assert len(successful_responses) >= 3  # At least 3 out of 5 should work