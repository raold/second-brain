# Second Brain Development Standards

**🎯 Mandatory Patterns for Maximum Developer Efficiency**

## 🏗️ Architectural Standards

### Dependency Injection (MANDATORY)

**✅ CORRECT: Service Factory Pattern**
```python
from app.services.service_factory import get_session_service, get_memory_service

# In routes
@router.post("/memories")
async def create_memory(data: MemoryCreate):
    memory_service = get_memory_service()  # ✅ Factory injection
    return await memory_service.create_memory(data)

# In services  
class SessionService:
    def __init__(self):
        self.memory_service = get_memory_service()  # ✅ Factory injection
```

**❌ WRONG: Direct Instantiation**
```python
# NEVER do this
session_service = SessionService()  # ❌ Breaks testability
memory_service = MemoryService(database, cache)  # ❌ Tight coupling
```

### Service Layer (MANDATORY)

**✅ CORRECT: Business Logic in Services**
```python
# app/services/memory_service.py
class MemoryService:
    async def create_memory(self, data: MemoryCreate) -> Memory:
        # All business logic here
        # Validation, processing, persistence
        pass

# app/routes/memory_routes.py  
@router.post("/memories")
async def create_memory(data: MemoryCreate):
    service = get_memory_service()  # Thin controller
    return await service.create_memory(data)
```

**❌ WRONG: Business Logic in Routes**
```python
@router.post("/memories")
async def create_memory(data: MemoryCreate):
    # NEVER put business logic in routes
    if not data.content:  # ❌ Validation in route
        raise HTTPException(400, "Content required")
    
    memory = Memory(...)  # ❌ Domain logic in route
    db.save(memory)       # ❌ Persistence in route
```

## 🧪 Testing Standards (MANDATORY)

### Test Organization
```
tests/
├── validation/     # Environment health, imports, basic setup
├── unit/          # Fast, isolated, mocked dependencies
├── integration/   # Service interactions, real database
└── comprehensive/ # Full workflows, performance tests
```

### Test Markers (REQUIRED)
```python
import pytest

@pytest.mark.validation
def test_environment_setup():
    """Validate development environment"""
    pass

@pytest.mark.unit
def test_memory_service_create():
    """Fast isolated test with mocks"""
    pass

@pytest.mark.integration  
def test_memory_api_endpoint():
    """Test with real database"""
    pass
```

### Test Performance Standards
- **Unit tests**: < 5 seconds total
- **Integration tests**: < 30 seconds total  
- **Validation tests**: < 10 seconds total
- **All tests together**: < 60 seconds

## 📊 Logging Standards (MANDATORY)

### Structured Logging
```python
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# ✅ CORRECT: Structured with context
logger.info("Memory created", extra={
    "operation": "memory_creation",
    "user_id": user_id,
    "memory_id": memory.id,
    "duration_ms": duration,
    "content_length": len(memory.content)
})

# ✅ CORRECT: Error with context
logger.error("Memory creation failed", extra={
    "operation": "memory_creation", 
    "user_id": user_id,
    "error_type": type(e).__name__,
    "error_message": str(e)
})
```

**❌ WRONG: Plain String Logging**
```python
logger.info("Memory created")  # ❌ No context
logger.error(f"Error: {e}")    # ❌ No structured data
print("Debug info")            # ❌ Never use print
```

## 🚨 Error Handling Standards (MANDATORY)

### Service-Level Error Handling
```python
from app.utils.exceptions import ServiceError, ServiceValidationError

class MemoryService:
    async def create_memory(self, data: MemoryCreate) -> Memory:
        try:
            # Business logic
            memory = Memory(**data.dict())
            await self.repository.save(memory)
            return memory
            
        except ValidationError as e:
            logger.error("Validation failed", extra={
                "operation": "memory_creation",
                "error": str(e),
                "data": data.dict()
            })
            raise ServiceValidationError(f"Memory validation failed: {e}")
            
        except DatabaseError as e:
            logger.error("Database error", extra={
                "operation": "memory_creation", 
                "error": str(e)
            })
            raise ServiceError("Failed to save memory")
            
        except Exception as e:
            logger.exception("Unexpected error in memory creation")
            raise ServiceError("Memory creation failed")
```

### Route-Level Error Handling
```python
@router.post("/memories")
async def create_memory(data: MemoryCreate):
    try:
        memory_service = get_memory_service()
        memory = await memory_service.create_memory(data)
        return {"status": "success", "memory": memory}
        
    except ServiceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except ServiceError as e:
        logger.error(f"Memory service error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 📁 File Organization (MANDATORY)

### Directory Structure
```
app/
├── services/           # ALL business logic
│   ├── memory_service.py
│   ├── session_service.py
│   └── service_factory.py
├── routes/            # Thin HTTP controllers  
├── models/            # Pydantic data models
├── repositories/      # Data access layer
└── utils/             # Shared utilities
```

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Variables**: `snake_case`

## 🔧 Environment Standards (MANDATORY)

### Development Commands
```bash
# Setup (works everywhere)
make setup              # Docker + .venv setup
make dev               # Start development environment
make status            # Check environment health

# Testing (standardized)  
make test              # All tests in Docker
make test-unit         # Unit tests only
make test-validation   # Environment validation

# Development tools
make shell             # Development shell
make dev-logs          # Application logs
```

### Environment Validation
```python
# Every service must validate its dependencies
class MemoryService:
    def __init__(self):
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        if not self.database:
            raise ServiceError("Database not available")
        if not self.cache:
            logger.warning("Cache not available, using fallback")
```

## ⚡ Performance Standards

### Response Time Targets
- **API endpoints**: < 200ms average
- **Database queries**: < 50ms average
- **Cache operations**: < 10ms average
- **File operations**: < 100ms average

### Code Quality Gates
```python
# REQUIRED: Type hints everywhere
async def create_memory(self, data: MemoryCreate) -> Memory:
    pass

# REQUIRED: Pydantic models for data
class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default=[])

# REQUIRED: Docstrings for public methods
def calculate_importance(self, content: str) -> float:
    """Calculate importance score for content.
    
    Args:
        content: Text content to analyze
        
    Returns:
        Importance score between 0.0 and 1.0
    """
    pass
```

## 🚀 Development Efficiency Rules

### One-Command Everything
- **Setup**: `make setup` (works on any OS)
- **Test**: `make test` (all categories)  
- **Deploy**: `make deploy` (when implemented)
- **Status**: `make status` (health check)

### Cross-Platform Guarantee
- All commands work on Windows, macOS, Linux
- No OS-specific paths or dependencies
- Docker-first with bulletproof .venv fallback
- Automated environment validation

### Fail-Fast Principles
- Validate environment before development
- Catch errors at service boundaries
- Clear error messages with solutions
- Automatic health checks and recovery

---

**💡 Remember: These standards exist to maximize developer efficiency. Every pattern should make development faster, not slower.**