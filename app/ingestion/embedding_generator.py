"""
Embedding generation component for automatic vector embeddings
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.ingestion.models import EmbeddingMetadata

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for content using various models"""

    def __init__(self,
                 model_type: str = "sentence-transformers",
                 model_name: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 cache_embeddings: bool = True):
        """
        Initialize embedding generator

        Args:
            model_type: Type of model to use
            model_name: Specific model name
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            cache_embeddings: Whether to cache generated embeddings
        """
        self.model_type = model_type
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.cache_embeddings = cache_embeddings

        # Initialize model
        self.model = None
        self.dimensions = None
        self._initialize_model()

        # Cache for embeddings
        self.embedding_cache = {} if cache_embeddings else None

    def _initialize_model(self):
        """Initialize the embedding model"""
        if self.model_type == "sentence-transformers" and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Try advanced models first
                advanced_models = [
                    "all-mpnet-base-v2",  # Best quality
                    "all-MiniLM-L12-v2",  # Good balance
                    "all-MiniLM-L6-v2",   # Faster
                ]

                model_to_load = self.model_name
                if self.model_name == "auto":
                    # Auto-select best available model
                    for model in advanced_models:
                        try:
                            self.model = SentenceTransformer(model)
                            self.model_name = model
                            model_to_load = model
                            break
                        except Exception:
                            continue
                else:
                    self.model = SentenceTransformer(self.model_name)

                # Get embedding dimensions
                dummy_embedding = self.model.encode("test")
                self.dimensions = len(dummy_embedding)
                logger.info(f"Loaded sentence-transformers model: {model_to_load} ({self.dimensions}D)")

                # Set max sequence length for better performance
                self.model.max_seq_length = 512

            except Exception as e:
                logger.error(f"Failed to load sentence-transformers model: {e}")
                self._fallback_to_mock()
        elif self.model_type == "openai":
            # OpenAI embeddings
            self.dimensions = 1536  # text-embedding-ada-002 dimensions
            logger.info("Configured for OpenAI embeddings (1536D)")
        else:
            self._fallback_to_mock()

    def _fallback_to_mock(self):
        """Fallback to mock embeddings"""
        logger.warning("Using mock embeddings (no model available)")
        self.model_type = "mock"
        self.dimensions = 384  # Standard dimension

    async def generate_embeddings(self,
                                text: str,
                                generate_chunks: bool = True) -> tuple[dict[str, list[float]], EmbeddingMetadata]:
        """
        Generate embeddings for text

        Args:
            text: Input text
            generate_chunks: Whether to generate chunk embeddings

        Returns:
            Tuple of embeddings dict and metadata
        """
        embeddings = {}

        # Generate full text embedding
        full_embedding = await self._generate_single_embedding(text, "full")
        embeddings["full"] = full_embedding

        # Generate chunk embeddings if requested
        if generate_chunks and len(text) > self.chunk_size:
            chunks = self._chunk_text(text)
            chunk_embeddings = await self._generate_chunk_embeddings(chunks)

            # Store chunk embeddings
            for i, chunk_emb in enumerate(chunk_embeddings):
                embeddings[f"chunk_{i}"] = chunk_emb

            # Generate average embedding from chunks
            if chunk_embeddings and NUMPY_AVAILABLE:
                avg_embedding = np.mean(chunk_embeddings, axis=0).tolist()
                embeddings["average"] = avg_embedding

        # Create metadata
        metadata = EmbeddingMetadata(
            model=self.model_name,
            dimensions=self.dimensions,
            chunk_id=len(chunks) if generate_chunks and len(text) > self.chunk_size else None,
            chunk_overlap=self.chunk_overlap if generate_chunks else None,
            generated_at=datetime.utcnow()
        )

        return embeddings, metadata

    async def _generate_single_embedding(self, text: str, cache_key: str = None) -> list[float]:
        """Generate embedding for a single text"""
        # Check cache
        if self.cache_embeddings and cache_key:
            cache_id = self._get_cache_id(text, cache_key)
            if cache_id in self.embedding_cache:
                return self.embedding_cache[cache_id]

        # Generate embedding based on model type
        if self.model_type == "sentence-transformers" and self.model:
            embedding = await self._generate_sentence_transformer_embedding(text)
        elif self.model_type == "openai":
            embedding = await self._generate_openai_embedding(text)
        else:
            embedding = self._generate_mock_embedding(text)

        # Cache if enabled
        if self.cache_embeddings and cache_key:
            self.embedding_cache[cache_id] = embedding

        return embedding

    async def _generate_sentence_transformer_embedding(self, text: str) -> list[float]:
        """Generate embedding using sentence-transformers"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(text, convert_to_numpy=True)
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating sentence-transformer embedding: {e}")
            return self._generate_mock_embedding(text)

    async def _generate_openai_embedding(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API"""
        try:
            from app.utils.openai_client import get_openai_client

            client = get_openai_client()
            if client:
                response = await client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            else:
                logger.warning("OpenAI client not available, using sentence-transformers")
                return await self._generate_sentence_transformer_embedding(text)
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            return self._generate_mock_embedding(text)

    def _generate_mock_embedding(self, text: str) -> list[float]:
        """Generate deterministic mock embedding from text"""
        # Create deterministic embedding based on text content
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Generate values from hash
        embedding = []
        for i in range(0, self.dimensions * 2, 2):
            # Use pairs of hex digits to generate values
            hex_pair = text_hash[i % len(text_hash):i % len(text_hash) + 2]
            value = int(hex_pair, 16) / 255.0 - 0.5  # Normalize to [-0.5, 0.5]
            embedding.append(value)

        # Add some variation based on text features
        text_features = [
            len(text) / 1000.0,  # Length feature
            text.count(' ') / max(len(text), 1),  # Word density
            sum(1 for c in text if c.isupper()) / max(len(text), 1),  # Uppercase ratio
            sum(1 for c in text if c.isdigit()) / max(len(text), 1),  # Digit ratio
        ]

        # Mix in text features
        for i, feature in enumerate(text_features):
            if i < len(embedding):
                embedding[i] = (embedding[i] + feature) / 2

        # Normalize
        if NUMPY_AVAILABLE:
            embedding = np.array(embedding)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (embedding / norm).tolist()

        return embedding[:self.dimensions]

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks"""
        chunks = []

        # Simple word-based chunking
        words = text.split()

        if not words:
            return [text]

        # Calculate chunk parameters in words
        chunk_size_words = self.chunk_size // 5  # Rough estimate: 5 chars per word
        overlap_words = self.chunk_overlap // 5

        i = 0
        while i < len(words):
            # Get chunk
            chunk_end = min(i + chunk_size_words, len(words))
            chunk_words = words[i:chunk_end]
            chunk = ' '.join(chunk_words)

            # Add chunk
            chunks.append(chunk)

            # Move position
            i += chunk_size_words - overlap_words

            # Break if we've processed all words
            if chunk_end >= len(words):
                break

        return chunks

    async def _generate_chunk_embeddings(self, chunks: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple chunks"""
        embeddings = []

        # Generate embeddings in parallel
        tasks = []
        for i, chunk in enumerate(chunks):
            task = self._generate_single_embedding(chunk, f"chunk_{i}")
            tasks.append(task)

        embeddings = await asyncio.gather(*tasks)
        return embeddings

    def _get_cache_id(self, text: str, key: str) -> str:
        """Generate cache ID for text"""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{self.model_name}_{key}_{text_hash}"

    def generate_embedding_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if not NUMPY_AVAILABLE:
            # Simple dot product for similarity
            return sum(a * b for a, b in zip(embedding1, embedding2, strict=False))

        # Cosine similarity
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)

        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_similar_chunks(self,
                          query_embedding: list[float],
                          chunk_embeddings: dict[str, list[float]],
                          top_k: int = 5,
                          min_similarity: float = 0.5) -> list[tuple[str, float]]:
        """Find most similar chunks to query embedding"""
        similarities = []

        for chunk_id, chunk_embedding in chunk_embeddings.items():
            if chunk_id == "full" or chunk_id == "average":
                continue  # Skip non-chunk embeddings

            similarity = self.generate_embedding_similarity(query_embedding, chunk_embedding)
            if similarity >= min_similarity:
                similarities.append((chunk_id, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def reduce_embedding_dimensions(self,
                                  embedding: list[float],
                                  target_dimensions: int) -> list[float]:
        """Reduce embedding dimensions using PCA-like approach"""
        if len(embedding) <= target_dimensions:
            return embedding

        if not NUMPY_AVAILABLE:
            # Simple truncation
            return embedding[:target_dimensions]

        # Simple dimension reduction by taking evenly spaced elements
        # (A proper implementation would use PCA or other techniques)
        indices = np.linspace(0, len(embedding) - 1, target_dimensions, dtype=int)
        reduced = [embedding[i] for i in indices]

        # Normalize
        reduced = np.array(reduced)
        norm = np.linalg.norm(reduced)
        if norm > 0:
            reduced = (reduced / norm).tolist()

        return reduced

    def combine_embeddings(self,
                         embeddings: list[list[float]],
                         weights: list[float] | None = None) -> list[float]:
        """Combine multiple embeddings with optional weights"""
        if not embeddings:
            return []

        if not NUMPY_AVAILABLE:
            # Simple average
            combined = [0.0] * len(embeddings[0])
            for embedding in embeddings:
                for i, val in enumerate(embedding):
                    combined[i] += val
            return [val / len(embeddings) for val in combined]

        # Weighted combination
        embeddings_array = np.array(embeddings)

        if weights:
            weights_array = np.array(weights)
            weights_array = weights_array / weights_array.sum()  # Normalize weights
            combined = np.average(embeddings_array, axis=0, weights=weights_array)
        else:
            combined = np.mean(embeddings_array, axis=0)

        # Normalize
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm

        return combined.tolist()

    def get_embedding_statistics(self, embeddings: dict[str, list[float]]) -> dict[str, Any]:
        """Get statistics about generated embeddings"""
        if not embeddings:
            return {
                "total_embeddings": 0,
                "dimensions": 0,
                "types": [],
                "chunk_count": 0
            }

        # Count chunk embeddings
        chunk_count = sum(1 for key in embeddings if key.startswith("chunk_"))

        # Get dimensions (assume all embeddings have same dimension)
        dimensions = len(next(iter(embeddings.values()))) if embeddings else 0

        stats = {
            "total_embeddings": len(embeddings),
            "dimensions": dimensions,
            "types": list(embeddings.keys()),
            "chunk_count": chunk_count,
            "has_full_embedding": "full" in embeddings,
            "has_average_embedding": "average" in embeddings,
            "cache_size": len(self.embedding_cache) if self.embedding_cache else 0
        }

        # Add similarity matrix for chunks if available
        if chunk_count > 1 and chunk_count <= 10:  # Only for reasonable number of chunks
            chunk_embeddings = {k: v for k, v in embeddings.items() if k.startswith("chunk_")}
            similarity_matrix = []

            chunk_ids = sorted(chunk_embeddings.keys())
            for i, chunk_id1 in enumerate(chunk_ids):
                row = []
                for j, chunk_id2 in enumerate(chunk_ids):
                    if i == j:
                        row.append(1.0)
                    else:
                        sim = self.generate_embedding_similarity(
                            chunk_embeddings[chunk_id1],
                            chunk_embeddings[chunk_id2]
                        )
                        row.append(round(sim, 3))
                similarity_matrix.append(row)

            stats["chunk_similarity_matrix"] = similarity_matrix

        return stats
