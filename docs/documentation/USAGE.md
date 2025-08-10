# Usage Guide

## Starting the Application
```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Access
- Base URL: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Basic Operations

### Create Memory
```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")
response = client.post("/api/v2/memories", json={
    "content": "Remember this important fact",
    "importance_score": 0.9,
    "tags": ["important", "work"]
})
memory = response.json()
```

### Search Memories
```python
results = client.get("/api/v2/memories/search", 
                     params={"query": "important fact"}).json()
```

### List All Memories
```python
memories = client.get("/api/v2/memories").json()
```

## CLI Usage
```bash
# Create memory
curl -X POST localhost:8000/api/v2/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "CLI memory"}'

# Search
curl "localhost:8000/api/v2/memories/search?query=CLI"
```

## WebSocket Connection
Connect to `ws://localhost:8000/ws` for real-time updates.

## Performance Tips
- Use batch operations when possible
- Set appropriate importance scores (0.0-1.0)
- Use tags for better organization
- Limit search results with `limit` parameter