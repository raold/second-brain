"""
Main automation service that coordinates scheduled tasks and triggers
for the Second Brain memory management system.

This service:
- Initializes and manages the task scheduler
- Sets up automated consolidation and cleanup tasks
- Configures triggers for event-driven automation
- Provides monitoring and control APIs
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from app.scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskStatus,
    TaskPriority,
    ConsolidationWorker,
    CleanupWorker,
    ImportanceUpdateWorker,
    MemoryAgingWorker,
    ThresholdTrigger,
    TimeTrigger,
    EventTrigger,
    PerformanceTrigger,
    trigger_manager
)
from app.config import settings

logger = logging.getLogger(__name__)


class AutomationService:
    """
    Main automation service for Second Brain.
    
    Manages all automated operations including:
    - Memory consolidation and deduplication
    - Log and data cleanup
    - Importance score updates
    - Memory aging calculations
    - Event-driven triggers
    """
    
    def __init__(self):
        self.scheduler = TaskScheduler(
            max_concurrent_tasks=settings.get("MAX_CONCURRENT_TASKS", 5)
        )
        self.is_initialized = False
        
        # Worker instances
        self.consolidation_worker = ConsolidationWorker()
        self.cleanup_worker = CleanupWorker()
        self.importance_worker = ImportanceUpdateWorker()
        self.aging_worker = MemoryAgingWorker()
        
    async def initialize(self):
        """Initialize the automation service with all scheduled tasks"""
        if self.is_initialized:
            logger.warning("Automation service already initialized")
            return
            
        logger.info("Initializing automation service...")
        
        # Register scheduled tasks
        await self._register_scheduled_tasks()
        
        # Set up triggers
        await self._setup_triggers()
        
        # Start the scheduler
        await self.scheduler.start()
        
        # Start trigger monitoring
        await trigger_manager.start_monitoring()
        
        self.is_initialized = True
        logger.info("Automation service initialized successfully")
        
    async def shutdown(self):
        """Gracefully shutdown the automation service"""
        logger.info("Shutting down automation service...")
        
        # Stop trigger monitoring
        await trigger_manager.stop_monitoring()
        
        # Stop the scheduler
        await self.scheduler.stop()
        
        self.is_initialized = False
        logger.info("Automation service shutdown complete")
        
    async def _register_scheduled_tasks(self):
        """Register all scheduled tasks with the scheduler"""
        
        # Daily consolidation task (runs at 2 AM)
        consolidation_task = ScheduledTask(
            id="daily_consolidation",
            name="Daily Memory Consolidation",
            function=self.consolidation_worker.run_consolidation,
            schedule="daily",
            priority=TaskPriority.HIGH,
            timeout=7200,  # 2 hours
            metadata={
                "description": "Automated memory deduplication and consolidation"
            }
        )
        self.scheduler.register_task(consolidation_task)
        
        # Daily cleanup task (runs at 3 AM)
        cleanup_task = ScheduledTask(
            id="daily_cleanup",
            name="Daily Log Cleanup",
            function=self.cleanup_worker.run_cleanup,
            schedule="daily",
            priority=TaskPriority.MEDIUM,
            timeout=3600,  # 1 hour
            metadata={
                "description": "Clean old logs and orphaned data"
            }
        )
        self.scheduler.register_task(cleanup_task)
        
        # Hourly importance update
        importance_task = ScheduledTask(
            id="hourly_importance",
            name="Hourly Importance Update",
            function=self.importance_worker.run_importance_update,
            schedule="every 1 hour",
            priority=TaskPriority.MEDIUM,
            timeout=1800,  # 30 minutes
            metadata={
                "description": "Update memory importance scores based on usage"
            }
        )
        self.scheduler.register_task(importance_task)
        
        # Daily memory aging calculation
        aging_task = ScheduledTask(
            id="daily_aging",
            name="Daily Memory Aging",
            function=self.aging_worker.run_aging_update,
            schedule="daily",
            priority=TaskPriority.LOW,
            timeout=3600,  # 1 hour
            metadata={
                "description": "Calculate memory aging and strength scores"
            }
        )
        self.scheduler.register_task(aging_task)
        
        # Weekly deep consolidation (runs on Sunday at 1 AM)
        deep_consolidation_task = ScheduledTask(
            id="weekly_deep_consolidation",
            name="Weekly Deep Consolidation",
            function=self._run_deep_consolidation,
            schedule="weekly",
            priority=TaskPriority.HIGH,
            timeout=14400,  # 4 hours
            metadata={
                "description": "Comprehensive memory consolidation and optimization"
            }
        )
        self.scheduler.register_task(deep_consolidation_task)
        
        logger.info("Registered 5 scheduled tasks")
        
    async def _setup_triggers(self):
        """Set up event and threshold-based triggers"""
        
        # Trigger consolidation when duplicate percentage exceeds 5%
        duplicate_trigger = ThresholdTrigger(
            trigger_id="high_duplicate_trigger",
            name="High Duplicate Percentage Trigger",
            action=self._trigger_immediate_consolidation,
            metric_name="duplicate_percentage",
            threshold=5.0,
            comparison="greater",
            cooldown_minutes=120  # 2 hour cooldown
        )
        trigger_manager.register_trigger(duplicate_trigger)
        
        # Trigger cleanup when disk usage exceeds 85%
        disk_trigger = PerformanceTrigger(
            trigger_id="high_disk_usage_trigger",
            name="High Disk Usage Trigger",
            action=self._trigger_immediate_cleanup,
            metric_type="disk",
            threshold=85.0,
            duration_seconds=300  # 5 minutes sustained
        )
        trigger_manager.register_trigger(disk_trigger)
        
        # Trigger importance update after bulk import
        import_trigger = EventTrigger(
            trigger_id="bulk_import_trigger",
            name="Bulk Import Completion Trigger",
            action=self._trigger_importance_update,
            event_types=["bulk_import_completed"],
            condition=lambda events, ctx: len(events) > 0
        )
        trigger_manager.register_trigger(import_trigger)
        
        # Trigger optimization when memory usage high
        memory_trigger = PerformanceTrigger(
            trigger_id="high_memory_trigger",
            name="High Memory Usage Trigger",
            action=self._trigger_memory_optimization,
            metric_type="memory",
            threshold=80.0,
            duration_seconds=180  # 3 minutes sustained
        )
        trigger_manager.register_trigger(memory_trigger)
        
        logger.info("Set up 4 automation triggers")
        
    async def _run_deep_consolidation(self, db: Any, **kwargs) -> Dict[str, Any]:
        """Run comprehensive consolidation including all optimization steps"""
        logger.info("Starting deep consolidation process...")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "steps_completed": []
        }
        
        try:
            # Step 1: Run deduplication
            dedup_result = await self.consolidation_worker.run_consolidation(db)
            results["steps_completed"].append({
                "step": "deduplication",
                "result": dedup_result
            })
            
            # Step 2: Update importance scores
            importance_result = await self.importance_worker.run_importance_update(db)
            results["steps_completed"].append({
                "step": "importance_update",
                "result": importance_result
            })
            
            # Step 3: Calculate aging
            aging_result = await self.aging_worker.run_aging_update(db)
            results["steps_completed"].append({
                "step": "aging_calculation",
                "result": aging_result
            })
            
            # Step 4: Clean up old data
            cleanup_result = await self.cleanup_worker.run_cleanup(db)
            results["steps_completed"].append({
                "step": "cleanup",
                "result": cleanup_result
            })
            
            results["status"] = "completed"
            results["end_time"] = datetime.now().isoformat()
            
            logger.info("Deep consolidation completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Deep consolidation failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            return results
    
    async def _trigger_immediate_consolidation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger immediate consolidation task"""
        logger.info("Triggering immediate consolidation due to high duplicate count")
        
        # Create one-time task
        task = ScheduledTask(
            id=f"triggered_consolidation_{datetime.now().timestamp()}",
            name="Triggered Consolidation",
            function=self.consolidation_worker.run_consolidation,
            schedule="once",  # One-time execution
            priority=TaskPriority.CRITICAL,
            timeout=3600,
            metadata={
                "trigger_reason": "high_duplicate_percentage",
                "context": context
            }
        )
        
        # Queue for immediate execution
        self.scheduler.register_task(task)
        
        return {"action": "consolidation_triggered", "task_id": task.id}
    
    async def _trigger_immediate_cleanup(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger immediate cleanup task"""
        logger.info("Triggering immediate cleanup due to high disk usage")
        
        task = ScheduledTask(
            id=f"triggered_cleanup_{datetime.now().timestamp()}",
            name="Triggered Cleanup",
            function=self.cleanup_worker.run_cleanup,
            schedule="once",
            priority=TaskPriority.CRITICAL,
            timeout=1800,
            metadata={
                "trigger_reason": "high_disk_usage",
                "context": context
            }
        )
        
        self.scheduler.register_task(task)
        
        return {"action": "cleanup_triggered", "task_id": task.id}
    
    async def _trigger_importance_update(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger importance update after bulk import"""
        logger.info("Triggering importance update after bulk import")
        
        task = ScheduledTask(
            id=f"triggered_importance_{datetime.now().timestamp()}",
            name="Post-Import Importance Update",
            function=self.importance_worker.run_importance_update,
            schedule="once",
            priority=TaskPriority.HIGH,
            timeout=3600,
            metadata={
                "trigger_reason": "bulk_import_completed",
                "context": context
            }
        )
        
        self.scheduler.register_task(task)
        
        return {"action": "importance_update_triggered", "task_id": task.id}
    
    async def _trigger_memory_optimization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger memory optimization when system memory is high"""
        logger.info("Triggering memory optimization due to high memory usage")
        
        # This could trigger various optimization strategies
        # For now, trigger a cleanup
        return await self._trigger_immediate_cleanup(context)
    
    # API Methods for external control
    
    def get_automation_status(self) -> Dict[str, Any]:
        """Get current status of automation service"""
        return {
            "initialized": self.is_initialized,
            "scheduler_running": self.scheduler._running,
            "scheduled_tasks": self.scheduler.get_all_tasks(),
            "active_triggers": [
                {
                    "id": trigger.trigger_id,
                    "name": trigger.name,
                    "enabled": trigger.enabled,
                    "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None,
                    "trigger_count": trigger.trigger_count
                }
                for trigger in trigger_manager.triggers.values()
            ]
        }
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task"""
        self.scheduler.enable_task(task_id)
        return True
        
    def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task"""
        self.scheduler.disable_task(task_id)
        return True
    
    def trigger_task(self, task_id: str) -> Optional[str]:
        """Manually trigger a scheduled task"""
        if task_id not in self.scheduler.tasks:
            return None
            
        # Create one-time execution task
        original_task = self.scheduler.tasks[task_id]
        manual_task = ScheduledTask(
            id=f"manual_{task_id}_{datetime.now().timestamp()}",
            name=f"Manual: {original_task.name}",
            function=original_task.function,
            schedule="once",
            priority=TaskPriority.HIGH,
            timeout=original_task.timeout,
            metadata={
                **original_task.metadata,
                "triggered_manually": True,
                "original_task_id": task_id
            }
        )
        
        self.scheduler.register_task(manual_task)
        return manual_task.id
    
    def record_event(self, event_type: str, event_data: Dict[str, Any]):
        """Record an event for trigger processing"""
        trigger_manager.record_event(event_type, event_data)


# Global automation service instance
automation_service = AutomationService()