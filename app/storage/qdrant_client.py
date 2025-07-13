from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, SearchParams, PointStruct
from openai import OpenAI
from uuid import uuid5, NAMESPACE_URL
from app.utils.logger import logger
import os

client = QdrantClient("qdrant", port=6333)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def store_vector(payload):
    note = payload.data.get("note")
    if not note:
        raise ValueError("Payload 'data.note' is required for vectorization.")

    try:
        model_name = "text-embedding-3-small"
        response = openai_client.embeddings.create(
            model=model_name,
            input=note
        )
        vector = response.data[0].embedding
    except Exception as e:
        logger.error(f"[OpenAI ERROR] Failed to embed note: {e}")
        return

    try:
        # Convert string IDs to UUIDv5 if not already an int
        point_id = payload.id
        if not isinstance(point_id, int):
            point_id = str(uuid5(NAMESPACE_URL, str(payload.id)))

        # Add embedding model to metadata
        payload.metadata["embedding_model"] = model_name

        client.upsert(
            collection_name="second_brain",
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload.dict()
                )
            ]
        )
        logger.info(f"[Qdrant] Stored vector for ID: {point_id}")
    except Exception as e:
        logger.error(f"[Qdrant ERROR] Failed to upsert vector: {e}")

def qdrant_search(query, top_k=5):
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        vector = response.data[0].embedding
    except Exception as e:
        logger.error(f"[OpenAI ERROR] Failed to embed search query: {e}")
        return []

    try:
        hits = client.search(
            collection_name="second_brain",
            query_vector=vector,
            limit=top_k
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "note": hit.payload.get("data", {}).get("note", ""),
                "timestamp": hit.payload.get("metadata", {}).get("timestamp", ""),
                "source": hit.payload.get("metadata", {}).get("source", "")
            }
            for hit in hits
        ]
    except Exception as e:
        logger.error(f"[Qdrant ERROR] Search failed: {e}")
        return []
