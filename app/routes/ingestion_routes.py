"""
Ingestion routes for file upload and processing
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.dependencies import get_current_user, get_db_instance
from app.ingestion.engine import IngestionEngine
from app.models.memory import User
from app.repositories.memory_repository import MemoryRepository
from app.services.service_factory import ServiceFactory
from app.utils.logging_config import get_logger
from typing import Optional
from typing import List
from typing import Any
from fastapi import Depends
from fastapi import HTTPException
from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel
from pydantic import Field
from app.dependencies.auth import verify_api_key, get_current_user, get_db_instance

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


class IngestionStatus(BaseModel):
    """Status of an ingestion job"""
    job_id: str
    status: str = Field(..., description="pending, processing, completed, failed")
    filename: str
    file_type: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class IngestionResponse(BaseModel):
    """Response for file ingestion"""
    success: bool
    job_id: str
    message: str
    result: Optional[dict[str, Any]] = None


class BatchIngestionRequest(BaseModel):
    """Request for batch file ingestion"""
    tags: Optional[list[str]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


# In-memory job tracking (replace with Redis in production)
ingestion_jobs: dict[str, IngestionStatus] = {}


@router.post("/upload", response_model=IngestionResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_instance)
):
    """
    Upload and ingest a single file

    Supported file types:
    - PDF (.pdf)
    - Word documents (.docx, .doc)
    - Text files (.txt, .md)
    - HTML files (.html, .htm)
    - Images with OCR (.jpg, .jpeg, .png, .gif, .bmp, .tiff)
    - Spreadsheets (.xlsx, .xls, .csv)
    - Audio files with transcription (.mp3, .wav, .m4a, .flac, .ogg)
    - Video files with transcription (.mp4, .avi, .mov, .mkv, .webm)
    - Subtitle files (.srt, .vtt, .sub)
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Parse tags and metadata
    tag_list = tags.split(",") if tags else []
    meta_dict = {}
    if metadata:
        try:
            import json
            meta_dict = json.loads(metadata)
        except:
            logger.warning(f"Failed to parse metadata: {metadata}")

    # Create job ID
    job_id = f"{current_user.id}_{datetime.utcnow().timestamp()}"

    # Create job status
    job_status = IngestionStatus(
        job_id=job_id,
        status="pending",
        filename=file.filename,
        file_type=file.content_type or "unknown",
        created_at=datetime.utcnow()
    )
    ingestion_jobs[job_id] = job_status

    # Process in background
    background_tasks.add_task(
        process_file_ingestion,
        job_id=job_id,
        file=file,
        filename=file.filename,
        user_id=current_user.id,
        tags=tag_list,
        metadata=meta_dict,
        db=db
    )

    return IngestionResponse(
        success=True,
        job_id=job_id,
        message=f"File '{file.filename}' queued for processing"
    )


@router.post("/upload/batch", response_model=IngestionResponse)
async def upload_files_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    request: BatchIngestionRequest = BatchIngestionRequest(),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_instance)
):
    """
    Upload and ingest multiple files in batch
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create batch job ID
    job_id = f"batch_{current_user.id}_{datetime.utcnow().timestamp()}"

    # Create job status
    job_status = IngestionStatus(
        job_id=job_id,
        status="pending",
        filename=f"{len(files)} files",
        file_type="batch",
        created_at=datetime.utcnow()
    )
    ingestion_jobs[job_id] = job_status

    # Process in background
    background_tasks.add_task(
        process_batch_ingestion,
        job_id=job_id,
        files=files,
        user_id=current_user.id,
        tags=request.tags,
        metadata=request.metadata,
        db=db
    )

    return IngestionResponse(
        success=True,
        job_id=job_id,
        message=f"Batch of {len(files)} files queued for processing"
    )


@router.get("/status/{job_id}", response_model=IngestionStatus)
async def get_ingestion_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of an ingestion job"""
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_status = ingestion_jobs[job_id]

    # Verify user owns this job
    if not job_id.startswith(f"{current_user.id}_") and not job_id.startswith(f"batch_{current_user.id}_"):
        raise HTTPException(status_code=403, detail="Access denied")

    return job_status


@router.get("/jobs", response_model=list[IngestionStatus])
async def list_ingestion_jobs(
    current_user: User = Depends(get_current_user)
):
    """List all ingestion jobs for the current user"""
    user_jobs = [
        job for job_id, job in ingestion_jobs.items()
        if job_id.startswith(f"{current_user.id}_") or job_id.startswith(f"batch_{current_user.id}_")
    ]

    # Sort by created_at descending
    user_jobs.sort(key=lambda x: x.created_at, reverse=True)

    return user_jobs


@router.get("/supported-types")
async def get_supported_file_types():
    """Get list of supported file types"""
    return {
        "supported_types": [
            {
                "category": "Documents",
                "types": [
                    {"extension": ".pdf", "mime_type": "application/pdf"},
                    {"extension": ".docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    {"extension": ".doc", "mime_type": "application/msword"},
                    {"extension": ".txt", "mime_type": "text/plain"},
                    {"extension": ".md", "mime_type": "text/markdown"}
                ]
            },
            {
                "category": "Web",
                "types": [
                    {"extension": ".html", "mime_type": "text/html"},
                    {"extension": ".htm", "mime_type": "text/html"}
                ]
            },
            {
                "category": "Images",
                "types": [
                    {"extension": ".jpg", "mime_type": "image/jpeg"},
                    {"extension": ".jpeg", "mime_type": "image/jpeg"},
                    {"extension": ".png", "mime_type": "image/png"},
                    {"extension": ".gif", "mime_type": "image/gif"},
                    {"extension": ".bmp", "mime_type": "image/bmp"},
                    {"extension": ".tiff", "mime_type": "image/tiff"}
                ]
            },
            {
                "category": "Spreadsheets",
                "types": [
                    {"extension": ".xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                    {"extension": ".xls", "mime_type": "application/vnd.ms-excel"},
                    {"extension": ".csv", "mime_type": "text/csv"}
                ]
            }
        ],
        "max_file_size_mb": 100,
        "notes": [
            "Images are processed using OCR to extract text",
            "Large files may take longer to process",
            "Batch upload supports up to 10 files at once"
        ]
    }


async def process_file_ingestion(
    job_id: str,
    file: UploadFile,
    filename: str,
    user_id: str,
    tags: list[str],
    metadata: dict[str, Any],
    db
):
    """Process file ingestion in background"""
    job_status = ingestion_jobs[job_id]
    job_status.status = "processing"

    try:
        # Initialize services
        memory_repository = MemoryRepository(db)
        service_factory = ServiceFactory(db)
        ingestion_engine = IngestionEngine(
            memory_repository=memory_repository,
            extraction_pipeline=service_factory.core_extraction_pipeline
        )

        # Read file content
        content = await file.read()

        # Ingest file
        result = await ingestion_engine.ingest_file(
            file=content,
            filename=filename,
            user_id=user_id,
            tags=tags,
            metadata=metadata
        )

        # Update job status
        job_status.status = "completed"
        job_status.completed_at = datetime.utcnow()
        job_status.result = {
            "success": result.success,
            "memories_created": len(result.memories_created),
            "chunks_processed": result.chunks_processed,
            "processing_time": result.processing_time,
            "file_hash": result.file_metadata.hash
        }

        if not result.success:
            job_status.status = "failed"
            job_status.error = "; ".join(result.errors)

    except Exception as e:
        logger.error(f"Failed to process file {filename}: {str(e)}")
        job_status.status = "failed"
        job_status.error = str(e)
        job_status.completed_at = datetime.utcnow()


async def process_batch_ingestion(
    job_id: str,
    files: list[UploadFile],
    user_id: str,
    tags: list[str],
    metadata: dict[str, Any],
    db
):
    """Process batch file ingestion in background"""
    job_status = ingestion_jobs[job_id]
    job_status.status = "processing"

    try:
        # Initialize services
        memory_repository = MemoryRepository(db)
        service_factory = ServiceFactory(db)
        ingestion_engine = IngestionEngine(
            memory_repository=memory_repository,
            extraction_pipeline=service_factory.core_extraction_pipeline
        )

        # Process each file
        results = []
        total_memories = 0
        total_chunks = 0
        failed_files = []

        for file in files:
            try:
                content = await file.read()
                result = await ingestion_engine.ingest_file(
                    file=content,
                    filename=file.filename,
                    user_id=user_id,
                    tags=tags,
                    metadata=metadata
                )

                if result.success:
                    total_memories += len(result.memories_created)
                    total_chunks += result.chunks_processed
                else:
                    failed_files.append({
                        "filename": file.filename,
                        "error": "; ".join(result.errors)
                    })

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {str(e)}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        # Update job status
        job_status.status = "completed"
        job_status.completed_at = datetime.utcnow()
        job_status.result = {
            "total_files": len(files),
            "successful_files": len(files) - len(failed_files),
            "failed_files": len(failed_files),
            "total_memories_created": total_memories,
            "total_chunks_processed": total_chunks,
            "failures": failed_files if failed_files else None
        }

        if len(failed_files) == len(files):
            job_status.status = "failed"
            job_status.error = "All files failed to process"

    except Exception as e:
        logger.error(f"Failed to process batch: {str(e)}")
        job_status.status = "failed"
        job_status.error = str(e)
        job_status.completed_at = datetime.utcnow()
