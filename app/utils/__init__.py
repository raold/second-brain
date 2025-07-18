"""
Utilities package for Second Brain application.
"""

from .logger import logger
from .openai_client import get_openai_embedding, get_openai_embedding_async

__all__ = ['logger', 'get_openai_embedding', 'get_openai_embedding_async']
