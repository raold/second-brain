"""
Embedding client for generating embeddings.

Supports multiple embedding providers.
"""

import os
from typing import List, Optional

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

from src.infrastructure.logging import get_logger
from src.infrastructure.observability.tracing import trace

from .models import EmbeddingModel, EmbeddingResult

logger = get_logger(__name__)


class EmbeddingClient:
    """Client for generating embeddings."""
    
    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.OPENAI_ADA_002,
        api_key: Optional[str] = None,
    ):
        """
        Initialize embedding client.
        
        Args:
            model: Embedding model to use
            api_key: API key for external providers
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._local_model = None
        
        # Model dimensions
        self.dimensions = {
            EmbeddingModel.OPENAI_ADA_002: 1536,
            EmbeddingModel.OPENAI_3_SMALL: 1536,
            EmbeddingModel.OPENAI_3_LARGE: 3072,
            EmbeddingModel.SENTENCE_TRANSFORMERS: 384,
            EmbeddingModel.LOCAL: 384,
        }
    
    @trace("generate_embedding")
    async def generate_embedding(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
    ) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Optional model override
            
        Returns:
            EmbeddingResult with embedding vector
        """
        model = model or self.model
        
        try:
            if model in [
                EmbeddingModel.OPENAI_ADA_002,
                EmbeddingModel.OPENAI_3_SMALL,
                EmbeddingModel.OPENAI_3_LARGE,
            ]:
                embedding = await self._generate_openai_embedding(text, model)
            else:
                embedding = await self._generate_local_embedding(text)
            
            return EmbeddingResult(
                text=text,
                embedding=embedding,
                model=model,
                dimensions=len(embedding),
                metadata={"provider": "openai" if "OPENAI" in model else "local"},
            )
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            dimensions = self.dimensions.get(model, 384)
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * dimensions,
                model=model,
                dimensions=dimensions,
                metadata={"error": str(e), "fallback": True},
            )
    
    @trace("batch_generate_embeddings")
    async def batch_generate_embeddings(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            model: Optional model override
            
        Returns:
            List of EmbeddingResults
        """
        model = model or self.model
        
        # OpenAI supports batch embedding
        if model in [
            EmbeddingModel.OPENAI_ADA_002,
            EmbeddingModel.OPENAI_3_SMALL,
            EmbeddingModel.OPENAI_3_LARGE,
        ]:
            return await self._batch_generate_openai_embeddings(texts, model)
        
        # For local models, process individually
        results = []
        for text in texts:
            result = await self.generate_embedding(text, model)
            results.append(result)
        
        return results
    
    async def _generate_openai_embedding(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> List[float]:
        """Generate embedding using OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": model.value,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            return data["data"][0]["embedding"]
    
    async def _batch_generate_openai_embeddings(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts using OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": model.value,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for i, item in enumerate(data["data"]):
                results.append(
                    EmbeddingResult(
                        text=texts[i],
                        embedding=item["embedding"],
                        model=model,
                        dimensions=len(item["embedding"]),
                        metadata={"provider": "openai", "index": i},
                    )
                )
            
            return results
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        if self._local_model is None:
            logger.info("Loading local embedding model...")
            self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Generate embedding
        embedding = self._local_model.encode(text)
        return embedding.tolist()
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        a_np = np.array(a)
        b_np = np.array(b)
        
        dot_product = np.dot(a_np, b_np)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))