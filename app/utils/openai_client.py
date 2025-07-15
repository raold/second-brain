# app/utils/openai_client.py

import time
from typing import List

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

import asyncio

from app.config import Config
from app.utils.logger import get_logger
from cachetools import LRUCache, cached
from prometheus_client import Counter, Histogram

logger = get_logger()

# LRU cache for embeddings (up to 1000 unique texts)
_embedding_cache = LRUCache(maxsize=1000)

# Prometheus metrics
embedding_cache_hit = Counter('embedding_cache_hit', 'Embedding cache hits')
embedding_cache_miss = Counter('embedding_cache_miss', 'Embedding cache misses')
embedding_latency = Histogram('embedding_latency_seconds', 'Embedding generation latency (seconds)')

@cached(_embedding_cache, key=lambda text, client=None, model=None: (text, model or "default"))
def get_openai_embedding(text: str, client=None, model: str = None):
    """
    Get embedding for text, using OpenAI API. Uses LRU cache for repeated texts.
    
    Args:
        text: Text to embed
        openai_client: Optional OpenAI client instance
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If text is invalid
        Exception: If API call fails after retries
    """
    cache_key = (text, model or "default")
    if cache_key in _embedding_cache:
        embedding_cache_hit.inc()
        return _embedding_cache[cache_key]
    embedding_cache_miss.inc()
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
        client = client or openai
        response = client.embeddings.create(
            input=text,
            model=Config.OPENAI_EMBEDDING_MODEL
        )
        
        # Validate response
        if not response or not hasattr(response, "data"):
            raise ValueError("Invalid response from OpenAI API")
        
        if not response.data or len(response.data) == 0:
            raise ValueError("No embedding data in response")
        
        embedding = response.data[0].embedding
        
        # Validate embedding
        if not embedding or not isinstance(embedding, list):
            raise ValueError("Invalid embedding format in response")
        
        if len(embedding) != Config.QDRANT_VECTOR_SIZE:
            logger.warning(f"Embedding size {len(embedding)} doesn't match expected size {Config.QDRANT_VECTOR_SIZE}")
        
        embedding_latency.observe(time.time() - start_time)
        duration = time.time() - start_time
        logger.info(f"Embedding generated in {duration:.2f}s (size: {len(embedding)})")
        
        return embedding
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed to generate embedding after {duration:.2f}s: {str(e)}")
        raise

async def get_openai_stream(prompt: str):
    """
    Async generator that yields text chunks for streaming.
    Replace this with real OpenAI stream=True logic as needed.
    """
    # Simulate streaming by splitting prompt into words
    for word in prompt.split():
        await asyncio.sleep(0.1)  # Simulate network/processing delay
        yield word + " "
