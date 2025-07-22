"""
Tests for the pagination system.
"""

import pytest
import json
import base64
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
from app.pagination import (
    CursorPaginator,
    KeysetPaginator,
    StreamingPaginator,
    PaginationParams,
    PaginationDirection,
    Cursor,
    KeysetCursor
)
from app.pagination.utils import (
    PaginationHelper,
    extract_pagination_params,
    build_pagination_url,
    create_page_urls,
    merge_pagination_results,
    create_offset_response
)
from app.pagination.models import (
    CursorData,
    PageInfo,
    PaginationMetadata,
    PaginatedResponse
)


class TestCursorPagination:
    """Test cursor-based pagination."""
    
    def test_cursor_encoding_decoding(self):
        """Test cursor encoding and decoding."""
        # Create a cursor
        cursor = Cursor(
            item_id="123",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            sort_value=99.5
        )
        
        # Encode
        encoded = cursor.encode()
        assert isinstance(encoded, str)
        
        # Decode
        decoded = Cursor.decode(encoded)
        assert decoded.item_id == "123"
        assert decoded.timestamp == datetime(2024, 1, 15, 10, 0, 0)
        assert decoded.sort_value == 99.5
    
    def test_cursor_data_model(self):
        """Test CursorData model."""
        data = CursorData(
            id="456",
            timestamp=datetime.now(),
            sort_value="test"
        )
        
        # Test encoding
        encoded = data.encode()
        assert isinstance(encoded, str)
        
        # Test decoding
        decoded = CursorData.decode(encoded)
        assert decoded.id == data.id
        assert decoded.timestamp == data.timestamp
        assert decoded.sort_value == data.sort_value
    
    @pytest.mark.asyncio
    async def test_cursor_paginator(self):
        """Test cursor paginator functionality."""
        paginator = CursorPaginator(
            id_column="id",
            timestamp_column="created_at",
            default_limit=10
        )
        
        # Mock database
        mock_db = AsyncMock()
        mock_rows = [
            {"id": str(i), "created_at": datetime.now(), "content": f"Item {i}"}
            for i in range(15)
        ]
        mock_db.fetch.return_value = mock_rows[:11]  # Return 11 to check has_more
        
        # Test pagination
        params = PaginationParams(limit=10)
        result = await paginator.paginate_query(
            db=mock_db,
            base_query="SELECT * FROM items",
            params=params
        )
        
        assert len(result.items) == 10
        assert result.has_next is True
        assert result.has_previous is False
        assert result.start_cursor is not None
        assert result.end_cursor is not None
    
    def test_build_paginated_query(self):
        """Test building paginated queries."""
        paginator = CursorPaginator()
        
        # Test forward pagination
        query, params = paginator._build_paginated_query(
            base_query="SELECT * FROM items WHERE active = true",
            cursor=None,
            direction=PaginationDirection.FORWARD,
            limit=50,
            sort_column="score",
            sort_order="desc",
            query_params=[True]
        )
        
        assert "ORDER BY score DESC" in query
        assert "LIMIT %s" in query
        assert params == [True, 50]
    
    def test_cursor_with_custom_sort(self):
        """Test cursor with custom sort column."""
        paginator = CursorPaginator()
        
        row = {
            "id": "123",
            "created_at": datetime.now(),
            "score": 95.5
        }
        
        cursor_str = paginator.create_cursor_from_item(row, sort_column="score")
        cursor = Cursor.decode(cursor_str)
        
        assert cursor.item_id == "123"
        assert cursor.sort_value == 95.5


class TestKeysetPagination:
    """Test keyset pagination."""
    
    def test_keyset_cursor(self):
        """Test keyset cursor functionality."""
        cursor = KeysetCursor(columns={
            "created_at": datetime(2024, 1, 15),
            "id": "123"
        })
        
        # Test conversion
        assert cursor.to_dict() == {
            "created_at": datetime(2024, 1, 15),
            "id": "123"
        }
        
        # Test where clause generation
        where, params = cursor.to_where_clause(
            direction=PaginationDirection.FORWARD
        )
        
        assert where
        assert len(params) == 3  # created_at once, id once, and created_at again
    
    @pytest.mark.asyncio
    async def test_keyset_paginator(self):
        """Test keyset paginator."""
        paginator = KeysetPaginator(
            key_columns=["created_at", "id"],
            default_limit=20
        )
        
        # Mock database
        mock_db = AsyncMock()
        mock_rows = [
            {"id": str(i), "created_at": datetime.now()}
            for i in range(25)
        ]
        mock_db.fetch.return_value = mock_rows[:21]
        
        # Test pagination
        params = PaginationParams(limit=20)
        result = await paginator.paginate_query(
            db=mock_db,
            base_query="SELECT * FROM items",
            params=params
        )
        
        assert len(result.items) == 20
        assert result.has_next is True
        assert result.first_keyset is not None
        assert result.last_keyset is not None
    
    def test_multi_column_keyset(self):
        """Test multi-column keyset conditions."""
        cursor = KeysetCursor(columns={
            "score": 95.5,
            "created_at": datetime(2024, 1, 15),
            "id": "123"
        })
        
        where, params = cursor.to_where_clause(
            direction=PaginationDirection.FORWARD,
            table_alias="t"
        )
        
        # Should generate proper multi-column comparison
        assert "t.score" in where
        assert "t.created_at" in where
        assert "t.id" in where
        assert len(params) == 6  # Each column appears twice in the nested conditions


class TestStreamingPagination:
    """Test streaming pagination."""
    
    @pytest.mark.asyncio
    async def test_stream_query(self):
        """Test streaming query results."""
        paginator = StreamingPaginator(chunk_size=10)
        
        # Mock database with cursor support
        mock_db = AsyncMock()
        mock_db.transaction = MagicMock()
        mock_db.execute = AsyncMock()
        
        # Mock fetch results
        mock_rows = [
            {"id": str(i), "content": f"Item {i}"}
            for i in range(25)
        ]
        
        # Simulate fetching in chunks
        mock_db.fetch = AsyncMock(side_effect=[
            mock_rows[:10],
            mock_rows[10:20],
            mock_rows[20:25],
            []  # Empty result to end streaming
        ])
        
        # Stream results
        chunks = []
        async for chunk in paginator.stream_query(
            db=mock_db,
            query="SELECT * FROM items"
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5
    
    @pytest.mark.asyncio
    async def test_stream_to_json(self):
        """Test streaming to JSON format."""
        paginator = StreamingPaginator(chunk_size=5)
        
        # Mock simple generator
        async def mock_stream_query(*args, **kwargs):
            yield [{"id": "1", "name": "Item 1"}]
            yield [{"id": "2", "name": "Item 2"}]
        
        paginator.stream_query = mock_stream_query
        
        # Collect JSON output
        output = []
        async for chunk in paginator.stream_to_json(None, ""):
            output.append(chunk)
        
        json_str = "".join(output)
        assert json_str.startswith("[")
        assert json_str.endswith("]")
        assert '"id": "1"' in json_str
        assert '"id": "2"' in json_str
    
    @pytest.mark.asyncio
    async def test_stream_to_csv(self):
        """Test streaming to CSV format."""
        paginator = StreamingPaginator(chunk_size=5)
        
        # Mock generator
        async def mock_stream_query(*args, **kwargs):
            yield [
                {"id": "1", "name": "Item 1", "score": 95},
                {"id": "2", "name": "Item 2", "score": 87}
            ]
        
        paginator.stream_query = mock_stream_query
        
        # Collect CSV output
        output = []
        async for chunk in paginator.stream_to_csv(None, ""):
            output.append(chunk)
        
        csv_str = "".join(output)
        lines = csv_str.strip().split("\n")
        
        assert len(lines) == 3  # Header + 2 data rows
        assert "id,name,score" in lines[0]
        assert "1,Item 1,95" in lines[1]
        assert "2,Item 2,87" in lines[2]


class TestPaginationUtils:
    """Test pagination utility functions."""
    
    def test_extract_pagination_params(self):
        """Test extracting pagination parameters."""
        query_params = {
            "limit": "25",
            "cursor": "abc123",
            "direction": "backward",
            "sort_by": "score",
            "sort_order": "asc",
            "include_total": "true"
        }
        
        params = extract_pagination_params(query_params)
        
        assert params.limit == 25
        assert params.cursor == "abc123"
        assert params.direction == "backward"
        assert params.sort_by == "score"
        assert params.sort_order == "asc"
        assert params.include_total is True
    
    def test_build_pagination_url(self):
        """Test building pagination URLs."""
        url = build_pagination_url(
            base_url="https://api.example.com/memories",
            cursor="xyz789",
            direction="forward",
            limit=50,
            sort_by="created_at"
        )
        
        assert "cursor=xyz789" in url
        assert "direction=forward" in url
        assert "limit=50" in url
        assert "sort_by=created_at" in url
    
    def test_create_page_urls(self):
        """Test creating navigation URLs."""
        page_info = PageInfo(
            has_next_page=True,
            has_previous_page=True,
            start_cursor="start123",
            end_cursor="end456"
        )
        
        urls = create_page_urls(
            base_url="https://api.example.com/memories",
            page_info=page_info,
            limit=25
        )
        
        assert urls["first"] is not None
        assert urls["next"] is not None
        assert urls["previous"] is not None
        assert "cursor=end456" in urls["next"]
        assert "cursor=start123" in urls["previous"]
        assert "direction=forward" in urls["next"]
        assert "direction=backward" in urls["previous"]
    
    def test_merge_pagination_results(self):
        """Test merging paginated results."""
        # Create mock responses
        response1 = PaginatedResponse(
            data=[{"id": "1"}, {"id": "2"}],
            pagination=PaginationMetadata(
                page_info=PageInfo(
                    has_next_page=True,
                    has_previous_page=False,
                    start_cursor="start1",
                    end_cursor="end1"
                ),
                page_size=2,
                query_time_ms=10.0
            )
        )
        
        response2 = PaginatedResponse(
            data=[{"id": "3"}, {"id": "4"}],
            pagination=PaginationMetadata(
                page_info=PageInfo(
                    has_next_page=False,
                    has_previous_page=True,
                    start_cursor="start2",
                    end_cursor="end2"
                ),
                page_size=2,
                query_time_ms=15.0
            )
        )
        
        # Merge
        merged = merge_pagination_results([response1, response2], limit=3)
        
        assert len(merged.data) == 3
        assert merged.pagination.page_size == 3
        assert merged.pagination.query_time_ms == 25.0
        assert merged.pagination.page_info.has_next_page is True
    
    def test_create_offset_response(self):
        """Test creating offset-based response."""
        items = [{"id": str(i)} for i in range(10)]
        
        response = create_offset_response(
            items=items,
            total_count=100,
            limit=10,
            offset=20,
            query_time_ms=5.5,
            base_url="https://api.example.com/items"
        )
        
        assert len(response.data) == 10
        assert response.pagination.total_count == 100
        assert response.pagination.page_info.has_next_page is True
        assert response.pagination.page_info.has_previous_page is True
        assert "offset=30" in response.pagination.next_page_url
        assert "offset=10" in response.pagination.previous_page_url
    
    @pytest.mark.asyncio
    async def test_pagination_helper(self):
        """Test PaginationHelper class."""
        helper = PaginationHelper(default_limit=25)
        
        # Mock database
        mock_db = AsyncMock()
        mock_rows = [
            {"id": str(i), "created_at": datetime.now()}
            for i in range(30)
        ]
        mock_db.fetch.return_value = mock_rows[:26]
        mock_db.fetchval.return_value = 100
        
        # Test with cursor
        params = PaginationParams(
            limit=25,
            cursor="test_cursor"
        )
        
        response = await helper.paginate(
            db=mock_db,
            query="SELECT * FROM items",
            params=params,
            count_query="SELECT COUNT(*) FROM items",
            base_url="https://api.example.com/items"
        )
        
        assert isinstance(response, PaginatedResponse)
        assert response.pagination.page_size == 25
        
        # Test with offset fallback
        params_offset = {"limit": 10, "offset": 20}
        response_offset = await helper.paginate(
            db=mock_db,
            query="SELECT * FROM items",
            params=params_offset
        )
        
        assert isinstance(response_offset, PaginatedResponse)