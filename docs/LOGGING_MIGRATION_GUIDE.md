# Logging System Migration Guide

## Overview

The Second Brain logging system has been modernized to provide structured logging, request tracing, performance metrics, and better debugging capabilities.

## What's Changed

### ❌ Old Pattern (Deprecated)
```python
import logging
logger = logging.getLogger(__name__)

# Basic logging
logger.info("User created")
logger.error(f"Database error: {e}")

# Print statements (anti-pattern)
print("Debug info")
```

### ✅ New Pattern (Recommended)
```python
from app.utils.logging_config import get_logger, LogContext, PerformanceLogger

logger = get_logger(__name__)

# Structured logging with context
with LogContext(operation="create_user", user_id="123"):
    logger.info("User created", extra={
        "user_email": "user@example.com",
        "signup_method": "oauth"
    })

# Performance tracking
with PerformanceLogger("database_query", logger):
    result = db.query()
```

## Migration Steps

### 1. Update Logger Imports

**Find and Replace:**
```python
# OLD
import logging
logger = logging.getLogger(__name__)

# NEW  
from app.utils.logging_config import get_logger
logger = get_logger(__name__)
```

### 2. Replace Print Statements

**Find all print() statements:**
```bash
grep -r "print(" app/ --include="*.py"
```

**Replace with appropriate logging:**
```python
# OLD
print(f"Processing {count} items")

# NEW
logger.info("Processing items", extra={"count": count})
```

### 3. Add Request Context

For API endpoints and request handlers:

```python
from app.utils.logging_config import LogContext

async def my_endpoint(request: Request):
    with LogContext(
        operation="create_memory", 
        user_id=current_user["user_id"],
        request_id=request.headers.get("X-Request-ID")
    ):
        logger.info("Creating memory")
        # ... endpoint logic
```

### 4. Add Performance Monitoring

For operations that should be monitored:

```python
from app.utils.logging_config import PerformanceLogger

async def expensive_operation():
    with PerformanceLogger("memory_synthesis", logger):
        # ... operation code
        return result
```

### 5. Structured Error Logging

```python
# OLD
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise

# NEW
try:
    result = risky_operation()
except Exception as e:
    logger.exception("Operation failed", extra={
        "operation": "risky_operation",
        "input_params": {"param1": value1},
        "error_type": type(e).__name__
    })
    raise
```

## Configuration

### Environment Variables

```bash
# Logging level
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

# Logging format  
LOG_FORMAT=structured|development

# Environment
ENVIRONMENT=development|testing|production
```

### Structured vs Development Logging

**Development Mode:**
```
10:30:15 | INFO     | app.services.memory  | [req:a1b2c3d4 | user:123] Memory created successfully
```

**Production Mode (JSON):**
```json
{
  "timestamp": "2025-01-22T10:30:15.123Z",
  "level": "INFO", 
  "logger": "app.services.memory",
  "message": "Memory created successfully",
  "request_id": "a1b2c3d4e5f6",
  "user_id": "123",
  "operation": "create_memory",
  "duration_ms": 45.2,
  "memory_id": "mem_456"
}
```

## Features

### 1. Request Tracing
```python
with LogContext(request_id="abc123", user_id="user456"):
    logger.info("Processing request")
    # All logs within this context will include request_id and user_id
```

### 2. Performance Monitoring
```python
with PerformanceLogger("database_operation"):
    result = db.expensive_query()
# Automatically logs duration and memory usage
```

### 3. Contextual Logging
```python
# Logger with persistent context
user_logger = logger.with_context(user_id="123", tenant="acme")
user_logger.info("User action")  # Always includes user_id and tenant
```

### 4. Structured Data
```python
logger.info("Memory synthesized", extra={
    "synthesis_strategy": "hierarchical",
    "input_memories": 15,
    "output_insights": 3,
    "confidence_score": 0.87
})
```

## Best Practices

### 1. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Something unexpected but handled
- **ERROR**: Serious problem that needs attention
- **CRITICAL**: System failure requiring immediate action

### 2. Include Context

Always include relevant context in your logs:

```python
logger.info("Memory created", extra={
    "memory_id": memory.id,
    "user_id": memory.user_id,
    "memory_type": memory.type,
    "importance": memory.importance
})
```

### 3. Don't Log Sensitive Information

```python
# ❌ BAD
logger.info(f"User authenticated with password: {password}")

# ✅ GOOD  
logger.info("User authenticated", extra={
    "user_id": user.id,
    "auth_method": "password"
})
```

### 4. Use Exception Logging

```python
try:
    dangerous_operation()
except Exception as e:
    logger.exception("Operation failed")  # Includes full traceback
    # or
    logger.error("Operation failed", exc_info=True)
```

## Monitoring Integration

The structured logs can be easily ingested by monitoring systems:

### ELK Stack
```json
{
  "timestamp": "2025-01-22T10:30:15.123Z",
  "level": "ERROR",
  "operation": "memory_synthesis", 
  "duration_ms": 1500,
  "error_type": "DatabaseTimeout"
}
```

### Prometheus Metrics
Performance logs can be converted to metrics:
- `operation_duration_seconds{operation="memory_synthesis"}`
- `operation_errors_total{operation="memory_synthesis"}`

## Migration Priority

### Phase 1: Critical (Immediate)
- Remove all `print()` statements from production code
- Update main application startup/shutdown logging
- Fix exception logging patterns

### Phase 2: High (This Sprint)
- Migrate service layer logging
- Add request context to API endpoints
- Implement performance logging for key operations

### Phase 3: Medium (Next Sprint)
- Migrate utility and helper functions
- Add structured data to business logic logs
- Implement monitoring dashboards

## Testing

### Unit Tests
```python
import logging
from app.utils.logging_config import configure_logging

def test_logging_configuration():
    configure_logging()
    logger = logging.getLogger("test")
    
    with self.assertLogs("test", level="INFO") as cm:
        logger.info("Test message")
    
    self.assertIn("Test message", cm.output[0])
```

### Log Assertion
```python
def test_user_creation_logging(self, caplog):
    with caplog.at_level(logging.INFO):
        create_user(email="test@example.com")
    
    assert "User created" in caplog.text
    assert "test@example.com" in caplog.text
```

## Rollback Plan

If issues arise, the legacy logging system remains available:

```python
# Fallback to legacy logging
from app.utils.logger import logger  # Will show deprecation warning
```

The new system is designed to be backward compatible during the migration period.