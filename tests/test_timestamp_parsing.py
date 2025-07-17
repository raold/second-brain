"""
Test timestamp parsing for Qdrant Range validation.
"""

import pytest
from datetime import datetime, timezone

from app.storage.qdrant_client import _parse_timestamp_to_unix, _build_qdrant_filter


class TestTimestampParsing:
    """Test timestamp parsing and Range validation fixes."""
    
    def test_parse_utc_timestamp(self):
        """Test parsing UTC timestamp with Z suffix"""
        timestamp = "2023-01-01T00:00:00Z"
        result = _parse_timestamp_to_unix(timestamp)
        
        # Should convert to Unix timestamp
        expected = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
        assert result == expected
    
    def test_parse_timezone_aware_timestamp(self):
        """Test parsing timestamp with timezone offset"""
        timestamp = "2023-01-01T00:00:00+05:00"
        result = _parse_timestamp_to_unix(timestamp)
        
        # Should handle timezone conversion
        expected = datetime.fromisoformat(timestamp).timestamp()
        assert result == expected
    
    def test_parse_no_timezone_timestamp(self):
        """Test parsing timestamp without timezone (assumes UTC)"""
        timestamp = "2023-01-01T00:00:00"
        result = _parse_timestamp_to_unix(timestamp)
        
        # Should assume UTC
        expected = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
        assert result == expected
    
    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp"""
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            _parse_timestamp_to_unix("invalid-timestamp")
    
    def test_build_filter_with_valid_timestamps(self):
        """Test building Qdrant filter with valid timestamp range"""
        filters = {
            "timestamp": {
                "from": "2023-01-01T00:00:00Z",
                "to": "2023-12-31T23:59:59Z"
            }
        }
        
        result = _build_qdrant_filter(filters)
        
        # Should create a valid filter
        assert result is not None
        assert hasattr(result, 'must')
        assert len(result.must) == 1
        
        condition = result.must[0]
        assert condition.key == "meta.timestamp"
        assert hasattr(condition, 'range')
        
        # Range values should be Unix timestamps (floats)
        assert isinstance(condition.range.gte, float)
        assert isinstance(condition.range.lte, float)
        assert condition.range.gte < condition.range.lte
    
    def test_build_filter_with_invalid_from_timestamp(self):
        """Test building filter with invalid 'from' timestamp"""
        filters = {
            "timestamp": {
                "from": "invalid-date",
                "to": "2023-12-31T23:59:59Z"
            }
        }
        
        # Should handle gracefully (log warning and skip invalid timestamp)
        result = _build_qdrant_filter(filters)
        
        # Should still create filter for valid 'to' timestamp
        assert result is not None
        condition = result.must[0]
        assert hasattr(condition.range, 'lte')
        assert not hasattr(condition.range, 'gte')  # Invalid 'from' should be skipped
    
    def test_build_filter_with_invalid_to_timestamp(self):
        """Test building filter with invalid 'to' timestamp"""
        filters = {
            "timestamp": {
                "from": "2023-01-01T00:00:00Z",
                "to": "invalid-date"
            }
        }
        
        # Should handle gracefully
        result = _build_qdrant_filter(filters)
        
        # Should still create filter for valid 'from' timestamp
        assert result is not None
        condition = result.must[0]
        assert hasattr(condition.range, 'gte')
        assert not hasattr(condition.range, 'lte')  # Invalid 'to' should be skipped
    
    def test_build_filter_with_both_invalid_timestamps(self):
        """Test building filter when both timestamps are invalid"""
        filters = {
            "timestamp": {
                "from": "invalid-from",
                "to": "invalid-to"
            }
        }
        
        # Should return None since no valid conditions
        result = _build_qdrant_filter(filters)
        assert result is None
    
    def test_build_filter_with_from_only(self):
        """Test building filter with only 'from' timestamp"""
        filters = {
            "timestamp": {
                "from": "2023-01-01T00:00:00Z"
            }
        }
        
        result = _build_qdrant_filter(filters)
        assert result is not None
        condition = result.must[0]
        assert hasattr(condition.range, 'gte')
        assert not hasattr(condition.range, 'lte')
    
    def test_build_filter_with_to_only(self):
        """Test building filter with only 'to' timestamp"""
        filters = {
            "timestamp": {
                "to": "2023-12-31T23:59:59Z"
            }
        }
        
        result = _build_qdrant_filter(filters)
        assert result is not None
        condition = result.must[0]
        assert hasattr(condition.range, 'lte')
        assert not hasattr(condition.range, 'gte')
    
    def test_build_filter_with_mixed_filters(self):
        """Test building filter with timestamp and other filters"""
        filters = {
            "timestamp": {
                "from": "2023-01-01T00:00:00Z",
                "to": "2023-12-31T23:59:59Z"
            },
            "type": "note",
            "tags": ["important", "work"]
        }
        
        result = _build_qdrant_filter(filters)
        assert result is not None
        assert len(result.must) == 3  # timestamp range + type + tags
        
        # Find the timestamp condition
        timestamp_condition = None
        for condition in result.must:
            if condition.key == "meta.timestamp":
                timestamp_condition = condition
                break
        
        assert timestamp_condition is not None
        assert isinstance(timestamp_condition.range.gte, float)
        assert isinstance(timestamp_condition.range.lte, float) 