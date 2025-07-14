# app/search_router.py
from fastapi import APIRouter, Body, Header
from app.models import Payload

router = APIRouter()

@router.post("/ingest")
async def ingest(
    payload: Payload = Body(...),
    authorization: str = Header(None),
):
    # Your processing logic here
    return {"message": "Payload ingested successfully"}
