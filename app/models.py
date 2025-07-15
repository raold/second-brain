import datetime
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()

class Memory(AsyncAttrs, Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    qdrant_id: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(String, nullable=False)
    intent: Mapped[str] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    user: Mapped[str] = mapped_column(String, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


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
    """Payload model for ingesting data into the second brain system.
    intent: semantic classification (question, reminder, note, todo, command, other)
    """
    
    id: str = Field(..., description="Unique identifier for the payload")
    type: PayloadType = Field(..., description="Type of payload")
    intent: Optional[str] = Field(
        None,
        description="Intent of the payload (semantic: question, reminder, note, todo, command, other)"
    )
    target: Optional[str] = Field(None, description="Target destination for the payload")
    context: str = Field(..., description="Context of the payload")
    priority: Priority = Field(default=Priority.NORMAL, description="Priority level")
    ttl: str = Field(..., description="Time to live for the payload")
    data: Dict[str, Any] = Field(..., description="Main data content")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class MemoryFeedback(AsyncAttrs, Base):
    __tablename__ = "memory_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped[str] = mapped_column(String, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String, nullable=False)  # upvote, correct, ignore
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
