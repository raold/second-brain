"""
Memory Service Adapter for v4.2.0
Provides backward compatibility by redirecting to PostgreSQL service
"""

import os
from typing import List, Dict, Any, Optional
import asyncio
import logging

from app.services.memory_service_postgres import MemoryServicePostgres

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Backward compatibility adapter for v4.2.0
    Redirects all operations to PostgreSQL backend
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize memory service adapter.
        Note: persist_path is ignored as we use PostgreSQL now
        """
        if persist_path:
            logger.warning(
                "persist_path parameter is deprecated in v4.2.0. "
                "Using PostgreSQL backend instead."
            )
        
        # Initialize PostgreSQL service
        db_url = os.getenv("DATABASE_URL", "postgresql://secondbrain:changeme@localhost/secondbrain")
        self._postgres_service = MemoryServicePostgres(
            connection_string=db_url,
            enable_embeddings=False  # Disable by default for compatibility
        )
        
        # Initialize on first use
        self._initialized = False
        
    def _ensure_initialized(self):
        """Ensure the PostgreSQL service is initialized"""
        if not self._initialized:
            asyncio.create_task(self._postgres_service.initialize())
            self._initialized = True
    
    def _run_async(self, coro):
        """Run async method synchronously for compatibility"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is already running, create a task
            task = asyncio.create_task(coro)
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        else:
            # If loop is not running, run the coroutine
            return loop.run_until_complete(coro)
    
    async def create_memory(
        self,
        content: str,
        memory_type: str = "generic",
        importance_score: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new memory using PostgreSQL backend"""
        self._ensure_initialized()
        return await self._postgres_service.create_memory(
            content=content,
            memory_type=memory_type,
            importance_score=importance_score,
            tags=tags,
            metadata=metadata,
            generate_embedding=False
        )
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        self._ensure_initialized()
        return await self._postgres_service.get_memory(memory_id)
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a memory"""
        self._ensure_initialized()
        return await self._postgres_service.update_memory(
            memory_id=memory_id,
            content=content,
            importance_score=importance_score,
            tags=tags
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        self._ensure_initialized()
        return await self._postgres_service.delete_memory(memory_id)
    
    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List memories with filtering"""
        self._ensure_initialized()
        return await self._postgres_service.list_memories(
            limit=limit,
            offset=offset,
            memory_type=memory_type,
            tags=tags
        )
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories"""
        self._ensure_initialized()
        return await self._postgres_service.keyword_search(query, limit)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        self._ensure_initialized()
        return await self._postgres_service.get_statistics()
    
    # Synchronous compatibility methods
    def create_memory_sync(self, **kwargs):
        """Synchronous version for backward compatibility"""
        return self._run_async(self.create_memory(**kwargs))
    
    def get_memory_sync(self, memory_id: str):
        """Synchronous version for backward compatibility"""
        return self._run_async(self.get_memory(memory_id))
    
    def list_memories_sync(self, **kwargs):
        """Synchronous version for backward compatibility"""
        return self._run_async(self.list_memories(**kwargs))
    
    def search_memories_sync(self, query: str, limit: int = 10):
        """Synchronous version for backward compatibility"""
        return self._run_async(self.search_memories(query, limit))