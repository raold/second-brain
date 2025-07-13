# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router import router
from app.utils.logger import logger
from app.config import Config

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

logger.info("🚀 LLM Output Processor ready")
logger.info(f"Loaded Config: {Config.summary()}")
