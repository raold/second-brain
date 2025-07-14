from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

class PayloadType(str, Enum):
    NOTE = "note"
    MEMORY = "memory"
    TASK = "task"
    BOOKMARK = "bookmark"
    PERSON = "person"

class Payload(BaseModel):
    """Payload model for ingesting data into the second brain system."""
    
    id: str = Field(..., description="Unique identifier for the payload")
    type: PayloadType = Field(..., description="Type of payload")
    intent: Optional[str] = Field(None, description="Intent of the payload (store, execute, etc.)")
    target: Optional[str] = Field(None, description="Target destination for the payload")
    context: str = Field(..., description="Context of the payload")
    priority: Priority = Field(default=Priority.NORMAL, description="Priority level")
    ttl: str = Field(..., description="Time to live for the payload")
    data: Dict[str, Any] = Field(..., description="Main data content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
