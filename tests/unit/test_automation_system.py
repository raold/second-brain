"""
Comprehensive tests for the automation system including:
- Task scheduler functionality
- Background workers
- Triggers and event handling
- API endpoints
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import json

from app.scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskStatus,
    TaskPriority,
    ThresholdTrigger,
    TimeTrigger,
    EventTrigger,
    PerformanceTrigger
)
from app.scheduler.background_workers import (
    ConsolidationWorker,
    CleanupWorker,
    ImportanceUpdateWorker,
    MemoryAgingWorker
)
from app.services.automation_service import AutomationService


class TestTaskScheduler:
    """Test the core task scheduler functionality"""
    
    @pytest.fixture
    def scheduler(self, tmp_path):
        """Create a scheduler instance for testing"""
        task_store = tmp_path / "test_tasks.json"
        return TaskScheduler(max_concurrent_tasks=2, task_store_path=task_store)
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample scheduled task"""
        async def test_function(db, **kwargs):
            return {"status": "completed", "test": True}
        
        return ScheduledTask(
            id="test_task",
            name="Test Task",
            function=test_function,
            schedule="every 1 hour",
            priority=TaskPriority.MEDIUM,
            timeout=60
        )
    
    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self, scheduler):
        """Test starting and stopping the scheduler"""
        # Start scheduler
        await scheduler.start()
        assert scheduler._running is True
        assert len(scheduler._workers) == 2  # max_concurrent_tasks
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler._running is False
    
    @pytest.mark.asyncio
    async def test_task_registration(self, scheduler, sample_task):
        """Test registering and unregistering tasks"""
        # Register task
        scheduler.register_task(sample_task)
        assert sample_task.id in scheduler.tasks
        assert scheduler.tasks[sample_task.id].name == "Test Task"
        
        # Unregister task
        scheduler.unregister_task(sample_task.id)
        assert sample_task.id not in scheduler.tasks
    
    @pytest.mark.asyncio
    async def test_task_enable_disable(self, scheduler, sample_task):
        """Test enabling and disabling tasks"""
        scheduler.register_task(sample_task)
        
        # Disable task
        scheduler.disable_task(sample_task.id)
        assert not scheduler.tasks[sample_task.id].enabled
        
        # Enable task
        scheduler.enable_task(sample_task.id)
        assert scheduler.tasks[sample_task.id].enabled
    
    def test_calculate_next_run(self, scheduler):
        """Test next run time calculation"""
        now = datetime.now()
        
        # Test interval scheduling
        task = ScheduledTask(
            id="interval_test",
            name="Interval Test",
            function=lambda: None,
            schedule="every 30 minutes"
        )
        next_run = scheduler._calculate_next_run(task)
        assert next_run is not None
        assert next_run > now
        assert (next_run - now).seconds <= 1800  # 30 minutes
        
        # Test daily scheduling
        task.schedule = "daily"
        next_run = scheduler._calculate_next_run(task)
        assert next_run is not None
        assert next_run.hour == 0
        assert next_run.minute == 0
    
    @pytest.mark.asyncio
    async def test_task_execution(self, scheduler):
        """Test task execution with mocked database"""
        executed = False
        
        async def test_function(db, **kwargs):
            nonlocal executed
            executed = True
            return {"status": "completed"}
        
        task = ScheduledTask(
            id="exec_test",
            name="Execution Test",
            function=test_function,
            schedule="once",
            timeout=5
        )
        
        # Mock database
        with patch('app.scheduler.task_scheduler.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            await scheduler._execute_task(task)
            
        assert executed
        assert task.status == TaskStatus.COMPLETED
        assert task.error_count == 0
    
    @pytest.mark.asyncio
    async def test_task_failure_and_retry(self, scheduler):
        """Test task failure handling and retry logic"""
        attempt_count = 0
        
        async def failing_function(db, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise Exception("Test failure")
        
        task = ScheduledTask(
            id="fail_test",
            name="Failure Test",
            function=failing_function,
            schedule="once",
            max_retries=3,
            retry_delay=1
        )
        
        with patch('app.scheduler.task_scheduler.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            # First execution - should fail and schedule retry
            await scheduler._execute_task(task)
            
        assert task.status == TaskStatus.RETRYING
        assert task.error_count == 1
        assert task.next_run is not None
    
    @pytest.mark.asyncio
    async def test_task_persistence(self, scheduler, tmp_path):
        """Test saving and loading task state"""
        # Add a task
        task = ScheduledTask(
            id="persist_test",
            name="Persistence Test",
            function=lambda: None,
            schedule="daily",
            enabled=True,
            last_run=datetime.now(),
            status=TaskStatus.COMPLETED
        )
        scheduler.register_task(task)
        
        # Save tasks
        await scheduler._save_tasks()
        
        # Verify file exists and contains task data
        task_file = tmp_path / "test_tasks.json"
        assert task_file.exists()
        
        with open(task_file) as f:
            data = json.load(f)
            assert "persist_test" in data
            assert data["persist_test"]["name"] == "Persistence Test"
            assert data["persist_test"]["status"] == "completed"


class TestBackgroundWorkers:
    """Test background worker implementations"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection"""
        db = AsyncMock()
        db.fetch = AsyncMock(return_value=[])
        db.fetchval = AsyncMock(return_value=0)
        db.execute = AsyncMock()
        return db
    
    @pytest.mark.asyncio
    async def test_consolidation_worker(self, mock_db):
        """Test memory consolidation worker"""
        worker = ConsolidationWorker(batch_size=10, similarity_threshold=0.9)
        
        # Mock the deduplication orchestrator
        with patch.object(worker.dedup_orchestrator, 'process_deduplication') as mock_dedup:
            mock_dedup.return_value = {
                "total_scanned": 100,
                "duplicates_found": 10,
                "merged_count": 8,
                "errors": []
            }
            
            result = await worker.run_consolidation(mock_db)
            
        assert result["status"] == "completed"
        assert result["memories_merged"] == 8
        assert "execution_time" in result
        mock_dedup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_worker(self, mock_db):
        """Test cleanup worker"""
        worker = CleanupWorker(retention_days=30)
        
        # Mock database responses
        mock_db.fetch.return_value = [{"id": i} for i in range(5)]
        
        result = await worker.run_cleanup(mock_db)
        
        assert result["status"] == "completed"
        assert result["retention_days"] == 30
        assert result["cleaned_items"]["access_logs"] == 5
        assert mock_db.execute.called
    
    @pytest.mark.asyncio
    async def test_importance_update_worker(self, mock_db):
        """Test importance update worker"""
        worker = ImportanceUpdateWorker(batch_size=10)
        
        # Mock memory data
        mock_memories = [
            {
                "id": f"mem_{i}",
                "importance_score": 5.0,
                "created_at": datetime.now() - timedelta(days=i),
                "last_accessed": datetime.now() - timedelta(days=i//2),
                "access_count": i * 10,
                "content_length": 100
            }
            for i in range(5)
        ]
        mock_db.fetch.return_value = mock_memories
        
        # Mock importance engine
        with patch.object(worker.importance_engine, 'calculate_importance') as mock_calc:
            mock_calc.return_value = 7.0  # New importance score
            
            result = await worker.run_importance_update(mock_db)
            
        assert result["status"] == "completed"
        assert result["memories_processed"] == 5
        assert result["memories_updated"] > 0
    
    @pytest.mark.asyncio
    async def test_memory_aging_worker(self, mock_db):
        """Test memory aging worker"""
        worker = MemoryAgingWorker(batch_size=10)
        
        # Mock memory data with aging info
        mock_memories = [
            {
                "id": f"mem_{i}",
                "created_at": datetime.now() - timedelta(days=30),
                "last_accessed": datetime.now() - timedelta(days=i),
                "access_count": 10,
                "importance_score": 7.0,
                "content": "Test memory content",
                "memory_type": "semantic",
                "initial_strength": 1.0,
                "current_strength": 0.8,
                "last_review": None,
                "review_count": 0
            }
            for i in range(3)
        ]
        mock_db.fetch.return_value = mock_memories
        
        # Mock aging algorithm response
        with patch.object(worker.aging_algorithms, 'calculate_memory_strength') as mock_calc:
            mock_calc.return_value = {
                "current_strength": 0.6,
                "consolidation_score": 0.7,
                "decay_rate": 0.1,
                "next_review": datetime.now() + timedelta(days=7),
                "strength_category": "moderate",
                "initial_strength": 1.0
            }
            
            result = await worker.run_aging_update(mock_db)
            
        assert result["status"] == "completed"
        assert result["processed"] == 3
        assert mock_db.execute.called


class TestTriggers:
    """Test trigger implementations"""
    
    @pytest.mark.asyncio
    async def test_threshold_trigger(self):
        """Test threshold-based triggers"""
        triggered = False
        
        async def trigger_action(context):
            nonlocal triggered
            triggered = True
            return {"triggered": True}
        
        trigger = ThresholdTrigger(
            trigger_id="test_threshold",
            name="Test Threshold",
            action=trigger_action,
            metric_name="test_metric",
            threshold=100,
            comparison="greater",
            cooldown_minutes=5
        )
        
        # Test below threshold
        context = {"test_metric": 50}
        result = await trigger.execute(context)
        assert not triggered
        
        # Test above threshold
        context = {"test_metric": 150}
        result = await trigger.execute(context)
        assert triggered
        assert trigger.trigger_count == 1
    
    @pytest.mark.asyncio
    async def test_time_trigger(self):
        """Test time-based triggers"""
        triggered = False
        
        async def trigger_action(context):
            nonlocal triggered
            triggered = True
            return {"triggered": True}
        
        trigger = TimeTrigger(
            trigger_id="test_time",
            name="Test Time",
            action=trigger_action,
            schedule_type="interval",
            schedule_config={"minutes": 5}
        )
        
        # First check should trigger (no last_triggered)
        context = {}
        result = await trigger.execute(context)
        assert triggered
        
        # Immediate second check should not trigger
        triggered = False
        result = await trigger.execute(context)
        assert not triggered
    
    @pytest.mark.asyncio
    async def test_event_trigger(self):
        """Test event-based triggers"""
        triggered = False
        
        async def trigger_action(context):
            nonlocal triggered
            triggered = True
            return {"triggered": True}
        
        trigger = EventTrigger(
            trigger_id="test_event",
            name="Test Event",
            action=trigger_action,
            event_types=["test_event_type"]
        )
        
        # No events - should not trigger
        context = {}
        result = await trigger.execute(context)
        assert not triggered
        
        # Record event and check
        trigger.record_event("test_event_type", {"data": "test"})
        result = await trigger.execute(context)
        assert triggered
    
    @pytest.mark.asyncio
    async def test_performance_trigger(self):
        """Test performance-based triggers"""
        triggered = False
        
        async def trigger_action(context):
            nonlocal triggered
            triggered = True
            return {"triggered": True}
        
        trigger = PerformanceTrigger(
            trigger_id="test_perf",
            name="Test Performance",
            action=trigger_action,
            metric_type="cpu",
            threshold=80.0,
            duration_seconds=2
        )
        
        # Mock psutil
        with patch('app.scheduler.triggers.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 90.0  # Above threshold
            
            # Record metrics over time
            for _ in range(3):
                await trigger.execute({})
                await asyncio.sleep(0.1)
            
            # Should trigger after sustained high CPU
            assert triggered


class TestAutomationService:
    """Test the main automation service"""
    
    @pytest.fixture
    def automation_service(self):
        """Create automation service instance"""
        return AutomationService()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, automation_service):
        """Test automation service initialization"""
        with patch.object(automation_service.scheduler, 'start') as mock_start:
            with patch('app.services.automation_service.trigger_manager') as mock_trigger:
                await automation_service.initialize()
                
        assert automation_service.is_initialized
        mock_start.assert_called_once()
        
        # Verify tasks were registered
        assert len(automation_service.scheduler.tasks) > 0
    
    @pytest.mark.asyncio
    async def test_service_shutdown(self, automation_service):
        """Test automation service shutdown"""
        automation_service.is_initialized = True
        
        with patch.object(automation_service.scheduler, 'stop') as mock_stop:
            with patch('app.services.automation_service.trigger_manager') as mock_trigger:
                await automation_service.shutdown()
                
        assert not automation_service.is_initialized
        mock_stop.assert_called_once()
    
    def test_get_automation_status(self, automation_service):
        """Test getting automation status"""
        automation_service.is_initialized = True
        automation_service.scheduler._running = True
        
        status = automation_service.get_automation_status()
        
        assert status["initialized"] is True
        assert status["scheduler_running"] is True
        assert "scheduled_tasks" in status
        assert "active_triggers" in status
    
    def test_manual_task_trigger(self, automation_service):
        """Test manual task triggering"""
        # Add a test task
        test_task = ScheduledTask(
            id="test_manual",
            name="Test Manual",
            function=lambda: None,
            schedule="daily"
        )
        automation_service.scheduler.tasks["test_manual"] = test_task
        
        # Trigger manually
        manual_id = automation_service.trigger_task("test_manual")
        
        assert manual_id is not None
        assert manual_id.startswith("manual_test_manual_")