"""
Batch Processing API Routes for Second Brain v2.6.0-dev
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.batch_processor import (
    BatchProcessor, BatchConfig, ProcessingMode, BatchStatus
)

router = APIRouter(prefix="/batch", tags=["batch"])

# Global batch processor instance
batch_processor = BatchProcessor()


class BatchJobRequest(BaseModel):
    """Request model for creating batch jobs"""
    name: str
    batch_size: int = Field(default=100, ge=1, le=10000)
    max_concurrent: int = Field(default=10, ge=1, le=100)
    mode: ProcessingMode = ProcessingMode.ADAPTIVE
    enable_checkpointing: bool = True


class MemoryBatchRequest(BatchJobRequest):
    """Request for batch processing memories"""
    memory_ids: List[UUID]
    operation: str = Field(description="Operation to perform: reprocess, export, analyze")


class ImportBatchRequest(BatchJobRequest):
    """Request for batch import"""
    format: str = Field(default="json", regex="^(json|csv|jsonl)$")


class ReprocessRequest(BatchJobRequest):
    """Request for reprocessing memories"""
    filters: Optional[dict] = None
    include_tags: Optional[List[str]] = None
    importance_min: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PatternAnalysisRequest(BatchJobRequest):
    """Request for pattern analysis"""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    analysis_types: List[str] = Field(
        default=["temporal", "semantic", "behavioral"],
        description="Types of patterns to analyze"
    )


@router.post("/process/memories")
async def batch_process_memories(
    request: MemoryBatchRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """
    Process a batch of memories with specified operation
    
    Operations:
    - reprocess: Re-run extraction pipeline
    - export: Export memories to file
    - analyze: Run analysis on memories
    """
    config = BatchConfig(
        batch_size=request.batch_size,
        max_concurrent=request.max_concurrent,
        mode=request.mode,
        enable_checkpointing=request.enable_checkpointing
    )
    
    processor = BatchProcessor(config)
    
    # Define operation based on request
    if request.operation == "reprocess":
        from app.ingestion.core_extraction_pipeline import CoreExtractionPipeline
        pipeline = CoreExtractionPipeline()
        
        async def reprocess_memory(memory):
            result = await pipeline.process(memory.content)
            # Update memory with results
            memory.metadata.update(result)
            await memory.save()
    
        operation = reprocess_memory
    elif request.operation == "export":
        # Export operation
        async def export_memory(memory):
            # Add to export buffer
            pass
        operation = export_memory
    else:
        raise HTTPException(400, f"Unknown operation: {request.operation}")
    
    # Start processing in background
    job = await processor.process_memories_batch(
        memory_ids=request.memory_ids,
        operation=operation,
        job_name=request.name
    )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "message": f"Batch job created for {len(request.memory_ids)} memories"
    }


@router.post("/process/files")
async def batch_process_files(
    files: List[UploadFile] = File(...),
    batch_size: int = 100,
    max_concurrent: int = 10,
    current_user=Depends(get_current_user)
):
    """
    Process multiple files in batch (images, audio, documents)
    """
    # Save uploaded files temporarily
    temp_dir = Path("temp_uploads") / f"batch_{datetime.now().timestamp()}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    file_paths = []
    for file in files:
        file_path = temp_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        file_paths.append(file_path)
    
    config = BatchConfig(
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        mode=ProcessingMode.ADAPTIVE
    )
    
    processor = BatchProcessor(config)
    job = await processor.process_files_batch(
        file_paths=file_paths,
        job_name=f"File batch: {len(files)} files"
    )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "files_count": len(files),
        "message": "File processing started"
    }


@router.post("/import")
async def batch_import(
    request: ImportBatchRequest,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """
    Import memories from file in batch
    
    Supported formats:
    - JSON: Array of memory objects
    - CSV: Columnar data with headers
    - JSONL: Line-delimited JSON
    """
    # Save uploaded file
    import_dir = Path("imports")
    import_dir.mkdir(exist_ok=True)
    
    file_path = import_dir / f"{datetime.now().timestamp()}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)
    
    config = BatchConfig(
        batch_size=request.batch_size,
        max_concurrent=request.max_concurrent,
        mode=request.mode,
        enable_checkpointing=request.enable_checkpointing
    )
    
    processor = BatchProcessor(config)
    job = await processor.import_from_export(
        export_file=file_path,
        format=request.format,
        job_name=request.name
    )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "file_size": len(content),
        "format": request.format
    }


@router.post("/reprocess/all")
async def reprocess_all_memories(
    request: ReprocessRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """
    Reprocess all memories (or filtered subset) with latest extraction pipeline
    
    This is useful when:
    - New extraction features are added
    - Model improvements are available
    - Fixing extraction errors
    """
    # Build filters from request
    filters = request.filters or {}
    
    if request.include_tags:
        filters["tags"] = {"$in": request.include_tags}
    if request.importance_min is not None:
        filters["importance"] = {"$gte": request.importance_min}
    if request.date_from or request.date_to:
        filters["created_at"] = {}
        if request.date_from:
            filters["created_at"]["$gte"] = request.date_from
        if request.date_to:
            filters["created_at"]["$lte"] = request.date_to
    
    config = BatchConfig(
        batch_size=request.batch_size,
        max_concurrent=request.max_concurrent,
        mode=request.mode,
        enable_checkpointing=request.enable_checkpointing
    )
    
    processor = BatchProcessor(config)
    
    # Start reprocessing in background
    background_tasks.add_task(
        processor.reprocess_all_memories,
        filters=filters,
        job_name=request.name
    )
    
    return {
        "message": "Reprocessing job started",
        "filters": filters
    }


@router.post("/analyze/patterns")
async def analyze_patterns(
    request: PatternAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """
    Analyze patterns across memories in batch
    
    Analysis types:
    - temporal: Time-based patterns
    - semantic: Content similarity patterns  
    - behavioral: Usage and access patterns
    - structural: Memory organization patterns
    """
    time_range = None
    if request.date_from or request.date_to:
        time_range = (
            request.date_from or datetime.min,
            request.date_to or datetime.max
        )
    
    config = BatchConfig(
        batch_size=request.batch_size,
        max_concurrent=request.max_concurrent,
        mode=request.mode
    )
    
    processor = BatchProcessor(config)
    job = await processor.analyze_memory_patterns(
        time_range=time_range,
        job_name=request.name,
        analysis_types=request.analysis_types
    )
    
    return {
        "job_id": job.id,
        "status": job.status,
        "analysis_types": request.analysis_types,
        "time_range": time_range
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user)
):
    """Get status and progress of a batch job"""
    job = await batch_processor.get_job_status(job_id)
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "result_summary": job.result_summary
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user=Depends(get_current_user)
):
    """Cancel a running batch job"""
    success = await batch_processor.cancel_job(job_id)
    
    if not success:
        raise HTTPException(400, "Job cannot be cancelled")
    
    return {"message": "Job cancelled", "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    current_user=Depends(get_current_user)
):
    """Resume a failed or paused job from checkpoint"""
    job = await batch_processor.resume_job(job_id)
    
    if not job:
        raise HTTPException(400, "Job cannot be resumed")
    
    return {
        "message": "Job resumed",
        "job_id": job_id,
        "status": job.status
    }


@router.get("/jobs")
async def list_jobs(
    status: Optional[BatchStatus] = None,
    limit: int = 20,
    offset: int = 0,
    current_user=Depends(get_current_user)
):
    """List batch processing jobs"""
    all_jobs = list(batch_processor.jobs.values())
    
    # Filter by status if provided
    if status:
        all_jobs = [j for j in all_jobs if j.status == status]
    
    # Sort by created_at descending
    all_jobs.sort(key=lambda j: j.created_at, reverse=True)
    
    # Paginate
    jobs = all_jobs[offset:offset + limit]
    
    return {
        "jobs": jobs,
        "total": len(all_jobs),
        "limit": limit,
        "offset": offset
    }


# Add performance monitoring endpoint
@router.get("/stats")
async def get_batch_stats(current_user=Depends(get_current_user)):
    """Get batch processing statistics"""
    jobs = batch_processor.jobs.values()
    
    stats = {
        "total_jobs": len(jobs),
        "by_status": {},
        "avg_processing_time": 0,
        "total_items_processed": 0,
        "overall_success_rate": 0
    }
    
    # Calculate statistics
    completed_jobs = []
    total_processed = 0
    total_succeeded = 0
    
    for job in jobs:
        # Count by status
        status = job.status.value
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        # Collect completed jobs
        if job.status == BatchStatus.COMPLETED and job.completed_at and job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            completed_jobs.append(duration)
        
        # Sum processed items
        if job.progress:
            total_processed += job.progress.get("processed", 0)
            total_succeeded += job.progress.get("succeeded", 0)
    
    # Calculate averages
    if completed_jobs:
        stats["avg_processing_time"] = sum(completed_jobs) / len(completed_jobs)
    
    if total_processed > 0:
        stats["overall_success_rate"] = total_succeeded / total_processed
    
    stats["total_items_processed"] = total_processed
    
    return stats