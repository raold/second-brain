"""Mock storage backend for development without PostgreSQL"""
import json
import uuid
from datetime import datetime
from pathlib import Path


class MockStorage:
    """In-memory storage with JSON persistence for development"""

    def __init__(self, persist_path: str = "data/mock_memories.json") -> None:
        self.memories: dict[str, dict] = {}
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    async def initialize(self):
        """Initialize mock storage"""
        print("✅ Mock storage initialized (development mode)")
        return self

    async def close(self) -> None:
        """Close mock storage"""
        self._save_to_disk()

    def _load_from_disk(self) -> None:
        """Load memories from JSON file if exists"""
        if self.persist_path.exists():
            try:
                with open(self.persist_path) as f:
                    data = json.load(f)
                    self.memories = {item["id"]: item for item in data}
                print(f"📂 Loaded {len(self.memories)} memories from {self.persist_path}")
            except Exception as e:
                print(f"⚠️ Could not load memories: {e}")

    def _save_to_disk(self) -> None:
        """Save memories to JSON file"""
        try:
            with open(self.persist_path, "w") as f:
                json.dump(list(self.memories.values()), f, indent=2, default=str)
            print(f"💾 Saved {len(self.memories)} memories to {self.persist_path}")
        except Exception as e:
            print(f"⚠️ Could not save memories: {e}")

    async def save_to_disk(self) -> None:
        """Public async method for periodic persistence"""
        self._save_to_disk()

    async def create_memory(self, data: dict) -> dict:
        """Create a new memory"""
        memory_id = str(uuid.uuid4())
        memory = {
            "id": memory_id,
            "content": data.get("content", ""),
            "importance_score": data.get("importance_score", 0.5),
            "tags": data.get("tags", []),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "embedding": data.get("embedding", [0.0] * 1536),  # Mock embedding
        }
        self.memories[memory_id] = memory
        self._save_to_disk()
        return memory

    async def get_memory(self, memory_id: str) -> dict | None:
        """Get a memory by ID"""
        return self.memories.get(memory_id)

    async def update_memory(self, memory_id: str, data: dict) -> dict | None:
        """Update a memory"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.update(data)
            memory["updated_at"] = datetime.utcnow().isoformat()
            self.memories[memory_id] = memory
            self._save_to_disk()
            return memory
        return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._save_to_disk()
            return True
        return False

    async def list_memories(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all memories"""
        memories = list(self.memories.values())
        memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return memories[offset:offset + limit]

    async def search_memories(self, query: str, limit: int = 10) -> list[dict]:
        """Simple text search in memories"""
        results = []
        query_lower = query.lower()

        for memory in self.memories.values():
            content_lower = memory.get("content", "").lower()
            if query_lower in content_lower:
                results.append(memory)

        # Sort by relevance (simple: how many times query appears)
        results.sort(key=lambda x: x.get("content", "").lower().count(query_lower), reverse=True)
        return results[:limit]

    async def get_statistics(self) -> dict:
        """Get storage statistics"""
        return {
            "total_memories": len(self.memories),
            "backend": "mock",
            "persist_path": str(self.persist_path),
            "status": "healthy",
        }
