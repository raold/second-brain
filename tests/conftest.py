# tests/conftest.py

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient
from types import SimpleNamespace

import app.router as app_router
from app.main import app
from app.models import Payload, PayloadType, Priority
from app.config import config


# ===== AUTHENTICATION FIXTURES =====

def always_allow(request: Request):
    """Mock auth function that always allows requests"""
    return None


@pytest.fixture(autouse=True)
def setup_test_auth():
    """Setup test authentication - automatically applied to all tests"""
    # Override auth dependency to always allow
    app.dependency_overrides[app_router.verify_token] = always_allow
    # Set test token in config
    config.override_for_testing(api_tokens=['test-token'])
    yield
    # Cleanup
    app.dependency_overrides.clear()
    config.reset_to_defaults()


@pytest.fixture
def auth_header():
    """Provide standard auth header for API requests"""
    return {"Authorization": "Bearer test-token"}


# ===== CLIENT FIXTURES =====

@pytest.fixture
def test_client():
    """Provide FastAPI test client with auth setup"""
    return TestClient(app)


# ===== MOCK FIXTURES =====

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = Mock()
    client.embeddings.create.return_value = Mock(
        data=[Mock(embedding=[0.1] * 1536)]
    )
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    client = Mock()
    client.upsert.return_value = None
    client.search.return_value = []
    client.retrieve.return_value = []
    return client


@pytest.fixture
def mock_embedding():
    """Mock embedding vector"""
    return [0.1, 0.2, 0.3] + [0.0] * 1533  # 1536 dimensions total


@pytest.fixture(autouse=True)
def patch_external_services(monkeypatch, mock_embedding):
    """Auto-patch external services to prevent real API calls"""
    # Patch OpenAI embedding generation
    monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", 
                       MagicMock(return_value=mock_embedding))
    monkeypatch.setattr("app.utils.openai_client.get_openai_embedding",
                       MagicMock(return_value=mock_embedding))
    
    # Patch Qdrant operations
    monkeypatch.setattr("app.router.qdrant_upsert", MagicMock(return_value=None))
    monkeypatch.setattr("app.router.qdrant_search", MagicMock(return_value=[]))
    
    # Patch file operations
    monkeypatch.setattr("app.router.write_markdown", MagicMock(return_value=True))
    
    # Patch async intent detection
    async def mock_detect_intent(*args, **kwargs):
        return "note"
    monkeypatch.setattr("app.router.detect_intent_via_llm", mock_detect_intent)
    
    # Patch background storage
    monkeypatch.setattr("app.router.store_memory_pg_background", MagicMock(return_value=None))


# ===== DATA FIXTURES =====

@pytest.fixture
def sample_payload_dict():
    """Sample payload as dictionary"""
    return {
        "id": "test-123",
        "type": "note",
        "context": "test-context",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "This is a test note."},
        "meta": {"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"},
        "intent": "note",
        "target": "test-target"
    }


@pytest.fixture
def sample_payload():
    """Sample payload as Pydantic model"""
    return Payload(
        id="test-123",
        type=PayloadType.NOTE,
        context="test-context",
        priority=Priority.NORMAL,
        ttl="1d",
        data={"note": "This is a test note."},
        meta={"source": "unit-test", "timestamp": "2025-07-13T00:00:00Z"},
        intent="note",
        target="test-target"
    )


@pytest.fixture
def sample_search_results():
    """Sample search results"""
    return [
        {
            "id": "test-id-123",
            "score": 0.99,
            "note": "Test note for version tracking",
            "timestamp": "2023-01-01T00:00:00Z",
            "embedding_model": "text-embedding-3-small",
            "model_version": "gpt-4o",
            "type": "test",
            "priority": "low",
            "meta": {
                "model_version": "gpt-4o", 
                "embedding_model": "text-embedding-3-small"
            }
        }
    ]


@pytest.fixture
def sample_qdrant_point():
    """Sample Qdrant point for testing"""
    return SimpleNamespace(
        id="test-id-123",
        score=0.99,
        embedding_model="text-embedding-3-small",
        model_version="gpt-4o",
        note="Test note for version tracking",
        timestamp="2025-07-14T00:00:00Z",
        type="test",
        priority="low",
        payload={
            "data": {"note": "Test note for version tracking"},
            "type": "test",
            "priority": "low",
            "meta": {
                "model_version": "gpt-4o", 
                "embedding_model": "text-embedding-3-small"
            }
        }
    )


# ===== WEBSOCKET FIXTURES =====

@pytest.fixture
def websocket_data_batch():
    """Sample WebSocket batch data"""
    return {
        "batch": [
            {"id": "1", "prompt": "test prompt 1", "type": "llm"},
            {"id": "2", "prompt": "test prompt 2", "type": "llm"}
        ],
        "json": True
    }


@pytest.fixture
def websocket_data_single():
    """Sample WebSocket single prompt data"""
    return {
        "prompt": "Hello world this is a test",
        "json": False
    }


# ===== ERROR TESTING FIXTURES =====

@pytest.fixture
def mock_openai_error():
    """Mock OpenAI API error"""
    def side_effect(*args, **kwargs):
        raise Exception("OpenAI API error")
    return side_effect


@pytest.fixture
def mock_qdrant_error():
    """Mock Qdrant connection error"""
    def side_effect(*args, **kwargs):
        raise Exception("Qdrant connection failed")
    return side_effect


@pytest.fixture
def mock_file_error():
    """Mock file system error"""
    def side_effect(*args, **kwargs):
        raise Exception("File system error")
    return side_effect


# ===== COMPREHENSIVE MOCK FIXTURE =====

@pytest.fixture
def comprehensive_mocks(monkeypatch, sample_search_results):
    """Comprehensive mocking fixture for complex tests"""
    mocks = {}
    
    # OpenAI mocks
    mocks['openai_client'] = Mock()
    mocks['embedding'] = Mock(return_value=[0.1] * 1536)
    
    # Qdrant mocks
    mocks['qdrant_upsert'] = Mock(return_value=None)
    mocks['qdrant_search'] = Mock(return_value=sample_search_results)
    
    # File system mocks
    mocks['write_markdown'] = Mock(return_value=True)
    
    # Apply patches
    monkeypatch.setattr("app.storage.qdrant_client.get_openai_client", 
                       lambda: mocks['openai_client'])
    monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", 
                       mocks['embedding'])
    monkeypatch.setattr("app.router.qdrant_upsert", mocks['qdrant_upsert'])
    monkeypatch.setattr("app.router.qdrant_search", mocks['qdrant_search'])
    monkeypatch.setattr("app.router.write_markdown", mocks['write_markdown'])
    
    return mocks


# ===== PERFORMANCE TESTING FIXTURES =====

@pytest.fixture
def large_payload():
    """Large payload for performance testing"""
    return {
        "id": "large-test-123",
        "type": "note",
        "context": "performance-test",
        "priority": "normal",
        "ttl": "1d",
        "data": {"note": "Large test note content. " * 1000},  # Large content
        "meta": {"source": "performance-test"},
        "intent": "note"
    }


@pytest.fixture
def multiple_payloads():
    """Multiple payloads for batch testing"""
    return [
        {
            "id": f"batch-test-{i}",
            "type": "note",
            "context": "batch-test",
            "priority": "normal",
            "ttl": "1d",
            "data": {"note": f"Batch test note {i}"},
            "meta": {"source": "batch-test", "batch_id": i},
            "intent": "note"
        }
        for i in range(10)
    ]


# ===== DATABASE FIXTURES =====

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.flush = Mock()
    session.execute = Mock()
    session.close = Mock()
    return session


# ===== PLUGIN FIXTURES =====

@pytest.fixture
def sample_plugin():
    """Sample plugin for testing"""
    class TestPlugin:
        def __init__(self):
            self.name = 'test_plugin'
        
        def on_memory(self, memory):
            return {"processed": True}
    
    return TestPlugin()


# ===== CONFIGURATION FIXTURES =====

@pytest.fixture
def test_config():
    """Test configuration overrides"""
    original_config = {}
    
    # Store original values
    for attr in dir(config):
        if not attr.startswith('_'):
            original_config[attr] = getattr(config, attr)
    
    # Set test values
    config.override_for_testing(
        api_tokens=['test-token'],
        log_level='DEBUG'
    )
    # Override qdrant collection for testing
    original_qdrant_collection = config.qdrant['collection']
    config.qdrant['collection'] = 'test_collection'
    
    yield config
    
    # Restore original values
    config.qdrant['collection'] = original_qdrant_collection
    config.reset_to_defaults()


# ===== ASYNC TESTING FIXTURES =====

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ===== TIMESTAMP FIXTURES =====

@pytest.fixture
def fixed_datetime():
    """Fixed datetime for testing"""
    from datetime import datetime
    return datetime(2023, 7, 13, 12, 0, 0)


@pytest.fixture
def mock_datetime(monkeypatch, fixed_datetime):
    """Mock datetime.now() to return fixed time"""
    class MockDateTime:
        @classmethod
        def now(cls):
            return fixed_datetime
        
        @classmethod
        def isoformat(cls):
            return fixed_datetime.isoformat()
    
    monkeypatch.setattr("datetime.datetime", MockDateTime)
    return fixed_datetime 