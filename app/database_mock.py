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

    async def store_memory(
        self, 
        content: str, 
        memory_type: str = "semantic",
        semantic_metadata: dict[str, Any] | None = None,
        episodic_metadata: dict[str, Any] | None = None,
        procedural_metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Store a memory in mock storage with cognitive metadata."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        memory_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Mock embedding generation (simple text-based similarity)
        mock_embedding = self._generate_mock_embedding(content)

        self.memories[memory_id] = {
            "id": memory_id,
            "content": content,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "access_count": 0,
            "last_accessed": now,
            "semantic_metadata": semantic_metadata or {},
            "episodic_metadata": episodic_metadata or {},
            "procedural_metadata": procedural_metadata or {},
            "consolidation_score": 0.5,
            "metadata": metadata or {},
            "embedding": mock_embedding,
            "created_at": now,
            "updated_at": now,
        }

        logger.info(f"Stored {memory_type} memory with ID: {memory_id}")
        return memory_id

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a memory by ID from mock storage with full cognitive metadata."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        memory = self.memories.get(memory_id)
        if memory:
            # Update access count
            memory["access_count"] += 1
            memory["last_accessed"] = datetime.now().isoformat()
            
            return {
                "id": memory["id"],
                "content": memory["content"],
                "memory_type": memory["memory_type"],
                "importance_score": memory["importance_score"],
                "access_count": memory["access_count"],
                "last_accessed": memory["last_accessed"],
                "semantic_metadata": memory["semantic_metadata"],
                "episodic_metadata": memory["episodic_metadata"],
                "procedural_metadata": memory["procedural_metadata"],
                "consolidation_score": memory["consolidation_score"],
                "metadata": memory["metadata"],
                "created_at": memory["created_at"],
                "updated_at": memory["updated_at"],
            }
        return None

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories using mock similarity (legacy method)."""
        return await self.contextual_search(
            query=query,
            limit=limit,
            memory_types=None,
            importance_threshold=None,
            timeframe=None
        )

    async def contextual_search(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        importance_threshold: float | None = None,
        timeframe: str | None = None,
        include_archived: bool = False
    ) -> list[dict[str, Any]]:
        """Mock contextual search with memory type filtering."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        query_embedding = self._generate_mock_embedding(query)
        results = []

        for memory in self.memories.values():
            # Apply memory type filtering
            if memory_types and memory["memory_type"] not in memory_types:
                continue

            # Apply importance threshold
            if importance_threshold is not None and memory["importance_score"] < importance_threshold:
                continue

            # Apply archive filtering
            if not include_archived and memory["importance_score"] <= 0.1:
                continue

            # Apply timeframe filtering (simplified for mock)
            if timeframe and timeframe == "last_week":
                # Mock: only return memories from last week
                from datetime import timedelta
                created_at = datetime.fromisoformat(memory["created_at"])
                week_ago = datetime.now() - timedelta(days=7)
                if created_at < week_ago:
                    continue

            # Calculate mock similarity
            vector_similarity = self._calculate_mock_similarity(query_embedding, memory["embedding"])
            
            # Mock contextual scoring
            contextual_score = (
                vector_similarity * 0.4 +
                memory["importance_score"] * 0.25 +
                memory["consolidation_score"] * 0.15 +
                min(memory["access_count"] / 10.0, 1.0) * 0.2
            )

            # Update access count (mock)
            memory["access_count"] += 1
            memory["last_accessed"] = datetime.now().isoformat()

            results.append(
                {
                    "id": memory["id"],
                    "content": memory["content"],
                    "memory_type": memory["memory_type"],
                    "importance_score": memory["importance_score"],
                    "access_count": memory["access_count"],
                    "last_accessed": memory["last_accessed"],
                    "semantic_metadata": memory["semantic_metadata"],
                    "episodic_metadata": memory["episodic_metadata"],
                    "procedural_metadata": memory["procedural_metadata"],
                    "consolidation_score": memory["consolidation_score"],
                    "metadata": memory["metadata"],
                    "created_at": memory["created_at"],
                    "updated_at": memory["updated_at"],
                    "similarity": vector_similarity,
                    "contextual_score": contextual_score,
                }
            )

        # Sort by contextual score and limit
        results.sort(key=lambda x: x["contextual_score"], reverse=True)
        results = results[:limit]

        logger.info(f"Found {len(results)} memories for contextual query: {query}")
        return results

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
        """Get all memories with pagination and full cognitive metadata from mock storage."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        all_memories = list(self.memories.values())
        # Sort by importance score descending, then created_at descending
        all_memories.sort(key=lambda x: (x["importance_score"], x["created_at"]), reverse=True)

        # Apply pagination
        paginated = all_memories[offset : offset + limit]

        return [
            {
                "id": memory["id"],
                "content": memory["content"],
                "memory_type": memory["memory_type"],
                "importance_score": memory["importance_score"],
                "access_count": memory["access_count"],
                "last_accessed": memory["last_accessed"],
                "semantic_metadata": memory["semantic_metadata"],
                "episodic_metadata": memory["episodic_metadata"],
                "procedural_metadata": memory["procedural_metadata"],
                "consolidation_score": memory["consolidation_score"],
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

        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        cosine_sim = dot_product / (magnitude1 * magnitude2)

        # Normalize to [0, 1] range and ensure minimum relevance for testing
        similarity = max(0.0, min(1.0, (cosine_sim + 1) / 2))

        # For testing purposes, ensure there's always some similarity
        # if the texts share common words
        return max(0.1, similarity)

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
