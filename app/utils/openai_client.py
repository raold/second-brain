# app/utils/openai_client.py

import asyncio
import base64
import os
import time
from typing import List, Optional

import aiohttp
import openai

from app.config import config
from app.utils.cache import EMBEDDING_CACHE_CONFIG, get_cache
from app.utils.logger import logger

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
    model = model or config.openai['embedding_model']
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
    # Check if response object exists
    if response is None:
        raise ValueError("Invalid embedding response: response is None")
    
    # Check for data field
    if not hasattr(response, 'data'):
        available_attrs = dir(response) if response else []
        raise ValueError(f"Invalid embedding response: no 'data' field. Available attributes: {available_attrs}")
    
    if not response.data:
        raise ValueError("Invalid embedding response: data field is None or empty")
    
    if len(response.data) == 0:
        raise ValueError("Invalid embedding response: data array is empty")
    
    # Check for embedding in first data item
    first_item = response.data[0]
    if not hasattr(first_item, 'embedding'):
        available_attrs = dir(first_item) if first_item else []
        raise ValueError(f"Invalid embedding response: no 'embedding' field in data[0]. Available attributes: {available_attrs}")
    
    embedding = first_item.embedding
    if embedding is None:
        raise ValueError("Invalid embedding response: embedding field is None")
    
    if not isinstance(embedding, list):
        raise ValueError(f"Invalid embedding response: embedding field is not a list, got {type(embedding)}")
    
    if len(embedding) == 0:
        raise ValueError("Invalid embedding response: embedding list is empty")
    
    # Validate embedding dimensions
    expected_size = config.qdrant.get('vector_size', 1536)
    if len(embedding) != expected_size:
        raise ValueError(f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_size}")
    
    # Validate embedding values are numbers
    if not all(isinstance(x, (int, float)) for x in embedding[:10]):  # Check first 10 values
        raise ValueError("Invalid embedding response: embedding contains non-numeric values")
    
    return embedding

def get_openai_embedding(text: str, model: str = None) -> List[float]:
    """
    Generate embeddings for the given text using OpenAI's API.
    
    Args:
        text: Input text to embed
        model: OpenAI embedding model to use (optional)
        
    Returns:
        List of float values representing the embedding
        
    Raises:
        Exception: If API call fails
    """
    model = model or config.openai['embedding_model']
    logger.debug(f"Generating embedding: input_length={len(text)}, model={model}")
    
    # Check cache first
    cache_key = f"embedding:{hash(text)}:{model}"
    cached_embedding = _embedding_cache.get(cache_key)
    if cached_embedding is not None:
        logger.debug(f"Cache hit for embedding: {text[:50]}...")
        return cached_embedding
    
    start_time = time.time()
    
    try:
        # Record API call attempt
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='attempt').inc()
        
        client = get_openai_client()
        response = client.embeddings.create(
            input=text,
            model=model
        )
        
        # Use the validation function for proper error handling
        embedding = _validate_embedding_response(response)
        
        # Cache the result
        _embedding_cache.set(cache_key, embedding)
        
        # Record metrics
        if embedding_latency:
            embedding_latency.observe(time.time() - start_time)
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='success').inc()
        
        logger.debug(f"Generated embedding in {time.time() - start_time:.2f}s")
        return embedding
        
    except ValueError as e:
        # Record validation failure
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='validation_error').inc()
        
        logger.error(f"Embedding validation error for text '{text[:50]}...': {e}")
        logger.debug(f"Full validation error details: {e}")
        raise
        
    except Exception as e:
        # Record general failure
        if openai_api_calls:
            openai_api_calls.labels(endpoint='embeddings', status='error').inc()
        
        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'text_length': len(text),
            'model': model
        }
        logger.error(f"Failed to generate embedding: {error_details}")
        raise

# Async version of embedding function
async def get_openai_embedding_async(text: str, model: str = None):
    """
    Async version of get_openai_embedding for better performance in async contexts.
    """
    # For now, we'll run the sync version in a thread pool
    # Future enhancement could implement true async OpenAI client
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_openai_embedding, text, model)

def get_openai_client() -> openai.OpenAI:
    """
    Get OpenAI client with API key validation.
    
    Returns:
        Configured OpenAI client
        
    Raises:
        ValueError: If API key is not configured
    """
    if not config.openai['api_key']:
        raise ValueError("OpenAI API key not configured")
    
    return openai.OpenAI(api_key=config.openai['api_key'])


def get_openai_embedding_with_fallback(text: str, model: str = None) -> Optional[List[float]]:
    """
    Generate embeddings with fallback handling.
    Returns None if embedding generation fails after retries.
    
    Args:
        text: Input text to embed
        model: OpenAI embedding model to use (optional)
        
    Returns:
        List of float values representing the embedding, or None if failed
    """
    try:
        return get_openai_embedding(text, model)
    except Exception as e:
        logger.warning(f"Embedding generation failed, returning None: {e}")
        return None

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
