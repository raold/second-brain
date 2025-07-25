"""
Tag repository interface.

Defines the contract for tag persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.models.tag import Tag, TagId


class TagRepository(ABC):
    """Abstract repository for tag persistence."""
    
    @abstractmethod
    async def get(self, tag_id: TagId) -> Optional[Tag]:
        """
        Get a tag by ID.
        
        Args:
            tag_id: The tag ID
            
        Returns:
            The tag if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_name(self, user_id: UUID, name: str) -> Optional[Tag]:
        """
        Get a tag by name for a user.
        
        Args:
            user_id: The user ID
            name: The tag name
            
        Returns:
            The tag if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        parent_id: Optional[TagId] = None,
    ) -> list[Tag]:
        """
        Get tags for a user.
        
        Args:
            user_id: The user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            parent_id: Filter by parent tag
            
        Returns:
            List of tags
        """
        pass
    
    @abstractmethod
    async def save(self, tag: Tag) -> Tag:
        """
        Save a tag (create or update).
        
        Args:
            tag: The tag to save
            
        Returns:
            The saved tag
        """
        pass
    
    @abstractmethod
    async def delete(self, tag_id: TagId) -> bool:
        """
        Delete a tag.
        
        Args:
            tag_id: The tag ID
            
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
    ) -> list[Tag]:
        """
        Search tags by name or description.
        
        Args:
            user_id: The user ID
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching tags
        """
        pass
    
    @abstractmethod
    async def get_popular(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[Tag]:
        """
        Get most popular tags by usage count.
        
        Args:
            user_id: The user ID
            limit: Maximum results
            
        Returns:
            List of popular tags
        """
        pass
    
    @abstractmethod
    async def get_children(self, tag_id: TagId) -> list[Tag]:
        """
        Get child tags of a parent tag.
        
        Args:
            tag_id: The parent tag ID
            
        Returns:
            List of child tags
        """
        pass
    
    @abstractmethod
    async def get_hierarchy(self, user_id: UUID) -> dict[Optional[TagId], list[Tag]]:
        """
        Get complete tag hierarchy for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary mapping parent IDs to their children
        """
        pass
    
    @abstractmethod
    async def merge_tags(
        self,
        source_tag_id: TagId,
        target_tag_id: TagId,
    ) -> bool:
        """
        Merge one tag into another.
        
        Args:
            source_tag_id: Tag to merge from (will be deleted)
            target_tag_id: Tag to merge into
            
        Returns:
            True if successful, False otherwise
        """
        pass