# app/utils/openai_client.py

import time
from openai import OpenAI
from app.utils.logger import logger
from app.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

client = OpenAI(api_key=Config.OPENAI_API_KEY)

@retry(
    stop=stop_after_attempt(Config.OPENAI_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=Config.OPENAI_RETRY_MULTIPLIER,
        min=Config.OPENAI_RETRY_MIN_WAIT,
        max=Config.OPENAI_RETRY_MAX_WAIT
    ),
    retry=retry_if_exception_type(Exception)
)
def get_openai_embedding(text: str) -> list:
    try:
        logger.debug(f"Generating embedding for input of length {len(text)} using model {Config.OPENAI_EMBEDDING_MODEL}")

        start_time = time.time()
        response = client.embeddings.create(
            input=text,
            model=Config.OPENAI_EMBEDDING_MODEL
        )
        duration = time.time() - start_time
        logger.info(f"Embedding generated in {duration:.2f}s for input of length {len(text)}")

        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        logger.exception(f"[OpenAI ERROR] Failed to get embedding: {str(e)}")
        raise
