# Second Brain v4.0.0 - Project Structure

## 🗂️ Directory Organization

```
second-brain/
├── app/                    # Main application code
│   ├── core/              # Core infrastructure (dependencies, logging, monitoring)
│   ├── models/            # Data models (Memory, User, API models)
│   ├── routes/            # API routes (v2_api_new.py)
│   ├── services/          # Business logic services
│   │   ├── memory_service_new.py
│   │   ├── knowledge_graph_builder.py
│   │   ├── reasoning_engine.py
│   │   ├── service_factory.py
│   │   └── synthesis/     # Synthesis services
│   ├── static/            # Static web files
│   ├── utils/             # Utility functions
│   ├── app.py            # Main FastAPI application
│   ├── config.py         # Configuration management
│   ├── database_new.py   # Database operations
│   └── dependencies_new.py # Dependency injection
│
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── validation/       # Validation tests
│   └── conftest.py      # Test configuration
│
├── docs/                  # Documentation
│   ├── project-status/   # Project status reports
│   ├── development/      # Development guides
│   ├── deployment/       # Deployment documentation
│   └── API_V2_UNIFIED_SPECIFICATION.md
│
├── scripts/              # Utility scripts
│   ├── test_runner.py
│   ├── setup_dev_environment.py
│   └── migrate.py
│
├── migrations/           # Database migrations
├── examples/             # Example usage code
├── docker/              # Docker configuration
│
├── .github/             # GitHub Actions CI/CD
├── .venv/               # Python virtual environment
│
├── docker-compose.yml   # Docker compose configuration
├── Dockerfile          # Main Docker image
├── requirements.txt    # Python dependencies
├── pyproject.toml     # Project configuration
├── pytest.ini         # Test configuration
├── README.md          # Project documentation
├── LICENSE            # MIT License
├── TODO.md            # Current tasks
└── CLAUDE.md          # AI assistant context

```

## 🔑 Key Files

### Application Core
- `app/app.py` - FastAPI application entry point
- `app/routes/v2_api_new.py` - V2 API implementation
- `app/services/memory_service_new.py` - Memory management service
- `app/models/memory.py` - Memory data models

### Configuration
- `app/config.py` - Application configuration
- `.env.example` - Environment variables template
- `docker-compose.yml` - Docker services configuration

### Testing
- `tests/unit/` - Unit test files
- `tests/conftest.py` - Test fixtures and configuration
- `scripts/test_runner.py` - Test execution script

### Documentation
- `README.md` - Main project documentation
- `docs/API_V2_UNIFIED_SPECIFICATION.md` - API documentation
- `TODO.md` - Current development tasks
- `CLAUDE.md` - AI assistant instructions

## 🚀 Quick Start

```bash
# Setup environment
make setup

# Run development server
make dev

# Run tests
make test

# Access API
open http://localhost:8000/docs
```

## 📝 Notes

- All old/deprecated code has been removed
- V2 API is the only implementation
- Clean, minimal structure focused on core functionality
- Docker-first development approach