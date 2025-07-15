[![CI Pipeline](https://github.com/raold/second-brain/actions/workflows/ci.yaml/badge.svg)](https://github.com/raold/second-brain/actions/workflows/ci.yaml)
[![Deploy](https://github.com/raold/second-brain/actions/workflows/deploy.yml/badge.svg)](https://github.com/raold/second-brain/actions/workflows/deploy.yml)

# LLM Output Processor

> Ingest, Embed, Search, Replay, and Summarize Text Semantically using OpenAI Embeddings, Qdrant Vector DB, and Postgres. Now with real-time streaming, intent detection, feedback/correction, plugin system, Electron/mobile/PWA support, and advanced UI/UX.

## 📦 Project Overview
This API enables ingestion of text data, which is embedded via OpenAI's `text-embedding-3-small` model and stored in Qdrant for semantic search. Memories and meta information are persisted in Postgres for advanced querying, replay, and personalized ranking.

## 🚀 Features
- **Token-based authentication** with environment-specific tokens
- **Production-grade logging** with rotation and environment-specific levels
- **Retry and backoff** for OpenAI API with tenacity
- **Dimension validation** for embeddings
- **Automated test suite** (pytest, Jest, Playwright) with comprehensive coverage
- **Makefile** for streamlined development workflow
- **CI/CD Pipeline** with advanced caching, Electron build/test, and artifact upload
- **Multi-environment deployment** (staging → production)
- **Docker layer caching** for 60-80% faster builds
- **Environment-specific configurations** with secure secret management
- **Real-time WebSocket streaming** for LLM output and TTS audio
- **Model version tracking** and version history per record
- **Intent detection/classification** (question, reminder, note, todo, command, other)
- **Memory persistence layer** with Postgres and SQL querying
- **Feedback/correction loop** (edit, delete, correct intent, upvote)
- **Replay and summarization** endpoints for memory synthesis
- **Personalized ranking** with feedback tracking
- **Plugin system** for reminders, webhooks, file/PDF search, and more
- **Electron/mobile/PWA clients** with voice, TTS, and advanced UI/UX
- **Advanced UI**: version history, theming, settings, accessibility, and export
- **Performance optimizations**: LRU caching, Prometheus metrics, Sentry, Grafana

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
│   │   ├── __init__.py
│   │   ├── logger.py          # structlog config
│   │   └── openai_client.py   # OpenAI embedding client (with caching)
│   ├── storage/
│   │   ├── qdrant_client.py   # Qdrant vector DB client (with caching)
│   │   ├── markdown_writer.py # Markdown file ops
│   │   ├── shell_runner.py    # Shell command exec
│   │   └── postgres_client.py # Postgres memory persistence
│   ├── plugins/               # Plugin system and integrations
│   ├── data/
│   │   ├── memories/          # Markdown memory files
│   │   └── tasks.md           # Task management
├── electron/                  # Electron voice assistant client
├── mobile/                    # Mobile/PWA client
├── tests/
│   ├── __init__.py
│   ├── test_health.py         # Health endpoint tests
│   ├── test_ingest.py         # Ingestion endpoint tests
│   ├── test_search.py         # Search endpoint tests
│   ├── test_ranked_search.py  # Hybrid/ranking search tests
│   ├── test_payload.json      # Test data
│   └── client/
│       └── ws_client_example.html
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── USAGE.md
│   ├── CI_CACHING.md
│   ├── ENVIRONMENT_VARIABLES.md
│   ├── CONTRIBUTING.md
│   ├── TESTING.md
│   ├── grafana_llm_observability_dashboard.json
│   ├── logging_monitoring_architecture.mmd
│   ├── architecture.puml
│   ├── system_architecture.png
│   ├── SECURITY.md
│   ├── LICENSE
│   └── CHANGELOG.md
├── logs/                      # Log files (gitignored)
├── qdrant_data*/              # Qdrant data (dev/staging/prod, gitignored)
├── docker-compose*.yml        # Compose files for all envs
├── Dockerfile
├── requirements.txt
├── Makefile
├── ruff.toml
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
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

- `GET /health` - Health check
- `POST /ingest` - Ingest a text payload (with intent detection, versioning, and Postgres persistence)
- `GET /search?q=text` - Search semantically (Qdrant + hybrid ranking)
- `GET /ws/generate` - Real-time LLM output streaming (WebSocket)
- `GET /models` - List current model/embedding versions
- `GET /records` - List/search records with filtering and pagination
- `GET /records/{id}/version-history` - Get version history for a record
- `POST /feedback` - Submit feedback (upvote, correct, ignore)
- `POST /memories/search` - SQL query for memories/metadata (Postgres)
- `POST /memories/summarize` - Summarize memories via LLM
- `POST /plugin/{name}` - Trigger plugin actions (reminder, webhook, file search, etc)

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

- [**CI Caching Strategy**](./docs/CI_CACHING.md) — How CI/CD caching works and how to optimize builds
- [**Environment Variables**](./docs/ENVIRONMENT_VARIABLES.md) — All environment configuration options
- [**Deployment Guide**](./docs/DEPLOYMENT.md) — How to deploy in production and staging
- [**Architecture Overview**](./docs/ARCHITECTURE.md) — System design and architecture
- [**Usage Examples**](./docs/USAGE.md) — Example API requests and usage patterns
- [**Contributing Guidelines**](./docs/CONTRIBUTING.md) — How to contribute to this project
- [**Testing Guide**](./docs/TESTING.md) — How to run and extend tests, and our mocking approach

## 📋 Resources

### 📖 Documentation
- [**Architecture Overview**](./docs/ARCHITECTURE.md) - System design and architecture
- [**Deployment Guide**](./docs/DEPLOYMENT.md) - Production deployment instructions
- [**Usage Examples**](./docs/USAGE.md) - API usage patterns and examples
- [**CI Caching Strategy**](./docs/CI_CACHING.md) - Performance optimization guide
- [**Environment Variables**](./docs/ENVIRONMENT_VARIABLES.md) - Configuration management
- [**Testing Guide**](./docs/TESTING.md) - Test running and mocking best practices

### 🛠️ Development
- [**Contributing Guidelines**](./docs/CONTRIBUTING.md) - How to contribute to the project
- [**Makefile**](./Makefile) - Development commands and shortcuts
- [**Requirements**](./requirements.txt) - Python dependencies
- [**Docker Configuration**](./Dockerfile) - Container setup

### 🔒 Security & Legal
- [**Security Policy**](./docs/SECURITY.md) - Security vulnerabilities and reporting
- [**License**](./docs/LICENSE) - AGPLv3 license terms
- [**Changelog**](./docs/CHANGELOG.md) - Release history and changes

### 🚀 CI/CD & Deployment
- [**CI Pipeline**](./.github/workflows/ci.yaml) - Continuous integration workflow
- [**Deployment Pipeline**](./.github/workflows/deploy.yml) - Automated deployment workflow
- [**Development Environment**](./docker-compose.yml) - Local development setup
- [**Staging Environment**](./docker-compose.staging.yml) - Staging deployment configuration
- [**Production Environment**](./docker-compose.production.yml) - Production deployment configuration

### 📊 Monitoring & Health
- **API Health Check**: `GET /health` - Service health status
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard) - Vector database management
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs) - Interactive API docs

## 📊 Metrics & Monitoring
- **Prometheus metrics** available at `/metrics` for all API endpoints (request count, latency, errors).
- **Sentry error monitoring** enabled if `SENTRY_DSN` is set in the environment.
- See [Architecture Overview](./docs/ARCHITECTURE.md#metrics--monitoring) for details.

## 🆕 Major Features (v1.4.0+)

- **Intent Detection & Classification**: Auto-tags transcripts with intent (question, reminder, note, todo, command, other) using OpenAI LLM.
- **Memory Persistence Layer**: Stores all memories and metadata in Postgres for advanced querying, replay, and personalized ranking.
- **Feedback & Correction Loop**: Edit, delete, correct intent, and upvote memories via API and UI.
- **Replay & Summarization**: Aggregate and summarize related memories for "recall everything about X" workflows.
- **Plugin System**: Extensible plugins for reminders, webhooks, file/PDF search, and more.
- **Electron/Mobile/PWA Clients**: Voice assistant pipeline with real-time streaming, TTS, and advanced UI/UX.
- **Advanced UI/UX**: Version history, theming, settings, accessibility, and export features.
- **Performance & Observability**: LRU caching, Prometheus metrics, Sentry error monitoring, Grafana dashboards.

## 📋 Roadmap
- **v1.3.0**: Full test mocking, metrics/monitoring, API rate limiting
- **v1.4.0**: Blue-green deployment, database migration automation
- **v1.5.0**: Advanced caching strategies, performance monitoring

## 🔒 Security Vulnerabilities

Please report any security vulnerabilities **privately** via [security@oldham.io](mailto:security@oldham.io).  
Do **not** open public issues for security concerns — see [SECURITY.md](./SECURITY.md) for full details.
