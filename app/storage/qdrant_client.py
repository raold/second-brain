import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import NAMESPACE_URL, UUID, uuid5

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, SearchParams
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import Config
from app.utils.logger import logger
from app.utils.openai_client import get_openai_embedding
import time
from dateutil import parser as date_parser

# Initialize Qdrant client
client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)

def to_uuid(text: str) -> UUID:
    """Convert text to deterministic UUID using namespace."""
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string")
    return uuid5(NAMESPACE_URL, text)

def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key validation."""
    api_key = os.getenv("OPENAI_API_KEY")
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
        if "metadata" not in payload:
            payload["metadata"] = {}
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
                ids=[to_uuid(payload["id"])],
                with_payload=True
            )
            if existing and existing[0].payload.get("metadata", {}).get("version_history"):
                version_history = existing[0].payload["metadata"]["version_history"]
        except UnexpectedResponse:
            # Not found, start new history
            version_history = []
        except Exception as e:
            logger.warning(f"[Qdrant] Could not fetch existing record for version history: {e}")
        version_history = version_history + [version_info]
        payload["metadata"]["embedding_model"] = version_info["embedding_model"]
        payload["metadata"]["model_version"] = version_info["model_version"]
        payload["metadata"]["timestamp"] = version_info["timestamp"]
        payload["metadata"]["version_history"] = version_history
        
        # Create point for Qdrant
        point = PointStruct(
            id=to_uuid(payload["id"]),
            vector=embedding,
            payload=payload
        )

        # Upsert to Qdrant
        client.upsert(
            collection_name=Config.QDRANT_COLLECTION,
            points=[point]
        )
        
        logger.info(f"[Qdrant] Successfully upserted vector for ID: {payload['id']}")
        
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Failed to upsert vector for ID={payload.get('id', 'unknown')}: {str(e)}")
        raise  # Re-raise the exception so the router can handle it

def qdrant_search(query: str, top_k: int = 5, filters: dict = None) -> List[Dict[str, Any]]:
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
    try:
        # Validate query
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        if top_k <= 0 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        # Get OpenAI client
        openai_client = get_openai_client()
        # Generate query embedding
        query_vector = get_openai_embedding(query, openai_client)
        if not query_vector:
            raise ValueError("Query embedding is empty")
        # Build Qdrant filter
        qdrant_filter = None
        if filters:
            from qdrant_client.http import models as qmodels
            must = []
            if filters.get("model_version"):
                must.append(qmodels.FieldCondition(
                    key="metadata.model_version",
                    match=qmodels.MatchValue(value=filters["model_version"])
                ))
            if filters.get("embedding_model"):
                must.append(qmodels.FieldCondition(
                    key="metadata.embedding_model",
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
                    # Convert ISO8601 to epoch seconds
                    try:
                        range_args["gte"] = int(date_parser.parse(ts["from"]).timestamp())
                    except Exception:
                        pass
                if ts.get("to"):
                    try:
                        range_args["lte"] = int(date_parser.parse(ts["to"]).timestamp())
                    except Exception:
                        pass
                if range_args:
                    must.append(qmodels.FieldCondition(
                        key="metadata.timestamp",
                        range=qmodels.Range(**range_args)
                    ))
            if must:
                qdrant_filter = qmodels.Filter(must=must)
        # Search in Qdrant
        search_result = client.search(
            collection_name=Config.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False),
            query_filter=qdrant_filter
        )
        # Process results
        results = [
            {
                "id": str(result.id),
                "score": float(result.score),
                "note": result.payload.get("data", {}).get("note", ""),
                "timestamp": result.payload.get("metadata", {}).get("timestamp", ""),
                "source": result.payload.get("metadata", {}).get("source", ""),
                "type": result.payload.get("type", ""),
                "priority": result.payload.get("priority", ""),
                "embedding_model": result.payload.get("metadata", {}).get("embedding_model", ""),
                "model_version": result.payload.get("metadata", {}).get("model_version", "")
            }
            for result in search_result
        ]
        logger.info(f"[Qdrant] Search for query '{query}' returned {len(results)} results")
        return results
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Search failed for query='{query}': {str(e)}")
        raise  # Re-raise the exception so the router can handle it
