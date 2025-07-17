"""
Test demonstrating proper mocking of external services (PostgreSQL, Qdrant, OpenAI).
Shows how the comprehensive mocks work together in integration tests.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_full_ingestion_flow_with_mocks(
    test_client: TestClient,
    auth_header: dict,
    sample_payload_dict: dict,
    mock_postgres_client,
    mock_qdrant_client,
    mock_openai_client
):
    """Test the full ingestion flow with all external services mocked"""
    
    # Make the ingestion request
    response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
    
    # Verify successful response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify OpenAI was called to generate embeddings
    mock_openai_client.embeddings.create.assert_called()
    
    # Verify PostgreSQL storage was called
    mock_postgres_client.store_memory.assert_called()
    
    # Verify the stored memory has correct properties
    call_args = mock_postgres_client.store_memory.call_args
    assert call_args.kwargs['text_content'] == sample_payload_dict['data']['note']
    assert call_args.kwargs['intent_type'] == 'note'
    assert call_args.kwargs['priority'] == 'normal'
    
    # Verify embedding was passed to storage
    assert 'embedding_vector' in call_args.kwargs
    assert len(call_args.kwargs['embedding_vector']) == 1536  # Correct dimensions


@pytest.mark.asyncio
async def test_search_with_mocked_services(
    test_client: TestClient,
    auth_header: dict,
    mock_postgres_client,
    mock_qdrant_client,
    mock_openai_client
):
    """Test search functionality with mocked external services"""
    
    # First ingest some test data
    test_memories = [
        {"id": "test-1", "data": {"note": "Python programming tips"}, "type": "note"},
        {"id": "test-2", "data": {"note": "Machine learning basics"}, "type": "note"},
        {"id": "test-3", "data": {"note": "Docker containerization"}, "type": "note"}
    ]
    
    for memory in test_memories:
        payload = {**memory, "context": "test", "priority": "normal", "intent": "note"}
        response = test_client.post("/ingest", json=payload, headers=auth_header)
        assert response.status_code == 200
    
    # Now search for content
    response = test_client.get(
        "/search",
        params={"q": "programming"},
        headers=auth_header
    )
    
    assert response.status_code == 200
    results = response.json()
    
    # Verify search behavior
    assert isinstance(results, list)
    assert len(results) > 0
    
    # Verify OpenAI was called for query embedding
    assert mock_openai_client.embeddings.create.call_count >= 4  # 3 ingests + 1 search
    
    # Verify Qdrant search was called
    mock_qdrant_client.search.assert_called()


@pytest.mark.asyncio
async def test_health_check_with_mocked_services(
    test_client: TestClient,
    auth_header: dict,
    mock_postgres_client,
    mock_qdrant_client
):
    """Test health check endpoint with mocked services"""
    
    response = test_client.get("/health", headers=auth_header)
    
    assert response.status_code == 200
    health_data = response.json()
    
    # Verify health check structure
    assert health_data["status"] == "healthy"
    assert "postgres" in health_data
    assert "qdrant" in health_data
    
    # Verify PostgreSQL health was checked
    mock_postgres_client.health_check.assert_called()
    
    # Verify mocked health values
    assert health_data["postgres"]["status"] == "healthy"
    assert health_data["postgres"]["pool_size"] == 20
    assert health_data["postgres"]["cache_hit_ratio"] == 0.85


@pytest.mark.asyncio
async def test_error_handling_with_service_failures(
    test_client: TestClient,
    auth_header: dict,
    sample_payload_dict: dict,
    mock_postgres_client,
    mock_openai_client
):
    """Test that the app handles external service failures gracefully"""
    
    # Simulate OpenAI failure
    mock_openai_client.embeddings.create.side_effect = Exception("OpenAI API error")
    
    # The app should still succeed (graceful degradation)
    response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Reset OpenAI mock
    mock_openai_client.embeddings.create.side_effect = None
    
    # Simulate PostgreSQL failure
    mock_postgres_client.store_memory.side_effect = Exception("Database connection error")
    
    # The app should still succeed (background storage failure)
    response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_mock_data_persistence(
    test_client: TestClient,
    auth_header: dict,
    sample_payload_dict: dict,
    mock_postgres_client
):
    """Test that mock data persists within a test session"""
    
    # Store a memory
    response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
    assert response.status_code == 200
    
    # Get the memory ID from the mock
    memory_id = mock_postgres_client.store_memory.return_value
    
    # Verify we can retrieve it
    stored_memory = await mock_postgres_client.get_memory(memory_id)
    assert stored_memory is not None
    assert stored_memory['text_content'] == sample_payload_dict['data']['note']
    
    # Search should find it
    search_results = await mock_postgres_client.search_memories(
        query_text=sample_payload_dict['data']['note'][:10]
    )
    assert len(search_results) > 0


def test_verify_no_real_api_calls(verify_no_external_calls):
    """Ensure that no real external API calls are made during tests"""
    
    # This test verifies that our mocking is properly set up
    # and no actual external service calls are made
    verify_no_external_calls()


@pytest.mark.parametrize("service", ["postgres", "qdrant", "openai"])
def test_individual_service_mocking(service, mock_postgres_client, mock_qdrant_client, mock_openai_client):
    """Test that each service can be mocked independently"""
    
    if service == "postgres":
        # Verify PostgreSQL mock works
        assert mock_postgres_client._initialized is True
        assert hasattr(mock_postgres_client, 'store_memory')
        assert hasattr(mock_postgres_client, 'search_memories')
        
    elif service == "qdrant":
        # Verify Qdrant mock works
        assert hasattr(mock_qdrant_client, 'upsert')
        assert hasattr(mock_qdrant_client, 'search')
        
    elif service == "openai":
        # Verify OpenAI mock works
        assert hasattr(mock_openai_client, 'embeddings')
        assert hasattr(mock_openai_client.embeddings, 'create')
        
        # Test embedding generation
        result = mock_openai_client.embeddings.create(input="test text")
        assert len(result.data) == 1
        assert len(result.data[0].embedding) == 1536 