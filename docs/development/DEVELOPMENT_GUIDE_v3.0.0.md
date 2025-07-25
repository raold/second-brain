# Second Brain v3.0.0 - Development Guide

## Overview

This guide provides comprehensive information for developers working on Second Brain v3.0.0, covering architecture, coding standards, testing practices, and development workflows.

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Architecture Overview](#architecture-overview)
3. [Coding Standards](#coding-standards)
4. [Testing Guidelines](#testing-guidelines)
5. [Database Development](#database-development)
6. [API Development](#api-development)
7. [Domain Modeling](#domain-modeling)
8. [Event-Driven Development](#event-driven-development)
9. [Performance Optimization](#performance-optimization)
10. [Debugging & Troubleshooting](#debugging--troubleshooting)

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- Your favorite IDE (VS Code, PyCharm recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-v3.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Copy environment configuration
cp .env.example .env.development
# Edit .env.development with your settings

# Start infrastructure services
docker-compose -f docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Verify setup
pytest tests/unit/test_health.py -v
```

### IDE Configuration

#### VS Code

`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": false,
  "python.formatting.provider": "black",
  "python.linting.mypyEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.envFile": "${workspaceFolder}/.env.development"
}
```

#### PyCharm

1. Set Python interpreter to virtual environment
2. Enable Black formatter
3. Configure pytest as test runner
4. Set environment variables from `.env.development`

## Architecture Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│              API Layer                  │
│  (FastAPI routes, middleware, auth)     │
├─────────────────────────────────────────┤
│          Application Layer              │
│    (Use cases, DTOs, services)         │
├─────────────────────────────────────────┤
│            Domain Layer                 │
│ (Entities, value objects, events)      │
├─────────────────────────────────────────┤
│        Infrastructure Layer             │
│ (Database, cache, external services)    │
└─────────────────────────────────────────┘
```

### Dependency Rules

1. **Dependencies point inward**: Outer layers depend on inner layers
2. **Domain has no dependencies**: Pure business logic
3. **Infrastructure implements interfaces**: Defined by domain/application
4. **API orchestrates**: Calls use cases, returns responses

## Coding Standards

### Python Style Guide

Follow PEP 8 with these additions:

```python
# Class naming
class MemoryAggregate:  # PascalCase for classes
    pass

# Function naming
def calculate_memory_score():  # snake_case for functions
    pass

# Constants
DEFAULT_MEMORY_TTL = 3600  # UPPER_CASE for constants

# Private methods
def _internal_helper():  # Leading underscore for private
    pass
```

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict, Union
from uuid import UUID
from datetime import datetime

def search_memories(
    query: str,
    user_id: UUID,
    limit: int = 10,
    tags: Optional[List[str]] = None
) -> List[Memory]:
    """Search memories with vector similarity."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def create_memory(content: str, user_id: UUID) -> Memory:
    """Create a new memory with embeddings.
    
    Args:
        content: The memory content text
        user_id: ID of the user creating the memory
        
    Returns:
        The created Memory object
        
    Raises:
        ValidationError: If content is empty
        UserNotFoundError: If user doesn't exist
    """
    ...
```

### Error Handling

```python
# Define custom exceptions
class DomainError(Exception):
    """Base exception for domain errors."""
    pass

class MemoryNotFoundError(DomainError):
    """Raised when memory is not found."""
    def __init__(self, memory_id: UUID):
        self.memory_id = memory_id
        super().__init__(f"Memory {memory_id} not found")

# Use specific error handling
try:
    memory = await repository.get(memory_id)
except MemoryNotFoundError:
    raise HTTPException(status_code=404, detail="Memory not found")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/               # Fast, isolated tests
│   ├── domain/        # Domain logic tests
│   ├── application/   # Use case tests
│   └── api/          # Route tests
├── integration/       # Tests with real services
│   ├── database/     # Database integration
│   ├── cache/        # Redis integration
│   └── messaging/    # RabbitMQ integration
├── e2e/              # End-to-end scenarios
└── fixtures/         # Test data and mocks
```

### Writing Unit Tests

```python
# tests/unit/domain/test_memory.py
import pytest
from uuid import uuid4
from src.domain.models.memory import Memory
from src.domain.events.memory_events import MemoryCreatedEvent

class TestMemory:
    def test_create_memory(self):
        """Test memory creation with valid data."""
        # Arrange
        content = "Test memory content"
        user_id = uuid4()
        
        # Act
        memory = Memory.create(content=content, user_id=user_id)
        
        # Assert
        assert memory.content == content
        assert memory.user_id == user_id
        assert len(memory.events) == 1
        assert isinstance(memory.events[0], MemoryCreatedEvent)
    
    def test_create_memory_empty_content(self):
        """Test memory creation with empty content."""
        # Arrange
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Memory.create(content="", user_id=user_id)
```

### Writing Integration Tests

```python
# tests/integration/database/test_memory_repository.py
import pytest
from uuid import uuid4
from src.domain.models.memory import Memory
from src.infrastructure.database.repositories.memory_repository import SQLMemoryRepository

@pytest.mark.asyncio
class TestMemoryRepository:
    async def test_save_and_retrieve(self, db_session):
        """Test saving and retrieving a memory."""
        # Arrange
        repository = SQLMemoryRepository(db_session)
        memory = Memory.create(
            content="Integration test memory",
            user_id=uuid4()
        )
        
        # Act
        saved_memory = await repository.save(memory)
        retrieved_memory = await repository.find_by_id(saved_memory.id)
        
        # Assert
        assert retrieved_memory is not None
        assert retrieved_memory.id == saved_memory.id
        assert retrieved_memory.content == memory.content
```

### Test Fixtures

```python
# tests/fixtures/factories.py
import factory
from factory import Faker, SubFactory
from uuid import uuid4
from src.domain.models.memory import Memory
from src.domain.models.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.LazyFunction(uuid4)
    email = Faker('email')
    name = Faker('name')

class MemoryFactory(factory.Factory):
    class Meta:
        model = Memory
    
    id = factory.LazyFunction(uuid4)
    content = Faker('text')
    user_id = factory.LazyFunction(uuid4)
    tags = factory.List([Faker('word') for _ in range(3)])
```

### Testing Best Practices

1. **Test behavior, not implementation**
2. **Use descriptive test names**
3. **Follow AAA pattern**: Arrange, Act, Assert
4. **One assertion per test** (when practical)
5. **Use fixtures for complex setup**
6. **Mock external dependencies**
7. **Test edge cases and errors**

## Database Development

### Migration Management

```bash
# Create new migration
alembic revision -m "add_user_preferences_table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Migration Best Practices

```python
# migrations/versions/001_add_user_preferences.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'user_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('theme', sa.String(50), default='light'),
        sa.Column('notifications_enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])

def downgrade():
    op.drop_index('idx_user_preferences_user_id')
    op.drop_table('user_preferences')
```

### Query Optimization

```python
# Use query explanation
from sqlalchemy import text

async def analyze_query(session, query):
    result = await session.execute(
        text(f"EXPLAIN ANALYZE {query}")
    )
    return result.fetchall()

# Optimize vector searches
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

# Use appropriate indexes
CREATE INDEX idx_memories_user_created 
ON memories(user_id, created_at DESC)
WHERE deleted_at IS NULL;
```

## API Development

### Route Structure

```python
# src/api/routes/memories.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from src.api.dependencies import get_current_user, get_memory_use_case
from src.application.dto.memory_dto import MemoryCreateDTO, MemoryResponseDTO
from src.application.use_cases.memory_use_cases import CreateMemoryUseCase

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])

@router.post(
    "/",
    response_model=MemoryResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
    description="Create a new memory with automatic embedding generation"
)
async def create_memory(
    request: MemoryCreateDTO,
    current_user: User = Depends(get_current_user),
    use_case: CreateMemoryUseCase = Depends(get_memory_use_case)
) -> MemoryResponseDTO:
    """Create a new memory."""
    try:
        memory = await use_case.execute(
            content=request.content,
            user_id=current_user.id,
            tags=request.tags,
            metadata=request.metadata
        )
        return MemoryResponseDTO.from_domain(memory)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### Request Validation

```python
# src/application/dto/memory_dto.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class MemoryCreateDTO(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    tags: Optional[List[str]] = Field(default_factory=list, max_items=10)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()
    
    @validator('tags')
    def normalize_tags(cls, v):
        if v:
            return [tag.lower().strip() for tag in v if tag.strip()]
        return []
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Important meeting notes from team standup",
                "tags": ["work", "meetings", "important"],
                "metadata": {"source": "manual", "priority": "high"}
            }
        }
```

### Middleware

```python
# src/api/middleware.py
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.infrastructure.observability.tracing import trace

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        with trace("http_request") as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("request.method", request.method)
            span.set_attribute("request.path", request.url.path)
            
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            
            span.set_attribute("response.status_code", response.status_code)
            span.set_attribute("response.duration", duration)
            
        return response
```

## Domain Modeling

### Aggregate Design

```python
# src/domain/models/memory.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from src.domain.events.base import DomainEvent
from src.domain.events.memory_events import (
    MemoryCreatedEvent,
    MemoryUpdatedEvent,
    MemoryTaggedEvent
)

@dataclass
class Memory:
    """Memory aggregate root."""
    
    id: UUID
    content: str
    embedding: Optional[List[float]]
    user_id: UUID
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int
    _events: List[DomainEvent] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        content: str,
        user_id: UUID,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Memory':
        """Create a new memory."""
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        
        memory_id = uuid4()
        now = datetime.utcnow()
        
        memory = cls(
            id=memory_id,
            content=content.strip(),
            embedding=None,  # Will be generated asynchronously
            user_id=user_id,
            tags=tags or [],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
            version=1,
            _events=[]
        )
        
        # Record domain event
        event = MemoryCreatedEvent(
            aggregate_id=memory_id,
            content=content,
            user_id=user_id,
            tags=tags or [],
            metadata=metadata or {},
            occurred_at=now
        )
        memory._record_event(event)
        
        return memory
    
    def update_content(self, new_content: str) -> None:
        """Update memory content."""
        if not new_content or not new_content.strip():
            raise ValueError("Content cannot be empty")
        
        old_content = self.content
        self.content = new_content.strip()
        self.updated_at = datetime.utcnow()
        self.version += 1
        
        # Clear embedding - needs regeneration
        self.embedding = None
        
        event = MemoryUpdatedEvent(
            aggregate_id=self.id,
            old_content=old_content,
            new_content=self.content,
            occurred_at=self.updated_at
        )
        self._record_event(event)
    
    def add_tags(self, tags: List[str]) -> None:
        """Add tags to memory."""
        new_tags = [tag.lower().strip() for tag in tags if tag.strip()]
        added_tags = list(set(new_tags) - set(self.tags))
        
        if added_tags:
            self.tags.extend(added_tags)
            self.updated_at = datetime.utcnow()
            self.version += 1
            
            event = MemoryTaggedEvent(
                aggregate_id=self.id,
                added_tags=added_tags,
                all_tags=self.tags,
                occurred_at=self.updated_at
            )
            self._record_event(event)
    
    def _record_event(self, event: DomainEvent) -> None:
        """Record a domain event."""
        self._events.append(event)
    
    def collect_events(self) -> List[DomainEvent]:
        """Collect and clear recorded events."""
        events = self._events.copy()
        self._events.clear()
        return events
```

### Value Objects

```python
# src/domain/models/tag.py
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Tag:
    """Tag value object."""
    
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Tag cannot be empty")
        
        # Normalize tag
        normalized = self.value.lower().strip()
        
        # Validate format
        if not re.match(r'^[a-z0-9-]+$', normalized):
            raise ValueError("Tag can only contain lowercase letters, numbers, and hyphens")
        
        if len(normalized) > 50:
            raise ValueError("Tag cannot exceed 50 characters")
        
        # Use object.__setattr__ since dataclass is frozen
        object.__setattr__(self, 'value', normalized)
    
    def __str__(self) -> str:
        return self.value
```

## Event-Driven Development

### Domain Events

```python
# src/domain/events/memory_events.py
from dataclasses import dataclass
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from src.domain.events.base import DomainEvent

@dataclass
class MemoryCreatedEvent(DomainEvent):
    """Event raised when a memory is created."""
    
    aggregate_id: UUID
    content: str
    user_id: UUID
    tags: List[str]
    metadata: Dict[str, Any]
    occurred_at: datetime
    
    @property
    def event_type(self) -> str:
        return "memory.created"
```

### Event Handlers

```python
# src/infrastructure/messaging/handlers.py
from typing import Dict, Any
import logging

from src.domain.events.memory_events import MemoryCreatedEvent
from src.infrastructure.embeddings.client import EmbeddingClient
from src.infrastructure.caching.cache import Cache

logger = logging.getLogger(__name__)

class MemoryCreatedHandler:
    """Handle memory created events."""
    
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        memory_repository: MemoryRepository,
        cache: Cache
    ):
        self.embedding_client = embedding_client
        self.memory_repository = memory_repository
        self.cache = cache
    
    async def handle(self, event_data: Dict[str, Any]) -> None:
        """Process memory created event."""
        try:
            # Generate embedding
            embedding = await self.embedding_client.generate_embedding(
                event_data['content']
            )
            
            # Update memory with embedding
            memory = await self.memory_repository.find_by_id(
                event_data['aggregate_id']
            )
            if memory:
                memory.embedding = embedding
                await self.memory_repository.save(memory)
                
                # Invalidate cache
                await self.cache.delete(f"memory:{memory.id}")
                
                logger.info(f"Processed embedding for memory {memory.id}")
            
        except Exception as e:
            logger.error(f"Error processing memory created event: {e}")
            raise
```

### Event Publisher

```python
# src/infrastructure/messaging/publisher.py
import json
from typing import List
from src.domain.events.base import DomainEvent
from src.infrastructure.messaging.broker import MessageBroker

class EventPublisher:
    """Publish domain events to message broker."""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
    
    async def publish(self, events: List[DomainEvent]) -> None:
        """Publish a list of domain events."""
        for event in events:
            await self.publish_event(event)
    
    async def publish_event(self, event: DomainEvent) -> None:
        """Publish a single domain event."""
        routing_key = f"domain.{event.event_type}"
        message = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "aggregate_id": str(event.aggregate_id),
            "occurred_at": event.occurred_at.isoformat(),
            "data": event.to_dict()
        }
        
        await self.broker.publish(
            routing_key=routing_key,
            message=message,
            persistent=True
        )
```

## Performance Optimization

### Query Optimization

```python
# Use select_related for foreign keys
memories = await session.execute(
    select(Memory)
    .options(selectinload(Memory.user))
    .where(Memory.user_id == user_id)
    .order_by(Memory.created_at.desc())
    .limit(10)
)

# Use indexes effectively
CREATE INDEX idx_memories_user_created 
ON memories(user_id, created_at DESC)
WHERE deleted_at IS NULL;

# Optimize vector searches
CREATE INDEX ON memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Caching Strategies

```python
# src/application/use_cases/memory_use_cases.py
from src.infrastructure.caching.decorators import cache_aside, cache_invalidate

class GetMemoryUseCase:
    @cache_aside(key="memory:{memory_id}", ttl=300)
    async def execute(self, memory_id: UUID) -> Memory:
        """Get memory with caching."""
        memory = await self.memory_repository.find_by_id(memory_id)
        if not memory:
            raise MemoryNotFoundError(memory_id)
        return memory

class UpdateMemoryUseCase:
    @cache_invalidate(pattern="memory:{memory_id}")
    async def execute(self, memory_id: UUID, content: str) -> Memory:
        """Update memory and invalidate cache."""
        memory = await self.memory_repository.find_by_id(memory_id)
        if not memory:
            raise MemoryNotFoundError(memory_id)
        
        memory.update_content(content)
        await self.memory_repository.save(memory)
        await self.event_publisher.publish(memory.collect_events())
        
        return memory
```

### Async Best Practices

```python
# Use asyncio.gather for parallel operations
import asyncio

async def get_user_dashboard(user_id: UUID):
    # Run queries in parallel
    memories_task = get_recent_memories(user_id)
    stats_task = get_user_stats(user_id)
    tags_task = get_user_tags(user_id)
    
    memories, stats, tags = await asyncio.gather(
        memories_task,
        stats_task,
        tags_task
    )
    
    return {
        "memories": memories,
        "stats": stats,
        "tags": tags
    }

# Use connection pooling
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Debugging & Troubleshooting

### Logging Configuration

```python
# src/infrastructure/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(level=logging.INFO)
formatter = JSONFormatter()

for handler in logging.root.handlers:
    handler.setFormatter(formatter)
```

### Debug Tools

```python
# Use debugpy for remote debugging
import debugpy

if os.getenv("DEBUG_MODE") == "true":
    debugpy.listen(("0.0.0.0", 5678))
    print("Waiting for debugger attach...")
    debugpy.wait_for_client()

# Profile performance
import cProfile
import pstats

def profile_function(func):
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats(20)
        
        return result
    return wrapper

# Memory profiling
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Function code
    pass
```

### Common Issues

1. **Circular Imports**
   - Use TYPE_CHECKING for type hints
   - Lazy imports in functions
   - Proper module organization

2. **Database Connection Issues**
   ```python
   # Check connection health
   async def check_db_health(session):
       try:
           await session.execute(text("SELECT 1"))
           return True
       except Exception as e:
           logger.error(f"Database health check failed: {e}")
           return False
   ```

3. **Memory Leaks**
   - Close connections properly
   - Clear event listeners
   - Use weak references where appropriate

4. **Performance Issues**
   - Enable query logging
   - Use EXPLAIN ANALYZE
   - Profile hot paths
   - Monitor connection pools

## Best Practices Summary

1. **Follow Clean Architecture**: Keep domain logic pure
2. **Write Tests First**: TDD for critical logic
3. **Use Type Hints**: Everywhere, no exceptions
4. **Handle Errors Gracefully**: Specific exceptions, proper logging
5. **Document Complex Logic**: Clear docstrings and comments
6. **Optimize Later**: Measure first, optimize based on data
7. **Keep It Simple**: Avoid over-engineering
8. **Review Your Code**: Self-review before PR

## Additional Resources

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [PostgreSQL Optimization](https://wiki.postgresql.org/wiki/Performance_Optimization)