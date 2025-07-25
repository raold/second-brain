"""
User Domain Model

Represents a user in the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class UserRole(str, Enum):
    """User roles in the system."""
    
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


@dataclass(frozen=True)
class UserId:
    """Value object for User ID."""
    
    value: UUID
    
    @classmethod
    def generate(cls) -> UserId:
        """Generate a new user ID."""
        return cls(value=uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> UserId:
        """Create from string representation."""
        return cls(value=UUID(value))
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)


@dataclass
class User:
    """
    User entity.
    
    Represents a user of the Second Brain system.
    """
    
    # Identity
    id: UserId
    email: str
    username: str
    
    # Profile
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Security
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    
    # Settings
    preferences: dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
    
    # Quotas
    memory_limit: int = 10000  # Number of memories allowed
    storage_limit_mb: int = 5000  # Storage in MB
    api_rate_limit: int = 1000  # Requests per hour
    
    def __post_init__(self) -> None:
        """Validate user after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate user state."""
        if not self.email:
            raise ValueError("Email cannot be empty")
        
        if not self.username:
            raise ValueError("Username cannot be empty")
        
        if "@" not in self.email:
            raise ValueError("Invalid email format")
        
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
    
    def update_profile(
        self,
        full_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> None:
        """Update user profile."""
        if full_name is not None:
            self.full_name = full_name
        if bio is not None:
            self.bio = bio
        if avatar_url is not None:
            self.avatar_url = avatar_url
        self.updated_at = datetime.now(timezone.utc)
    
    def update_email(self, email: str) -> None:
        """Update user email."""
        if not email or "@" not in email:
            raise ValueError("Invalid email format")
        self.email = email
        self.is_verified = False  # Require re-verification
        self.updated_at = datetime.now(timezone.utc)
    
    def verify(self) -> None:
        """Mark user as verified."""
        self.is_verified = True
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def promote_to_premium(self) -> None:
        """Promote user to premium tier."""
        self.role = UserRole.PREMIUM
        self.memory_limit = 50000
        self.storage_limit_mb = 50000
        self.api_rate_limit = 10000
        self.updated_at = datetime.now(timezone.utc)
    
    def promote_to_admin(self) -> None:
        """Promote user to admin."""
        self.role = UserRole.ADMIN
        self.memory_limit = -1  # Unlimited
        self.storage_limit_mb = -1  # Unlimited
        self.api_rate_limit = -1  # Unlimited
        self.updated_at = datetime.now(timezone.utc)
    
    def record_login(self) -> None:
        """Record user login."""
        self.last_login_at = datetime.now(timezone.utc)
    
    def update_preference(self, key: str, value: Any) -> None:
        """Update a user preference."""
        self.preferences[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.preferences.get(key, default)
    
    def can_create_memory(self, current_count: int) -> bool:
        """Check if user can create more memories."""
        if self.memory_limit == -1:  # Unlimited
            return True
        return current_count < self.memory_limit
    
    def can_use_storage(self, current_usage_mb: int, additional_mb: int) -> bool:
        """Check if user has storage quota."""
        if self.storage_limit_mb == -1:  # Unlimited
            return True
        return (current_usage_mb + additional_mb) <= self.storage_limit_mb
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "memory_limit": self.memory_limit,
            "storage_limit_mb": self.storage_limit_mb,
            "api_rate_limit": self.api_rate_limit,
        }