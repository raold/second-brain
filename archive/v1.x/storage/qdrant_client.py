"""
Qdrant Vector Database Client for Second Brain Application.

This module provides a clean, high-performance interface to Qdrant vector database
with advanced caching, monitoring, and error handling.
"""
import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import NAMESPACE_URL, UUID, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue

from app.config import config
from app.utils.cache import get_cache
from app.utils.logger import logger
from app.utils.openai_client import get_openai_embedding, get_openai_client

# Initialize Qdrant client with connection pooling
client = QdrantClient(
    host=config.qdrant['host'], 
    port=config.qdrant['port'],
    timeout=config.qdrant['timeout'],  # 30 second timeout
    grpc_port=config.qdrant.get('grpc_port', 6334),  # Enable gRPC for better performance
    prefer_grpc=True
)

# Cache for search results
search_cache = get_cache('search')

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram
    search_cache_hit = Counter('search_cache_hit', 'Search result cache hits')
    search_cache_miss = Counter('search_cache_miss', 'Search result cache misses')
    qdrant_search_latency = Histogram('qdrant_search_latency_seconds', 'Qdrant search latency (seconds)')
except ImportError:
    search_cache_hit = search_cache_miss = qdrant_search_latency = None


def _search_cache_key(query: str, top_k: int = 5, filters: Optional[Dict] = None) -> str:
    """Create cache key for search results."""
    import json
    return f"search:{hash(query)}:{top_k}:{hash(json.dumps(filters, sort_keys=True) if filters else '')}"


def to_uuid(text: str) -> UUID:
    """Convert text to deterministic UUID using namespace."""
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string")
    return uuid5(NAMESPACE_URL, text)


def qdrant_upsert(payload: Dict[str, Any]) -> None:
    """
    Upsert a payload into Qdrant vector database.
    
    Args:
        payload: Dictionary containing payload data
        
    Raises:
        ValueError: If payload is invalid
        Exception: If upsert operation fails
    """
    try:
        # Validate payload structure
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")
        
        if "id" not in payload:
            raise ValueError("Payload must contain 'id' field")
        
        if "data" not in payload or "note" not in payload["data"]:
            raise ValueError("Payload must contain 'data.note' field")
        
        # Get OpenAI client
        openai_client = get_openai_client()
        
        # Generate embedding
        note_text = payload["data"]["note"]
        if not note_text or not isinstance(note_text, str):
            raise ValueError("Note text must be a non-empty string")
        
        embedding = get_openai_embedding(note_text, openai_client)
        if not embedding:
            raise ValueError("Generated embedding is empty")

        # Prepare payload with metadata
        if "meta" not in payload:
            payload["meta"] = {}
        
        # Add version info
        version_info = {
            "embedding_model": config.model_versions["embedding"],
            "model_version": config.model_versions["llm"],
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to fetch existing record for version history
        version_history = []
        try:
            existing = client.retrieve(
                collection_name=config.qdrant['collection'],
                ids=[str(to_uuid(payload["id"]))],
                with_payload=True
            )
            if existing and getattr(existing[0], "payload", None):
                meta = existing[0].payload.get("meta", {}) if isinstance(existing[0].payload, dict) else {}
                if meta and meta.get("version_history"):
                    version_history = meta["version_history"]
        except UnexpectedResponse:
            # Not found, start new history
            version_history = []
        except Exception as e:
            logger.warning(f"[Qdrant] Could not fetch existing record for version history: {e}")
        
        # Update metadata
        version_history.append(version_info)
        payload["meta"].update({
            "embedding_model": version_info["embedding_model"],
            "model_version": version_info["model_version"],
            "timestamp": version_info["timestamp"],
            "version_history": version_history
        })
        
        # Create point for Qdrant
        point = PointStruct(
            id=str(to_uuid(payload["id"])),
            vector=embedding,
            payload=payload
        )

        # Upsert to Qdrant
        client.upsert(
            collection_name=config.qdrant['collection'],
            points=[point]
        )
        
        logger.info(f"[Qdrant] Successfully upserted vector for ID: {payload['id']}")
        
    except Exception as e:
        logger.error(f"[Qdrant] Failed to upsert vector for ID={payload.get('id', 'unknown')}: {str(e)}")
        raise


def _build_qdrant_filter(filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
    """Build Qdrant filter from filter dictionary."""
    if not filters:
        return None
    
    try:
        from qdrant_client.http import models as qmodels
        
        must = []
        
        # Handle different filter types
        for key, value in filters.items():
            if key == "user_id" and value:
                must.append(
                    qmodels.FieldCondition(
                        key=f"meta.{key}",
                        match=qmodels.MatchValue(value=value)
                    )
                )
            elif key == "tags" and value:
                # Support both single tag and list of tags
                if isinstance(value, list):
                    for tag in value:
                        must.append(
                            qmodels.FieldCondition(
                                key=f"meta.{key}",
                                match=qmodels.MatchValue(value=tag)
                            )
                        )
                else:
                    must.append(
                        qmodels.FieldCondition(
                            key=f"meta.{key}",
                            match=qmodels.MatchValue(value=value)
                        )
                    )
            elif key == "created_after" and value:
                must.append(
                    qmodels.FieldCondition(
                        key="meta.timestamp",
                        range=qmodels.Range(gte=value)
                    )
                )
            elif key == "created_before" and value:
                must.append(
                    qmodels.FieldCondition(
                        key="meta.timestamp",
                        range=qmodels.Range(lte=value)
                    )
                )
        
        return qmodels.Filter(must=must) if must else None
        
    except Exception as e:
        logger.error(f"[Qdrant] Error building filter: {e}")
        return None


def _process_qdrant_results(search_result) -> List[Dict[str, Any]]:
    """Process Qdrant search results into standardized format."""
    processed_results = []
    
    for result in search_result:
        try:
            # Extract payload
            payload = result.payload if hasattr(result, 'payload') else {}
            
            # Create standardized result
            processed_result = {
                "id": payload.get("id", "unknown"),
                "score": float(result.score) if hasattr(result, 'score') else 0.0,
                "data": payload.get("data", {}),
                "meta": payload.get("meta", {}),
                "vector_id": str(result.id) if hasattr(result, 'id') else None
            }
            
            processed_results.append(processed_result)
            
        except Exception as e:
            logger.error(f"[Qdrant] Error processing result: {e}")
            continue
    
    return processed_results


def qdrant_search(query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Search Qdrant vector database with caching and monitoring.
    
    Args:
        query: Search query string
        top_k: Number of results to return
        filters: Optional filters to apply
        
    Returns:
        List of search results
    """
    # Create cache key
    cache_key = _search_cache_key(query, top_k, filters)
    
    # Check cache first
    if search_cache:
        cached_result = search_cache.get(cache_key)
        if cached_result:
            if search_cache_hit:
                search_cache_hit.inc()
            logger.debug(f"[Qdrant] Cache hit for query: {query[:50]}...")
            return cached_result
    
    # Cache miss
    if search_cache_miss:
        search_cache_miss.inc()
    
    start_time = time.time()
    
    try:
        # Get OpenAI client and generate embedding
        openai_client = get_openai_client()
        query_embedding = get_openai_embedding(query, openai_client)
        
        if not query_embedding:
            logger.error("[Qdrant] Failed to generate query embedding")
            return []
        
        # Build filter
        qdrant_filter = _build_qdrant_filter(filters)
        
        # Search Qdrant
        search_result = client.search(
            collection_name=config.qdrant['collection'],
            query_vector=query_embedding,
            query_filter=qdrant_filter,
            limit=top_k
        )
        
        # Process results
        processed_results = _process_qdrant_results(search_result)
        
        # Cache results
        if search_cache:
            search_cache.set(cache_key, processed_results)
        
        # Record metrics
        search_time = time.time() - start_time
        if qdrant_search_latency:
            qdrant_search_latency.observe(search_time)
        
        logger.info(f"[Qdrant] Search completed in {search_time:.3f}s, {len(processed_results)} results")
        return processed_results
        
    except Exception as e:
        logger.error(f"[Qdrant] Search failed: {e}")
        return []


def qdrant_delete(record_id: str) -> bool:
    """
    Delete a record from Qdrant by ID.
    
    Args:
        record_id: The ID of the record to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        # Convert to UUID
        vector_id = str(to_uuid(record_id))
        
        # Delete from Qdrant
        client.delete(
            collection_name=config.qdrant['collection'],
            points_selector=[vector_id]
        )
        
        # Clear cache
        if search_cache:
            search_cache.clear()
        
        logger.info(f"[Qdrant] Successfully deleted record: {record_id}")
        return True
        
    except Exception as e:
        logger.error(f"[Qdrant] Failed to delete record {record_id}: {e}")
        return False


def qdrant_get_collection_info() -> Dict[str, Any]:
    """
    Get information about the Qdrant collection.
    
    Returns:
        Dictionary containing collection information
    """
    try:
        collection_info = client.get_collection(config.qdrant['collection'])
        
        return {
            "name": config.qdrant['collection'],
            "status": collection_info.status,
            "points_count": collection_info.points_count,
            "segments_count": collection_info.segments_count,
            # "disk_data_size": collection_info.disk_data_size,
            # "ram_data_size": collection_info.ram_data_size,
            "config": {
                "params": collection_info.config.params,
                "hnsw_config": collection_info.config.hnsw_config,
                "optimizer_config": collection_info.config.optimizer_config,
                "wal_config": collection_info.config.wal_config
            }
        }
        
    except Exception as e:
        logger.error(f"[Qdrant] Failed to get collection info: {e}")
        return {}


def qdrant_health_check() -> Dict[str, Any]:
    """
    Perform a health check on the Qdrant connection.
    
    Returns:
        Dictionary containing health status
    """
    health_status = {
        "healthy": False,
        "response_time": None,
        "error": None,
        "collection_exists": False,
        "points_count": 0
    }
    
    start_time = time.time()
    
    try:
        # Test basic connection
        collections = client.get_collections()
        response_time = time.time() - start_time
        
        health_status.update({
            "healthy": True,
            "response_time": response_time,
            "collections_count": len(collections.collections)
        })
        
        # Check if our collection exists
        try:
            collection_info = client.get_collection(config.qdrant['collection'])
            health_status.update({
                "collection_exists": True,
                "points_count": collection_info.points_count or 0
            })
        except UnexpectedResponse:
            health_status["collection_exists"] = False
            
    except Exception as e:
        health_status.update({
            "healthy": False,
            "error": str(e),
            "response_time": time.time() - start_time
        })
    
    return health_status


def clear_search_cache() -> None:
    """Clear the search cache."""
    if search_cache:
        search_cache.clear()
        logger.info("[Qdrant] Search cache cleared")


def get_qdrant_stats() -> Dict[str, Any]:
    """
    Get Qdrant statistics (alias for qdrant_get_collection_info).
    
    Returns:
        Dictionary containing Qdrant statistics
    """
    return qdrant_get_collection_info()


# Export main functions
__all__ = [
    'qdrant_upsert',
    'qdrant_search', 
    'qdrant_delete',
    'qdrant_get_collection_info',
    'qdrant_health_check',
    'clear_search_cache',
    'get_qdrant_stats',
    'to_uuid'
]
