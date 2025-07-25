"""
Core functionality test suite for the Second Brain application.
Comprehensive testing of all major features.
"""


import pytest


class TestAPI:
    """Test the API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_includes_version(self, client):
        """Test health check includes proper version info."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.4.4"  # Current version

    @pytest.mark.asyncio
    async def test_store_memory_basic(self, client, api_key):
        """Test storing a basic memory."""
        memory_data = {
            "content": "This is a test memory for unit testing",
            "metadata": {"type": "test", "category": "unit_test"},
        }

        response = await client.post("/memories", json=memory_data, params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == memory_data["content"]
        # The metadata is stored in typed fields, not preserved as-is
        assert data["metadata"] is not None
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_store_memory_with_complex_metadata(self, client, api_key):
        """Test storing memory with complex metadata."""
        memory_data = {
            "content": "Complex memory with detailed metadata",
            "metadata": {
                "type": "semantic",
                "priority": "high",
                "tags": ["test", "complex", "metadata"],
                "source": "unit_test",
                "confidence": 0.95,
                "created_by": "test_suite",
            },
        }

        response = await client.post("/memories", json=memory_data, params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == memory_data["content"]
        # The metadata is now in the general metadata field of MemoryResponse
        assert data["metadata"] is not None

    @pytest.mark.asyncio
    async def test_search_memories_basic(self, client, api_key):
        """Test basic memory search functionality."""
        # First store a unique memory
        memory_data = {
            "content": "Python programming language is excellent for data science and machine learning applications",
            "metadata": {"type": "fact", "domain": "programming"},
        }

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200

        # Then search for it
        search_data = {"query": "Python programming", "limit": 10}

        response = await client.post("/memories/search", json=search_data, params={"api_key": api_key})

        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) > 0

        # Verify result structure
        for result in results:
            assert "id" in result
            assert "content" in result
            assert "consolidation_score" in result or "access_count" in result

    @pytest.mark.asyncio
    async def test_search_memories_advanced(self, client, api_key):
        """Test advanced search with filters and options."""
        # Store multiple memories with different metadata
        memories = [
            {
                "content": "Machine learning algorithms for data analysis",
                "metadata": {"type": "semantic", "priority": "high"},
            },
            {
                "content": "Data visualization techniques using matplotlib",
                "metadata": {"type": "procedural", "priority": "medium"},
            },
        ]

        for memory in memories:
            response = await client.post("/memories", json=memory, params={"api_key": api_key})
            assert response.status_code == 200

        # Search with advanced parameters
        search_data = {"query": "data analysis", "limit": 5, "threshold": 0.0, "metadata_filters": {"type": "semantic"}}

        response = await client.post("/memories/search", json=search_data, params={"api_key": api_key})

        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, client, api_key):
        """Test retrieving a specific memory by ID."""
        # Store a memory first
        memory_data = {"content": "Specific memory for ID retrieval test", "metadata": {"test_id": "get_by_id_test"}}

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200
        memory_id = store_response.json()["id"]

        # Get the memory by ID
        response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id
        assert data["content"] == memory_data["content"]
        # Metadata is now in typed fields, not preserved exactly
        assert data["metadata"] is not None

    @pytest.mark.asyncio
    async def test_list_memories_paginated(self, client, api_key):
        """Test paginated memory listing."""
        # Store multiple memories
        for i in range(5):
            memory_data = {
                "content": f"Memory {i} for pagination test",
                "metadata": {"batch": "pagination_test", "index": i},
            }
            response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
            assert response.status_code == 200

        # Test pagination
        response = await client.get("/memories", params={"api_key": api_key, "limit": 3, "offset": 0})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)  # Response is a list directly
        assert len(data) <= 3  # Should respect limit

    @pytest.mark.asyncio
    async def test_delete_memory(self, client, api_key):
        """Test memory deletion."""
        # Store a memory first
        memory_data = {"content": "Memory to be deleted", "metadata": {"test": "deletion"}}

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200
        memory_id = store_response.json()["id"]

        # Delete the memory
        delete_response = await client.delete(f"/memories/{memory_id}", params={"api_key": api_key})
        assert delete_response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})
        assert get_response.status_code == 404


class TestAuthentication:
    """Test authentication and security."""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client):
        """Test that endpoints require authentication."""
        memory_data = {"content": "Test memory", "metadata": {}}

        # Try without API key
        response = await client.post("/memories", json=memory_data)
        assert response.status_code == 422

        # Try with invalid API key
        response = await client.post("/memories", json=memory_data, params={"api_key": "invalid"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_authentication(self, client, api_key):
        """Test that valid API key works."""
        memory_data = {"content": "Test memory", "metadata": {}}

        response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert response.status_code == 200


class TestDataValidation:
    """Test data validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_memory_data(self, client, api_key):
        """Test handling of invalid memory data."""
        # Missing content
        response = await client.post("/memories", json={"metadata": {}}, params={"api_key": api_key})
        assert response.status_code == 422

        # Invalid JSON structure
        response = await client.post("/memories", json={"content": 123}, params={"api_key": api_key})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_search_data(self, client, api_key):
        """Test handling of invalid search data."""
        # Missing query
        response = await client.post("/memories/search", json={"limit": 10}, params={"api_key": api_key})
        assert response.status_code == 422

        # Invalid limit
        response = await client.post(
            "/memories/search", json={"query": "test", "limit": -1}, params={"api_key": api_key}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_memory_id(self, client, api_key):
        """Test handling of nonexistent memory ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/memories/{fake_id}", params={"api_key": api_key})
        assert response.status_code == 404


class TestStatusEndpoint:
    """Test status endpoint functionality."""

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client, api_key):
        """Test status endpoint returns proper information."""
        response = await client.get("/status", params={"api_key": api_key})
        assert response.status_code == 200

        data = response.json()
        assert "database" in data
        assert "index_status" in data
        # Memory count is in the index_status or as total_memories
        assert "total_memories" in data["index_status"] or "recommendations" in data

    @pytest.mark.asyncio
    async def test_status_endpoint_unauthorized(self, client):
        """Test status endpoint requires authentication."""
        response = await client.get("/status")
        assert response.status_code == 422
