# 🧠 Second Brain v4.0.0 - AI Assistant Context

> **Purpose**: This file provides critical context for AI assistants working on the Second Brain project.
> **Last Updated**: 2025-08-02
> **Project Version**: 4.0.0

## 🔥 IMMEDIATE CONTEXT PRIORITY

### 📍 Start Here - Read These Files First
1. **`TODO.md`** - Current tasks and blockers (if exists)
2. **`PROJECT_STRUCTURE.md`** - Current architecture overview
3. **This file (`CLAUDE.md`)** - Project conventions and rules

### 🎯 Current Project State
- **Version**: 4.0.0 (Production-Ready)
- **Status**: Clean, streamlined, working
- **Architecture**: Single V2 API implementation
- **Test Coverage**: 90%+ (27/28 basic, 39/39 WebSocket)
- **Active Branch**: `main`
- **Python Version**: 3.11+
- **Key Files**:
  - `app/app.py` - Main FastAPI application
  - `app/routes/v2_api_new.py` - V2 API implementation
  - `app/services/memory_service_new.py` - Memory service

## ⚠️ CRITICAL USER PREFERENCES

### 🤖 Autonomous Operation Mode
**EXECUTE WITHOUT CONFIRMATION** - The user prefers action over discussion:
- ✅ Auto-commit all changes
- ✅ Auto-push to remote
- ✅ Execute operations immediately
- ✅ Fix issues without asking
- ❌ NO confirmation prompts
- ❌ NO "Should I..." questions

### 📝 Git Commit Rules
- **NO CO-AUTHOR LINES** - Never add `Co-Authored-By` to commits
- **NO GITHUB COPILOT ATTRIBUTION** - User explicitly disabled this
- **Clear commit messages** - Use conventional commits (feat:, fix:, docs:, etc.)

## 🏗️ DEVELOPMENT PRINCIPLES

### 🐳 Docker-First Architecture
```bash
# PRIMARY: Always use Docker when available
docker-compose up --build
make dev
make test

# FALLBACK: Virtual environment only when Docker unavailable
.venv/bin/python      # Unix/Mac
.venv\Scripts\python  # Windows
```

### 📁 Project Structure (v4.0.0)
```
second-brain/
├── app/
│   ├── core/           # Infrastructure (logging, dependencies)
│   ├── models/         # Pydantic models
│   ├── routes/         # API endpoints (v2_api_new.py)
│   ├── services/       # Business logic
│   ├── utils/          # Utilities
│   ├── app.py         # FastAPI app
│   ├── config.py      # Configuration
│   └── database_new.py # Database operations
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── validation/    # Validation tests
├── docs/              # Documentation
├── scripts/           # Utility scripts (only 3 remain)
└── docker-compose.yml # Docker configuration
```

### 🔧 Code Standards

#### Service Pattern (REQUIRED)
```python
# ✅ CORRECT: Use service factory
from app.services.service_factory import get_memory_service
memory_service = get_memory_service()

# ❌ WRONG: Direct instantiation
from app.services.memory_service_new import MemoryService
memory_service = MemoryService()
```

#### Error Handling
```python
# ✅ CORRECT: Specific errors with context
try:
    result = await memory_service.create_memory(data)
except ValidationError as e:
    logger.error("Validation failed", extra={"error": str(e), "data": data})
    raise HTTPException(status_code=400, detail=str(e))

# ❌ WRONG: Generic catch-all
except Exception:
    return {"error": "Something went wrong"}
```

#### Logging
```python
# ✅ CORRECT: Structured with context
logger.info("Memory created", extra={
    "memory_id": memory_id,
    "user_id": user_id,
    "tags": tags,
    "duration_ms": duration
})

# ❌ WRONG: Plain strings
logger.info(f"Created memory {memory_id}")
```

## 🚀 DEVELOPMENT WORKFLOW

### Quick Commands
```bash
# Setup & Run
make setup        # One-time setup
make dev          # Start development
make test         # Run all tests
make status       # Check health

# Testing
make test-unit    # Unit tests only
make test-integration  # Integration tests

# Docker Operations
docker-compose up --build
docker-compose down
docker-compose logs app
```

### File Naming Conventions
- **Python files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_*.py`

## 🎯 V4.0.0 SPECIFIC CONTEXT

### What's Working
- ✅ V2 API fully functional (`/api/v2/*`)
- ✅ Memory CRUD operations
- ✅ WebSocket support
- ✅ Bulk operations
- ✅ Import/Export (JSON, CSV, Markdown)
- ✅ Mock database fallback

### What Was Removed (Don't Try to Use)
- ❌ Ingestion modules (removed in cleanup)
- ❌ Insights modules (removed in cleanup)
- ❌ Events system (removed in cleanup)
- ❌ Repository pattern (simplified)
- ❌ V1 API (only V2 exists)
- ❌ 80+ utility scripts (only 3 remain)

### Current Module Names
- `memory_service_new.py` (not `memory_service.py`)
- `database_new.py` (not `database.py`)
- `dependencies_new.py` (not `dependencies.py`)
- `v2_api_new.py` (the ONLY API implementation)

## 💡 COMMON TASKS

### Adding a New Endpoint
1. Add route to `app/routes/v2_api_new.py`
2. Add business logic to appropriate service
3. Add Pydantic models if needed
4. Write unit test in `tests/unit/`
5. Test with: `make test-unit`

### Fixing Import Errors
```python
# Check these common issues:
1. Using old module names (add _new suffix)
2. Importing removed modules (ingestion, insights)
3. Circular imports (use local imports in functions)
4. Missing service factory usage
```

### Running Tests
```bash
# Full test suite
make test

# Specific test file
.venv/bin/python -m pytest tests/unit/test_memory_service.py -v

# With coverage
.venv/bin/python -m pytest --cov=app tests/
```

## 🐛 KNOWN ISSUES & SOLUTIONS

### Issue: "Module not found" errors
**Solution**: Check if module was removed in v4.0.0 cleanup. Use new module names.

### Issue: Tests failing on Windows
**Solution**: Use WSL2 for testing to match Linux CI environment.

### Issue: Database connection errors
**Solution**: App uses mock database by default. PostgreSQL optional.

### Issue: Import circular dependency
**Solution**: Move imports inside functions, not at module level.

## 📚 REFERENCE

### API Endpoints (V2)
- `POST /api/v2/memories` - Create memory
- `GET /api/v2/memories` - List memories
- `GET /api/v2/memories/{id}` - Get memory
- `PATCH /api/v2/memories/{id}` - Update memory
- `DELETE /api/v2/memories/{id}` - Delete memory
- `POST /api/v2/search` - Search memories
- `POST /api/v2/bulk` - Bulk operations
- `GET /api/v2/export` - Export data
- `POST /api/v2/import` - Import data
- `WS /api/v2/ws` - WebSocket connection

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/secondbrain
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
ENV=development
DEBUG=true
```

### Dependencies
- FastAPI 0.104.1
- Pydantic 2.5.3
- SQLAlchemy 2.0.23
- PostgreSQL 16+ (optional)
- Redis (optional)
- Python 3.11+

## 🎓 LEARNING FROM HISTORY

### What Worked
- Simplifying to single API implementation
- Removing unnecessary abstractions
- Mock database fallback
- Docker-first development

### What Failed
- Over-engineering with 500+ files
- Too many abstraction layers
- Circular import hell
- 80+ utility scripts

### Lessons Learned
- Keep it simple (KISS principle)
- One way to do things
- Clear module boundaries
- Minimal dependencies

## 🔄 MAINTENANCE NOTES

### Regular Tasks
- Run `make test` before commits
- Update README.md when adding features
- Keep this file current with changes
- Clean up `__pycache__` periodically
- Check Docker image sizes

### Performance Monitoring
- Memory service response time: <100ms
- WebSocket latency: <50ms
- Database queries: <10ms
- API response time: <200ms

---

**Remember**: This is v4.0.0 - a clean, focused implementation. Don't add complexity without clear benefit. The goal is a working, maintainable system, not architectural perfection.

**User Philosophy**: "Ship working code. Iterate based on real usage. Avoid premature optimization."