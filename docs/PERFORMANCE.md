# Performance Optimization Guide

## Vector Index Performance - Current Status

### System Metrics
```
Index Type    Memory     Build Time   Query Speed   Accuracy
HNSW         45MB       2:34         <10ms         95.2%
IVFFlat      12MB       0:42         <25ms         92.1%  
Sequential   0MB        0:00         >500ms        100%
```

### Production Thresholds
```
Memories     Status      Index        Query Time    Action
<1,000      ▁▁▁▁▁▁▁▁▁   None         <50ms         ✓ No action
1,000-10K   ▂▄▅▇▇▅▄▂   HNSW         <10ms         ✓ Auto-create  
10K-100K    ▅▇████▇▅   HNSW+        <15ms         ⚠ Monitor
>100K       ████████    HNSW+ Tune   <25ms         🔧 Optimize
```

## Index Strategy Decision Matrix

**Primary: HNSW (m=16, ef_construction=64)**
- Query speed: <10ms ████████████████████░
- Memory usage: 45MB ██████████░░░░░░░░░░░
- Build time: 2:34 ████████░░░░░░░░░░░░░
- **Use when**: >1K memories, production workloads

**Fallback: IVFFlat (lists=100)**  
- Query speed: <25ms ████████░░░░░░░░░░░░░
- Memory usage: 12MB ████░░░░░░░░░░░░░░░░░
- Build time: 0:42 ████████████████░░░░░
- **Use when**: Memory-constrained, <10K memories

## Distance Metrics Performance
```
Metric          Use Case                Speed    Accuracy
cosine          Text embeddings         ████     █████
euclidean       Spatial data           █████     ████  
inner_product   Normalized vectors     █████     ████
```

## Automatic Management Triggers
```
Event                    Threshold    Action              Time
Memory insertion        1,000 items   → Create HNSW       ~2min
Query performance       >100ms avg    → Rebuild index     ~5min
Memory deletion         >10% deleted  → Reindex           ~3min
System startup         Index missing  → Auto-create       ~2min
```

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
