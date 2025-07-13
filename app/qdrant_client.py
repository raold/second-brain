from uuid import uuid5, NAMESPACE_URL, UUID
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, SearchParams, Distance, VectorParams
from app.utils.logger import logger
from app.utils.openai_client import get_openai_embedding
from app.config import Config

client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)

COLLECTION_NAME = Config.QDRANT_COLLECTION
EXPECTED_DIMENSION = Config.QDRANT_VECTOR_SIZE

def recreate_collection_if_needed():
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        current_dim = collection_info.config.params.vectors.size
        if current_dim != EXPECTED_DIMENSION:
            logger.info(f"Qdrant collection '{COLLECTION_NAME}' has dim {current_dim}, recreating to dim {EXPECTED_DIMENSION}.")
            client.recreate_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EXPECTED_DIMENSION, distance=Distance[Config.QDRANT_DISTANCE.upper()])
            )
        else:
            logger.info(f"Qdrant collection '{COLLECTION_NAME}' already has correct dimension {current_dim}.")
    except Exception as e:
        logger.warning(f"Collection '{COLLECTION_NAME}' does not exist or failed to fetch. Creating new collection.")
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EXPECTED_DIMENSION, distance=Distance[Config.QDRANT_DISTANCE.upper()])
        )

recreate_collection_if_needed()

def to_uuid(text: str) -> UUID:
    return uuid5(NAMESPACE_URL, text)

def qdrant_upsert(payload: dict):
    try:
        vector = get_openai_embedding(payload["data"]["note"])
        if len(vector) != EXPECTED_DIMENSION:
            logger.error(f"[Qdrant ERROR] Embedding size mismatch: got {len(vector)} expected {EXPECTED_DIMENSION}")
            return

        payload["metadata"]["embedding_model"] = Config.OPENAI_EMBEDDING_MODEL
        point = PointStruct(
            id=to_uuid(payload["id"]),
            vector=vector,
            payload=payload
        )

        logger.info(f"Upserting point ID={payload['id']} into {COLLECTION_NAME}")
        result = client.upsert(collection_name=COLLECTION_NAME, points=[point])
        logger.info(f"Qdrant upsert response: {result}")
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Failed to upsert vector for ID={payload['id']}: {str(e)}")

def qdrant_search(query: str, top_k: int = 5):
    try:
        query_vector = get_openai_embedding(query)
        if len(query_vector) != EXPECTED_DIMENSION:
            logger.error(f"[Qdrant ERROR] Query embedding size mismatch: got {len(query_vector)} expected {EXPECTED_DIMENSION}")
            return []

        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False)
        )

        logger.info(f"Search query: '{query}' returned {len(search_result)} results")
        results = []
        for result in search_result:
            payload = result.payload
            results.append({
                "id": str(result.id),
                "score": result.score,
                "note": payload.get("data", {}).get("note"),
                "timestamp": payload.get("metadata", {}).get("timestamp", ""),
                "source": payload.get("metadata", {}).get("source", "")
            })

        return results
    except Exception as e:
        logger.exception(f"[Qdrant ERROR] Search failed: {str(e)}")
        return []
