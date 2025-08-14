"""
Background Task Queue System

Implements Redis-based task queue for asynchronous processing
of Google Drive files and other background operations.
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskType(Enum):
    """Types of background tasks"""
    DRIVE_FILE_SYNC = "drive_file_sync"
    DRIVE_FOLDER_SYNC = "drive_folder_sync"
    DRIVE_WEBHOOK = "drive_webhook"
    MEMORY_REINDEX = "memory_reindex"
    BATCH_EMBEDDING = "batch_embedding"


class TaskQueue:
    """
    Redis-based task queue for background processing.
    
    Features:
    - Priority-based task execution
    - Automatic retry with exponential backoff
    - Task deduplication
    - Progress tracking
    - Dead letter queue for failed tasks
    """
    
    def __init__(self):
        """
        Initialize the in-memory task queue.
        """
        self.redis = None  # No Redis support
        self.queue_prefix = "task_queue"
        self.processing_timeout = 300  # 5 minutes default timeout
        
    async def initialize(self):
        """Initialize the in-memory task queue"""
        # Always use in-memory queue
        self.in_memory_queue = asyncio.Queue()
        self.in_memory_tasks = {}
        logger.info("Task queue initialized (in-memory mode)")
    
    async def enqueue(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        user_id: Optional[str] = None,
        dedupe_key: Optional[str] = None
    ) -> str:
        """
        Add a task to the queue.
        
        Args:
            task_type: Type of task to execute
            payload: Task data/parameters
            priority: Task priority level
            user_id: Optional user ID for tracking
            dedupe_key: Optional key for deduplication
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        # Check for duplicate if dedupe key provided
        if dedupe_key:
            existing = await self._check_duplicate(dedupe_key)
            if existing:
                logger.info(f"Task already exists with dedupe_key: {dedupe_key}")
                return existing
        
        task = {
            "id": task_id,
            "type": task_type.value,
            "payload": payload,
            "priority": priority.value,
            "user_id": user_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "dedupe_key": dedupe_key
        }
        
        # Use in-memory queue
        await self.in_memory_queue.put(task)
        self.in_memory_tasks[task_id] = task
        
        logger.info(f"Task enqueued", extra={
            "task_id": task_id,
            "task_type": task_type.value,
            "priority": priority.name,
            "user_id": user_id
        })
        
        return task_id
    
    async def dequeue(self, priority: Optional[TaskPriority] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next task from the queue.
        
        Args:
            priority: Optional specific priority to dequeue from
            
        Returns:
            Task data or None if queue is empty
        """
        # Use in-memory queue
        try:
            task = await asyncio.wait_for(self.in_memory_queue.get(), timeout=0.1)
            task["status"] = TaskStatus.PROCESSING.value
            return task
        except asyncio.TimeoutError:
            return None
        
        return None
    
    async def complete(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            result: Optional task result data
        """
        # In-memory update
        if task_id in self.in_memory_tasks:
            self.in_memory_tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.in_memory_tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
            if result:
                self.in_memory_tasks[task_id]["result"] = result
        
        logger.info(f"Task completed", extra={
            "task_id": task_id
        })
    
    async def fail(self, task_id: str, error: str, retry: bool = True):
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            retry: Whether to retry the task
        """
        if False:  # Removed Redis code
            task_key = f"{self.queue_prefix}:task:{task_id}"
            task_data = await self.redis.hget(task_key, "data")
            
            if task_data:
                task = json.loads(task_data)
                retry_count = task.get("retry_count", 0)
                
                if retry and retry_count < 3:
                    # Retry with exponential backoff
                    task["status"] = TaskStatus.RETRYING.value
                    task["retry_count"] = retry_count + 1
                    task["last_error"] = error
                    
                    # Re-enqueue with delay
                    delay = (2 ** retry_count) * 10  # 10s, 20s, 40s
                    await asyncio.sleep(delay)
                    
                    # Re-add to queue
                    priority = task.get("priority", 2)
                    queue_key = f"{self.queue_prefix}:priority:{priority}"
                    await self.redis.lpush(queue_key, json.dumps(task))
                    
                    logger.info(f"Task retry scheduled", extra={
                        "task_id": task_id,
                        "retry_count": retry_count + 1,
                        "delay": delay
                    })
                else:
                    # Move to dead letter queue
                    task["status"] = TaskStatus.FAILED.value
                    task["failed_at"] = datetime.utcnow().isoformat()
                    task["error"] = error
                    
                    dlq_key = f"{self.queue_prefix}:dead_letter"
                    await self.redis.lpush(dlq_key, json.dumps(task))
                    
                    logger.error(f"Task failed permanently", extra={
                        "task_id": task_id,
                        "error": error
                    })
                
                await self.redis.hset(task_key, mapping={
                    "data": json.dumps(task),
                    "status": task["status"]
                })
                
                pass  # Redis code removed
                
        # In-memory handling
        if task_id in self.in_memory_tasks:
            self.in_memory_tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.in_memory_tasks[task_id]["error"] = error
    
    async def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status information
        """
        return self.in_memory_tasks.get(task_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue statistics including counts by priority and status
        """
        stats = {
            "pending": {},
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        if self.redis:
            # Count pending by priority
            for priority in [1, 2, 3, 4]:
                queue_key = f"{self.queue_prefix}:priority:{priority}"
                count = await self.redis.llen(queue_key)
                stats["pending"][TaskPriority(priority).name] = count
            
            # Count processing tasks
            processing_pattern = f"{self.queue_prefix}:processing:*"
            processing_keys = await self.redis.keys(processing_pattern)
            stats["processing"] = len(processing_keys)
            
            # Count in dead letter queue
            dlq_key = f"{self.queue_prefix}:dead_letter"
            stats["failed"] = await self.redis.llen(dlq_key)
            
        else:
            # In-memory stats
            stats["pending"]["TOTAL"] = self.in_memory_queue.qsize()
            for task in self.in_memory_tasks.values():
                status = task.get("status")
                if status == TaskStatus.PROCESSING.value:
                    stats["processing"] += 1
                elif status == TaskStatus.COMPLETED.value:
                    stats["completed"] += 1
                elif status == TaskStatus.FAILED.value:
                    stats["failed"] += 1
        
        return stats
    
    async def _check_duplicate(self, dedupe_key: str) -> Optional[str]:
        """
        Check if a task with the given deduplication key already exists.
        
        Args:
            dedupe_key: Deduplication key
            
        Returns:
            Task ID if duplicate exists, None otherwise
        """
        if self.redis:
            dedupe_hash_key = f"{self.queue_prefix}:dedupe:{dedupe_key}"
            task_id = await self.redis.get(dedupe_hash_key)
            return task_id.decode() if task_id else None
        
        # Check in-memory tasks
        for task_id, task in self.in_memory_tasks.items():
            if task.get("dedupe_key") == dedupe_key:
                return task_id
        
        return None
    
    async def cleanup_stale_tasks(self, timeout_minutes: int = 30):
        """
        Clean up tasks that have been processing for too long.
        
        Args:
            timeout_minutes: Minutes after which a processing task is considered stale
        """
        if not self.redis:
            return
        
        processing_pattern = f"{self.queue_prefix}:processing:*"
        processing_keys = await self.redis.keys(processing_pattern)
        
        for key in processing_keys:
            task_id = key.decode().split(":")[-1]
            
            # Check if task has timed out
            ttl = await self.redis.ttl(key)
            if ttl < 0:  # Key has expired
                # Mark task as failed
                await self.fail(task_id, "Task processing timeout", retry=True)
                
                logger.warning(f"Cleaned up stale task", extra={
                    "task_id": task_id
                })