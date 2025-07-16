# app/utils/openai_client.py

import asyncio
import base64
import os
import time
from typing import List

import aiohttp
import openai
from cachetools import LRUCache, cached

from app.config import Config
from app.utils.logger import logger
from app.utils.cache import (
    get_cache, async_cached_function, 
    EMBEDDING_CACHE_CONFIG, CacheConfig
)

# Enhanced embedding cache with TTL and metrics
_embedding_cache = get_cache("embeddings", EMBEDDING_CACHE_CONFIG)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram
    embedding_latency = Histogram('embedding_latency_seconds', 'Embedding generation latency (seconds)')
    openai_api_calls = Counter('openai_api_calls_total', 'OpenAI API calls', ['endpoint', 'status'])
except ImportError:
    embedding_latency = openai_api_calls = None

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "demo-key")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

def _validate_embedding_input(text: str) -> None:
    """
    Validate input text for embedding generation.
    
    Args:
        text: Text to validate
        
    Raises:
        ValueError: If text is invalid
    """
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string")
    
    if len(text.strip()) == 0:
        raise ValueError("Text cannot be empty or whitespace only")
    
    # Check for reasonable length limits
    if len(text) > 100000:  # 100k characters
        raise ValueError("Text too long for embedding generation")

def _preprocess_text_for_embedding(text: str) -> str:
    """
    Preprocess text before sending to embedding API.
    
    Args:
        text: Input text
        
    Returns:
        Preprocessed text
    """
    # Strip whitespace and normalize
    processed = text.strip()
    
    # Remove excessive whitespace
    import re
    processed = re.sub(r'\s+', ' ', processed)
    
    return processed

def _call_openai_embedding_api(text: str, client, model: str = None):
    """
    Make the actual API call to OpenAI embeddings endpoint.
    
    Args:
        text: Text to embed
        client: OpenAI client instance
        model: Optional model override
        
    Returns:
        Raw OpenAI API response
        
    Raises:
        Exception: If API call fails
    """
    model = model or Config.OPENAI_EMBEDDING_MODEL
    logger.debug(f"Generating embedding: input_length={len(text)}, model={model}")
    
    # Use the provided client or the global openai module
    client = client or openai
    return client.embeddings.create(
        input=text,
        model=model
    )

def _validate_embedding_response(response) -> List[float]:
    """
    Validate and extract embedding from OpenAI API response.
    
    Args:
        response: OpenAI API response
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If response is invalid
    """
    if not hasattr(response, 'data') or not response.data:
        raise ValueError("Invalid embedding response: no data field")
    
    if len(response.data) == 0:
        raise ValueError("Invalid embedding response: empty data")
    
    embedding = response.data[0].embedding
    if not embedding or not isinstance(embedding, list):
        raise ValueError("Invalid embedding response: invalid embedding field")
    
    # Validate embedding dimensions
    if len(embedding) != Config.QDRANT_VECTOR_SIZE:
        raise ValueError(f"Embedding dimension mismatch: got {len(embedding)}, expected {Config.QDRANT_VECTOR_SIZE}")
    
    return embedding

def get_openai_embedding(text: str, client=None, model: str = None):
    """
    Get embedding for text, using OpenAI API. Uses advanced LRU cache with TTL.
    
    Args:
        text: Text to embed
        client: Optional OpenAI client instance
        model: Optional model override
        
    Returns:
        List of embedding values
        
    Raises:
        ValueError: If text is invalid
        Exception: If API call fails after retries
    """
    # Generate cache key
    cache_key = f"{text}::{model or 'default'}"
    
    # Check cache first
    cached_result = _embedding_cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Embedding cache hit for text length: {len(text)}")
        return cached_result
    
    start_time = time.time()
    
    try:
        # Validate input
        _validate_embedding_input(text)
        
        # Preprocess text
        processed_text = _preprocess_text_for_embedding(text)
        
        # Make API call
        response = _call_openai_embedding_api(processed_text, client, model)
        
        # Record API call metric
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='success').inc()
        
        # Validate and extract embedding
        embedding = _validate_embedding_response(response)
        
        # Store in cache
        _embedding_cache.set(cache_key, embedding)
        
        # Log performance metrics
        if embedding_latency:
            embedding_latency.observe(time.time() - start_time)
        duration = time.time() - start_time
        logger.info(f"Embedding generated in {duration:.2f}s (size: {len(embedding)})")
        
        return embedding
        
    except Exception as e:
        # Record API failure metric
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='error').inc()
            
        duration = time.time() - start_time
        logger.error(f"Failed to generate embedding after {duration:.2f}s: {str(e)}")
        raise

# Async version of embedding function
async def get_openai_embedding_async(text: str, client=None, model: str = None):
    """
    Async version of get_openai_embedding for better performance in async contexts.
    """
    # For now, we'll run the sync version in a thread pool
    # Future enhancement could implement true async OpenAI client
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_openai_embedding, text, client, model)

def get_openai_client():
    """
    Get configured OpenAI client instance.
    
    Returns:
        OpenAI client instance
        
    Raises:
        ValueError: If API key is not configured
    """
    if not Config.OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    
    return openai.OpenAI(api_key=Config.OPENAI_API_KEY)

async def get_openai_stream(prompt: str):
    """
    Async generator that yields text chunks for streaming.
    Replace this with real OpenAI stream=True logic as needed.
    """
    # Simulate streaming by splitting prompt into words
    for word in prompt.split():
        await asyncio.sleep(0.1)  # Simulate network/processing delay
        yield word + " "

async def elevenlabs_tts_stream(text: str, voice_id: str = None, api_key: str = None):
    """
    Async generator that yields audio chunks from ElevenLabs TTS API as base64 strings.
    """
    voice_id = str(voice_id or ELEVENLABS_VOICE_ID or "EXAVITQu4vr4xnSDxMaL")
    api_key = str(api_key or ELEVENLABS_API_KEY or "demo-key")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                detail = await resp.text()
                raise Exception(f"TTS error: {resp.status} {detail}")
            async for chunk in resp.content.iter_chunked(4096):
                if not chunk:
                    break
                # Yield as base64 for easy transport
                yield base64.b64encode(chunk).decode("utf-8")

async def detect_intent_via_llm(text: str, client=None, model: str = None) -> str:
    """
    Use OpenAI LLM to classify the intent of the text.
    Returns one of: question, reminder, note, todo, command, other
    """
    import openai
    client = client or openai
    model = model or "gpt-3.5-turbo"
    prompt = (
        "Classify the following text as one of: question, reminder, note, todo, command, other. "
        "Respond with only the label.\nText: " + text
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are an intent classifier."},
                  {"role": "user", "content": prompt}],
        max_tokens=5,
        temperature=0
    )
    label = response.choices[0].message.content.strip().lower()
    allowed = {"question", "reminder", "note", "todo", "command", "other"}
    return label if label in allowed else "other"
