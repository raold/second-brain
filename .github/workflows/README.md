# Second Brain v3.0.0 CI/CD Workflows

This directory contains the GitHub Actions workflows for Second Brain v3.0.0 (Clean Architecture).

## Active Workflows

### Core Testing
- **`test-v3.yml`** - Main CI/CD pipeline for v3.0.0 Clean Architecture
  - Runs on: Push to main/v3.0.0 branches, PRs
  - Tests: Domain layer, application layer, infrastructure layer
  - Features: PostgreSQL with pgvector, dependency validation, portable .venv setup

### Feature Testing  
- **`test-synthesis.yml`** - Specialized testing for synthesis features
  - Runs on: Changes to synthesis-related code, manual dispatch
  - Tests: Synthesis models, services, and routes
  - Compatible with both v2.x (app/) and v3.0.0 (src/) architectures

## Environment Setup

Both workflows use the project's standardized environment setup:
- **Virtual Environment**: Uses `.venv` with portable setup via `scripts/setup_dev_environment.py`
- **Testing**: Uses `scripts/test_runner.py` for comprehensive test execution
- **Dependencies**: Installs from `config/requirements-ci.txt` for CI-specific needs

## Key Features

### ✅ **Clean Architecture Support**
- Domain layer testing (entities, value objects)
- Application layer testing (use cases, DTOs) 
- Infrastructure layer testing (repositories, external services)
- API layer testing (FastAPI routes, middleware)

### 🚀 **Modern CI/CD**
- PostgreSQL 16 with pgvector extension
- Redis caching support
- Dependency conflict resolution
- Portable environment across different machines

### 🧪 **Testing Strategy**
- Environment validation tests
- Unit tests (fast, isolated)
- Integration tests (with real services)
- End-to-end tests for complete workflows

## Usage

### Running Tests Locally
```bash
# Setup environment
python scripts/setup_dev_environment.py

# Validate environment matches CI
python scripts/test_runner.py --validation

# Run full test suite
python scripts/test_runner.py --all
```

### Manual Workflow Dispatch
```bash
# Run v3.0.0 tests
gh workflow run test-v3.yml

# Run synthesis feature tests
gh workflow run test-synthesis.yml
```

## Migration from v2.x

The v2.x workflows have been removed. The current workflows support:
- ✅ **v3.0.0 Clean Architecture** (`src/` directory)
- ✅ **Legacy v2.x code** (`app/` directory) 
- ✅ **Portable .venv setup** (works on any machine)
- ✅ **Organized project structure** (scripts/, tests/, config/, docs/)

For v3.0.0 development, use the reorganized structure with proper .venv usage as documented in `CLAUDE.md`.