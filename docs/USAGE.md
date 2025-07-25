# Second Brain v2.4.4 - Usage Guide

**Single-User AI Memory System** | PostgreSQL + pgvector + OpenAI embeddings

---

## Quick Start Matrix

| Step | Command | Purpose | Time |
|------|---------|---------|------|
| **Clone** | `git clone https://github.com/raold/second-brain.git` | Get source code | ~30s |
| **Branch** | `git checkout develop` | Latest features | ~5s |
| **Install** | `pip install -r requirements-minimal.txt` | Dependencies | ~2min |
| **Config** | `cp .env.example .env` → edit | Environment setup | ~1min |
| **Database** | `python setup_db.py` | Initialize pgvector | ~30s |
| **Run** | `python -m app.main` | Start server | ~5s |

**Total Setup Time: ~4 minutes**

---

## Essential Configuration

**Required Environment Variables** (`.env`)
```
DATABASE_URL=postgresql://user:password@localhost:5432/second_brain
OPENAI_API_KEY=your_openai_api_key_here  
AUTH_TOKEN=your_secure_auth_token_here
```

**Optional Settings**
```
HOST=v2.4.4.0    # Default: all interfaces
PORT=8000       # Default: 8000
```

---

## API Command Reference

**Authentication**: `Authorization: Bearer your_auth_token_here`

| Operation | Method | Endpoint | Body | Response |
|-----------|---------|----------|------|----------|
| **Health Check** | GET | `/health` | None | `{"status": "ok"}` |
| **Store Memory** | POST | `/memories` | `{"content": "text", "metadata": {}}` | `{"id": "uuid"}` |
| **Search** | POST | `/memories/search` | `{"query": "text", "limit": 5}` | `[{memory}, ...]` |
| **List All** | GET | `/memories?limit=10&offset=0` | None | `[{memory}, ...]` |
| **Get One** | GET | `/memories/{uuid}` | None | `{memory}` |
| **Delete** | DELETE | `/memories/{uuid}` | None | `204 No Content` |

---

## Performance Characteristics

| Metric | PostgreSQL+pgvector | Typical Response |
|--------|---------------------|------------------|
| **Search Latency** | ~50-200ms | Sub-second |
| **Storage per Memory** | ~6KB + content | Efficient |
| **Concurrent Users** | 10-50 (default pool) | Single-user focus |
| **Embedding Dimension** | 1536 (OpenAI) | Industry standard |

**Database Index Performance**
```sql
-- Vector similarity index (IVFFlat)
CREATE INDEX memories_embedding_idx ON memories 
USING ivfflat (embedding vector_cosine_ops);

-- Full-text search (GIN) 
CREATE INDEX memories_content_idx ON memories 
USING gin(to_tsvector('english', content));

-- Metadata search (GIN)
CREATE INDEX memories_metadata_idx ON memories 
USING gin(metadata);
```

---

## Python Client Implementation

```python
class SecondBrainClient:
    """Minimal client with error handling and rate limiting"""
    
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}", 
                       "Content-Type": "application/json"}
    
    def store_memory(self, content, metadata=None):
        return requests.post(f"{self.base_url}/memories", 
                           headers=self.headers,
                           json={"content": content, "metadata": metadata or {}})
    
    def search_memories(self, query, limit=5):
        return requests.post(f"{self.base_url}/memories/search",
                           headers=self.headers, 
                           json={"query": query, "limit": limit})
```

---

## Testing Matrix

| Test Type | Command | Purpose | Duration |
|-----------|---------|---------|----------|
| **Unit Tests** | `pytest test_refactored.py -v` | Core functionality | ~30s |
| **Coverage** | `pytest --cov=app --cov-report=html` | Code coverage | ~45s |
| **Mock Database** | `python test_mock_database.py` | No OpenAI costs | ~10s |
| **Health Check** | `python -c "from app.database import Database; import asyncio; asyncio.run(Database().health_check())"` | DB connectivity | ~2s |

---

## Environment Variables Reference

| Variable | Required | Default | Validation | Description |
|----------|----------|---------|------------|-------------|
| `DATABASE_URL` | ✅ | None | PostgreSQL URI format | Connection string |
| `OPENAI_API_KEY` | ✅ | None | `sk-...` format | Embedding API access |
| `AUTH_TOKEN` | ✅ | None | Min 32 chars | Security token |
| `HOST` | ❌ | `v2.4.4.0` | Valid IP/hostname | Server bind address |
| `PORT` | ❌ | `8000` | 1024-65535 | Server port |

---

## Troubleshooting Decision Tree

**Database Connection Failed**
```
DATABASE_URL correct? → Test: psql $DATABASE_URL -c "SELECT version();"
├─ Yes → Check pgvector: SELECT * FROM pg_extension WHERE extname='vector';
└─ No → Fix connection string format
```

**OpenAI API Errors**  
```
API key valid? → Test: curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
├─ Yes → Check rate limits and quotas
└─ No → Generate new API key from OpenAI dashboard
```

**Memory Search Returns Empty**
```
Memories exist? → Test: psql $DATABASE_URL -c "SELECT count(*) FROM memories;"
├─ Yes → Check embedding generation and similarity thresholds
└─ No → Store test memories first
```

---

## Migration Path: v1.x → v2.4.4

| Migration Step | v1.x State | v2.4.4 Target | Action Required |
|----------------|------------|----------------|-----------------|
| **Database Schema** | Complex tables | Simple `memories` table | Run migration script |
| **Configuration** | Multiple files | Single `.env` file | Consolidate settings |
| **Dependencies** | Plugin system | Minimal requirements | Update `requirements.txt` |
| **API Endpoints** | Plugin-specific | REST standard | Update client code |
| **Authentication** | Various methods | Bearer token only | Set `AUTH_TOKEN` |

**Migration Commands**
```sql
-- Add pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to existing table
ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create performance indexes
CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops);
```

---

## Production Deployment Checklist

| Category | Configuration | Status |
|----------|---------------|---------|
| **Security** | Strong AUTH_TOKEN (32+ chars) | ⬜ |
| | SSL/TLS certificates | ⬜ |
| | Database access controls | ⬜ |
| **Performance** | Connection pooling enabled | ⬜ |
| | Vector indexes created | ⬜ |
| | Reverse proxy configured | ⬜ |
| **Monitoring** | Health check endpoint | ⬜ |
| | Error logging enabled | ⬜ |
| | Performance metrics | ⬜ |
| **Backup** | Database backup schedule | ⬜ |
| | Environment file backup | ⬜ |
| | Recovery procedure tested | ⬜ |

---

## Support Resources

**Primary Channels**
- GitHub Issues: [github.com/raold/second-brain/issues](https://github.com/raold/second-brain/issues)
- Documentation: [github.com/raold/second-brain/tree/main/docs](https://github.com/raold/second-brain/tree/main/docs)  
- Discussions: [github.com/raold/second-brain/discussions](https://github.com/raold/second-brain/discussions)

**Response Times** (Community Support)
- Bug reports: 24-48 hours
- Feature requests: 1-2 weeks  
- Documentation: 24 hours
