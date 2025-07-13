# app/router.py

from fastapi import APIRouter, Request, Depends
from app.auth import verify_token
from app.qdrant_client import qdrant_upsert, qdrant_search
from app.utils.logger import logger

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/ingest")
async def ingest_endpoint(request: Request, _: None = Depends(verify_token)):
    payload = await request.json()
    logger.info(f"Received ingestion request: {payload.get('id')}")
    qdrant_upsert(payload)
    return {"status": "ingested", "id": payload.get("id")}

@router.get("/search")
async def search_endpoint(q: str, _: None = Depends(verify_token)):
    logger.info(f"Received search query: '{q}'")
    results = qdrant_search(q)
    return {"query": q, "results": results}
