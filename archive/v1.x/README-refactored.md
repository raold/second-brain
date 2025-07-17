# Second Brain - Refactored

A simplified memory storage and search system using PostgreSQL with pgvector.

## Architecture

- **Single Storage System**: PostgreSQL with pgvector extension
- **Direct Database Access**: No ORM overhead, simple asyncpg queries
- **Minimal Dependencies**: FastAPI + PostgreSQL + OpenAI API
- **Simple Authentication**: API key-based authentication
- **Environment Configuration**: Environment variables only

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements-minimal.txt
   ```

2. **Set environment variables:**
   ```bash
   # PostgreSQL
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=secondbrain
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=postgres
   
   # OpenAI
   export OPENAI_API_KEY=your_openai_api_key
   export OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   
   # Authentication
   export API_TOKENS=your_api_token_here
   ```

3. **Setup database:**
   ```bash
   python setup_db.py
   ```

4. **Run the application:**
   ```bash
   python -m app.app
   ```

## API Endpoints

### Health Check
- `GET /health` - Health check

### Memory Operations
- `POST /memories` - Store a memory
- `GET /memories` - List all memories (paginated)
- `GET /memories/{id}` - Get specific memory
- `DELETE /memories/{id}` - Delete memory
- `POST /memories/search` - Search memories by similarity

### Authentication
All endpoints (except `/health`) require an `api_key` query parameter.

## Example Usage

```bash
# Store a memory
curl -X POST "http://localhost:8000/memories?api_key=your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Python is great for data science",
    "metadata": {"type": "fact", "tags": ["python", "data-science"]}
  }'

# Search memories
curl -X POST "http://localhost:8000/memories/search?api_key=your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "data science",
    "limit": 5
  }'
```

## Database Schema

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops);
```

## Testing

```bash
python -m pytest test_refactored.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `secondbrain` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `API_TOKENS` | Required | Comma-separated API tokens |

## What Was Removed

- Qdrant vector database
- Complex caching systems
- Extensive monitoring and metrics
- ORM overhead
- Complex configuration classes
- Dual storage complexity
- WebSocket support
- Complex authentication systems
- Excessive logging and monitoring

## What Was Kept

- PostgreSQL with pgvector for vector search
- OpenAI API for embeddings
- Basic logging
- Simple REST API
- Environment-based configuration
