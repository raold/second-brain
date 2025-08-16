"""
FastAPI wrapper for LM Studio integration
Port 8004 - Local LLM processing
"""

import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from lm_studio_service import LMStudioService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instance
lm_studio: Optional[LMStudioService] = None


class TextRequest(BaseModel):
    text: str
    max_tokens: int = 500
    temperature: float = 0.7
    model: Optional[str] = None


class EmbeddingRequest(BaseModel):
    text: str
    model: Optional[str] = None


class SummarizeRequest(BaseModel):
    content: str
    max_length: int = 500


class QuestionRequest(BaseModel):
    context: str
    question: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global lm_studio
    
    # Startup
    logger.info("Initializing LM Studio service...")
    lm_studio = LMStudioService()
    
    # Check if LM Studio is running
    if await lm_studio.check_health():
        logger.info("✅ LM Studio is running and ready")
        models = await lm_studio.get_models()
        logger.info(f"Available models: {models}")
    else:
        logger.warning("⚠️ LM Studio is not running. Please start it on port 1234")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LM Studio service...")


# Create FastAPI app
app = FastAPI(
    title="LM Studio Local LLM Service",
    description="Local text generation and embeddings via LM Studio",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "LM Studio Integration",
        "port": 8004,
        "status": "ready" if await lm_studio.check_health() else "LM Studio not running",
        "features": [
            "Text generation",
            "Document summarization",
            "Keyword extraction",
            "Question answering",
            "Embeddings (if model available)"
        ]
    }


@app.get("/lm-studio/status")
async def get_status():
    """Check LM Studio status"""
    healthy = await lm_studio.check_health()
    models = await lm_studio.get_models() if healthy else []
    
    return {
        "running": healthy,
        "base_url": lm_studio.base_url,
        "models": models,
        "model_count": len(models)
    }


@app.post("/lm-studio/generate")
async def generate_text(request: TextRequest):
    """Generate text using LM Studio"""
    if not await lm_studio.check_health():
        raise HTTPException(status_code=503, detail="LM Studio is not running")
    
    start_time = time.time()
    
    try:
        response = await lm_studio.generate_text(
            request.text,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            model=request.model
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "response": response,
            "processing_time_ms": processing_time,
            "model": request.model or "default"
        }
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lm-studio/embed")
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding using LM Studio"""
    if not await lm_studio.check_health():
        raise HTTPException(status_code=503, detail="LM Studio is not running")
    
    start_time = time.time()
    
    try:
        embedding = await lm_studio.generate_embedding(request.text, request.model)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "embedding": embedding.tolist(),
            "dimensions": len(embedding),
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lm-studio/summarize")
async def summarize_document(request: SummarizeRequest):
    """Summarize a document"""
    if not await lm_studio.check_health():
        raise HTTPException(status_code=503, detail="LM Studio is not running")
    
    start_time = time.time()
    
    try:
        summary = await lm_studio.summarize_document(
            request.content,
            request.max_length
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "summary": summary,
            "processing_time_ms": processing_time,
            "original_length": len(request.content),
            "summary_length": len(summary)
        }
        
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lm-studio/keywords")
async def extract_keywords(content: str = Body(...)):
    """Extract keywords from content"""
    if not await lm_studio.check_health():
        raise HTTPException(status_code=503, detail="LM Studio is not running")
    
    start_time = time.time()
    
    try:
        keywords = await lm_studio.extract_keywords(content)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "keywords": keywords,
            "count": len(keywords),
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"Keyword extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lm-studio/answer")
async def answer_question(request: QuestionRequest):
    """Answer a question based on context"""
    if not await lm_studio.check_health():
        raise HTTPException(status_code=503, detail="LM Studio is not running")
    
    start_time = time.time()
    
    try:
        answer = await lm_studio.answer_question(
            request.context,
            request.question
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "question": request.question,
            "answer": answer,
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        logger.error(f"QA error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)