"""
Mock implementations for testing.

Used when USE_MOCK_DATABASE is true or services are unavailable.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.domain.models.memory import Memory, MemoryId
from src.domain.models.session import Session, SessionId
from src.domain.models.tag import Tag, TagId
from src.domain.models.user import User, UserId
from src.domain.repositories.memory_repository import MemoryRepository
from src.infrastructure.embeddings.models import EmbeddingModel, EmbeddingResult


class MockMemoryRepository(MemoryRepository):
    """In-memory mock implementation of MemoryRepository."""
    
    def __init__(self):
        self._memories: Dict[UUID, Memory] = {}
        self._links: List[tuple[UUID, UUID, Optional[str]]] = []
    
    async def get(self, memory_id: MemoryId) -> Optional[Memory]:
        """Get a memory by ID."""
        return self._memories.get(memory_id.value)
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Memory]:
        """Get memories for a user."""
        memories = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]
        
        if memory_type:
            memories = [m for m in memories if m.memory_type.value == memory_type]
        
        if status:
            memories = [m for m in memories if m.status.value == status]
        
        # Sort by created_at desc
        memories.sort(key=lambda m: m.created_at, reverse=True)
        
        return memories[skip:skip + limit]
    
    async def save(self, memory: Memory) -> Memory:
        """Save a memory."""
        self._memories[memory.id.value] = memory
        return memory
    
    async def delete(self, memory_id: MemoryId) -> bool:
        """Delete a memory."""
        if memory_id.value in self._memories:
            del self._memories[memory_id.value]
            return True
        return False
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
        memory_type: Optional[str] = None,
    ) -> List[Memory]:
        """Search memories by content."""
        query_lower = query.lower()
        memories = [
            m for m in self._memories.values()
            if m.user_id == user_id and (
                query_lower in m.title.lower() or
                query_lower in m.content.lower()
            )
        ]
        
        if memory_type:
            memories = [m for m in memories if m.memory_type.value == memory_type]
        
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]
    
    async def find_similar(
        self,
        user_id: UUID,
        embedding: List[float],
        limit: int = 10,
        threshold: float = 0.8,
    ) -> List[Memory]:
        """Find memories with similar embeddings."""
        # Simple mock: return random memories
        user_memories = [
            m for m in self._memories.values()
            if m.user_id == user_id and m.embedding is not None
        ]
        
        # In real implementation, would calculate cosine similarity
        # For mock, just return first N memories
        return user_memories[:limit]
    
    async def get_by_tag(
        self,
        user_id: UUID,
        tag_id: TagId,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Memory]:
        """Get memories with a specific tag."""
        memories = [
            m for m in self._memories.values()
            if m.user_id == user_id and tag_id.value in m.tags
        ]
        
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[skip:skip + limit]
    
    async def get_linked_memories(
        self,
        memory_id: MemoryId,
        link_type: Optional[str] = None,
    ) -> List[Memory]:
        """Get memories linked to a specific memory."""
        linked_ids = [
            to_id for from_id, to_id, lt in self._links
            if from_id == memory_id.value and (link_type is None or lt == link_type)
        ]
        
        return [
            self._memories[lid] for lid in linked_ids
            if lid in self._memories
        ]
    
    async def link_memories(
        self,
        from_memory_id: MemoryId,
        to_memory_id: MemoryId,
        link_type: Optional[str] = None,
    ) -> bool:
        """Create a link between memories."""
        # Check if link already exists
        for link in self._links:
            if link[0] == from_memory_id.value and link[1] == to_memory_id.value:
                return False
        
        self._links.append((from_memory_id.value, to_memory_id.value, link_type))
        return True
    
    async def unlink_memories(
        self,
        from_memory_id: MemoryId,
        to_memory_id: MemoryId,
    ) -> bool:
        """Remove a link between memories."""
        original_len = len(self._links)
        self._links = [
            link for link in self._links
            if not (link[0] == from_memory_id.value and link[1] == to_memory_id.value)
        ]
        return len(self._links) < original_len
    
    async def update_access_time(self, memory_id: MemoryId) -> None:
        """Update the last access time for a memory."""
        memory = self._memories.get(memory_id.value)
        if memory:
            memory.accessed_at = datetime.utcnow()
            memory.retrieval_count += 1
    
    async def count_by_user(self, user_id: UUID) -> int:
        """Count memories for a user."""
        return sum(1 for m in self._memories.values() if m.user_id == user_id)


class MockEmbeddingClient:
    """Mock embedding client for testing."""
    
    def __init__(self, model: EmbeddingModel = EmbeddingModel.LOCAL):
        self.model = model
        self.use_mock = os.getenv("MOCK_EMBEDDINGS", "false").lower() == "true"
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
    ) -> EmbeddingResult:
        """Generate mock embedding."""
        model = model or self.model
        
        # Generate deterministic embedding based on text hash
        text_hash = hash(text) % 1000000
        embedding_dim = 1536 if "OPENAI" in model else 384
        
        # Create a deterministic but varied embedding
        embedding = [
            float((text_hash + i) % 100) / 100.0
            for i in range(embedding_dim)
        ]
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=model,
            dimensions=embedding_dim,
            metadata={"mock": True, "text_hash": text_hash},
        )
    
    async def batch_generate_embeddings(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
    ) -> List[EmbeddingResult]:
        """Generate mock embeddings for multiple texts."""
        results = []
        for text in texts:
            result = await self.generate_embedding(text, model)
            results.append(result)
        return results


class MockCache:
    """In-memory mock cache for testing."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._ttls: Dict[str, datetime] = {}
    
    async def connect(self) -> None:
        """Mock connect."""
        pass
    
    async def disconnect(self) -> None:
        """Mock disconnect."""
        pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check TTL
        if key in self._ttls:
            if datetime.utcnow() > self._ttls[key]:
                del self._data[key]
                del self._ttls[key]
                return None
        
        return self._data.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        self._data[key] = value
        
        if ttl:
            self._ttls[key] = datetime.utcnow() + timedelta(seconds=ttl)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._data:
            del self._data[key]
            if key in self._ttls:
                del self._ttls[key]
            return True
        return False
    
    async def flush(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._ttls.clear()
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self._data.keys())
        
        # Simple pattern matching
        import re
        regex = pattern.replace("*", ".*")
        return [k for k in self._data.keys() if re.match(regex, k)]


class MockMessageBroker:
    """In-memory mock message broker for testing."""
    
    def __init__(self, url: str = ""):
        self._queues: Dict[str, List[Dict[str, Any]]] = {}
        self._handlers: Dict[str, List[Any]] = {}
        self.connected = False
    
    async def connect(self) -> None:
        """Mock connect."""
        self.connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnect."""
        self.connected = False
    
    async def publish(
        self,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True,
    ) -> None:
        """Publish message to queue."""
        if routing_key not in self._queues:
            self._queues[routing_key] = []
        
        self._queues[routing_key].append(message)
        
        # Immediately call handlers for testing
        if routing_key in self._handlers:
            for handler in self._handlers[routing_key]:
                await handler(message)
    
    async def subscribe(
        self,
        routing_key: str,
        handler: Any,
        queue_name: Optional[str] = None,
    ) -> None:
        """Subscribe to messages."""
        if routing_key not in self._handlers:
            self._handlers[routing_key] = []
        
        self._handlers[routing_key].append(handler)
    
    def get_messages(self, routing_key: str) -> List[Dict[str, Any]]:
        """Get messages from queue (for testing)."""
        return self._queues.get(routing_key, [])
    
    def clear_queue(self, routing_key: str) -> None:
        """Clear queue (for testing)."""
        if routing_key in self._queues:
            self._queues[routing_key] = []


class MockStorageClient:
    """In-memory mock storage client for testing."""
    
    def __init__(self, endpoint: str = "", access_key: str = "", secret_key: str = ""):
        self._buckets: Dict[str, Dict[str, bytes]] = {}
        self._metadata: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.connected = False
    
    async def connect(self) -> None:
        """Mock connect."""
        self.connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnect."""
        self.connected = False
    
    async def bucket_exists(self, bucket: str) -> bool:
        """Check if bucket exists."""
        return bucket in self._buckets
    
    async def create_bucket(self, bucket: str) -> None:
        """Create bucket."""
        if bucket not in self._buckets:
            self._buckets[bucket] = {}
            self._metadata[bucket] = {}
    
    async def remove_bucket(self, bucket: str, force: bool = False) -> None:
        """Remove bucket."""
        if bucket in self._buckets:
            if not force and self._buckets[bucket]:
                raise ValueError("Bucket not empty")
            del self._buckets[bucket]
            del self._metadata[bucket]
    
    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload object."""
        if bucket not in self._buckets:
            return None
        
        self._buckets[bucket][key] = data
        self._metadata[bucket][key] = metadata or {}
        
        return {
            "bucket": bucket,
            "key": key,
            "size": len(data),
            "content_type": content_type,
            "etag": f"mock-etag-{hash(data)}",
        }
    
    async def download(self, bucket: str, key: str) -> Optional[bytes]:
        """Download object."""
        if bucket not in self._buckets:
            return None
        
        return self._buckets[bucket].get(key)
    
    async def delete(self, bucket: str, key: str) -> bool:
        """Delete object."""
        if bucket not in self._buckets or key not in self._buckets[bucket]:
            return False
        
        del self._buckets[bucket][key]
        if key in self._metadata[bucket]:
            del self._metadata[bucket][key]
        
        return True
    
    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get presigned URL."""
        return f"mock://presigned/{bucket}/{key}?expires={expires_in}"