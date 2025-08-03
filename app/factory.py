"""
Application Factory Pattern for Second Brain
Creates configured FastAPI instances for different environments
"""

import os
from contextlib import asynccontextmanager
from typing import Optional
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.env_manager import get_env_manager
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Version
__version__ = "4.2.0"


class AppState:
    """Application state container"""
    def __init__(self):
        self.ready = False
        self.memory_service = None
        self.qdrant_client = None
        self.persistence_task = None
        self.shutdown_event = asyncio.Event()
        self.startup_time = None
        self.memory_count = 0


def create_lifespan(config_name: str):
    """Create lifespan handler for specific configuration"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Handle application startup and shutdown"""
        # === STARTUP ===
        logger.info(f"🚀 Starting Second Brain v{__version__} [{config_name}]")
        
        # Initialize app state
        app.state = AppState()
        
        try:
            # Initialize degradation manager
            from app.core.degradation import get_degradation_manager
            app.state.degradation_manager = get_degradation_manager()
            await app.state.degradation_manager.perform_health_checks()
            
            # Initialize memory service with PostgreSQL backend
            from app.services.memory_service import MemoryService
            
            # Use PostgreSQL for all environments
            app.state.memory_service = MemoryService()
            await app.state.memory_service.initialize()
            
            # Load existing memories
            memories = await app.state.memory_service.list_memories()
            app.state.memory_count = len(memories)
            
            # Log status
            stats = await app.state.memory_service.get_statistics()
            logger.info(f"📚 Loaded {app.state.memory_count} memories using {stats['backend']} backend")
            logger.info(f"⚡ Degradation level: {stats['degradation_level']}")
            
            # Start background persistence task (if not testing)
            if config_name != "testing":
                app.state.persistence_task = asyncio.create_task(
                    periodic_persistence(app.state.memory_service)
                )
            
            # Mark as ready
            app.state.ready = True
            logger.info("✅ Application ready to serve requests")
            
        except Exception as e:
            logger.error(f"❌ Startup failed: {e}")
            raise
        
        yield
        
        # === SHUTDOWN ===
        logger.info("👋 Graceful shutdown initiated...")
        
        # Stop accepting new requests
        app.state.ready = False
        
        # Cancel background tasks
        if app.state.persistence_task:
            app.state.persistence_task.cancel()
            try:
                await app.state.persistence_task
            except asyncio.CancelledError:
                pass
        
        # Final persistence
        if app.state.memory_service and config_name != "testing":
            try:
                await app.state.memory_service.save_to_disk()
                logger.info("💾 Final memory persistence complete")
            except Exception as e:
                logger.error(f"Failed to persist memories on shutdown: {e}")
        
        logger.info("✅ Shutdown complete")
    
    return lifespan


async def periodic_persistence(memory_service, interval: int = 30):
    """Periodically persist memories to disk"""
    while True:
        try:
            await asyncio.sleep(interval)
            await memory_service.save_to_disk()
            logger.debug(f"💾 Periodic persistence checkpoint")
        except asyncio.CancelledError:
            # Final save before exit
            await memory_service.save_to_disk()
            raise
        except Exception as e:
            logger.error(f"Persistence error: {e}")


def create_app(config_name: str = "development") -> FastAPI:
    """
    Application factory for creating configured FastAPI instances
    
    Args:
        config_name: Configuration name (development, production, testing)
    
    Returns:
        Configured FastAPI application
    """
    # Validate config name
    valid_configs = ["development", "production", "testing"]
    if config_name not in valid_configs:
        raise ValueError(f"Invalid config: {config_name}. Must be one of {valid_configs}")
    
    # Create app with lifespan
    app = FastAPI(
        title=f"Second Brain API [{config_name.title()}]",
        description="Single-user memory management system with advanced features",
        version=__version__,
        lifespan=create_lifespan(config_name),
        docs_url="/docs" if config_name != "production" else None,
        redoc_url="/redoc" if config_name != "production" else None,
    )
    
    # Add CORS middleware
    cors_origins = ["*"] if config_name == "development" else os.getenv("CORS_ORIGINS", "").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store config in app
    app.config_name = config_name
    
    # Include routers with tags for better organization
    try:
        from app.routes.v2 import (
            memories_router,
            search_router,
            health_router,
            websocket_router
        )
        
        # Include routers with proper tags
        app.include_router(memories_router, prefix="/api/v2", tags=["Memories"])
        app.include_router(search_router, prefix="/api/v2", tags=["Search"])
        app.include_router(health_router, prefix="/api/v2", tags=["System"])
        app.include_router(websocket_router, prefix="/api/v2", tags=["Real-time"])
        
        logger.info("📍 Routes registered successfully with tags")
    except ImportError as e:
        logger.error(f"Failed to import routes: {e}")
        # Continue anyway for testing
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with environment info"""
        return {
            "name": "Second Brain API",
            "version": __version__,
            "environment": config_name,
            "ready": getattr(app.state, 'ready', False),
            "docs": f"/docs" if config_name != "production" else None,
        }
    
    # Add basic health check
    @app.get("/health")
    async def health():
        """Basic health check"""
        is_ready = getattr(app.state, 'ready', False)
        if not is_ready:
            return {"status": "starting", "ready": False}, 503
        
        return {
            "status": "healthy",
            "ready": True,
            "environment": config_name,
            "memories_loaded": getattr(app.state, 'memory_count', 0)
        }
    
    return app


# Convenience functions for common configurations
def create_dev_app() -> FastAPI:
    """Create development application"""
    return create_app("development")


def create_prod_app() -> FastAPI:
    """Create production application"""
    return create_app("production")


def create_test_app() -> FastAPI:
    """Create testing application"""
    return create_app("testing")