# Second Brain API Specification v3.0.0

## Overview

Second Brain v3.0.0 provides a RESTful API built with FastAPI, following clean architecture principles with comprehensive documentation via OpenAPI/Swagger.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

All API endpoints (except health checks) require authentication using JWT tokens.

### Headers
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Get Token
```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Core Endpoints

### Memories

#### Create Memory
```http
POST /api/v1/memories
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Important meeting notes from today's standup",
  "tags": ["work", "meetings", "standup"],
  "metadata": {
    "source": "manual",
    "importance": 8
  }
}
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Important meeting notes from today's standup",
  "embedding": [...],
  "tags": ["work", "meetings", "standup"],
  "metadata": {
    "source": "manual",
    "importance": 8
  },
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-07-25T10:30:00Z",
  "updated_at": "2025-07-25T10:30:00Z",
  "version": 1
}
```

#### List Memories
```http
GET /api/v1/memories?page=1&size=20&tag=work&sort=created_at:desc
Authorization: Bearer <token>
```

Query Parameters:
- `page` (int): Page number (default: 1)
- `size` (int): Items per page (default: 20, max: 100)
- `tag` (string): Filter by tag
- `user_id` (uuid): Filter by user (admin only)
- `sort` (string): Sort field and direction (e.g., "created_at:desc")
- `search` (string): Full-text search in content

Response:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Important meeting notes from today's standup",
      "tags": ["work", "meetings", "standup"],
      "created_at": "2025-07-25T10:30:00Z",
      "updated_at": "2025-07-25T10:30:00Z"
    }
  ],
  "total": 156,
  "page": 1,
  "size": 20,
  "pages": 8
}
```

#### Get Memory
```http
GET /api/v1/memories/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Important meeting notes from today's standup",
  "embedding": [...],
  "tags": ["work", "meetings", "standup"],
  "metadata": {
    "source": "manual",
    "importance": 8
  },
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-07-25T10:30:00Z",
  "updated_at": "2025-07-25T10:30:00Z",
  "version": 1,
  "events": [
    {
      "event_type": "MemoryCreated",
      "timestamp": "2025-07-25T10:30:00Z",
      "data": {...}
    }
  ]
}
```

#### Update Memory
```http
PUT /api/v1/memories/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Updated meeting notes with action items",
  "tags": ["work", "meetings", "standup", "action-items"],
  "metadata": {
    "source": "manual",
    "importance": 9,
    "updated_by": "user"
  }
}
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Updated meeting notes with action items",
  "tags": ["work", "meetings", "standup", "action-items"],
  "version": 2,
  "updated_at": "2025-07-25T11:00:00Z"
}
```

#### Delete Memory
```http
DELETE /api/v1/memories/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

Response:
```http
204 No Content
```

### Search

#### Vector Search
```http
POST /api/v1/memories/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "meeting action items from last week",
  "limit": 10,
  "threshold": 0.7,
  "filters": {
    "tags": ["work", "meetings"],
    "date_range": {
      "start": "2025-07-18",
      "end": "2025-07-25"
    }
  }
}
```

Response:
```json
{
  "results": [
    {
      "memory": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "content": "Important meeting notes from today's standup",
        "tags": ["work", "meetings", "standup"],
        "created_at": "2025-07-25T10:30:00Z"
      },
      "score": 0.89,
      "highlights": [
        "Important <em>meeting</em> notes from today's standup"
      ]
    }
  ],
  "total": 3,
  "query_embedding": [...],
  "processing_time_ms": 45
}
```

### Sessions

#### Create Session
```http
POST /api/v1/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Project Planning Session",
  "description": "Q3 roadmap planning",
  "metadata": {
    "participants": ["alice", "bob"],
    "project": "second-brain"
  }
}
```

Response:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Project Planning Session",
  "description": "Q3 roadmap planning",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-07-25T14:00:00Z",
  "metadata": {
    "participants": ["alice", "bob"],
    "project": "second-brain"
  }
}
```

#### Add Memory to Session
```http
POST /api/v1/sessions/660e8400-e29b-41d4-a716-446655440000/memories
Authorization: Bearer <token>
Content-Type: application/json

{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response:
```http
204 No Content
```

#### Get Session with Memories
```http
GET /api/v1/sessions/660e8400-e29b-41d4-a716-446655440000?include_memories=true
Authorization: Bearer <token>
```

Response:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Project Planning Session",
  "description": "Q3 roadmap planning",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-07-25T14:00:00Z",
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Important meeting notes from today's standup",
      "tags": ["work", "meetings", "standup"],
      "added_at": "2025-07-25T14:05:00Z"
    }
  ],
  "memory_count": 1
}
```

### Tags

#### List All Tags
```http
GET /api/v1/tags
Authorization: Bearer <token>
```

Response:
```json
{
  "tags": [
    {
      "name": "work",
      "count": 45,
      "first_used": "2025-01-15T10:00:00Z",
      "last_used": "2025-07-25T10:30:00Z"
    },
    {
      "name": "meetings",
      "count": 23,
      "first_used": "2025-02-01T09:00:00Z",
      "last_used": "2025-07-25T10:30:00Z"
    }
  ],
  "total": 15
}
```

#### Get Tag Statistics
```http
GET /api/v1/tags/work/stats
Authorization: Bearer <token>
```

Response:
```json
{
  "tag": "work",
  "total_memories": 45,
  "users": 1,
  "related_tags": [
    {"tag": "meetings", "correlation": 0.72},
    {"tag": "projects", "correlation": 0.65}
  ],
  "usage_trend": [
    {"date": "2025-07-01", "count": 5},
    {"date": "2025-07-02", "count": 3}
  ]
}
```

### Attachments

#### Upload Attachment
```http
POST /api/v1/attachments
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary data>
memory_id: 550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "filename": "meeting-notes.pdf",
  "content_type": "application/pdf",
  "size": 245632,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_url": "/api/v1/attachments/770e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-07-25T15:00:00Z"
}
```

#### Download Attachment
```http
GET /api/v1/attachments/770e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

Response:
```http
200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="meeting-notes.pdf"

<binary data>
```

### Health & Monitoring

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "rabbitmq": "healthy",
    "minio": "healthy"
  },
  "timestamp": "2025-07-25T16:00:00Z"
}
```

#### Readiness Check
```http
GET /ready
```

Response:
```json
{
  "ready": true,
  "checks": {
    "database": {"ready": true, "latency_ms": 5},
    "cache": {"ready": true, "latency_ms": 1},
    "message_queue": {"ready": true, "latency_ms": 3},
    "storage": {"ready": true, "latency_ms": 8}
  }
}
```

#### Metrics (Prometheus Format)
```http
GET /metrics
```

Response:
```text
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/memories",status="200"} 1543
http_requests_total{method="POST",endpoint="/api/v1/memories",status="201"} 234

# HELP memory_operations_total Total memory operations
# TYPE memory_operations_total counter
memory_operations_total{operation="create"} 234
memory_operations_total{operation="update"} 89
memory_operations_total{operation="delete"} 12

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 1289
http_request_duration_seconds_bucket{le="0.5"} 1456
http_request_duration_seconds_bucket{le="1.0"} 1523
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "content",
        "message": "Content cannot be empty"
      }
    ],
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid authentication |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

API requests are rate-limited per user:
- **Default**: 1000 requests per hour
- **Search endpoints**: 100 requests per hour
- **Attachment uploads**: 50 requests per hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1627392000
```

## Pagination

All list endpoints support pagination:

```http
GET /api/v1/memories?page=2&size=50
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 500,
  "page": 2,
  "size": 50,
  "pages": 10,
  "has_next": true,
  "has_previous": true
}
```

## Webhooks

Configure webhooks for real-time notifications:

```http
POST /api/v1/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://example.com/webhook",
  "events": ["memory.created", "memory.updated", "memory.deleted"],
  "secret": "webhook_secret_key"
}
```

Webhook payload:
```json
{
  "event": "memory.created",
  "timestamp": "2025-07-25T16:30:00Z",
  "data": {
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "signature": "sha256=..."
}
```

## SDK Examples

### Python
```python
from secondbrain import Client

client = Client(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# Create memory
memory = client.memories.create(
    content="Important note",
    tags=["work"]
)

# Search memories
results = client.memories.search(
    query="important notes",
    limit=10
)
```

### JavaScript/TypeScript
```typescript
import { SecondBrainClient } from '@secondbrain/client';

const client = new SecondBrainClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your_api_key'
});

// Create memory
const memory = await client.memories.create({
  content: 'Important note',
  tags: ['work']
});

// Search memories
const results = await client.memories.search({
  query: 'important notes',
  limit: 10
});
```

## API Versioning

The API uses URL versioning:
- Current version: `/api/v1`
- Previous versions are maintained for backward compatibility
- Deprecation notices provided via headers:
  ```http
  Sunset: Sat, 31 Dec 2025 23:59:59 GMT
  Deprecation: true
  Link: </api/v2/memories>; rel="successor-version"
  ```

## OpenAPI/Swagger

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`