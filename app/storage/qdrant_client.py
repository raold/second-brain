import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from qdrant_client import QdrantClient

from app.config import config
from app.utils.cache import SEARCH_CACHE_CONFIG, CacheConfig, get_cache, get_smart_cache
from app.utils.logger import logger
from app.utils.openai_client import get_openai_embedding

# Initialize Qdrant client with connection pooling
client = QdrantClient(
    host=config.qdrant['host'], 
    port=config.qdrant['port'],
    timeout=config.qdrant['timeout'],  # 30 second timeout
    grpc_port=6334,  # Enable gRPC for better performance
    prefer_grpc=True
)

# Enhanced search cache with TTL and smart eviction
_search_cache = get_smart_cache("qdrant_search", SEARCH_CACHE_CONFIG)

# Enhanced caches for different operation types
_vector_cache = get_cache("qdrant_vectors", CacheConfig(
    max_size=500, 
    ttl_seconds=1800,  # 30 minutes
    enable_metrics=True
))

_collection_info_cache = get_cache("qdrant_collection_info", CacheConfig(
    max_size=10,
    ttl_seconds=300,  # 5 minutes
    enable_metrics=True
))

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    qdrant_search_latency = Histogram('qdrant_search_latency_seconds', 'Qdrant search latency (seconds)')
    qdrant_operations = Counter('qdrant_operations_total', 'Qdrant operations by type', ['operation', 'status'])
    qdrant_connection_pool = Gauge('qdrant_connection_pool_size', 'Qdrant connection pool size')
except ImportError:
    qdrant_search_latency = qdrant_operations = qdrant_connection_pool = None

if TYPE_CHECKING:
    pass  # type: ignore

def _search_cache_key(query: str, top_k: int = 5, filters: Optional[dict] = None) -> str:
    """Generate cache key for search queries."""
    import json
    filter_str = json.dumps(filters or {}, sort_keys=True)
    return f"search:{query}:{top_k}:{filter_str}"

def _get_qdrant_health() -> Dict[str, Any]:
    """Get Qdrant health status with caching."""
    cache_key = "health_status"
    cached_result = _collection_info_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Get cluster info
        cluster_info = client.get_cluster()
        
        # Get collection info
        collections = client.get_collections()
        collection_count = len(collections.collections) if collections else 0
        
        # Check if our collection exists
        our_collection_exists = False
        our_collection_info = None
        try:
            our_collection_info = client.get_collection(config.qdrant['collection'])
            our_collection_exists = True
        except Exception:
            pass
        
        health_data = {
            "status": "healthy",
            "cluster_status": "ok" if cluster_info else "unknown",
            "total_collections": collection_count,
            "our_collection_exists": our_collection_exists,
            "our_collection_points": our_collection_info.points_count if our_collection_info else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache the result
        _collection_info_cache.set(cache_key, health_data)
        return health_data
        
    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return error_data

def to_uuid(value: str) -> UUID:
    """
    Convert string to deterministic UUID using namespace.
    
    Args:
        value: String to convert
        
    Returns:
        UUID object
    """
    return uuid5(NAMESPACE_URL, value)

def _validate_payload_structure(payload: Dict[str, Any]) -> None:
    """
    Validate payload structure before processing.
    
    Args:
        payload: Payload dictionary to validate
        
    Raises:
        ValueError: If payload structure is invalid
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    
    if "id" not in payload:
        raise ValueError("Payload must contain 'id' field")
    
    if not payload["id"]:
        raise ValueError("Payload 'id' cannot be empty")

def _generate_embedding_for_payload(payload: Dict[str, Any]) -> List[float]:
    """
    Generate embedding for payload content with caching.
    
    Args:
        payload: Payload dictionary
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If embedding generation fails
    """
    # Extract text for embedding
    data = payload.get("data", {})
    note = data.get("note", "")
    
    if not note:
        # Fallback to other text fields
        note = str(data) if data else payload.get("id", "")
    
    if not note.strip():
        raise ValueError("No text content found for embedding generation")
    
    # Generate embedding (this will use the enhanced caching)
    from app.utils.openai_client import get_openai_client
    openai_client = get_openai_client()
    return get_openai_embedding(note, openai_client)

def _get_version_history(payload_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve version history for an existing payload from Qdrant.
    
    Args:
        payload_id: The ID of the payload
        
    Returns:
        List of version history entries
    """
    try:
        from qdrant_client.http.exceptions import UnexpectedResponse
        
        existing = client.retrieve(
            collection_name=config.qdrant['collection'],
            ids=[str(to_uuid(payload_id))],
            with_payload=True
        )
        if existing and getattr(existing[0], "payload", None):
            meta = existing[0].payload.get("meta", {}) if isinstance(existing[0].payload, dict) else {}
            if meta and meta.get("version_history"):
                return meta["version_history"]
    except UnexpectedResponse:
        # Not found, start new history
        pass
    except Exception as e:
        logger.warning(f"[Qdrant] Could not fetch existing record for version history: {e}")
    
    return []

def _update_payload_metadata(payload: Dict[str, Any]) -> None:
    """
    Update payload metadata with version history and timestamps.
    
    Args:
        payload: Payload dictionary to update
    """
    meta = payload.setdefault("meta", {})
    
    # Add timestamps
    meta["timestamp"] = datetime.now().isoformat()
    meta["embedding_model"] = config.openai['embedding_model']
    meta["model_version"] = config.model_versions.get("embedding", "unknown")
    
    # Version history management
    version_history = _get_version_history(payload["id"])
    current_version = {
        "version": len(version_history) + 1,
        "timestamp": meta["timestamp"],
        "changes": "Updated via API"
    }
    version_history.append(current_version)
    meta["version_history"] = version_history[-10:]  # Keep last 10 versions

def _create_qdrant_point(payload: Dict[str, Any], embedding: List[float]):
    """
    Create a Qdrant point structure from payload and embedding.
    
    Args:
        payload: Dictionary containing payload data
        embedding: List of embedding values
        
    Returns:
        PointStruct for Qdrant
    """
    from qdrant_client.http.models import PointStruct
    
    return PointStruct(
        id=str(to_uuid(payload["id"])),
        vector=embedding,
        payload=payload
    )

def _perform_upsert(point) -> None:
    """
    Perform the actual upsert operation to Qdrant and clear cache.
    
    Args:
        point: PointStruct to upsert
    """
    try:
        client.upsert(
            collection_name=config.qdrant['collection'],
            points=[point]
        )
        
        # Record success metric
        if qdrant_operations:
            qdrant_operations.labels(operation='upsert', status='success').inc()
        
        # Invalidate search cache on upsert
        _search_cache.clear()
        
    except Exception:
        # Record failure metric
        if qdrant_operations:
            qdrant_operations.labels(operation='upsert', status='error').inc()
        raise

def qdrant_upsert(payload: Dict[str, Any]) -> None:
    """
    Upsert a payload into Qdrant vector database.
    
    Args:
        payload: Dictionary containing payload data
        
    Raises:
        ValueError: If payload is invalid
        Exception: If upsert operation fails
    """
    start_time = time.time()
    
    try:
        # Validate payload structure
        _validate_payload_structure(payload)
        
        # Generate embedding
        embedding = _generate_embedding_for_payload(payload)
        
        # Update metadata with version information
        _update_payload_metadata(payload)
        
        # Create Qdrant point
        point = _create_qdrant_point(payload, embedding)
        
        # Perform upsert
        _perform_upsert(point)
        
        logger.info(f"[Qdrant] Successfully upserted vector for ID: {payload['id']}")
        
        # Record latency
        if qdrant_search_latency:
            qdrant_search_latency.observe(time.time() - start_time)
        
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Failed to upsert vector for ID={payload.get('id', 'unknown')}: {str(e)}")
        raise  # Re-raise the exception so the router can handle it

def _parse_timestamp_to_unix(timestamp: str) -> float:
    """
    Parse ISO timestamp string to Unix timestamp.
    
    Args:
        timestamp: ISO timestamp string (e.g., "2023-01-01T00:00:00Z")
        
    Returns:
        Unix timestamp as float
        
    Raises:
        ValueError: If timestamp cannot be parsed
    """
    from datetime import datetime
    
    try:
        # Handle various ISO formats
        if timestamp.endswith('Z'):
            # UTC timezone
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif '+' in timestamp or timestamp.count('-') > 2:
            # Has timezone info
            dt = datetime.fromisoformat(timestamp)
        else:
            # Assume UTC if no timezone
            dt = datetime.fromisoformat(timestamp + '+00:00')
        
        return dt.timestamp()
    except ValueError as e:
        raise ValueError(f"Unable to parse timestamp '{timestamp}': {e}")


def _build_qdrant_filter(filters: dict):
    """
    Build Qdrant filter from search filters dictionary.
    
    Args:
        filters: Dictionary of filters to apply
        
    Returns:
        Qdrant filter object or None
    """
    if not filters:
        return None
    
    from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue, Range
    
    conditions = []
    
    # Handle various filter types
    for key, value in filters.items():
        if key == "timestamp" and isinstance(value, dict):
            # Handle timestamp range - convert ISO strings to Unix timestamps
            from_ts = value.get("from")
            to_ts = value.get("to")
            if from_ts or to_ts:
                range_condition = {}
                if from_ts:
                    try:
                        range_condition["gte"] = _parse_timestamp_to_unix(from_ts)
                    except ValueError as e:
                        logger.warning(f"Invalid 'from' timestamp '{from_ts}': {e}")
                        continue  # Skip this filter if timestamp is invalid
                if to_ts:
                    try:
                        range_condition["lte"] = _parse_timestamp_to_unix(to_ts)
                    except ValueError as e:
                        logger.warning(f"Invalid 'to' timestamp '{to_ts}': {e}")
                        continue  # Skip this filter if timestamp is invalid
                
                if range_condition:  # Only add if we have valid timestamps
                    conditions.append(
                        FieldCondition(
                            key="meta.timestamp",
                            range=Range(**range_condition)
                        )
                    )
        elif isinstance(value, list):
            # Handle list values (match any)
            conditions.append(
                FieldCondition(
                    key=f"meta.{key}",
                    match=MatchAny(any=value)
                )
            )
        else:
            # Handle single values
            conditions.append(
                FieldCondition(
                    key=f"meta.{key}" if key != "type" else key,
                    match=MatchValue(value=value)
                )
            )
    
    return Filter(must=conditions) if conditions else None

def _process_qdrant_results(search_result):
    """Process Qdrant search results into standardized format."""
    results = []
    for result in search_result:
        payload = getattr(result, "payload", {})
        if payload is None:
            payload = {}
        meta = payload.get("meta", {})
        results.append({
            "id": str(result.id),
            "score": float(result.score),
            "note": payload.get("data", {}).get("note", ""),
            "timestamp": meta.get("timestamp", ""),
            "source": meta.get("source", ""),
            "type": payload.get("type", ""),
            "priority": payload.get("priority", ""),
            "embedding_model": meta.get("embedding_model", ""),
            "model_version": meta.get("model_version", "")
        })
    return results

def qdrant_search(query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    """
    Search for semantically similar content in Qdrant, with optional metadata filtering.
    Uses advanced caching with TTL and smart eviction.
    
    Args:
        query: Search query string
        top_k: Number of results to return (default: 5)
        filters: Dict of metadata filters (model_version, embedding_model, type, timestamp)
        
    Returns:
        List of search results with metadata
        
    Raises:
        ValueError: If query is invalid
    """
    # Generate cache key
    cache_key = _search_cache_key(query, top_k, filters or {})
    
    # Check cache first
    cached_result = _search_cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Qdrant search cache hit for query: {query[:50]}...")
        return cached_result
    
    start_time = time.time()
    
    try:
        # Validate inputs
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        if top_k <= 0 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        
        # Import here to avoid circular imports
        try:
            from qdrant_client.http.models import SearchParams
        except ImportError:
            raise ImportError("qdrant-client package is required. Please install it.")
        
        # Generate query embedding
        from app.utils.openai_client import get_openai_client
        openai_client = get_openai_client()
        query_vector = get_openai_embedding(query, openai_client)
        
        if not query_vector:
            raise ValueError("Query embedding is empty")
        
        # Build filters
        qdrant_filter = _build_qdrant_filter(filters or {})
        
        # Perform search with optimized parameters
        search_result = client.search(
            collection_name=config.qdrant['collection'],
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(
                hnsw_ef=128,  # Higher ef for better recall
                exact=False   # Use approximate search for speed
            ),
            query_filter=qdrant_filter
        )
        
        # Process results
        results = _process_qdrant_results(search_result)
        
        # Cache the results
        _search_cache.set(cache_key, results)
        
        # Record metrics
        if qdrant_search_latency:
            qdrant_search_latency.observe(time.time() - start_time)
        if qdrant_operations:
            qdrant_operations.labels(operation='search', status='success').inc()
        
        logger.info(f"[Qdrant] Search for query '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        # Record failure metric
        if qdrant_operations:
            qdrant_operations.labels(operation='search', status='error').inc()
            
        logger.exception(f"[Qdrant ERROR] Search failed for query='{query}': {str(e)}")
        raise  # Re-raise the exception so the router can handle it

def get_qdrant_stats() -> Dict[str, Any]:
    """Get comprehensive Qdrant performance statistics."""
    try:
        health_data = _get_qdrant_health()
        
        # Add cache statistics
        cache_stats = {
            "search_cache": _search_cache.stats(),
            "vector_cache": _vector_cache.stats(),
            "collection_info_cache": _collection_info_cache.stats()
        }
        
        return {
            **health_data,
            "cache_statistics": cache_stats,
            "performance_optimizations": {
                "grpc_enabled": True,
                "connection_timeout": config.qdrant['timeout'],
                "search_cache_ttl": SEARCH_CACHE_CONFIG.ttl_seconds,
                "smart_eviction": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get Qdrant stats: {e}")
        return {"status": "error", "error": str(e)}

# Async version for better integration with async codebases
async def qdrant_search_async(query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    """
    Async version of qdrant_search for better performance in async contexts.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, qdrant_search, query, top_k, filters)
