"""
User-related Data Transfer Objects.

DTOs for user operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.models.user import UserRole


@dataclass
class CreateUserDTO:
    """DTO for creating a new user."""
    
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    
    def __post_init__(self):
        """Validate fields."""
        # Basic email validation
        if "@" not in self.email:
            raise ValueError("Invalid email format")
        
        # Username validation
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        # Password validation
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")


@dataclass
class UpdateUserDTO:
    """DTO for updating user information."""
    
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[dict] = None
    
    def __post_init__(self):
        """Validate fields."""
        if self.email and "@" not in self.email:
            raise ValueError("Invalid email format")
        
        if self.username and len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")


@dataclass
class UserDTO:
    """DTO for user data."""
    
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    preferences: dict
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    memory_limit: int
    storage_limit_mb: int
    api_rate_limit: int
    
    @classmethod
    def from_domain(cls, user):
        """Create DTO from domain model."""
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            memory_limit=user.memory_limit,
            storage_limit_mb=user.storage_limit_mb,
            api_rate_limit=user.api_rate_limit,
        )


@dataclass
class LoginDTO:
    """DTO for user login."""
    
    username_or_email: str
    password: str
    
    def __post_init__(self):
        """Validate fields."""
        if not self.username_or_email:
            raise ValueError("Username or email is required")
        if not self.password:
            raise ValueError("Password is required")


@dataclass
class TokenDTO:
    """DTO for authentication tokens."""
    
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds
    
    @property
    def authorization_header(self) -> str:
        """Get the authorization header value."""
        return f"{self.token_type} {self.access_token}"