# Second Brain Project Structure

**🐳 Docker-First Development with Service-Oriented Architecture**

This document defines the current v3.0.0 organization optimized for developer experience.

## Current Directory Structure

```
second-brain/
├── main.py                       # Application entry point
├── Dockerfile                    # Multi-stage Docker build (dev/prod)
├── docker-compose.yml            # Full development stack
├── Makefile                      # Cross-platform development commands

├── app/                          # Main application module
│   ├── services/                 # Business logic layer (moved from root)
│   │   ├── importance_engine.py  # Importance scoring (moved)
│   │   ├── batch_classification_engine.py  # Batch classification (moved)
│   │   ├── memory_deduplication_engine.py  # Deduplication (moved)
│   │   └── bulk_memory_manager.py  # Bulk operations (moved)
│   ├── routes/                   # API endpoints (thin controllers)
│   ├── models/                   # Data models and schemas
│   ├── ingestion/                # File processing and parsing
│   ├── insights/                 # Analytics and insights
│   └── utils/                    # Utility functions

├── scripts/                      # Development automation
│   ├── dev                       # Universal development script
│   ├── setup-bulletproof-venv.py  # Automated .venv creation
│   └── test_runner.py           # Comprehensive test runner

├── tests/                        # All test files organized by type
│   ├── unit/                     # Unit tests (fast, isolated)
│   ├── integration/              # Integration tests (services)
│   ├── validation/               # Environment validation
│   └── comprehensive/            # Full end-to-end tests

├── config/                       # Configuration management
│   ├── requirements.txt         # Main dependencies
│   ├── requirements-production.txt  # Production-only deps
│   └── requirements-ci.txt      # CI-specific deps

├── docs/                         # Documentation (updated)
├── archive/                      # Previous versions (v1.x, v2.x)
├── .venv/                        # Virtual environment (auto-created)
├── activate-venv.bat            # Windows activation (auto-created)
├── activate-venv.sh             # Unix activation (auto-created)
└── session_storage/             # Session persistence
```

## File Organization Rules

### 🚀 **Scripts Directory (`scripts/`)**
**Purpose**: Development automation and environment management

**Current scripts**:
- `dev` - Universal development script (Docker-first with .venv fallback)
- `setup-bulletproof-venv.py` - Automated .venv creation with validation
- `test_runner.py` - Comprehensive test runner
- `setup_dev_environment.py` - Legacy setup script

**Key Features**:
- **Cross-Platform**: Works on Windows, macOS, Linux
- **Smart Detection**: Automatically chooses Docker or .venv
- **Environment Validation**: Health checks and dependency verification
- **Self-Healing**: Automatic error recovery and environment repair

**Naming convention**: `kebab-case` for main scripts, `snake_case.py` for Python modules

### 🧪 **Tests Directory (`tests/`)**
**Purpose**: All testing code organized by test type

#### `tests/unit/`
- Fast tests with no external dependencies
- Test individual functions/classes in isolation
- Should run in < 5 seconds total
- Use mocks for external dependencies

#### `tests/integration/`
- Test interaction between components
- May require database, Redis, or other services
- Test API endpoints, database operations
- Use real services (Docker containers)

#### `tests/validation/`
- Environment setup validation
- CI/CD pipeline validation
- Development environment health checks
- Dependency conflict detection

#### `tests/e2e/`
- Full application workflow tests
- Test complete user journeys
- Browser automation tests (if applicable)
- Performance tests

**Test file naming**: `test_*.py` or `*_test.py`

### ⚙️ **Config Directory (`config/`)**
**Purpose**: Configuration and requirements files

**What goes here**:
- `requirements*.txt` files
- Environment configuration templates
- Docker configuration files
- Database schema files
- CI/CD configuration

### 📚 **Docs Directory (`docs/`)**
**Purpose**: Project documentation

**What goes here**:
- Setup guides
- Architecture documentation
- API documentation
- Development guides
- Project status updates

## File Naming Conventions

| File Type | Convention | Examples |
|-----------|------------|----------|
| Python modules | `snake_case.py` | `user_service.py`, `memory_repository.py` |
| Test files | `test_*.py` | `test_user_service.py`, `test_memory_domain.py` |
| Scripts | `snake_case.py` | `setup_dev_environment.py`, `migrate_data.py` |
| Config files | `kebab-case.ext` | `requirements-ci.txt`, `docker-compose.yml` |
| Documentation | `SCREAMING_SNAKE_CASE.md` | `README.md`, `PROJECT_STRUCTURE.md` |

## Testing Strategy

### Test Pyramid
```
    /\     E2E Tests (few, slow, high confidence)
   /  \    
  /____\   Integration Tests (some, medium speed)
 /      \  
/________\  Unit Tests (many, fast, low-level)
```

### Test Commands

#### Docker-First Testing (Recommended)
```bash
# Make commands (cross-platform)
make test                    # All tests in containers
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-validation        # Environment validation
```

#### Universal Testing Scripts
```bash
# Works with Docker or .venv automatically
python scripts/dev test --test-type all
python scripts/dev test --test-type unit
python scripts/dev test --test-type integration
python scripts/dev test --test-type validation
```

#### Direct Testing (Fallback)
```bash
# Windows (.venv fallback)
.venv\Scripts\python.exe scripts/test_runner.py --validation

# Unix (.venv fallback)  
.venv/bin/python scripts/test_runner.py --validation
```

### CI/CD Integration
The test runner integrates with GitHub Actions:
- Pull requests run: validation + unit + integration tests
- Main branch runs: all tests including E2E
- Nightly runs: performance and stress tests

## Development Workflow

### Setting Up Development Environment

#### Instant Setup (Recommended)
```bash
# Clone repository
git clone <repository-url>
cd second-brain

# One-command setup (Docker + .venv fallback)
make setup

# Start development
make dev

# Check status
make status
```

#### Manual Setup (if needed)
```bash
# Docker-first approach
docker-compose up --build

# OR bulletproof .venv creation
python scripts/setup-bulletproof-venv.py

# Activate environment
activate-venv.bat        # Windows (auto-created)
./activate-venv.sh       # Unix (auto-created)

# Validate setup
make test-validation
```

### Adding New Features
1. Write tests first (TDD approach)
2. Place tests in appropriate test directory
3. Use test markers to categorize tests
4. Run test suite before committing
5. Ensure CI pipeline passes

### File Organization Guidelines
- **Keep root directory clean** - only essential project files
- **Group related files** - use subdirectories effectively  
- **Follow naming conventions** - consistent across project
- **Document new directories** - update this file when adding structure
- **Regular cleanup** - remove temporary and obsolete files

## Quality Gates

Before merging to main branch:
- ✅ All validation tests pass
- ✅ Unit test coverage ≥ 70%
- ✅ Integration tests pass
- ✅ Linting checks pass
- ✅ No critical security vulnerabilities
- ✅ Documentation updated

This structure ensures:
- 🎯 **Clear separation of concerns**
- 🚀 **Fast feedback loops**
- 🔧 **Easy maintenance**
- 📈 **Scalable testing strategy**
- 🤝 **Consistent developer experience**