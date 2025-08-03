"""
Memory Service - PostgreSQL Only Implementation
Single-user-per-container with PostgreSQL + pgvector
"""

import os
from typing import List, Dict, Any, Optional
import asyncio

from app.services.memory_service_postgres import MemoryServicePostgres
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    Memory service for v4.2.0 - PostgreSQL only
    Single user per container, no multi-tenancy
    """
    
    def __init__(self):
        """Initialize PostgreSQL memory service"""
        db_url = os.getenv("DATABASE_URL", "postgresql://secondbrain:changeme@localhost/secondbrain")
        self.service = MemoryServicePostgres(
            connection_string=db_url,
            enable_embeddings=False  # Disabled by default for performance
        )
        self._initialized = False
    
    async def initialize(self):
        """Initialize the PostgreSQL connection"""
        if not self._initialized:
            await self.service.initialize()
            self._initialized = True
            logger.info("Memory service initialized with PostgreSQL")
    
    async def create_memory(
        self,
        content: str,
        memory_type: str = "generic",
        importance_score: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new memory"""
        await self.initialize()
        return await self.service.create_memory(
            content=content,
            memory_type=memory_type,
            importance_score=importance_score,
            tags=tags,
            metadata=metadata,
            generate_embedding=False
        )
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        await self.initialize()
        return await self.service.get_memory(memory_id)
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a memory"""
        await self.initialize()
        return await self.service.update_memory(
            memory_id=memory_id,
            content=content,
            importance_score=importance_score,
            tags=tags,
            metadata=metadata
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        await self.initialize()
        return await self.service.delete_memory(memory_id)
    
    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List memories with filtering"""
        await self.initialize()
        return await self.service.list_memories(
            limit=limit,
            offset=offset,
            memory_type=memory_type,
            tags=tags
        )
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        search_type: str = "text"
    ) -> List[Dict[str, Any]]:
        """Search memories"""
        await self.initialize()
        if search_type == "semantic":
            return await self.service.semantic_search(query, limit)
        elif search_type == "hybrid":
            return await self.service.search_memories(
                query=query,
                limit=limit,
                search_type="hybrid"
            )
        else:
            return await self.service.keyword_search(query, limit)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        await self.initialize()
        return await self.service.get_statistics()