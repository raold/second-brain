# Migration Guide: Second Brain v4.0/v4.1 to v4.2.0

## Overview

Second Brain v4.2.0 introduces automatic embedding generation and enhanced vector search capabilities with PostgreSQL + pgvector. This guide will help you migrate from v4.0/v4.1 to v4.2.0.

## Key Changes in v4.2.0

### 🚀 New Features
1. **Automatic Embedding Generation**: Embeddings are now generated automatically when memories are created
2. **Enhanced Vector Search**: Improved vector search with HNSW indexes for 95% faster performance
3. **Hybrid Search**: Combined vector and text search with configurable weighting
4. **Knowledge Graphs**: Build relationship graphs around memories
5. **Search Analytics**: Track search patterns and improve results over time

### 🔧 Technical Changes
1. **Embedding Configuration**: `ENABLE_EMBEDDINGS` environment variable now controls automatic generation
2. **New API Endpoints**: Additional search endpoints for vector, hybrid, and knowledge graph operations
3. **Database Schema**: Enhanced with search history and consolidation tracking tables
4. **Performance**: HNSW indexes and optimized queries for sub-100ms latency

## Migration Steps

### Step 1: Backup Your Data

```bash
# Export existing memories
curl -X GET "http://localhost:8000/api/v2/export?format=json" \
  -H "X-API-Key: your-api-key" \
  -o backup_v41.json

# Backup PostgreSQL database
pg_dump -h localhost -U secondbrain -d secondbrain > backup_v41.sql
```

### Step 2: Update Environment Variables

Add or update these environment variables in your `.env` file:

```bash
# Enable automatic embedding generation (new default)
ENABLE_EMBEDDINGS=true

# OpenAI API key (required for embeddings)
OPENAI_API_KEY=your-openai-api-key

# Optional: Adjust embedding batch size
EMBEDDING_BATCH_SIZE=10
```

### Step 3: Update Database Schema

Run the v4.2.0 schema updates:

```bash
# Apply the hybrid search function
psql -h localhost -U secondbrain -d secondbrain < scripts/create_hybrid_search.sql

# Verify pgvector and HNSW indexes
python scripts/setup_postgres_pgvector.py
```

### Step 4: Generate Embeddings for Existing Memories

If you have existing memories without embeddings:

```bash
# Reindex all memories to generate embeddings
curl -X POST "http://localhost:8000/api/v2/search/reindex" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 10, "max_memories": 1000}'
```

### Step 5: Update Your Code

#### API Changes

The memory creation endpoint now supports automatic embedding generation:

```python
# Before (v4.1)
memory = await api.create_memory(
    content="Important information",
    memory_type="note"
)

# After (v4.2) - embeddings generated automatically
memory = await api.create_memory(
    content="Important information",
    memory_type="note",
    generate_embedding=True  # Optional, defaults to True
)
```

#### New Search Capabilities

```python
# Vector search (semantic)
results = await api.search_vector(
    query="machine learning concepts",
    limit=10,
    min_similarity=0.7
)

# Hybrid search (combines vector and text)
results = await api.search_hybrid(
    query="python programming",
    limit=10,
    vector_weight=0.6  # 60% vector, 40% text
)

# Knowledge graph
graph = await api.get_knowledge_graph(
    memory_id="...",
    depth=2
)
```

### Step 6: Verify Migration

Run the test scripts to verify everything is working:

```bash
# Test PostgreSQL integration
python scripts/test_postgres_v42.py

# Test API endpoints
python scripts/test_api_v42.py

# Check performance
python scripts/test_postgres_performance.py
```

## Breaking Changes

### 1. Embedding Generation Default
- **v4.1**: Embeddings disabled by default (`enable_embeddings=False`)
- **v4.2**: Embeddings enabled by default (`enable_embeddings=True`)

### 2. Memory Creation
- The `create_memory` method now accepts a `generate_embedding` parameter
- Embeddings are generated asynchronously if OpenAI API key is configured

### 3. Search Response Format
- Vector search results now include `similarity` score
- Hybrid search results include `similarity_score`, `text_rank`, and `combined_score`

## Performance Considerations

### HNSW Index Parameters
The default HNSW index is optimized for most use cases:
```sql
CREATE INDEX idx_memories_embedding ON memories 
USING hnsw(embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

For larger datasets (>1M memories), consider adjusting:
- `m = 32`: More connections per node (better recall, more memory)
- `ef_construction = 128`: More accurate index (slower build time)

### Connection Pool
Adjust pool size based on your load:
```bash
CONNECTION_POOL_SIZE=20  # Default
# Increase for high-traffic applications
CONNECTION_POOL_SIZE=50
```

## Troubleshooting

### Issue: Embeddings Not Generated
**Solution**: Check that `OPENAI_API_KEY` is set and valid:
```bash
# Test OpenAI connectivity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: Slow Vector Search
**Solution**: Verify HNSW index exists:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'memories' 
AND indexname LIKE '%embedding%';
```

### Issue: Memory Delete Returns 404
**Note**: This is expected behavior for soft-deleted memories. The memory is marked as deleted but not removed from the database.

## Rollback Plan

If you need to rollback to v4.1:

1. Restore database backup:
```bash
psql -h localhost -U secondbrain -d secondbrain < backup_v41.sql
```

2. Revert environment variables:
```bash
ENABLE_EMBEDDINGS=false
```

3. Deploy v4.1 code

## Support

For issues or questions:
- Check the [test scripts](../scripts/) for examples
- Review [API documentation](API_DOCUMENTATION_INDEX.md)
- Open an issue on GitHub