"""
Utilities package for Second Brain application.
"""

from .logger import logger
from .openai_client import get_openai_embedding, get_openai_embedding_async
from .anthropic_client import get_anthropic_client, create_claude_completion, analyze_with_claude

__all__ = [
    "logger", 
    "get_openai_embedding", 
    "get_openai_embedding_async",
    "get_anthropic_client",
    "create_claude_completion",
    "analyze_with_claude"
]
