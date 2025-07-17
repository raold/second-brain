# Second Brain v2.0.0 - Usage Guide

## Overview
Second Brain v2.0.0 is a simplified AI memory system using PostgreSQL with pgvector for semantic search. This guide covers installation, configuration, and usage.

## Quick Start

### 1. Installation
```bash
# Clone repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# Install dependencies
pip install -r requirements-minimal.txt

# Setup environment
cp .env.example .env
```

### 2. Configuration
Edit `.env` file with your settings:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/second_brain

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Authentication
AUTH_TOKEN=your_secure_auth_token_here

# Optional
HOST=0.0.0.0
PORT=8000
```

### 3. Database Setup
```bash
# Initialize database with pgvector extension
python setup_db.py
```

### 4. Run Application
```bash
# Start the server
python -m app.app

# Or with uvicorn
uvicorn app.app:app --reload
```

## API Usage

### Authentication
Include the `Authorization` header in all requests:
```bash
curl -H "Authorization: Bearer your_auth_token_here" \
  http://localhost:8000/health
```

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

### Store a Memory
```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_auth_token_here" \
  -d '{
    "content": "I learned about PostgreSQL pgvector for semantic search",
    "metadata": {
      "category": "learning",
      "tags": ["database", "AI", "search"]
    }
  }'
```

### Search Memories
```bash
curl -X POST http://localhost:8000/memories/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_auth_token_here" \
  -d '{
    "query": "database search",
    "limit": 5
  }'
```

### List All Memories
```bash
curl -X GET "http://localhost:8000/memories?limit=10&offset=0" \
  -H "Authorization: Bearer your_auth_token_here"
```

### Get Specific Memory
```bash
curl -X GET http://localhost:8000/memories/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer your_auth_token_here"
```

### Delete Memory
```bash
curl -X DELETE http://localhost:8000/memories/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer your_auth_token_here"
```

## Python Client Example

```python
import requests
import json

class SecondBrainClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def store_memory(self, content, metadata=None):
        """Store a new memory"""
        data = {
            "content": content,
            "metadata": metadata or {}
        }
        response = requests.post(
            f"{self.base_url}/memories",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def search_memories(self, query, limit=5):
        """Search for memories by semantic similarity"""
        data = {
            "query": query,
            "limit": limit
        }
        response = requests.post(
            f"{self.base_url}/memories/search",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def get_memory(self, memory_id):
        """Get a specific memory by ID"""
        response = requests.get(
            f"{self.base_url}/memories/{memory_id}",
            headers=self.headers
        )
        return response.json()
    
    def list_memories(self, limit=10, offset=0):
        """List all memories with pagination"""
        response = requests.get(
            f"{self.base_url}/memories?limit={limit}&offset={offset}",
            headers=self.headers
        )
        return response.json()
    
    def delete_memory(self, memory_id):
        """Delete a specific memory"""
        response = requests.delete(
            f"{self.base_url}/memories/{memory_id}",
            headers=self.headers
        )
        return response.status_code == 200

# Example usage
client = SecondBrainClient(token="your_auth_token_here")

# Store memory
memory = client.store_memory(
    "PostgreSQL pgvector provides excellent performance for semantic search",
    {"topic": "database", "importance": "high"}
)

# Search memories
results = client.search_memories("database performance", limit=5)

# List all memories
all_memories = client.list_memories(limit=20)
```

## Testing

### Unit Tests
```bash
# Run full test suite
python -m pytest test_refactored.py -v

# Run with coverage
python -m pytest test_refactored.py --cov=app --cov-report=html
```

### Mock Database Testing
For testing without OpenAI API costs:
```python
from app.database_mock import MockDatabase

# Create mock database
mock_db = MockDatabase()

# Test memory operations
memory_id = await mock_db.store_memory(
    "Test content",
    {"category": "test"}
)

# Test search
results = await mock_db.search_memories("test query")
```

### Manual Testing
```bash
# Test basic functionality
python test_mock_database.py

# Test database connection
python -c "from app.database import Database; import asyncio; asyncio.run(Database().health_check())"
```

## Configuration Options

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | None | PostgreSQL connection string |
| `OPENAI_API_KEY` | Yes | None | OpenAI API key for embeddings |
| `AUTH_TOKEN` | Yes | None | Authentication token |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

### Database Configuration
```sql
-- Required PostgreSQL version: 15+
-- Required extension: pgvector

-- Setup commands
CREATE EXTENSION IF NOT EXISTS vector;
CREATE DATABASE second_brain;
```

## Performance Optimization

### Database Indexing
```sql
-- Vector similarity index
CREATE INDEX memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops);

-- Full-text search index
CREATE INDEX memories_content_idx 
ON memories USING gin(to_tsvector('english', content));

-- Metadata index
CREATE INDEX memories_metadata_idx 
ON memories USING gin(metadata);
```

### Connection Pooling
The application uses asyncpg connection pooling for optimal performance:
- Default pool size: 10 connections
- Automatic connection recycling
- Connection health checks

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database connection
   psql $DATABASE_URL -c "SELECT version();"
   
   # Check pgvector extension
   psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname='vector';"
   ```

2. **OpenAI API Errors**
   ```bash
   # Test API key
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
   ```

3. **Memory Not Found Errors**
   ```bash
   # Check memory table
   psql $DATABASE_URL -c "SELECT count(*) FROM memories;"
   ```

### Debugging
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check database connection
from app.database import Database
db = Database()
await db.health_check()
```

## Migration from v1.x

### Database Migration
```sql
-- Add pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column (if upgrading existing database)
ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create vector index
CREATE INDEX IF NOT EXISTS memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops);
```

### Configuration Migration
1. Replace complex config files with `.env` variables
2. Update database connection strings
3. Set OpenAI API key and auth tokens
4. Remove unused environment variables

### Code Migration
- API endpoints remain compatible
- Update client code to use new simplified responses
- Remove plugin-specific code
- Update authentication to use bearer tokens

## Best Practices

### Memory Content
- Use clear, descriptive content
- Include relevant context
- Add meaningful metadata
- Keep content focused and atomic

### Search Queries
- Use natural language queries
- Include specific keywords
- Combine with metadata filtering
- Adjust similarity thresholds as needed

### Production Deployment
- Use environment-specific configurations
- Implement proper logging
- Set up database backups
- Monitor API performance
- Use reverse proxy (nginx/traefik)

## Security Considerations

- Store sensitive data in environment variables
- Use strong authentication tokens
- Implement rate limiting for production
- Enable SSL/TLS in production
- Regular security updates
- Database access controls

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/raold/second-brain/issues
- Documentation: https://github.com/raold/second-brain/tree/main/docs
- Discussions: https://github.com/raold/second-brain/discussions
