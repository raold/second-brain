"""FastAPI server for CLIP embedding service."""

import io
import time
import logging
from typing import List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from clip.clip_service import CLIPService
from shared.base_model import (
    EmbeddingRequest, 
    EmbeddingResponse, 
    ModelStatus
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instance
clip_service: Optional[CLIPService] = None


class TextEmbeddingRequest(BaseModel):
    text: Union[str, List[str]]
    normalize: bool = True


class SimilarityRequest(BaseModel):
    embedding1: List[float]
    embedding2: List[float]


class SimilarityResponse(BaseModel):
    similarity: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage model lifecycle."""
    global clip_service
    
    # Startup
    logger.info("Starting CLIP service...")
    clip_service = CLIPService()
    await clip_service.load_model()
    logger.info("CLIP service ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CLIP service...")
    if clip_service:
        clip_service.unload_model()


# Create FastAPI app
app = FastAPI(
    title="CLIP Embedding Service",
    description="Fast multimodal embeddings with CLIP",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "CLIP Embedding Service",
        "model": clip_service.model_name if clip_service else None,
        "status": "ready" if clip_service and clip_service.model else "loading"
    }


@app.get("/clip/status", response_model=ModelStatus)
async def get_status():
    """Get service status."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return clip_service.get_status()


@app.get("/clip/model-info")
async def get_model_info():
    """Get model information."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "model_name": clip_service.model_name,
        "embedding_dimensions": clip_service.embedding_dim,
        "device": clip_service.device,
        "device_info": clip_service.get_device_info()
    }


@app.post("/clip/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: TextEmbeddingRequest):
    """Generate text embedding(s)."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        if isinstance(request.text, str):
            # Single text
            embedding = await clip_service.generate_embedding(request.text)
            embeddings = [embedding.tolist()]
        else:
            # Multiple texts
            embeddings_np = await clip_service.generate_batch_embeddings(request.text)
            embeddings = [emb.tolist() for emb in embeddings_np]
        
        processing_time = (time.time() - start_time) * 1000
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model=clip_service.model_name,
            dimensions=clip_service.embedding_dim,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clip/embed/image", response_model=EmbeddingResponse)
async def embed_image(file: UploadFile = File(...)):
    """Generate image embedding."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        # Read image bytes
        image_bytes = await file.read()
        
        # Generate embedding
        embedding = await clip_service.generate_embedding(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        return EmbeddingResponse(
            embeddings=[embedding.tolist()],
            model=clip_service.model_name,
            dimensions=clip_service.embedding_dim,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error embedding image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clip/embed/batch", response_model=EmbeddingResponse)
async def embed_batch(
    files: List[UploadFile] = File(None),
    texts: List[str] = Body(None)
):
    """Generate embeddings for multiple images and/or texts."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not files and not texts:
        raise HTTPException(status_code=400, detail="No content provided")
    
    start_time = time.time()
    
    try:
        contents = []
        
        # Add texts
        if texts:
            contents.extend(texts)
        
        # Add images
        if files:
            for file in files:
                image_bytes = await file.read()
                contents.append(image_bytes)
        
        # Generate embeddings
        embeddings_np = await clip_service.generate_batch_embeddings(contents)
        embeddings = [emb.tolist() for emb in embeddings_np]
        
        processing_time = (time.time() - start_time) * 1000
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model=clip_service.model_name,
            dimensions=clip_service.embedding_dim,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error batch embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clip/similarity", response_model=SimilarityResponse)
async def compute_similarity(request: SimilarityRequest):
    """Compute cosine similarity between two embeddings."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        emb1 = np.array(request.embedding1)
        emb2 = np.array(request.embedding2)
        
        similarity = await clip_service.compute_similarity(emb1, emb2)
        
        return SimilarityResponse(similarity=similarity)
        
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clip/clear-cache")
async def clear_cache():
    """Clear GPU cache."""
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    clip_service.clear_cache()
    return {"status": "cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)