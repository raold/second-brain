# Performance Optimization Guide

## Vector Index Strategy

### Overview
Second Brain uses PostgreSQL with pgvector extension for semantic search. As your memory collection grows, query performance becomes critical. This guide explains our indexing strategy and performance optimization.

### Index Types

#### HNSW (Hierarchical Navigable Small World) - Primary Choice
- **When**: Default choice for production use
- **Pros**: 
  - Excellent query performance
  - Good balance of speed and recall accuracy
  - Faster than IVFFlat for most use cases
  - Better for read-heavy workloads
- **Cons**: 
  - Higher memory usage
  - Slower index building
- **Configuration**: `m=16, ef_construction=64`

#### IVFFlat - Fallback Option
- **When**: Fallback if HNSW fails or for memory-constrained environments
- **Pros**: 
  - Lower memory usage
  - Faster index building
- **Cons**: 
  - Slower query performance
  - May require tuning for optimal results
- **Configuration**: `lists=100` (automatically calculated)

### Distance Metrics

#### Cosine Similarity (Default)
- **Use Case**: Text embeddings (OpenAI text-embedding-3-small)
- **Operator**: `vector_cosine_ops`
- **Why**: Most text embedding models are trained for cosine similarity
- **Formula**: `1 - (embedding <=> query_embedding)`

#### Alternative Metrics
- **Euclidean Distance**: `vector_l2_ops` - For spatial/geometric data
- **Inner Product**: `vector_ip_ops` - For normalized vectors

### Automatic Index Management

#### Index Creation Timing
- **Threshold**: 1000+ memories with embeddings
- **Reason**: Indexes are most effective with sufficient data
- **Behavior**: Automatic creation when storing memories

#### Index Monitoring
- **Endpoint**: `GET /status` - Check index status
- **Metrics**: Memory count, index existence, performance recommendations

### Performance Recommendations

#### Development (< 1000 memories)
- No index needed
- Sequential scan performs well
- Focus on data quality

#### Production (1000+ memories)
- HNSW index automatically created
- Monitor query performance
- Consider memory allocation

#### Large Scale (100K+ memories)
- Optimize PostgreSQL configuration
- Consider connection pooling
- Monitor index maintenance

### Manual Index Operations

#### Check Index Status
```python
# Using the API
GET /status

# Response includes:
{
    "index_status": {
        "total_memories": 1500,
        "memories_with_embeddings": 1500,
        "hnsw_index_exists": true,
        "index_ready": true
    }
}
```

#### Force Index Creation
```python
# In database client
await db.force_create_index()
```

#### Index Maintenance
```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'memories';

-- Rebuild index if needed
REINDEX INDEX memories_embedding_hnsw_idx;
```

### Performance Tuning

#### PostgreSQL Configuration
```sql
-- For better vector operations
SET max_parallel_workers_per_gather = 2;
SET work_mem = '256MB';
SET shared_buffers = '1GB';  -- Adjust based on available memory
```

#### Application Level
- **Batch operations**: Store multiple memories in transactions
- **Connection pooling**: Reuse database connections
- **Caching**: Cache frequently accessed memories

### Troubleshooting

#### Slow Queries
1. Check if index exists: `GET /status`
2. Verify index is being used: `EXPLAIN ANALYZE` on queries
3. Consider index rebuild if data has changed significantly

#### Index Creation Failures
1. Check PostgreSQL logs for errors
2. Verify pgvector extension is properly installed
3. Ensure sufficient memory for index building
4. Fallback to IVFFlat index

#### Memory Issues
1. Monitor PostgreSQL memory usage
2. Adjust `work_mem` and `shared_buffers`
3. Consider horizontal scaling for very large datasets

### Monitoring

#### Key Metrics
- **Query Response Time**: < 100ms for typical searches
- **Index Hit Ratio**: > 95% for optimal performance
- **Memory Usage**: Monitor PostgreSQL memory consumption
- **Index Size**: Track index growth over time

#### Alerts
- Query response time > 500ms
- Index hit ratio < 90%
- Memory usage > 80% of allocated
- Index creation failures

### Best Practices

1. **Start Simple**: Let automatic index creation handle optimization
2. **Monitor Performance**: Use `/status` endpoint regularly
3. **Test with Production Data**: Performance varies with data characteristics
4. **Plan for Scale**: Consider memory and storage requirements
5. **Regular Maintenance**: Monitor index health and rebuild if needed

### Future Considerations

- **Hybrid Search**: Combine vector similarity with full-text search
- **Partitioning**: For very large datasets (millions of memories)
- **Distributed Setup**: Multiple PostgreSQL instances for horizontal scaling
- **Advanced Indexing**: Custom index parameters for specific use cases
