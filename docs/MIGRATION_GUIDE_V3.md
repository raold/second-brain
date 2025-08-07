# Second Brain v3.0.0 Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from Second Brain v2.x to v3.0.0. The migration involves significant architectural changes, including the adoption of clean architecture, event sourcing, and new infrastructure components.

**Estimated Migration Time**: 2-4 hours (depending on data volume)

## Table of Contents

1. [Pre-Migration Checklist](#pre-migration-checklist)
2. [Breaking Changes Summary](#breaking-changes-summary)
3. [Data Migration](#data-migration)
4. [Infrastructure Updates](#infrastructure-updates)
5. [API Migration](#api-migration)
6. [Configuration Changes](#configuration-changes)
7. [Code Migration](#code-migration)
8. [Testing Migration](#testing-migration)
9. [Rollback Plan](#rollback-plan)
10. [Troubleshooting](#troubleshooting)

## Pre-Migration Checklist

Before starting the migration:

- [ ] **Backup your database** (PostgreSQL and Qdrant if used)
- [ ] **Document current configuration** (environment variables, API keys)
- [ ] **Identify custom code** that needs migration
- [ ] **Review breaking changes** in this guide
- [ ] **Set up staging environment** for testing
- [ ] **Notify users** of planned downtime
- [ ] **Prepare rollback plan**

## Breaking Changes Summary

### 1. API Changes
- All endpoints moved under `/api/v1/` prefix
- New authentication mechanism (JWT required)
- Updated request/response formats
- Removed deprecated endpoints

### 2. Database Changes
- Qdrant removed (consolidated on PostgreSQL + pgvector)
- New event sourcing tables
- Updated schema for clean architecture

### 3. Infrastructure Requirements
- Redis (new requirement)
- RabbitMQ (new requirement)
- MinIO or S3 (new requirement)

### 4. Configuration Changes
- New environment variables
- Removed Qdrant configuration
- Updated connection strings

## Data Migration

### Step 1: Export Existing Data

```bash
# 1. Export PostgreSQL data
pg_dump -h localhost -U postgres -d secondbrain > backup_v2.sql

# 2. Export Qdrant data (if used)
python scripts/export_qdrant_data.py > qdrant_backup.json

# 3. Export any file attachments
tar -czf attachments_backup.tar.gz /path/to/attachments/
```

### Step 2: Prepare New Database

```sql
-- Create new database for v3
CREATE DATABASE secondbrain_v3;

-- Enable required extensions
\c secondbrain_v3;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Step 3: Run Migration Scripts

```bash
# 1. Apply v3 schema
alembic upgrade head

# 2. Migrate existing data
python scripts/migrate_v2_to_v3.py \
  --source-db postgresql://user:pass@host/secondbrain \
  --target-db postgresql://user:pass@host/secondbrain_v3 \
  --qdrant-backup qdrant_backup.json
```

### Migration Script Example

```python
# scripts/migrate_v2_to_v3.py
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

async def migrate_memories():
    """Migrate memories from v2 to v3 format."""
    # Connect to v2 database
    v2_engine = create_engine(SOURCE_DB_URL)
    V2Session = sessionmaker(bind=v2_engine)
    
    # Connect to v3 database
    v3_engine = create_engine(TARGET_DB_URL)
    V3Session = sessionmaker(bind=v3_engine)
    
    with V2Session() as v2_session, V3Session() as v3_session:
        # Fetch v2 memories
        v2_memories = v2_session.query(V2Memory).all()
        
        for v2_memory in v2_memories:
            # Create v3 memory with event sourcing
            v3_memory = V3Memory(
                id=v2_memory.id,
                content=v2_memory.content,
                user_id=v2_memory.user_id,
                tags=v2_memory.tags,
                created_at=v2_memory.created_at,
                updated_at=v2_memory.updated_at,
                version=1
            )
            
            # Create initial event
            event = MemoryCreatedEvent(
                event_id=uuid4(),
                aggregate_id=v3_memory.id,
                user_id=v2_memory.user_id,
                content=v2_memory.content,
                occurred_at=v2_memory.created_at
            )
            
            # Save to v3 database
            v3_session.add(v3_memory)
            v3_session.add(event)
        
        v3_session.commit()
        print(f"Migrated {len(v2_memories)} memories")

async def migrate_embeddings():
    """Migrate embeddings from Qdrant to PostgreSQL."""
    # Load Qdrant backup
    with open('qdrant_backup.json', 'r') as f:
        qdrant_data = json.load(f)
    
    # Connect to v3 database
    async with get_db_session() as session:
        for point in qdrant_data['points']:
            # Update memory with embedding
            memory = await session.get(Memory, point['payload']['memory_id'])
            if memory:
                memory.embedding = point['vector']
                await session.commit()
```

## Infrastructure Updates

### Step 1: Install New Services

#### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:v0.5.1-pg16
    environment:
      POSTGRES_DB: secondbrain_v3
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
```

#### Manual Installation

```bash
# PostgreSQL with pgvector
sudo apt install postgresql-16 postgresql-16-pgvector

# Redis
sudo apt install redis-server

# RabbitMQ
sudo apt install rabbitmq-server

# MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /data
```

### Step 2: Update Network Configuration

```bash
# Update firewall rules
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis
sudo ufw allow 5672/tcp  # RabbitMQ
sudo ufw allow 9000/tcp  # MinIO
```

## API Migration

### Step 1: Update API Endpoints

```python
# Old API client
response = requests.get('http://api.example.com/memories')

# New API client
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://api.example.com/api/v1/memories', headers=headers)
```

### Step 2: Update Authentication

```python
# Get authentication token
def get_auth_token(username: str, password: str) -> str:
    response = requests.post(
        'http://api.example.com/api/v1/auth/token',
        json={'username': username, 'password': password}
    )
    return response.json()['access_token']

# Use token in requests
token = get_auth_token('user@example.com', 'password')
headers = {'Authorization': f'Bearer {token}'}
```

### Step 3: Update Request Formats

```python
# Old format
memory_data = {
    'text': 'Memory content',
    'user': 'user_id'
}

# New format
memory_data = {
    'content': 'Memory content',
    'tags': ['tag1', 'tag2'],
    'metadata': {'source': 'api'}
}
```

## Configuration Changes

### Step 1: Update Environment Variables

Create new `.env` file:

```bash
# Database (updated)
DATABASE_URL=postgresql://user:password@localhost:5432/secondbrain_v3

# New services
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=secondbrain

# API Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600

# OpenAI (unchanged)
OPENAI_API_KEY=your-openai-key

# Observability (new)
OTEL_SERVICE_NAME=secondbrain
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
PROMETHEUS_PORT=9090

# Remove these old variables
# QDRANT_URL=...
# QDRANT_API_KEY=...
```

### Step 2: Update Configuration Files

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # New services
    redis_url: str
    rabbitmq_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    
    # Removed
    # qdrant_url: str
    # qdrant_api_key: str
    
    class Config:
        env_file = ".env"
```

## Code Migration

### Step 1: Update Import Paths

```python
# Old imports
from app.models import Memory
from app.services import MemoryService

# New imports
from src.domain.models.memory import Memory
from src.application.use_cases.memory_use_cases import CreateMemoryUseCase
```

### Step 2: Update Service Layer

```python
# Old service pattern
class MemoryService:
    def create_memory(self, text: str, user_id: str):
        memory = Memory(text=text, user_id=user_id)
        self.db.save(memory)
        return memory

# New use case pattern
class CreateMemoryUseCase:
    def __init__(self, repository: MemoryRepository, publisher: EventPublisher):
        self.repository = repository
        self.publisher = publisher
    
    async def execute(self, content: str, user_id: UUID) -> Memory:
        memory = Memory.create(content=content, user_id=user_id)
        await self.repository.save(memory)
        await self.publisher.publish(memory.collect_events())
        return memory
```

### Step 3: Update API Routes

```python
# Old route
@app.post("/memories")
def create_memory(text: str, user_id: str = Depends(get_current_user)):
    return memory_service.create_memory(text, user_id)

# New route
@router.post("/api/v1/memories", response_model=MemoryResponse)
async def create_memory(
    request: CreateMemoryRequest,
    current_user: User = Depends(get_current_user),
    use_case: CreateMemoryUseCase = Depends(get_create_memory_use_case)
) -> MemoryResponse:
    memory = await use_case.execute(
        content=request.content,
        user_id=current_user.id,
        tags=request.tags
    )
    return MemoryResponse.from_domain(memory)
```

## Testing Migration

### Step 1: Update Test Configuration

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("ankane/pgvector:v0.5.1-pg16") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis
```

### Step 2: Update Test Cases

```python
# Old test
def test_create_memory():
    memory = Memory(text="Test", user_id="123")
    assert memory.text == "Test"

# New test
def test_create_memory():
    memory = Memory.create(
        content="Test",
        user_id=uuid4(),
        tags=["test"]
    )
    assert memory.content == "Test"
    assert len(memory._events) == 1
    assert memory._events[0].event_type == "memory.created"
```

## Rollback Plan

If migration fails, follow these steps:

### Step 1: Stop v3 Services

```bash
docker-compose down
```

### Step 2: Restore v2 Database

```bash
# Restore PostgreSQL
psql -h localhost -U postgres -d secondbrain < backup_v2.sql

# Restore Qdrant (if used)
python scripts/restore_qdrant_data.py < qdrant_backup.json
```

### Step 3: Revert Code

```bash
git checkout v2.8.3
```

### Step 4: Restart v2 Services

```bash
docker-compose -f docker-compose.v2.yml up -d
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Problem**: Cannot connect to PostgreSQL with pgvector
```
psycopg2.errors.UndefinedFile: could not open extension control file
```

**Solution**:
```sql
CREATE EXTENSION vector;
```

#### 2. Redis Connection Timeout

**Problem**: Redis connection timeout
```
redis.exceptions.ConnectionError: Error -2 connecting to localhost:6379
```

**Solution**:
```bash
# Check Redis status
sudo systemctl status redis
sudo systemctl start redis
```

#### 3. Migration Script Failures

**Problem**: Migration script fails with foreign key constraint
```
sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed
```

**Solution**:
```python
# Disable foreign key checks during migration
with engine.begin() as conn:
    conn.execute("SET session_replication_role = 'replica';")
    # Run migration
    conn.execute("SET session_replication_role = 'origin';")
```

#### 4. API Authentication Issues

**Problem**: 401 Unauthorized errors
```
{"detail": "Could not validate credentials"}
```

**Solution**:
```python
# Ensure JWT secret is set
export JWT_SECRET_KEY="your-secret-key"

# Check token expiration
jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

### Performance Issues

If experiencing performance degradation after migration:

1. **Rebuild indexes**:
   ```sql
   REINDEX DATABASE secondbrain_v3;
   ```

2. **Analyze tables**:
   ```sql
   ANALYZE;
   ```

3. **Check pgvector settings**:
   ```sql
   SET ivfflat.probes = 10;
   ```

4. **Monitor with explain**:
   ```sql
   EXPLAIN ANALYZE SELECT ...;
   ```

## Post-Migration Tasks

After successful migration:

1. **Monitor system health**
   - Check API response times
   - Monitor error rates
   - Verify data integrity

2. **Update documentation**
   - API documentation
   - Internal wikis
   - Client libraries

3. **Train team**
   - New architecture
   - Debugging procedures
   - Deployment process

4. **Clean up**
   - Remove old Qdrant data
   - Archive v2 backups
   - Update CI/CD pipelines

## Support

If you encounter issues during migration:

1. Check [GitHub Issues](https://github.com/yourusername/second-brain/issues)
2. Join [Discord Community](https://discord.gg/secondbrain)
3. Review [FAQ](https://docs.secondbrain.ai/faq)
4. Contact support@secondbrain.ai

---

**Remember**: Always test the migration in a staging environment before applying to production!