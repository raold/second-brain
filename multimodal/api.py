"""
Multi-Modal Memory API for Second Brain v2.6.0
Enhanced FastAPI endpoints supporting text, audio, video, image, and document content
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiofiles
from fastapi import (
    APIRouter, 
    BackgroundTasks, 
    Depends, 
    File, 
    Form, 
    HTTPException, 
    Query, 
    UploadFile, 
    status
)
from fastapi.responses import JSONResponse

from .models import (
    ContentType,
    MultiModalMemoryCreate,
    MultiModalMemoryResponse,
    MultiModalMemoryUpdate,
    MultiModalSearchRequest,
    MultiModalSearchResponse,
    MultiModalStats,
    FileUploadRequest,
    FileUploadResponse,
    ProcessingStatus
)
from .processing import MultiModalProcessingService, ProcessingError
from .database import MultiModalDatabase

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/multimodal", tags=["Multimodal Memory"])

# Services
processing_service = MultiModalProcessingService()
database = MultiModalDatabase()


# Dependency for authentication (implement based on your auth system)
async def get_current_user():
    """Placeholder for authentication - implement based on your auth system."""
    # This should validate API tokens, JWT tokens, etc.
    return {"user_id": "default_user"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    content: Optional[str] = Form(None),
    importance: float = Form(5.0),
    tags: str = Form(""),
    auto_process: bool = Form(True),
    extract_text: bool = Form(True),
    generate_summary: bool = Form(True),
    analyze_content: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process a multimodal file."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Check file size (100MB limit)
        max_size = 100 * 1024 * 1024
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            )
        
        # Save file temporarily
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"upload_{int(time.time())}_{file.filename}"
        
        async with aiofiles.open(temp_file, 'wb') as f:
            content_bytes = await file.read()
            await f.write(content_bytes)
        
        # Detect content type
        content_type = await processing_service.detect_content_type(str(temp_file))
        
        # Create memory record
        memory_data = MultiModalMemoryCreate(
            content=content or f"Uploaded file: {file.filename}",
            content_type=content_type,
            file_name=file.filename,
            file_path=str(temp_file),
            mime_type=file.content_type,
            importance=max(0.0, min(10.0, importance)),
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            metadata={
                "uploaded_by": current_user.get("user_id"),
                "original_filename": file.filename,
                "file_size": len(content_bytes)
            }
        )
        
        # Save to database
        memory_id = await database.create_memory(memory_data)
        
        # Process in background if requested
        if auto_process:
            background_tasks.add_task(
                process_memory_background,
                memory_id,
                str(temp_file),
                {
                    "extract_text": extract_text,
                    "generate_summary": generate_summary,
                    "analyze_content": analyze_content
                }
            )
            processing_status = ProcessingStatus.PENDING
        else:
            processing_status = ProcessingStatus.COMPLETED
        
        return FileUploadResponse(
            memory_id=memory_id,
            file_name=file.filename,
            file_size=len(content_bytes),
            content_type=content_type,
            processing_status=processing_status,
            message="File uploaded successfully"
        )
        
    except ProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed"
        )


async def process_memory_background(
    memory_id: UUID, 
    file_path: str, 
    processing_options: Dict[str, Any]
):
    """Background task for processing uploaded files."""
    try:
        # Update status to processing
        await database.update_processing_status(memory_id, ProcessingStatus.PROCESSING)
        
        # Process the file
        result = await processing_service.process_file(file_path, **processing_options)
        
        # Update memory with results
        update_data = MultiModalMemoryUpdate(
            extracted_text=result.get('extracted_text'),
            summary=result.get('summary'),
            keywords=result.get('keywords', []),
            entities=result.get('entities', {}),
            sentiment=result.get('sentiment', {})
        )
        
        await database.update_memory(memory_id, update_data)
        await database.update_processing_status(memory_id, ProcessingStatus.COMPLETED)
        
        # Clean up temp file
        Path(file_path).unlink(missing_ok=True)
        
        logger.info(f"Successfully processed memory {memory_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {memory_id}: {e}")
        await database.update_processing_status(
            memory_id, 
            ProcessingStatus.FAILED,
            error_message=str(e)
        )


@router.post("/memories", response_model=MultiModalMemoryResponse)
async def create_memory(
    memory: MultiModalMemoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new multimodal memory."""
    try:
        memory_id = await database.create_memory(memory)
        return await database.get_memory(memory_id)
    except Exception as e:
        logger.error(f"Create memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory"
        )


@router.get("/memories", response_model=List[MultiModalMemoryResponse])
async def list_memories(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    content_type: Optional[ContentType] = Query(None),
    importance_min: Optional[float] = Query(None, ge=0.0, le=10.0),
    importance_max: Optional[float] = Query(None, ge=0.0, le=10.0),
    tags: Optional[str] = Query(None),
    processing_status: Optional[ProcessingStatus] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List multimodal memories with filtering."""
    try:
        filters = {}
        if content_type:
            filters['content_type'] = content_type
        if importance_min is not None:
            filters['importance_min'] = importance_min
        if importance_max is not None:
            filters['importance_max'] = importance_max
        if tags:
            filters['tags'] = [tag.strip() for tag in tags.split(",")]
        if processing_status:
            filters['processing_status'] = processing_status
        
        return await database.list_memories(
            limit=limit,
            offset=offset,
            filters=filters
        )
    except Exception as e:
        logger.error(f"List memories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memories"
        )


@router.get("/memories/{memory_id}", response_model=MultiModalMemoryResponse)
async def get_memory(
    memory_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific multimodal memory."""
    try:
        memory = await database.get_memory(memory_id)
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        return memory
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory"
        )


@router.put("/memories/{memory_id}", response_model=MultiModalMemoryResponse)
async def update_memory(
    memory_id: UUID,
    memory_update: MultiModalMemoryUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a multimodal memory."""
    try:
        # Check if memory exists
        existing_memory = await database.get_memory(memory_id)
        if not existing_memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        await database.update_memory(memory_id, memory_update)
        return await database.get_memory(memory_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory"
        )


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Delete a multimodal memory."""
    try:
        # Check if memory exists
        existing_memory = await database.get_memory(memory_id)
        if not existing_memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        await database.delete_memory(memory_id)
        return {"message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory"
        )


@router.post("/search", response_model=MultiModalSearchResponse)
async def search_memories(
    search_request: MultiModalSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search multimodal memories with advanced filtering."""
    try:
        start_time = time.time()
        
        results = await database.search_memories(search_request)
        
        processing_time = time.time() - start_time
        
        return MultiModalSearchResponse(
            results=results,
            total_count=len(results),
            query=search_request.query,
            processing_time=processing_time,
            filters_applied={
                "content_types": search_request.content_types,
                "importance_range": [search_request.importance_min, search_request.importance_max],
                "tags": search_request.tags,
                "threshold": search_request.threshold
            }
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/stats", response_model=MultiModalStats)
async def get_multimodal_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for multimodal content."""
    try:
        return await database.get_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.post("/reprocess/{memory_id}")
async def reprocess_memory(
    memory_id: UUID,
    background_tasks: BackgroundTasks,
    extract_text: bool = Query(True),
    generate_summary: bool = Query(True),
    analyze_content: bool = Query(True),
    current_user: dict = Depends(get_current_user)
):
    """Reprocess an existing memory."""
    try:
        # Check if memory exists
        memory = await database.get_memory(memory_id)
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        if not memory.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Memory has no associated file to reprocess"
            )
        
        # Add reprocessing task
        background_tasks.add_task(
            process_memory_background,
            memory_id,
            memory.file_path,
            {
                "extract_text": extract_text,
                "generate_summary": generate_summary,
                "analyze_content": analyze_content
            }
        )
        
        return {"message": "Reprocessing started", "memory_id": memory_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reprocess error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reprocessing failed to start"
        )


@router.get("/processing-queue")
async def get_processing_queue(
    current_user: dict = Depends(get_current_user)
):
    """Get current processing queue status."""
    try:
        queue_items = await database.get_processing_queue()
        return {
            "queue_size": len(queue_items),
            "items": queue_items
        }
    except Exception as e:
        logger.error(f"Processing queue error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing queue"
        )


@router.get("/health")
async def multimodal_health_check():
    """Health check for multimodal services."""
    try:
        # Check database connection
        db_healthy = await database.health_check()
        
        # Check processing service
        processing_healthy = True  # Add actual health check for processing service
        
        # Get basic stats
        stats = await database.get_stats()
        
        return {
            "status": "healthy" if db_healthy and processing_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "processing_service": "available" if processing_healthy else "unavailable",
            "total_memories": stats.total_memories,
            "processing_queue_size": stats.processing_queue_size,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# Export router
__all__ = ['router']
