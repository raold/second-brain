"""
SQLAlchemy models for database tables.

These are the concrete database representations of our domain models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


# Many-to-many association tables
memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", PGUUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE")),
    Column("tag_id", PGUUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE")),
    UniqueConstraint("memory_id", "tag_id", name="uq_memory_tags"),
)

memory_links = Table(
    "memory_links",
    Base.metadata,
    Column("from_memory_id", PGUUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE")),
    Column("to_memory_id", PGUUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE")),
    Column("link_type", String(50), nullable=True),
    UniqueConstraint("from_memory_id", "to_memory_id", name="uq_memory_links"),
)

session_memories = Table(
    "session_memories",
    Base.metadata,
    Column("session_id", PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE")),
    Column("memory_id", PGUUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE")),
    UniqueConstraint("session_id", "memory_id", name="uq_session_memories"),
)


class UserModel(Base):
    """User table model."""
    
    __tablename__ = "users"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Security
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    # Settings
    preferences = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quotas
    memory_limit = Column(Integer, nullable=False, default=10000)
    storage_limit_mb = Column(Integer, nullable=False, default=5000)
    api_rate_limit = Column(Integer, nullable=False, default=1000)
    
    # Relationships
    memories = relationship("MemoryModel", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("TagModel", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_role_active", "role", "is_active"),
    )


class MemoryModel(Base):
    """Memory table model."""
    
    __tablename__ = "memories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Core content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), nullable=False)
    
    # Metadata
    status = Column(String(50), nullable=False, default="active")
    importance_score = Column(Float, nullable=False, default=0.5)
    confidence_score = Column(Float, nullable=False, default=1.0)
    
    # Source
    source_url = Column(String(1000), nullable=True)
    
    # Embeddings
    embedding = Column(JSON, nullable=True)  # Store as JSON array (legacy)
    embedding_vector = Column(Vector(1536), nullable=True)  # pgvector column for similarity search
    embedding_model = Column(String(100), nullable=True)
    
    # Additional data
    metadata = Column(JSON, nullable=False, default=dict)
    attachments = Column(JSON, nullable=False, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    accessed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Cognitive properties
    retention_strength = Column(Float, nullable=False, default=1.0)
    retrieval_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    user = relationship("UserModel", back_populates="memories")
    tags = relationship("TagModel", secondary=memory_tags, back_populates="memories")
    linked_to = relationship(
        "MemoryModel",
        secondary=memory_links,
        primaryjoin=(id == memory_links.c.from_memory_id),
        secondaryjoin=(id == memory_links.c.to_memory_id),
        backref="linked_from",
    )
    sessions = relationship("SessionModel", secondary=session_memories, back_populates="memories")
    
    __table_args__ = (
        Index("idx_memories_user_type", "user_id", "memory_type"),
        Index("idx_memories_user_status", "user_id", "status"),
        Index("idx_memories_created", "created_at"),
    )


class SessionModel(Base):
    """Session table model."""
    
    __tablename__ = "sessions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    messages = Column(JSON, nullable=False, default=list)
    
    # State
    is_active = Column(Boolean, nullable=False, default=True)
    context = Column(JSON, nullable=False, default=dict)
    
    # Tags
    tags = Column(JSON, nullable=False, default=list)
    
    # Metadata
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserModel", back_populates="sessions")
    memories = relationship("MemoryModel", secondary=session_memories, back_populates="sessions")
    
    __table_args__ = (
        Index("idx_sessions_user_active", "user_id", "is_active"),
        Index("idx_sessions_last_activity", "last_activity_at"),
    )


class TagModel(Base):
    """Tag table model."""
    
    __tablename__ = "tags"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    name = Column(String(100), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Hierarchy
    parent_id = Column(PGUUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=True)
    
    # Display
    color = Column(String(7), nullable=True)  # Hex color
    icon = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Statistics
    usage_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="tags")
    memories = relationship("MemoryModel", secondary=memory_tags, back_populates="tags")
    parent = relationship("TagModel", remote_side=[id], backref="children")
    
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_tag_name"),
        Index("idx_tags_user_usage", "user_id", "usage_count"),
    )


class EventModel(Base):
    """Event store table model."""
    
    __tablename__ = "events"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    aggregate_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(Integer, nullable=False)
    event_data = Column(JSON, nullable=False)
    
    # Metadata
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    correlation_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    causation_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Version for optimistic locking
    stream_version = Column(Integer, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("aggregate_id", "stream_version", name="uq_aggregate_version"),
        Index("idx_events_type_created", "event_type", "created_at"),
    )


class SnapshotModel(Base):
    """Event snapshot table model."""
    
    __tablename__ = "snapshots"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    aggregate_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("aggregate_id", "version", name="uq_snapshot_version"),
    )