# Code Organization Architecture

## Overview

The Second Brain application follows a clean architecture pattern with clear separation of concerns. This document describes the code organization and architectural decisions.

## Architectural Layers

### 1. **Route Layer** (`app/routes/`)
Thin controllers that handle HTTP concerns only:
- Request/response handling
- HTTP status codes
- Request validation
- Authentication/authorization checks
- Delegating to service layer

**Example:**
```python
@router.post("/memories")
async def store_memory(request: MemoryRequest, ...):
    # Validate security
    if not security_manager.validate_request(request_obj):
        raise HTTPException(429, "Rate limit exceeded")
    
    # Delegate to service
    memory_service = get_memory_service()
    return await memory_service.store_memory(...)
```

### 2. **Service Layer** (`app/services/`)
Business logic and orchestration:
- Core business rules
- Data processing
- Cross-cutting concerns
- Integration between components
- Transaction management

**Services:**
- `MemoryService`: Memory storage, retrieval, and search operations
- `SessionService`: Session management, idea processing (woodchipper)
- `DashboardService`: Project metrics, milestones, and reporting
- `HealthService`: System health, diagnostics, and monitoring

### 3. **Data Layer** (`app/database.py`, `app/database_mock.py`)
Data persistence and retrieval:
- Database operations
- Query optimization
- Connection management
- Mock implementations for testing

### 4. **Domain Models** (`app/docs.py`)
Core domain entities and DTOs:
- Request/response models
- Business entities
- Validation rules
- Type definitions

### 5. **Infrastructure** (`app/`)
Cross-cutting infrastructure:
- Security (`app/security.py`)
- Connection pooling (`app/connection_pool.py`)
- Session management (`app/session_manager.py`)
- Conversation processing (`app/conversation_processor.py`)

## Directory Structure

```
app/
├── routes/                  # Route handlers (thin controllers)
│   ├── __init__.py
│   ├── memory_routes.py    # Memory-related endpoints
│   ├── health_routes.py    # Health check endpoints
│   ├── session_routes.py   # Session management endpoints
│   └── dashboard_routes.py # Dashboard endpoints
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── service_factory.py  # Service instantiation and DI
│   ├── memory_service.py   # Memory business logic
│   ├── session_service.py  # Session business logic
│   ├── dashboard_service.py # Dashboard business logic
│   └── health_service.py   # Health check logic
│
├── database.py            # PostgreSQL data layer
├── database_mock.py       # Mock database for testing
├── docs.py               # Domain models and DTOs
├── security.py           # Security infrastructure
├── app.py                # Application setup and configuration
└── ...
```

## Key Design Patterns

### 1. **Dependency Injection**
Services receive dependencies through constructor injection:
```python
class MemoryService:
    def __init__(self, database: Database, validator: InputValidator):
        self.db = database
        self.validator = validator
```

### 2. **Service Factory Pattern**
Centralized service creation and management:
```python
service_factory = get_service_factory()
service_factory.set_database(db)
service_factory.set_security_manager(security_manager)
```

### 3. **Repository Pattern** (implicit)
Database classes act as repositories, abstracting data access:
```python
# Service doesn't know about SQL
memory_id = await self.db.store_memory(...)
```

### 4. **DTO Pattern**
Clear data transfer objects for API contracts:
```python
class MemoryRequest(BaseModel):
    content: str
    memory_type: MemoryType
    # ...
```

## Benefits of This Architecture

### 1. **Testability**
- Services can be tested independently with mocked dependencies
- Business logic isolated from HTTP concerns
- Clear interfaces for mocking

### 2. **Maintainability**
- Single Responsibility: Each layer has one reason to change
- Modular structure: Easy to locate and modify features
- Clear dependencies: Easy to understand data flow

### 3. **Scalability**
- Services can be extracted to microservices if needed
- Database layer can be swapped without affecting business logic
- Easy to add new features without modifying existing code

### 4. **Developer Experience**
- Clear separation makes code easier to understand
- Consistent patterns across the codebase
- Less coupling means fewer breaking changes

## Migration Strategy

### Phase 1: Service Layer Creation ✅
- Created service layer infrastructure
- Implemented core services
- Set up dependency injection

### Phase 2: Route Refactoring ✅
- Refactored routes to use services
- Removed business logic from routes
- Maintained backward compatibility

### Phase 3: Testing Enhancement (Next)
- Add comprehensive unit tests for services
- Integration tests for route/service interaction
- Performance testing for service layer

### Phase 4: Documentation & Training
- Update API documentation
- Create developer guides
- Team training on new architecture

## Best Practices

### 1. **Keep Routes Thin**
Routes should only:
- Parse requests
- Call services
- Format responses
- Handle HTTP errors

### 2. **Service Responsibilities**
Services should:
- Contain business logic
- Orchestrate operations
- Handle business errors
- Log important events

### 3. **Dependency Management**
- Use dependency injection
- Avoid circular dependencies
- Minimize service-to-service calls
- Keep interfaces focused

### 4. **Error Handling**
```python
# Route layer: HTTP errors
raise HTTPException(404, "Not found")

# Service layer: Business errors
raise ValueError("Invalid importance score")

# Data layer: Infrastructure errors
raise DatabaseError("Connection failed")
```

## Code Examples

### Before (Mixed Concerns):
```python
@app.post("/memories")
async def store_memory(request: MemoryRequest, db=Depends(get_db)):
    # Validation mixed with route
    if len(request.content) > 1000:
        raise HTTPException(400, "Content too long")
    
    # Business logic in route
    importance = request.importance_score or 0.5
    if request.memory_type == "semantic":
        importance *= 1.2
    
    # Direct database access
    memory_id = await db.execute(
        "INSERT INTO memories ..."
    )
    
    return {"id": memory_id}
```

### After (Clean Separation):
```python
# Route (thin controller)
@router.post("/memories")
async def store_memory(request: MemoryRequest, ...):
    memory_service = get_memory_service()
    return await memory_service.store_memory(request)

# Service (business logic)
class MemoryService:
    async def store_memory(self, request: MemoryRequest):
        # Validation
        self._validate_memory(request)
        
        # Business logic
        importance = self._calculate_importance(request)
        
        # Delegate to data layer
        return await self.db.store_memory(...)
```

## Future Enhancements

1. **Event-Driven Architecture**
   - Add event bus for service communication
   - Implement domain events
   - Enable async processing

2. **Caching Layer**
   - Add Redis for caching
   - Implement cache-aside pattern
   - Service-level cache management

3. **API Versioning**
   - Version routes independently
   - Service version compatibility
   - Gradual migration support

4. **Monitoring & Observability**
   - Service-level metrics
   - Distributed tracing
   - Performance monitoring

## Conclusion

This architecture provides a solid foundation for the Second Brain application, enabling:
- Clean, maintainable code
- Easy testing and debugging
- Flexibility for future growth
- Better developer experience

The separation of concerns ensures that each component has a single, well-defined responsibility, making the system easier to understand, modify, and extend. 