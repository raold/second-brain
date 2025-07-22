# 🤖 Second Brain Automation Guide

## Overview

The Second Brain automation system provides enterprise-grade task scheduling and automated memory management capabilities. This guide covers the automation infrastructure that keeps your memory system optimized and healthy.

## Table of Contents

1. [Architecture](#architecture)
2. [Scheduled Tasks](#scheduled-tasks)
3. [Automation Triggers](#automation-triggers)
4. [Background Workers](#background-workers)
5. [API Reference](#api-reference)
6. [Configuration](#configuration)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

## Architecture

The automation system consists of four main components:

```
┌─────────────────────────────────────────────────────────┐
│                   Automation Service                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────┐ │
│  │ Task Scheduler │  │ Trigger Manager │  │ Workers  │ │
│  │                │  │                 │  │          │ │
│  │ - Daily tasks  │  │ - Threshold     │  │ - Dedup  │ │
│  │ - Hourly tasks │  │ - Time-based    │  │ - Clean  │ │
│  │ - Weekly tasks │  │ - Event-driven  │  │ - Score  │ │
│  │ - One-time     │  │ - Performance   │  │ - Aging  │ │
│  └────────────────┘  └─────────────────┘  └──────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Scheduled Tasks

### Default Schedule

The system runs the following automated tasks:

| Task | Schedule | Priority | Description |
|------|----------|----------|-------------|
| **Memory Consolidation** | Daily 2 AM | High | Deduplication and memory merging |
| **Log Cleanup** | Daily 3 AM | Medium | Remove old logs and orphaned data |
| **Importance Update** | Every hour | Medium | Recalculate memory importance scores |
| **Memory Aging** | Daily 4 AM | Low | Apply cognitive aging models |
| **Deep Consolidation** | Weekly Sunday 1 AM | High | Comprehensive optimization |

### Task Configuration

Each task can be configured with:

```python
{
    "schedule": "daily",           # or "hourly", "weekly", "every N minutes"
    "priority": "high",            # low, medium, high, critical
    "max_retries": 3,              # Number of retry attempts
    "retry_delay": 60,             # Seconds between retries
    "timeout": 3600,               # Maximum execution time (seconds)
    "enabled": true                # Enable/disable without removal
}
```

## Automation Triggers

### Threshold Triggers

Automatically execute tasks when metrics exceed thresholds:

- **High Duplicate Percentage** (>5%): Triggers immediate consolidation
- **High Disk Usage** (>85%): Triggers cleanup operations
- **Memory Count** (>10,000): Triggers optimization

### Event Triggers

React to system events:

- **Bulk Import Completion**: Updates importance scores
- **Error Threshold Exceeded**: Triggers diagnostic tasks
- **Memory Creation Burst**: Activates deduplication

### Performance Triggers

Monitor system performance:

- **High CPU Usage** (>80% for 3 min): Optimizes processing
- **High Memory Usage** (>80% for 3 min): Triggers cleanup
- **Slow Query Times**: Initiates index optimization

## Background Workers

### Consolidation Worker

Handles memory deduplication and merging:

```python
# Configuration
batch_size: 100              # Memories per batch
similarity_threshold: 0.95   # Minimum similarity for duplicates
merge_strategy: "smart"      # smart, keep_oldest, keep_newest
```

**Features:**
- Semantic similarity detection
- Metadata preservation
- Relationship maintenance
- Progress tracking

### Cleanup Worker

Manages data retention and cleanup:

```python
# Configuration
retention_days: 90          # Days to retain logs
cleanup_targets: [
    "access_logs",
    "operation_logs", 
    "orphaned_embeddings",
    "temporary_files"
]
```

**Operations:**
- Log rotation
- Orphaned data removal
- Temporary file cleanup
- Index maintenance

### Importance Update Worker

Recalculates memory importance based on usage:

```python
# Configuration
batch_size: 500            # Memories per update batch
decay_factor: 0.95         # Importance decay rate
access_boost: 1.2          # Boost per access
```

**Factors considered:**
- Access frequency
- Time since last access
- Content length
- User interactions

### Memory Aging Worker

Applies cognitive science models:

```python
# Configuration
batch_size: 200            # Memories per batch
algorithms: [
    "ebbinghaus",          # Forgetting curve
    "spacing_effect",      # Spaced repetition
    "consolidation"        # Memory consolidation theory
]
```

**Outputs:**
- Memory strength scores
- Optimal review times
- Archival recommendations

## API Reference

### Automation Status

```http
GET /automation/status
Authorization: Bearer <api_key>
```

**Response:**
```json
{
    "initialized": true,
    "scheduler_running": true,
    "scheduled_tasks": [...],
    "active_triggers": [...],
    "system_health": {
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "disk_percent": 73.5
    }
}
```

### Task Control

```http
POST /automation/tasks/control
Authorization: Bearer <api_key>
Content-Type: application/json

{
    "task_id": "daily_consolidation",
    "action": "trigger"  // enable, disable, trigger
}
```

### Manual Triggers

```http
POST /automation/consolidation/immediate
POST /automation/cleanup/immediate
Authorization: Bearer <api_key>
```

### Event Recording

```http
POST /automation/events/record
Authorization: Bearer <api_key>
Content-Type: application/json

{
    "event_type": "bulk_import_completed",
    "event_data": {
        "imported_count": 1000,
        "duration": 45.2
    }
}
```

## Configuration

### Environment Variables

```bash
# Automation Settings
MAX_CONCURRENT_TASKS=5        # Parallel task limit
TASK_SCHEDULER_ENABLED=true   # Enable/disable automation
AUTOMATION_LOG_LEVEL=INFO     # Logging verbosity

# Worker Configuration
CONSOLIDATION_BATCH_SIZE=100
CLEANUP_RETENTION_DAYS=90
IMPORTANCE_UPDATE_INTERVAL=3600
AGING_CALCULATION_BATCH=200

# Trigger Thresholds
DUPLICATE_THRESHOLD_PERCENT=5.0
DISK_USAGE_THRESHOLD=85.0
MEMORY_USAGE_THRESHOLD=80.0
```

### Task Persistence

Task states are persisted to:
```
data/scheduled_tasks.json
```

This allows recovery after system restart.

## Monitoring

### Health Check

```http
GET /automation/health
```

Returns simple health status for monitoring systems.

### Metrics

The automation system exposes Prometheus metrics:

```
# Task execution metrics
task_execution_total{task_id="...", status="..."}
task_execution_duration_seconds{task_id="..."}
task_retry_total{task_id="..."}

# Trigger metrics
trigger_activation_total{trigger_id="..."}
trigger_condition_check_total{trigger_id="...", result="..."}

# Worker metrics
worker_items_processed_total{worker_type="..."}
worker_processing_duration_seconds{worker_type="..."}
```

### Logging

Detailed logs are written with structured format:

```
2024-01-15 02:00:00 INFO [automation.scheduler] Starting task: daily_consolidation
2024-01-15 02:15:32 INFO [automation.consolidation] Processed 1523 memories, merged 47
2024-01-15 02:15:33 INFO [automation.scheduler] Task completed: daily_consolidation (932.1s)
```

## Troubleshooting

### Common Issues

#### Tasks Not Running

1. Check automation status:
   ```http
   GET /automation/status
   ```

2. Verify task is enabled:
   ```http
   GET /automation/tasks/{task_id}
   ```

3. Check logs for errors:
   ```bash
   grep "ERROR.*automation" logs/app.log
   ```

#### High Resource Usage

1. Reduce concurrent tasks:
   ```bash
   MAX_CONCURRENT_TASKS=2
   ```

2. Adjust batch sizes:
   ```bash
   CONSOLIDATION_BATCH_SIZE=50
   ```

3. Increase task timeouts for large datasets

#### Trigger Not Activating

1. Verify trigger conditions in status
2. Check cooldown periods haven't blocked execution
3. Ensure metrics are being updated
4. Review trigger thresholds

### Manual Recovery

If automation fails, manually trigger critical tasks:

```python
# Via API
POST /automation/tasks/trigger/daily_consolidation

# Or trigger all maintenance
POST /automation/consolidation/immediate
POST /automation/cleanup/immediate
```

### Performance Tuning

For large deployments (>100K memories):

1. **Increase batch sizes** for better throughput
2. **Adjust schedules** to avoid peak usage
3. **Enable streaming mode** for consolidation
4. **Use dedicated worker processes**

## Best Practices

1. **Monitor regularly**: Check automation status weekly
2. **Test changes**: Use dry-run mode before enabling new tasks
3. **Gradual rollout**: Enable one automation at a time
4. **Backup first**: Ensure backups before major consolidations
5. **Resource planning**: Schedule intensive tasks during off-hours

## Advanced Usage

### Custom Workers

Create custom workers by extending the base class:

```python
from app.scheduler.background_workers import BaseWorker

class CustomWorker(BaseWorker):
    async def run_task(self, db, **kwargs):
        # Your custom logic here
        pass
```

### Custom Triggers

Implement custom trigger logic:

```python
from app.scheduler.triggers import BaseTrigger

class CustomTrigger(BaseTrigger):
    async def check_condition(self, context):
        # Your trigger logic
        return condition_met
```

## Conclusion

The automation system ensures your Second Brain remains optimized and efficient without manual intervention. Regular monitoring and appropriate configuration will keep your memory system running smoothly at scale.

For additional help, consult the API documentation at `/docs` or file an issue in the repository.