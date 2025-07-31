# Comprehensive Caching Strategy for Second-Brain

## Overview

This document outlines all caching opportunities in the second-brain project to optimize performance and reduce redundant operations.

## Current Caching Implementation

### 1. Context File Cache (Implemented)
- **Files**: CLAUDE.md, TODO.md, DEVELOPMENT_CONTEXT.md
- **TTL**: 1 hour, 5 minutes, 1 minute respectively
- **Location**: In-memory + `.claude/cache/`
- **Benefit**: 90% reduction in file reads

## Additional Caching Targets

### 2. Agent Execution Cache
```python
class AgentResultCache:
    """Cache expensive agent operations"""
    
    cache_config = {
        "architecture-analyzer": {
            "ttl_seconds": 1800,  # 30 minutes
            "key_params": ["file_path", "analysis_type"],
            "invalidate_on": ["*.py", "*.yml"]
        },
        "code-quality-analyzer": {
            "ttl_seconds": 900,   # 15 minutes
            "key_params": ["file_path", "metrics"],
            "invalidate_on": ["*.py"]
        },
        "performance-analyzer": {
            "ttl_seconds": 600,   # 10 minutes
            "key_params": ["file_path", "profile_type"],
            "invalidate_on": ["*.py", "*.sql"]
        }
    }
```

### 3. Tool Operation Cache
```yaml
tool_cache:
  grep:
    ttl_seconds: 300
    max_size_mb: 50
    key: "pattern_hash + path_hash + options"
  
  glob:
    ttl_seconds: 300
    max_entries: 1000
    key: "pattern + path"
  
  ls:
    ttl_seconds: 60
    key: "path + options"
```

### 4. Vector Embeddings Cache
```python
class EmbeddingCache:
    """Cache pgvector embeddings for notes"""
    
    def get_embedding(self, content: str) -> Optional[List[float]]:
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check cache first
        cached = self.redis_client.get(f"embed:{content_hash}")
        if cached:
            return json.loads(cached)
        
        # Generate and cache
        embedding = self.generate_embedding(content)
        self.redis_client.setex(
            f"embed:{content_hash}",
            86400,  # 24 hours
            json.dumps(embedding)
        )
        return embedding
```

### 5. Search Results Cache
```python
class SearchCache:
    """Cache search results with LRU eviction"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = LRUCache(max_size)
        self.ttl_seconds = 600  # 10 minutes
    
    def get_results(self, query: str, filters: dict) -> Optional[List]:
        cache_key = self._generate_key(query, filters)
        
        entry = self.cache.get(cache_key)
        if entry and not self._is_expired(entry):
            return entry['results']
        
        return None
```

### 6. Note Relationships Graph
```python
class GraphCache:
    """Cache computed note relationships"""
    
    def __init__(self):
        self.graph = {}  # node_id -> connections
        self.last_update = {}  # node_id -> timestamp
    
    def update_node(self, node_id: str, connections: List[str]):
        self.graph[node_id] = connections
        self.last_update[node_id] = datetime.now()
        
        # Persist to disk for recovery
        self._persist_graph()
    
    def get_connections(self, node_id: str) -> List[str]:
        return self.graph.get(node_id, [])
```

### 7. Test Results Cache
```yaml
# .claude/test-cache.yml
test_cache:
  enabled: true
  cache_dir: .pytest_cache/results
  
  strategy:
    - key: "file_hash + test_name"
    - store: "outcome + duration + output"
    - invalidate_on:
        - source_file_change
        - dependency_update
        - config_change
```

### 8. Docker Layer Cache
```dockerfile
# Optimized Dockerfile with caching
FROM python:3.11-slim AS base

# Cache pip packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip

# Cache dependencies separately
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# App code changes don't invalidate dependency cache
COPY . .
```

### 9. API Response Cache
```python
class APICache:
    """Cache external API responses"""
    
    cache_rules = {
        "docs.anthropic.com": {
            "ttl_seconds": 3600,  # 1 hour
            "cache_errors": False
        },
        "api.github.com": {
            "ttl_seconds": 300,   # 5 minutes
            "cache_errors": True,
            "error_ttl": 60
        }
    }
    
    def fetch_with_cache(self, url: str) -> dict:
        domain = urlparse(url).netloc
        rules = self.cache_rules.get(domain, {"ttl_seconds": 300})
        
        # Check cache
        cached = self.get_cached(url)
        if cached:
            return cached
        
        # Fetch and cache
        response = self.fetch(url)
        self.cache_response(url, response, rules['ttl_seconds'])
        return response
```

## Cache Implementation Priority

### Phase 1: High-Impact, Easy Implementation
1. **Tool Operation Cache** - Immediate 50% reduction in file operations
2. **Agent Result Cache** - Avoid re-analyzing unchanged files
3. **Search Results Cache** - Faster repeated searches

### Phase 2: Medium-Impact, Moderate Complexity
4. **Vector Embeddings Cache** - Significant compute savings
5. **Test Results Cache** - Faster CI/CD pipelines
6. **API Response Cache** - Reduce external dependencies

### Phase 3: Long-term Optimization
7. **Note Relationships Graph** - Enable instant navigation
8. **Docker Layer Cache** - Faster builds and deployments
9. **Distributed Cache** - Team-wide sharing

## Cache Metrics & Monitoring

```python
class CacheMetrics:
    """Track cache effectiveness"""
    
    def __init__(self):
        self.metrics = {
            "hits": Counter(),
            "misses": Counter(),
            "evictions": Counter(),
            "size_bytes": Gauge(),
            "response_time_ms": Histogram()
        }
    
    def record_hit(self, cache_name: str, response_time: float):
        self.metrics["hits"].labels(cache=cache_name).inc()
        self.metrics["response_time_ms"].labels(
            cache=cache_name, 
            result="hit"
        ).observe(response_time * 1000)
```

## Best Practices

1. **Cache Key Design**
   - Include version in keys for easy invalidation
   - Use consistent hashing for distributed caches
   - Consider hierarchical keys for bulk invalidation

2. **TTL Strategy**
   - Shorter TTL for frequently changing data
   - Longer TTL for computationally expensive operations
   - Use sliding expiration for active items

3. **Invalidation Patterns**
   - Event-based invalidation preferred over TTL
   - Cascade invalidation for dependent caches
   - Provide manual invalidation endpoints

4. **Memory Management**
   - Set maximum cache sizes
   - Implement eviction policies (LRU, LFU)
   - Monitor memory usage

5. **Persistence**
   - Critical caches should persist to disk
   - Use write-through for important data
   - Implement cache warming on startup

## Estimated Impact

| Cache Type | Implementation Effort | Performance Impact | Token Savings |
|------------|---------------------|-------------------|---------------|
| Context Files | ✅ Done | 90% file read reduction | High |
| Tool Operations | Low | 50% operation reduction | Medium |
| Agent Results | Medium | 70% compute reduction | High |
| Embeddings | Medium | 95% compute reduction | Medium |
| Search Results | Low | 80% query reduction | Low |
| Test Results | Medium | 40% test time reduction | N/A |
| Docker Layers | Low | 60% build time reduction | N/A |

## Next Steps

1. Implement Tool Operation Cache (1 day)
2. Add Agent Result Cache (2 days)
3. Create cache metrics dashboard
4. Set up cache warming strategies
5. Document cache debugging procedures