"""
Comprehensive mock fixtures for external services (PostgreSQL, Qdrant, OpenAI).
Provides realistic mocks that simulate actual service behavior for testing.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from qdrant_client.http.models import PointStruct, ScoredPoint


# ===== OPENAI MOCKS =====

class MockOpenAIEmbedding:
    """Mock OpenAI embedding response"""
    def __init__(self, embedding: List[float]):
        self.embedding = embedding


class MockOpenAIResponse:
    """Mock OpenAI API response"""
    def __init__(self, embeddings: List[MockOpenAIEmbedding]):
        self.data = embeddings


@pytest.fixture
def mock_openai_embedding():
    """Generate a realistic mock embedding vector"""
    # Create a 1536-dimensional embedding (text-embedding-3-small dimension)
    import random
    random.seed(42)  # For consistent test results
    return [random.uniform(-1, 1) for _ in range(1536)]


@pytest.fixture
def mock_openai_client(mock_openai_embedding):
    """Mock OpenAI client with realistic behavior"""
    client = Mock()
    
    # Mock embeddings.create method
    def create_embedding(input, model="text-embedding-3-small", **kwargs):
        # Simulate API delay
        time.sleep(0.01)
        
        # Handle single or batch input
        if isinstance(input, str):
            inputs = [input]
        else:
            inputs = input
        
        # Generate embeddings for each input
        embeddings = []
        for text in inputs:
            # Create slightly different embeddings based on text length
            base_embedding = mock_openai_embedding.copy()
            # Add some variation based on text
            for i in range(min(10, len(text))):
                base_embedding[i] += 0.01
            embeddings.append(MockOpenAIEmbedding(base_embedding))
        
        return MockOpenAIResponse(embeddings)
    
    client.embeddings.create = Mock(side_effect=create_embedding)
    return client


# ===== QDRANT MOCKS =====

@pytest.fixture
def mock_qdrant_point():
    """Create a mock Qdrant point"""
    return {
        "id": str(uuid.uuid4()),
        "payload": {
            "text": "Test memory content",
            "type": "note",
            "priority": "normal",
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model_version": "v1.5.0",
                "embedding_model": "text-embedding-3-small"
            }
        },
        "vector": [0.1] * 1536
    }


@pytest.fixture
def mock_qdrant_search_result(mock_qdrant_point):
    """Create mock Qdrant search results"""
    def create_results(query: str, limit: int = 5):
        results = []
        for i in range(min(limit, 3)):  # Return max 3 results
            point = mock_qdrant_point.copy()
            point["id"] = str(uuid.uuid4())
            point["payload"]["text"] = f"Result {i+1} for query: {query}"
            
            # Create scored point
            scored_point = ScoredPoint(
                id=point["id"],
                score=0.95 - (i * 0.1),  # Decreasing relevance
                payload=point["payload"],
                vector=None,  # Don't include vector in results
                version=0  # Add required version parameter
            )
            results.append(scored_point)
        
        return results
    
    return create_results


@pytest.fixture
def mock_qdrant_client(mock_qdrant_search_result):
    """Mock Qdrant client with realistic behavior"""
    client = Mock()
    
    # Storage for upserted points (in-memory simulation)
    storage = {}
    
    def upsert(collection_name: str, points: List[PointStruct], **kwargs):
        """Mock upsert operation"""
        time.sleep(0.02)  # Simulate network delay
        
        for point in points:
            # Store point in our mock storage
            if hasattr(point, 'id'):
                storage[point.id] = {
                    "id": point.id,
                    "payload": point.payload,
                    "vector": point.vector
                }
        
        return None
    
    def search(collection_name: str, query_vector: List[float], 
               limit: int = 5, **kwargs):
        """Mock search operation"""
        time.sleep(0.03)  # Simulate search delay
        
        # Return mock results based on collection
        if collection_name == "memories":
            return mock_qdrant_search_result("mock query", limit)
        return []
    
    def retrieve(collection_name: str, ids: List[str], **kwargs):
        """Mock retrieve operation"""
        time.sleep(0.01)  # Simulate retrieval delay
        
        results = []
        for id in ids:
            if id in storage:
                results.append(storage[id])
        return results
    
    # Assign mock methods
    client.upsert = Mock(side_effect=upsert)
    client.search = Mock(side_effect=search)
    client.retrieve = Mock(side_effect=retrieve)
    client.get_collection = Mock(return_value={"vectors_count": len(storage)})
    
    return client


# ===== POSTGRESQL MOCKS =====

class MockMemory:
    """Mock Memory model object"""
    def __init__(self, **kwargs):
        self.id = uuid.uuid4()
        self.text_content = kwargs.get('text_content', 'Test memory')
        self.embedding_vector = kwargs.get('embedding_vector')
        self.intent_type = kwargs.get('intent_type', 'note')
        self.model_version = kwargs.get('model_version', 'v1.5.0')
        self.embedding_model = kwargs.get('embedding_model', 'text-embedding-3-small')
        self.embedding_dimensions = len(self.embedding_vector) if self.embedding_vector else 0
        self.priority = kwargs.get('priority', 'normal')
        self.source = kwargs.get('source', 'api')
        self.tags = kwargs.get('tags', [])
        self.memory_metadata = kwargs.get('memory_metadata', {})
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.is_active = True
        self.feedback_score = 0.0
        self.access_count = 0
        self.version = 1
        self.parent_id = None


class MockAsyncSession:
    """Mock SQLAlchemy async session"""
    def __init__(self):
        self.storage = {}
        self.committed = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and not self.committed:
            await self.commit()
    
    def add(self, obj):
        """Add object to session"""
        if hasattr(obj, 'id'):
            self.storage[str(obj.id)] = obj
    
    async def commit(self):
        """Commit transaction"""
        self.committed = True
        await asyncio.sleep(0.01)  # Simulate commit delay
    
    async def refresh(self, obj):
        """Refresh object"""
        pass  # No-op in mock
    
    async def execute(self, query):
        """Execute query - returns mock result"""
        # Simple mock - return all stored memories
        storage = self.storage
        
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return list(storage.values())
                    
                    def first(self):
                        return list(storage.values())[0] if storage else None
                
                return MockScalars()
        
        return MockResult()


@pytest.fixture
def mock_postgres_client():
    """Mock PostgreSQL client with realistic behavior"""
    client = AsyncMock()
    
    # In-memory storage
    memory_storage = {}
    search_history = {}
    
    async def store_memory(**kwargs):
        """Mock store_memory operation"""
        await asyncio.sleep(0.02)  # Simulate DB delay
        
        memory = MockMemory(**kwargs)
        memory_id = str(memory.id)
        memory_storage[memory_id] = memory
        
        return memory_id
    
    async def get_memory(memory_id: str, use_cache: bool = True):
        """Mock get_memory operation"""
        await asyncio.sleep(0.01)  # Simulate DB delay
        
        if memory_id in memory_storage:
            memory = memory_storage[memory_id]
            return {
                "id": str(memory.id),
                "text_content": memory.text_content,
                "intent_type": memory.intent_type,
                "priority": memory.priority,
                "created_at": memory.created_at.isoformat(),
                "embedding_dimensions": memory.embedding_dimensions,
                "tags": memory.tags,
                "metadata": memory.memory_metadata
            }
        return None
    
    async def search_memories(**kwargs):
        """Mock search_memories operation"""
        await asyncio.sleep(0.03)  # Simulate search delay
        
        # Return mock search results
        results = []
        for memory_id, memory in list(memory_storage.items())[:kwargs.get('limit', 20)]:
            results.append({
                "id": memory_id,
                "text_content": memory.text_content,
                "intent_type": memory.intent_type,
                "priority": memory.priority,
                "score": 0.95,
                "created_at": memory.created_at.isoformat()
            })
        
        return results
    
    async def health_check():
        """Mock health check"""
        await asyncio.sleep(0.01)
        return {
            "status": "healthy",
            "connected": True,
            "pool_size": 20,
            "active_connections": 5,
            "memory_count": len(memory_storage),
            "avg_query_time": 0.025,
            "cache_hit_ratio": 0.85,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Assign mock methods
    client.store_memory = AsyncMock(side_effect=store_memory)
    client.get_memory = AsyncMock(side_effect=get_memory)
    client.search_memories = AsyncMock(side_effect=search_memories)
    client.health_check = AsyncMock(side_effect=health_check)
    client.update_memory_access = AsyncMock(return_value=None)
    client.record_search = AsyncMock(return_value=str(uuid.uuid4()))
    client._initialized = True
    
    # Mock session factory
    client.session_factory = lambda: MockAsyncSession()
    
    return client


# ===== DEPENDENCY INJECTION FIXTURES =====

@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch, mock_openai_client, mock_qdrant_client, mock_postgres_client):
    """Automatically mock all external services for tests"""
    
    # Mock OpenAI client creation
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: mock_openai_client)
    monkeypatch.setattr("app.utils.openai_client.get_openai_client", lambda: mock_openai_client)
    
    # Mock embedding functions
    async def mock_get_embedding_async(text: str):
        await asyncio.sleep(0.01)
        return mock_openai_client.embeddings.create(input=text).data[0].embedding
    
    def mock_get_embedding(text: str, client=None):
        return mock_openai_client.embeddings.create(input=text).data[0].embedding
    
    monkeypatch.setattr("app.utils.openai_client.get_openai_embedding", mock_get_embedding)
    monkeypatch.setattr("app.utils.openai_client.get_openai_embedding_async", mock_get_embedding_async)
    monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", mock_get_embedding)
    
    # Mock Qdrant
    monkeypatch.setattr("app.storage.qdrant_client.client", mock_qdrant_client)
    
    # Mock PostgreSQL
    monkeypatch.setattr("app.storage.postgres_client.postgres_client", mock_postgres_client)
    monkeypatch.setattr("app.storage.postgres_client.get_postgres_client", 
                       AsyncMock(return_value=mock_postgres_client))
    
    # Mock additional router functions
    monkeypatch.setattr("app.router.write_markdown", AsyncMock(return_value=True))
    monkeypatch.setattr("app.router.qdrant_upsert", AsyncMock(return_value=None))
    monkeypatch.setattr("app.router.qdrant_search", AsyncMock(return_value=[]))
    
    # Mock intent detection
    async def mock_detect_intent(*args, **kwargs):
        return "note"
    monkeypatch.setattr("app.router.detect_intent_via_llm", mock_detect_intent)
    
    # Mock background tasks
    monkeypatch.setattr("app.router.store_memory_pg_background", AsyncMock(return_value=None))
    
    yield
    
    # Cleanup is handled by pytest's monkeypatch


# ===== TEST HELPER FIXTURES =====

@pytest.fixture
def verify_no_external_calls():
    """Helper to verify no real external API calls are made"""
    
    def verify():
        # This would check that mock methods were called instead of real ones
        # Implementation depends on your specific needs
        pass
    
    return verify


@pytest.fixture
def reset_mock_storage(mock_postgres_client, mock_qdrant_client):
    """Reset all mock storage between tests"""
    # Clear any in-memory storage
    if hasattr(mock_postgres_client, 'memory_storage'):
        mock_postgres_client.memory_storage.clear()
    
    # Reset call counts
    mock_postgres_client.reset_mock()
    mock_qdrant_client.reset_mock()
    
    yield
    
    # Post-test cleanup if needed 