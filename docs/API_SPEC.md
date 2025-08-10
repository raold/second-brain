# API Specification v4.2

## Base URL
`http://localhost:8000/api/v2`

## Endpoints

### Memories
- `GET /memories` - List all memories
- `POST /memories` - Create memory
- `GET /memories/{id}` - Get memory
- `PUT /memories/{id}` - Update memory
- `DELETE /memories/{id}` - Delete memory
- `GET /memories/search` - Semantic search

### Health
- `GET /health` - System health check
- `GET /stats` - Database statistics

## Models

### Memory
```python
{
  "id": "uuid",
  "content": "string",
  "importance_score": 0.0-1.0,
  "tags": ["string"],
  "created_at": "datetime",
  "updated_at": "datetime",
  "embedding": [1536 floats]  # Optional
}
```

### Search Request
```python
{
  "query": "string",
  "limit": 10,
  "threshold": 0.7
}
```

## Authentication
Not implemented yet. Add Bearer token support in v4.3.

## Rate Limiting
Not implemented yet. Consider for production.

## Errors
Standard HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Server Error

See interactive docs at http://localhost:8000/docs