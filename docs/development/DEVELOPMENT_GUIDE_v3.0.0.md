# Second Brain v3.0.0 - Development Guide

## Overview

This guide provides practical information for developers working on Second Brain v3.0.0, focusing on what actually works in our current architecture.

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Working with Virtual Environments](#working-with-virtual-environments)
5. [API Development](#api-development)
6. [Database Development](#database-development)
7. [Testing Guidelines](#testing-guidelines)
8. [Docker Development](#docker-development)
9. [Common Development Tasks](#common-development-tasks)
10. [Debugging & Troubleshooting](#debugging--troubleshooting)

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git
- PostgreSQL 16 (or use Docker)
- Redis (or use Docker)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# CRITICAL: Create and use virtual environment
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Install dependencies
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r config/requirements.txt
.venv/Scripts/python.exe -m pip install -r config/requirements-dev.txt

# Setup environment
cp .env.example .env.development
# Edit .env.development with your settings

# Option 1: Use Docker for services
docker-compose up -d postgres redis

# Option 2: Run everything locally
# Start PostgreSQL and Redis manually

# Verify setup
.venv/Scripts/python.exe -m pytest tests/unit/test_health.py -v
```

## Architecture Overview

### Current Architecture (v3.0.0)

```
second-brain/
├── app/                        # Main application code
│   ├── core/                   # Core functionality
│   │   ├── dependencies.py     # Dependency injection
│   │   ├── exceptions.py       # Exception handling
│   │   ├── logging.py          # Logging configuration
│   │   ├── monitoring.py       # Metrics and monitoring
│   │   └── security_audit.py   # Security features
│   ├── models/                 # Data models
│   │   └── memory.py          # Memory model
│   ├── routes/                 # API routes
│   │   ├── health_router.py
│   │   ├── memory_router.py
│   │   └── session_router.py
│   ├── services/              # Business logic
│   │   ├── memory_service.py
│   │   ├── session_service.py
│   │   └── service_factory.py
│   ├── ingestion/             # File ingestion
│   │   ├── engine.py
│   │   └── parsers.py
│   ├── database.py            # Database management
│   ├── database_mock.py       # Mock database for testing
│   └── app.py                 # Main FastAPI application
├── config/                    # Configuration files
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/                      # Documentation
├── scripts/                   # Development scripts
├── tests/                     # Test suite
├── docker-compose.yml         # Docker configuration
└── pytest.ini                 # Test configuration
```

## Project Structure

### Core Components

#### 1. Models (`app/models/`)
```python
# Memory model - the core data structure
from app.models.memory import Memory, MemoryType

memory = Memory(
    content="Important information",
    memory_type=MemoryType.SEMANTIC,
    user_id="user123",
    tags=["important", "work"]
)
```

#### 2. Services (`app/services/`)
Business logic layer that handles operations:
- `MemoryService`: Memory CRUD operations
- `SessionService`: Session management
- `OpenAIService`: AI integrations

#### 3. Routes (`app/routes/`)
API endpoints organized by feature:
- `/health` - Health checks
- `/memories` - Memory operations
- `/sessions` - Session management

#### 4. Core (`app/core/`)
Cross-cutting concerns:
- Exception handling
- Logging and monitoring
- Security features
- Dependency injection

## Working with Virtual Environments

**CRITICAL**: Always use the project's virtual environment to ensure consistency.

### Windows
```bash
# Activate
.venv\Scripts\activate

# Always use full path for Python
.venv\Scripts\python.exe script.py
.venv\Scripts\python.exe -m pip install package
```

### Unix/macOS
```bash
# Activate
source .venv/bin/activate

# Use Python
.venv/bin/python script.py
.venv/bin/python -m pip install package
```

### Why This Matters
- Ensures consistent dependencies across all machines
- Prevents conflicts with system Python
- Makes CI/CD predictable
- Allows easy cleanup and recreation

## API Development

### Creating New Endpoints

1. **Create Route Module** (`app/routes/feature_router.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_service_factory
from app.models.memory import Memory

router = APIRouter(prefix="/api/v1/features", tags=["Features"])

@router.post("/")
async def create_feature(
    data: dict,
    service_factory = Depends(get_service_factory)
):
    """Create a new feature"""
    try:
        service = service_factory.get_feature_service()
        result = await service.create(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

2. **Register Router** (in `app/app.py`):
```python
from app.routes.feature_router import router as feature_router
app.include_router(feature_router)
```

### Request/Response Models

Use Pydantic for validation:
```python
from pydantic import BaseModel, Field

class MemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    memory_type: str = Field(default="semantic")
    tags: list[str] = Field(default_factory=list)

class MemoryResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

## Database Development

### Working with PostgreSQL

The project uses PostgreSQL with pgvector for embeddings:

```python
# Database initialization
from app.database import get_database

db = await get_database()

# Store memory with embedding
memory_id = await db.store_memory(
    content="Important information",
    embedding=[0.1] * 1536,  # OpenAI embedding
    metadata={"source": "manual"}
)

# Vector search
results = await db.search_memories(
    query="find important info",
    limit=10
)
```

### Database Migrations

Currently using SQL scripts. For new tables:

1. Create migration script in `scripts/migrations/`
2. Run manually or via script
3. Document changes

## Testing Guidelines

### Running Tests

```bash
# All tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Specific category
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# With coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=app
```

### Writing Tests

```python
# Unit test example
import pytest
from app.services.memory_service import MemoryService

class TestMemoryService:
    @pytest.fixture
    def service(self):
        return MemoryService(database=mock_db)
    
    async def test_create_memory(self, service):
        result = await service.create("Test content")
        assert result.id is not None
```

## Docker Development

### Development Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: secondbrain
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  app:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/secondbrain
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
```

### Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Rebuild after changes
docker-compose build app
docker-compose up -d app

# Stop everything
docker-compose down
```

## Common Development Tasks

### Adding a New Feature

1. **Create Model** (if needed)
2. **Create Service** with business logic
3. **Create Router** for API endpoints
4. **Add Tests** for each component
5. **Update Documentation**

### Running the Application

```bash
# Development mode with auto-reload
.venv/Scripts/python.exe -m uvicorn app.app:app --reload --host 0.0.0.0 --port 8000

# Production mode
.venv/Scripts/python.exe -m uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

Key environment variables:
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/secondbrain
USE_MOCK_DATABASE=false

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=your-api-key

# Security
API_TOKENS=token1,token2
SECRET_KEY=your-secret-key

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## Debugging & Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Problem: ModuleNotFoundError
# Solution: Ensure you're using .venv Python
.venv/Scripts/python.exe -m pip install -r config/requirements.txt
```

#### 2. Database Connection Failed
```bash
# Check PostgreSQL is running
docker-compose ps

# Check connection string
echo $DATABASE_URL

# Test connection
.venv/Scripts/python.exe -c "from app.database import get_database; import asyncio; asyncio.run(get_database())"
```

#### 3. Async Errors
```python
# Problem: "RuntimeError: This event loop is already running"
# Solution: Use pytest-asyncio for tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
```

### Debugging Tools

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use debugger
import pdb; pdb.set_trace()

# FastAPI debug mode
app = FastAPI(debug=True)
```

### Performance Profiling

```python
# Simple timing
import time
start = time.time()
# ... code ...
print(f"Took {time.time() - start:.2f} seconds")

# Memory profiling
from memory_profiler import profile

@profile
def memory_intensive_function():
    # ... code ...
```

## Best Practices

### 1. Code Style
- Use Black for formatting
- Follow PEP 8
- Type hints where helpful
- Docstrings for public functions

### 2. Error Handling
```python
from app.core.exceptions import NotFoundException, ValidationException

try:
    result = await service.get_memory(memory_id)
except NotFoundException:
    raise HTTPException(status_code=404, detail="Memory not found")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### 3. Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Processing request", extra={"user_id": user_id})
logger.error("Failed to process", exc_info=True)
```

### 4. Security
- Always validate input
- Use parameterized queries
- Sanitize user content
- Keep secrets in environment variables

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [Docker Documentation](https://docs.docker.com/)

---

This development guide focuses on practical, working approaches for Second Brain v3.0.0. Always use the virtual environment and follow established patterns for consistency.