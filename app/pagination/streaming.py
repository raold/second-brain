"""
Streaming pagination for massive datasets.

Provides memory-efficient streaming of large result sets using:
- Async generators for constant memory usage
- Server-side cursors for database efficiency
- Chunked responses for network efficiency
- Progress tracking for long-running exports
"""

import logging
import json
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TypeVar
from datetime import datetime
import asyncio

from fastapi import Response
from fastapi.responses import StreamingResponse
import asyncpg

logger = logging.getLogger(__name__)

T = TypeVar('T')


class StreamingPaginator:
    """
    Streaming paginator for very large datasets.
    
    Uses server-side cursors and async generators to stream
    results without loading entire dataset into memory.
    """
    
    def __init__(self,
                 chunk_size: int = 100,
                 prefetch_size: int = 1000,
                 timeout: int = 3600):  # 1 hour default
        """
        Initialize streaming paginator.
        
        Args:
            chunk_size: Number of items per chunk sent to client
            prefetch_size: Number of rows to prefetch from database
            timeout: Maximum time for streaming operation (seconds)
        """
        self.chunk_size = chunk_size
        self.prefetch_size = prefetch_size
        self.timeout = timeout
    
    async def stream_query(self,
                          db: Any,
                          query: str,
                          params: Optional[List[Any]] = None,
                          transform: Optional[Callable] = None) -> AsyncIterator[List[Dict[str, Any]]]:
        """
        Stream query results in chunks.
        
        Args:
            db: Database connection (must support server-side cursors)
            query: SQL query to stream
            params: Query parameters
            transform: Optional function to transform each row
            
        Yields:
            Chunks of results
        """
        params = params or []
        transform = transform or (lambda x: dict(x))
        
        # For asyncpg, use server-side cursor
        if hasattr(db, 'cursor'):  # asyncpg connection
            async with db.transaction():
                # Create server-side cursor
                cursor_name = f"stream_cursor_{datetime.now().timestamp()}"
                
                # Declare cursor
                await db.execute(
                    f"DECLARE {cursor_name} CURSOR FOR {query}",
                    *params
                )
                
                try:
                    chunk = []
                    
                    while True:
                        # Fetch chunk from cursor
                        rows = await db.fetch(
                            f"FETCH {self.prefetch_size} FROM {cursor_name}"
                        )
                        
                        if not rows:
                            # Yield final chunk if any
                            if chunk:
                                yield chunk
                            break
                        
                        # Process rows
                        for row in rows:
                            chunk.append(transform(row))
                            
                            if len(chunk) >= self.chunk_size:
                                yield chunk
                                chunk = []
                                
                                # Allow other tasks to run
                                await asyncio.sleep(0)
                    
                finally:
                    # Clean up cursor
                    await db.execute(f"CLOSE {cursor_name}")
        else:
            # Fallback for connections without cursor support
            # Use LIMIT/OFFSET with smaller chunks
            offset = 0
            
            while True:
                chunk_query = f"{query} LIMIT %s OFFSET %s"
                chunk_params = params + [self.chunk_size, offset]
                
                rows = await db.fetch(chunk_query, *chunk_params)
                
                if not rows:
                    break
                
                chunk = [transform(row) for row in rows]
                yield chunk
                
                offset += self.chunk_size
                
                # Prevent infinite loops on large datasets
                if offset > 1000000:  # Safety limit
                    logger.warning("Streaming query exceeded safety limit")
                    break
                
                await asyncio.sleep(0)
    
    async def stream_to_json(self,
                           db: Any,
                           query: str,
                           params: Optional[List[Any]] = None,
                           transform: Optional[Callable] = None) -> AsyncIterator[str]:
        """
        Stream query results as JSON lines.
        
        Yields:
            JSON strings, one per line
        """
        first = True
        
        # Start JSON array
        yield "[\n"
        
        async for chunk in self.stream_query(db, query, params, transform):
            for item in chunk:
                if not first:
                    yield ",\n"
                else:
                    first = False
                
                yield json.dumps(item, default=str)
        
        # Close JSON array
        yield "\n]"
    
    async def stream_to_csv(self,
                          db: Any,
                          query: str,
                          params: Optional[List[Any]] = None,
                          headers: Optional[List[str]] = None) -> AsyncIterator[str]:
        """
        Stream query results as CSV.
        
        Args:
            db: Database connection
            query: SQL query
            params: Query parameters
            headers: CSV headers (auto-detected if not provided)
            
        Yields:
            CSV lines
        """
        import csv
        import io
        
        first = True
        
        async for chunk in self.stream_query(db, query, params):
            # Auto-detect headers from first chunk
            if first and not headers and chunk:
                headers = list(chunk[0].keys())
                
                # Yield header row
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(headers)
                yield output.getvalue()
                
                first = False
            
            # Write data rows
            for item in chunk:
                output = io.StringIO()
                writer = csv.writer(output)
                
                if headers:
                    row = [item.get(h, '') for h in headers]
                else:
                    row = list(item.values())
                
                writer.writerow(row)
                yield output.getvalue()
    
    def create_streaming_response(self,
                                generator: AsyncIterator[str],
                                media_type: str = "application/json",
                                filename: Optional[str] = None) -> StreamingResponse:
        """
        Create a FastAPI streaming response.
        
        Args:
            generator: Async generator yielding response chunks
            media_type: Response content type
            filename: Optional filename for download
            
        Returns:
            StreamingResponse configured for the content
        """
        headers = {}
        
        if filename:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return StreamingResponse(
            generator,
            media_type=media_type,
            headers=headers
        )


async def stream_generator(
    query_func: Callable,
    transform_func: Optional[Callable] = None,
    batch_size: int = 100,
    format: str = "json"
) -> AsyncIterator[str]:
    """
    Generic streaming generator for any query function.
    
    Args:
        query_func: Async function that yields results
        transform_func: Optional transformation for each item
        batch_size: Items per batch
        format: Output format (json, jsonl, csv)
        
    Yields:
        Formatted strings
    """
    if format == "json":
        yield '{"data": ['
        first = True
        
        async for item in query_func():
            if transform_func:
                item = transform_func(item)
            
            if not first:
                yield ","
            else:
                first = False
            
            yield json.dumps(item, default=str)
        
        yield ']}'
    
    elif format == "jsonl":
        # JSON Lines format - one JSON object per line
        async for item in query_func():
            if transform_func:
                item = transform_func(item)
            
            yield json.dumps(item, default=str) + "\n"
    
    elif format == "csv":
        import csv
        import io
        
        first = True
        headers = None
        
        async for item in query_func():
            if transform_func:
                item = transform_func(item)
            
            # Extract headers from first item
            if first and isinstance(item, dict):
                headers = list(item.keys())
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(headers)
                yield output.getvalue()
                first = False
            
            # Write data row
            output = io.StringIO()
            writer = csv.writer(output)
            
            if isinstance(item, dict) and headers:
                row = [item.get(h, '') for h in headers]
            else:
                row = list(item.values()) if hasattr(item, 'values') else [str(item)]
            
            writer.writerow(row)
            yield output.getvalue()


class ProgressTracker:
    """Track progress for long-running streaming operations"""
    
    def __init__(self, total_items: Optional[int] = None):
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        self.update_interval = 1.0  # seconds
    
    async def update(self, count: int = 1) -> Optional[Dict[str, Any]]:
        """
        Update progress counter.
        
        Returns:
            Progress info if update interval passed, None otherwise
        """
        self.processed_items += count
        
        now = datetime.now()
        if (now - self.last_update).total_seconds() >= self.update_interval:
            self.last_update = now
            return self.get_progress()
        
        return None
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed_items / elapsed if elapsed > 0 else 0
        
        progress = {
            "processed": self.processed_items,
            "elapsed_seconds": elapsed,
            "items_per_second": rate
        }
        
        if self.total_items:
            progress["total"] = self.total_items
            progress["percentage"] = (self.processed_items / self.total_items) * 100
            
            if rate > 0:
                remaining_items = self.total_items - self.processed_items
                progress["estimated_remaining_seconds"] = remaining_items / rate
        
        return progress