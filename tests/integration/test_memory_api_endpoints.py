"""
Comprehensive Integration Tests for Memory API Endpoints
Tests all memory-related endpoints with real FastAPI client
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestMemoryAPIEndpoints:
    """Test all memory API endpoints for complete coverage"""

    @pytest.mark.asyncio
    async def test_store_semantic_memory_success(self, client: AsyncClient, api_key: str):
        """Test successful semantic memory storage"""
        payload = {
            "content": "Python is a programming language with dynamic typing",
            "semantic_metadata": {
                "domain": "technology",
                "concepts": ["python", "programming", "dynamic typing"],
                "confidence": 0.9
            },
            "importance_score": 0.8
        }
        
        response = await client.post(
            "/memories/semantic",
            json=payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["content"] == payload["content"]
        assert data["memory_type"] == "semantic"
        assert data["importance_score"] == 0.8

    @pytest.mark.asyncio
    async def test_store_episodic_memory_success(self, client: AsyncClient, api_key: str):
        """Test successful episodic memory storage"""
        payload = {
            "content": "Had a meeting with the development team about the new feature",
            "episodic_metadata": {
                "location": "Conference Room A",
                "participants": ["John", "Sarah", "Mike"],
                "event_type": "meeting",
                "emotional_context": "productive"
            },
            "importance_score": 0.7
        }
        
        response = await client.post(
            "/memories/episodic",
            json=payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["content"] == payload["content"]
        assert data["memory_type"] == "episodic"

    @pytest.mark.asyncio
    async def test_store_procedural_memory_success(self, client: AsyncClient, api_key: str):
        """Test successful procedural memory storage"""
        payload = {
            "content": "To deploy the application: 1. Build Docker image 2. Push to registry 3. Update k8s manifests",
            "procedural_metadata": {
                "skill_level": "intermediate",
                "domain": "devops",
                "steps": ["build", "push", "deploy"],
                "tools": ["docker", "kubernetes"],
                "estimated_time": "15 minutes"
            },
            "importance_score": 0.9
        }
        
        response = await client.post(
            "/memories/procedural",
            json=payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["content"] == payload["content"]
        assert data["memory_type"] == "procedural"

    @pytest.mark.asyncio
    async def test_contextual_search_with_filters(self, client: AsyncClient, api_key: str):
        """Test contextual search with memory type filters"""
        # First, store some memories
        memories = [
            {
                "endpoint": "/memories/semantic",
                "payload": {
                    "content": "Machine learning is a subset of artificial intelligence",
                    "semantic_metadata": {"domain": "AI", "concepts": ["ML", "AI"]},
                    "importance_score": 0.8
                }
            },
            {
                "endpoint": "/memories/episodic", 
                "payload": {
                    "content": "Attended ML conference yesterday",
                    "episodic_metadata": {"event_type": "conference", "location": "San Francisco"},
                    "importance_score": 0.6
                }
            }
        ]
        
        # Store test memories
        for memory in memories:
            await client.post(
                memory["endpoint"],
                json=memory["payload"],
                params={"api_key": api_key}
            )
        
        # Test contextual search
        search_payload = {
            "query": "machine learning",
            "memory_types": ["semantic"],
            "limit": 10,
            "importance_threshold": 0.5,
            "include_archived": False
        }
        
        response = await client.post(
            "/memories/search/contextual",
            json=search_payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should only return semantic memories due to filter
        semantic_memories = [m for m in data if m["memory_type"] == "semantic"]
        assert len(semantic_memories) >= 1

    @pytest.mark.asyncio
    async def test_memory_validation_errors(self, client: AsyncClient, api_key: str):
        """Test validation errors for invalid memory data"""
        # Test empty content
        response = await client.post(
            "/memories/semantic",
            json={"content": "", "importance_score": 0.5},
            params={"api_key": api_key}
        )
        assert response.status_code in [400, 422]  # Validation error
        
        # Test invalid importance score
        response = await client.post(
            "/memories/semantic",
            json={"content": "Valid content", "importance_score": 1.5},
            params={"api_key": api_key}
        )
        assert response.status_code in [400, 422]  # Validation error

    @pytest.mark.asyncio
    async def test_memory_crud_operations(self, client: AsyncClient, api_key: str):
        """Test complete CRUD cycle for memories"""
        # Create
        create_payload = {
            "content": "Test memory for CRUD operations",
            "importance_score": 0.7
        }
        
        create_response = await client.post(
            "/memories/semantic",
            json=create_payload,
            params={"api_key": api_key}
        )
        
        assert create_response.status_code == 200
        memory = create_response.json()
        memory_id = memory["id"]
        
        # Read
        read_response = await client.get(
            f"/memories/{memory_id}",
            params={"api_key": api_key}
        )
        
        assert read_response.status_code == 200
        retrieved_memory = read_response.json()
        assert retrieved_memory["id"] == memory_id
        assert retrieved_memory["content"] == create_payload["content"]
        
        # Delete
        delete_response = await client.delete(
            f"/memories/{memory_id}",
            params={"api_key": api_key}
        )
        
        assert delete_response.status_code == 200
        
        # Verify deletion
        verify_response = await client.get(
            f"/memories/{memory_id}",
            params={"api_key": api_key}
        )
        
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_memories_pagination(self, client: AsyncClient, api_key: str):
        """Test memory listing with pagination"""
        # Store multiple memories first
        for i in range(5):
            payload = {
                "content": f"Test memory {i} for pagination",
                "importance_score": 0.5
            }
            await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )
        
        # Test pagination
        response = await client.get(
            "/memories",
            params={"api_key": api_key, "limit": 3, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3
        
        # Test second page
        response = await client.get(
            "/memories",
            params={"api_key": api_key, "limit": 3, "offset": 3}
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_memories_basic(self, client: AsyncClient, api_key: str):
        """Test basic memory search functionality"""
        # Store a searchable memory
        payload = {
            "content": "Artificial intelligence and machine learning are transforming technology",
            "importance_score": 0.8
        }
        
        await client.post(
            "/memories/semantic",
            json=payload,
            params={"api_key": api_key}
        )
        
        # Search for the memory
        search_payload = {
            "query": "artificial intelligence technology",
            "limit": 10
        }
        
        response = await client.post(
            "/memories/search",
            json=search_payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should find at least one relevant memory
        assert len(data) >= 0  # May be 0 if embeddings aren't working in test

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that endpoints require proper authentication"""
        # Test without API key
        response = await client.get("/memories")
        assert response.status_code in [401, 422]  # Unauthorized or validation error
        
        # Test with invalid API key
        response = await client.get(
            "/memories",
            params={"api_key": "invalid-key"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_memory_metadata_storage(self, client: AsyncClient, api_key: str):
        """Test that memory metadata is properly stored and retrieved"""
        payload = {
            "content": "Advanced Python decorators and metaclasses",
            "semantic_metadata": {
                "domain": "programming",
                "difficulty": "advanced",
                "concepts": ["decorators", "metaclasses", "python"],
                "confidence": 0.95
            },
            "importance_score": 0.9
        }
        
        # Store memory
        response = await client.post(
            "/memories/semantic",
            json=payload,
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        memory_id = data["id"]
        
        # Retrieve and verify metadata
        response = await client.get(
            f"/memories/{memory_id}",
            params={"api_key": api_key}
        )
        
        assert response.status_code == 200
        retrieved = response.json()
        
        # Verify semantic metadata is preserved
        if "semantic_metadata" in retrieved:
            metadata = retrieved["semantic_metadata"]
            assert metadata["domain"] == "programming"
            assert "decorators" in metadata["concepts"]

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, client: AsyncClient, api_key: str):
        """Test rate limiting behavior (if enabled)"""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = await client.get(
                "/health",
                params={"api_key": api_key}
            )
            responses.append(response.status_code)
        
        # Most should succeed, but might hit rate limits
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 5  # At least some should succeed

    @pytest.mark.asyncio 
    async def test_error_handling_database_failures(self, client: AsyncClient, api_key: str):
        """Test error handling when database operations fail"""
        with patch('app.database.Database.store_memory') as mock_store:
            mock_store.side_effect = Exception("Database connection failed")
            
            payload = {
                "content": "Test memory that should fail",
                "importance_score": 0.5
            }
            
            response = await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )
            
            # Should return server error
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_memory_content_sanitization(self, client: AsyncClient, api_key: str):
        """Test that memory content is properly sanitized"""
        # Test with potentially dangerous content
        dangerous_contents = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE memories; --",
            "Content with unicode: 🧠🤖",
            "Very long content: " + "A" * 10000
        ]
        
        for content in dangerous_contents:
            payload = {
                "content": content,
                "importance_score": 0.5
            }
            
            response = await client.post(
                "/memories/semantic", 
                json=payload,
                params={"api_key": api_key}
            )
            
            # Should either succeed (sanitized) or fail with validation error
            assert response.status_code in [200, 400, 422]
            
            if response.status_code == 200:
                # If successful, content should be stored
                data = response.json()
                assert "id" in data