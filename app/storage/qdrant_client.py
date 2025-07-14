from uuid import uuid5, NAMESPACE_URL, UUID
from datetime import datetime
from typing import Union, Optional, List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue, SearchParams
from app.utils.logger import logger
from app.config import Config
from app.utils.openai_client import get_openai_embedding
import os
from openai import OpenAI

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
        
        payload["metadata"]["embedding_model"] = Config.OPENAI_EMBEDDING_MODEL
        payload["metadata"]["timestamp"] = datetime.now().isoformat()
        
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

def qdrant_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for semantically similar content in Qdrant.
    
    Args:
        query: Search query string
        top_k: Number of results to return (default: 5)
        
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

        # Search in Qdrant
        search_result = client.search(
            collection_name=Config.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False)
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
                "priority": result.payload.get("priority", "")
            }
            for result in search_result
        ]

        logger.info(f"[Qdrant] Search for query '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Search failed for query='{query}': {str(e)}")
        raise  # Re-raise the exception so the router can handle it
