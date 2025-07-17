"""
Simple test suite for the refactored Second Brain application.
"""

import pytest
from httpx import AsyncClient

from app.app import app
from app.database import get_database


class TestAPI:
    """Test the API endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def api_key(self):
        """Get API key for testing."""
        import os

        tokens = os.getenv("API_TOKENS", "").split(",")
        return tokens[0].strip() if tokens else "test-key"

    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_store_memory(self, client, api_key):
        """Test storing a memory."""
        memory_data = {"content": "This is a test memory", "metadata": {"type": "test", "tags": ["example"]}}

        response = await client.post("/memories", json=memory_data, params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == memory_data["content"]
        assert data["metadata"] == memory_data["metadata"]
        assert "id" in data

    async def test_search_memories(self, client, api_key):
        """Test searching memories."""
        # First store a memory
        memory_data = {"content": "Python is a programming language", "metadata": {"type": "fact"}}

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200

        # Then search for it
        search_data = {"query": "programming language", "limit": 5}

        response = await client.post("/memories/search", json=search_data, params={"api_key": api_key})

        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0
        assert results[0]["content"] == memory_data["content"]

    async def test_get_memory(self, client, api_key):
        """Test getting a specific memory."""
        # First store a memory
        memory_data = {"content": "Test memory for retrieval", "metadata": {"type": "test"}}

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200
        memory_id = store_response.json()["id"]

        # Then get it
        response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == memory_data["content"]
        assert data["id"] == memory_id

    async def test_delete_memory(self, client, api_key):
        """Test deleting a memory."""
        # First store a memory
        memory_data = {"content": "Memory to be deleted", "metadata": {"type": "temporary"}}

        store_response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
        assert store_response.status_code == 200
        memory_id = store_response.json()["id"]

        # Then delete it
        response = await client.delete(f"/memories/{memory_id}", params={"api_key": api_key})

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify it's deleted
        get_response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})
        assert get_response.status_code == 404

    async def test_list_memories(self, client, api_key):
        """Test listing memories."""
        response = await client.get("/memories", params={"api_key": api_key, "limit": 10})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_authentication_required(self, client):
        """Test that authentication is required."""
        response = await client.get("/memories")
        assert response.status_code == 422  # Missing required parameter

        response = await client.get("/memories", params={"api_key": "invalid"})
        assert response.status_code == 401


class TestDatabase:
    """Test database operations."""

    @pytest.fixture
    async def db(self):
        """Get database instance."""
        return await get_database()

    async def test_store_and_retrieve_memory(self, db):
        """Test storing and retrieving a memory."""
        content = "Test memory content"
        metadata = {"type": "test", "priority": "high"}

        # Store memory
        memory_id = await db.store_memory(content, metadata)
        assert memory_id is not None

        # Retrieve memory
        memory = await db.get_memory(memory_id)
        assert memory is not None
        assert memory["content"] == content
        assert memory["metadata"] == metadata
        assert memory["id"] == memory_id

    async def test_search_memories(self, db):
        """Test searching memories."""
        # Store test memories
        await db.store_memory("Python is great for data science", {"type": "fact"})
        await db.store_memory("Machine learning is fascinating", {"type": "opinion"})

        # Search for related content
        results = await db.search_memories("Python data science", limit=5)
        assert len(results) > 0
        assert results[0]["similarity"] > 0.5  # Should be reasonably similar

    async def test_delete_memory(self, db):
        """Test deleting a memory."""
        # Store memory
        memory_id = await db.store_memory("Memory to delete", {"type": "temporary"})

        # Verify it exists
        memory = await db.get_memory(memory_id)
        assert memory is not None

        # Delete it
        deleted = await db.delete_memory(memory_id)
        assert deleted is True

        # Verify it's gone
        memory = await db.get_memory(memory_id)
        assert memory is None

    async def test_list_memories(self, db):
        """Test listing memories."""
        # Store a few memories
        await db.store_memory("First memory", {"order": 1})
        await db.store_memory("Second memory", {"order": 2})

        # List memories
        memories = await db.get_all_memories(limit=10)
        assert len(memories) >= 2

        # Should be ordered by creation time (newest first)
        assert memories[0]["created_at"] >= memories[1]["created_at"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
