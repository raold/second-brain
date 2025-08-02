# Second Brain v4.0.0 🧠 - **Production-Ready AI Memory System**

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](tests/)

> **🐳 Docker-First Development**: Zero host dependencies, bulletproof cross-platform development experience.

## 🎯 **Design Philosophy**

Second Brain v3.0.0 is built on **developer-first principles** that eliminate environment friction:

### **🐳 Docker-First Architecture**
- **Zero Host Dependencies**: No Python, PostgreSQL, or Redis installation required
- **Identical Environments**: Same containers run on Windows, macOS, and Linux
- **One-Command Setup**: `make setup` gets you developing in minutes
- **Production Parity**: Development mirrors production exactly

### **🔒 Bulletproof Fallback**
- **Smart Detection**: Automatically uses Docker when available
- **Automated .venv**: Creates bulletproof virtual environments when Docker unavailable
- **Cross-Platform Scripts**: Windows `.bat` and Unix `.sh` activation scripts
- **Environment Validation**: Automatic health checks ensure everything works

### **🛠️ Developer Experience**
- **Intelligent Makefile**: Commands work everywhere, adapt to your environment
- **Real-Time Feedback**: Hot reload, live logs, instant test results
- **Clear Status**: Always know your environment health at a glance
- **No Configuration**: Sensible defaults, minimal setup required

## 🚀 **What's New in v3.0.0**

Second Brain v3.0.0 is a complete architectural overhaul designed for production scalability, maintainability, and enterprise deployment.

### **✨ Key Features**

- **🏛️ Clean Architecture**: Domain-driven design with clear separation of concerns
- **📨 Event Sourcing**: Complete audit trail and event-driven architecture
- **🔄 CQRS Pattern**: Optimized read/write separation for scalability
- **📦 Message Queue**: RabbitMQ integration for async processing
- **📊 Observability**: OpenTelemetry tracing, Prometheus metrics, structured logging
- **💾 Caching Layer**: Redis caching with multiple strategies
- **📁 Multi-Modal Ingestion**: Support for documents, images, audio, and video files
- **🎯 Batch Classification**: Intelligent categorization with multiple methods
- **🔍 Vector Search**: PostgreSQL with pgvector for embeddings
- **🐳 Docker-First**: Cross-platform compatibility (Windows, macOS, Linux)
- **🧪 Comprehensive Testing**: Unit, integration, and e2e test suites

## 🏗️ **Architecture Overview**

```
app/                 # Main application module
├── models/          # Pydantic models and domain entities
├── services/        # Business logic and service layer
├── routes/          # API route handlers
├── ingestion/       # Data ingestion and processing
├── insights/        # Analytics and insights generation
└── utils/           # Utility functions and helpers

main.py             # Application entry point
```

### **Core Principles**

1. **Domain-Driven Design**: Business logic isolated in the domain layer
2. **Dependency Inversion**: All dependencies point inward
3. **Event-Driven**: Domain events for decoupled communication
4. **Repository Pattern**: Abstract data access
5. **Use Case Pattern**: Clear application boundaries

## 🚀 **Quick Start**

### **⚡ Instant Setup (Recommended)**

```bash
# Clone repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# One-command setup (Docker + fallback .venv)
make setup

# Start development environment
make dev

# Check status
make status

# Run tests
make test
```

### **📋 What Just Happened?**

The setup automatically:
- ✅ Detects if Docker is available and running
- ✅ Starts PostgreSQL, Redis, and application containers
- ✅ Creates bulletproof .venv if Docker unavailable
- ✅ Installs all dependencies correctly
- ✅ Validates environment health
- ✅ Provides activation scripts for your OS

### **🔧 Manual Setup (if needed)**

```bash
# Docker-first approach
docker-compose up --build          # Full development stack
docker-compose exec app python scripts/test_runner.py --all

# Bulletproof .venv fallback
python scripts/setup-bulletproof-venv.py  # Creates validated .venv
.venv/Scripts/python.exe main.py          # Windows
.venv/bin/python main.py                  # Unix

# Access application
open http://localhost:8000
```

### **🎯 Development Commands**

```bash
# Core workflow
make dev           # Start development environment
make test          # Run all tests
make shell         # Open development shell
make dev-logs      # Show application logs
make dev-stop      # Stop development environment

# Testing options
make test-unit           # Unit tests only
make test-integration    # Integration tests only
make test-validation     # Environment validation

# Status and health
make status              # Environment health check
make db-shell           # PostgreSQL shell
```

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/secondbrain

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

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## 📚 **API Documentation**

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### **Core Endpoints**

```bash
# Memories
POST   /api/v1/memories          # Create memory
GET    /api/v1/memories          # List memories
GET    /api/v1/memories/{id}     # Get memory
PUT    /api/v1/memories/{id}     # Update memory
DELETE /api/v1/memories/{id}     # Delete memory

# Search
POST   /api/v1/memories/search   # Vector similarity search

# Multi-Modal Ingestion
POST   /api/v1/ingest/upload     # Upload single file (PDF, audio, video, etc.)
POST   /api/v1/ingest/batch      # Batch file upload
GET    /api/v1/ingest/status/{id} # Check ingestion status

# Bulk Operations
POST   /bulk/import              # Import memories (CSV, JSON, etc.)
POST   /bulk/export              # Export memories
POST   /bulk/classify            # Batch classification
POST   /bulk/deduplicate         # Remove duplicates

# Sessions
POST   /api/v1/sessions          # Create session
GET    /api/v1/sessions          # List sessions
GET    /api/v1/sessions/{id}     # Get session with memories

# Health & Metrics
GET    /health                   # Health check
GET    /metrics                  # Prometheus metrics
```

### **🎯 Multi-Modal Ingestion**

Second Brain now supports ingestion of various file types:

- **Documents**: PDF, Word, HTML, Markdown, Plain text
- **Spreadsheets**: Excel, CSV, OpenDocument
- **Images**: JPG, PNG, GIF (with OCR support)
- **Audio**: MP3, WAV, M4A (with transcription)
- **Video**: MP4, AVI, MOV (with audio extraction)
- **Subtitles**: SRT, VTT

```bash
# Upload a PDF with automatic text extraction
curl -X POST "http://localhost:8000/api/v1/ingest/upload" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@document.pdf"

# For full multi-modal support with audio/video
docker build -f Dockerfile.multimodal -t secondbrain:multimodal .
```

## 📖 **Comprehensive Documentation**

Second Brain v3.0.0 provides extensive documentation for all aspects of development, deployment, and integration:

### **🚀 Quick Start Guides**

| Guide | Purpose | Time | Audience |
|-------|---------|------|----------|
| **[📋 Documentation Index](docs/DOCUMENTATION_INDEX.md)** | Complete documentation hub | 5 min | Everyone |
| **[🚀 CI/CD Quick Reference](docs/CI_CD_DEVELOPER_QUICK_REFERENCE.md)** | Daily CI/CD commands | 5 min | Developers |
| **[🌐 API Documentation](docs/API_DOCUMENTATION_INDEX.md)** | API integration guide | 10 min | Frontend devs |
| **[🔧 Development Guide](docs/development/DEVELOPMENT_GUIDE_v3.0.0.md)** | Local development setup | 15 min | New developers |

### **🎯 Documentation by Role**

**👨‍💻 New Developers**:
1. [Setup Guide](docs/SETUP.md) - Get environment running (20 min)
2. [CI/CD Quick Reference](docs/CI_CD_DEVELOPER_QUICK_REFERENCE.md) - Essential commands (5 min)
3. [Development Guide](docs/development/DEVELOPMENT_GUIDE_v3.0.0.md) - Learn workflow (15 min)

**🔧 DevOps Engineers**:
1. [CI/CD Comprehensive Guide](docs/CI_CD_COMPREHENSIVE_GUIDE.md) - Complete CI/CD system (30 min)
2. [CI/CD Workflow Documentation](docs/CI_CD_WORKFLOW_DOCUMENTATION.md) - GitHub Actions (20 min)
3. [Deployment Guide](docs/deployment/DEPLOYMENT_V3.md) - Production deployment (45 min)

**🌐 Frontend Developers**:
1. [API Documentation Index](docs/API_DOCUMENTATION_INDEX.md) - API overview (10 min)
2. [API Usage Examples](docs/API_USAGE_EXAMPLES.md) - Integration examples (15 min)
3. [WebSocket Events](docs/WEBSOCKET_EVENTS_SPECIFICATION.md) - Real-time features (20 min)

### **🤖 CI/CD System**

Our tiered CI/CD pipeline ensures fast feedback and reliable deployments:

```
🔥 Smoke Tests (30-60s) → ⚡ Fast Feedback (2-5min) → 🔍 Comprehensive (10-15min) → 📊 Performance (5-20min) → 🚀 Deploy
```

**Essential Commands**:
```bash
make test-smoke        # Quick validation (< 1 min)
make test-fast         # Core functionality (< 5 min)
make test-comprehensive # Full validation (< 15 min)
make ci-full          # Complete pipeline simulation
```

**Documentation**:
- **[CI/CD Developer Quick Reference](docs/CI_CD_DEVELOPER_QUICK_REFERENCE.md)** - Daily commands and troubleshooting
- **[CI/CD Comprehensive Guide](docs/CI_CD_COMPREHENSIVE_GUIDE.md)** - Complete system documentation
- **[CI/CD Troubleshooting Guide](docs/CI_CD_TROUBLESHOOTING_GUIDE.md)** - Problem diagnosis and solutions

### **🌐 API Integration**

Complete API documentation with real-time WebSocket support:

**Key Resources**:
- **[API Documentation Index](docs/API_DOCUMENTATION_INDEX.md)** - Complete API overview
- **[API v2 Specification](docs/API_V2_UNIFIED_SPECIFICATION.md)** - Detailed API reference
- **[API Usage Examples](docs/API_USAGE_EXAMPLES.md)** - Framework-specific examples
- **[WebSocket Events](docs/WEBSOCKET_EVENTS_SPECIFICATION.md)** - Real-time communication

**Quick Start**:
```javascript
const api = new SecondBrainAPI('your-api-key');
const metrics = await api.getMetrics();
const ws = api.connectWebSocket(handleUpdate);
```

### **📚 Complete Documentation Index**

All documentation is organized in [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md):

- **🔧 Development**: Setup, architecture, contributing guidelines
- **🤖 CI/CD**: Automated testing, deployment, troubleshooting
- **🌐 API**: Integration guides, specifications, examples
- **🧪 Testing**: Testing strategies, performance benchmarks
- **🚢 Deployment**: Production deployment, monitoring, operations

## 🧪 **Testing**

```bash
# Docker-first testing (recommended)
make test                    # All tests in containers
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-validation        # Environment validation

# Direct script access (cross-platform)
python scripts/dev test --test-type all         # All tests
python scripts/dev test --test-type unit        # Unit tests
python scripts/dev test --test-type integration # Integration tests
python scripts/dev test --test-type validation  # Validation tests

# Fallback .venv testing (when Docker unavailable)
.venv/Scripts/python.exe scripts/test_runner.py --validation  # Windows
.venv/bin/python scripts/test_runner.py --validation          # Unix
```

### **🔍 Test Categories**

- **Validation**: Environment health, dependency checks, basic imports
- **Unit**: Fast isolated tests, no external dependencies
- **Integration**: Database, API, service integration tests
- **Comprehensive**: Full end-to-end testing (slower)

## 📊 **Monitoring & Observability**

### **Metrics (Prometheus)**
- Request latency histograms
- Memory operation counters
- Cache hit/miss rates
- Message queue metrics

### **Tracing (OpenTelemetry)**
- Distributed request tracing
- Database query performance
- External service calls
- Async task execution

### **Logging**
- Structured JSON logging
- Correlation IDs
- Error tracking
- Performance metrics

## 🚢 **Deployment**

### **Docker**

```bash
# Build image
docker build -t second-brain:v3.0.0 .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  second-brain:v3.0.0
```

### **Kubernetes**

```yaml
# See /k8s directory for manifests
kubectl apply -f k8s/
```

### **Cloud Platforms**

- **AWS**: ECS/Fargate, RDS PostgreSQL, ElastiCache, SQS
- **GCP**: Cloud Run, Cloud SQL, Memorystore, Pub/Sub
- **Azure**: Container Instances, Database for PostgreSQL, Cache for Redis

## 🔄 **Migration from v2.x**

See [MIGRATION_GUIDE_V3.md](docs/MIGRATION_GUIDE_V3.md) for detailed migration instructions.

### **Breaking Changes**
- New API structure (`/api/v1/` prefix)
- Updated data models (event sourcing)
- Removed Qdrant dependency
- New authentication mechanism

## 🤝 **Contributing**

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### **Development Process**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 **License**

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- Clean Architecture principles by Robert C. Martin
- Domain-Driven Design by Eric Evans
- Event Sourcing patterns by Martin Fowler
- The amazing Python community

## 📞 **Support**

- **Documentation**: [/docs](./docs)
- **Issues**: [GitHub Issues](https://github.com/raold/second-brain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/raold/second-brain/discussions)

---

Built with ❤️ by the Second Brain team
