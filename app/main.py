# app/main.py

<<<<<<< HEAD
=======
import logging
import os
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
import uuid

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.websocket import router as ws_router
<<<<<<< HEAD
from app.config import Config
from app.router import router
from app.utils.logger import logger
=======
from app.config import config
from app.router import router
from app.storage.postgres_client import close_postgres_client, postgres_client

# Setup logging with Windows compatibility first
config.setup_logging()
logger = logging.getLogger("main")

def safe_log(level, message_with_emoji, message_without_emoji):
    """
    Safely log messages with emoji support detection for Windows compatibility.
    
    Args:
        level: logging level function (logger.info, logger.error, etc.)
        message_with_emoji: message with emoji characters for Unix systems
        message_without_emoji: plain text message for Windows/CI systems
    """
    if config.is_windows or config.is_ci:
        level(message_without_emoji)
    else:
        level(message_with_emoji)
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

app = FastAPI(
    title="Second Brain - AI Memory Assistant",
    version="1.5.0",
    description="Ingest, embed, search, and replay text semantically with PostgreSQL persistence"
)

# Correlation ID middleware
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Bind correlation_id to structlog context for this request
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        # Unbind after request
        structlog.contextvars.clear_contextvars()
        return response

app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)
<<<<<<< HEAD

# Serve static UI files at /ui
import os

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/ui", StaticFiles(directory=static_dir), name="ui")

# Prometheus metrics
Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)

# Sentry error monitoring (optional, set SENTRY_DSN env var)
import os

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)
=======
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

# Serve static UI files at /ui
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/ui", StaticFiles(directory=static_dir), name="ui")

# Prometheus metrics
Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)

# Sentry error monitoring (optional, set SENTRY_DSN env var)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    if config.is_windows or config.is_ci:
        logger.info("Initializing application services...")
    else:
        logger.info("🔄 Initializing application services...")
    
    try:
        # Initialize PostgreSQL client
        await postgres_client.initialize()
        safe_log(logger.info, "✅ PostgreSQL client initialized", "PostgreSQL client initialized")
        safe_log(logger.info, "🚀 Second Brain - AI Memory Assistant ready", "Second Brain - AI Memory Assistant ready")
        
        logger.info(f"Loaded Config: {config.summary()}")
        
    except Exception as e:
        safe_log(logger.error, f"❌ Failed to initialize services: {e}", f"Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown."""
    if config.is_windows or config.is_ci:
        logger.info("Shutting down application services...")
    else:
        logger.info("🔄 Shutting down application services...")
    
    try:
        # Close PostgreSQL connections
        await close_postgres_client()
        safe_log(logger.info, "✅ PostgreSQL client closed", "PostgreSQL client closed")
        safe_log(logger.info, "👋 Application shutdown complete", "Application shutdown complete")
        
    except Exception as e:
        safe_log(logger.error, f"❌ Error during shutdown: {e}", f"Error during shutdown: {e}")
