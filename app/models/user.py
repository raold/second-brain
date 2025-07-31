"""User model for Second Brain"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from pydantic import Field


class User(BaseModel):
    """User model"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_active: bool = Field(True, description="Whether user is active")