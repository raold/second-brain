"""
Memory repository interface.

Defines the contract for memory persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus


class MemoryRepository(ABC):
    """Abstract repository for memory persistence."""
    
    @abstractmethod
    async def get(self, memory_id: MemoryId) -> Optional[Memory]:
        """
        Get a memory by ID.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            The memory if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[MemoryStatus] = None,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """
        Get memories for a user.
        
        Args:
            user_id: The user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            memory_type: Filter by type
            
        Returns:
            List of memories
        """
        pass
    
    @abstractmethod
    async def save(self, memory: Memory) -> Memory:
        """
        Save a memory (create or update).
        
        Args:
            memory: The memory to save
            
        Returns:
            The saved memory
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: MemoryId) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """
        Search memories by content.
        
        Args:
            user_id: The user ID
            query: Search query
            limit: Maximum results
            memory_type: Filter by type
            
        Returns:
            List of matching memories
        """
        pass
    
    @abstractmethod
    async def get_by_tags(
        self,
        user_id: UUID,
        tags: list[str],
        match_all: bool = False,
        limit: int = 100,
    ) -> list[Memory]:
        """
        Get memories by tags.
        
        Args:
            user_id: The user ID
            tags: Tags to search for
            match_all: If True, match all tags; if False, match any
            limit: Maximum results
            
        Returns:
            List of memories with matching tags
        """
        pass
    
    @abstractmethod
    async def get_linked(self, memory_id: MemoryId) -> list[Memory]:
        """
        Get memories linked to a specific memory.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            List of linked memories
        """
        pass
    
    @abstractmethod
    async def count_by_user(
        self,
        user_id: UUID,
        status: Optional[MemoryStatus] = None,
    ) -> int:
        """
        Count memories for a user.
        
        Args:
            user_id: The user ID
            status: Filter by status
            
        Returns:
            Number of memories
        """
        pass
    
    @abstractmethod
    async def get_similar(
        self,
        memory_id: MemoryId,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[tuple[Memory, float]]:
        """
        Get memories similar to a given memory.
        
        Args:
            memory_id: The memory ID
            limit: Maximum results
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of (memory, similarity_score) tuples
        """
        pass
    
    @abstractmethod
    async def update_embedding(
        self,
        memory_id: MemoryId,
        embedding: list[float],
        model: str,
    ) -> bool:
        """
        Update memory embedding.
        
        Args:
            memory_id: The memory ID
            embedding: Embedding vector
            model: Model used to generate embedding
            
        Returns:
            True if updated, False if not found
        """
        pass