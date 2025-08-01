"""
Second Brain API - Clean Rebuild

A minimal, working FastAPI application that we can build upon.
No circular imports, no bullshit, just clean code that works.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Version info
__version__ = "3.2.0"


# Basic models
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class MemoryCreate(BaseModel):
    content: str
    importance_score: float = 0.5
    tags: list[str] = []


class MemoryResponse(BaseModel):
    id: str
    content: str
    importance_score: float
    tags: list[str]
    created_at: datetime


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    print(f"🚀 Starting Second Brain v{__version__}")
    
    # Initialize database connection here
    # For now, we'll use in-memory storage
    app.state.memories = {}
    app.state.memory_counter = 0
    
    yield
    
    # Shutdown
    print("👋 Shutting down Second Brain")


# Create the app
app = FastAPI(
    title="Second Brain API",
    description="A clean, working memory storage system",
    version=__version__,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Setup dependency overrides for clean implementations
def setup_dependencies():
    """Setup dependency injection overrides."""
    from app import dependencies as old_deps
    from app import shared as old_shared
    from app import dependencies_new, shared_new
    from app.services import memory_service
    from app.services import memory_service_new
    
    # Override old implementations with new ones
    old_deps.get_current_user = dependencies_new.get_current_user
    old_deps.verify_api_key = dependencies_new.verify_api_key
    old_shared.verify_api_key = shared_new.verify_api_key
    
    # Override service factory
    from app.services import service_factory
    service_factory.get_memory_service = lambda: memory_service_new.MemoryService()
    
    print("✅ Dependencies configured")


# Import and include routers
def include_routers():
    """Include all API routers."""
    try:
        # Setup dependencies first
        setup_dependencies()
        
        # Import routers with error handling
        from app.routes import health_routes
        app.include_router(health_routes.router, prefix="/api/v1")
        
        # Memory routes - now should work with our implementations
        try:
            from app.routes import memory_routes
            app.include_router(memory_routes.router, prefix="/api/v1")
            print("✅ Memory routes included")
        except Exception as e:
            print(f"⚠️ Memory routes error: {e}")
        
        # V2 API routes - the excellent new implementation
        try:
            from app.routes import v2_api_new
            app.include_router(v2_api_new.router, prefix="")
            print("✅ V2 API routes included")
        except Exception as e:
            print(f"⚠️ V2 API routes error: {e}")
        
        # V2 unified API routes for backwards compatibility
        try:
            from app.routes import v2_unified_api
            app.include_router(v2_unified_api.router, prefix="")
            print("✅ V2 unified API routes included")
        except Exception as e:
            print(f"⚠️ V2 unified API routes error: {e}")
        
        # More routes can be added incrementally
        print("✅ Routers included successfully")
    except Exception as e:
        print(f"⚠️ Error including routers: {e}")
        # Continue anyway - app will work with basic endpoints


# Include routers after app creation
include_routers()


# Basic routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Second Brain API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow()
    )


@app.post("/api/v1/memories", response_model=MemoryResponse)
async def create_memory(memory: MemoryCreate):
    """Create a new memory."""
    # Generate ID
    app.state.memory_counter += 1
    memory_id = f"mem_{app.state.memory_counter}"
    
    # Store memory
    stored_memory = {
        "id": memory_id,
        "content": memory.content,
        "importance_score": memory.importance_score,
        "tags": memory.tags,
        "created_at": datetime.utcnow()
    }
    app.state.memories[memory_id] = stored_memory
    
    return MemoryResponse(**stored_memory)


@app.get("/api/v1/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str):
    """Get a memory by ID."""
    if memory_id not in app.state.memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return MemoryResponse(**app.state.memories[memory_id])


@app.get("/api/v1/memories", response_model=list[MemoryResponse])
async def list_memories(limit: int = 10):
    """List all memories."""
    memories = list(app.state.memories.values())
    # Sort by created_at descending
    memories.sort(key=lambda x: x["created_at"], reverse=True)
    return [MemoryResponse(**m) for m in memories[:limit]]


@app.delete("/api/v1/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    if memory_id not in app.state.memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    del app.state.memories[memory_id]
    return {"message": "Memory deleted successfully"}


# Error handling
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    return {
        "error": "Internal server error",
        "message": str(exc),
        "type": type(exc).__name__
    }


if __name__ == "__main__":
    # For testing only
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)