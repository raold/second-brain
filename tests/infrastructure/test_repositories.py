"""
Test repository implementations.

Validates that concrete repositories implement interfaces correctly.
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.domain.models.memory import Memory, MemoryId, MemoryStatus, MemoryType
from src.domain.models.user import User, UserRole
from src.domain.models.session import Session, SessionId
from src.domain.models.tag import Tag, TagId
from src.infrastructure.database.models import Base
from src.infrastructure.database.repositories import (
    SQLMemoryRepository,
    SQLUserRepository,
    SQLSessionRepository,
    SQLTagRepository,
)


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    async with AsyncSession(engine) as session:
        yield session


@pytest.mark.asyncio
async def test_user_repository(session):
    """Test user repository operations."""
    repo = SQLUserRepository(session)
    
    # Create user
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        role=UserRole.USER,
    )
    
    # Save user
    saved_user = await repo.save(user)
    await session.commit()
    
    assert saved_user.id == user.id
    
    # Get by ID
    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.email == user.email
    
    # Get by email
    by_email = await repo.get_by_email(user.email)
    assert by_email is not None
    assert by_email.id == user.id
    
    # Get by username
    by_username = await repo.get_by_username(user.username)
    assert by_username is not None
    assert by_username.id == user.id
    
    # Update
    user.full_name = "Test User"
    await repo.save(user)
    await session.commit()
    
    updated = await repo.get(user.id)
    assert updated.full_name == "Test User"
    
    # Search
    results = await repo.search("test")
    assert len(results) == 1
    assert results[0].id == user.id
    
    # Delete
    deleted = await repo.delete(user.id)
    await session.commit()
    assert deleted is True
    
    # Verify deleted
    not_found = await repo.get(user.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_memory_repository(session):
    """Test memory repository operations."""
    # First create a user
    user_repo = SQLUserRepository(session)
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        role=UserRole.USER,
    )
    await user_repo.save(user)
    
    repo = SQLMemoryRepository(session)
    
    # Create memory
    memory = Memory(
        id=MemoryId(uuid4()),
        user_id=user.id,
        title="Test Memory",
        content="Test content",
        memory_type=MemoryType.NOTE,
    )
    
    # Save memory
    saved = await repo.save(memory)
    await session.commit()
    
    assert saved.id == memory.id
    
    # Get by ID
    fetched = await repo.get(memory.id)
    assert fetched is not None
    assert fetched.title == memory.title
    
    # Get by user
    user_memories = await repo.get_by_user(user.id)
    assert len(user_memories) == 1
    assert user_memories[0].id == memory.id
    
    # Search
    results = await repo.search(user.id, "Test")
    assert len(results) == 1
    assert results[0].id == memory.id
    
    # Update access time
    await repo.update_access_time(memory.id)
    await session.commit()
    
    updated = await repo.get(memory.id)
    assert updated.retrieval_count == 1
    
    # Count
    count = await repo.count_by_user(user.id)
    assert count == 1
    
    # Delete
    deleted = await repo.delete(memory.id)
    await session.commit()
    assert deleted is True


@pytest.mark.asyncio
async def test_tag_repository(session):
    """Test tag repository operations."""
    # First create a user
    user_repo = SQLUserRepository(session)
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        role=UserRole.USER,
    )
    await user_repo.save(user)
    
    repo = SQLTagRepository(session)
    
    # Create tag
    tag = Tag(
        id=TagId(uuid4()),
        name="test-tag",
        user_id=user.id,
        color="#FF0000",
    )
    
    # Save tag
    saved = await repo.save(tag)
    await session.commit()
    
    assert saved.id == tag.id
    
    # Get by ID
    fetched = await repo.get(tag.id)
    assert fetched is not None
    assert fetched.name == tag.name
    
    # Get by name
    by_name = await repo.get_by_name(user.id, tag.name)
    assert by_name is not None
    assert by_name.id == tag.id
    
    # Get by user
    user_tags = await repo.get_by_user(user.id)
    assert len(user_tags) == 1
    assert user_tags[0].id == tag.id
    
    # Search
    results = await repo.search(user.id, "test")
    assert len(results) == 1
    assert results[0].id == tag.id
    
    # Create child tag
    child_tag = Tag(
        id=TagId(uuid4()),
        name="child-tag",
        user_id=user.id,
        parent_id=tag.id,
    )
    await repo.save(child_tag)
    await session.commit()
    
    # Get children
    children = await repo.get_children(tag.id)
    assert len(children) == 1
    assert children[0].id == child_tag.id
    
    # Get hierarchy
    hierarchy = await repo.get_hierarchy(user.id)
    assert None in hierarchy  # Root level
    assert tag.id in hierarchy  # Parent level
    
    # Delete
    deleted = await repo.delete(tag.id)
    await session.commit()
    assert deleted is True


@pytest.mark.asyncio
async def test_session_repository(session):
    """Test session repository operations."""
    # First create a user
    user_repo = SQLUserRepository(session)
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        role=UserRole.USER,
    )
    await user_repo.save(user)
    
    repo = SQLSessionRepository(session)
    
    # Create session
    chat_session = Session(
        id=SessionId(uuid4()),
        user_id=user.id,
        title="Test Session",
        messages=[],
    )
    
    # Save session
    saved = await repo.save(chat_session)
    await session.commit()
    
    assert saved.id == chat_session.id
    
    # Get by ID
    fetched = await repo.get(chat_session.id)
    assert fetched is not None
    assert fetched.title == chat_session.title
    
    # Get by user
    user_sessions = await repo.get_by_user(user.id)
    assert len(user_sessions) == 1
    assert user_sessions[0].id == chat_session.id
    
    # Get active
    active = await repo.get_active_sessions(user.id)
    assert len(active) == 1
    assert active[0].id == chat_session.id
    
    # Search
    results = await repo.search(user.id, "Test")
    assert len(results) == 1
    assert results[0].id == chat_session.id
    
    # Update activity
    await repo.update_activity(chat_session.id)
    await session.commit()
    
    # Count
    count = await repo.count_by_user(user.id)
    assert count == 1
    
    # Delete
    deleted = await repo.delete(chat_session.id)
    await session.commit()
    assert deleted is True


if __name__ == "__main__":
    # Run tests
    asyncio.run(pytest.main([__file__, "-v"]))