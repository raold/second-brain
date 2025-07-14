# app/router.py

from fastapi import APIRouter, Depends
from app.auth import verify_token
from app.storage.qdrant_client import qdrant_search, qdrant_upsert
from app.storage.markdown_writer import write_markdown
from app.models import Payload
from app.utils.logger import logger

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/ingest")
async def ingest_endpoint(payload: Payload, _: None = Depends(verify_token)):
    logger.info(f"Received ingestion request: {payload.id}")
    
    # Store in markdown file
    write_markdown(payload)
    
    # Store in vector database
    qdrant_upsert(payload.model_dump())
    
    return {"status": "ingested", "id": payload.id}

@router.get("/search")
async def search_endpoint(q: str, _: None = Depends(verify_token)):
    logger.info(f"Received search query: '{q}'")
    results = qdrant_search(q)
    return {"query": q, "results": results}
