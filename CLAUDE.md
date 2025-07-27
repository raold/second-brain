# Claude Memory - Second Brain Project

## 🔥 CONTEXT HOTSWAP - READ THESE FILES FIRST
1. **TODO.md** - Current tasks, blockers, project state (PRIMARY CONTEXT)
2. **DEVELOPMENT_CONTEXT.md** - Session history, decisions, user prefs
3. **This file (CLAUDE.md)** - Core principles, patterns, architecture

## 🎯 CURRENT STATE (as of last session)
- **Enterprise Ready**: 7/10 (working toward 10/10)
- **Blockers**: 25 TODOs, test failures, missing load tests
- **User Mode**: AUTONOMOUS - no confirmations needed
- **Active Branch**: main
- **Next Action**: Check TODO.md for priority tasks

## ⚠️ IMPORTANT USER PREFERENCES
- **NO CO-AUTHOR LINES IN COMMITS** - User has requested multiple times not to include co-author attribution

## 🚨 FOUNDATIONAL DEVELOPMENT PRINCIPLES

### 🐳 Docker-First Architecture - MANDATORY
**ALL DEVELOPMENT AND DEPLOYMENT USES DOCKER - NO EXCEPTIONS**

- **No Python libraries on host machine** - Everything runs in containers
- **Developer environment is containerized** - Dev tools, dependencies, databases all in Docker
- **Cross-platform guarantee** - Same containers work on Windows, Mac, Linux
- **Isolation by design** - No dependency conflicts, version mismatches, or environment drift

### 🔒 Bulletproof .venv Management 
**WHEN PYTHON IS NEEDED LOCALLY (rare cases only)**

- **Never use system Python** - always use `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix)
- **Never install packages globally** - all pip installs must target the .venv
- **Automated .venv creation** - Scripts handle all virtual environment setup
- **Environment validation** - Automatic checks ensure correct Python/package versions

### 🏗️ Development Workflow
```bash
# PREFERRED - Docker-first approach
make setup                          # Automatic environment setup
make dev                            # Start full development stack
make test                           # Run tests in containers
make shell                          # Open development shell

# ALTERNATIVE - Direct Docker commands
docker-compose up --build          # Start full development environment
docker-compose exec app python scripts/test_runner.py --all

# FALLBACK - When Docker unavailable (rare)
python scripts/setup-bulletproof-venv.py  # One-time setup
.venv/Scripts/python.exe main.py          # Start application
```

### 🛠️ Development Commands
```bash
# Quick setup (works everywhere)
make setup                    # Docker + .venv setup
make dev                      # Start development environment
make status                   # Check environment status

# Testing  
make test                     # All tests
make test-unit               # Unit tests only
make test-integration        # Integration tests

# Development tools
make shell                    # Development shell
make dev-logs                # Show application logs
```

## 🏗️ ARCHITECTURAL DESIGN PRINCIPLES

### 🎯 Core Design Philosophy
**Developer Efficiency Above All Else**

1. **Zero Friction Development**
   - One command setup: `make setup`
   - Instant feedback loops
   - Self-healing environments
   - Cross-platform guarantee

2. **Consistency by Design**
   - Standardized patterns across all modules
   - Uniform error handling
   - Consistent dependency injection
   - Shared logging infrastructure

3. **Fail-Fast, Fix-Fast**
   - Comprehensive validation at every step
   - Automated error detection and recovery
   - Clear error messages with solutions
   - Health checks built into everything

### 🔧 Mandatory Architectural Standards

#### **Dependency Injection Pattern**
```python
# REQUIRED: Service Factory Pattern
from app.services.service_factory import get_session_service, get_memory_service

# NEVER: Direct instantiation
session_service = SessionService()  # ❌ WRONG

# ALWAYS: Factory injection
session_service = get_session_service()  # ✅ CORRECT
```

#### **Testing Standards**
```python
# REQUIRED: Test categories with clear boundaries
tests/
├── validation/     # Environment health, imports, basic functionality
├── unit/          # Fast, isolated, no external dependencies  
├── integration/   # Service interactions, database, API endpoints
└── comprehensive/ # Full workflows, performance, edge cases

# REQUIRED: Test markers
@pytest.mark.unit
@pytest.mark.integration  
@pytest.mark.validation
```

#### **Logging Standards**
```python
# REQUIRED: Structured logging with context
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# ALWAYS: Include operation context
logger.info("Operation completed", extra={
    "operation": "memory_creation",
    "user_id": user_id,
    "memory_id": memory_id,
    "duration_ms": duration
})

# NEVER: Plain string logging
logger.info("Memory created")  # ❌ WRONG
```

#### **Error Handling Standards**
```python
# REQUIRED: Service-level error handling
class MemoryService:
    async def create_memory(self, data: MemoryCreate) -> Memory:
        try:
            # Business logic
            return memory
        except ValidationError as e:
            logger.error("Validation failed", extra={
                "error": str(e),
                "data": data.dict()
            })
            raise ServiceValidationError(f"Memory validation failed: {e}")
        except Exception as e:
            logger.exception("Unexpected error in memory creation")
            raise ServiceError("Memory creation failed")

# NEVER: Bare exceptions or unclear error messages
```

#### **Route Handler Standards**
```python
# REQUIRED: Thin controllers, delegate to services
@router.post("/memories")
async def create_memory(memory_data: MemoryCreate):
    try:
        memory_service = get_memory_service()
        memory = await memory_service.create_memory(memory_data)
        return {"status": "success", "memory": memory}
    except ServiceError as e:
        logger.error(f"Memory creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# NEVER: Business logic in routes
```

### 🚀 Development Efficiency Rules

#### **Environment Management**
- **Docker-first**: Always prefer containerized development
- **Bulletproof fallback**: .venv must work when Docker unavailable
- **One-command everything**: Setup, test, deploy should be single commands
- **Cross-platform**: Code must work identically on Windows/Mac/Linux

#### **Code Organization**
- **Services directory**: All business logic in `app/services/`
- **Thin routes**: Controllers only handle HTTP concerns
- **Clear boundaries**: No circular dependencies between layers
- **Consistent naming**: `snake_case` for files, `PascalCase` for classes

#### **Quality Gates**
- **Validation tests**: Must pass before any development
- **Type checking**: Pydantic models for all data structures
- **Integration tests**: All service interactions tested
- **Documentation**: Code changes require doc updates

### 💡 Efficiency Multipliers

1. **Standardized Patterns**: Every developer knows exactly how to structure code
2. **Automated Validation**: Catch issues before they become problems  
3. **Self-Documenting**: Code structure tells the story
4. **Rapid Feedback**: Tests run fast, errors are clear
5. **Portable Knowledge**: Patterns work across entire codebase

### ⚡ Speed Optimization Rules

- **Fast feedback loops**: Unit tests < 5 seconds total
- **Parallel execution**: Tests run concurrently when possible
- **Smart caching**: Docker layers, pip cache, test results
- **Incremental updates**: Only rebuild what changed
- **Status awareness**: Always know environment health

### Correct Commands
```bash
# CORRECT - Always use .venv Python
.venv/Scripts/python.exe scripts/test_runner.py --validation
.venv/Scripts/python.exe -m pip install package_name

# WRONG - Never use system Python
python scripts/test_runner.py --validation
python -m pip install package_name
```

### File Organization
- **Scripts**: All development scripts are in `scripts/` directory
- **Tests**: All tests are in `tests/` with subdirectories (unit, integration, validation, e2e)
- **Config**: All requirements files are in `config/` directory
- **Docs**: All documentation is in `docs/` directory

### Testing Commands
```bash
# Environment validation
python scripts/test_runner.py --validation

# Run specific test types
python scripts/test_runner.py --unit
python scripts/test_runner.py --integration
python scripts/test_runner.py --all

# Setup environment (works on any machine)
python scripts/setup_dev_environment.py
```

### 🐧 WSL2 Testing on Windows - CRITICAL
**ALWAYS USE WSL2 FOR TESTING ON WINDOWS WHEN AVAILABLE**

The CI/CD pipeline runs on Ubuntu Linux. Testing only on Windows can miss platform-specific issues that will cause CI failures. WSL2 provides a Linux environment that matches GitHub Actions.

#### WSL2 Testing Workflow
```bash
# Enter WSL2 Ubuntu environment
wsl

# Navigate to project (Windows drives mounted under /mnt)
cd /mnt/c/Users/dro/second-brain

# Run tests in Linux environment (matches CI)
python scripts/test_runner.py --all

# Expected output should match CI:
# ================= 430 passed, 6 skipped, 64 warnings ==================
```

#### Why WSL2 is Critical
- **CI runs on Ubuntu**: GitHub Actions uses ubuntu-latest
- **Path separators differ**: Windows uses `\`, Linux uses `/`
- **File encodings differ**: Windows uses cp1252, Linux uses UTF-8
- **File sizes vary**: Line endings and encoding affect byte counts
- **Case sensitivity**: Linux is case-sensitive, Windows is not

#### Common Cross-Platform Issues
1. **Hardcoded paths**: Use `pathlib.Path` for OS-agnostic paths
2. **Unicode in tests**: Replace emojis with ASCII for Windows compatibility
3. **File size assertions**: Avoid exact byte count checks
4. **Path separators in strings**: Use `os.path.join()` or `Path`

**Remember**: After 2 weeks of CI failures, using WSL2 solved all platform-specific test issues immediately.

### Why This Matters
- **Portability**: Code must work on work computer, laptop, home desktop
- **Dependency Isolation**: Avoid conflicts with system packages
- **Version Control**: Specific package versions in .venv prevent CI/CD failures
- **Team Consistency**: Everyone uses same dependency versions

## Project Context
- **Architecture**: Clean Architecture (v3.0.0) with Domain/Application/Infrastructure layers
- **Tech Stack**: FastAPI, PostgreSQL with pgvector, Redis, Pydantic 2.5.3
- **File Structure**: Organized with scripts/, tests/, config/, docs/ directories
- **CI/CD**: GitHub Actions with dependency validation and testing

**Remember**: The user was frustrated about hardcoded Python paths from different machines. The .venv solution ensures portability across all their computers.