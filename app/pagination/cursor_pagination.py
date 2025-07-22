"""
Cursor-based pagination implementation for efficient large dataset navigation.

This provides:
- Stable pagination that handles insertions/deletions
- Efficient queries using index-based cursors
- Bi-directional navigation
- No need for total count queries
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic, Callable
from datetime import datetime
import base64
import json

from app.pagination.models import (
    PaginationParams,
    PaginationMetadata,
    PageInfo,
    CursorData,
    PaginationDirection,
    PaginatedResponse
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Cursor:
    """Represents a cursor position in a dataset"""
    
    def __init__(self, 
                 item_id: str, 
                 timestamp: datetime,
                 sort_value: Any = None):
        self.item_id = item_id
        self.timestamp = timestamp
        self.sort_value = sort_value
    
    def encode(self) -> str:
        """Encode cursor to base64 string"""
        data = CursorData(
            id=self.item_id,
            timestamp=self.timestamp,
            sort_value=self.sort_value
        )
        return data.encode()
    
    @classmethod
    def decode(cls, cursor_str: str) -> 'Cursor':
        """Decode cursor from base64 string"""
        data = CursorData.decode(cursor_str)
        return cls(
            item_id=data.id,
            timestamp=data.timestamp,
            sort_value=data.sort_value
        )


class CursorPage(Generic[T]):
    """Represents a page of results with cursor information"""
    
    def __init__(self,
                 items: List[T],
                 has_next: bool,
                 has_previous: bool,
                 start_cursor: Optional[str] = None,
                 end_cursor: Optional[str] = None,
                 total_count: Optional[int] = None):
        self.items = items
        self.has_next = has_next
        self.has_previous = has_previous
        self.start_cursor = start_cursor
        self.end_cursor = end_cursor
        self.total_count = total_count
    
    def to_response(self, 
                    query_time_ms: Optional[float] = None,
                    base_url: Optional[str] = None) -> PaginatedResponse[T]:
        """Convert to standard paginated response"""
        page_info = PageInfo(
            has_next_page=self.has_next,
            has_previous_page=self.has_previous,
            start_cursor=self.start_cursor,
            end_cursor=self.end_cursor
        )
        
        metadata = PaginationMetadata(
            page_info=page_info,
            total_count=self.total_count,
            page_size=len(self.items),
            query_time_ms=query_time_ms
        )
        
        # Build navigation URLs if base URL provided
        if base_url:
            if self.has_next and self.end_cursor:
                metadata.next_page_url = f"{base_url}?cursor={self.end_cursor}&direction=forward"
            if self.has_previous and self.start_cursor:
                metadata.previous_page_url = f"{base_url}?cursor={self.start_cursor}&direction=backward"
        
        return PaginatedResponse(
            data=self.items,
            pagination=metadata
        )


class CursorPaginator:
    """
    Cursor-based paginator for PostgreSQL queries.
    
    Provides efficient pagination for large datasets by using
    indexed columns to create stable cursors.
    """
    
    def __init__(self,
                 id_column: str = "id",
                 timestamp_column: str = "created_at",
                 default_limit: int = 50,
                 max_limit: int = 1000):
        self.id_column = id_column
        self.timestamp_column = timestamp_column
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    async def paginate_query(self,
                           db: Any,
                           base_query: str,
                           params: PaginationParams,
                           count_query: Optional[str] = None,
                           query_params: Optional[List[Any]] = None,
                           item_mapper: Optional[Callable] = None) -> CursorPage[Dict[str, Any]]:
        """
        Paginate a query using cursor-based pagination.
        
        Args:
            db: Database connection
            base_query: Base SQL query (without ORDER BY or LIMIT)
            params: Pagination parameters
            count_query: Optional query to get total count
            query_params: Parameters for the base query
            item_mapper: Optional function to transform result rows
            
        Returns:
            CursorPage with results and pagination info
        """
        limit = min(params.limit or self.default_limit, self.max_limit)
        query_params = query_params or []
        
        # Decode cursor if provided
        cursor = None
        if params.cursor:
            try:
                cursor = Cursor.decode(params.cursor)
            except ValueError as e:
                logger.warning(f"Invalid cursor: {e}")
                # Continue without cursor on invalid input
        
        # Build the paginated query
        paginated_query, paginated_params = self._build_paginated_query(
            base_query=base_query,
            cursor=cursor,
            direction=params.direction,
            limit=limit + 1,  # Fetch one extra to check for more pages
            sort_column=params.sort_by,
            sort_order=params.sort_order,
            query_params=query_params
        )
        
        # Execute query
        start_time = datetime.now()
        rows = await db.fetch(paginated_query, *paginated_params)
        query_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Check if we have more pages
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]  # Remove the extra row
        
        # Map items if mapper provided
        if item_mapper:
            items = [item_mapper(row) for row in rows]
        else:
            items = [dict(row) for row in rows]
        
        # Determine pagination state
        if params.direction == PaginationDirection.BACKWARD:
            # Reverse items for backward pagination
            items.reverse()
            has_previous = has_more
            has_next = cursor is not None  # If we have a cursor, there are items after it
        else:
            has_next = has_more
            has_previous = cursor is not None  # If we have a cursor, there are items before it
        
        # Generate cursors
        start_cursor = None
        end_cursor = None
        
        if items:
            # Get cursor fields from first and last items
            first_item = rows[0] if params.direction == PaginationDirection.FORWARD else rows[-1]
            last_item = rows[-1] if params.direction == PaginationDirection.FORWARD else rows[0]
            
            start_cursor = self._create_cursor(first_item, params.sort_by).encode()
            end_cursor = self._create_cursor(last_item, params.sort_by).encode()
        
        # Get total count if requested
        total_count = None
        if params.include_total and count_query:
            total_count = await db.fetchval(count_query, *query_params)
        
        return CursorPage(
            items=items,
            has_next=has_next,
            has_previous=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=total_count
        )
    
    def _build_paginated_query(self,
                              base_query: str,
                              cursor: Optional[Cursor],
                              direction: PaginationDirection,
                              limit: int,
                              sort_column: Optional[str],
                              sort_order: str,
                              query_params: List[Any]) -> Tuple[str, List[Any]]:
        """Build the paginated query with cursor conditions"""
        
        # Determine sort column and order
        sort_col = sort_column or self.timestamp_column
        
        # Build cursor condition
        cursor_condition = ""
        cursor_params = []
        
        if cursor:
            if direction == PaginationDirection.FORWARD:
                if sort_column:
                    # Custom sort column with ID tiebreaker
                    cursor_condition = f"""
                        AND ({sort_col}, {self.id_column}) > (%s, %s)
                    """
                    cursor_params = [cursor.sort_value, cursor.item_id]
                else:
                    # Default: timestamp with ID tiebreaker
                    cursor_condition = f"""
                        AND ({self.timestamp_column}, {self.id_column}) > (%s, %s)
                    """
                    cursor_params = [cursor.timestamp, cursor.item_id]
            else:  # BACKWARD
                if sort_column:
                    cursor_condition = f"""
                        AND ({sort_col}, {self.id_column}) < (%s, %s)
                    """
                    cursor_params = [cursor.sort_value, cursor.item_id]
                else:
                    cursor_condition = f"""
                        AND ({self.timestamp_column}, {self.id_column}) < (%s, %s)
                    """
                    cursor_params = [cursor.timestamp, cursor.item_id]
        
        # Determine actual sort order based on direction
        if direction == PaginationDirection.BACKWARD:
            # Reverse sort order for backward pagination
            actual_order = "ASC" if sort_order == "desc" else "DESC"
        else:
            actual_order = sort_order.upper()
        
        # Build the complete query
        # Handle both CTE and regular queries
        if "WITH" in base_query.upper():
            # Query uses CTE, inject conditions before final ORDER BY
            query_parts = base_query.split("ORDER BY", 1)
            if len(query_parts) == 2:
                query = f"""
                    {query_parts[0]}
                    {cursor_condition}
                    ORDER BY {sort_col} {actual_order}, {self.id_column} {actual_order}
                    LIMIT %s
                """
            else:
                # No ORDER BY in original query
                query = f"""
                    {base_query}
                    {cursor_condition}
                    ORDER BY {sort_col} {actual_order}, {self.id_column} {actual_order}
                    LIMIT %s
                """
        else:
            # Regular query
            query = f"""
                {base_query}
                {cursor_condition}
                ORDER BY {sort_col} {actual_order}, {self.id_column} {actual_order}
                LIMIT %s
            """
        
        # Combine all parameters
        all_params = query_params + cursor_params + [limit]
        
        return query, all_params
    
    def _create_cursor(self, row: Dict[str, Any], sort_column: Optional[str]) -> Cursor:
        """Create a cursor from a result row"""
        item_id = row[self.id_column]
        timestamp = row[self.timestamp_column]
        
        sort_value = None
        if sort_column and sort_column != self.timestamp_column:
            sort_value = row[sort_column]
        
        return Cursor(
            item_id=str(item_id),
            timestamp=timestamp,
            sort_value=sort_value
        )
    
    def create_cursor_from_item(self, 
                               item: Dict[str, Any],
                               sort_column: Optional[str] = None) -> str:
        """Create an encoded cursor from an item"""
        cursor = self._create_cursor(item, sort_column)
        return cursor.encode()