"""
Test the DashboardService implementation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.services.dashboard_service import DashboardService


class TestDashboardService:
    """Test DashboardService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.dashboard_service = DashboardService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_overview(self):
        """Test dashboard overview data retrieval"""
        # Mock database responses
        self.mock_db.get_memory_count.return_value = 150
        self.mock_db.get_recent_memories.return_value = [
            {"id": "mem-1", "content": "Recent memory 1", "created_at": "2024-01-01T12:00:00Z"},
            {"id": "mem-2", "content": "Recent memory 2", "created_at": "2024-01-01T11:00:00Z"}
        ]
        self.mock_db.get_session_count.return_value = 25
        self.mock_db.get_active_sessions.return_value = [
            {"id": "session-1", "user_id": "user-1", "status": "active"}
        ]
        
        overview = await self.dashboard_service.get_dashboard_overview()
        
        assert overview["total_memories"] == 150
        assert overview["total_sessions"] == 25
        assert overview["active_sessions"] == 1
        assert len(overview["recent_memories"]) == 2
        assert "system_status" in overview
        assert overview["system_status"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_get_memory_analytics(self):
        """Test memory analytics data"""
        # Mock analytics data
        self.mock_db.get_memory_count_by_date.return_value = [
            {"date": "2024-01-01", "count": 10},
            {"date": "2024-01-02", "count": 15},
            {"date": "2024-01-03", "count": 12}
        ]
        self.mock_db.get_memory_count_by_type.return_value = [
            {"type": "semantic", "count": 80},
            {"type": "episodic", "count": 50},
            {"type": "procedural", "count": 20}
        ]
        self.mock_db.get_average_memory_size.return_value = 256.5
        
        analytics = await self.dashboard_service.get_memory_analytics(days=7)
        
        assert analytics["total_memories"] == 150  # From previous setup
        assert analytics["memory_growth"] == [
            {"date": "2024-01-01", "count": 10},
            {"date": "2024-01-02", "count": 15},
            {"date": "2024-01-03", "count": 12}
        ]
        assert analytics["memory_types"] == [
            {"type": "semantic", "count": 80},
            {"type": "episodic", "count": 50},
            {"type": "procedural", "count": 20}
        ]
        assert analytics["average_size_bytes"] == 256.5
    
    @pytest.mark.asyncio
    async def test_get_search_analytics(self):
        """Test search analytics data"""
        self.mock_db.get_search_stats.return_value = {
            "total_searches": 450,
            "unique_queries": 320,
            "average_results": 8.5,
            "top_queries": [
                {"query": "python", "count": 25},
                {"query": "async", "count": 18},
                {"query": "testing", "count": 15}
            ]
        }
        
        search_analytics = await self.dashboard_service.get_search_analytics(days=30)
        
        assert search_analytics["total_searches"] == 450
        assert search_analytics["unique_queries"] == 320
        assert search_analytics["average_results"] == 8.5
        assert len(search_analytics["top_queries"]) == 3
        assert search_analytics["top_queries"][0]["query"] == "python"
    
    @pytest.mark.asyncio
    async def test_get_user_activity(self):
        """Test user activity analytics"""
        self.mock_db.get_user_activity_stats.return_value = {
            "active_users_today": 15,
            "active_users_week": 45,
            "active_users_month": 120,
            "activity_by_hour": [
                {"hour": 9, "activity_count": 25},
                {"hour": 10, "activity_count": 32},
                {"hour": 11, "activity_count": 28}
            ],
            "top_users": [
                {"user_id": "user-1", "activity_count": 85},
                {"user_id": "user-2", "activity_count": 72}
            ]
        }
        
        user_activity = await self.dashboard_service.get_user_activity(days=7)
        
        assert user_activity["active_users_today"] == 15
        assert user_activity["active_users_week"] == 45
        assert user_activity["active_users_month"] == 120
        assert len(user_activity["activity_by_hour"]) == 3
        assert len(user_activity["top_users"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_system_performance(self):
        """Test system performance metrics"""
        performance = await self.dashboard_service.get_system_performance()
        
        assert "cpu_usage" in performance
        assert "memory_usage" in performance
        assert "disk_usage" in performance
        assert "response_times" in performance
        assert "database_stats" in performance
        
        # Check that percentages are valid
        assert 0 <= performance["cpu_usage"]["percent"] <= 100
        assert 0 <= performance["memory_usage"]["percent"] <= 100
        assert 0 <= performance["disk_usage"]["percent"] <= 100
    
    @pytest.mark.asyncio
    async def test_get_recent_activities(self):
        """Test recent activities retrieval"""
        mock_activities = [
            {
                "id": "activity-1",
                "type": "memory_created",
                "user_id": "user-1",
                "timestamp": "2024-01-01T12:00:00Z",
                "details": {"memory_id": "mem-123"}
            },
            {
                "id": "activity-2",
                "type": "search_performed",
                "user_id": "user-2",
                "timestamp": "2024-01-01T11:30:00Z",
                "details": {"query": "python functions"}
            }
        ]
        self.mock_db.get_recent_activities.return_value = mock_activities
        
        activities = await self.dashboard_service.get_recent_activities(limit=10)
        
        assert activities == mock_activities
        self.mock_db.get_recent_activities.assert_called_once_with(limit=10)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_alerts(self):
        """Test dashboard alerts generation"""
        # Mock data that would trigger alerts
        self.mock_db.get_memory_count.return_value = 9500  # Near limit
        self.mock_db.get_failed_operations_count.return_value = 15
        self.mock_db.get_database_size.return_value = 950 * 1024 * 1024  # Near 1GB
        
        alerts = await self.dashboard_service.get_dashboard_alerts()
        
        # Should have alerts for high memory count and failed operations
        assert len(alerts) >= 2
        
        alert_types = [alert["type"] for alert in alerts]
        assert "high_memory_count" in alert_types
        assert "failed_operations" in alert_types
        
        # Check alert structure
        for alert in alerts:
            assert "type" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert
    
    @pytest.mark.asyncio
    async def test_get_dashboard_overview_with_timeframe(self):
        """Test dashboard overview with specific timeframe"""
        self.mock_db.get_memory_count.return_value = 150
        self.mock_db.get_recent_memories.return_value = []
        self.mock_db.get_session_count.return_value = 25
        self.mock_db.get_active_sessions.return_value = []
        
        # Test with different timeframes
        timeframes = ["24h", "7d", "30d"]
        
        for timeframe in timeframes:
            overview = await self.dashboard_service.get_dashboard_overview(timeframe=timeframe)
            
            assert "total_memories" in overview
            assert "timeframe" in overview
            assert overview["timeframe"] == timeframe


class TestDashboardServiceErrorHandling:
    """Test error handling in DashboardService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.dashboard_service = DashboardService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_overview_database_error(self):
        """Test dashboard overview when database fails"""
        self.mock_db.get_memory_count.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await self.dashboard_service.get_dashboard_overview()
    
    @pytest.mark.asyncio
    async def test_get_memory_analytics_partial_failure(self):
        """Test memory analytics with partial database failures"""
        # Some calls succeed, others fail
        self.mock_db.get_memory_count.return_value = 100
        self.mock_db.get_memory_count_by_date.side_effect = Exception("Query failed")
        self.mock_db.get_memory_count_by_type.return_value = []
        self.mock_db.get_average_memory_size.return_value = 250.0
        
        with pytest.raises(Exception, match="Query failed"):
            await self.dashboard_service.get_memory_analytics()
    
    @pytest.mark.asyncio
    async def test_get_system_performance_graceful_degradation(self):
        """Test system performance with graceful degradation"""
        # Should handle system call failures gracefully
        performance = await self.dashboard_service.get_system_performance()
        
        # Should still return basic structure even if some metrics fail
        assert isinstance(performance, dict)
        assert "cpu_usage" in performance
        assert "memory_usage" in performance


class TestDashboardServiceIntegration:
    """Integration tests for DashboardService"""
    
    @pytest.mark.asyncio
    async def test_complete_dashboard_data_flow(self):
        """Test complete dashboard data retrieval flow"""
        mock_db = AsyncMock()
        dashboard_service = DashboardService(mock_db)
        
        # Mock all required database calls
        mock_db.get_memory_count.return_value = 200
        mock_db.get_recent_memories.return_value = []
        mock_db.get_session_count.return_value = 30
        mock_db.get_active_sessions.return_value = []
        mock_db.get_memory_count_by_date.return_value = []
        mock_db.get_memory_count_by_type.return_value = []
        mock_db.get_average_memory_size.return_value = 300.0
        mock_db.get_search_stats.return_value = {
            "total_searches": 100,
            "unique_queries": 80,
            "average_results": 5.0,
            "top_queries": []
        }
        mock_db.get_user_activity_stats.return_value = {
            "active_users_today": 10,
            "active_users_week": 25,
            "active_users_month": 50,
            "activity_by_hour": [],
            "top_users": []
        }
        mock_db.get_recent_activities.return_value = []
        mock_db.get_failed_operations_count.return_value = 2
        mock_db.get_database_size.return_value = 100 * 1024 * 1024
        
        # Get all dashboard data
        overview = await dashboard_service.get_dashboard_overview()
        analytics = await dashboard_service.get_memory_analytics()
        search_analytics = await dashboard_service.get_search_analytics()
        user_activity = await dashboard_service.get_user_activity()
        performance = await dashboard_service.get_system_performance()
        activities = await dashboard_service.get_recent_activities()
        alerts = await dashboard_service.get_dashboard_alerts()
        
        # Verify all data is retrieved successfully
        assert overview["total_memories"] == 200
        assert analytics["total_memories"] == 200
        assert search_analytics["total_searches"] == 100
        assert user_activity["active_users_today"] == 10
        assert isinstance(performance, dict)
        assert isinstance(activities, list)
        assert isinstance(alerts, list)
    
    @pytest.mark.asyncio
    async def test_dashboard_real_time_updates(self):
        """Test dashboard data reflects real-time changes"""
        mock_db = AsyncMock()
        dashboard_service = DashboardService(mock_db)
        
        # Initial state
        mock_db.get_memory_count.return_value = 100
        overview1 = await dashboard_service.get_dashboard_overview()
        assert overview1["total_memories"] == 100
        
        # Simulate memory addition
        mock_db.get_memory_count.return_value = 101
        overview2 = await dashboard_service.get_dashboard_overview()
        assert overview2["total_memories"] == 101
        
        # Verify the change is reflected
        assert overview2["total_memories"] > overview1["total_memories"]