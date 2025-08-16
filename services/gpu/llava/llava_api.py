"""FastAPI server for LLaVA service with async processing."""

import io
import time
import uuid
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llava_service import LLaVAService
from shared.base_model import ModelStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
llava_service: Optional[LLaVAService] = None
redis_client: Optional[redis.Redis] = None


class AnalyzeRequest(BaseModel):
    instruction: str = "Describe this image in detail, including any text you can see."
    webhook_url: Optional[str] = None


class OCRRequest(BaseModel):
    webhook_url: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str
    webhook_url: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    description: str
    embedding: list
    dimensions: int
    ocr_text: Optional[str] = None
    processing_time_ms: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    global llava_service, redis_client
    
    # Startup
    logger.info("Starting LLaVA service...")
    
    # Initialize Redis for job queue
    try:
        redis_client = await redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Async processing disabled.")
        redis_client = None
    
    # Initialize and load model during startup
    llava_service = LLaVAService(load_in_4bit=True)
    logger.info("LLaVA service initialized, loading model...")
    
    # Load model proactively
    try:
        await llava_service.load_model()
        logger.info("LLaVA model loaded successfully during startup")
    except Exception as e:
        logger.warning(f"Could not load model during startup: {e}")
        logger.info("Model will load on first request")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLaVA service...")
    if llava_service and llava_service.model:
        llava_service.unload_model()
    if redis_client:
        await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="LLaVA Deep Understanding Service",
    description="Deep multimodal analysis with LLaVA",
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
        "service": "LLaVA Deep Understanding Service",
        "model": llava_service.model_name if llava_service else None,
        "status": "ready" if llava_service and llava_service.model else "not loaded",
        "async_enabled": redis_client is not None
    }


@app.get("/llava/status", response_model=ModelStatus)
async def get_status():
    """Get service status."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return llava_service.get_status()


@app.get("/llava/model-info")
async def get_model_info():
    """Get model information."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "model_name": llava_service.model_name,
        "embedding_dimensions": llava_service.embedding_dim,
        "quantization": "4-bit" if llava_service.load_in_4bit else "none",
        "device": llava_service.device,
        "device_info": llava_service.get_device_info() if llava_service.model else "Model not loaded"
    }


@app.post("/llava/embed/text")
async def embed_text(text: str = Body(...)):
    """Generate text embedding."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        embedding = await llava_service.generate_embedding(text)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "embedding": embedding.tolist(),
            "dimensions": len(embedding),
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llava/embed/image")
async def embed_image(
    file: UploadFile = File(...),
    instruction: str = Body(default="Describe this image in detail.")
):
    """Generate image embedding."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        image_bytes = await file.read()
        embedding = await llava_service.generate_embedding(image_bytes, instruction)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "embedding": embedding.tolist(),
            "dimensions": len(embedding),
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error embedding image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llava/analyze/image", response_model=AnalyzeResponse)
async def analyze_image(
    file: UploadFile = File(...),
    instruction: str = Body(default="Describe this image in detail, including any text you can see.")
):
    """Analyze image synchronously."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        image_bytes = await file.read()
        
        # Analyze image
        result = await llava_service.analyze_image(image_bytes, instruction)
        
        # Also extract text
        ocr_text = await llava_service.extract_text(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        return AnalyzeResponse(
            description=result["description"],
            embedding=result["embedding"],
            dimensions=result["dimensions"],
            ocr_text=ocr_text if ocr_text != "No text found" else None,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llava/ocr/image")
async def extract_text_from_image(file: UploadFile = File(...)):
    """Extract text from image (OCR)."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        image_bytes = await file.read()
        text = await llava_service.extract_text(image_bytes)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "text": text,
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llava/question/image")
async def answer_question_about_image(
    question: str = Body(...),
    file: UploadFile = File(...)
):
    """Answer a question about an image."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    start_time = time.time()
    
    try:
        image_bytes = await file.read()
        answer = await llava_service.answer_question(image_bytes, question)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "question": question,
            "answer": answer,
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Async queue endpoints
@app.post("/llava/queue/analyze")
async def queue_analyze_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    instruction: str = Body(default="Describe this image in detail."),
    webhook_url: Optional[str] = Body(default=None)
):
    """Queue image for async analysis."""
    if not redis_client:
        raise HTTPException(
            status_code=503, 
            detail="Async processing not available. Use synchronous endpoint."
        )
    
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Read image
        image_bytes = await file.read()
        
        # Create job entry
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "instruction": instruction,
            "webhook_url": webhook_url
        }
        
        # Store job in Redis
        await redis_client.hset(f"job:{job_id}", mapping=job_data)
        await redis_client.setex(f"job:image:{job_id}", 3600, image_bytes)  # 1 hour TTL
        
        # Add to queue
        await redis_client.lpush("llava:queue", job_id)
        
        # Process in background
        background_tasks.add_task(process_job, job_id)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/llava/queue/status/{job_id}"
        }
        
    except Exception as e:
        logger.error(f"Error queueing job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_job(job_id: str):
    """Process a queued job."""
    try:
        # Update status
        await redis_client.hset(f"job:{job_id}", "status", "processing")
        await redis_client.hset(f"job:{job_id}", "updated_at", datetime.utcnow().isoformat())
        
        # Get job data
        job_data = await redis_client.hgetall(f"job:{job_id}")
        image_bytes = await redis_client.get(f"job:image:{job_id}")
        
        if not image_bytes:
            raise ValueError("Image data not found")
        
        # Process with LLaVA
        result = await llava_service.analyze_image(
            image_bytes, 
            job_data.get("instruction", "Describe this image.")
        )
        
        # Extract text
        ocr_text = await llava_service.extract_text(image_bytes)
        
        # Update job with results
        result_data = {
            "status": "completed",
            "updated_at": datetime.utcnow().isoformat(),
            "result": json.dumps({
                "description": result["description"],
                "embedding": result["embedding"],
                "dimensions": result["dimensions"],
                "ocr_text": ocr_text if ocr_text != "No text found" else None
            })
        }
        
        await redis_client.hset(f"job:{job_id}", mapping=result_data)
        
        # Call webhook if provided
        if job_data.get("webhook_url"):
            # TODO: Implement webhook call
            pass
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        await redis_client.hset(f"job:{job_id}", mapping={
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow().isoformat()
        })


@app.get("/llava/queue/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a queued job."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Async processing not available")
    
    job_data = await redis_client.hgetall(f"job:{job_id}")
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Parse result if completed
    result = None
    if job_data.get("result"):
        result = json.loads(job_data["result"])
    
    return JobStatus(
        job_id=job_id,
        status=job_data.get("status", "unknown"),
        created_at=job_data.get("created_at", ""),
        updated_at=job_data.get("updated_at", ""),
        result=result,
        error=job_data.get("error")
    )


@app.post("/llava/clear-cache")
async def clear_cache():
    """Clear GPU cache."""
    if not llava_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    llava_service.clear_cache()
    return {"status": "cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)