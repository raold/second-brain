from uuid import uuid5, NAMESPACE_URL, UUID
from datetime import datetime
from typing import Union, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue, SearchParams
from app.utils.logger import logger
from app.config import Config
from app.utils.openai_client import get_openai_embedding
import os
from openai import OpenAI

client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)

def to_uuid(text: str) -> UUID:
    return uuid5(NAMESPACE_URL, text)

def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def qdrant_upsert(payload: dict):
    try:
        openai_client = get_openai_client()
        embedding = get_openai_embedding(payload["data"]["note"], openai_client)
        if not embedding:
            raise ValueError("Generated embedding is empty")

        payload["metadata"]["embedding_model"] = Config.OPENAI_EMBEDDING_MODEL
        point = PointStruct(
            id=to_uuid(payload["id"]),
            vector=embedding,
            payload=payload
        )

        client.upsert(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            points=[point]
        )
        logger.info(f"[Qdrant] Upserted vector for ID: {payload['id']}")
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Failed to upsert vector for ID={payload['id']}: {str(e)}")

def qdrant_search(query: str, top_k: int = 5):
    try:
        openai_client = get_openai_client()
        query_vector = get_openai_embedding(query, openai_client)
        if not query_vector:
            raise ValueError("Query embedding is empty")

        search_result = client.search(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False)
        )

        logger.info(f"[Qdrant] Search for query '{query}' returned {len(search_result)} results")
        results = [
            {
                "id": str(result.id),
                "score": result.score,
                "note": result.payload.get("data", {}).get("note"),
                "timestamp": result.payload.get("metadata", {}).get("timestamp"),
                "source": result.payload.get("metadata", {}).get("source")
            }
            for result in search_result
        ]

        return results
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Search failed for query='{query}': {str(e)}")
        return []
