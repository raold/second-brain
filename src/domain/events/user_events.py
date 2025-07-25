"""
User-related domain events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from src.domain.events.base import DomainEvent
from src.domain.models.user import UserRole


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """Event raised when a user is created."""
    
    email: str
    username: str
    role: UserRole
    
    @property
    def event_type(self) -> str:
        return "user.created"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "email": self.email,
            "username": self.username,
            "role": self.role.value,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class UserUpdated(DomainEvent):
    """Event raised when a user profile is updated."""
    
    changes: dict[str, Any]
    
    @property
    def event_type(self) -> str:
        return "user.updated"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "changes": self.changes,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class UserDeleted(DomainEvent):
    """Event raised when a user is deleted."""
    
    deletion_type: str  # "deactivated" or "purged"
    reason: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "user.deleted"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "deletion_type": self.deletion_type,
            "reason": self.reason,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    """Event raised when a user logs in."""
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    @property
    def event_type(self) -> str:
        return "user.logged_in"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class UserPromoted(DomainEvent):
    """Event raised when a user is promoted to a new role."""
    
    old_role: UserRole
    new_role: UserRole
    promoted_by: UUID
    
    @property
    def event_type(self) -> str:
        return "user.promoted"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "old_role": self.old_role.value,
            "new_role": self.new_role.value,
            "promoted_by": str(self.promoted_by),
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class UserVerified(DomainEvent):
    """Event raised when a user's email is verified."""
    
    verification_method: str  # "email", "admin", etc.
    
    @property
    def event_type(self) -> str:
        return "user.verified"
    
    @property
    def event_version(self) -> int:
        return 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": str(self.aggregate_id),
            "verification_method": self.verification_method,
            "metadata": self.metadata.to_dict(),
        }