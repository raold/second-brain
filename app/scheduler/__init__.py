"""
Task Scheduler Module for Second Brain

This module provides enterprise-grade task scheduling and automation
capabilities for memory consolidation, cleanup, and maintenance operations.
"""

from .task_scheduler import TaskScheduler, ScheduledTask, TaskStatus
from .background_workers import (
    ConsolidationWorker,
    CleanupWorker,
    ImportanceUpdateWorker,
    MemoryAgingWorker
)
from .triggers import (
    ThresholdTrigger,
    TimeTrigger,
    EventTrigger,
    PerformanceTrigger
)

__all__ = [
    "TaskScheduler",
    "ScheduledTask",
    "TaskStatus",
    "ConsolidationWorker",
    "CleanupWorker",
    "ImportanceUpdateWorker",
    "MemoryAgingWorker",
    "ThresholdTrigger",
    "TimeTrigger",
    "EventTrigger",
    "PerformanceTrigger"
]