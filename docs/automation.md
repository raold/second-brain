# Automation System Documentation

## Overview

The Second Brain automation system provides intelligent, hands-off memory management through background workers, scheduled tasks, and event-driven triggers. The system automatically maintains optimal performance and storage efficiency without manual intervention.

## Architecture

### Components

1. **Task Scheduler** (`app/scheduler/task_scheduler.py`)
   - Enterprise-grade task scheduling with cron-like expressions
   - Concurrent task execution with configurable limits
   - Persistent task state across restarts
   - Built-in retry logic with exponential backoff

2. **Background Workers** (`app/scheduler/background_workers.py`)
   - **ConsolidationWorker**: Deduplicates similar memories
   - **CleanupWorker**: Removes stale data and logs
   - **ImportanceUpdateWorker**: Recalculates memory importance
   - **MemoryAgingWorker**: Applies cognitive decay models

3. **Event Triggers** (`app/scheduler/triggers.py`)
   - **ThresholdTrigger**: Activates on metric thresholds
   - **PerformanceTrigger**: Monitors system resources
   - **EventTrigger**: Responds to system events

4. **Automation Service** (`app/services/automation_service.py`)
   - Central orchestrator for all automation
   - REST API integration
   - Monitoring and control interface

## Configuration

### Default Schedule

```python
# Daily Tasks
- Memory Consolidation: 2:00 AM daily
- System Cleanup: 3:00 AM daily

# Hourly Tasks
- Importance Updates: Every hour
- Memory Aging: Every hour

# Event-Driven
- Duplicate Detection: When rate exceeds 5%
- Performance Optimization: When CPU > 80%
```

### Thresholds

| Metric | Threshold | Action |
|--------|-----------|---------|
| Duplicate Rate | 5% | Trigger consolidation |
| CPU Usage | 80% | Pause non-critical tasks |
| Memory Usage | 85% | Trigger cleanup |
| Disk Usage | 90% | Emergency cleanup |
| Log Age | 90 days | Delete old logs |

## API Endpoints

### Get Automation Status
```bash
GET /automation/status
```

Response:
```json
{
  "status": "active",
  "scheduled_tasks": {
    "consolidation": {
      "next_run": "2025-07-23T02:00:00Z",
      "last_run": "2025-07-22T02:00:00Z",
      "status": "completed"
    },
    "cleanup": {
      "next_run": "2025-07-23T03:00:00Z",
      "last_run": "2025-07-22T03:00:00Z",
      "status": "completed"
    }
  },
  "triggers": {
    "duplicate_monitor": {
      "enabled": true,
      "current_value": 2.3,
      "threshold": 5.0
    }
  },
  "metrics": {
    "duplicate_rate": 2.3,
    "memories_consolidated_today": 45,
    "storage_saved_mb": 127
  }
}
```

### Control Tasks
```bash
POST /automation/tasks/control?action=pause
POST /automation/tasks/control?action=resume
POST /automation/tasks/control?action=stop
```

### Trigger Immediate Actions
```bash
POST /automation/consolidation/immediate
POST /automation/cleanup/immediate
```

## Workers Detail

### Consolidation Worker

**Purpose**: Automatically deduplicate similar memories

**Algorithm**:
1. Compute embeddings for all memories
2. Find pairs with similarity > 95%
3. Merge metadata and tags
4. Keep the more recent/important memory
5. Update references

**Configuration**:
```python
SIMILARITY_THRESHOLD = 0.95
BATCH_SIZE = 100
MAX_MEMORIES_PER_RUN = 10000
```

### Cleanup Worker

**Purpose**: Remove stale data and maintain storage efficiency

**Targets**:
- System logs older than 90 days
- Orphaned embeddings
- Temporary processing files
- Failed upload remnants

**Safety**:
- Never deletes user memories
- Maintains audit trail
- Checks references before deletion

### Importance Update Worker

**Purpose**: Dynamically adjust memory importance based on usage

**Factors**:
- Access frequency
- Time since last access
- User interactions
- Semantic relationships

**Formula**:
```python
new_importance = (
    0.4 * access_score +
    0.3 * recency_score +
    0.2 * relationship_score +
    0.1 * original_importance
)
```

### Memory Aging Worker

**Purpose**: Apply cognitive science models for natural forgetting

**Models**:
- Ebbinghaus forgetting curve
- Spaced repetition principles
- Consolidation theory

**Effects**:
- Gradual importance decay
- Strengthening through access
- Semantic network preservation

## Monitoring

### Metrics Tracked

1. **Performance Metrics**
   - Task execution time
   - Success/failure rates
   - Resource usage

2. **Business Metrics**
   - Memories processed
   - Storage saved
   - Duplicate rate

3. **System Health**
   - Worker status
   - Queue depth
   - Error rates

### Alerts

Configure alerts for:
- Task failures
- Threshold breaches
- Performance degradation
- Resource exhaustion

## Best Practices

1. **Scheduling**
   - Run heavy tasks during off-peak hours
   - Stagger task start times
   - Consider time zones

2. **Resource Management**
   - Set appropriate worker limits
   - Monitor memory usage
   - Use connection pooling

3. **Error Handling**
   - Configure retry policies
   - Set timeout limits
   - Log errors comprehensively

4. **Testing**
   - Test in staging first
   - Monitor after deployment
   - Have rollback plan

## Troubleshooting

### Common Issues

1. **Tasks Not Running**
   - Check automation status
   - Verify scheduler is active
   - Review task logs

2. **High Resource Usage**
   - Adjust batch sizes
   - Increase task intervals
   - Check for infinite loops

3. **Consolidation Errors**
   - Verify embedding service
   - Check similarity threshold
   - Review memory formats

### Debug Commands

```bash
# View task history
GET /automation/tasks/history

# Get detailed task log
GET /automation/tasks/{task_id}/logs

# Force task execution
POST /automation/tasks/{task_id}/run

# Reset task state
POST /automation/tasks/{task_id}/reset
```

## Advanced Configuration

### Custom Schedules

```python
# Configure custom schedule
scheduler.schedule_task(
    task_id="custom_analysis",
    task=custom_analysis_worker,
    schedule="0 4 * * 1",  # Every Monday at 4 AM
    enabled=True
)
```

### Custom Triggers

```python
# Create custom trigger
trigger = ThresholdTrigger(
    trigger_id="memory_growth",
    name="Memory Growth Monitor",
    action=growth_analysis,
    metric_name="daily_memory_count",
    threshold=1000,
    comparison="greater"
)
```

### Performance Tuning

```python
# Adjust for large deployments
CONSOLIDATION_BATCH_SIZE = 500
CLEANUP_CHUNK_SIZE = 10000
MAX_CONCURRENT_TASKS = 10
TASK_TIMEOUT = 3600  # 1 hour
```

## Security Considerations

1. **Access Control**
   - Admin-only automation control
   - Read-only status for users
   - Audit all actions

2. **Data Safety**
   - Never auto-delete user content
   - Backup before consolidation
   - Validate all operations

3. **Resource Limits**
   - Prevent runaway tasks
   - Set memory limits
   - Monitor disk usage

## Future Enhancements

1. **Machine Learning**
   - Predictive scheduling
   - Anomaly detection
   - Smart consolidation

2. **Distributed Processing**
   - Multi-node support
   - Queue-based architecture
   - Horizontal scaling

3. **Advanced Analytics**
   - Pattern recognition
   - Trend analysis
   - Optimization suggestions