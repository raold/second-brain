# tests/test_refactored_functions.py

from unittest.mock import AsyncMock, Mock, patch

import pytest


# Test the refactored qdrant_client functions
class TestQdrantClientRefactored:
    
    def test_validate_payload_structure_valid(self):
        """Test payload validation with valid payload"""
        from app.storage.qdrant_client import _validate_payload_structure
        
        valid_payload = {
            "id": "test-123",
            "data": {"note": "Test note"}
        }
        
        # Should not raise any exception
        _validate_payload_structure(valid_payload)
    
    def test_validate_payload_structure_invalid_type(self):
        """Test payload validation with invalid type"""
        from app.storage.qdrant_client import _validate_payload_structure
        
        with pytest.raises(ValueError, match="Payload must be a dictionary"):
            _validate_payload_structure("invalid")
    
    def test_validate_payload_structure_missing_id(self):
        """Test payload validation with missing ID"""
        from app.storage.qdrant_client import _validate_payload_structure
        
        invalid_payload = {"data": {"note": "Test note"}}
        
        with pytest.raises(ValueError, match="Payload must contain 'id' field"):
            _validate_payload_structure(invalid_payload)
    
    def test_validate_payload_structure_missing_note(self):
        """Test payload validation with missing note"""
        from app.storage.qdrant_client import _validate_payload_structure
        
        invalid_payload = {"id": "test-123", "data": {}}
        
        with pytest.raises(ValueError, match="Payload must contain 'data.note' field"):
            _validate_payload_structure(invalid_payload)
    
    @patch('app.storage.qdrant_client.get_openai_client')
    @patch('app.storage.qdrant_client.get_openai_embedding')
    def test_generate_embedding_for_payload_success(self, mock_embedding, mock_client):
        """Test successful embedding generation"""
        from app.storage.qdrant_client import _generate_embedding_for_payload
        
        mock_client.return_value = Mock()
        mock_embedding.return_value = [0.1, 0.2, 0.3]
        
        payload = {"data": {"note": "Test note"}}
        result = _generate_embedding_for_payload(payload)
        
        assert result == [0.1, 0.2, 0.3]
        mock_embedding.assert_called_once()
    
    def test_generate_embedding_for_payload_invalid_note(self):
        """Test embedding generation with invalid note"""
        from app.storage.qdrant_client import _generate_embedding_for_payload
        
        payload = {"data": {"note": ""}}
        
        with pytest.raises(ValueError, match="Note text must be a non-empty string"):
            _generate_embedding_for_payload(payload)
    
    @patch('app.storage.qdrant_client.client')
    def test_get_version_history_existing(self, mock_client):
        """Test retrieving existing version history"""
        from app.storage.qdrant_client import _get_version_history
        
        mock_point = Mock()
        mock_point.payload = {
            "meta": {
                "version_history": [
                    {"embedding_model": "old-model", "timestamp": "2023-01-01"}
                ]
            }
        }
        mock_client.retrieve.return_value = [mock_point]
        
        result = _get_version_history("test-id")
        
        assert len(result) == 1
        assert result[0]["embedding_model"] == "old-model"
    
    @patch('app.storage.qdrant_client.client')
    def test_get_version_history_not_found(self, mock_client):
        """Test retrieving version history when record not found"""
        from qdrant_client.http.exceptions import UnexpectedResponse

        from app.storage.qdrant_client import _get_version_history
        
        mock_client.retrieve.side_effect = UnexpectedResponse(
            status_code=404,
            reason_phrase="Not Found", 
            content="Not found",
            headers={}
        )
        
        result = _get_version_history("test-id")
        
        assert result == []
    
    @patch('app.storage.qdrant_client._get_version_history')
    def test_update_payload_metadata(self, mock_history):
        """Test payload metadata update"""
        from app.storage.qdrant_client import _update_payload_metadata
        
        mock_history.return_value = [{"old": "history"}]
        
        payload = {"id": "test-123"}
        _update_payload_metadata(payload)
        
        assert "meta" in payload
        assert "embedding_model" in payload["meta"]
        assert "model_version" in payload["meta"]
        assert "timestamp" in payload["meta"]
        assert "version_history" in payload["meta"]
        assert len(payload["meta"]["version_history"]) == 2  # old + new
    
    def test_create_qdrant_point(self):
        """Test Qdrant point creation"""
        from app.storage.qdrant_client import _create_qdrant_point
        
        payload = {"id": "test-123", "data": {"note": "test"}}
        embedding = [0.1, 0.2, 0.3]
        
        point = _create_qdrant_point(payload, embedding)
        
        assert point.vector == embedding
        assert point.payload == payload
    
    @patch('app.storage.qdrant_client.client')
    @patch('app.storage.qdrant_client._search_cache')
    def test_perform_upsert(self, mock_cache, mock_client):
        """Test upsert operation"""
        from app.storage.qdrant_client import _perform_upsert
        
        mock_point = Mock()
        _perform_upsert(mock_point)
        
        mock_client.upsert.assert_called_once()
        mock_cache.clear.assert_called_once()


# Test the refactored openai_client functions
class TestOpenAIClientRefactored:
    
    def test_validate_embedding_input_valid(self):
        """Test input validation with valid text"""
        from app.utils.openai_client import _validate_embedding_input
        
        # Should not raise any exception
        _validate_embedding_input("Valid test text")
    
    def test_validate_embedding_input_empty(self):
        """Test input validation with empty text"""
        from app.utils.openai_client import _validate_embedding_input
        
        with pytest.raises(ValueError, match="Text must be a non-empty string"):
            _validate_embedding_input("")
    
    def test_validate_embedding_input_whitespace(self):
        """Test input validation with whitespace only"""
        from app.utils.openai_client import _validate_embedding_input
        
        with pytest.raises(ValueError, match="Text cannot be empty or whitespace only"):
            _validate_embedding_input("   ")
    
    def test_preprocess_text_for_embedding_short(self):
        """Test text preprocessing with short text"""
        from app.utils.openai_client import _preprocess_text_for_embedding
        
        text = "Short text"
        result = _preprocess_text_for_embedding(text)
        
        assert result == text
    
    @patch('app.utils.openai_client.logger')
    def test_preprocess_text_for_embedding_long(self, mock_logger):
        """Test text preprocessing with long text that needs truncation"""
        from app.utils.openai_client import _preprocess_text_for_embedding
        
        long_text = "a" * 10000  # Longer than 8192 limit
        result = _preprocess_text_for_embedding(long_text)
        
        assert len(result) == 8192
        mock_logger.warning.assert_called_once()
    
    @patch('openai.embeddings.create')
    def test_call_openai_embedding_api_success(self, mock_create):
        """Test successful OpenAI API call"""
        from app.utils.openai_client import _call_openai_embedding_api
        
        mock_client = Mock()
        mock_client.embeddings.create.return_value = "response"
        
        result = _call_openai_embedding_api("test text", mock_client)
        
        assert result == "response"
    
    def test_validate_embedding_response_valid(self):
        """Test response validation with valid response"""
        from app.utils.openai_client import _validate_embedding_response
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2] + [0.0] * 1534)]  # 1536 total
        
        result = _validate_embedding_response(mock_response)
        
        assert len(result) == 1536
        assert result[0] == 0.1
    
    def test_validate_embedding_response_no_data(self):
        """Test response validation with no data"""
        from app.utils.openai_client import _validate_embedding_response
        
        mock_response = Mock()
        mock_response.data = []
        
        with pytest.raises(ValueError, match="No embedding data in response"):
            _validate_embedding_response(mock_response)
    
    def test_validate_embedding_response_invalid_format(self):
        """Test response validation with invalid embedding format"""
        from app.utils.openai_client import _validate_embedding_response
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding="invalid")]
        
        with pytest.raises(ValueError, match="Invalid embedding format in response"):
            _validate_embedding_response(mock_response)


# Test the refactored router functions
class TestRouterRefactored:
    
    @patch('app.router.detect_intent_via_llm')
    @pytest.mark.asyncio
    async def test_detect_or_assign_intent_missing(self, mock_detect):
        """Test intent detection when not provided"""
        from app.models import Payload, PayloadType, Priority
        from app.router import _detect_or_assign_intent
        
        mock_detect.return_value = "detected_intent"
        
        payload = Payload(
            id="test",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={"note": "Test note"},
            meta={}
        )
        
        await _detect_or_assign_intent(payload)
        
        assert payload.intent == "detected_intent"
        assert payload.meta["intent"] == "detected_intent"
    
    @pytest.mark.asyncio
    async def test_detect_or_assign_intent_existing(self):
        """Test intent detection when already provided"""
        from app.models import Payload, PayloadType, Priority
        from app.router import _detect_or_assign_intent
        
        payload = Payload(
            id="test",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={"note": "Test note"},
            meta={},
            intent="existing_intent"
        )
        
        await _detect_or_assign_intent(payload)
        
        assert payload.intent == "existing_intent"
    
    @patch('app.router.write_markdown')
    @patch('app.router.qdrant_upsert')
    def test_perform_storage_operations(self, mock_qdrant, mock_markdown):
        """Test storage operations"""

        from app.models import Payload, PayloadType, Priority
        from app.router import _perform_storage_operations
        
        payload = Payload(
            id="test",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={"note": "Test note"},
            meta={}
        )
        
        background_tasks = Mock()
        
        _perform_storage_operations(payload, background_tasks)
        
        mock_markdown.assert_called_once_with(payload)
        mock_qdrant.assert_called_once()
        background_tasks.add_task.assert_called_once()
    
    def test_build_ingest_response(self):
        """Test ingest response building"""
        from app.models import Payload, PayloadType, Priority
        from app.router import _build_ingest_response
        
        payload = Payload(
            id="test-123",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={"note": "Test note"},
            meta={},
            intent="test_intent"
        )
        
        result = _build_ingest_response(payload)
        
        assert result["status"] == "ingested"
        assert result["id"] == "test-123"
        assert result["intent"] == "test_intent"
    
    def test_rank_and_score_results(self):
        """Test result ranking and scoring"""
        from app.router import _rank_and_score_results
        
        results = [
            {"score": 0.8, "id": "1"},
            {"score": 0.9, "id": "2"}
        ]
        filters = {"model_version": "v1"}
        
        with patch('app.router._score_and_explain_result') as mock_score:
            mock_score.side_effect = [
                {"final_score": 0.85, "id": "1"},
                {"final_score": 0.95, "id": "2"}
            ]
            
            ranked = _rank_and_score_results(results, filters)
            
            assert len(ranked) == 2
            assert ranked[0]["id"] == "2"  # Higher score first
            assert ranked[1]["id"] == "1"
    
    def test_build_ranked_search_response(self):
        """Test ranked search response building"""
        from app.router import _build_ranked_search_response
        
        query = "test query"
        results = [{"id": "1", "score": 0.9}]
        
        response = _build_ranked_search_response(query, results)
        
        assert response["query"] == query
        assert response["results"] == results


# Test the refactored websocket functions
class TestWebSocketRefactored:
    
    def test_parse_websocket_request_batch(self):
        """Test parsing request with batch"""
        from app.api.websocket import _parse_websocket_request
        
        data = {
            "batch": [{"id": "1", "prompt": "test"}],
            "json": True
        }
        
        batch, stream_json = _parse_websocket_request(data)
        
        assert batch == [{"id": "1", "prompt": "test"}]
        assert stream_json is True
    
    def test_parse_websocket_request_single_prompt(self):
        """Test parsing request with single prompt"""
        from app.api.websocket import _parse_websocket_request
        
        data = {"prompt": "test prompt", "json": False}
        
        batch, stream_json = _parse_websocket_request(data)
        
        assert len(batch) == 1
        assert batch[0]["prompt"] == "test prompt"
        assert batch[0]["type"] == "llm"
        assert stream_json is False
    
    def test_parse_websocket_request_missing_prompt(self):
        """Test parsing request with missing prompt"""
        from app.api.websocket import _parse_websocket_request
        
        data = {"json": True}
        
        batch, stream_json = _parse_websocket_request(data)
        
        assert batch is None
        assert stream_json is True
    
    @pytest.mark.asyncio
    async def test_process_batch_items_llm(self):
        """Test processing batch items with LLM type"""
        from app.api.websocket import _process_batch_items
        
        batch = [{"id": "1", "type": "llm", "prompt": "test"}]
        mock_websocket = Mock()
        
        with patch('app.api.websocket.process_llm_item') as mock_process:
            await _process_batch_items(batch, mock_websocket, True)
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_batch_items_unknown_type(self):
        """Test processing batch items with unknown type"""
        from app.api.websocket import _process_batch_items
        
        batch = [{"id": "1", "type": "unknown"}]
        mock_websocket = AsyncMock()
        
        await _process_batch_items(batch, mock_websocket, True)
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert "error" in call_args
        assert "Unknown type" in call_args["error"]


# Test the refactored handlers functions
class TestHandlersRefactored:
    
    @patch('app.handlers.Path')
    def test_write_to_markdown_file_success(self, mock_path):
        """Test successful markdown file writing"""
        from app.handlers import _write_to_markdown_file
        
        mock_file = Mock()
        mock_path.return_value.__truediv__.return_value.open.return_value.__enter__.return_value = mock_file
        
        result = _write_to_markdown_file("test.md", "content")
        
        assert result is True
        mock_file.write.assert_called_once_with("content")
    
    @patch('app.handlers.Path')
    def test_write_to_markdown_file_failure(self, mock_path):
        """Test markdown file writing failure"""
        from app.handlers import _write_to_markdown_file
        
        mock_path.side_effect = Exception("File error")
        
        result = _write_to_markdown_file("test.md", "content")
        
        assert result is False


# Test the refactored qdrant filter functions
class TestQdrantFilterRefactored:
    
    def test_parse_timestamp_range_both(self):
        """Test parsing timestamp range with both from and to"""
        from app.storage.qdrant_client import _parse_timestamp_range
        
        timestamp_filter = {
            "from": "2023-01-01T00:00:00Z",
            "to": "2023-12-31T23:59:59Z"
        }
        
        result = _parse_timestamp_range(timestamp_filter)
        
        assert "gte" in result
        assert "lte" in result
        assert isinstance(result["gte"], int)
        assert isinstance(result["lte"], int)
    
    def test_parse_timestamp_range_invalid(self):
        """Test parsing invalid timestamp range"""
        from app.storage.qdrant_client import _parse_timestamp_range
        
        timestamp_filter = {"from": "invalid-date"}
        
        with patch('app.storage.qdrant_client.logger') as mock_logger:
            result = _parse_timestamp_range(timestamp_filter)
            
            assert result == {}
            mock_logger.warning.assert_called_once()
    
    def test_add_field_condition(self):
        """Test adding field condition"""
        from app.storage.qdrant_client import _add_field_condition
        
        must = []
        _add_field_condition(must, "test.field", "test_value")
        
        assert len(must) == 1
        assert must[0].key == "test.field"
    
    def test_add_timestamp_condition(self):
        """Test adding timestamp condition"""
        from app.storage.qdrant_client import _add_timestamp_condition
        
        must = []
        timestamp_filter = {"from": "2023-01-01T00:00:00Z"}
        
        with patch('app.storage.qdrant_client._parse_timestamp_range') as mock_parse:
            mock_parse.return_value = {"gte": 1672531200}
            
            _add_timestamp_condition(must, timestamp_filter)
            
            assert len(must) == 1
    
    def test_build_qdrant_filter_comprehensive(self):
        """Test building comprehensive Qdrant filter"""
        from app.storage.qdrant_client import _build_qdrant_filter
        
        filters = {
            "model_version": "v1",
            "embedding_model": "text-embedding-3-small",
            "type": "note",
            "timestamp": {"from": "2023-01-01T00:00:00Z"}
        }
        
        # Test the actual functionality without mocking internal calls
        result = _build_qdrant_filter(filters)
        
        # Should return a Filter object when filters are provided
        assert result is not None
        assert hasattr(result, 'must')
        assert len(result.must) == 4  # 3 field conditions + 1 timestamp condition 