# Second Brain v3.0.0 - Complete Setup Guide

> **🐳 Docker-First Development**: Zero host dependencies, bulletproof cross-platform development experience with intelligent .venv fallback.

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Setup Options](#setup-options)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Platform Compatibility](#platform-compatibility)
10. [Architecture Benefits](#architecture-benefits)

## ⚡ Quick Start

The fastest way to get started:

```bash
# 1. Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# 2. One-command setup (Docker + fallback)
make setup

# 3. Start development
make dev

# 4. Verify installation
make status

# 5. Access application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## 🛠️ Prerequisites

### Required Software
- **Python 3.11+** (3.11 or 3.12 recommended)
- **Git** for version control
- **Docker Desktop** (recommended) or individual services:
  - PostgreSQL 16+ with pgvector
  - Redis 7+
  - RabbitMQ 3.12+
  - MinIO (S3-compatible storage)

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB free space
- **OS**: Windows 10/11, macOS 10.15+, or Linux

## 📦 Setup Options

### Option 1: Docker Setup (Recommended)

```bash
# Clone and navigate
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Configure environment
cp .env.example .env

# Build and start services
docker-compose up --build -d

# Run migrations
docker-compose exec app alembic upgrade head

# Verify services
docker-compose ps

# View logs
docker-compose logs -f app
```

### Option 2: Bulletproof Virtual Environment

When Docker is unavailable:

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create bulletproof .venv
python scripts/setup-bulletproof-venv.py

# Activate environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure and run
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

### Option 3: Hybrid Setup

Best for active development:

```bash
# Start infrastructure only
docker-compose up -d postgres redis rabbitmq minio

# Use local Python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure for Docker services
# Update .env with Docker endpoints

# Run application
alembic upgrade head
uvicorn main:app --reload
```

## ⚙️ Configuration

### Essential Environment Variables

```bash
# Application
APP_NAME=SecondBrain
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/secondbrain

# Redis
REDIS_URL=redis://localhost:6379

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# MinIO/S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# OpenAI
OPENAI_API_KEY=your-api-key
```

### Docker Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| PostgreSQL | localhost:5432 | postgres/password |
| Redis | localhost:6379 | - |
| RabbitMQ | localhost:5672 | guest/guest |
| RabbitMQ UI | http://localhost:15672 | guest/guest |
| MinIO | http://localhost:9000 | minioadmin/minioadmin |

## 🏃 Running the Application

### Development Commands

```bash
# Core workflow
make dev           # Start development
make dev-logs      # View logs
make dev-stop      # Stop services
make shell         # Development shell
make status        # Health check

# Database
make db-shell      # PostgreSQL CLI
make db-migrate    # Run migrations
make db-rollback   # Rollback migration

# Testing
make test          # All tests
make test-unit     # Unit tests only
make test-integration # Integration tests
```

### Direct Commands

```bash
# Docker approach
docker-compose up -d
docker-compose logs -f app

# Python approach
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Multi-modal support
docker build -f Dockerfile.multimodal -t secondbrain:multimodal .
```

## 🧪 Testing

### Test Categories
- **Validation**: Environment health checks
- **Unit**: Fast isolated tests
- **Integration**: Database/API tests
- **E2E**: Full workflow tests

### Running Tests

```bash
# Using Make
make test                # All tests
make test-unit          # Unit only
make test-integration   # Integration only
make test-validation    # Health checks

# Using pytest
pytest                  # All tests
pytest tests/unit/      # Unit tests
pytest -v --cov=app     # With coverage
pytest -k "test_memory" # Pattern match

# Using universal script
python scripts/dev test --test-type all
python scripts/dev test --test-type unit
```

## 🔄 Development Workflow

### Daily Development

```bash
# 1. Start environment
make dev

# 2. Check status
make status

# 3. Make changes and test
make test-unit      # Fast feedback
make test           # Full validation

# 4. Code quality
make format         # Auto-format
make lint           # Check style
make type-check     # Type validation

# 5. Commit with conventional commits
git commit -m "feat: add new feature"
git commit -m "fix: resolve issue"
git commit -m "docs: update README"
```

### Database Operations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Database shell
make db-shell
```

### API Development

```bash
# Test endpoints
curl -X POST "http://localhost:8000/api/v1/memories" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory"}'

# Upload file
curl -X POST "http://localhost:8000/api/v1/ingest/upload" \
  -F "file=@document.pdf"
```

## 🔍 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Find process using port
lsof -i :8000           # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Solution: Change port in .env
API_PORT=8001
```

#### Database Connection
```bash
# Check PostgreSQL
docker-compose ps postgres
pg_isready -h localhost -p 5432

# Verify connection string
DATABASE_URL=postgresql://user:pass@host:port/db
```

#### Import Errors
```bash
# Verify environment
which python  # Should show .venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run validation
make test-validation
```

#### Docker Issues
```bash
# Restart Docker
make dev-stop
make dev

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Emergency Commands

```bash
# Full reset (WARNING: data loss)
make clean-all
make setup

# Kill all containers
docker kill $(docker ps -q)

# Remove volumes
docker volume prune -f

# Fix permissions
sudo chown -R $USER:$USER .
```

## 🌍 Platform Compatibility

**✅ Verified on:**
- Windows 10/11 (native and WSL2)
- macOS (Intel and Apple Silicon)
- Linux (Ubuntu, Debian, Arch, CentOS)
- Docker Desktop 4.x+
- Python 3.11+ environments

## 🚀 Architecture Benefits

This setup provides:

- **🔒 Isolation**: No system Python conflicts
- **📦 Consistency**: Identical environments everywhere
- **⚡ Speed**: One-command setup and deployment
- **🛡️ Reliability**: Automatic fallback mechanisms
- **🔄 Portability**: Seamless machine switching
- **🎯 Production Parity**: Dev mirrors production

## 💡 Pro Tips

1. **Always use Make commands** - They handle platform differences
2. **Check status first** - `make status` before debugging
3. **Use Docker logs** - `make dev-logs` for real-time debugging
4. **Enable pre-commit** - `pre-commit install` for code quality
5. **Test in container** - `make shell` for accurate testing
6. **Profile queries** - Set `SQLALCHEMY_ECHO=true` for SQL logs
7. **Monitor metrics** - Check `/metrics` endpoint regularly

## 📚 Additional Resources

- [Project Structure](PROJECT_STRUCTURE.md)
- [API Documentation](API_SPECIFICATION_v3.0.0.md)
- [Architecture Guide](ARCHITECTURE_V3.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Migration Guide](MIGRATION_GUIDE_V3.md)

---

**Need help?** Check `make help` or open an issue on GitHub.