# Second Brain v4.0.0 - Project Structure

**Last Updated**: August 2, 2025

## 🗂️ Directory Organization

```
second-brain/
├── app/                            # Main application code
│   ├── core/                      # Core infrastructure
│   │   ├── dependencies.py        # Dependency injection
│   │   ├── env_manager.py         # Environment variable management (NEW)
│   │   ├── logging.py             # Logging configuration
│   │   ├── monitoring.py          # Metrics and monitoring
│   │   ├── rate_limiting.py       # Rate limiting
│   │   ├── redis_manager.py       # Redis connection management
│   │   └── security_audit.py      # Security audit utilities
│   │
│   ├── models/                     # Data models
│   │   ├── synthesis/             # Synthesis models (stubs)
│   │   │   ├── websocket_models.py
│   │   │   ├── consolidation_models.py
│   │   │   ├── metrics_models.py
│   │   │   ├── summary_models.py
│   │   │   ├── suggestion_models.py
│   │   │   ├── report_models.py
│   │   │   ├── repetition_models.py
│   │   │   └── advanced_models.py
│   │   ├── memory.py               # Memory models
│   │   ├── user.py                 # User models
│   │   └── api_models.py           # API request/response models
│   │
│   ├── routes/                     # API routes
│   │   └── v2_api_new.py           # V2 API implementation (ONLY API)
│   │
│   ├── services/                   # Business logic services
│   │   ├── synthesis/              # Synthesis services
│   │   ├── memory_service_new.py   # Memory operations
│   │   ├── knowledge_graph_builder.py # Graph builder (stub)
│   │   ├── reasoning_engine.py     # Reasoning (stub)
│   │   └── service_factory.py      # Service instances factory
│   │
│   ├── events/                     # Domain events (minimal stubs)
│   │   ├── __init__.py
│   │   └── domain_events.py
│   │
│   ├── insights/                   # Analytics (minimal stubs)
│   │   ├── __init__.py
│   │   └── models.py
│   │
│   ├── static/                     # Static web files
│   ├── utils/                      # Utility functions
│   ├── app.py                      # FastAPI application entry
│   ├── config.py                   # Configuration (uses env_manager)
│   ├── database_new.py             # Database operations
│   └── dependencies_new.py         # Dependency injection
│
├── tests/                          # Test suites
│   ├── unit/                       # Unit tests (55 passing)
│   ├── integration/                # Integration tests
│   ├── validation/                 # Validation tests
│   └── conftest.py                 # Test configuration
│
├── docs/                           # Documentation
│   ├── ENVIRONMENT_GUIDE.md       # Environment setup guide (NEW)
│   ├── SECURITY_AUDIT_REPORT.md   # Security audit results (NEW)
│   └── [other docs...]
│
├── scripts/                        # Utility scripts (only 3!)
│   ├── check_secrets.py            # Security scanner (NEW)
│   ├── setup_dev_environment.py    # Development setup
│   └── test_runner.py              # Test runner
│
├── migrations/                     # Database migrations
├── examples/                       # Example usage code
├── docker/                         # Docker configuration
│
├── .claude/                        # Claude Code configuration
│   ├── claude.json                 # Claude settings & preferences
│   └── hooks/                      # Automation hooks
│       └── startup.py              # Session startup hook
│
├── .github/                        # GitHub Actions CI/CD
├── .venv/                          # Python virtual environment
│
├── docker-compose.yml              # Docker services
├── Dockerfile                      # Container image
├── Makefile                        # Development commands
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project configuration
├── pytest.ini                      # Test configuration
│
├── .env.example                    # Environment template (ONLY ONE!)
├── .gitignore                      # Git ignore (enhanced security)
│
├── README.md                       # Project documentation
├── SECURITY.md                     # Security guidelines (NEW)
├── LICENSE                         # MIT License
├── TODO.md                         # Current tasks & status
├── CLAUDE.md                       # AI assistant context
├── DEVELOPMENT_CONTEXT.md          # Session history (NEW)
└── PROJECT_STRUCTURE.md           # This file

```

## 🔑 Key Files & Their Purpose

### Core Application
- `app/app.py` - FastAPI application with V2 API routes included
- `app/config.py` - Centralized configuration using env_manager
- `app/core/env_manager.py` - Type-safe environment variable management
- `app/routes/v2_api_new.py` - Complete V2 API implementation
- `app/services/memory_service_new.py` - Memory CRUD operations
- `app/services/service_factory.py` - Singleton service instances

### Configuration & Environment
- `.env.example` - Single template with all configuration options
- `.env` - Local configuration (create from template, never commit)
- `app/core/env_manager.py` - Robust environment management with validation

### Security
- `SECURITY.md` - Comprehensive security guidelines
- `scripts/check_secrets.py` - Automated secret detection
- `.gitignore` - Enhanced with security patterns

### Testing
- `tests/unit/` - 55 unit tests passing
- `tests/conftest.py` - Test fixtures and configuration
- `scripts/test_runner.py` - Cross-platform test execution

### Documentation
- `README.md` - Main project documentation (v4.0.0)
- `CLAUDE.md` - AI assistant context and decisions
- `DEVELOPMENT_CONTEXT.md` - Detailed session history
- `TODO.md` - Current tasks and priorities
- `docs/ENVIRONMENT_GUIDE.md` - Environment setup instructions

## 📊 Statistics

### File Count
- **Total Files**: ~100 (down from 500+)
- **Python Files**: ~60
- **Test Files**: ~30
- **Documentation**: ~15
- **Scripts**: 3 (down from 80+)

### Code Metrics
- **Lines of Code**: ~15,000 (down from 100,000+)
- **Test Coverage**: 55 tests passing
- **API Endpoints**: 10 (V2 only)
- **Models**: 15+ (including stubs)

## 🚀 Quick Navigation

### For Development
1. Start here: `app/app.py`
2. API routes: `app/routes/v2_api_new.py`
3. Business logic: `app/services/memory_service_new.py`
4. Configuration: `app/config.py` + `app/core/env_manager.py`

### For Testing
1. Run tests: `scripts/test_runner.py`
2. Unit tests: `tests/unit/`
3. Test config: `tests/conftest.py`

### For Security
1. Guidelines: `SECURITY.md`
2. Scanner: `scripts/check_secrets.py`
3. Environment: `.env.example` (template only)

### For Documentation
1. Project overview: `README.md`
2. Current tasks: `TODO.md`
3. AI context: `CLAUDE.md`
4. Session history: `DEVELOPMENT_CONTEXT.md`

## 📝 Notes

### Technical Debt
- Files with `_new` suffix need renaming (legacy from v3→v4 migration)
- Synthesis services are mostly stubs (implement as needed)
- Some WebSocket model validation issues

### Design Decisions
- **Single API**: Only V2 exists, no multiple versions
- **Mock Support**: Database optional with in-memory fallback
- **Minimal Scripts**: Only 3 essential scripts remain
- **Unified Environment**: One template, one local file

### Clean Code Principles
- No circular dependencies
- Clear module boundaries
- Consistent naming conventions
- Comprehensive documentation

---

**Remember**: This structure is intentionally minimal and focused. Don't add complexity without clear benefit.