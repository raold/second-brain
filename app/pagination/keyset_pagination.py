"""
Keyset pagination implementation for ultra-efficient pagination.

Keyset pagination (also known as seek pagination) provides:
- Constant time queries regardless of page depth
- Perfect consistency even with concurrent modifications
- Ideal for infinite scroll implementations
- No offset performance degradation
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic
from datetime import datetime

from app.pagination.models import (
    PaginationParams,
    KeysetData,
    PaginationDirection,
    PageInfo,
    PaginationMetadata,
    PaginatedResponse
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class KeysetCursor:
    """Represents a keyset position in ordered data"""
    
    def __init__(self, columns: Dict[str, Any]):
        """
        Initialize keyset cursor.
        
        Args:
            columns: Dictionary of column names to values that define the position
        """
        self.columns = columns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return self.columns
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeysetCursor':
        """Create from dictionary"""
        return cls(columns=data)
    
    def to_where_clause(self, 
                       direction: PaginationDirection = PaginationDirection.FORWARD,
                       table_alias: str = "") -> Tuple[str, List[Any]]:
        """
        Generate WHERE clause for keyset pagination.
        
        Returns:
            Tuple of (where_clause, parameters)
        """
        if not self.columns:
            return "", []
        
        # Sort columns by name for consistent ordering
        sorted_columns = sorted(self.columns.items())
        
        conditions = []
        params = []
        
        # Build nested conditions for multi-column keyset
        # Example for (a, b, c) > (1, 2, 3):
        # (a > 1) OR (a = 1 AND b > 2) OR (a = 1 AND b = 2 AND c > 3)
        
        op = ">" if direction == PaginationDirection.FORWARD else "<"
        
        for i in range(len(sorted_columns)):
            # Build equality conditions for previous columns
            eq_conditions = []
            for j in range(i):
                col_name, _ = sorted_columns[j]
                if table_alias:
                    eq_conditions.append(f"{table_alias}.{col_name} = %s")
                else:
                    eq_conditions.append(f"{col_name} = %s")
                params.append(sorted_columns[j][1])
            
            # Add comparison for current column
            col_name, col_value = sorted_columns[i]
            if table_alias:
                comp_condition = f"{table_alias}.{col_name} {op} %s"
            else:
                comp_condition = f"{col_name} {op} %s"
            params.append(col_value)
            
            # Combine conditions
            if eq_conditions:
                condition = f"({' AND '.join(eq_conditions)} AND {comp_condition})"
            else:
                condition = comp_condition
            
            conditions.append(condition)
        
        # Combine all conditions with OR
        where_clause = f"({' OR '.join(conditions)})"
        
        return where_clause, params


class KeysetPage(Generic[T]):
    """Represents a page of results using keyset pagination"""
    
    def __init__(self,
                 items: List[T],
                 has_next: bool,
                 has_previous: bool,
                 first_keyset: Optional[Dict[str, Any]] = None,
                 last_keyset: Optional[Dict[str, Any]] = None):
        self.items = items
        self.has_next = has_next
        self.has_previous = has_previous
        self.first_keyset = first_keyset
        self.last_keyset = last_keyset
    
    def to_response(self,
                    query_time_ms: Optional[float] = None) -> PaginatedResponse[T]:
        """Convert to standard paginated response"""
        page_info = PageInfo(
            has_next_page=self.has_next,
            has_previous_page=self.has_previous,
            # Keyset pagination doesn't use traditional cursors
            start_cursor=None,
            end_cursor=None
        )
        
        metadata = PaginationMetadata(
            page_info=page_info,
            page_size=len(self.items),
            query_time_ms=query_time_ms
        )
        
        return PaginatedResponse(
            data=self.items,
            pagination=metadata
        )


class KeysetPaginator:
    """
    Keyset paginator for ultra-efficient pagination.
    
    This paginator is ideal for:
    - Very large datasets (millions of rows)
    - Infinite scroll implementations
    - Real-time data with frequent updates
    """
    
    def __init__(self,
                 key_columns: List[str],
                 default_limit: int = 50,
                 max_limit: int = 1000):
        """
        Initialize keyset paginator.
        
        Args:
            key_columns: Ordered list of columns that form the keyset
            default_limit: Default page size
            max_limit: Maximum allowed page size
        """
        self.key_columns = key_columns
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    async def paginate_query(self,
                           db: Any,
                           base_query: str,
                           params: PaginationParams,
                           query_params: Optional[List[Any]] = None,
                           keyset_values: Optional[Dict[str, Any]] = None) -> KeysetPage[Dict[str, Any]]:
        """
        Paginate a query using keyset pagination.
        
        Args:
            db: Database connection
            base_query: Base SQL query (without ORDER BY or LIMIT)
            params: Pagination parameters
            query_params: Parameters for the base query
            keyset_values: Current keyset position
            
        Returns:
            KeysetPage with results
        """
        limit = min(params.limit or self.default_limit, self.max_limit)
        query_params = query_params or []
        
        # Build keyset condition
        keyset_condition = ""
        keyset_params = []
        
        if keyset_values:
            cursor = KeysetCursor(keyset_values)
            keyset_condition, keyset_params = cursor.to_where_clause(
                direction=params.direction
            )
            if keyset_condition:
                keyset_condition = f"AND {keyset_condition}"
        
        # Determine sort order
        sort_order = "ASC" if params.sort_order == "asc" else "DESC"
        if params.direction == PaginationDirection.BACKWARD:
            # Reverse order for backward pagination
            sort_order = "DESC" if sort_order == "ASC" else "ASC"
        
        # Build ORDER BY clause
        order_columns = []
        for col in self.key_columns:
            order_columns.append(f"{col} {sort_order}")
        order_by = f"ORDER BY {', '.join(order_columns)}"
        
        # Build complete query
        query = f"""
            {base_query}
            {keyset_condition}
            {order_by}
            LIMIT %s
        """
        
        # Execute query
        start_time = datetime.now()
        all_params = query_params + keyset_params + [limit + 1]
        rows = await db.fetch(query, *all_params)
        query_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Check for more pages
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]
        
        # Convert to list of dicts
        items = [dict(row) for row in rows]
        
        # Reverse for backward pagination
        if params.direction == PaginationDirection.BACKWARD:
            items.reverse()
        
        # Determine pagination state
        if params.direction == PaginationDirection.BACKWARD:
            has_previous = has_more
            has_next = keyset_values is not None
        else:
            has_next = has_more
            has_previous = keyset_values is not None
        
        # Extract keyset values for navigation
        first_keyset = None
        last_keyset = None
        
        if items:
            first_keyset = {col: items[0][col] for col in self.key_columns}
            last_keyset = {col: items[-1][col] for col in self.key_columns}
        
        return KeysetPage(
            items=items,
            has_next=has_next,
            has_previous=has_previous,
            first_keyset=first_keyset,
            last_keyset=last_keyset
        )
    
    def get_keyset_from_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keyset values from an item"""
        return {col: item[col] for col in self.key_columns}
    
    def build_keyset_filter(self,
                           after: Optional[Dict[str, Any]] = None,
                           before: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Any]]:
        """
        Build WHERE clause for keyset filtering.
        
        Args:
            after: Keyset values to start after
            before: Keyset values to start before
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        conditions = []
        params = []
        
        if after:
            cursor = KeysetCursor(after)
            where_clause, where_params = cursor.to_where_clause(
                direction=PaginationDirection.FORWARD
            )
            if where_clause:
                conditions.append(where_clause)
                params.extend(where_params)
        
        if before:
            cursor = KeysetCursor(before)
            where_clause, where_params = cursor.to_where_clause(
                direction=PaginationDirection.BACKWARD
            )
            if where_clause:
                conditions.append(where_clause)
                params.extend(where_params)
        
        if conditions:
            combined = " AND ".join(conditions)
            return combined, params
        
        return "", []