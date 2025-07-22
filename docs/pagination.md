# Pagination System Documentation

## Overview

The Second Brain system now includes an enterprise-grade pagination system that provides efficient navigation of large datasets. The system supports three types of pagination:

1. **Cursor-based Pagination** - Stable pagination for real-time data
2. **Keyset Pagination** - Ultra-efficient for very large datasets
3. **Streaming Pagination** - Memory-efficient export of massive result sets

## Key Features

- **Consistent API** across all endpoints
- **Bi-directional navigation** (forward and backward)
- **Stable pagination** that handles insertions/deletions
- **Performance optimized** with index-based queries
- **Memory efficient** streaming for large exports
- **Rich metadata** including navigation URLs and query times

## API Usage

### List Memories with Cursor Pagination

```bash
# First page
GET /api/memories?limit=50&sort_by=created_at&sort_order=desc

# Next page using cursor
GET /api/memories?cursor=eyJpZCI6ICIxMjM0NSIsICJ0cyI6ICIyMDI0LTAxLTE1VDEwOjAwOjAwWiJ9&direction=forward

# Previous page
GET /api/memories?cursor=eyJpZCI6ICIxMjM0NSIsICJ0cyI6ICIyMDI0LTAxLTE1VDEwOjAwOjAwWiJ9&direction=backward
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Number of items per page (1-1000) |
| `cursor` | string | null | Cursor for pagination position |
| `direction` | string | forward | Pagination direction (forward/backward) |
| `sort_by` | string | created_at | Field to sort by |
| `sort_order` | string | desc | Sort order (asc/desc) |
| `include_total` | bool | false | Include total count (expensive) |

### Response Format

```json
{
  "data": [
    {
      "id": "123",
      "content": "Memory content",
      "memory_type": "semantic",
      "created_at": "2024-01-15T10:00:00Z",
      // ... other fields
    }
  ],
  "pagination": {
    "page_info": {
      "has_next_page": true,
      "has_previous_page": false,
      "start_cursor": "eyJpZCI6ICIxMjMiLCAidHMiOiAiMjAyNC0wMS0xNVQxMDowMDowMFoifQ==",
      "end_cursor": "eyJpZCI6ICIxNzMiLCAidHMiOiAiMjAyNC0wMS0xNVQxMDozMDowMFoifQ=="
    },
    "page_size": 50,
    "total_count": 10000,  // Only if include_total=true
    "query_time_ms": 45.2,
    "next_page_url": "/api/memories?cursor=eyJpZCI6ICIxNzMi...&direction=forward",
    "previous_page_url": null,
    "first_page_url": "/api/memories?direction=forward&limit=50",
    "last_page_url": null
  }
}
```

## Streaming Exports

For exporting large datasets, use the streaming endpoint:

```bash
# Export as JSON
GET /api/memories/export/stream?format=json

# Export as CSV
GET /api/memories/export/stream?format=csv

# Export as JSON Lines (JSONL)
GET /api/memories/export/stream?format=jsonl&memory_type=semantic
```

### Streaming Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | json | Export format (json/csv/jsonl) |
| `memory_type` | string | null | Filter by memory type |
| `chunk_size` | int | 100 | Chunk size for streaming (10-1000) |

## Implementation Details

### Cursor Structure

Cursors are base64-encoded JSON objects containing:
- `id`: Primary key of the item
- `ts`: Timestamp for stable ordering
- `sv`: Optional sort value for custom sorting

### Database Optimization

The pagination system leverages indexes for optimal performance:

```sql
-- Recommended indexes for cursor pagination
CREATE INDEX idx_memories_created_at_id ON memories(created_at DESC, id DESC);
CREATE INDEX idx_memories_updated_at_id ON memories(updated_at DESC, id DESC);
CREATE INDEX idx_memories_importance_score_id ON memories(importance_score DESC, id DESC);
```

### Performance Characteristics

| Dataset Size | Offset Pagination | Cursor Pagination | Keyset Pagination |
|--------------|-------------------|-------------------|-------------------|
| 1K rows | ~5ms | ~5ms | ~3ms |
| 100K rows | ~50ms | ~5ms | ~3ms |
| 1M rows | ~500ms | ~5ms | ~3ms |
| 10M rows | ~5000ms | ~5ms | ~3ms |

## Best Practices

1. **Use cursor pagination** for most use cases
2. **Avoid `include_total=true`** for large datasets
3. **Use streaming exports** for data dumps
4. **Implement proper error handling** for invalid cursors
5. **Cache cursor positions** for user sessions
6. **Use keyset pagination** for infinite scroll implementations

## Migration Guide

### From Offset to Cursor Pagination

```python
# Old approach
memories = await service.get_memories(limit=50, offset=100)

# New approach
response = await service.list_memories(
    limit=50,
    cursor=previous_response.pagination.page_info.end_cursor
)
```

### Handling Both Pagination Types

The system supports both pagination types during migration:

```python
# The pagination helper automatically detects the type
if params.cursor:
    # Use cursor pagination
elif params.offset:
    # Fall back to offset pagination (deprecated)
```

## Error Handling

```python
try:
    response = await list_memories(cursor=user_cursor)
except ValueError as e:
    if "Invalid cursor" in str(e):
        # Reset to first page
        response = await list_memories()
```

## Example Integration

```typescript
// TypeScript client example
interface PaginationState {
  cursor: string | null;
  hasMore: boolean;
}

async function* iterateMemories(): AsyncGenerator<Memory[]> {
  let state: PaginationState = { cursor: null, hasMore: true };
  
  while (state.hasMore) {
    const response = await fetchMemories({
      cursor: state.cursor,
      limit: 100
    });
    
    yield response.data;
    
    state = {
      cursor: response.pagination.page_info.end_cursor,
      hasMore: response.pagination.page_info.has_next_page
    };
  }
}

// Usage
for await (const batch of iterateMemories()) {
  processBatch(batch);
}
```

## Troubleshooting

### Common Issues

1. **Invalid Cursor Error**
   - Cursors expire after 24 hours
   - Cursors are tied to specific sort orders
   - Solution: Start fresh from the first page

2. **Slow Queries**
   - Check if proper indexes exist
   - Avoid `include_total=true` for large datasets
   - Use streaming for exports

3. **Memory Issues with Large Exports**
   - Use streaming endpoints
   - Reduce chunk_size parameter
   - Implement client-side buffering