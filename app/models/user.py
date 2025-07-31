"""User model for Second Brain"""

from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str | None = Field(None, description="User name")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_active: bool = Field(True, description="Whether user is active")
