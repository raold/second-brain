"""
Test data factories for v3.0.0.

Provides factory functions for creating test data.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus
from src.domain.models.session import Session, SessionId, Message, MessageRole, SessionContext
from src.domain.models.tag import Tag, TagId
from src.domain.models.user import User, UserId, UserRole, UserPreferences


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create(
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password_hash: str = "$2b$12$test_hash",
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        is_verified: bool = True,
        preferences: Optional[UserPreferences] = None,
    ) -> User:
        """Create a test user."""
        user_id = user_id or uuid4()
        email = email or f"user_{user_id}@example.com"
        username = username or f"user_{str(user_id)[:8]}"
        
        return User(
            id=UserId(user_id),
            email=email,
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
            is_verified=is_verified,
            preferences=preferences or UserPreferences(),
        )
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> List[User]:
        """Create multiple test users."""
        return [UserFactory.create(**kwargs) for _ in range(count)]


class MemoryFactory:
    """Factory for creating test memories."""
    
    @staticmethod
    def create(
        memory_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        memory_type: MemoryType = MemoryType.FACT,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        importance_score: float = 0.5,
        confidence_score: float = 1.0,
        source_url: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        embedding_model: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[List[UUID]] = None,
        linked_memories: Optional[List[MemoryId]] = None,
        attachments: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ) -> Memory:
        """Create a test memory."""
        memory_id = memory_id or uuid4()
        user_id = user_id or uuid4()
        title = title or f"Test Memory {str(memory_id)[:8]}"
        content = content or f"This is test content for memory {str(memory_id)[:8]}"
        
        memory = Memory(
            id=MemoryId(memory_id),
            user_id=user_id,
            title=title,
            content=content,
            memory_type=memory_type,
            status=status,
            importance_score=importance_score,
            confidence_score=confidence_score,
            source_url=source_url,
            embedding=embedding,
            embedding_model=embedding_model,
            metadata=metadata or {},
            tags=tags or [],
            linked_memories=linked_memories or [],
            attachments=attachments or [],
        )
        
        if created_at:
            memory.created_at = created_at
            memory.updated_at = created_at
            memory.accessed_at = created_at
        
        return memory
    
    @staticmethod
    def create_batch(
        count: int,
        user_id: Optional[UUID] = None,
        **kwargs
    ) -> List[Memory]:
        """Create multiple test memories."""
        user_id = user_id or uuid4()
        return [
            MemoryFactory.create(user_id=user_id, **kwargs)
            for _ in range(count)
        ]
    
    @staticmethod
    def create_with_embedding(
        embedding_dim: int = 1536,
        **kwargs
    ) -> Memory:
        """Create a memory with mock embedding."""
        import random
        
        # Create deterministic but varied embedding
        memory_id = kwargs.get("memory_id", uuid4())
        seed = hash(str(memory_id)) % 1000000
        random.seed(seed)
        
        embedding = [random.random() for _ in range(embedding_dim)]
        
        return MemoryFactory.create(
            memory_id=memory_id,
            embedding=embedding,
            embedding_model="test-model",
            **kwargs
        )
    
    @staticmethod
    def create_linked_memories(
        count: int = 3,
        user_id: Optional[UUID] = None,
    ) -> List[Memory]:
        """Create a set of linked memories."""
        user_id = user_id or uuid4()
        memories = []
        
        # Create memories
        for i in range(count):
            memory = MemoryFactory.create(
                user_id=user_id,
                title=f"Linked Memory {i+1}",
                content=f"Content for linked memory {i+1}",
            )
            memories.append(memory)
        
        # Link them in a chain
        for i in range(len(memories) - 1):
            memories[i].link_memory(memories[i+1].id)
            memories[i+1].link_memory(memories[i].id)
        
        return memories


class SessionFactory:
    """Factory for creating test sessions."""
    
    @staticmethod
    def create(
        session_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        messages: Optional[List[Message]] = None,
        context: Optional[SessionContext] = None,
        memory_ids: Optional[List[MemoryId]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_at: Optional[datetime] = None,
    ) -> Session:
        """Create a test session."""
        session_id = session_id or uuid4()
        user_id = user_id or uuid4()
        title = title or f"Test Session {str(session_id)[:8]}"
        
        session = Session(
            id=SessionId(session_id),
            user_id=user_id,
            title=title,
            description=description,
            is_active=is_active,
            messages=messages or [],
            context=context or SessionContext(),
            memory_ids=memory_ids or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        
        if created_at:
            session.created_at = created_at
            session.updated_at = created_at
            session.last_activity_at = created_at
        
        return session
    
    @staticmethod
    def create_with_messages(
        message_count: int = 5,
        **kwargs
    ) -> Session:
        """Create a session with messages."""
        session = SessionFactory.create(**kwargs)
        
        for i in range(message_count):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            content = f"Message {i+1}: {'User' if role == MessageRole.USER else 'Assistant'} message"
            
            session.add_message(role, content)
        
        return session
    
    @staticmethod
    def create_research_session(
        user_id: Optional[UUID] = None,
        memory_count: int = 3,
    ) -> tuple[Session, List[Memory]]:
        """Create a research session with associated memories."""
        user_id = user_id or uuid4()
        
        # Create memories
        memories = MemoryFactory.create_batch(
            memory_count,
            user_id=user_id,
            memory_type=MemoryType.FACT,
        )
        
        # Create session
        session = SessionFactory.create(
            user_id=user_id,
            title="Research Session",
            description="Researching test topics",
            memory_ids=[m.id for m in memories],
            tags=["research", "test"],
        )
        
        return session, memories


class TagFactory:
    """Factory for creating test tags."""
    
    @staticmethod
    def create(
        tag_id: Optional[UUID] = None,
        name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        parent_id: Optional[TagId] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        description: Optional[str] = None,
        usage_count: int = 0,
    ) -> Tag:
        """Create a test tag."""
        tag_id = tag_id or uuid4()
        user_id = user_id or uuid4()
        name = name or f"tag-{str(tag_id)[:8]}"
        
        return Tag(
            id=TagId(tag_id),
            name=name,
            user_id=user_id,
            parent_id=parent_id,
            color=color,
            icon=icon,
            description=description,
            usage_count=usage_count,
        )
    
    @staticmethod
    def create_hierarchy(
        user_id: Optional[UUID] = None,
        depth: int = 3,
        children_per_node: int = 2,
    ) -> List[Tag]:
        """Create a hierarchical tag structure."""
        user_id = user_id or uuid4()
        tags = []
        
        # Create root tag
        root = TagFactory.create(
            user_id=user_id,
            name="root",
            color="#000000",
            icon="📁",
        )
        tags.append(root)
        
        # Create children recursively
        def create_children(parent: Tag, current_depth: int):
            if current_depth >= depth:
                return
            
            for i in range(children_per_node):
                child = TagFactory.create(
                    user_id=user_id,
                    name=f"{parent.name}-child-{i+1}",
                    parent_id=parent.id,
                    color=f"#{i:02x}{current_depth:02x}00",
                )
                tags.append(child)
                create_children(child, current_depth + 1)
        
        create_children(root, 1)
        return tags
    
    @staticmethod
    def create_common_tags(user_id: Optional[UUID] = None) -> List[Tag]:
        """Create a set of common tags."""
        user_id = user_id or uuid4()
        
        tag_specs = [
            ("work", "#0066CC", "💼", "Work-related items"),
            ("personal", "#FF6B6B", "👤", "Personal items"),
            ("urgent", "#FF0000", "🔴", "Urgent priority"),
            ("idea", "#FFD93D", "💡", "Ideas and thoughts"),
            ("todo", "#6BCF7E", "✅", "To-do items"),
            ("reference", "#9B59B6", "📚", "Reference materials"),
            ("project", "#3498DB", "📂", "Project-related"),
            ("meeting", "#E67E22", "🤝", "Meeting notes"),
        ]
        
        tags = []
        for name, color, icon, description in tag_specs:
            tag = TagFactory.create(
                user_id=user_id,
                name=name,
                color=color,
                icon=icon,
                description=description,
            )
            tags.append(tag)
        
        return tags


class TestDataBuilder:
    """Builder for creating complete test scenarios."""
    
    @staticmethod
    def create_user_with_data(
        memory_count: int = 10,
        session_count: int = 3,
        tag_count: int = 5,
    ) -> dict:
        """Create a user with associated data."""
        user = UserFactory.create()
        tags = TagFactory.create_common_tags(user.id.value)[:tag_count]
        
        memories = []
        for i in range(memory_count):
            memory = MemoryFactory.create_with_embedding(
                user_id=user.id.value,
                tags=[tags[i % len(tags)].id.value] if tags else [],
            )
            memories.append(memory)
        
        sessions = []
        for i in range(session_count):
            session = SessionFactory.create_with_messages(
                user_id=user.id.value,
                message_count=3 + i,
                memory_ids=[memories[i].id] if i < len(memories) else [],
            )
            sessions.append(session)
        
        return {
            "user": user,
            "tags": tags,
            "memories": memories,
            "sessions": sessions,
        }
    
    @staticmethod
    def create_test_ecosystem(
        user_count: int = 3,
        memories_per_user: int = 5,
    ) -> dict:
        """Create a complete test ecosystem with multiple users."""
        ecosystem = {
            "users": [],
            "all_memories": [],
            "all_sessions": [],
            "all_tags": [],
        }
        
        for _ in range(user_count):
            data = TestDataBuilder.create_user_with_data(
                memory_count=memories_per_user,
                session_count=2,
                tag_count=3,
            )
            
            ecosystem["users"].append(data["user"])
            ecosystem["all_memories"].extend(data["memories"])
            ecosystem["all_sessions"].extend(data["sessions"])
            ecosystem["all_tags"].extend(data["tags"])
        
        return ecosystem