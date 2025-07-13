from fastapi import APIRouter, Query, Header, HTTPException, Body
from app.storage.qdrant_client import qdrant_search
from app.handlers import dispatch_payload, categorize_payload
from app.models import Payload
import os

router = APIRouter()

API_KEY = os.getenv("SECOND_BRAIN_API_KEY")

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/search")
async def search(
    q: str = Query(..., description="Query string to search semantic memory"),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or malformed authorization header")

    token = authorization.split(" ")[1]
    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    results = qdrant_search(q)
    return {"query": q, "results": results}


@router.post("/ingest")
async def ingest(
    payload: Payload = Body(...),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or malformed authorization header")

    token = authorization.split(" ")[1]
    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    payload = categorize_payload(payload)
    dispatch_payload(payload)
    return {"status": "ingested", "id": payload.id}
