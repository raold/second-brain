# API Reference

## Authentication

All API endpoints require bearer token authentication:

```http
Authorization: Bearer <your-api-token>
```

## Memory Endpoints

### List Memories
```http
GET /memories
```

Query Parameters:
- `limit` (int): Number of items per page (1-1000, default: 50)
- `cursor` (string): Cursor for pagination
- `direction` (string): Pagination direction (forward/backward)
- `sort_by` (string): Field to sort by (default: created_at)
- `sort_order` (string): Sort order (asc/desc, default: desc)
- `memory_type` (string): Filter by memory type
- `include_total` (bool): Include total count (expensive)

Response:
```json
{
  "data": [
    {
      "id": "123",
      "content": "Memory content",
      "memory_type": "semantic",
      "created_at": "2024-01-15T10:00:00Z",
      "importance_score": 8.5
    }
  ],
  "pagination": {
    "page_info": {
      "has_next_page": true,
      "has_previous_page": false,
      "start_cursor": "eyJpZCI6ICIxMjMi...",
      "end_cursor": "eyJpZCI6ICIxNzMi..."
    },
    "page_size": 50,
    "total_count": 10000,
    "next_page_url": "/memories?cursor=..."
  }
}
```

### Create Memory
```http
POST /memories
```

Request Body:
```json
{
  "content": "Memory content",
  "memory_type": "semantic",
  "importance_score": 8.5,
  "tags": ["tag1", "tag2"],
  "metadata": {
    "source": "api",
    "category": "technical"
  }
}
```

### Get Memory
```http
GET /memories/{memory_id}
```

### Update Memory
```http
PUT /memories/{memory_id}
```

### Delete Memory
```http
DELETE /memories/{memory_id}
```

### Search Memories
```http
POST /memories/search
```

Request Body:
```json
{
  "query": "search query",
  "limit": 50
}
```

Response includes pagination metadata.

### Contextual Search
```http
POST /memories/search/contextual
```

Request Body:
```json
{
  "query": "search query",
  "memory_types": ["semantic", "episodic"],
  "importance_threshold": 7.0,
  "limit": 50
}
```

### Stream Export
```http
GET /memories/export/stream
```

Query Parameters:
- `format` (string): Export format (json/csv/jsonl)
- `memory_type` (string): Filter by type
- `chunk_size` (int): Streaming chunk size (10-1000)

## Multimodal Endpoints

### Upload File
```http
POST /multimodal/upload
```

Form Data:
- `file`: File to upload
- `importance` (float): Importance score
- `tags` (string): Comma-separated tags

### Process Status
```http
GET /multimodal/status/{task_id}
```

## Automation Endpoints

### Get Automation Status
```http
GET /automation/status
```

Response:
```json
{
  "status": "active",
  "scheduled_tasks": {
    "consolidation": {
      "next_run": "2025-07-23T02:00:00Z",
      "last_run": "2025-07-22T02:00:00Z",
      "status": "completed"
    }
  },
  "triggers": {
    "duplicate_monitor": {
      "enabled": true,
      "current_value": 2.3,
      "threshold": 5.0
    }
  },
  "metrics": {
    "duplicate_rate": 2.3,
    "memories_consolidated_today": 45,
    "storage_saved_mb": 127
  }
}
```

### Control Automation
```http
POST /automation/tasks/control
```

Query Parameters:
- `action` (string): Control action (pause/resume/stop)

### Trigger Consolidation
```http
POST /automation/consolidation/immediate
```

### Trigger Cleanup
```http
POST /automation/cleanup/immediate
```

### Get Task History
```http
GET /automation/tasks/history
```

Query Parameters:
- `task_type` (string): Filter by task type
- `status` (string): Filter by status
- `limit` (int): Number of results

## Pattern Discovery Endpoints

### Discover Patterns
```http
POST /patterns/discover
```

Request Body:
```json
{
  "pattern_types": ["temporal", "semantic"],
  "min_confidence": 0.7,
  "limit": 100
}
```

### Get Pattern Details
```http
GET /patterns/{pattern_id}
```

### Get Memory Clusters
```http
GET /patterns/clusters
```

## Analytics Endpoints

### Get Insights
```http
GET /analytics/insights
```

### Get Usage Stats
```http
GET /analytics/usage
```

Query Parameters:
- `period` (string): Time period (day/week/month/year)
- `metrics` (array): Specific metrics to include

### Get Memory Growth
```http
GET /analytics/growth
```

## System Endpoints

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "embedding_service": "available",
  "automation": "active",
  "version": "2.7.0-dev"
}
```

### API Documentation
```http
GET /docs
```

Interactive OpenAPI documentation.

### Dashboard
```http
GET /dashboard
```

Web-based dashboard interface.

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description",
  "status_code": 400,
  "type": "validation_error"
}
```

Common status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `429`: Rate Limited
- `500`: Internal Server Error

## Rate Limiting

Default limits:
- 1000 requests per hour per API key
- 100 requests per minute per API key
- Streaming exports: 10 concurrent connections

Headers returned:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Pagination

The API supports three pagination methods:

### Cursor Pagination (Recommended)
Best for real-time data and large datasets.

```http
GET /memories?cursor=eyJpZCI6ICIxMjM0NSI...&direction=forward
```

### Keyset Pagination
Ultra-efficient for sorted data.

```http
GET /memories?after_id=12345&limit=50
```

### Offset Pagination (Deprecated)
Legacy support, avoid for large datasets.

```http
GET /memories?offset=100&limit=50
```

## Webhooks

Configure webhooks for events:

### Supported Events
- `memory.created`
- `memory.updated`
- `memory.deleted`
- `consolidation.completed`
- `pattern.discovered`

### Webhook Payload
```json
{
  "event": "memory.created",
  "timestamp": "2025-07-22T10:00:00Z",
  "data": {
    "memory_id": "123",
    "content": "..."
  }
}
```