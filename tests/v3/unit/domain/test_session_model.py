"""
Unit tests for Session domain model.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.domain.models.session import (
    Session,
    SessionId,
    Message,
    MessageRole,
    SessionContext,
    SessionFactory,
)
from src.domain.models.memory import MemoryId


class TestSessionId:
    """Tests for SessionId value object."""
    
    def test_create_session_id(self):
        """Test creating a SessionId."""
        id_value = uuid4()
        session_id = SessionId(id_value)
        assert session_id.value == id_value
    
    def test_session_id_equality(self):
        """Test SessionId equality."""
        id_value = uuid4()
        session_id1 = SessionId(id_value)
        session_id2 = SessionId(id_value)
        session_id3 = SessionId(uuid4())
        
        assert session_id1 == session_id2
        assert session_id1 != session_id3


class TestMessageRole:
    """Tests for MessageRole enum."""
    
    def test_message_role_values(self):
        """Test all message role values exist."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
    
    def test_message_role_from_string(self):
        """Test creating MessageRole from string."""
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT
        assert MessageRole("system") == MessageRole.SYSTEM


class TestMessage:
    """Tests for Message value object."""
    
    def test_create_message(self):
        """Test creating a message."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello, world!",
        )
        
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, world!"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}
    
    def test_message_with_metadata(self):
        """Test creating a message with metadata."""
        metadata = {"source": "api", "version": "1.0"}
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Hello! How can I help?",
            metadata=metadata,
        )
        
        assert msg.metadata == metadata
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(
            role=MessageRole.USER,
            content="Test message",
            metadata={"key": "value"},
        )
        
        msg_dict = msg.to_dict()
        assert msg_dict["role"] == "user"
        assert msg_dict["content"] == "Test message"
        assert msg_dict["metadata"] == {"key": "value"}
        assert "timestamp" in msg_dict
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "role": "assistant",
            "content": "Response message",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"model": "gpt-4"},
        }
        
        msg = Message.from_dict(data)
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Response message"
        assert msg.metadata["model"] == "gpt-4"


class TestSessionContext:
    """Tests for SessionContext value object."""
    
    def test_create_default_context(self):
        """Test creating default session context."""
        ctx = SessionContext()
        
        assert ctx.temperature == 0.7
        assert ctx.max_tokens == 2048
        assert ctx.model == "gpt-4"
        assert ctx.system_prompt is None
        assert ctx.custom_settings == {}
    
    def test_create_custom_context(self):
        """Test creating custom session context."""
        ctx = SessionContext(
            temperature=0.9,
            max_tokens=4096,
            model="gpt-4-turbo",
            system_prompt="You are a helpful assistant.",
            custom_settings={"style": "formal"},
        )
        
        assert ctx.temperature == 0.9
        assert ctx.max_tokens == 4096
        assert ctx.model == "gpt-4-turbo"
        assert ctx.system_prompt == "You are a helpful assistant."
        assert ctx.custom_settings["style"] == "formal"
    
    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        ctx = SessionContext(
            temperature=0.5,
            system_prompt="Test prompt",
        )
        
        ctx_dict = ctx.to_dict()
        assert ctx_dict["temperature"] == 0.5
        assert ctx_dict["system_prompt"] == "Test prompt"
        assert "model" in ctx_dict
    
    def test_context_from_dict(self):
        """Test creating context from dictionary."""
        data = {
            "temperature": 0.8,
            "max_tokens": 1024,
            "model": "claude-2",
            "system_prompt": "Be concise.",
        }
        
        ctx = SessionContext.from_dict(data)
        assert ctx.temperature == 0.8
        assert ctx.max_tokens == 1024
        assert ctx.model == "claude-2"
        assert ctx.system_prompt == "Be concise."


class TestSession:
    """Tests for Session aggregate."""
    
    def test_create_session(self):
        """Test creating a session."""
        session_id = SessionId(uuid4())
        user_id = uuid4()
        
        session = Session(
            id=session_id,
            user_id=user_id,
            title="Test Session",
        )
        
        assert session.id == session_id
        assert session.user_id == user_id
        assert session.title == "Test Session"
        assert session.description is None
        assert session.is_active is True
        assert len(session.messages) == 0
        assert isinstance(session.context, SessionContext)
    
    def test_session_with_description(self):
        """Test creating session with description."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
            description="This is a test session for unit testing.",
        )
        
        assert session.description == "This is a test session for unit testing."
    
    def test_session_timestamps(self):
        """Test session timestamps."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert isinstance(session.last_activity_at, datetime)
        assert session.created_at == session.updated_at == session.last_activity_at
    
    def test_add_message(self):
        """Test adding messages to session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        # Add user message
        user_msg = session.add_message(
            role=MessageRole.USER,
            content="Hello!",
        )
        
        assert len(session.messages) == 1
        assert session.messages[0] == user_msg
        assert session.messages[0].role == MessageRole.USER
        assert session.messages[0].content == "Hello!"
        
        # Add assistant message
        assistant_msg = session.add_message(
            role=MessageRole.ASSISTANT,
            content="Hi there!",
            metadata={"model": "gpt-4"},
        )
        
        assert len(session.messages) == 2
        assert session.messages[1] == assistant_msg
        assert session.messages[1].metadata["model"] == "gpt-4"
    
    def test_update_context(self):
        """Test updating session context."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        new_context = SessionContext(
            temperature=0.9,
            model="claude-2",
            system_prompt="Be creative.",
        )
        
        session.update_context(new_context)
        
        assert session.context.temperature == 0.9
        assert session.context.model == "claude-2"
        assert session.context.system_prompt == "Be creative."
    
    def test_add_memory(self):
        """Test adding memories to session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        memory_id1 = MemoryId(uuid4())
        memory_id2 = MemoryId(uuid4())
        
        session.add_memory(memory_id1)
        assert memory_id1 in session.memory_ids
        
        session.add_memory(memory_id2)
        assert len(session.memory_ids) == 2
        
        # Test duplicate memory
        session.add_memory(memory_id1)
        assert len(session.memory_ids) == 2  # Should not add duplicate
    
    def test_remove_memory(self):
        """Test removing memories from session."""
        memory_id = MemoryId(uuid4())
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
            memory_ids=[memory_id],
        )
        
        assert memory_id in session.memory_ids
        
        session.remove_memory(memory_id)
        assert memory_id not in session.memory_ids
    
    def test_add_tag(self):
        """Test adding tags to session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        session.add_tag("python")
        assert "python" in session.tags
        
        session.add_tag("testing")
        assert len(session.tags) == 2
        
        # Test duplicate tag
        session.add_tag("python")
        assert len(session.tags) == 2  # Should not add duplicate
    
    def test_remove_tag(self):
        """Test removing tags from session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
            tags=["python", "testing"],
        )
        
        session.remove_tag("python")
        assert "python" not in session.tags
        assert "testing" in session.tags
    
    def test_close_session(self):
        """Test closing a session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        assert session.is_active is True
        
        session.close()
        assert session.is_active is False
    
    def test_reopen_session(self):
        """Test reopening a closed session."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        session.close()
        assert session.is_active is False
        
        session.reopen()
        assert session.is_active is True
    
    def test_get_message_count(self):
        """Test getting message count by role."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        session.add_message(MessageRole.USER, "Message 1")
        session.add_message(MessageRole.ASSISTANT, "Response 1")
        session.add_message(MessageRole.USER, "Message 2")
        session.add_message(MessageRole.ASSISTANT, "Response 2")
        session.add_message(MessageRole.SYSTEM, "System message")
        
        assert session.get_message_count(MessageRole.USER) == 2
        assert session.get_message_count(MessageRole.ASSISTANT) == 2
        assert session.get_message_count(MessageRole.SYSTEM) == 1
    
    def test_get_last_message(self):
        """Test getting the last message."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        assert session.get_last_message() is None
        
        msg1 = session.add_message(MessageRole.USER, "First")
        msg2 = session.add_message(MessageRole.ASSISTANT, "Second")
        msg3 = session.add_message(MessageRole.USER, "Third")
        
        assert session.get_last_message() == msg3
        assert session.get_last_message(MessageRole.ASSISTANT) == msg2
        assert session.get_last_message(MessageRole.USER) == msg3
    
    def test_clear_messages(self):
        """Test clearing all messages."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        session.add_message(MessageRole.USER, "Message 1")
        session.add_message(MessageRole.ASSISTANT, "Response 1")
        assert len(session.messages) == 2
        
        session.clear_messages()
        assert len(session.messages) == 0
    
    def test_update_metadata(self):
        """Test updating session metadata."""
        session = Session(
            id=SessionId(uuid4()),
            user_id=uuid4(),
            title="Test Session",
        )
        
        session.update_metadata({"key1": "value1"})
        assert session.metadata["key1"] == "value1"
        
        session.update_metadata({"key2": "value2", "key1": "updated"})
        assert session.metadata["key1"] == "updated"
        assert session.metadata["key2"] == "value2"


class TestSessionFactory:
    """Tests for SessionFactory."""
    
    def test_create_chat_session(self):
        """Test creating a chat session."""
        user_id = uuid4()
        session = SessionFactory.create_chat_session(
            user_id=user_id,
            title="Chat Session",
            system_prompt="You are a helpful assistant.",
        )
        
        assert session.title == "Chat Session"
        assert session.context.system_prompt == "You are a helpful assistant."
        assert len(session.messages) == 0
    
    def test_create_research_session(self):
        """Test creating a research session."""
        user_id = uuid4()
        memory_ids = [MemoryId(uuid4()), MemoryId(uuid4())]
        
        session = SessionFactory.create_research_session(
            user_id=user_id,
            title="Research Session",
            description="Researching Python best practices",
            related_memories=memory_ids,
        )
        
        assert session.title == "Research Session"
        assert session.description == "Researching Python best practices"
        assert len(session.memory_ids) == 2
        assert all(mid in session.memory_ids for mid in memory_ids)
    
    def test_create_brainstorming_session(self):
        """Test creating a brainstorming session."""
        user_id = uuid4()
        session = SessionFactory.create_brainstorming_session(
            user_id=user_id,
            title="Brainstorming Session",
            tags=["ideas", "creativity"],
        )
        
        assert session.title == "Brainstorming Session"
        assert "ideas" in session.tags
        assert "creativity" in session.tags
        assert session.context.temperature == 0.9  # Higher for creativity