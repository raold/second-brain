# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk

from app.config import Config
from app.router import router
from app.api.websocket import router as ws_router
from app.utils.logger import logger

app = FastAPI(
    title="LLM Output Processor",
    version="1.0.0",
    description="Ingest and search semantically indexed memory"
)

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
