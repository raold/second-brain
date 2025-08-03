"""
Enhanced Memory Service with SQLite and Graceful Degradation
Supports both in-memory and persistent storage with automatic fallback
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from app.utils.logging_config import get_logger
from app.core.degradation import get_degradation_manager, DegradationLevel

logger = get_logger(__name__)


class StorageBackend(Enum):
    """Available storage backends"""
    MEMORY = "memory"
    JSON = "json"
    SQLITE = "sqlite"


class MemoryServiceV2:
    """
    Enhanced memory service with multiple storage backends and graceful degradation
    """
    
    def __init__(
        self,
        storage_backend: Optional[str] = None,
        persist_path: Optional[str] = None
    ):
        """
        Initialize memory service with specified backend
        
        Args:
            storage_backend: 'memory', 'json', or 'sqlite' (auto-detect if None)
            persist_path: Path for persistent storage
        """
        self.degradation_manager = get_degradation_manager()
        self.persist_path = persist_path or os.getenv("MEMORY_PERSIST_PATH", "/data")
        
        # Auto-detect best available backend
        if storage_backend:
            self.backend_type = StorageBackend(storage_backend)
        else:
            self.backend_type = self._detect_best_backend()
        
        # Initialize backend
        self._init_backend()
        
        # In-memory cache for fast access
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_enabled = True
        
        logger.info(f"Memory service initialized with {self.backend_type.value} backend")
    
    def _detect_best_backend(self) -> StorageBackend:
        """Detect the best available storage backend"""
        
        # Check if SQLite is available and configured
        if os.getenv("USE_SQLITE", "false").lower() == "true":
            try:
                import sqlite3
                # Test if we can write to the persist path
                test_db = os.path.join(self.persist_path, ".test.db")
                conn = sqlite3.connect(test_db)
                conn.close()
                os.remove(test_db)
                return StorageBackend.SQLITE
            except Exception as e:
                logger.warning(f"SQLite not available: {e}")
        
        # Check if JSON persistence is available
        if self.persist_path and os.path.exists(os.path.dirname(self.persist_path)):
            try:
                test_file = os.path.join(self.persist_path, ".test.json")
                with open(test_file, "w") as f:
                    f.write("{}")
                os.remove(test_file)
                return StorageBackend.JSON
            except Exception as e:
                logger.warning(f"JSON persistence not available: {e}")
        
        # Fallback to memory-only
        logger.warning("No persistent storage available, using memory-only mode")
        return StorageBackend.MEMORY
    
    def _init_backend(self):
        """Initialize the storage backend"""
        if self.backend_type == StorageBackend.SQLITE:
            from app.storage.sqlite_backend import SQLiteBackend
            db_path = os.path.join(self.persist_path, "memories.db")
            self.backend = SQLiteBackend(db_path)
            
        elif self.backend_type == StorageBackend.JSON:
            self.backend = None  # Will use internal JSON methods
            self.json_path = os.path.join(self.persist_path, "memories.json")
            self._load_from_json()
            
        else:  # MEMORY
            self.backend = None
            self.memories: Dict[str, Dict[str, Any]] = {}
    
    async def create_memory(
        self,
        content: str,
        memory_type: str = "generic",
        importance_score: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a new memory with graceful degradation
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance_score: Importance (0-1)
            tags: List of tags
            metadata: Additional metadata
        
        Returns:
            Created memory dictionary
        """
        # Check if we can write
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, storing in cache only")
            return self._create_in_cache(content, memory_type, importance_score, tags, metadata)
        
        # Create memory object
        memory = {
            "id": str(uuid.uuid4()),
            "content": content,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Try AI enhancements if available
        if self.degradation_manager.is_feature_available("ai_features"):
            memory = await self._enhance_with_ai(memory)
        
        # Store based on backend
        try:
            if self.backend_type == StorageBackend.SQLITE:
                memory = await self.backend.create_memory(memory)
            elif self.backend_type == StorageBackend.JSON:
                self.memories[memory["id"]] = memory
                await self._save_to_json()
            else:
                self.memories[memory["id"]] = memory
            
            # Update cache
            if self.cache_enabled:
                self.cache[memory["id"]] = memory
            
            logger.info(f"Created memory {memory['id'][:8]}...")
            return memory
            
        except Exception as e:
            logger.error(f"Failed to persist memory, falling back to cache: {e}")
            return self._create_in_cache(content, memory_type, importance_score, tags, metadata)
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID with cache support"""
        
        # Check cache first
        if self.cache_enabled and memory_id in self.cache:
            return self.cache[memory_id]
        
        # Get from backend
        memory = None
        
        if self.backend_type == StorageBackend.SQLITE:
            memory = await self.backend.get_memory(memory_id)
        elif self.backend_type == StorageBackend.JSON:
            memory = self.memories.get(memory_id)
        else:
            memory = self.memories.get(memory_id)
        
        # Update cache
        if memory and self.cache_enabled:
            self.cache[memory_id] = memory
        
        return memory
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a memory with graceful degradation"""
        
        # Check if we can write
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, cannot update")
            return None
        
        updates = {}
        if content is not None:
            updates["content"] = content
        if importance_score is not None:
            updates["importance_score"] = importance_score
        if tags is not None:
            updates["tags"] = tags
        
        if not updates:
            return await self.get_memory(memory_id)
        
        updates["updated_at"] = datetime.now().isoformat()
        
        # Update based on backend
        if self.backend_type == StorageBackend.SQLITE:
            memory = await self.backend.update_memory(memory_id, updates)
        else:
            if memory_id not in self.memories:
                return None
            
            self.memories[memory_id].update(updates)
            
            if self.backend_type == StorageBackend.JSON:
                await self._save_to_json()
            
            memory = self.memories[memory_id]
        
        # Update cache
        if memory and self.cache_enabled:
            self.cache[memory_id] = memory
        
        return memory
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory with graceful degradation"""
        
        # Check if we can write
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, cannot delete")
            return False
        
        # Delete from backend
        success = False
        
        if self.backend_type == StorageBackend.SQLITE:
            success = await self.backend.delete_memory(memory_id)
        elif self.backend_type == StorageBackend.JSON:
            if memory_id in self.memories:
                del self.memories[memory_id]
                await self._save_to_json()
                success = True
        else:
            if memory_id in self.memories:
                del self.memories[memory_id]
                success = True
        
        # Remove from cache
        if success and memory_id in self.cache:
            del self.cache[memory_id]
        
        return success
    
    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List memories with pagination"""
        
        if self.backend_type == StorageBackend.SQLITE:
            return await self.backend.list_memories(limit, offset)
        else:
            # Sort by created_at
            sorted_memories = sorted(
                self.memories.values(),
                key=lambda m: m.get("created_at", ""),
                reverse=True
            )
            return sorted_memories[offset:offset + limit]
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories with graceful degradation
        
        Falls back from semantic -> full-text -> keyword search
        """
        
        # Try semantic search if available
        if self.degradation_manager.is_feature_available("semantic_search"):
            try:
                return await self._semantic_search(query, limit)
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back: {e}")
        
        # Try full-text search if SQLite
        if self.backend_type == StorageBackend.SQLITE:
            try:
                return await self.backend.search_memories(query, limit)
            except Exception as e:
                logger.warning(f"Full-text search failed, falling back: {e}")
        
        # Fallback to simple keyword search
        return await self._keyword_search(query, limit)
    
    async def _keyword_search(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Simple keyword search fallback"""
        query_lower = query.lower()
        results = []
        
        memories = self.memories if self.backend_type != StorageBackend.SQLITE else {}
        
        for memory in memories.values():
            if query_lower in memory.get("content", "").lower():
                results.append(memory)
                if len(results) >= limit:
                    break
        
        return results
    
    async def _semantic_search(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings (placeholder)"""
        # This would use vector embeddings with Qdrant
        # For now, fall back to keyword search
        return await self._keyword_search(query, limit)
    
    async def _enhance_with_ai(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance memory with AI features (placeholder)"""
        # This would:
        # - Auto-generate tags
        # - Calculate importance score
        # - Generate embeddings
        return memory
    
    def _create_in_cache(
        self,
        content: str,
        memory_type: str,
        importance_score: float,
        tags: List[str],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create memory in cache only (degraded mode)"""
        memory = {
            "id": str(uuid.uuid4()),
            "content": content,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0,
            "ephemeral": True  # Mark as not persisted
        }
        
        self.cache[memory["id"]] = memory
        return memory
    
    def _load_from_json(self):
        """Load memories from JSON file"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r") as f:
                    data = json.load(f)
                    self.memories = data if isinstance(data, dict) else {}
                logger.info(f"Loaded {len(self.memories)} memories from JSON")
            except Exception as e:
                logger.error(f"Failed to load JSON: {e}")
                self.memories = {}
        else:
            self.memories = {}
    
    async def _save_to_json(self):
        """Save memories to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, "w") as f:
                json.dump(self.memories, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory service statistics"""
        base_stats = {
            "backend": self.backend_type.value,
            "degradation_level": self.degradation_manager.current_level.name,
            "cache_size": len(self.cache),
            "ephemeral_memories": sum(
                1 for m in self.cache.values() 
                if m.get("ephemeral", False)
            )
        }
        
        if self.backend_type == StorageBackend.SQLITE:
            backend_stats = await self.backend.get_statistics()
            return {**base_stats, **backend_stats}
        else:
            base_stats["total_memories"] = len(self.memories)
            return base_stats