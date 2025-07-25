"""
FastAPI application factory.

Creates and configures the FastAPI application.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.api.exceptions import setup_exception_handlers
from src.api.middleware import setup_middleware
from src.api.routes import setup_routes
from src.application import get_dependencies, reset_dependencies
from src.infrastructure.logging import get_logger, setup_logging
from src.infrastructure.observability import setup_tracing

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifespan.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Second Brain API")
    
    # Initialize dependencies
    deps = await get_dependencies()
    app.state.dependencies = deps
    
    # Setup tracing
    setup_tracing(
        service_name="secondbrain-api",
        environment=os.getenv("ENVIRONMENT", "development"),
    )
    
    logger.info("Second Brain API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Second Brain API")
    
    # Clean up dependencies
    await reset_dependencies()
    
    logger.info("Second Brain API shut down successfully")


def create_app(
    title: str = "Second Brain API",
    version: str = "3.0.0",
    debug: bool = False,
) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        title: API title
        version: API version
        debug: Debug mode flag
        
    Returns:
        Configured FastAPI application
    """
    # Setup logging
    setup_logging(
        level="DEBUG" if debug else "INFO",
        json_logs=not debug,
    )
    
    # Create FastAPI app
    app = FastAPI(
        title=title,
        version=version,
        debug=debug,
        lifespan=lifespan,
        docs_url="/api/docs" if debug else None,
        redoc_url="/api/redoc" if debug else None,
        openapi_url="/api/openapi.json" if debug else None,
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if debug else ["https://secondbrain.example.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Setup trusted hosts
    if not debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["secondbrain.example.com", "*.secondbrain.example.com"],
        )
    
    # Setup custom middleware
    setup_middleware(app)
    
    # Setup routes
    setup_routes(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    return app