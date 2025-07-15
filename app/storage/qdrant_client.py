import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from cachetools import LRUCache, cached
from openai import OpenAI
from qdrant_client import QdrantClient

from app.config import Config
from app.utils.logger import logger
from app.utils.openai_client import get_openai_embedding

# Initialize Qdrant client
client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)

# LRU cache for search results (up to 1000 unique queries)
_search_cache = LRUCache(maxsize=1000)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram
    search_cache_hit = Counter('search_cache_hit', 'Search result cache hits')
    search_cache_miss = Counter('search_cache_miss', 'Search result cache misses')
    qdrant_search_latency = Histogram('qdrant_search_latency_seconds', 'Qdrant search latency (seconds)')
except ImportError:
    search_cache_hit = search_cache_miss = qdrant_search_latency = None

if TYPE_CHECKING:
    pass  # type: ignore

def _search_cache_key(query, top_k=5, filters=None):
    import json
    return (query, top_k, json.dumps(filters, sort_keys=True))

def to_uuid(text: str) -> UUID:
    """Convert text to deterministic UUID using namespace."""
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string")
    return uuid5(NAMESPACE_URL, text)

def get_openai_client() -> 'OpenAI':
    """Get OpenAI client with API key validation."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package is required for embedding. Please install it.")
    api_key = Config.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

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
        try:
            from qdrant_client.http.exceptions import UnexpectedResponse
            from qdrant_client.http.models import PointStruct
        except ImportError:
            raise ImportError("qdrant-client package is required. Please install it.")
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

        # Prepare payload with meta
        if "meta" not in payload:
            payload["meta"] = {}
        # Version info to append
        version_info = {
            "embedding_model": Config.MODEL_VERSIONS["embedding"],
            "model_version": Config.MODEL_VERSIONS["llm"],
            "timestamp": datetime.now().isoformat(),
        }
        # Try to fetch existing record for version history
        version_history = []
        try:
            existing = client.retrieve(
                collection_name=Config.QDRANT_COLLECTION,
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
        version_history = version_history + [version_info]
        payload["meta"]["embedding_model"] = version_info["embedding_model"]
        payload["meta"]["model_version"] = version_info["model_version"]
        payload["meta"]["timestamp"] = version_info["timestamp"]
        payload["meta"]["version_history"] = version_history
        
        # Create point for Qdrant
        point = PointStruct(
            id=str(to_uuid(payload["id"])),
            vector=embedding,
            payload=payload
        )

        # Upsert to Qdrant
        client.upsert(
            collection_name=Config.QDRANT_COLLECTION,
            points=[point]
        )
        
        logger.info(f"[Qdrant] Successfully upserted vector for ID: {payload['id']}")
        
        # Invalidate search cache on upsert
        _search_cache.clear()
        
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Failed to upsert vector for ID={payload.get('id', 'unknown')}: {str(e)}")
        raise  # Re-raise the exception so the router can handle it

def _build_qdrant_filter(filters):
    from qdrant_client.http import models as qmodels
    must = []
    if filters.get("model_version"):
        must.append(qmodels.FieldCondition(
            key="meta.model_version",
            match=qmodels.MatchValue(value=filters["model_version"])
        ))
    if filters.get("embedding_model"):
        must.append(qmodels.FieldCondition(
            key="meta.embedding_model",
            match=qmodels.MatchValue(value=filters["embedding_model"])
        ))
    if filters.get("type"):
        must.append(qmodels.FieldCondition(
            key="type",
            match=qmodels.MatchValue(value=filters["type"])
        ))
    if filters.get("timestamp"):
        ts = filters["timestamp"]
        range_args = {}
        if ts.get("from"):
            try:
                from dateutil import parser as date_parser
                range_args["gte"] = int(date_parser.parse(ts["from"]).timestamp())
            except Exception:
                pass
        if ts.get("to"):
            try:
                from dateutil import parser as date_parser
                range_args["lte"] = int(date_parser.parse(ts["to"]).timestamp())
            except Exception:
                pass
        if range_args:
            must.append(qmodels.FieldCondition(
                key="meta.timestamp",
                range=qmodels.Range(**range_args)
            ))
    return qmodels.Filter(must=must) if must else None

def _process_qdrant_results(search_result):
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

@cached(_search_cache, key=lambda query, top_k=5, filters=None: _search_cache_key(query, top_k, filters or {}))
def qdrant_search(query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    """
    Search for semantically similar content in Qdrant, with optional metadata filtering.
    Args:
        query: Search query string
        top_k: Number of results to return (default: 5)
        filters: Dict of metadata filters (model_version, embedding_model, type, timestamp)
    Returns:
        List of search results with metadata
    Raises:
        ValueError: If query is invalid
    """
    filters = filters or {}
    cache_key = _search_cache_key(query, top_k, filters)
    if cache_key in _search_cache:
        if search_cache_hit:
            search_cache_hit.inc()
        return _search_cache[cache_key]
    if search_cache_miss:
        search_cache_miss.inc()
    start = time.time()
    try:
        try:
            from qdrant_client.http.models import SearchParams
        except ImportError:
            raise ImportError("qdrant-client package is required. Please install it.")
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        if top_k <= 0 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        openai_client = get_openai_client()
        query_vector = get_openai_embedding(query, openai_client)
        if not query_vector:
            raise ValueError("Query embedding is empty")
        qdrant_filter = _build_qdrant_filter(filters)
        search_result = client.search(
            collection_name=Config.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False),
            query_filter=qdrant_filter
        )
        results = _process_qdrant_results(search_result)
        logger.info(f"[Qdrant] Search for query '{query}' returned {len(results)} results")
        if qdrant_search_latency:
            qdrant_search_latency.observe(time.time() - start)
        return results
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Search failed for query='{query}': {str(e)}")
        raise  # Re-raise the exception so the router can handle it
