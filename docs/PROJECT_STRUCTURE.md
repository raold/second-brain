# Second Brain Project Structure

This document defines the organization and file structure for the Second Brain project.

## Directory Structure

```
second-brain/
├── src/                          # v3.0.0 source code (Clean Architecture)
│   ├── domain/                   # Domain layer (entities, value objects)
│   ├── application/              # Application layer (use cases, DTOs)
│   ├── infrastructure/           # Infrastructure layer (databases, APIs)
│   └── api/                      # API layer (FastAPI routes, middleware)
├── app/                          # Legacy v2.x source code
├── tests/                        # All test files organized by type
│   ├── unit/                     # Unit tests (fast, no external deps)
│   ├── integration/              # Integration tests (require services)
│   ├── validation/               # Environment and CI validation tests
│   └── e2e/                      # End-to-end tests
├── scripts/                      # Development and utility scripts
│   ├── setup_dev_environment.py # Portable environment setup
│   ├── test_runner.py           # Comprehensive test runner
│   └── test_services.py         # Service connectivity tests
├── config/                       # Configuration files
│   ├── requirements.txt         # Main production dependencies
│   ├── requirements-ci.txt      # CI-specific dependencies
│   └── requirements-dev.txt     # Development dependencies
├── docs/                         # Documentation
│   ├── SETUP.md                 # Development setup guide
│   ├── PROJECT_STRUCTURE.md     # This file
│   └── ARCHITECTURE.md          # Architecture documentation
├── .github/                      # GitHub Actions workflows
│   └── workflows/
├── docker-compose.yml           # Development services (PostgreSQL, Redis)
├── pytest.ini                  # Pytest configuration
├── .gitignore                   # Git ignore rules
└── README.md                    # Project overview
```

## File Organization Rules

### 🚀 **Scripts Directory (`scripts/`)**
**Purpose**: Development, setup, and utility scripts

**What goes here**:
- `setup_dev_environment.py` - Portable environment setup
- `test_runner.py` - Comprehensive test runner
- `test_services.py` - Service connectivity validation
- `validate_environment.py` - Environment validation
- Deployment scripts
- Data migration scripts
- Development utilities

**Naming convention**: `snake_case.py`

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
```bash
# Run all tests
python scripts/test_runner.py --all

# Run specific test types
python scripts/test_runner.py --unit        # Fast unit tests
python scripts/test_runner.py --integration # Integration tests  
python scripts/test_runner.py --validation  # Environment validation
python scripts/test_runner.py --e2e         # End-to-end tests

# Generate coverage report
python scripts/test_runner.py --coverage

# Run linting
python scripts/test_runner.py --lint
```

### CI/CD Integration
The test runner integrates with GitHub Actions:
- Pull requests run: validation + unit + integration tests
- Main branch runs: all tests including E2E
- Nightly runs: performance and stress tests

## Development Workflow

### Setting Up Development Environment
```bash
# Clone repository
git clone <repository-url>
cd second-brain

# Setup environment (works on any OS)
python scripts/setup_dev_environment.py

# Activate environment
.venv/Scripts/activate    # Windows
source .venv/bin/activate # Linux/Mac

# Start services
docker-compose up -d

# Validate setup
python scripts/test_runner.py --validation
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