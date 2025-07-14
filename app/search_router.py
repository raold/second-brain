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


# app/utils/openai_client.py
import time
import openai
from app.config import Config
from app.utils.logger import get_logger

logger = get_logger()


def get_openai_embedding(text: str) -> list:
    start_time = time.time()

    logger.debug(
        "Generating embedding",
        extra={
            "input_length": len(text),
            "model": Config.OPENAI_EMBEDDING_MODEL,
        }
    )

    response = openai.Embedding.create(
        input=text,
        model=Config.OPENAI_EMBEDDING_MODEL
    )

    embedding = response["data"][0]["embedding"]
    duration = time.time() - start_time

    logger.info(f"Embedding generated in {duration:.2f}s")
    return embedding
