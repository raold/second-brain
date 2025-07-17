"""
Mock version of the database for testing without OpenAI API calls or database connection.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MockDatabase:
    """Mock database client for testing without any external dependencies."""

    def __init__(self):
        self.memories: dict[str, dict[str, Any]] = {}
        self.is_initialized = False

    async def initialize(self):
        """Initialize mock database (no actual connection needed)."""
        self.is_initialized = True
        logger.info("Mock database initialized")

    async def close(self):
        """Close mock database (no actual connection to close)."""
        self.is_initialized = False
        logger.info("Mock database closed")

    async def store_memory(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Store a memory in mock storage."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        memory_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Mock embedding generation (simple text-based similarity)
        mock_embedding = self._generate_mock_embedding(content)

        self.memories[memory_id] = {
            "id": memory_id,
            "content": content,
            "metadata": metadata or {},
            "embedding": mock_embedding,
            "created_at": now,
            "updated_at": now,
        }

        logger.info(f"Stored memory with ID: {memory_id}")
        return memory_id

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a memory by ID from mock storage."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        memory = self.memories.get(memory_id)
        if memory:
            return {
                "id": memory["id"],
                "content": memory["content"],
                "metadata": memory["metadata"],
                "created_at": memory["created_at"],
                "updated_at": memory["updated_at"],
            }
        return None

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories using mock similarity."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        query_embedding = self._generate_mock_embedding(query)
        results = []

        for memory in self.memories.values():
            # Calculate mock similarity based on simple text matching
            similarity = self._calculate_mock_similarity(query_embedding, memory["embedding"])

            results.append({
                "id": memory["id"],
                "content": memory["content"],
                "metadata": memory["metadata"],
                "created_at": memory["created_at"],
                "updated_at": memory["updated_at"],
                "similarity": similarity,
            })

        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from mock storage."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.info(f"Deleted memory with ID: {memory_id}")
            return True
        return False

    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Get all memories with pagination from mock storage."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        all_memories = list(self.memories.values())
        # Sort by created_at descending
        all_memories.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply pagination
        paginated = all_memories[offset : offset + limit]

        return [
            {
                "id": memory["id"],
                "content": memory["content"],
                "metadata": memory["metadata"],
                "created_at": memory["created_at"],
                "updated_at": memory["updated_at"],
            }
            for memory in paginated
        ]

    def _generate_mock_embedding(self, text: str) -> list[float]:
        """Generate a mock embedding based on text content."""
        # Simple hash-based mock embedding for testing
        import hashlib

        # Create a deterministic "embedding" based on text content
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to list of floats (mock 1536-dimensional embedding)
        embedding = []
        for i in range(1536):
            # Use hash bytes cyclically to generate pseudo-random floats
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1] range
            embedding.append((byte_val - 127.5) / 127.5)

        return embedding

    def _calculate_mock_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calculate mock cosine similarity between two embeddings."""
        # Simple dot product for mock similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2, strict=False))
        # Normalize to [0, 1] range for similarity score
        return max(0, min(1, (dot_product + 1) / 2))

    async def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about mock database."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        total_memories = len(self.memories)
        avg_content_length = (
            sum(len(memory["content"]) for memory in self.memories.values()) / total_memories
            if total_memories > 0
            else 0
        )

        return {
            "total_memories": total_memories,
            "memories_with_embeddings": total_memories,
            "avg_content_length": avg_content_length,
            "hnsw_index_exists": False,  # Mock doesn't use real indexes
            "ivf_index_exists": False,
            "recommended_index_threshold": 1000,
            "index_ready": False,  # Mock doesn't need real indexes
        }

    async def force_create_index(self) -> bool:
        """Force creation of vector index (mock version - always succeeds)."""
        logger.info("Mock database: Index creation simulated")
        return True


# Global mock database instance
mock_database = MockDatabase()


async def get_mock_database() -> MockDatabase:
    """Get initialized mock database instance."""
    if not mock_database.is_initialized:
        await mock_database.initialize()
    return mock_database
