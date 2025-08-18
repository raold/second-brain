"""Base model service for GPU inference."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import torch
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingRequest(BaseModel):
    """Standard embedding request."""
    content: str | bytes | list[str]
    batch_size: int | None = 1


class EmbeddingResponse(BaseModel):
    """Standard embedding response."""
    embeddings: list[list[float]]
    model: str
    dimensions: int
    processing_time_ms: float


class ModelStatus(BaseModel):
    """Model service status."""
    model_name: str
    model_loaded: bool
    device: str
    vram_used_gb: float | None
    total_vram_gb: float | None
    requests_processed: int


class BaseModelService(ABC):
    """Base class for model services."""

    def __init__(self, model_name: str, device: str = "cuda") -> None:
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        self.requests_processed = 0

    @abstractmethod
    async def load_model(self):
        """Load the model into memory."""

    @abstractmethod
    async def generate_embedding(self, content: str | bytes) -> np.ndarray:
        """Generate embedding for content."""

    def get_device_info(self) -> dict[str, Any]:
        """Get GPU device information."""
        if not torch.cuda.is_available():
            return {"device": "cpu", "cuda_available": False}

        return {
            "device": self.device,
            "cuda_available": True,
            "gpu_name": torch.cuda.get_device_name(0),
            "total_vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
            "allocated_vram_gb": torch.cuda.memory_allocated(0) / 1e9,
            "cached_vram_gb": torch.cuda.memory_reserved(0) / 1e9,
        }

    def get_status(self) -> ModelStatus:
        """Get current model status."""
        device_info = self.get_device_info()

        return ModelStatus(
            model_name=self.model_name,
            model_loaded=self.model is not None,
            device=device_info.get("device", "cpu"),
            vram_used_gb=device_info.get("allocated_vram_gb"),
            total_vram_gb=device_info.get("total_vram_gb"),
            requests_processed=self.requests_processed,
        )

    def clear_cache(self) -> None:
        """Clear GPU cache."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
