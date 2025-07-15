# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
import structlog
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Config
from app.router import router
from app.api.websocket import router as ws_router
from app.utils.logger import logger

app = FastAPI(
    title="LLM Output Processor",
    version="1.0.0",
    description="Ingest and search semantically indexed memory"
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

logger.info("🚀 LLM Output Processor ready")
logger.info(f"Loaded Config: {Config.summary()}")
