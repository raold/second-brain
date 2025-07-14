# app/search_router.py
from fastapi import APIRouter, Header
from app.models import Payload

router = APIRouter()

@router.post("/ingest")
async def ingest(
    payload: Payload,
    authorization: str = Header(None),
):
    # You can add validation here if needed
    return {"message": "Payload ingested successfully"}
