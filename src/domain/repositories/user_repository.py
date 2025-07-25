"""
User repository interface.

Defines the contract for user persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.user import User, UserId, UserRole


class UserRepository(ABC):
    """Abstract repository for user persistence."""
    
    @abstractmethod
    async def get(self, user_id: UserId) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        
        Args:
            email: The user's email
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: The username
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Save a user (create or update).
        
        Args:
            user: The user to save
            
        Returns:
            The saved user
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: UserId) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> list[User]:
        """
        List users with optional filters.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Filter by role
            is_active: Filter by active status
            
        Returns:
            List of users
        """
        pass
    
    @abstractmethod
    async def count(
        self,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Count users with optional filters.
        
        Args:
            role: Filter by role
            is_active: Filter by active status
            
        Returns:
            Number of users
        """
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if a user exists with the given email.
        
        Args:
            email: The email to check
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """
        Check if a user exists with the given username.
        
        Args:
            username: The username to check
            
        Returns:
            True if exists, False otherwise
        """
        pass