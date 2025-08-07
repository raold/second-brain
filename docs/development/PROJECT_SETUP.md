# Second Brain v3.0.0 - Complete Project Setup Instructions

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start Guide](#quick-start-guide)
4. [Detailed Setup Options](#detailed-setup-options)
5. [Configuration Guide](#configuration-guide)
6. [Running the Application](#running-the-application)
7. [Testing](#testing)
8. [Development Workflow](#development-workflow)
9. [Troubleshooting](#troubleshooting)
10. [Additional Resources](#additional-resources)

## 🎯 Project Overview

Second Brain v3.0.0 is an enterprise-ready AI memory system built with:
- **FastAPI** for high-performance API
- **PostgreSQL** with pgvector for vector search
- **Redis** for caching
- **RabbitMQ** for message queuing
- **MinIO** for object storage
- **Clean Architecture** with Domain-Driven Design
- **Event Sourcing** and CQRS patterns

### Architecture Highlights
- Docker-first development with cross-platform support
- Comprehensive test coverage (>90%)
- Multi-modal file ingestion (documents, images, audio, video)
- Production-ready observability with OpenTelemetry
- Automated environment validation and fallback mechanisms

## 🛠️ Prerequisites

### Required Software
- **Python 3.11+** (3.11 or 3.12 recommended)
- **Git** for version control
- **Docker Desktop** (recommended) or individual services:
  - PostgreSQL 16+ with pgvector extension
  - Redis 7+
  - RabbitMQ 3.12+
  - MinIO (S3-compatible storage)

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB free space
- **OS**: Windows 10/11, macOS 10.15+, or Linux

## 🚀 Quick Start Guide

The fastest way to get started is using the automated setup:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# 2. Run automated setup (handles Docker + fallback)
make setup

# 3. Start development environment
make dev

# 4. Verify installation
make status

# 5. Access the application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## 📦 Detailed Setup Options

### Option 1: Docker Setup (Recommended)

This is the preferred method as it ensures consistent environments across all platforms.

```bash
# 1. Clone and navigate to project
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# 2. Copy environment configuration
cp .env.example .env

# 3. Build and start all services
docker-compose up --build -d

# 4. Run database migrations
docker-compose exec app alembic upgrade head

# 5. Verify services are running
docker-compose ps

# 6. View logs
docker-compose logs -f app
```

### Option 2: Manual Setup with Virtual Environment

Use this when Docker is not available or for lightweight development.

```bash
# 1. Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# 2. Create bulletproof virtual environment
python scripts/setup-bulletproof-venv.py

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 6. Install and start required services
# PostgreSQL: https://www.postgresql.org/download/
# Redis: https://redis.io/download
# RabbitMQ: https://www.rabbitmq.com/download.html
# MinIO: https://min.io/download

# 7. Create PostgreSQL database and enable pgvector
createdb secondbrain
psql -d secondbrain -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 8. Run database migrations
alembic upgrade head

# 9. Start the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Hybrid Setup (Docker for Services, Local Python)

Best for active development with quick iteration.

```bash
# 1. Start only infrastructure services
docker-compose -f docker-compose.yml up -d postgres redis rabbitmq minio

# 2. Set up Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Update .env to point to Docker services:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/secondbrain
# REDIS_URL=redis://localhost:6379
# RABBITMQ_URL=amqp://guest:guest@localhost:5672/
# MINIO_ENDPOINT=localhost:9000

# 4. Run migrations and start app
alembic upgrade head
uvicorn main:app --reload
```

## ⚙️ Configuration Guide

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application Settings
APP_NAME=SecondBrain
APP_VERSION=3.0.0
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# API Configuration
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/secondbrain
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis Cache
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# RabbitMQ Message Queue
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=secondbrain
RABBITMQ_QUEUE_PREFIX=sb_

# MinIO/S3 Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET=secondbrain

# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Authentication
SECRET_KEY=your-secret-key-here-generate-with-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=secondbrain
PROMETHEUS_PORT=9090

# Feature Flags
ENABLE_MULTI_MODAL_INGESTION=true
ENABLE_BATCH_PROCESSING=true
ENABLE_CACHE_WARMING=true
```

### Service-Specific Configuration

#### PostgreSQL with pgvector
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Configure for performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

#### Redis Configuration
```bash
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

#### RabbitMQ Setup
```bash
# Enable management plugin
rabbitmq-plugins enable rabbitmq_management

# Access management UI at http://localhost:15672
# Default credentials: guest/guest
```

## 🏃 Running the Application

### Development Mode

```bash
# Using Make (cross-platform)
make dev          # Start all services
make dev-logs     # View logs
make dev-stop     # Stop services

# Using Docker Compose
docker-compose up -d
docker-compose logs -f app

# Using Python directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Build optimized image
docker build -f Dockerfile -t secondbrain:v3.0.0 .

# Run with production settings
docker run -d \
  --name secondbrain \
  -p 8000:8000 \
  --env-file .env.production \
  secondbrain:v3.0.0

# Or use Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Multi-Modal Support

For full audio/video processing capabilities:

```bash
# Build multi-modal image
docker build -f Dockerfile.multimodal -t secondbrain:multimodal .

# Run with multi-modal support
docker run -d \
  --name secondbrain-mm \
  -p 8000:8000 \
  --env-file .env \
  secondbrain:multimodal
```

## 🧪 Testing

### Running Tests

```bash
# All tests (recommended)
make test

# Specific test suites
make test-unit        # Fast unit tests
make test-integration # Database/API tests
make test-e2e        # End-to-end tests
make test-validation # Environment health checks

# Using pytest directly
pytest                           # All tests
pytest tests/unit/              # Unit tests only
pytest -v --cov=app             # With coverage
pytest -k "test_memory"         # Specific test pattern
pytest -m "not slow"            # Exclude slow tests

# Watch mode for development
pytest-watch
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

## 🔄 Development Workflow

### 1. Environment Management

```bash
# Check environment health
make status

# Access development shell
make shell

# Database management
make db-shell      # PostgreSQL CLI
make db-migrate    # Run migrations
make db-rollback   # Rollback migration
```

### 2. Code Quality

```bash
# Format code
make format
# or
black app/ tests/
ruff check --fix app/ tests/

# Type checking
make type-check
# or
mypy app/

# Security scan
bandit -r app/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### 3. API Development

```bash
# Generate OpenAPI schema
python scripts/generate_openapi.py

# Test endpoints
# Create memory
curl -X POST "http://localhost:8000/api/v1/memories" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "tags": ["test"]}'

# Search memories
curl -X POST "http://localhost:8000/api/v1/memories/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 10}'
```

### 4. Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. Port Conflicts
```bash
# Error: Port 8000 is already in use
Solution:
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Change port in .env
API_PORT=8001
```

#### 2. Database Connection Issues
```bash
# Error: could not connect to database
Solution:
# Check PostgreSQL is running
docker-compose ps postgres
# or
pg_isready -h localhost -p 5432

# Verify credentials in .env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

#### 3. Redis Connection Failed
```bash
# Error: Redis connection refused
Solution:
# Check Redis is running
docker-compose ps redis
# or
redis-cli ping

# Test connection
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

#### 4. Import Errors
```bash
# Error: ModuleNotFoundError
Solution:
# Ensure virtual environment is activated
which python  # Should show .venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 5. Migration Failures
```bash
# Error: alembic.util.exc.CommandError
Solution:
# Reset migration history
alembic stamp head

# Drop and recreate database
dropdb secondbrain
createdb secondbrain
alembic upgrade head
```

### Performance Optimization

```bash
# Monitor resource usage
docker stats

# Optimize PostgreSQL
docker-compose exec postgres psql -U postgres -d secondbrain -c "VACUUM ANALYZE;"

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Check application metrics
curl http://localhost:8000/metrics
```

## 📚 Additional Resources

### Project Documentation
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Migration Guide**: [docs/MIGRATION_GUIDE_V3.md](docs/MIGRATION_GUIDE_V3.md)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
- [Redis Documentation](https://redis.io/documentation)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Docker Documentation](https://docs.docker.com/)

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Discord Community**: Real-time help and discussions
- **Email Support**: team@secondbrain.ai

---

**Remember**: The recommended approach is to use `make setup` followed by `make dev` for the smoothest setup experience. The system will automatically detect your environment and use the best available option (Docker or virtual environment).

Happy coding! 🧠✨