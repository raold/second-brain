[![CI Pipeline](https://github.com/raold/second-brain/actions/workflows/ci.yaml/badge.svg)](https://github.com/raold/second-brain/actions/workflows/ci.yaml)
[![Deploy](https://github.com/raold/second-brain/actions/workflows/deploy.yml/badge.svg)](https://github.com/raold/second-brain/actions/workflows/deploy.yml)

# Second Brain - AI Memory Assistant

> Ingest, Embed, Search, and Replay Text Semantically using OpenAI Embeddings and Qdrant Vector DB. Real-time processing with comprehensive testing and CI/CD pipeline.

## 📦 Project Overview
This API enables ingestion of text data, which is embedded via OpenAI's `text-embedding-3-small` model and stored in Qdrant for semantic search. Memories are persisted as Markdown files with metadata for advanced querying and replay capabilities.

## 🚀 Features

### Core Memory System
- **Semantic vector search** with Qdrant vector database
- **OpenAI embeddings** with `text-embedding-3-small` model
- **Dual storage system**: Markdown files + PostgreSQL database
- **Intent detection**: Automatic classification (questions, todos, reminders, commands, notes)
- **Version history tracking** with parent-child memory relationships
- **Structured metadata** with tags, priority levels, and context tracking

### Performance & Optimization
- **Advanced caching system** with TTL, LRU eviction, and hit rate tracking
- **Connection pooling** for PostgreSQL with health monitoring
- **Background job processing** for parallel storage operations
- **Performance monitoring** with comprehensive metrics and recommendations
- **Smart eviction algorithms** based on access patterns
- **Query optimization** with 10-12ms average response times

### Database & Storage
- **PostgreSQL integration** with async connection pooling
- **Database schema** with proper indexing and timezone support
- **Health checks** for all external dependencies
- **Graceful degradation** when storage services are unavailable
- **Migration support** with version-controlled schema changes
- **Backup and recovery** mechanisms

### API & Authentication
- **Token-based authentication** with environment-specific tokens
- **RESTful API** with FastAPI and automatic OpenAPI documentation
- **Advanced search endpoints** with filtering and ranking
- **Performance monitoring endpoints** (`/performance`, `/performance/cache`, `/performance/database`)
- **Health monitoring** with detailed service status
- **Comprehensive error handling** and validation

### Development & Operations
- **Production-grade logging** with structured JSON and correlation IDs
- **Comprehensive test suite** (89 passed tests) with integration and performance testing
- **CI/CD Pipeline** with advanced caching (50-70% faster builds)
- **Multi-environment deployment** (staging → production)
- **Docker layer caching** for 60-80% faster builds
- **Makefile** for streamlined development workflow
- **Modular architecture** with refactored, testable components

## ⚙️ Requirements
- Docker + Docker Compose
- OpenAI API Key
- Python 3.11+ (for local dev)
- GitHub repository (for CI/CD features)

## 🏗️ Project Structure
```
second-brain/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry
│   ├── router.py              # API endpoints & routing
│   ├── auth.py                # Auth middleware
│   ├── config.py              # Config management
│   ├── models.py              # Pydantic models
│   ├── handlers.py            # Business logic
│   ├── static/                # Static UI assets (version history, etc)
│   ├── api/
│   │   └── websocket.py       # WebSocket endpoints
│   ├── utils/
│   │   ├── logger.py          # structlog config
│   │   └── openai_client.py   # OpenAI embedding client (with caching)
│   ├── storage/
│   │   ├── markdown_writer.py # Markdown file operations
│   │   └── shell_runner.py    # Shell command execution
├── data/
│   └── memories/              # Additional memory storage
├── tests/
├── docs/
```

## 🔧 Setup

### Local Development

1. Clone the repo:
```bash
git clone <repo-url>
cd second-brain
```

2. Create a `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Build and run:
```bash
make build
make up
```

### Production Deployment

1. **Set up GitHub Secrets**:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `DOCKER_REGISTRY`: Your Docker registry (e.g., `ghcr.io/username`)
   - `STAGING_API_TOKENS`: Staging environment tokens
   - `PRODUCTION_API_TOKENS`: Production environment tokens

2. **Create GitHub Environments**:
   - Go to Settings → Environments
   - Create "staging" and "production" environments
   - Configure protection rules as needed

3. **Deploy automatically**:
   - Push to `main` branch triggers CI
   - Successful CI automatically deploys to staging
   - Manual approval deploys to production

## 🏁 Getting Started

See the [full Deployment Instructions](./docs/DEPLOYMENT.md) for detailed setup and configuration steps.

### Local Development URLs
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### Staging Environment URLs
- **API Docs**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Qdrant Dashboard**: [http://localhost:6334/dashboard](http://localhost:6334/dashboard)

## ✅ API Endpoints

### Core Memory Operations
- `POST /ingest` - Ingest text with OpenAI embeddings and dual storage
- `GET /search?q=text` - Semantic search with vector similarity
- `GET /ranked_search?q=text` - Advanced search with ranking and scoring
- `POST /transcribe` - Audio transcription with file upload support

### Health & Monitoring
- `GET /health` - Comprehensive health check with service status
- `GET /performance` - System performance overview with health score
- `GET /performance/cache` - Cache statistics and hit rates
- `GET /performance/database` - Database performance metrics
- `GET /performance/recommendations` - AI-driven optimization suggestions
- `POST /performance/cache/clear` - Manual cache management

### Advanced Features
- **Intent Detection**: Automatic memory classification
- **Version History**: Parent-child memory relationships
- **Filtering**: Search by intent, tags, priority, date ranges
- **Analytics**: User feedback and search history tracking

## 🧪 Testing
```bash
make test
```
- See [Testing Guide](./docs/TESTING.md) for our approach to mocking OpenAI and Qdrant in integration tests.

## 🧹 Formatting
```bash
make lint
```

## 📝 Logging
- Structured JSON logs via [structlog](https://www.structlog.org/), compatible with log aggregation tools (Loki, ELK, etc).
- Each request gets a unique correlation ID (`X-Request-ID`), included in all logs for distributed tracing.
- Search logs by correlation ID to trace requests end-to-end.
- See [Architecture Overview](./docs/ARCHITECTURE.md#logging--monitoring-architecture) for a diagram of the logging and monitoring flow.

## 🚀 CI/CD Features

### Performance Optimizations
- **50-70% faster CI builds** through intelligent caching
- **Docker layer caching** for 60-80% faster builds
- **Parallel job execution** (setup, docker-build, lint, test)
- **Smart cache invalidation** based on file changes

### Deployment Automation
- **Automatic deployment** after successful CI
- **Multi-environment support** (staging → production)
- **Health checks** and rollback capabilities
- **Environment protection** with approval gates

### Environment Management
- **Environment-specific configurations** with separate Docker Compose files
- **GitHub Secrets integration** for secure credential management
- **Resource limits** and production optimizations
- **Comprehensive documentation** and setup guides

## 📚 Documentation

- [**Architecture Overview**](./docs/ARCHITECTURE.md) — System design and architecture
- [**Deployment Guide**](./docs/DEPLOYMENT.md) — How to deploy in production and staging  
- [**Usage Examples**](./docs/USAGE.md) — Example API requests and usage patterns

## 📋 Resources

### 📖 Documentation
- [**Architecture Overview**](./docs/ARCHITECTURE.md) - System design and architecture
- [**Deployment Guide**](./docs/DEPLOYMENT.md) - Production deployment instructions
- [**Usage Examples**](./docs/USAGE.md) - API usage patterns and examples

### 🛠️ Development
- [**Makefile**](./Makefile) - Development commands and shortcuts
- [**Requirements**](./requirements.txt) - Python dependencies
- [**Docker Configuration**](./Dockerfile) - Container setup

### 🔒 Security & Legal
- [**Security Policy**](./SECURITY.md) - Security vulnerabilities and reporting
- [**License**](./LICENSE) - Project license terms
- [**Changelog**](./CHANGELOG.md) - Release history and changes

### 🚀 CI/CD & Deployment
- [**Development Environment**](./docker-compose.yml) - Local development setup

### 📊 Monitoring & Health
- **API Health Check**: `GET /health` - Service health status
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard) - Vector database management
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs) - Interactive API docs

## 📊 Metrics & Monitoring
- **Prometheus metrics** available at `/metrics` for all API endpoints (request count, latency, errors).
- **Sentry error monitoring** enabled if `SENTRY_DSN` is set in the environment.
- See [Architecture Overview](./docs/ARCHITECTURE.md#metrics--monitoring) for details.

## 🆕 Recent Improvements (v1.4.0)

- **Comprehensive Test Suite**: Added unit tests, integration tests, and error scenario testing with 90%+ coverage
- **Code Refactoring**: Broke down monolithic functions into smaller, testable components
- **Improved Error Handling**: Enhanced error scenarios and edge case handling
- **Test Infrastructure**: Shared fixtures, mocking improvements, and parallel test execution
- **Documentation Updates**: Accurate project structure and API documentation

## 📋 Roadmap

### 🔄 Version 1.5.0 - Advanced Storage & Performance (IN PROGRESS)
**Focus: Database Integration & Optimization**

- 🔄 **PostgreSQL Integration** (Code Complete, Deployment Pending)
  - ✅ Added `app/storage/postgres_client.py` with async connection pooling
  - ✅ Implemented SQL-based memory querying and filtering
  - ✅ Created comprehensive database schema with proper indexing
  - ❌ **PostgreSQL not running in production** - container setup needed
  - ✅ Dual storage: Markdown files + PostgreSQL with graceful degradation

- ✅ **Performance Optimizations**
  - ✅ Implemented advanced LRU caching with TTL and smart eviction
  - ✅ Added connection pooling design for PostgreSQL (20 connections, 30 overflow)
  - ✅ Background job processing for parallel storage operations
  - ✅ Performance monitoring endpoints and health scoring

- 🔄 **Advanced Search Features** (Partially Complete)
  - ✅ Intent-based memory classification and filtering (code level)
  - ✅ Advanced filtering by date ranges, intent types, tags, and priority (code level)
  - ❌ **Version history and analytics require PostgreSQL to be running**
  - ❌ Search analytics and user feedback collection (needs DB)

- ✅ **Monitoring & Observability**
  - ✅ Comprehensive health checks for all external dependencies
  - ✅ Performance monitoring with system health scoring
  - ✅ Cache hit rate tracking and optimization recommendations
  - ⚠️ PostgreSQL metrics show connection failures

**Current Status**: 
- **Code Implementation**: 90% complete
- **Infrastructure Deployment**: 30% complete (PostgreSQL not running)
- **Test Results**: 85.7% success rate with Markdown-only fallback mode
- **Production Ready**: ❌ Requires PostgreSQL container setup

### 🎯 Version 1.6.0 - Plugin System & Real-time Features (CURRENT)
**Focus: Extensibility & Live Processing**

- **Plugin Architecture**
  - Create `app/plugins/` framework with plugin manager
  - Built-in plugins: reminders, webhooks, file search, calendar integration
  - Plugin marketplace and documentation system
  - Configurable plugin pipelines and event handlers

- **Real-time WebSocket API**
  - Add `app/api/websocket.py` for live streaming
  - Real-time LLM output streaming for chat interfaces
  - Live transcription processing and intent detection
  - WebSocket authentication and connection management

- **Intent Detection & Classification**
  - Advanced LLM-based intent classification
  - Custom intent types and user-defined categories
  - Intent-based routing and automated actions
  - Machine learning model for intent prediction improvement

- **Feedback & Correction System**
  - Memory editing and correction workflows
  - User feedback collection (upvote/downvote/edit)
  - Automated quality scoring and content improvement
  - Version history and change tracking

### 🚀 Version 1.7.0 - Client Applications & Advanced UI
**Focus: User Interfaces & Multi-platform Support**

- **Electron Desktop Client**
  - Create `electron/` directory with voice assistant interface
  - Real-time speech-to-text and text-to-speech integration
  - Advanced UI with dark/light themes and accessibility features
  - Offline mode with local caching and sync capabilities

- **Mobile & PWA Support**
  - Add `mobile/` Progressive Web App
  - Touch-optimized interface for mobile devices
  - Voice commands and audio recording on mobile
  - Push notifications for reminders and updates

- **Advanced Memory Features**
  - Memory replay and summarization endpoints
  - Automated memory consolidation and archiving
  - Smart memory suggestions based on context
  - Memory export in multiple formats (PDF, JSON, Markdown)

- **Enterprise Features**
  - Multi-tenant support with user isolation
  - Role-based access control (RBAC)
  - Audit logging and compliance features
  - Backup and disaster recovery automation

### 🔄 Post-1.7.0 Future Considerations
- **AI Model Integration**: Support for multiple embedding models and LLM providers
- **Collaborative Features**: Shared memory spaces and team collaboration
- **Advanced Analytics**: Memory usage analytics and insights dashboard
- **API Ecosystem**: GraphQL API, advanced rate limiting, API versioning

## 🔒 Security Vulnerabilities

Please report any security vulnerabilities **privately** via [security@oldham.io](mailto:security@oldham.io).  
Do **not** open public issues for security concerns — see [SECURITY.md](./SECURITY.md) for full details.
