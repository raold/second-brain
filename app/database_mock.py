"""
Mock version of the database for testing without OpenAI API calls or database connection.
"""

from datetime import datetime
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MockDatabase:
    """Mock database client for testing without any external dependencies."""

    def __init__(self):
        self.memories: dict[str, dict[str, Any]] = {}
        self.is_initialized = False
        self.pool = None  # Mock pool attribute for compatibility

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
        metadata: dict[str, Any] | None = None,
        memory_type: str | None = None,
        semantic_metadata: dict[str, Any] | None = None,
        episodic_metadata: dict[str, Any] | None = None,
        procedural_metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
    ) -> str:
        """Store a memory in mock storage with cognitive metadata."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        memory_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Extract memory type from metadata if not provided
        if metadata and "type" in metadata:
            memory_type = metadata["type"]
        elif memory_type is None:
            memory_type = "semantic"  # Default type

        memory = {
            "id": memory_id,
            "content": content,
            "embedding": [0.1] * 1536,  # Mock embedding
            "memory_type": memory_type,
            "importance_score": importance_score,
            "access_count": 0,
            "last_accessed": now,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {},
            "semantic_metadata": semantic_metadata or {},
            "episodic_metadata": episodic_metadata or {},
            "procedural_metadata": procedural_metadata or {},
            "consolidation_score": importance_score,
            "last_consolidated": now,
            "decay_applied": False
        }

        self.memories[memory_id] = memory
        logger.debug(f"Stored mock memory with ID: {memory_id}")
        return memory_id

    async def search_memories(self, query: str, limit: int = 10, threshold: float = 0.0) -> list[dict[str, Any]]:
        """Search memories using simple content matching."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        # Simple search - return all memories containing query text
        results = []
        query_lower = query.lower()

        for memory in self.memories.values():
            if query_lower in memory["content"].lower():
                result = memory.copy()
                result["similarity"] = 0.9  # Mock similarity score
                results.append(result)

        # Sort by creation date and limit
        results.sort(key=lambda m: m["created_at"], reverse=True)
        return results[:limit]

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a specific memory by ID."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        return self.memories.get(memory_id)

    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Get all memories with pagination."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        # Convert to list and apply pagination
        all_memories = list(self.memories.values())
        all_memories.sort(key=lambda m: m["created_at"], reverse=True)

        return all_memories[offset:offset + limit]

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.debug(f"Deleted mock memory with ID: {memory_id}")
            return True
        return False

    async def contextual_search(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        importance_threshold: float = 0.0,
        timeframe: str | None = None,
        include_archived: bool = False
    ) -> list[dict[str, Any]]:
        """Advanced search with filters."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        # Use basic search and apply filters
        results = await self.search_memories(query, limit=limit*2)  # Get more for filtering

        # Apply memory type filter
        if memory_types:
            results = [r for r in results if r.get("memory_type") in memory_types]

        # Apply importance filter
        if importance_threshold is not None:
            results = [r for r in results if r.get("importance_score", 0) >= importance_threshold]

        return results[:limit]

    async def get_index_stats(self) -> dict[str, Any]:
        """Get mock index statistics."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        return {
            "total_memories": len(self.memories),
            "memories_with_embeddings": len(self.memories),  # All have mock embeddings
            "ivf_index_exists": False,
            "hnsw_index_exists": False,
            "index_ready": False
        }

    async def _execute(self, query: str, *args) -> Any:
        """Mock execute method for compatibility."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        # Return mock results based on query patterns
        if "COUNT(*)" in query:
            return [(len(self.memories),)]
        elif "SELECT" in query:
            return []
        return None

    async def _fetch(self, query: str, *args) -> list[Any]:
        """Mock fetch method for compatibility."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")

        return []
