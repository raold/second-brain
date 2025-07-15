# app/router.py

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth import verify_token
from app.models import Payload
from app.storage.markdown_writer import write_markdown
from app.storage.qdrant_client import qdrant_search, qdrant_upsert, to_uuid, client
from qdrant_client.http.exceptions import UnexpectedResponse
from app.utils.logger import logger
from app.config import Config

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

@router.post("/ingest")
async def ingest_endpoint(payload: Payload, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Ingest a payload into the second brain system.
    
    Args:
        payload: The payload to ingest
        
    Returns:
        Dict containing status and payload ID
        
    Raises:
        HTTPException: If ingestion fails
    """
    try:
        logger.info(f"Received ingestion request: {payload.id}")
        
        # Store in markdown file
        write_markdown(payload)
        
        # Store in vector database
        qdrant_upsert(payload.model_dump())
        
        logger.info(f"Successfully ingested payload: {payload.id}")
        return {"status": "ingested", "id": payload.id}
        
    except Exception as e:
        logger.error(f"Failed to ingest payload {payload.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest payload: {str(e)}"
        ) from e

@router.get("/search")
async def search_endpoint(
    q: str,
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    embedding_model: Optional[str] = Query(None, description="Filter by embedding model"),
    type: Optional[str] = Query(None, description="Filter by record type"),
    timestamp_from: Optional[str] = Query(None, description="Filter: timestamp >= (ISO8601)"),
    timestamp_to: Optional[str] = Query(None, description="Filter: timestamp <= (ISO8601)"),
    _: None = Depends(verify_token)
) -> dict:
    """
    Search for semantically similar content, with optional metadata filtering.
    
    Args:
        q: Search query string
        model_version: Filter by model version
        embedding_model: Filter by embedding model
        type: Filter by record type
        timestamp_from: Filter: timestamp >= (ISO8601)
        timestamp_to: Filter: timestamp <= (ISO8601)
    Returns:
        Dict containing query and search results
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info("Received search query", query=q, model_version=model_version, embedding_model=embedding_model, type=type, timestamp_from=timestamp_from, timestamp_to=timestamp_to)
        filters = {}
        if model_version:
            filters["model_version"] = model_version
        if embedding_model:
            filters["embedding_model"] = embedding_model
        if type:
            filters["type"] = type
        if timestamp_from or timestamp_to:
            filters["timestamp"] = {"from": timestamp_from, "to": timestamp_to}
        results = qdrant_search(q, filters=filters)
        logger.info("Search completed", query=q, num_results=len(results))
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        ) from e

@router.get("/ranked-search", tags=["Search"])
async def ranked_search_endpoint(
    q: str,
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    embedding_model: Optional[str] = Query(None, description="Filter by embedding model"),
    type: Optional[str] = Query(None, description="Filter by record type"),
    timestamp_from: Optional[str] = Query(None, description="Filter: timestamp >= (ISO8601)"),
    timestamp_to: Optional[str] = Query(None, description="Filter: timestamp <= (ISO8601)"),
    _: None = Depends(verify_token)
) -> dict:
    """
    Hybrid ranked search: combines vector similarity and metadata relevance.
    Returns ranked results with score explanations.
    """
    try:
        logger.info("Received ranked search query", query=q, model_version=model_version, embedding_model=embedding_model, type=type, timestamp_from=timestamp_from, timestamp_to=timestamp_to)
        filters = {}
        if model_version:
            filters["model_version"] = model_version
        if embedding_model:
            filters["embedding_model"] = embedding_model
        if type:
            filters["type"] = type
        if timestamp_from or timestamp_to:
            filters["timestamp"] = {"from": timestamp_from, "to": timestamp_to}
        # Use hybrid search
        results = qdrant_search(q, filters=filters)
        # Compute metadata score and final score
        ranked = []
        for r in results:
            meta_score = 0.0
            explanation = []
            if model_version:
                if r["model_version"] == model_version:
                    meta_score += 0.5
                    explanation.append("model_version match")
            if embedding_model:
                if r["embedding_model"] == embedding_model:
                    meta_score += 0.2
                    explanation.append("embedding_model match")
            if type:
                if r["type"] == type:
                    meta_score += 0.2
                    explanation.append("type match")
            # Timestamp range bonus
            if filters.get("timestamp"):
                ts = r.get("timestamp")
                tf = filters["timestamp"].get("from")
                tt = filters["timestamp"].get("to")
                if ts and ((not tf or ts >= tf) and (not tt or ts <= tt)):
                    meta_score += 0.1
                    explanation.append("timestamp in range")
            # Normalize meta_score to max 1.0
            meta_score = min(meta_score, 1.0)
            vector_score = r["score"]
            final_score = 0.8 * vector_score + 0.2 * meta_score
            ranked.append({
                **r,
                "vector_score": vector_score,
                "metadata_score": meta_score,
                "final_score": final_score,
                "explanation": ", ".join(explanation) or "vector only"
            })
        ranked.sort(key=lambda x: x["final_score"], reverse=True)
        logger.info("Ranked search completed", query=q, num_results=len(ranked))
        return {"query": q, "results": ranked}
    except Exception as e:
        logger.error(f"Ranked search failed for query '{q}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranked search failed: {str(e)}"
        ) from e

@router.get("/records/{id}/version-history", tags=["Records"])
async def get_version_history(id: str, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Retrieve the version history for a given record ID.
    """
    try:
        result = client.retrieve(
            collection_name=Config.QDRANT_COLLECTION,
            ids=[to_uuid(id)],
            with_payload=True
        )
        if not result or not result[0].payload.get("metadata", {}).get("version_history"):
            raise HTTPException(status_code=404, detail="Version history not found for this record.")
        return {"id": id, "version_history": result[0].payload["metadata"]["version_history"]}
    except UnexpectedResponse:
        raise HTTPException(status_code=404, detail="Record not found.")
    except Exception as e:
        logger.error(f"Failed to fetch version history for {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch version history: {e}")

@router.get("/records", tags=["Records"])
async def list_records(
    type: Optional[str] = Query(None, description="Filter by record type"),
    note: Optional[str] = Query(None, description="Filter by note substring"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    _: None = Depends(verify_token)
) -> dict:
    """
    List records with optional filtering and pagination.
    """
    try:
        # Qdrant scroll API for pagination
        scroll_result = client.scroll(
            collection_name=Config.QDRANT_COLLECTION,
            limit=limit,
            offset=offset,
            with_payload=True
        )
        records = []
        for point in scroll_result[0]:
            payload = point.payload
            meta = payload.get("metadata", {})
            data = payload.get("data", {})
            # Filtering
            if type and payload.get("type") != type:
                continue
            if note and note.lower() not in data.get("note", "").lower():
                continue
            records.append({
                "id": str(point.id),
                "note": data.get("note", ""),
                "type": payload.get("type", ""),
                "timestamp": meta.get("timestamp", "")
            })
        return {"records": records, "total": len(records)}
    except Exception as e:
        logger.error(f"Failed to list records: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list records: {e}")

@router.get("/models", tags=["Models"])
def get_models():
    """
    Returns the current LLM and embedding model versions in use.
    """
    return {"model_versions": Config.MODEL_VERSIONS}
