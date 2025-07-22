"""
Event and threshold-based triggers for automated task execution.

These triggers monitor system state and automatically initiate
consolidation, cleanup, and maintenance tasks based on configurable conditions.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
import psutil

logger = logging.getLogger(__name__)


@dataclass
class TriggerEvent:
    """Represents a trigger event"""
    trigger_id: str
    trigger_type: str
    condition_met: bool
    timestamp: datetime
    metadata: Dict[str, Any]
    action: Optional[Callable] = None


class BaseTrigger(ABC):
    """Base class for all triggers"""
    
    def __init__(self, 
                 trigger_id: str,
                 name: str,
                 action: Callable,
                 enabled: bool = True):
        self.trigger_id = trigger_id
        self.name = name
        self.action = action
        self.enabled = enabled
        self.last_triggered: Optional[datetime] = None
        self.trigger_count = 0
        
    @abstractmethod
    async def check_condition(self, context: Dict[str, Any]) -> bool:
        """Check if trigger condition is met"""
        pass
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the trigger action if conditions are met"""
        if not self.enabled:
            return None
            
        if await self.check_condition(context):
            logger.info(f"Trigger {self.name} activated")
            self.last_triggered = datetime.now()
            self.trigger_count += 1
            
            # Execute the action
            return await self.action(context)
        
        return None


class ThresholdTrigger(BaseTrigger):
    """
    Triggers based on numeric thresholds.
    
    Examples:
    - Trigger consolidation when duplicate count > 100
    - Trigger cleanup when disk usage > 90%
    - Trigger archival when memory count > 10000
    """
    
    def __init__(self,
                 trigger_id: str,
                 name: str,
                 action: Callable,
                 metric_name: str,
                 threshold: float,
                 comparison: str = "greater",  # greater, less, equal
                 cooldown_minutes: int = 60,
                 enabled: bool = True):
        super().__init__(trigger_id, name, action, enabled)
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.cooldown_minutes = cooldown_minutes
        
    async def check_condition(self, context: Dict[str, Any]) -> bool:
        """Check if metric exceeds threshold"""
        # Check cooldown period
        if self.last_triggered:
            cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
            if datetime.now() < cooldown_end:
                return False
        
        # Get metric value from context
        metric_value = context.get(self.metric_name)
        if metric_value is None:
            return False
        
        # Compare against threshold
        if self.comparison == "greater":
            return metric_value > self.threshold
        elif self.comparison == "less":
            return metric_value < self.threshold
        elif self.comparison == "equal":
            return metric_value == self.threshold
        else:
            logger.warning(f"Unknown comparison type: {self.comparison}")
            return False


class TimeTrigger(BaseTrigger):
    """
    Triggers based on time conditions.
    
    Examples:
    - Trigger at specific time of day
    - Trigger after certain duration since last run
    - Trigger on specific days of week
    """
    
    def __init__(self,
                 trigger_id: str,
                 name: str,
                 action: Callable,
                 schedule_type: str,  # "daily", "weekly", "interval"
                 schedule_config: Dict[str, Any],
                 enabled: bool = True):
        super().__init__(trigger_id, name, action, enabled)
        self.schedule_type = schedule_type
        self.schedule_config = schedule_config
        
    async def check_condition(self, context: Dict[str, Any]) -> bool:
        """Check if time condition is met"""
        now = datetime.now()
        
        if self.schedule_type == "daily":
            # Check if it's the right time of day
            target_hour = self.schedule_config.get("hour", 0)
            target_minute = self.schedule_config.get("minute", 0)
            
            if now.hour == target_hour and now.minute == target_minute:
                # Make sure we haven't triggered in the last minute
                if self.last_triggered and (now - self.last_triggered).seconds < 60:
                    return False
                return True
                
        elif self.schedule_type == "weekly":
            # Check day of week and time
            target_day = self.schedule_config.get("day_of_week", 0)  # 0 = Monday
            target_hour = self.schedule_config.get("hour", 0)
            
            if now.weekday() == target_day and now.hour == target_hour:
                if self.last_triggered and (now - self.last_triggered).days < 1:
                    return False
                return True
                
        elif self.schedule_type == "interval":
            # Check if enough time has passed since last trigger
            interval_minutes = self.schedule_config.get("minutes", 60)
            
            if not self.last_triggered:
                return True
                
            time_since_last = (now - self.last_triggered).total_seconds() / 60
            return time_since_last >= interval_minutes
            
        return False


class EventTrigger(BaseTrigger):
    """
    Triggers based on system events.
    
    Examples:
    - Trigger on memory creation
    - Trigger on bulk import completion
    - Trigger on error threshold exceeded
    """
    
    def __init__(self,
                 trigger_id: str,
                 name: str,
                 action: Callable,
                 event_types: List[str],
                 condition: Optional[Callable] = None,
                 enabled: bool = True):
        super().__init__(trigger_id, name, action, enabled)
        self.event_types = set(event_types)
        self.condition = condition
        self.event_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 100
        
    def record_event(self, event_type: str, event_data: Dict[str, Any]):
        """Record an event for processing"""
        if event_type in self.event_types:
            event = {
                "type": event_type,
                "timestamp": datetime.now(),
                "data": event_data
            }
            
            self.event_buffer.append(event)
            
            # Keep buffer size manageable
            if len(self.event_buffer) > self.buffer_size:
                self.event_buffer = self.event_buffer[-self.buffer_size:]
    
    async def check_condition(self, context: Dict[str, Any]) -> bool:
        """Check if event condition is met"""
        if not self.event_buffer:
            return False
        
        # Check custom condition if provided
        if self.condition:
            return await self.condition(self.event_buffer, context)
        
        # Default: trigger if any relevant event exists
        return len(self.event_buffer) > 0


class PerformanceTrigger(BaseTrigger):
    """
    Triggers based on system performance metrics.
    
    Examples:
    - Trigger optimization when query time > threshold
    - Trigger cleanup when memory usage high
    - Trigger scaling when CPU usage sustained high
    """
    
    def __init__(self,
                 trigger_id: str,
                 name: str,
                 action: Callable,
                 metric_type: str,  # "cpu", "memory", "disk", "query_time"
                 threshold: float,
                 duration_seconds: int = 60,
                 enabled: bool = True):
        super().__init__(trigger_id, name, action, enabled)
        self.metric_type = metric_type
        self.threshold = threshold
        self.duration_seconds = duration_seconds
        self.metric_history: List[tuple[datetime, float]] = []
        self.history_size = 100
        
    def record_metric(self, value: float):
        """Record a performance metric"""
        now = datetime.now()
        self.metric_history.append((now, value))
        
        # Clean old entries
        cutoff = now - timedelta(seconds=self.duration_seconds * 2)
        self.metric_history = [
            (ts, val) for ts, val in self.metric_history 
            if ts > cutoff
        ]
    
    async def check_condition(self, context: Dict[str, Any]) -> bool:
        """Check if performance condition is met"""
        # Get current metric value
        current_value = await self._get_current_metric()
        
        if current_value is not None:
            self.record_metric(current_value)
        
        # Check if threshold exceeded for duration
        now = datetime.now()
        start_time = now - timedelta(seconds=self.duration_seconds)
        
        recent_metrics = [
            val for ts, val in self.metric_history
            if ts >= start_time
        ]
        
        if not recent_metrics:
            return False
        
        # Check if all recent metrics exceed threshold
        avg_metric = sum(recent_metrics) / len(recent_metrics)
        return avg_metric > self.threshold
    
    async def _get_current_metric(self) -> Optional[float]:
        """Get current value of the performance metric"""
        try:
            if self.metric_type == "cpu":
                return psutil.cpu_percent(interval=0.1)
            elif self.metric_type == "memory":
                return psutil.virtual_memory().percent
            elif self.metric_type == "disk":
                return psutil.disk_usage('/').percent
            elif self.metric_type == "query_time":
                # This would come from database monitoring
                # For now, return None
                return None
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting metric {self.metric_type}: {e}")
            return None


class TriggerManager:
    """
    Manages all triggers and coordinates their execution.
    """
    
    def __init__(self):
        self.triggers: Dict[str, BaseTrigger] = {}
        self.running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
    def register_trigger(self, trigger: BaseTrigger):
        """Register a new trigger"""
        self.triggers[trigger.trigger_id] = trigger
        logger.info(f"Registered trigger: {trigger.name}")
        
    def unregister_trigger(self, trigger_id: str):
        """Remove a trigger"""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            logger.info(f"Unregistered trigger: {trigger_id}")
    
    async def start_monitoring(self, check_interval: int = 30):
        """Start monitoring all triggers"""
        if self.running:
            logger.warning("Trigger monitoring already running")
            return
            
        self.running = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(check_interval)
        )
        logger.info("Trigger monitoring started")
        
    async def stop_monitoring(self):
        """Stop monitoring triggers"""
        self.running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Trigger monitoring stopped")
        
    async def _monitor_loop(self, check_interval: int):
        """Main monitoring loop"""
        while self.running:
            try:
                # Gather system context
                context = await self._gather_context()
                
                # Check all triggers
                for trigger in self.triggers.values():
                    if trigger.enabled:
                        try:
                            await trigger.execute(context)
                        except Exception as e:
                            logger.error(f"Error executing trigger {trigger.name}: {e}")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in trigger monitor loop: {e}")
                await asyncio.sleep(check_interval)
    
    async def _gather_context(self) -> Dict[str, Any]:
        """Gather system context for trigger evaluation"""
        from app.database import get_db
        
        context = {
            "timestamp": datetime.now(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
        
        # Gather database metrics
        try:
            async with get_db() as db:
                # Count memories
                memory_count = await db.fetchval("SELECT COUNT(*) FROM memories")
                context["memory_count"] = memory_count
                
                # Check for duplicates (simplified check)
                duplicate_query = """
                    SELECT COUNT(DISTINCT m1.id)
                    FROM memories m1
                    INNER JOIN memories m2 ON m1.id < m2.id
                    WHERE similarity(m1.content, m2.content) > 0.9
                """
                # Note: This is a simplified check - real implementation
                # would use vector similarity
                
                # Get recent operation counts
                recent_creates = await db.fetchval("""
                    SELECT COUNT(*) FROM memories
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                context["recent_memory_creates"] = recent_creates
                
        except Exception as e:
            logger.error(f"Error gathering database context: {e}")
        
        return context
    
    def record_event(self, event_type: str, event_data: Dict[str, Any]):
        """Record an event for event triggers"""
        for trigger in self.triggers.values():
            if isinstance(trigger, EventTrigger):
                trigger.record_event(event_type, event_data)


# Global trigger manager instance
trigger_manager = TriggerManager()