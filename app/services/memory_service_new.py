"""
Memory Service - Single User Implementation
Optimized for single-user-per-container architecture
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import os
from pathlib import Path


class MemoryService:
    """
    Memory service for a single user's brain.
    Uses in-memory storage with optional persistence to SQLite.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize memory service.
        
        Args:
            persist_path: Optional path for SQLite persistence
        """
        # In-memory storage - perfect for single user
        self.memories: Dict[str, Dict[str, Any]] = {}
        
        # Optional persistence path (for K8s persistent volume)
        self.persist_path = persist_path or os.getenv("MEMORY_PERSIST_PATH", "/data/memories.json")
        
        # Load existing memories if available
        self._load_memories()
    
    def _load_memories(self):
        """Load memories from persistent storage if available."""
        if Path(self.persist_path).exists():
            try:
                with open(self.persist_path, 'r') as f:
                    data = json.load(f)
                    self.memories = data.get("memories", {})
            except Exception as e:
                print(f"Could not load memories: {e}")
    
    def _save_memories(self):
        """Save memories to persistent storage."""
        try:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump({"memories": self.memories}, f, indent=2, default=str)
        except Exception as e:
            print(f"Could not save memories: {e}")
    
    async def create_memory(
        self,
        content: str,
        memory_type: str = "generic",
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new memory.
        No user_id needed - this container IS one user's brain.
        """
        memory_id = str(uuid.uuid4())
        
        memory = {
            "id": memory_id,
            "content": content,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "access_count": 0
        }
        
        self.memories[memory_id] = memory
        self._save_memories()  # Auto-persist
        return memory
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID."""
        memory = self.memories.get(memory_id)
        if memory:
            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed"] = datetime.utcnow().isoformat()
            self._save_memories()
        return memory
    
    async def list_memories(
        self,
        limit: int = 10,
        offset: int = 0,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all memories.
        No user filtering needed - all memories belong to this container's user.
        """
        memories = list(self.memories.values())
        
        # Filter by type if specified
        if memory_type:
            memories = [m for m in memories if m.get("memory_type") == memory_type]
        
        # Sort by created_at descending (newest first)
        memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Apply pagination
        return memories[offset:offset + limit]
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a memory."""
        memory = self.memories.get(memory_id)
        if not memory:
            return None
        
        if content is not None:
            memory["content"] = content
        if importance_score is not None:
            memory["importance_score"] = importance_score
        if tags is not None:
            memory["tags"] = tags
        if metadata is not None:
            memory["metadata"].update(metadata)
        
        memory["updated_at"] = datetime.utcnow().isoformat()
        self._save_memories()
        return memory
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._save_memories()
            return True
        return False
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Simple text search in memories.
        For vector search, integrate with Qdrant.
        """
        query_lower = query.lower()
        results = []
        
        for memory in self.memories.values():
            content_lower = memory.get("content", "").lower()
            tags = [t.lower() for t in memory.get("tags", [])]
            
            # Search in content and tags
            if query_lower in content_lower or any(query_lower in tag for tag in tags):
                results.append(memory)
        
        # Sort by importance and recency
        results.sort(
            key=lambda x: (x.get("importance_score", 0), x.get("created_at", "")),
            reverse=True
        )
        
        return results[:limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics for this user."""
        total = len(self.memories)
        
        # Count by type
        type_counts = {}
        for memory in self.memories.values():
            mem_type = memory.get("memory_type", "generic")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        # Calculate average importance
        avg_importance = 0
        if total > 0:
            avg_importance = sum(m.get("importance_score", 0) for m in self.memories.values()) / total
        
        return {
            "total_memories": total,
            "memories_by_type": type_counts,
            "average_importance": round(avg_importance, 2),
            "storage_size_bytes": len(json.dumps(self.memories)),
            "container_uptime": datetime.utcnow().isoformat()
        }
    
    async def export_memories(self) -> Dict[str, Any]:
        """Export all memories for backup or migration."""
        return {
            "export_date": datetime.utcnow().isoformat(),
            "total_memories": len(self.memories),
            "memories": list(self.memories.values())
        }
    
    async def import_memories(self, data: Dict[str, Any]) -> int:
        """Import memories from backup."""
        imported = 0
        memories = data.get("memories", [])
        
        for memory in memories:
            memory_id = memory.get("id", str(uuid.uuid4()))
            self.memories[memory_id] = memory
            imported += 1
        
        self._save_memories()
        return imported