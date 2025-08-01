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


# Minimal models for basic endpoints


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    print(f"🚀 Starting Second Brain v{__version__}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Second Brain")


# Create the app
app = FastAPI(
    title="Second Brain API v2",
    description="Excellence-focused memory storage system with advanced WebSocket support",
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


# Setup dependency overrides - minimal setup for V2 API
def setup_dependencies():
    """Setup minimal dependencies for V2 API."""
    print("✅ V2 API dependencies ready")


# Import and include routers
def include_routers():
    """Include all API routers."""
    try:
        # Setup dependencies first
        setup_dependencies()
        
        # V2 API routes - the ONLY implementation we use
        from app.routes import v2_api_new
        app.include_router(v2_api_new.router, prefix="")
        print("✅ V2 API routes included")
        
    except Exception as e:
        print(f"⚠️ Error including routers: {e}")
        # Continue anyway - app will work with basic endpoints


# Include routers after app creation
include_routers()


# Root endpoint - keep this minimal
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Second Brain API v2",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v2/health"
    }


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