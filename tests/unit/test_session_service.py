"""
Test the SessionService implementation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.session_service import SessionService


class TestSessionService:
    """Test SessionService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.session_service = SessionService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Test successful session creation"""
        self.mock_db.create_session.return_value = "session-123"
        
        session_id = await self.session_service.create_session(
            user_id="user-456",
            session_type="chat",
            metadata={"client": "web"}
        )
        
        assert session_id == "session-123"
        self.mock_db.create_session.assert_called_once()
        
        # Verify the call was made with proper structure
        call_args = self.mock_db.create_session.call_args[1]
        assert call_args["user_id"] == "user-456"
        assert call_args["session_type"] == "chat"
        assert call_args["metadata"]["client"] == "web"
    
    @pytest.mark.asyncio
    async def test_create_session_with_default_values(self):
        """Test session creation with default values"""
        self.mock_db.create_session.return_value = "session-default"
        
        session_id = await self.session_service.create_session("user-123")
        
        assert session_id == "session-default"
        
        # Verify defaults were applied
        call_args = self.mock_db.create_session.call_args[1]
        assert call_args["session_type"] == "interactive"
        assert call_args["metadata"] == {}
    
    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Test successful session retrieval"""
        mock_session = {
            "id": "session-123",
            "user_id": "user-456",
            "session_type": "chat",
            "status": "active",
            "created_at": "2024-01-01T12:00:00Z",
            "metadata": {"client": "web"}
        }
        self.mock_db.get_session.return_value = mock_session
        
        session = await self.session_service.get_session("session-123")
        
        assert session == mock_session
        self.mock_db.get_session.assert_called_once_with("session-123")
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test session retrieval when session doesn't exist"""
        self.mock_db.get_session.return_value = None
        
        session = await self.session_service.get_session("nonexistent")
        
        assert session is None
    
    @pytest.mark.asyncio
    async def test_get_session_status_active(self):
        """Test getting session status for active session"""
        mock_session = {
            "id": "session-123",
            "status": "active",
            "created_at": "2024-01-01T12:00:00Z",
            "last_activity": "2024-01-01T12:30:00Z"
        }
        self.mock_db.get_session.return_value = mock_session
        
        status = await self.session_service.get_session_status("session-123")
        
        assert status["status"] == "active"
        assert status["is_active"] is True
        assert "uptime" in status
        assert "last_activity" in status
    
    @pytest.mark.asyncio
    async def test_get_session_status_paused(self):
        """Test getting session status for paused session"""
        mock_session = {
            "id": "session-123",
            "status": "paused",
            "created_at": "2024-01-01T12:00:00Z",
            "last_activity": "2024-01-01T12:30:00Z"
        }
        self.mock_db.get_session.return_value = mock_session
        
        status = await self.session_service.get_session_status("session-123")
        
        assert status["status"] == "paused"
        assert status["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_get_session_status_not_found(self):
        """Test getting status for nonexistent session"""
        self.mock_db.get_session.return_value = None
        
        status = await self.session_service.get_session_status("nonexistent")
        
        assert status["status"] == "not_found"
        assert status["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_pause_session_success(self):
        """Test successful session pausing"""
        self.mock_db.update_session.return_value = True
        
        result = await self.session_service.pause_session("session-123")
        
        assert result is True
        self.mock_db.update_session.assert_called_once_with(
            "session-123",
            status="paused"
        )
    
    @pytest.mark.asyncio
    async def test_pause_session_not_found(self):
        """Test pausing nonexistent session"""
        self.mock_db.update_session.return_value = False
        
        result = await self.session_service.pause_session("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resume_session_success(self):
        """Test successful session resuming"""
        self.mock_db.update_session.return_value = True
        
        result = await self.session_service.resume_session("session-123")
        
        assert result is True
        self.mock_db.update_session.assert_called_once_with(
            "session-123",
            status="active"
        )
    
    @pytest.mark.asyncio
    async def test_end_session_success(self):
        """Test successful session ending"""
        self.mock_db.update_session.return_value = True
        
        result = await self.session_service.end_session("session-123")
        
        assert result is True
        self.mock_db.update_session.assert_called_once_with(
            "session-123",
            status="ended"
        )
    
    @pytest.mark.asyncio
    @patch('app.core.dependencies.get_memory_service')
    async def test_ingest_idea_success(self, mock_get_memory_service):
        """Test successful idea ingestion (woodchipper functionality)"""
        # Mock the memory service
        mock_memory_service = AsyncMock()
        mock_memory_service.create_memory.return_value = "memory-789"
        mock_get_memory_service.return_value = mock_memory_service
        
        # Mock session exists
        self.mock_db.get_session.return_value = {"id": "session-123", "status": "active"}
        self.mock_db.add_session_activity.return_value = True
        
        result = await self.session_service.ingest_idea(
            "session-123",
            "This is a great idea for the project",
            source="mobile",
            priority="high",
            context="Morning brainstorm"
        )
        
        assert result["success"] is True
        assert result["memory_id"] == "memory-789"
        assert result["session_id"] == "session-123"
        
        # Verify memory was created with proper metadata
        mock_memory_service.create_memory.assert_called_once()
        call_args = mock_memory_service.create_memory.call_args
        assert call_args[0][0] == "This is a great idea for the project"  # content
        
        metadata = call_args[1]["metadata"]
        assert metadata["memory_type"] == "idea"
        assert metadata["source"] == "mobile"
        assert metadata["priority"] == "high"
        assert metadata["context"] == "Morning brainstorm"
        assert metadata["session_id"] == "session-123"
    
    @pytest.mark.asyncio
    async def test_ingest_idea_empty_content(self):
        """Test idea ingestion with empty content"""
        result = await self.session_service.ingest_idea(
            "session-123",
            "",
            source="web"
        )
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_ingest_idea_session_not_found(self):
        """Test idea ingestion for nonexistent session"""
        self.mock_db.get_session.return_value = None
        
        result = await self.session_service.ingest_idea(
            "nonexistent",
            "Some idea",
            source="web"
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_ingest_idea_session_not_active(self):
        """Test idea ingestion for inactive session"""
        self.mock_db.get_session.return_value = {
            "id": "session-123",
            "status": "ended"
        }
        
        result = await self.session_service.ingest_idea(
            "session-123",
            "Some idea",
            source="web"
        )
        
        assert result["success"] is False
        assert "not active" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_session_activities(self):
        """Test retrieving session activities"""
        mock_activities = [
            {
                "id": "activity-1",
                "session_id": "session-123",
                "type": "idea_ingested",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {"memory_id": "memory-789"}
            },
            {
                "id": "activity-2",
                "session_id": "session-123",
                "type": "session_paused",
                "timestamp": "2024-01-01T12:30:00Z",
                "data": {}
            }
        ]
        self.mock_db.get_session_activities.return_value = mock_activities
        
        activities = await self.session_service.get_session_activities("session-123")
        
        assert activities == mock_activities
        self.mock_db.get_session_activities.assert_called_once_with("session-123", limit=100)
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self):
        """Test retrieving user sessions"""
        mock_sessions = [
            {"id": "session-1", "user_id": "user-123", "status": "active"},
            {"id": "session-2", "user_id": "user-123", "status": "ended"}
        ]
        self.mock_db.get_user_sessions.return_value = mock_sessions
        
        sessions = await self.session_service.get_user_sessions("user-123")
        
        assert sessions == mock_sessions
        self.mock_db.get_user_sessions.assert_called_once_with("user-123", limit=50)


class TestSessionServiceErrorHandling:
    """Test error handling in SessionService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.session_service = SessionService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_create_session_database_error(self):
        """Test session creation when database fails"""
        self.mock_db.create_session.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await self.session_service.create_session("user-123")
    
    @pytest.mark.asyncio
    async def test_get_session_status_database_error(self):
        """Test get session status when database fails"""
        self.mock_db.get_session.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            await self.session_service.get_session_status("session-123")
    
    @pytest.mark.asyncio
    @patch('app.core.dependencies.get_memory_service')
    async def test_ingest_idea_memory_service_error(self, mock_get_memory_service):
        """Test idea ingestion when memory service fails"""
        # Mock memory service failure
        mock_memory_service = AsyncMock()
        mock_memory_service.create_memory.side_effect = Exception("Memory creation failed")
        mock_get_memory_service.return_value = mock_memory_service
        
        # Mock session exists and is active
        self.mock_db.get_session.return_value = {"id": "session-123", "status": "active"}
        
        result = await self.session_service.ingest_idea(
            "session-123",
            "Test idea",
            source="web"
        )
        
        assert result["success"] is False
        assert "Memory creation failed" in result["error"]


class TestSessionServiceIntegration:
    """Integration tests for SessionService"""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        mock_db = AsyncMock()
        session_service = SessionService(mock_db)
        
        # Create session
        mock_db.create_session.return_value = "session-123"
        session_id = await session_service.create_session("user-456")
        assert session_id == "session-123"
        
        # Get session
        mock_session = {
            "id": "session-123",
            "user_id": "user-456",
            "status": "active"
        }
        mock_db.get_session.return_value = mock_session
        session = await session_service.get_session("session-123")
        assert session == mock_session
        
        # Pause session
        mock_db.update_session.return_value = True
        paused = await session_service.pause_session("session-123")
        assert paused is True
        
        # Resume session
        resumed = await session_service.resume_session("session-123")
        assert resumed is True
        
        # End session
        ended = await session_service.end_session("session-123")
        assert ended is True
    
    @pytest.mark.asyncio
    @patch('app.core.dependencies.get_memory_service')
    async def test_idea_ingestion_workflow(self, mock_get_memory_service):
        """Test idea ingestion workflow"""
        mock_db = AsyncMock()
        session_service = SessionService(mock_db)
        
        # Mock memory service
        mock_memory_service = AsyncMock()
        mock_memory_service.create_memory.return_value = "memory-123"
        mock_get_memory_service.return_value = mock_memory_service
        
        # Mock active session
        mock_db.get_session.return_value = {"id": "session-456", "status": "active"}
        mock_db.add_session_activity.return_value = True
        
        # Ingest multiple ideas
        ideas = [
            "Implement dark mode toggle",
            "Add keyboard shortcuts",
            "Improve search functionality"
        ]
        
        results = []
        for i, idea in enumerate(ideas):
            mock_memory_service.create_memory.return_value = f"memory-{i+1}"
            result = await session_service.ingest_idea(
                "session-456",
                idea,
                source="brainstorm",
                priority="medium"
            )
            results.append(result)
        
        # Verify all ideas were processed
        assert all(result["success"] for result in results)
        assert len(results) == 3
        assert mock_memory_service.create_memory.call_count == 3