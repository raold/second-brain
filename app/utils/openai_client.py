# app/utils/openai_client.py

import time
from typing import List, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import Config
from app.utils.logger import get_logger

logger = get_logger()

@retry(
    stop=stop_after_attempt(Config.OPENAI_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=Config.OPENAI_RETRY_MULTIPLIER,
        min=Config.OPENAI_RETRY_MIN_WAIT,
        max=Config.OPENAI_RETRY_MAX_WAIT
    )
)
def get_openai_embedding(text: str, openai_client=None) -> List[float]:
    """
    Generate embedding for text using OpenAI API with retry logic.
    
    Args:
        text: Text to embed
        openai_client: Optional OpenAI client instance
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If text is invalid
        Exception: If API call fails after retries
    """
    start_time = time.time()
    
    # Validate input
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string")
    
    if len(text.strip()) == 0:
        raise ValueError("Text cannot be empty or whitespace only")
    
    # Truncate text if too long (OpenAI has limits)
    max_length = 8192  # Conservative limit for embedding models
    if len(text) > max_length:
        logger.warning(f"Text truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]
    
    logger.debug(
        "Generating embedding",
        extra={
            "input_length": len(text),
            "model": Config.OPENAI_EMBEDDING_MODEL,
        }
    )

    try:
        # Use the provided client or the global openai module
        client = openai_client or openai
        
        response = client.Embedding.create(
            input=text,
            model=Config.OPENAI_EMBEDDING_MODEL
        )
        
        # Validate response
        if not response or "data" not in response:
            raise ValueError("Invalid response from OpenAI API")
        
        if not response["data"] or len(response["data"]) == 0:
            raise ValueError("No embedding data in response")
        
        embedding = response["data"][0]["embedding"]
        
        # Validate embedding
        if not embedding or not isinstance(embedding, list):
            raise ValueError("Invalid embedding format in response")
        
        if len(embedding) != Config.QDRANT_VECTOR_SIZE:
            logger.warning(f"Embedding size {len(embedding)} doesn't match expected size {Config.QDRANT_VECTOR_SIZE}")
        
        duration = time.time() - start_time
        logger.info(f"Embedding generated in {duration:.2f}s (size: {len(embedding)})")
        
        return embedding
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed to generate embedding after {duration:.2f}s: {str(e)}")
        raise
