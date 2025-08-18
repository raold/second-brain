"""
Utilities package for Second Brain application.
Uses local models only - no API keys required!
"""

from .local_embedding_client import (
    get_local_client,
    get_openai_client,  # Compatibility wrapper
    get_openai_embedding,  # Compatibility wrapper
    get_openai_embedding_async,  # Compatibility wrapper
)
from .logger import logger

__all__ = [
    "get_local_client",
    "get_openai_client",  # For backward compatibility
    "get_openai_embedding",  # For backward compatibility
    "get_openai_embedding_async",  # For backward compatibility
    "logger",
]
