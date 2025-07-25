# Second Brain v3.0.0 🧠 - **Enterprise-Ready AI Memory System**

![Python](https://img.shields.io/badge/python-3.11+-blue.svg) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg) ![Clean Architecture](https://img.shields.io/badge/Clean%20Architecture-DDD-green.svg) ![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg) ![Production Ready](https://img.shields.io/badge/Production-Ready-blue.svg)

> **Major Release**: v3.0.0 brings clean architecture, event sourcing, and enterprise-grade features to Second Brain.

## 🚀 **What's New in v3.0.0**

Second Brain v3.0.0 is a complete architectural overhaul designed for production scalability, maintainability, and enterprise deployment.

### **✨ Key Features**

- **🏛️ Clean Architecture**: Domain-driven design with clear separation of concerns
- **📨 Event Sourcing**: Complete audit trail and event-driven architecture
- **🔄 CQRS Pattern**: Optimized read/write separation for scalability
- **📦 Message Queue**: RabbitMQ integration for async processing
- **📊 Observability**: OpenTelemetry tracing, Prometheus metrics, structured logging
- **💾 Caching Layer**: Redis caching with multiple strategies
- **📁 Object Storage**: MinIO/S3-compatible attachment handling
- **🔍 Vector Search**: PostgreSQL with pgvector for embeddings (Qdrant removed)
- **🧪 Comprehensive Testing**: Unit, integration, and e2e test suites

## 🏗️ **Architecture Overview**

```
src/
├── domain/           # Core business logic (entities, value objects, domain events)
├── application/      # Use cases and DTOs
├── infrastructure/   # External services (database, cache, message queue, storage)
└── api/             # FastAPI routes and middleware
```

### **Core Principles**

1. **Domain-Driven Design**: Business logic isolated in the domain layer
2. **Dependency Inversion**: All dependencies point inward
3. **Event-Driven**: Domain events for decoupled communication
4. **Repository Pattern**: Abstract data access
5. **Use Case Pattern**: Clear application boundaries

## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Redis 7+
- RabbitMQ 3.12+
- MinIO (or S3-compatible storage)

### **Docker Compose Setup**

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec api python -m alembic upgrade head

# Access the application
open http://localhost:8000
```

### **Local Development**

```bash
# Clone and setup environment (works on any OS)
git clone https://github.com/yourusername/second-brain.git
cd second-brain
python scripts/setup_dev_environment.py

# Activate virtual environment
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Start services
docker-compose up -d

# Run tests to validate setup
python scripts/test_runner.py --validation

# Start the application
uvicorn src.main:app --reload
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

# Sessions
POST   /api/v1/sessions          # Create session
GET    /api/v1/sessions          # List sessions
GET    /api/v1/sessions/{id}     # Get session with memories

# Health & Metrics
GET    /health                   # Health check
GET    /metrics                  # Prometheus metrics
```

## 🧪 **Testing**

```bash
# Validate environment and run tests
python scripts/test_runner.py --validation   # Environment validation
python scripts/test_runner.py --unit         # Unit tests only
python scripts/test_runner.py --integration  # Integration tests
python scripts/test_runner.py --e2e          # End-to-end tests
python scripts/test_runner.py --all          # All tests (fast)
python scripts/test_runner.py --all --slow   # All tests including slow ones

# Generate coverage report
python scripts/test_runner.py --coverage

# Run linting
python scripts/test_runner.py --lint

# Direct pytest (alternative)
pytest tests/unit/              # Unit tests only
pytest tests/integration/        # Integration tests
pytest -m "unit"                # Unit tests with marker
```

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
- **Issues**: [GitHub Issues](https://github.com/yourusername/second-brain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/second-brain/discussions)

---

Built with ❤️ by the Second Brain team