"""
Tag-related Data Transfer Objects.

DTOs for tag operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateTagDTO:
    """DTO for creating a new tag."""
    
    name: str
    parent_id: Optional[UUID] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate fields."""
        if not self.name:
            raise ValueError("Tag name cannot be empty")
        
        # Validate color format
        if self.color and not self.color.startswith("#"):
            raise ValueError("Color must be in hex format (e.g., #FF0000)")


@dataclass
class UpdateTagDTO:
    """DTO for updating tag information."""
    
    name: Optional[str] = None
    parent_id: Optional[UUID] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate fields."""
        if self.name is not None and not self.name:
            raise ValueError("Tag name cannot be empty")
        
        if self.color and not self.color.startswith("#"):
            raise ValueError("Color must be in hex format (e.g., #FF0000)")


@dataclass
class TagDTO:
    """DTO for tag data."""
    
    id: UUID
    name: str
    user_id: UUID
    parent_id: Optional[UUID]
    color: Optional[str]
    icon: Optional[str]
    description: Optional[str]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    children: list['TagDTO'] = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.children is None:
            self.children = []
    
    @classmethod
    def from_domain(cls, tag, include_children=False):
        """Create DTO from domain model."""
        dto = cls(
            id=tag.id.value,
            name=tag.name,
            user_id=tag.user_id,
            parent_id=tag.parent_id.value if tag.parent_id else None,
            color=tag.color,
            icon=tag.icon,
            description=tag.description,
            usage_count=tag.usage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            last_used_at=tag.last_used_at,
        )
        
        if include_children and hasattr(tag, 'children'):
            dto.children = [cls.from_domain(child) for child in tag.children]
        
        return dto


@dataclass
class TagListDTO:
    """DTO for a list of tags."""
    
    tags: list[TagDTO]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1