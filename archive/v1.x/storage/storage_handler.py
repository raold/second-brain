"""
Simplified storage interface for Second Brain.
Uses PostgreSQL as primary storage with optional Qdrant integration.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.storage.postgres_client import get_postgres_client
from app.utils.logger import logger

# Optional Qdrant integration
try:
    from app.storage.qdrant_client import qdrant_upsert, qdrant_search
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    qdrant_upsert = None
    qdrant_search = None
    logger.warning("Qdrant not available, using PostgreSQL only")


class StorageHandler:
    """
    Simplified storage handler that uses PostgreSQL as primary storage.
    Optionally integrates with Qdrant for vector search if available.
    """
    
    def __init__(self):
        self.postgres_enabled = True
        self.qdrant_enabled = QDRANT_AVAILABLE
        self._stats = {
            "total_stores": 0,
            "successful_stores": 0,
            "total_searches": 0,
            "successful_searches": 0
        }
    
    async def store_memory(
        self,
        payload_id: str,
        text_content: str,
        intent_type: Optional[str] = None,
        priority: str = "normal",
        source: str = "api",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        create_embedding: bool = True
    ) -> Tuple[str, Optional[List[float]]]:
        """
        Store a memory in PostgreSQL and optionally in Qdrant.
        
        Args:
            payload_id: Unique identifier for the memory
            text_content: The text content to store
            intent_type: Type of intent (note, todo, reminder, etc.)
            priority: Priority level (low, normal, high)
            source: Source of the memory (api, voice, etc.)
            tags: List of tags
            metadata: Additional metadata
            user: User identifier
            create_embedding: Whether to create embeddings
            
        Returns:
            Tuple of (memory_id, embedding_vector)
        """
        start_time = time.time()
        self._stats["total_stores"] += 1
        
        try:
            # Store in PostgreSQL (primary storage)
            client = await get_postgres_client()
            
            # Prepare metadata
            full_metadata = {
                "payload_id": payload_id,
                "user": user,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }
            
            # Store memory in PostgreSQL
            memory_id = await client.store_memory(
                text_content=text_content,
                intent_type=intent_type or "note",
                priority=priority,
                source=source,
                tags=tags or [],
                metadata=full_metadata,
                embedding_vector=None  # Will be populated if embedding is created
            )
            
            embedding_vector = None
            
            # Optionally store in Qdrant for vector search
            if self.qdrant_enabled and create_embedding and qdrant_upsert:
                try:
                    payload = {
                        "id": payload_id,
                        "data": {
                            "note": text_content,
                            "tags": tags or []
                        },
                        "meta": {
                            "intent_type": intent_type or "note",
                            "priority": priority,
                            "user": user,
                            "memory_id": memory_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    qdrant_upsert(payload)
                    logger.info(f"Memory {payload_id} stored in both PostgreSQL and Qdrant")
                    
                except Exception as e:
                    logger.warning(f"Failed to store in Qdrant (continuing with PostgreSQL): {e}")
            
            self._stats["successful_stores"] += 1
            
            duration = time.time() - start_time
            logger.info(f"Memory {payload_id} stored successfully in {duration:.2f}s")
            
            return memory_id, embedding_vector
            
        except Exception as e:
            logger.error(f"Failed to store memory {payload_id}: {e}")
            raise
    
    async def search_memories(
        self,
        query_text: str,
        limit: int = 10,
        intent_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[str] = None,
        use_vector_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search memories using PostgreSQL and optionally Qdrant.
        
        Args:
            query_text: Search query
            limit: Number of results
            intent_types: Filter by intent types
            tags: Filter by tags
            priority: Filter by priority
            use_vector_search: Whether to use vector search if available
            
        Returns:
            List of search results
        """
        start_time = time.time()
        self._stats["total_searches"] += 1
        
        try:
            results = []
            
            # Try vector search first if available and requested
            if self.qdrant_enabled and use_vector_search and qdrant_search:
                try:
                    filters = {}
                    if intent_types:
                        filters["intent_type"] = intent_types[0]  # Qdrant filter limitation
                    if tags:
                        filters["tags"] = tags
                    if priority:
                        filters["priority"] = priority
                    
                    qdrant_results = qdrant_search(query_text, top_k=limit, filters=filters)
                    
                    # Convert Qdrant results to standardized format
                    for result in qdrant_results:
                        results.append({
                            "id": result.get("meta", {}).get("memory_id", result.get("id")),
                            "text_content": result.get("data", {}).get("note", ""),
                            "intent_type": result.get("meta", {}).get("intent_type", ""),
                            "priority": result.get("meta", {}).get("priority", "normal"),
                            "tags": result.get("data", {}).get("tags", []),
                            "score": result.get("score", 0.0),
                            "created_at": result.get("meta", {}).get("timestamp", ""),
                            "metadata": result.get("meta", {})
                        })
                    
                    logger.info(f"Vector search returned {len(results)} results")
                    
                except Exception as e:
                    logger.warning(f"Vector search failed, falling back to PostgreSQL: {e}")
                    results = []
            
            # Fallback to PostgreSQL text search if no vector results
            if not results:
                client = await get_postgres_client()
                results = await client.search_memories(
                    query_text=query_text,
                    limit=limit,
                    intent_types=intent_types,
                    tags=tags,
                    priority=priority
                )
                
                logger.info(f"PostgreSQL search returned {len(results)} results")
            
            self._stats["successful_searches"] += 1
            
            duration = time.time() - start_time
            logger.info(f"Search completed in {duration:.2f}s with {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a memory by ID from PostgreSQL.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory data or None if not found
        """
        try:
            client = await get_postgres_client()
            return await client.get_memory(memory_id)
            
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a memory in PostgreSQL.
        
        Args:
            memory_id: Memory ID
            updates: Updates to apply
            
        Returns:
            True if successful
        """
        try:
            client = await get_postgres_client()
            return await client.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False
    
    async def add_feedback(
        self,
        memory_id: str,
        feedback_type: str,
        feedback_value: Optional[float] = None,
        feedback_text: Optional[str] = None
    ) -> str:
        """
        Add feedback for a memory.
        
        Args:
            memory_id: Memory ID
            feedback_type: Type of feedback
            feedback_value: Numeric feedback value
            feedback_text: Text feedback
            
        Returns:
            Feedback ID
        """
        try:
            client = await get_postgres_client()
            return await client.add_feedback(
                memory_id=memory_id,
                feedback_type=feedback_type,
                feedback_value=feedback_value,
                feedback_text=feedback_text
            )
            
        except Exception as e:
            logger.error(f"Failed to add feedback for memory {memory_id}: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Performance statistics
        """
        success_rate = (
            self._stats["successful_stores"] / max(self._stats["total_stores"], 1)
        ) * 100
        
        search_success_rate = (
            self._stats["successful_searches"] / max(self._stats["total_searches"], 1)
        ) * 100
        
        return {
            "storage": {
                "total_stores": self._stats["total_stores"],
                "successful_stores": self._stats["successful_stores"],
                "success_rate": round(success_rate, 2)
            },
            "search": {
                "total_searches": self._stats["total_searches"],
                "successful_searches": self._stats["successful_searches"],
                "success_rate": round(search_success_rate, 2)
            },
            "features": {
                "postgres_enabled": self.postgres_enabled,
                "qdrant_enabled": self.qdrant_enabled
            }
        }


# Global storage handler instance
_storage_handler = None


async def get_storage_handler() -> StorageHandler:
    """
    Get the global storage handler instance.
    
    Returns:
        StorageHandler instance
    """
    global _storage_handler
    if _storage_handler is None:
        _storage_handler = StorageHandler()
    return _storage_handler


# Alias for backward compatibility
async def get_dual_storage() -> StorageHandler:
    """Backward compatibility alias for get_storage_handler."""
    return await get_storage_handler()
