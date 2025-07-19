"""
Test suite for dashboard migrations module - working version.
Tests the migration dashboard integration and monitoring functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.dashboard_migrations import MigrationDashboard, get_migration_dashboard


class TestMigrationDashboardWorking:
    """Test MigrationDashboard class - working tests only."""

    def setup_method(self):
        """Setup test environment."""
        # Clear global instance
        import app.dashboard_migrations
        app.dashboard_migrations._migration_dashboard = None
        
        self.dashboard = MigrationDashboard()
        self.mock_engine = AsyncMock()
        self.mock_db = AsyncMock()
        self.mock_db.pool = AsyncMock()

    def test_dashboard_initialization(self):
        """Test dashboard initializes correctly."""
        assert self.dashboard.migration_engine is None
        assert self.dashboard._last_refresh is None
        assert self.dashboard._cache_duration == timedelta(minutes=5)
        assert self.dashboard._cached_data == {}

    @pytest.mark.asyncio
    @patch('app.dashboard_migrations.get_database')
    @patch('app.dashboard_migrations.MigrationEngine')
    async def test_initialize_success(self, mock_engine_class, mock_get_database):
        """Test successful dashboard initialization."""
        # Mock database and engine
        mock_get_database.return_value = self.mock_db
        mock_engine_class.return_value = self.mock_engine
        
        await self.dashboard.initialize()
        
        mock_get_database.assert_called_once()
        mock_engine_class.assert_called_once_with(self.mock_db.pool)
        self.mock_engine.initialize.assert_called_once()
        assert self.dashboard.migration_engine == self.mock_engine

    @pytest.mark.asyncio
    @patch('app.dashboard_migrations.get_database')
    async def test_initialize_database_failure(self, mock_get_database):
        """Test initialization with database failure."""
        mock_get_database.return_value.pool = None
        
        await self.dashboard.initialize()
        
        assert self.dashboard.migration_engine is None

    @pytest.mark.asyncio
    async def test_get_migration_summary_no_engine(self):
        """Test get_migration_summary without engine."""
        result = await self.dashboard.get_migration_summary()
        
        expected = {
            "status": "unavailable",
            "message": "Migration engine not available",
            "pending_count": 0,
            "running_count": 0,
            "recent_failures": 0,
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_migration_summary_cached(self):
        """Test cached migration summary retrieval."""
        self.dashboard.migration_engine = self.mock_engine
        
        # Set up cache
        cached_summary = {"status": "cached", "pending_count": 5}
        self.dashboard._cached_data["summary"] = cached_summary
        self.dashboard._last_refresh = datetime.now()
        
        result = await self.dashboard.get_migration_summary()
        
        # Should return cached data without calling engine
        assert result == cached_summary
        self.mock_engine.get_pending_migrations.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_migration_summary_error(self):
        """Test migration summary with engine error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.get_pending_migrations.side_effect = Exception("Engine error")
        
        result = await self.dashboard.get_migration_summary()
        
        assert result["status"] == "error"
        assert result["message"] == "Engine error"
        assert result["pending_count"] == 0

    @pytest.mark.asyncio
    async def test_get_pending_migrations_no_engine(self):
        """Test get_pending_migrations without engine."""
        result = await self.dashboard.get_pending_migrations()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pending_migrations_error(self):
        """Test get_pending_migrations with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.get_pending_migrations.side_effect = Exception("Pending error")
        
        result = await self.dashboard.get_pending_migrations()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pending_migrations_limit(self):
        """Test pending migrations respects limit."""
        from app.migration_framework import MigrationType
        
        self.dashboard.migration_engine = self.mock_engine
        
        # Mock 15 migrations (should be limited to 10)
        mock_migrations = []
        for i in range(15):
            mock_migration = MagicMock()
            mock_migration.id = f"migration_{i}"
            mock_migration.name = f"Migration {i}"
            mock_migration.migration_type = MigrationType.DATABASE_SCHEMA
            mock_migration.version = "1.0.0"
            mock_migration.dependencies = []
            mock_migration.reversible = True
            mock_migration.estimated_duration = 30
            mock_migration.author = "test_author"
            mock_migration.created_at = datetime(2024, 1, 1)
            mock_migrations.append(mock_migration)
        
        self.mock_engine.get_pending_migrations.return_value = mock_migrations
        
        result = await self.dashboard.get_pending_migrations()
        
        assert len(result) == 10  # Should be limited

    @pytest.mark.asyncio
    async def test_get_running_migrations_no_engine(self):
        """Test get_running_migrations without engine."""
        result = await self.dashboard.get_running_migrations()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_running_migrations_error(self):
        """Test get_running_migrations with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.get_running_migrations.side_effect = Exception("Running error")
        
        result = await self.dashboard.get_running_migrations()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_history_no_engine(self):
        """Test get_recent_history without engine."""
        result = await self.dashboard.get_recent_history()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_history_success(self):
        """Test successful recent history retrieval."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        
        self.mock_engine.history.get_applied_migrations.return_value = [
            "migration_1", "migration_2", "migration_3"
        ]
        self.mock_engine.history.get_migration_status.side_effect = [
            {
                "status": "completed",
                "applied_at": "2024-01-01T12:00:00",
                "execution_time_ms": 1500,
                "affected_items": 100
            },
            {
                "status": "failed",
                "applied_at": "2024-01-02T12:00:00",
                "execution_time_ms": 500,
                "affected_items": 0
            },
            {
                "status": "completed",
                "applied_at": "2024-01-03T12:00:00",
                "execution_time_ms": 2000,
                "affected_items": 200
            }
        ]
        
        result = await self.dashboard.get_recent_history(limit=5)
        
        assert len(result) == 3
        # Should be reversed (most recent first)
        assert result[0]["id"] == "migration_3"
        assert result[0]["status"] == "completed"
        assert result[1]["id"] == "migration_2"
        assert result[1]["status"] == "failed"
        assert result[2]["id"] == "migration_1"

    @pytest.mark.asyncio
    async def test_get_recent_history_error(self):
        """Test get_recent_history with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        self.mock_engine.history.get_applied_migrations.side_effect = Exception("History error")
        
        result = await self.dashboard.get_recent_history()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_migration_statistics_no_engine(self):
        """Test get_migration_statistics without engine."""
        result = await self.dashboard.get_migration_statistics()
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_migration_statistics_success(self):
        """Test successful migration statistics retrieval."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        
        self.mock_engine.history.get_applied_migrations.return_value = [
            "migration_1", "migration_2", "migration_3"
        ]
        self.mock_engine.history.get_migration_status.side_effect = [
            {
                "status": "completed",
                "metadata": {"migration_type": "DATABASE_SCHEMA"},
                "execution_time_ms": 1000
            },
            {
                "status": "failed", 
                "metadata": {"migration_type": "DATABASE_DATA"},
                "execution_time_ms": 500
            },
            {
                "status": "completed",
                "metadata": {"migration_type": "DATABASE_SCHEMA"},
                "execution_time_ms": 2000
            }
        ]
        
        result = await self.dashboard.get_migration_statistics()
        
        assert result["total_migrations"] == 3
        assert result["success_rate"] == 66.7  # 2/3 * 100 rounded to 1 decimal
        assert result["type_distribution"]["DATABASE_SCHEMA"] == 2
        assert result["type_distribution"]["DATABASE_DATA"] == 1
        assert result["average_execution_time_ms"] == 1167  # (1000+500+2000)/3 rounded
        assert result["successful"] == 2
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_get_migration_statistics_cached(self):
        """Test cached migration statistics retrieval."""
        self.dashboard.migration_engine = self.mock_engine
        
        # Set up cache
        cached_stats = {"total_migrations": 10, "success_rate": 95.0}
        self.dashboard._cached_data["stats"] = cached_stats
        self.dashboard._last_refresh = datetime.now()
        
        result = await self.dashboard.get_migration_statistics()
        
        # Should return cached data
        assert result == cached_stats

    @pytest.mark.asyncio
    async def test_get_migration_statistics_error(self):
        """Test get_migration_statistics with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        self.mock_engine.history.get_applied_migrations.side_effect = Exception("Stats error")
        
        result = await self.dashboard.get_migration_statistics()
        assert result == {}

    def test_is_cache_valid_no_cache(self):
        """Test cache validity with no cached data."""
        assert not self.dashboard._is_cache_valid("nonexistent")

    def test_is_cache_valid_no_refresh_time(self):
        """Test cache validity with no refresh time."""
        self.dashboard._cached_data["test"] = {"data": "value"}
        assert not self.dashboard._is_cache_valid("test")

    def test_is_cache_valid_expired(self):
        """Test cache validity with expired cache."""
        self.dashboard._cached_data["test"] = {"data": "value"}
        self.dashboard._last_refresh = datetime.now() - timedelta(minutes=10)
        
        assert not self.dashboard._is_cache_valid("test")

    def test_is_cache_valid_fresh(self):
        """Test cache validity with fresh cache."""
        self.dashboard._cached_data["test"] = {"data": "value"}
        self.dashboard._last_refresh = datetime.now() - timedelta(minutes=2)
        
        assert self.dashboard._is_cache_valid("test")

    @pytest.mark.asyncio
    async def test_get_recent_failures_no_engine(self):
        """Test get_recent_failures without engine."""
        result = await self.dashboard._get_recent_failures()
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_recent_failures_datetime_objects(self):
        """Test recent failures counting with datetime objects."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        
        # Mock migrations with recent and old failures
        recent_time = datetime.now() - timedelta(hours=2)
        old_time = datetime.now() - timedelta(days=2)
        
        self.mock_engine.history.get_applied_migrations.return_value = ["m1", "m2", "m3"]
        self.mock_engine.history.get_migration_status.side_effect = [
            {"status": "failed", "applied_at": recent_time},  # Should count
            {"status": "failed", "applied_at": old_time},     # Should not count
            {"status": "completed", "applied_at": recent_time} # Should not count
        ]
        
        result = await self.dashboard._get_recent_failures()
        
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_recent_failures_string_timestamps(self):
        """Test recent failures counting with string timestamps."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        
        # Mock migrations with string timestamps
        recent_time = (datetime.now() - timedelta(hours=2)).isoformat()
        old_time = (datetime.now() - timedelta(days=2)).isoformat()
        
        self.mock_engine.history.get_applied_migrations.return_value = ["m1", "m2"]
        self.mock_engine.history.get_migration_status.side_effect = [
            {"status": "failed", "applied_at": recent_time},
            {"status": "failed", "applied_at": old_time}
        ]
        
        result = await self.dashboard._get_recent_failures()
        
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_recent_failures_error(self):
        """Test get_recent_failures with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.history = AsyncMock()
        self.mock_engine.history.get_applied_migrations.side_effect = Exception("Failures error")
        
        result = await self.dashboard._get_recent_failures()
        assert result == 0

    @pytest.mark.asyncio
    async def test_execute_migration_from_dashboard_no_engine(self):
        """Test migration execution without engine."""
        result = await self.dashboard.execute_migration_from_dashboard("test_migration")
        
        assert result["success"] is False
        assert result["error"] == "Migration engine not available"

    @pytest.mark.asyncio
    async def test_execute_migration_from_dashboard_error(self):
        """Test migration execution with error."""
        self.dashboard.migration_engine = self.mock_engine
        self.mock_engine.execute_migration.side_effect = Exception("Execution failed")
        
        result = await self.dashboard.execute_migration_from_dashboard("test_migration")
        
        assert result["success"] is False
        assert result["error"] == "Execution failed"

    def test_cache_duration_property(self):
        """Test cache duration is properly set."""
        assert self.dashboard._cache_duration == timedelta(minutes=5)

    def test_cached_data_initialization(self):
        """Test cached data initializes as empty dict."""
        dashboard = MigrationDashboard()
        assert dashboard._cached_data == {}
        assert isinstance(dashboard._cached_data, dict)


class TestGlobalFunctions:
    """Test global functions."""

    def setup_method(self):
        """Reset global state."""
        import app.dashboard_migrations
        app.dashboard_migrations._migration_dashboard = None

    def test_get_migration_dashboard_creates_instance(self):
        """Test that get_migration_dashboard creates new instance."""
        dashboard = get_migration_dashboard()
        
        assert isinstance(dashboard, MigrationDashboard)
        
        # Should return same instance on subsequent calls
        dashboard2 = get_migration_dashboard()
        assert dashboard is dashboard2

    def test_get_migration_dashboard_singleton(self):
        """Test singleton behavior of migration dashboard."""
        dashboard1 = get_migration_dashboard()
        dashboard2 = get_migration_dashboard()
        
        assert dashboard1 is dashboard2

    def test_global_instance_initialization(self):
        """Test global instance starts as None."""
        import app.dashboard_migrations
        app.dashboard_migrations._migration_dashboard = None
        
        # Should be None initially
        assert app.dashboard_migrations._migration_dashboard is None
        
        # Should create instance
        dashboard = get_migration_dashboard()
        assert app.dashboard_migrations._migration_dashboard is dashboard
