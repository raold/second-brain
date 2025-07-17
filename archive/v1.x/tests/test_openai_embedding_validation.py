"""
Test OpenAI embedding validation and error handling improvements.
"""

import pytest
from unittest.mock import Mock, patch

from app.utils.openai_client import _validate_embedding_response, get_openai_embedding_with_fallback


class TestEmbeddingValidation:
    """Test the improved embedding validation logic."""
    
    def test_validate_none_response(self):
        """Test validation with None response"""
        with pytest.raises(ValueError, match="response is None"):
            _validate_embedding_response(None)
    
    def test_validate_missing_data_field(self):
        """Test validation when response has no data field"""
        mock_response = Mock(spec=[])  # No attributes
        with pytest.raises(ValueError, match="no 'data' field"):
            _validate_embedding_response(mock_response)
    
    def test_validate_none_data_field(self):
        """Test validation when data field is None"""
        mock_response = Mock()
        mock_response.data = None
        with pytest.raises(ValueError, match="data field is None or empty"):
            _validate_embedding_response(mock_response)
    
    def test_validate_empty_data_array(self):
        """Test validation when data array is empty"""
        mock_response = Mock()
        mock_response.data = []
        with pytest.raises(ValueError, match="data field is None or empty"):
            _validate_embedding_response(mock_response)
    
    def test_validate_missing_embedding_field(self):
        """Test validation when data[0] has no embedding field"""
        mock_response = Mock()
        mock_item = Mock(spec=[])  # No embedding attribute
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="no 'embedding' field"):
            _validate_embedding_response(mock_response)
    
    def test_validate_none_embedding(self):
        """Test validation when embedding is None"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = None
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="embedding field is None"):
            _validate_embedding_response(mock_response)
    
    def test_validate_non_list_embedding(self):
        """Test validation when embedding is not a list"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = "not a list"
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="embedding field is not a list"):
            _validate_embedding_response(mock_response)
    
    def test_validate_empty_embedding_list(self):
        """Test validation when embedding list is empty"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = []
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="embedding list is empty"):
            _validate_embedding_response(mock_response)
    
    def test_validate_wrong_dimensions(self):
        """Test validation when embedding has wrong dimensions"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = [0.1] * 100  # Wrong size
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="dimension mismatch"):
            _validate_embedding_response(mock_response)
    
    def test_validate_non_numeric_values(self):
        """Test validation when embedding contains non-numeric values"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = ["not", "numeric"] + [0.1] * 1534
        mock_response.data = [mock_item]
        with pytest.raises(ValueError, match="non-numeric values"):
            _validate_embedding_response(mock_response)
    
    def test_validate_success(self):
        """Test successful validation"""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = [0.1] * 1536  # Correct size
        mock_response.data = [mock_item]
        
        result = _validate_embedding_response(mock_response)
        assert len(result) == 1536
        assert all(x == 0.1 for x in result)
    
    @patch('app.utils.openai_client.get_openai_embedding')
    def test_embedding_with_fallback_success(self, mock_get_embedding):
        """Test fallback function with successful embedding"""
        mock_get_embedding.return_value = [0.1] * 1536
        
        result = get_openai_embedding_with_fallback("test text")
        assert result == [0.1] * 1536
        mock_get_embedding.assert_called_once_with("test text", None)
    
    @patch('app.utils.openai_client.get_openai_embedding')
    def test_embedding_with_fallback_failure(self, mock_get_embedding):
        """Test fallback function when embedding fails"""
        mock_get_embedding.side_effect = ValueError("Invalid response")
        
        result = get_openai_embedding_with_fallback("test text")
        assert result is None
        mock_get_embedding.assert_called_once_with("test text", None) 