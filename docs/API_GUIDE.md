# API Guide

Base URL: `http://localhost:8000`

## Quick Examples

### Create Memory
```bash
curl -X POST localhost:8000/api/v2/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Important note", "importance_score": 0.8}'
```

### Search Memories
```bash
curl "localhost:8000/api/v2/memories/search?query=important"
```

### Python Client
```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    response = await client.post("/api/v2/memories", 
                                json={"content": "Python example"})
```

Full API docs: http://localhost:8000/docs