"""
Memory Service - Clean implementation
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class MemoryService:
    """Service for managing memories."""
    
    def __init__(self):
        # In-memory storage for now
        self.memories: Dict[str, Dict[str, Any]] = {}
    
    async def create_memory(
        self,
        content: str,
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default-user"
    ) -> Dict[str, Any]:
        """Create a new memory."""
        memory_id = str(uuid.uuid4())
        
        memory = {
            "id": memory_id,
            "user_id": user_id,
            "content": content,
            "memory_type": "generic",
            "importance_score": importance_score,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.memories[memory_id] = memory
        return memory
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID."""
        return self.memories.get(memory_id)
    
    async def list_memories(
        self,
        user_id: str = "default-user",
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List memories for a user."""
        user_memories = [
            m for m in self.memories.values() 
            if m["user_id"] == user_id
        ]
        
        # Sort by created_at descending
        user_memories.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        return user_memories[offset:offset + limit]
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None
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
        
        memory["updated_at"] = datetime.utcnow().isoformat()
        return memory
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False
    
    async def search_memories(
        self,
        query: str,
        user_id: str = "default-user",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories by content."""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            if memory["user_id"] == user_id and query_lower in memory["content"].lower():
                results.append(memory)
        
        # Sort by relevance (simple implementation)
        results.sort(key=lambda x: x["content"].lower().count(query_lower), reverse=True)
        
        return results[:limit]