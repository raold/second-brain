# app/utils/openai_client.py

import asyncio
import base64
import os
import time
from typing import List, Optional

import aiohttp
import openai
from cachetools import LRUCache, cached

from app.config import config
from app.utils.logger import logger

# LRU cache for embeddings (up to 1000 unique texts)
_embedding_cache = LRUCache(maxsize=1000)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram
    embedding_cache_hit = Counter('embedding_cache_hit', 'Embedding cache hits')
    embedding_cache_miss = Counter('embedding_cache_miss', 'Embedding cache misses')
    embedding_latency = Histogram('embedding_latency_seconds', 'Embedding generation latency (seconds)')
except ImportError:
    embedding_cache_hit = embedding_cache_miss = embedding_latency = None

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "demo-key")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

@cached(_embedding_cache, key=lambda text, client=None, model=None: (text, model or "default"))
def get_openai_embedding(text: str, client=None, model: str = None):
    """
    Get embedding for text, using OpenAI API. Uses LRU cache for repeated texts.
    
    Args:
        text: Text to embed
        client: Optional OpenAI client instance
        model: Model to use for embedding
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If text is invalid
        Exception: If API call fails after retries
    """
    cache_key = (text, model or "default")
    if cache_key in _embedding_cache:
        if embedding_cache_hit:
            embedding_cache_hit.inc()
        return _embedding_cache[cache_key]
    if embedding_cache_miss:
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
    
    logger.debug(f"Generating embedding: input_length={len(text)}, model={config.OPENAI_EMBEDDING_MODEL}")

    try:
        # Use the provided client or the global openai module
        client = client or openai
        
        response = client.embeddings.create(
            input=text,
            model=model or config.OPENAI_EMBEDDING_MODEL
        )
        
        if not response or not hasattr(response, "data"):
            raise ValueError("Invalid response from OpenAI API")
        
        embedding = response.data[0].embedding
        
        # Validate the embedding
        if not isinstance(embedding, list) or len(embedding) == 0:
            raise ValueError("Invalid embedding format from OpenAI API")
        
        if not all(isinstance(x, (int, float)) for x in embedding):
            raise ValueError("Embedding contains non-numeric values")
        
        duration = time.time() - start_time
        if embedding_latency:
            embedding_latency.observe(duration)
        
        logger.debug(f"Embedding generated successfully: dimension={len(embedding)}, time={duration:.3f}s")
        
        return embedding
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"OpenAI embedding failed: {e} (time={duration:.3f}s)")
        raise


def openai_health_check() -> bool:
    """Check if OpenAI API is accessible."""
    try:
        # Simple test with minimal token usage
        embedding = get_openai_embedding("test")
        return len(embedding) > 0
    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")
        return False
