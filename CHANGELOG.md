# Changelog

All notable changes to the Second Brain project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-07-17

### 🚀 **MAJOR RELEASE - Complete System Refactor**

**BREAKING CHANGES**: Complete architectural overhaul with 90% code reduction and simplified single-database architecture.

#### **Added**
- **PostgreSQL pgvector** for vector similarity search (replacing Qdrant)
- **FastAPI application** with 165 lines (90% reduction from 1,596 lines)
- **Mock database** for cost-free testing without OpenAI API or database connection
- **Direct SQL queries** using asyncpg (no ORM overhead)
- **Environment-only configuration** with simple .env setup
- **Token-based authentication** for API security
- **JSONB metadata storage** for flexible data structures
- **Comprehensive test suite** with 90%+ coverage using mock database
- **Docker deployment** with single database system
- **Performance optimization** with automatic HNSW indexing
- **System status endpoint** for monitoring and performance metrics
- **Automatic index creation** at 1000+ memories for optimal performance

#### **Changed**
- **Database architecture**: Single PostgreSQL with pgvector (removed Qdrant)
- **Dependencies**: Reduced from 50+ to 5 core packages
- **Configuration**: Simplified to environment variables only
- **API endpoints**: Streamlined to 7 essential endpoints (including `/status`)
- **Documentation**: Complete rewrite for v2.0.0 architecture
- **Testing**: Full mock database implementation for CI/CD without external dependencies

#### **Removed**
- **Qdrant vector database** → PostgreSQL pgvector
- **Complex caching layers** → Direct database access
- **ORM complexity** → Pure SQL queries
- **Extensive monitoring** → Basic logging with performance metrics
- **Plugin architecture** → Core functionality focus
- **WebSocket streaming** → REST API only
- **Background tasks** → Synchronous operations
- **Intent detection** → Simplified operations
- **Version history** → Single version per memory
- **Feedback systems** → Core CRUD operations
- **Complex configuration** → Environment variables only

#### **Migration Notes**
- **Database**: Add pgvector extension and embedding column
- **Configuration**: Replace config files with .env variables
- **API**: Core endpoints remain compatible
- **Dependencies**: Update to minimal requirements
- **Testing**: Use mock database for development and CI/CD

---

## [1.5.0] - 2025-07-15

### **Added**
- Real-time WebSocket streaming for LLM and TTS output
- Model version tracking and version history per record
- Intent detection/classification (question, reminder, note, todo, command, other)
- Memory persistence layer with PostgreSQL and SQL querying
- Feedback/correction loop (edit, delete, correct intent, upvote)
- Replay and summarization endpoints for memory synthesis
- Personalized ranking with feedback tracking
- Plugin system for reminders, webhooks, file/PDF search
- Electron/mobile/PWA clients with voice, TTS, and advanced UI/UX
- Advanced UI with theming, settings, accessibility, and export
- Performance optimizations with LRU caching, Prometheus metrics, Sentry, Grafana

---

## [1.4.0] - 2025-07-14

### **Added**
- **Intent Detection**: OpenAI LLM auto-classification of transcripts
- **Memory Persistence**: PostgreSQL integration with SQLAlchemy async models
- **Metadata API**: `/memories/search` endpoint for PostgreSQL queries
- **Database Integration**: Async DB connection and initialization scripts

### **Changed**
- Backend models updated for intent classification and PostgreSQL persistence
- Enhanced test coverage for ingestion flow and intent detection accuracy

---

## [1.3.0] - 2025-07-14

### **Added**
- **Advanced Version History UI**: Web interface for record management
- **Records API**: List records with filtering and pagination
- **Prometheus Metrics**: `/metrics` endpoint for monitoring
- **Sentry Error Monitoring**: Optional error tracking integration
- **Hybrid Search**: Metadata filtering with vector similarity
- **Ranking Pipeline**: Weighted search results with explanations

### **Changed**
- Improved UI/UX for version history and record management
- Enhanced documentation and cross-linking

### **Fixed**
- Robust testing with mocked external dependencies

---

## [1.2.4] - 2025-07-14

### **Added**
- Prometheus metrics integration
- Sentry error monitoring integration

---

## [1.2.3] - 2025-07-14

### **Added**
- Version history tracking for model/embedding versions
- `/records/{id}/version-history` API endpoint
- Simple web UI for version history display

---

## [1.2.2] - 2025-07-14

### **Added**
- Comprehensive `docs/TESTING.md` guide
- Cross-linked documentation files
- Improved mocking and testing approach documentation

### **Changed**
- Enhanced documentation clarity and completeness

---

## [1.2.0] - 2025-07-14

### **Added**
- **CI Pipeline Optimization**: 50-70% faster builds with caching
- **Deployment Pipeline**: Automated multi-environment deployments
- **Environment Management**: Staging and production configurations
- **Docker Optimizations**: Better layer caching and Buildx integration
- **Performance Monitoring**: Comprehensive metrics and guidelines

### **Changed**
- Consolidated router functionality
- Proper Pydantic v2 compatibility
- Enhanced type hints and error handling

### **Fixed**
- Import path inconsistencies
- Test mocks for correct import paths

---

## [1.1.0] - 2025-07-14

### **Added**
- Expanded `.env.example` with all configuration options
- `SECURITY.md` with policies and reporting guidelines
- `CONTRIBUTING.md` with contribution guidelines
- Docker Compose healthchecks for API and Qdrant services
- CI-safe defaults with `APP_ENV=ci` support

### **Changed**
- Centralized configuration via `Config` class
- Environment-aware authentication and token management
- Explicit Docker Compose networking configuration

### **Fixed**
- Authentication failures in CI environments
- Docker Compose volume paths and network configurations

---

*For detailed information about any release, see the corresponding documentation and commit history.* 
