# CI/CD Troubleshooting Guide - Second Brain v3.0.0

## Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Stage-Specific Failures](#stage-specific-failures)
3. [Common Error Patterns](#common-error-patterns)
4. [Environment Issues](#environment-issues)
5. [Performance Problems](#performance-problems)
6. [Advanced Debugging](#advanced-debugging)
7. [Recovery Procedures](#recovery-procedures)

---

## Quick Diagnosis

### 🚨 Emergency Triage (< 2 minutes)

Use this flowchart to quickly identify the problem category:

```mermaid
flowchart TD
    A[CI Pipeline Failed] --> B{Which Stage Failed?}
    
    B -->|Smoke Tests| C[🔥 CRITICAL: Basic System Broken]
    B -->|Fast Feedback| D[⚡ WARNING: Core Features Affected]
    B -->|Comprehensive| E[🔍 BLOCKING: Deployment Issues]
    B -->|Performance| F[📊 INFO: Performance Regression]
    
    C --> G[Fix Immediately - Pipeline Blocked]
    D --> H[Fix Soon - Development Impacted]
    E --> I[Fix Before Merge - Deployment Blocked]
    F --> J[Investigate - Non-blocking]
    
    G --> K[Check Environment/Imports/Health]
    H --> L[Check Unit/Integration/API Tests]
    I --> M[Check Security/Database/E2E]
    J --> N[Check Benchmarks/Load/Memory]
```

### 🔍 Quick Commands for Diagnosis

```bash
# 1. Check what failed (< 30 seconds)
make test-smoke 2>&1 | grep -E "(FAIL|ERROR|BLOCK)"

# 2. Get detailed error for specific stage
python scripts/ci_runner.py --stage smoke --save-report debug.json
cat debug.json | jq '.stages[].tests[] | select(.status=="FAIL")'

# 3. Check environment issues
python scripts/validate_environment.py

# 4. Check service status
docker-compose ps
docker-compose logs --tail=50 postgres redis

# 5. Test basic connectivity
python -c "import app.app; print('✅ Imports OK')"
python -c "from app.database import get_database; print('✅ Database OK')"
```

### 📊 Error Severity Classification

| Severity | Impact | Response Time | Examples |
|----------|---------|---------------|----------|
| **🚨 CRITICAL** | Pipeline blocked, all development stopped | Immediate (< 1 hour) | Import errors, database down, health endpoint failing |
| **⚠️ HIGH** | Deployment blocked, PR cannot merge | Same day (< 8 hours) | Security vulnerabilities, critical test failures |
| **📋 MEDIUM** | Development impacted, warnings generated | Next day (< 24 hours) | Integration test failures, performance degradations |
| **💡 LOW** | Informational, monitoring alerts | Next sprint (< 1 week) | Flaky tests, documentation issues |

---

## Stage-Specific Failures

### 🔥 Smoke Test Failures (CRITICAL)

Smoke test failures stop the entire pipeline. These are the most serious issues.

#### Import/Module Errors

**Symptom**:
```
❌ ImportError: cannot import name 'ServiceFactory' from 'app.services'
❌ ModuleNotFoundError: No module named 'app.core.dependencies'
```

**Immediate Diagnosis**:
```bash
# Test imports directly
python -c "import app.services.service_factory"
python -c "from app.core.dependencies import get_database"

# Check Python path
echo $PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"

# Verify file exists
ls -la app/services/service_factory.py
ls -la app/core/dependencies.py
```

**Common Causes & Fixes**:

1. **Missing `__init__.py` files**:
   ```bash
   # Find missing __init__.py files
   find app/ -type d -exec test ! -f "{}/__init__.py" \; -print
   
   # Fix: Create missing __init__.py files
   find app/ -type d -exec touch "{}/__init__.py" \;
   ```

2. **Circular imports**:
   ```bash
   # Find circular imports
   python -c "
   import ast, os
   def find_imports(file):
       with open(file) as f:
           tree = ast.parse(f.read())
       return [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
   
   for root, dirs, files in os.walk('app'):
       for file in files:
           if file.endswith('.py'):
               path = os.path.join(root, file)
               try:
                   imports = find_imports(path)
                   print(f'{path}: {imports}')
               except: pass
   "
   ```

3. **PYTHONPATH issues**:
   ```bash
   # Fix PYTHONPATH
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   
   # Permanent fix in pytest.ini:
   [tool:pytest]
   pythonpath = .
   ```

#### Database Connection Failures

**Symptom**:
```
❌ psycopg2.OperationalError: connection to server at "localhost", port 5432 failed
❌ Could not connect to Redis at localhost:6379
```

**Immediate Diagnosis**:
```bash
# Check if services are running
docker-compose ps

# Check service logs
docker-compose logs postgres
docker-compose logs redis

# Test connectivity
nc -zv localhost 5432  # PostgreSQL
nc -zv localhost 6379  # Redis

# Manual connection test
docker-compose exec postgres psql -U secondbrain -c "SELECT 1;"
docker-compose exec redis redis-cli ping
```

**Common Causes & Fixes**:

1. **Services not started**:
   ```bash
   # Start services
   docker-compose up -d postgres redis
   
   # Wait for services to be ready
   docker-compose exec postgres pg_isready -U secondbrain
   docker-compose exec redis redis-cli ping
   ```

2. **Services starting slowly**:
   ```bash
   # Add health check wait
   timeout 60 bash -c 'until docker-compose exec postgres pg_isready -U secondbrain; do sleep 2; done'
   timeout 30 bash -c 'until docker-compose exec redis redis-cli ping; do sleep 1; done'
   ```

3. **Port conflicts**:
   ```bash
   # Check what's using the ports
   lsof -i :5432
   lsof -i :6379
   
   # Use different ports in docker-compose.yml
   services:
     postgres:
       ports:
         - "5433:5432"  # Use 5433 instead of 5432
   ```

#### Health Endpoint Failures

**Symptom**:
```
❌ Health check failed: GET http://localhost:8000/health -> 500 Internal Server Error
❌ Application startup failed
```

**Immediate Diagnosis**:
```bash
# Test application startup manually
python app/app.py

# Check for startup errors
python -c "
from app.app import create_app
try:
    app = create_app()
    print('✅ App creation successful')
except Exception as e:
    print(f'❌ App creation failed: {e}')
"

# Test health endpoint directly
curl -v http://localhost:8000/health
```

**Common Causes & Fixes**:

1. **Configuration errors**:
   ```bash
   # Check environment variables
   env | grep -E "(DATABASE_URL|REDIS_URL|OPENAI_API_KEY)"
   
   # Validate configuration
   python -c "
   from app.config import settings
   print('Database URL:', settings.database_url)
   print('Redis URL:', settings.redis_url)
   "
   ```

2. **Database migration issues**:
   ```bash
   # Check migration status
   docker-compose run --rm app alembic current
   
   # Run migrations
   docker-compose run --rm app alembic upgrade head
   ```

### ⚡ Fast Feedback Failures (HIGH PRIORITY)

Fast feedback failures indicate core functionality problems but don't stop the pipeline completely.

#### Unit Test Failures

**Symptom**:
```
❌ tests/unit/test_memory_service.py::test_create_memory FAILED
❌ AssertionError: Expected memory.id to be not None
```

**Immediate Diagnosis**:
```bash
# Run the specific failing test with verbose output
python -m pytest tests/unit/test_memory_service.py::test_create_memory -v -s

# Run with debugging
python -m pytest tests/unit/test_memory_service.py::test_create_memory -v -s --pdb

# Check test dependencies and fixtures
python -m pytest tests/unit/test_memory_service.py -v --setup-show
```

**Common Causes & Fixes**:

1. **Test isolation issues**:
   ```python
   # Problem: Tests affecting each other
   def test_create_memory():
       memory = create_memory_service().create(data)
       assert memory.id is not None  # Fails if previous test created same memory
   
   # Fix: Proper test isolation
   @pytest.fixture(autouse=True)
   async def reset_database():
       await database.truncate_all_tables()
       yield
       # Cleanup happens automatically
   ```

2. **Mock configuration problems**:
   ```python
   # Problem: Mock not configured correctly
   @patch('app.services.openai_client.OpenAIClient')
   def test_embedding_generation(mock_openai):
       # Mock not configured - returns MagicMock instead of expected data
       result = embedding_service.generate("test")
       assert len(result) == 1536  # Fails
   
   # Fix: Proper mock configuration
   @patch('app.services.openai_client.OpenAIClient')
   def test_embedding_generation(mock_openai):
       mock_openai.return_value.generate_embedding.return_value = [0.1] * 1536
       result = embedding_service.generate("test")
       assert len(result) == 1536  # Passes
   ```

3. **Async/await issues**:
   ```python
   # Problem: Missing await
   async def test_async_operation():
       result = async_service.process()  # Missing await
       assert result.status == "success"  # Fails - result is coroutine
   
   # Fix: Proper async handling
   async def test_async_operation():
       result = await async_service.process()
       assert result.status == "success"  # Passes
   ```

#### Integration Test Failures

**Symptom**:
```
❌ tests/integration/test_api_endpoints.py::test_create_memory_endpoint FAILED
❌ 422 Unprocessable Entity: Invalid input data
```

**Immediate Diagnosis**:
```bash
# Test the API endpoint directly
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{"title":"test","content":"test content"}'

# Check API documentation/schema
python -c "
from app.app import create_app
app = create_app()
print(app.openapi())
" | jq '.paths["/api/memories"]'

# Run integration tests with database
python -m pytest tests/integration/test_api_endpoints.py -v --setup-show
```

**Common Causes & Fixes**:

1. **Database not properly seeded**:
   ```python
   # Problem: Test expects data that doesn't exist
   def test_get_memory():
       response = client.get("/api/memories/123")
       assert response.status_code == 200  # Fails - memory 123 doesn't exist
   
   # Fix: Proper test data setup
   @pytest.fixture
   async def sample_memory():
       memory_data = {"title": "Test", "content": "Test content"}
       memory = await memory_service.create(memory_data)
       return memory
   
   def test_get_memory(sample_memory):
       response = client.get(f"/api/memories/{sample_memory.id}")
       assert response.status_code == 200  # Passes
   ```

2. **Service dependency issues**:
   ```python
   # Problem: Service not properly injected
   @router.post("/memories")
   async def create_memory(data: MemoryCreate):
       service = MemoryService()  # Hard-coded dependency
       return await service.create(data)
   
   # Fix: Proper dependency injection
   @router.post("/memories")
   async def create_memory(
       data: MemoryCreate,
       service: MemoryService = Depends(get_memory_service)
   ):
       return await service.create(data)
   ```

### 🔍 Comprehensive Test Failures (BLOCKING)

Comprehensive test failures block deployment and usually indicate serious integration or security issues.

#### Security Test Failures

**Symptom**:
```
❌ Security vulnerability detected: SQL Injection risk
❌ bandit: High severity issue found in app/database.py
```

**Immediate Diagnosis**:
```bash
# Run security scans manually
python -m bandit -r app/ -f json

# Check for SQL injection patterns
grep -r "f\".*{.*}.*\"" app/ | grep -i sql

# Check for hardcoded secrets
python -m trufflehog filesystem app/

# Dependency vulnerability scan
python -m safety check
```

**Common Causes & Fixes**:

1. **SQL injection vulnerabilities**:
   ```python
   # Problem: String formatting in SQL
   def get_user_by_name(name):
       query = f"SELECT * FROM users WHERE name = '{name}'"  # Vulnerable
       return database.execute(query)
   
   # Fix: Parameterized queries
   def get_user_by_name(name):
       query = "SELECT * FROM users WHERE name = %s"
       return database.execute(query, (name,))
   ```

2. **Hardcoded secrets**:
   ```python
   # Problem: Hardcoded API key
   OPENAI_API_KEY = "sk-1234567890abcdef"  # Vulnerable
   
   # Fix: Environment variable
   OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
   if not OPENAI_API_KEY:
       raise ValueError("OPENAI_API_KEY environment variable required")
   ```

#### Database Migration Failures

**Symptom**:
```
❌ alembic.util.exc.CommandError: Target database is not up to date
❌ psycopg2.errors.DuplicateTable: relation "memories" already exists
```

**Immediate Diagnosis**:
```bash
# Check current migration status
docker-compose run --rm app alembic current

# Check migration history
docker-compose run --rm app alembic history

# Check database schema
docker-compose exec postgres psql -U secondbrain -c "\dt"

# Check for migration conflicts
ls -la migrations/versions/
```

**Common Causes & Fixes**:

1. **Migration conflicts**:
   ```bash
   # Check for multiple head revisions
   docker-compose run --rm app alembic heads
   
   # Resolve conflicts by merging heads
   docker-compose run --rm app alembic merge -m "merge conflicts" head1 head2
   ```

2. **Database state mismatch**:
   ```bash
   # Reset database to known state
   docker-compose down -v  # WARNING: Destroys data
   docker-compose up -d postgres
   docker-compose run --rm app alembic upgrade head
   ```

### 📊 Performance Test Issues (INFORMATIONAL)

Performance test failures don't block deployment but indicate potential issues.

#### Response Time Regressions

**Symptom**:
```
⚠️ Performance regression detected: /api/memories endpoint
   Previous: 150ms average, Current: 450ms average (+200% increase)
```

**Immediate Diagnosis**:
```bash
# Run performance tests locally
python scripts/run_performance_tests.py --type benchmark

# Profile specific endpoints
python -c "
import cProfile
import requests
import time

def test_endpoint():
    start = time.time()
    response = requests.get('http://localhost:8000/api/memories')
    duration = time.time() - start
    print(f'Response time: {duration*1000:.1f}ms')
    return response

cProfile.run('test_endpoint()')
"

# Check database query performance
docker-compose exec postgres psql -U secondbrain -c "
EXPLAIN ANALYZE SELECT * FROM memories ORDER BY created_at DESC LIMIT 20;
"
```

**Common Causes & Fixes**:

1. **Missing database indexes**:
   ```sql
   -- Problem: Query scanning entire table
   SELECT * FROM memories WHERE user_id = 123 ORDER BY created_at DESC;
   
   -- Fix: Add appropriate index
   CREATE INDEX idx_memories_user_created ON memories(user_id, created_at DESC);
   ```

2. **N+1 query problems**:
   ```python
   # Problem: Multiple queries in loop
   memories = session.query(Memory).all()
   for memory in memories:
       user = session.query(User).filter(User.id == memory.user_id).first()  # N+1
   
   # Fix: Use joins or eager loading
   memories = session.query(Memory).join(User).all()
   ```

---

## Common Error Patterns

### 🐍 Python-Specific Issues

#### Import and Module Problems

**Pattern Recognition**:
```bash
# Find import-related errors quickly
grep -E "(ImportError|ModuleNotFoundError|cannot import)" ci_logs.txt

# Common patterns:
# - "cannot import name 'X' from 'Y'" → Check if X exists in Y
# - "No module named 'app.something'" → Check PYTHONPATH and __init__.py files
# - "attempted relative import with no known parent package" → Check relative imports
```

**Systematic Fix Approach**:
```bash
# 1. Verify file structure
find app/ -name "*.py" | head -20
find app/ -name "__init__.py" | wc -l

# 2. Test imports manually
python -c "import app"
python -c "from app.services import service_factory"
python -c "from app.models.memory import Memory"

# 3. Check for circular imports
python -m py_compile app/services/service_factory.py
python -m py_compile app/models/memory.py

# 4. Fix PYTHONPATH issues
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -c "import sys; print('\\n'.join(sys.path))"
```

#### Async/Await Issues

**Pattern Recognition**:
```bash
# Find async-related errors
grep -E "(RuntimeWarning.*coroutine|was never awaited|cannot use await)" ci_logs.txt

# Common patterns:
# - "coroutine 'function' was never awaited" → Missing await
# - "object has no attribute '__await__'" → Trying to await non-async function
# - "cannot use await in a non-async function" → Missing async keyword
```

**Systematic Fix Approach**:
```python
# 1. Identify async functions that need await
# Bad:
def sync_function():
    result = async_function()  # Missing await
    return result

# Good:
async def async_function_caller():
    result = await async_function()
    return result

# 2. Fix event loop issues in tests
# Bad:
def test_async_function():
    result = async_function()  # Won't work
    assert result.value == "test"

# Good:
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result.value == "test"

# 3. Handle mixed sync/async code
import asyncio

# For calling async from sync:
def sync_wrapper():
    return asyncio.run(async_function())

# For calling sync from async:
async def async_wrapper():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_function)
    return result
```

### 🗄️ Database-Related Issues

#### Connection Pool Exhaustion

**Pattern Recognition**:
```bash
# Find connection pool errors
grep -E "(pool.*exhausted|too many connections|connection.*timeout)" ci_logs.txt

# Check active connections
docker-compose exec postgres psql -U secondbrain -c "
SELECT count(*) as active_connections, 
       max_conn, 
       max_conn - count(*) as remaining_connections
FROM pg_stat_activity, 
     (SELECT setting::int as max_conn FROM pg_settings WHERE name='max_connections') mc
GROUP BY max_conn;
"
```

**Systematic Fix Approach**:
```python
# 1. Proper connection management
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Bad: No connection pooling configured
engine = create_engine(DATABASE_URL)

# Good: Proper connection pool configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300
)

# 2. Always close connections in tests
@pytest.fixture
async def database_session():
    async with async_session() as session:
        yield session
        # Connection automatically closed

# 3. Monitor connection usage
import psutil

def check_connection_usage():
    process = psutil.Process()
    connections = process.connections()
    db_connections = [c for c in connections if c.laddr.port == 5432]
    print(f"Active DB connections: {len(db_connections)}")
```

#### Migration and Schema Issues

**Pattern Recognition**:
```bash
# Find migration errors
grep -E "(migration.*failed|alembic.*error|schema.*mismatch)" ci_logs.txt

# Check migration status
docker-compose run --rm app alembic current
docker-compose run --rm app alembic history --verbose
```

**Systematic Fix Approach**:
```bash
# 1. Reset migration state (DESTRUCTIVE - only in development)
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm app alembic upgrade head

# 2. Fix migration conflicts
docker-compose run --rm app alembic heads  # Should show only one head
docker-compose run --rm app alembic merge -m "resolve conflicts" head1 head2

# 3. Validate schema consistency
docker-compose exec postgres psql -U secondbrain -c "
SELECT schemaname, tablename, attname, typname 
FROM pg_tables 
JOIN pg_attribute ON pg_tables.tablename = pg_attribute.attrelid::regclass::text
JOIN pg_type ON pg_attribute.atttypid = pg_type.oid
WHERE schemaname = 'public' 
ORDER BY tablename, attname;
"

# 4. Backup before risky migrations
docker-compose exec postgres pg_dump -U secondbrain > backup_before_migration.sql
```

### 🔗 Network and Service Issues

#### Service Discovery Problems

**Pattern Recognition**:
```bash
# Find service connection errors
grep -E "(connection refused|timeout|service unavailable)" ci_logs.txt

# Check service status
docker-compose ps
docker-compose logs --tail=20 postgres redis
```

**Systematic Fix Approach**:
```bash
# 1. Verify service availability
timeout 30 bash -c 'until nc -z localhost 5432; do sleep 1; done'
timeout 30 bash -c 'until nc -z localhost 6379; do sleep 1; done'

# 2. Check service health
docker-compose exec postgres pg_isready -U secondbrain
docker-compose exec redis redis-cli ping

# 3. Restart services if needed
docker-compose restart postgres redis

# 4. Check for port conflicts
lsof -i :5432
lsof -i :6379

# 5. Use service names in docker-compose network
# Bad: Using localhost in containerized environment
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Good: Using service name
DATABASE_URL=postgresql://user:pass@postgres:5432/db
```

---

## Environment Issues

### 🐳 Docker and Container Problems

#### Container Startup Failures

**Symptoms**:
```
❌ Container postgres exited with code 1
❌ Network second-brain_default not found
❌ Volume mount failed: permission denied
```

**Diagnosis and Fixes**:

```bash
# 1. Check container logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs app

# 2. Verify Docker daemon
docker info
docker version

# 3. Clean up problematic containers/networks
docker-compose down -v
docker system prune -f
docker-compose up -d

# 4. Check volume permissions (Linux/WSL)
ls -la $(pwd)  # Should be readable by Docker user
sudo chown -R $USER:$USER $(pwd)

# 5. Restart Docker if needed (macOS/Windows)
# Docker Desktop → Restart Docker Desktop
```

#### Image Building Issues

**Symptoms**:
```
❌ failed to solve with frontend dockerfile.v0
❌ Error response from daemon: pull access denied
❌ COPY failed: no such file or directory
```

**Diagnosis and Fixes**:

```bash
# 1. Rebuild images from scratch
docker-compose build --no-cache

# 2. Check Dockerfile syntax
docker build -t test-build -f docker/Dockerfile .

# 3. Verify file paths in COPY commands
ls -la config/requirements.txt
ls -la app/

# 4. Check Docker Hub connectivity
docker pull python:3.11-slim
docker pull postgres:16

# 5. Clear Docker cache if needed
docker builder prune -a
```

### 🔧 Virtual Environment Issues

#### Python Version Conflicts

**Symptoms**:
```
❌ Python version 3.8 found, but 3.11 required
❌ ImportError: No module named '_ctypes'
❌ ModuleNotFoundError: No module named 'asyncio'
```

**Diagnosis and Fixes**:

```bash
# 1. Check Python version
python --version
python3 --version
which python

# 2. Check virtual environment
which python
pip list | grep -E "(fastapi|pydantic|pytest)"

# 3. Recreate virtual environment
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 4. Install dependencies
pip install --upgrade pip
pip install -r config/requirements.txt
pip install -r config/requirements-dev.txt

# 5. Verify installation
python -c "import fastapi; print(fastapi.__version__)"
python -c "import pydantic; print(pydantic.__version__)"
```

#### Package Dependency Conflicts

**Symptoms**:
```
❌ ERROR: pip's dependency resolver does not currently have a solution
❌ ImportError: cannot import name 'BaseModel' from 'pydantic'
❌ AttributeError: module 'fastapi' has no attribute 'APIRouter'
```

**Diagnosis and Fixes**:

```bash
# 1. Check for conflicts
pip check

# 2. Show dependency tree
pip show fastapi
pip show pydantic

# 3. Update pip and try again
pip install --upgrade pip setuptools wheel
pip install --upgrade -r config/requirements.txt

# 4. Use pip-tools for clean dependencies
pip install pip-tools
pip-compile config/requirements.in
pip-sync config/requirements.txt

# 5. Create clean environment if needed
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r config/requirements.txt
```

### 🔑 Environment Variables and Configuration

#### Missing or Invalid Configuration

**Symptoms**:
```
❌ KeyError: 'DATABASE_URL'
❌ ValueError: invalid database URL format
❌ OpenAI API key not provided or invalid
```

**Diagnosis and Fixes**:

```bash
# 1. Check environment variables
env | grep -E "(DATABASE_URL|REDIS_URL|OPENAI_API_KEY)"

# 2. Validate configuration format
python -c "
import os
from urllib.parse import urlparse

db_url = os.getenv('DATABASE_URL', '')
if db_url:
    parsed = urlparse(db_url)
    print(f'Scheme: {parsed.scheme}')
    print(f'Host: {parsed.hostname}')
    print(f'Port: {parsed.port}')
    print(f'Database: {parsed.path.lstrip(\"/\")}')
else:
    print('DATABASE_URL not set')
"

# 3. Load from .env file
cp .env.example .env
# Edit .env with appropriate values

# 4. Export for current session
export DATABASE_URL="postgresql://secondbrain:changeme@localhost:5432/secondbrain_test"
export REDIS_URL="redis://localhost:6379"
export OPENAI_API_KEY="test-key-mock"

# 5. Validate configuration loading
python -c "
from app.config import settings
print('Database URL:', settings.database_url)
print('Redis URL:', settings.redis_url)
print('OpenAI configured:', bool(settings.openai_api_key))
"
```

---

## Performance Problems

### 🐌 Slow Test Execution

#### Test Performance Analysis

**Diagnosis Tools**:

```bash
# 1. Profile test execution time
python -m pytest tests/unit/ --durations=10

# 2. Identify slow tests
python -m pytest tests/unit/ --durations=0 | sort -k2 -nr

# 3. Run tests with timing
python -m pytest tests/unit/ -v --tb=line --durations=20

# 4. Check resource usage during tests
python -c "
import psutil
import subprocess
import time

def monitor_tests():
    process = subprocess.Popen(['python', '-m', 'pytest', 'tests/unit/'])
    
    while process.poll() is None:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        print(f'CPU: {cpu}%, Memory: {memory.percent}%')
        time.sleep(5)
    
    return process.returncode

monitor_tests()
"
```

**Optimization Strategies**:

```python
# 1. Use pytest-xdist for parallel execution
# Install: pip install pytest-xdist
# Run: python -m pytest tests/unit/ -n auto

# 2. Optimize database fixtures
@pytest.fixture(scope="session")  # Session-scoped for expensive setup
async def database_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")  # Function-scoped for test isolation
async def database_session(database_engine):
    async with async_session(database_engine) as session:
        yield session
        await session.rollback()  # Rollback instead of truncate

# 3. Mock expensive operations
@pytest.fixture(autouse=True)
def mock_openai():
    with patch('app.services.openai_client.OpenAIClient') as mock:
        mock.return_value.generate_embedding.return_value = [0.1] * 1536
        yield mock

# 4. Use test markers to skip slow tests in development
@pytest.mark.slow
def test_large_dataset_processing():
    # This test only runs when explicitly requested
    pass

# Run without slow tests: pytest -m "not slow"
```

### 💾 Memory Usage Issues

#### Memory Leak Detection

**Diagnosis Tools**:

```python
import tracemalloc
import psutil
import gc

def monitor_memory_usage():
    """Monitor memory usage during test execution"""
    tracemalloc.start()
    initial_memory = psutil.Process().memory_info().rss
    
    # Run your tests here
    yield
    
    # Analyze memory usage
    current, peak = tracemalloc.get_traced_memory()
    final_memory = psutil.Process().memory_info().rss
    
    print(f"Initial memory: {initial_memory / 1024 / 1024:.1f}MB")
    print(f"Final memory: {final_memory / 1024 / 1024:.1f}MB")
    print(f"Memory delta: {(final_memory - initial_memory) / 1024 / 1024:.1f}MB")
    print(f"Peak traced memory: {peak / 1024 / 1024:.1f}MB")
    
    tracemalloc.stop()

# Check for memory leaks in specific tests
def test_with_memory_monitoring():
    with monitor_memory_usage():
        # Run test that might leak memory
        for i in range(1000):
            result = some_operation()
        
        # Force garbage collection
        gc.collect()
```

**Memory Optimization Strategies**:

```python
# 1. Proper cleanup in fixtures
@pytest.fixture
async def large_dataset():
    data = create_large_dataset()  # Memory-intensive
    yield data
    del data  # Explicit cleanup
    gc.collect()

# 2. Limit concurrent test execution
# pytest.ini:
[tool:pytest]
addopts = -n 2  # Limit to 2 workers instead of auto

# 3. Use generators for large datasets
def create_test_memories():
    """Generator instead of creating all data at once"""
    for i in range(10000):
        yield {"title": f"Memory {i}", "content": f"Content {i}"}

# 4. Clear caches between tests
@pytest.fixture(autouse=True)
def clear_caches():
    yield
    # Clear any application caches
    from app.utils.cache import cache
    cache.clear()
```

---

## Advanced Debugging

### 🔍 Interactive Debugging

#### Using pdb for Step-by-step Debugging

```bash
# Run test with debugger
python -m pytest tests/unit/test_memory.py::test_create -v -s --pdb

# Set breakpoints in code
import pdb; pdb.set_trace()

# Common pdb commands:
# n (next line)
# s (step into)
# c (continue)
# l (list code)
# p variable_name (print variable)
# pp variable_name (pretty print)
# u (up stack frame)
# d (down stack frame)
# h (help)
```

#### Remote Debugging with CI

```yaml
# Add to GitHub Actions for remote debugging
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: failure()
  timeout-minutes: 30
```

### 📊 Performance Profiling

#### CPU Profiling

```python
import cProfile
import pstats

def profile_test_execution():
    """Profile CPU usage during test execution"""
    profiler = cProfile.Profile()
    
    profiler.enable()
    # Run your test here
    result = run_expensive_operation()
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions by cumulative time
    
    return result

# Use with pytest
def test_performance():
    with profile_test_execution():
        # Your test code here
        pass
```

#### Memory Profiling with memory_profiler

```bash
# Install memory profiler
pip install memory-profiler

# Profile specific function
@profile
def memory_intensive_function():
    # Function implementation
    pass

# Run with profiler
python -m memory_profiler test_script.py

# Line-by-line memory usage
mprof run test_script.py
mprof plot
```

### 🌐 Network and Service Debugging

#### API Endpoint Testing

```bash
# Test API endpoints directly
curl -v -X GET http://localhost:8000/health
curl -v -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"title":"Test","content":"Test content"}'

# Test with different HTTP methods
http GET localhost:8000/api/memories  # Using httpie
http POST localhost:8000/api/memories title="Test" content="Test content"

# Check OpenAPI documentation
curl http://localhost:8000/openapi.json | jq '.'
```

#### Database Query Analysis

```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Analyze slow queries
EXPLAIN ANALYZE SELECT * FROM memories WHERE user_id = 123;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'memories';

-- Monitor active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

---

## Recovery Procedures

### 🚨 Emergency Recovery

#### Complete Environment Reset

```bash
#!/bin/bash
# emergency_reset.sh - Complete environment reset

echo "🚨 EMERGENCY RECOVERY - This will destroy all local data!"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo "🧹 Cleaning Docker environment..."
docker-compose down -v
docker system prune -af
docker volume prune -f

echo "🐍 Recreating Python environment..."
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt

echo "🔧 Resetting configuration..."
cp .env.example .env
export PYTHONPATH=$(pwd)

echo "🐳 Starting fresh services..."
docker-compose up -d postgres redis
sleep 10

echo "🗄️ Setting up database..."
docker-compose run --rm app alembic upgrade head

echo "✅ Recovery complete. Running smoke tests..."
make test-smoke

echo "🎉 Environment recovered successfully!"
```

#### Partial Recovery Procedures

**Database Only**:
```bash
# Reset database while keeping other services
docker-compose stop app
docker-compose down postgres
docker volume rm second-brain_postgres_data
docker-compose up -d postgres
sleep 10
docker-compose run --rm app alembic upgrade head
make test-smoke
```

**Python Environment Only**:
```bash
# Reset Python environment while keeping Docker services
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r config/requirements.txt
make test-smoke
```

### 🔄 Rollback Procedures

#### Git-based Rollback

```bash
# Find last known good commit
git log --oneline -10

# Create rollback branch
git checkout -b rollback-emergency main
git reset --hard <last-good-commit-hash>

# Test the rollback
make test-smoke
make test-fast

# If tests pass, force push (emergency only)
git push origin rollback-emergency --force
```

#### Configuration Rollback

```bash
# Backup current configuration
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Restore from known good configuration
git checkout HEAD~1 -- .env.example
cp .env.example .env
git checkout HEAD~1 -- docker-compose.yml

# Test configuration
make test-smoke
```

### 📈 Recovery Validation

#### Post-Recovery Verification

```bash
#!/bin/bash
# verify_recovery.sh - Comprehensive recovery verification

echo "🔍 Starting recovery verification..."

# 1. Environment validation
echo "1. Checking environment..."
python scripts/validate_environment.py || exit 1

# 2. Service connectivity
echo "2. Testing service connectivity..."
docker-compose exec postgres pg_isready -U secondbrain || exit 1
docker-compose exec redis redis-cli ping || exit 1

# 3. Application startup
echo "3. Testing application startup..."
timeout 30 python -c "from app.app import create_app; app = create_app(); print('✅ App OK')" || exit 1

# 4. Database integrity
echo "4. Checking database integrity..."
docker-compose run --rm app alembic current || exit 1

# 5. Basic functionality
echo "5. Running smoke tests..."
make test-smoke || exit 1

# 6. Core functionality
echo "6. Running fast feedback tests..."
make test-fast || exit 1

echo "✅ Recovery verification complete - System operational!"
```

This comprehensive troubleshooting guide provides systematic approaches to diagnosing and fixing CI/CD issues, from quick emergency fixes to detailed debugging procedures. The key is to start with quick diagnosis to identify the severity and category of the problem, then follow the appropriate systematic approach to resolve it.