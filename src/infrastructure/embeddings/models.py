"""
Embedding models and data structures.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EmbeddingModel(str, Enum):
    """Available embedding models."""
    
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS = "all-MiniLM-L6-v2"
    LOCAL = "local"


class EmbeddingResult(BaseModel):
    """Result of embedding generation."""
    
    text: str = Field(..., description="Original text that was embedded")
    embedding: List[float] = Field(..., description="Embedding vector")
    model: EmbeddingModel = Field(..., description="Model used for embedding")
    dimensions: int = Field(..., description="Number of dimensions in embedding")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "This is a sample memory",
                "embedding": [0.1, 0.2, 0.3],
                "model": "text-embedding-ada-002",
                "dimensions": 1536,
                "metadata": {"tokens": 5}
            }
        }