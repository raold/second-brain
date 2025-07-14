# app/router.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_token
from app.models import Payload
from app.storage.markdown_writer import write_markdown
from app.storage.qdrant_client import qdrant_search, qdrant_upsert
from app.utils.logger import logger

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
async def search_endpoint(q: str, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Search for semantically similar content.
    
    Args:
        q: Search query string
        
    Returns:
        Dict containing query and search results
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"Received search query: '{q}'")
        results = qdrant_search(q)
        
        logger.info(f"Search completed for query '{q}' with {len(results)} results")
        return {"query": q, "results": results}
        
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        ) from e
