"""
Extended integration tests for Second Brain v2.0.0
Comprehensive test coverage for all components
"""

import os

import pytest

from app.database_mock import MockDatabase
from app.version import get_version_info, get_version

# Set up test environment
os.environ["USE_MOCK_DATABASE"] = "true"
os.environ["API_TOKENS"] = "test-key-1,test-key-2"


class TestIntegrationSuite:
    """Integration tests for full system functionality."""

    @pytest.mark.asyncio
    async def test_version_info_integration(self, client):
        """Test version info integration across app, API, and docs."""
        # Get version from version module
        version_info = get_version_info()
        assert version_info["version"] == get_version()
        assert version_info["build"] == "development"  # Current build status

        # Get version from API endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        api_data = response.json()
        assert api_data["version"] == get_version()

        # Ensure consistency across sources
        assert version_info["version"] == api_data["version"]

    @pytest.mark.asyncio
    async def test_health_endpoint_with_version(self, client):
        """Test health endpoint returns correct version."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == get_version()
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_status_endpoint_comprehensive(self, client, api_key):
        """Test status endpoint with comprehensive data."""
        response = await client.get("/status", params={"api_key": api_key})
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "index_status" in data
        assert data["database"] == "connected"

    @pytest.mark.asyncio
    async def test_memory_lifecycle_comprehensive(self, client, api_key):
        """Test complete memory lifecycle with edge cases."""
        # Test storing memory with complex metadata (simplified for security validation)
        complex_memory = {
            "content": "This is a complex memory with unicode: 🧠 and safe special chars",
            "metadata": {
                "type": "test",
                "tags": "unicode,special-chars",  # Changed from array to string
                "priority": 1,
                "level": 2,  # Flattened nested structure
                "timestamp": "2025-07-17T13:00:00Z",
            },
        }

        # Store memory
        response = await client.post("/memories", json=complex_memory, params={"api_key": api_key})
        assert response.status_code == 200
        stored_memory = response.json()
        memory_id = stored_memory["id"]

        # Verify stored data
        assert stored_memory["content"] == complex_memory["content"]
        # The metadata is now stored in the generic metadata field in MemoryResponse
        assert stored_memory["metadata"] is not None

        # Retrieve memory
        response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})
        assert response.status_code == 200
        retrieved_memory = response.json()
        assert retrieved_memory["content"] == complex_memory["content"]

        # Search for memory
        search_response = await client.post(
            "/memories/search", json={"query": "unicode special", "limit": 5}, params={"api_key": api_key}
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) > 0
        assert search_results[0]["id"] == memory_id

        # Delete memory
        delete_response = await client.delete(f"/memories/{memory_id}", params={"api_key": api_key})
        assert delete_response.status_code == 200

        # Verify deletion
        get_response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_memory_operations(self, client, api_key):
        """Test batch operations and pagination."""
        # Store multiple memories
        memories = []
        for i in range(15):
            memory_data = {
                "content": f"Batch memory {i} with unique content",
                "metadata": {"batch": i, "type": "batch_test"},
            }
            response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
            assert response.status_code == 200
            memories.append(response.json())

        # Test pagination
        response = await client.get("/memories", params={"api_key": api_key, "limit": 10})
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1) == 10

        response = await client.get("/memories", params={"api_key": api_key, "limit": 10, "offset": 10})
        assert response.status_code == 200
        page2 = response.json()
        # We expect the remaining memories (15 total - 10 from first page = 5)
        # But there may be additional memories from other tests, so check >= 5
        assert len(page2) >= 5

        # Test search with limit
        search_response = await client.post(
            "/memories/search", json={"query": "batch", "limit": 3}, params={"api_key": api_key}
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results) == 3

    @pytest.mark.asyncio
    async def test_error_handling_comprehensive(self, client, api_key):
        """Test comprehensive error handling."""
        # Test invalid JSON
        response = await client.post(
            "/memories",
            content="invalid json",
            headers={"Content-Type": "application/json"},
            params={"api_key": api_key},
        )
        assert response.status_code == 422

        # Test missing required fields
        response = await client.post("/memories", json={}, params={"api_key": api_key})
        assert response.status_code == 422

        # Test invalid memory ID
        response = await client.get("/memories/invalid-id", params={"api_key": api_key})
        assert response.status_code == 404

        # Test invalid search query
        response = await client.post("/memories/search", json={"limit": -1}, params={"api_key": api_key})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_authentication_edge_cases(self, client):
        """Test authentication edge cases."""
        # Test missing API key
        response = await client.get("/memories")
        assert response.status_code == 422

        # Test empty API key
        response = await client.get("/memories", params={"api_key": ""})
        assert response.status_code == 401

        # Test invalid API key
        response = await client.get("/memories", params={"api_key": "invalid-key"})
        assert response.status_code == 401

        # Test valid API key from list
        response = await client.get("/memories", params={"api_key": "test-key-2"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_and_headers(self, client, api_key):
        """Test CORS and header handling."""
        # Test CORS headers
        response = await client.options("/memories", params={"api_key": api_key})
        # FastAPI handles OPTIONS automatically

        # Test with custom headers
        response = await client.get("/memories", params={"api_key": api_key}, headers={"X-Test-Header": "test-value"})
        assert response.status_code == 200


class TestMockDatabaseEdgeCases:
    """Test mock database edge cases for full coverage."""

    @pytest.mark.asyncio
    async def test_uninitialized_database(self):
        """Test operations on uninitialized database."""
        db = MockDatabase()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.store_memory("test", {})

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.get_memory("test-id")

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.search_memories("test")

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, db):
        """Test handling of empty and edge case content."""
        # Empty content
        memory_id = await db.store_memory("", {})
        memory = await db.get_memory(memory_id)
        assert memory["content"] == ""

        # Very long content
        long_content = "x" * 10000
        memory_id = await db.store_memory(long_content, {})
        memory = await db.get_memory(memory_id)
        assert memory["content"] == long_content

    @pytest.mark.asyncio
    async def test_metadata_edge_cases(self, db):
        """Test metadata edge cases."""
        # None metadata - MockDatabase automatically adds memory type
        memory_id = await db.store_memory("test", None)
        memory = await db.get_memory(memory_id)
        assert memory["metadata"] == {"type": "semantic"}  # MockDatabase defaults to semantic

        # Empty metadata - type is added automatically
        memory_id = await db.store_memory("test", {})
        memory = await db.get_memory(memory_id)
        assert memory["metadata"] == {"type": "semantic"}  # Type is added automatically

        # Complex nested metadata
        complex_metadata = {"nested": {"deep": {"value": 42}}, "array": [1, 2, 3], "boolean": True, "null": None}
        memory_id = await db.store_memory("test", complex_metadata)
        memory = await db.get_memory(memory_id)
        assert memory["metadata"]["nested"]["deep"]["value"] == 42

    @pytest.mark.asyncio
    async def test_search_edge_cases(self, db):
        """Test search edge cases."""
        # Store some test memories
        await db.store_memory("Python programming", {"type": "code"})
        await db.store_memory("Java development", {"type": "code"})
        await db.store_memory("Database design", {"type": "design"})

        # Empty query
        results = await db.search_memories("", limit=10)
        assert len(results) == 3

        # Very specific query
        results = await db.search_memories("Python", limit=1)
        assert len(results) == 1

        # Limit of 0
        results = await db.search_memories("Python", limit=0)
        assert len(results) == 0

        # Large limit
        results = await db.search_memories("code", limit=100)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, db):
        """Test pagination edge cases."""
        # Store memories
        for i in range(5):
            await db.store_memory(f"Memory {i}", {"index": i})

        # Normal pagination
        results = await db.get_all_memories(limit=3, offset=0)
        assert len(results) == 3

        # Offset beyond data
        results = await db.get_all_memories(limit=3, offset=10)
        assert len(results) == 0

        # Large limit
        results = await db.get_all_memories(limit=100, offset=0)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_nonexistent_memory_operations(self, db):
        """Test operations on nonexistent memories."""
        # Get nonexistent memory
        memory = await db.get_memory("nonexistent-id")
        assert memory is None

        # Delete nonexistent memory
        result = await db.delete_memory("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_database_cleanup(self, db):
        """Test database cleanup operations."""
        # Store and delete memory
        memory_id = await db.store_memory("test", {})
        await db.delete_memory(memory_id)

        # Verify cleanup
        memory = await db.get_memory(memory_id)
        assert memory is None

        # Close database
        await db.close()
        assert db.is_initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
