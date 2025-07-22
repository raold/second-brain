"""
Pagination utilities and helpers for common operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from app.pagination.models import (
    PaginationParams,
    PaginatedResponse,
    PaginationMetadata,
    PageInfo
)
from app.pagination.cursor_pagination import CursorPaginator
from app.pagination.keyset_pagination import KeysetPaginator

logger = logging.getLogger(__name__)


def extract_pagination_params(
    query_params: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None
) -> PaginationParams:
    """
    Extract pagination parameters from query string.
    
    Args:
        query_params: Raw query parameters
        defaults: Default values to use
        
    Returns:
        Validated PaginationParams
    """
    defaults = defaults or {}
    
    # Extract and validate parameters
    params = {
        "limit": int(query_params.get("limit", defaults.get("limit", 50))),
        "offset": int(query_params.get("offset", defaults.get("offset", 0))),
        "cursor": query_params.get("cursor"),
        "direction": query_params.get("direction", "forward"),
        "after_id": query_params.get("after_id"),
        "before_id": query_params.get("before_id"),
        "sort_by": query_params.get("sort_by", defaults.get("sort_by")),
        "sort_order": query_params.get("sort_order", defaults.get("sort_order", "desc")),
        "include_total": query_params.get("include_total", "false").lower() == "true"
    }
    
    return PaginationParams(**params)


def build_pagination_url(
    base_url: str,
    cursor: Optional[str] = None,
    direction: str = "forward",
    limit: Optional[int] = None,
    **kwargs
) -> str:
    """
    Build a pagination URL with query parameters.
    
    Args:
        base_url: Base URL without query parameters
        cursor: Cursor for pagination
        direction: Pagination direction
        limit: Page size
        **kwargs: Additional query parameters
        
    Returns:
        Complete URL with query parameters
    """
    # Parse the base URL
    parsed = urlparse(base_url)
    
    # Start with existing query parameters
    query_params = parse_qs(parsed.query)
    
    # Update with new parameters
    if cursor:
        query_params["cursor"] = [cursor]
    if direction:
        query_params["direction"] = [direction]
    if limit:
        query_params["limit"] = [str(limit)]
    
    # Add any additional parameters
    for key, value in kwargs.items():
        if value is not None:
            query_params[key] = [str(value)]
    
    # Flatten the query parameters
    flat_params = {k: v[0] for k, v in query_params.items()}
    
    # Rebuild the URL
    new_query = urlencode(flat_params)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def create_page_urls(
    base_url: str,
    page_info: PageInfo,
    limit: int
) -> Dict[str, Optional[str]]:
    """
    Create navigation URLs for pagination.
    
    Args:
        base_url: Base URL for the endpoint
        page_info: Page information with cursors
        limit: Page size
        
    Returns:
        Dictionary with navigation URLs
    """
    urls = {
        "first": None,
        "last": None,
        "next": None,
        "previous": None
    }
    
    # First page - no cursor, forward direction
    urls["first"] = build_pagination_url(
        base_url,
        direction="forward",
        limit=limit
    )
    
    # Next page
    if page_info.has_next_page and page_info.end_cursor:
        urls["next"] = build_pagination_url(
            base_url,
            cursor=page_info.end_cursor,
            direction="forward",
            limit=limit
        )
    
    # Previous page
    if page_info.has_previous_page and page_info.start_cursor:
        urls["previous"] = build_pagination_url(
            base_url,
            cursor=page_info.start_cursor,
            direction="backward",
            limit=limit
        )
    
    return urls


def merge_pagination_results(
    results: List[PaginatedResponse],
    limit: int
) -> PaginatedResponse:
    """
    Merge multiple paginated results into a single response.
    
    Useful for aggregating results from multiple sources.
    
    Args:
        results: List of paginated responses to merge
        limit: Maximum items in merged result
        
    Returns:
        Merged paginated response
    """
    if not results:
        return PaginatedResponse(
            data=[],
            pagination=PaginationMetadata(
                page_info=PageInfo(
                    has_next_page=False,
                    has_previous_page=False
                ),
                page_size=0
            )
        )
    
    # Merge all items
    all_items = []
    total_query_time = 0.0
    
    for result in results:
        all_items.extend(result.data)
        if result.pagination.query_time_ms:
            total_query_time += result.pagination.query_time_ms
    
    # Limit results
    has_more = len(all_items) > limit
    items = all_items[:limit]
    
    # Create merged metadata
    page_info = PageInfo(
        has_next_page=has_more or any(r.pagination.page_info.has_next_page for r in results),
        has_previous_page=any(r.pagination.page_info.has_previous_page for r in results),
        start_cursor=results[0].pagination.page_info.start_cursor if results else None,
        end_cursor=results[-1].pagination.page_info.end_cursor if results else None
    )
    
    metadata = PaginationMetadata(
        page_info=page_info,
        page_size=len(items),
        query_time_ms=total_query_time if total_query_time > 0 else None
    )
    
    return PaginatedResponse(data=items, pagination=metadata)


def create_offset_response(
    items: List[Any],
    total_count: int,
    limit: int,
    offset: int,
    query_time_ms: Optional[float] = None,
    base_url: Optional[str] = None
) -> PaginatedResponse:
    """
    Create a paginated response for offset-based pagination.
    
    This is a compatibility helper for transitioning from offset to cursor pagination.
    
    Args:
        items: List of items in the page
        total_count: Total number of items
        limit: Page size
        offset: Current offset
        query_time_ms: Query execution time
        base_url: Base URL for navigation links
        
    Returns:
        PaginatedResponse with offset-based metadata
    """
    has_next = offset + limit < total_count
    has_previous = offset > 0
    
    page_info = PageInfo(
        has_next_page=has_next,
        has_previous_page=has_previous,
        # No cursors for offset pagination
        start_cursor=None,
        end_cursor=None
    )
    
    metadata = PaginationMetadata(
        page_info=page_info,
        total_count=total_count,
        page_size=len(items),
        query_time_ms=query_time_ms
    )
    
    # Add navigation URLs if base URL provided
    if base_url:
        if has_next:
            metadata.next_page_url = build_pagination_url(
                base_url,
                limit=limit,
                offset=offset + limit
            )
        if has_previous:
            metadata.previous_page_url = build_pagination_url(
                base_url,
                limit=limit,
                offset=max(0, offset - limit)
            )
        
        # First and last pages
        metadata.first_page_url = build_pagination_url(
            base_url,
            limit=limit,
            offset=0
        )
        
        last_offset = max(0, total_count - limit)
        metadata.last_page_url = build_pagination_url(
            base_url,
            limit=limit,
            offset=last_offset
        )
    
    return PaginatedResponse(data=items, pagination=metadata)


class PaginationHelper:
    """
    Helper class for consistent pagination across services.
    """
    
    def __init__(self,
                 default_limit: int = 50,
                 max_limit: int = 1000,
                 id_column: str = "id",
                 timestamp_column: str = "created_at"):
        """
        Initialize pagination helper.
        
        Args:
            default_limit: Default page size
            max_limit: Maximum allowed page size
            id_column: Primary key column name
            timestamp_column: Timestamp column for ordering
        """
        self.default_limit = default_limit
        self.max_limit = max_limit
        
        # Initialize paginators
        self.cursor_paginator = CursorPaginator(
            id_column=id_column,
            timestamp_column=timestamp_column,
            default_limit=default_limit,
            max_limit=max_limit
        )
        
        self.keyset_paginator = KeysetPaginator(
            key_columns=[timestamp_column, id_column],
            default_limit=default_limit,
            max_limit=max_limit
        )
    
    async def paginate(self,
                      db: Any,
                      query: str,
                      params: Union[PaginationParams, Dict[str, Any]],
                      count_query: Optional[str] = None,
                      query_params: Optional[List[Any]] = None,
                      base_url: Optional[str] = None) -> PaginatedResponse:
        """
        Paginate a query using the appropriate method.
        
        Automatically selects between cursor, keyset, or offset pagination
        based on the provided parameters.
        
        Args:
            db: Database connection
            query: SQL query to paginate
            params: Pagination parameters
            count_query: Optional query for total count
            query_params: Query parameters
            base_url: Base URL for navigation links
            
        Returns:
            Paginated response
        """
        # Convert dict to PaginationParams if needed
        if isinstance(params, dict):
            params = extract_pagination_params(params)
        
        # Use cursor pagination if cursor provided
        if params.cursor:
            page = await self.cursor_paginator.paginate_query(
                db=db,
                base_query=query,
                params=params,
                count_query=count_query,
                query_params=query_params
            )
            
            response = page.to_response(base_url=base_url)
            
            # Add navigation URLs
            if base_url:
                urls = create_page_urls(base_url, page_info=page.page_info, limit=params.limit)
                response.pagination.first_page_url = urls["first"]
                response.pagination.next_page_url = urls["next"]
                response.pagination.previous_page_url = urls["previous"]
            
            return response
        
        # Use keyset pagination if after_id or before_id provided
        elif params.after_id or params.before_id:
            # Build keyset values
            keyset_values = None
            if params.after_id:
                # Fetch the item to get its keyset values
                item_query = f"SELECT * FROM ({query}) q WHERE id = %s"
                item = await db.fetchrow(item_query, params.after_id)
                if item:
                    keyset_values = self.keyset_paginator.get_keyset_from_item(dict(item))
            
            page = await self.keyset_paginator.paginate_query(
                db=db,
                base_query=query,
                params=params,
                query_params=query_params,
                keyset_values=keyset_values
            )
            
            return page.to_response()
        
        # Fall back to offset pagination
        else:
            return await self._offset_paginate(
                db=db,
                query=query,
                params=params,
                count_query=count_query,
                query_params=query_params,
                base_url=base_url
            )
    
    async def _offset_paginate(self,
                              db: Any,
                              query: str,
                              params: PaginationParams,
                              count_query: Optional[str] = None,
                              query_params: Optional[List[Any]] = None,
                              base_url: Optional[str] = None) -> PaginatedResponse:
        """
        Fallback offset-based pagination.
        
        This should be avoided for large datasets but is kept
        for backwards compatibility.
        """
        query_params = query_params or []
        
        # Get total count if requested
        total_count = None
        if params.include_total and count_query:
            total_count = await db.fetchval(count_query, *query_params)
        
        # Build paginated query
        paginated_query = f"""
            {query}
            ORDER BY {params.sort_by or self.cursor_paginator.timestamp_column} {params.sort_order}
            LIMIT %s OFFSET %s
        """
        
        # Execute query
        from datetime import datetime
        start_time = datetime.now()
        
        all_params = query_params + [params.limit, params.offset]
        rows = await db.fetch(paginated_query, *all_params)
        
        query_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Convert to list of dicts
        items = [dict(row) for row in rows]
        
        return create_offset_response(
            items=items,
            total_count=total_count or 0,
            limit=params.limit,
            offset=params.offset or 0,
            query_time_ms=query_time_ms,
            base_url=base_url
        )