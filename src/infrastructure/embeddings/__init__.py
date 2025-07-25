"""
Embeddings infrastructure for vector search.

Handles generation and storage of embeddings.
"""

from .client import EmbeddingClient
from .models import EmbeddingModel, EmbeddingResult

__all__ = [
    "EmbeddingClient",
    "EmbeddingModel",
    "EmbeddingResult",
]