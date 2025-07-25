"""
Tag Domain Model

Represents a tag for organizing content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TagId:
    """Value object for Tag ID."""
    
    value: UUID
    
    @classmethod
    def generate(cls) -> TagId:
        """Generate a new tag ID."""
        return cls(value=uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> TagId:
        """Create from string representation."""
        return cls(value=UUID(value))
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)


@dataclass
class Tag:
    """
    Tag entity.
    
    Used for organizing and categorizing memories.
    """
    
    # Identity
    id: TagId
    name: str
    user_id: UUID
    
    # Hierarchy
    parent_id: Optional[TagId] = None
    
    # Display
    color: Optional[str] = None  # Hex color code
    icon: Optional[str] = None  # Icon name or emoji
    description: Optional[str] = None
    
    # Statistics
    usage_count: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate tag after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate tag state."""
        if not self.name:
            raise ValueError("Tag name cannot be empty")
        
        if self.color and not self._is_valid_hex_color(self.color):
            raise ValueError("Invalid color format. Use hex color code (e.g., #FF5733)")
        
        # Normalize tag name
        self.name = self.name.lower().strip()
    
    @staticmethod
    def _is_valid_hex_color(color: str) -> bool:
        """Check if color is valid hex format."""
        if not color.startswith("#"):
            return False
        if len(color) not in [4, 7]:  # #RGB or #RRGGBB
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False
    
    def update_name(self, name: str) -> None:
        """Update tag name."""
        if not name:
            raise ValueError("Tag name cannot be empty")
        self.name = name.lower().strip()
        self.updated_at = datetime.now(timezone.utc)
    
    def update_color(self, color: Optional[str]) -> None:
        """Update tag color."""
        if color and not self._is_valid_hex_color(color):
            raise ValueError("Invalid color format")
        self.color = color
        self.updated_at = datetime.now(timezone.utc)
    
    def update_icon(self, icon: Optional[str]) -> None:
        """Update tag icon."""
        self.icon = icon
        self.updated_at = datetime.now(timezone.utc)
    
    def update_description(self, description: Optional[str]) -> None:
        """Update tag description."""
        self.description = description
        self.updated_at = datetime.now(timezone.utc)
    
    def set_parent(self, parent_id: Optional[TagId]) -> None:
        """Set parent tag."""
        if parent_id == self.id:
            raise ValueError("Tag cannot be its own parent")
        self.parent_id = parent_id
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1
        self.last_used_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def decrement_usage(self) -> None:
        """Decrement usage count."""
        if self.usage_count > 0:
            self.usage_count -= 1
            self.updated_at = datetime.now(timezone.utc)
    
    def is_child_of(self, tag_id: TagId) -> bool:
        """Check if this tag is a child of another tag."""
        return self.parent_id == tag_id
    
    def has_parent(self) -> bool:
        """Check if tag has a parent."""
        return self.parent_id is not None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "user_id": str(self.user_id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "color": self.color,
            "icon": self.icon,
            "description": self.description,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }