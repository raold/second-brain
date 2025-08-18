"""
Google Drive Pipeline API - Feed the Beast!
"""

import os
import tarfile
import tempfile
import zipfile
from typing import Any

import py7zr
import rarfile
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.services.gdrive_processor import GDriveProcessor
from app.services.google_drive_simple import GoogleDriveService
from app.services.memory_service_postgres import MemoryServicePostgres
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/gdrive", tags=["gdrive-pipeline"])

# Global processor instance
processor: GDriveProcessor | None = None


def get_processor() -> GDriveProcessor:
    """Get or create the processor instance"""
    global processor
    if not processor:
        gdrive_service = GoogleDriveService()
        processor = GDriveProcessor(gdrive_service)
    return processor


@router.post("/process-folder")
async def process_folder(
    folder_id: str = "root",
    recursive: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    processor: GDriveProcessor = Depends(get_processor),
):
    """
    Start processing a Google Drive folder
    This unleashes the beast on your data!
    """
    # Check if authenticated
    gdrive = processor.gdrive
    if not gdrive.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")

    # Start processing in background
    background_tasks.add_task(
        process_folder_task,
        processor,
        folder_id,
        recursive,
    )

    return {
        "status": "processing_started",
        "folder_id": folder_id,
        "recursive": recursive,
        "message": "The beast is feeding! Check /api/v1/gdrive/process-status for progress.",
    }


async def process_folder_task(processor: GDriveProcessor, folder_id: str, recursive: bool) -> None:
    """Background task to process folder"""
    try:
        logger.info(f"Starting folder processing: {folder_id}")
        stats = await processor.process_folder(folder_id, recursive)
        logger.info(f"Processing complete: {stats}")

        # Store results in database
        await store_processing_results(processor)

    except Exception:
        logger.exception("Processing failed")


async def store_processing_results(processor: GDriveProcessor) -> None:
    """Store processed data in PostgreSQL"""
    MemoryServicePostgres()

    # This would store all the processed files
    # For now, just log the stats
    logger.info(f"Would store {processor.processing_stats['processed']} files in database")


@router.get("/process-status")
async def get_process_status(
    processor: GDriveProcessor = Depends(get_processor),
) -> dict[str, Any]:
    """Get the current processing status"""
    return processor.processing_stats


@router.post("/process-archive")
async def process_archive(
    file_id: str,
    background_tasks: BackgroundTasks,
    processor: GDriveProcessor = Depends(get_processor),
):
    """
    Process an archive file (.zip, .tar.gz, .rar, .7z)
    Extracts and processes all contents!
    """
    gdrive = processor.gdrive
    if not gdrive.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get file metadata
    file_metadata = await gdrive.get_file(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    file_name = file_metadata.get("name", "archive")
    file_metadata.get("mimeType", "")

    # Check if it's an archive
    archive_extensions = [".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".rar", ".7z"]
    is_archive = any(file_name.lower().endswith(ext) for ext in archive_extensions)

    if not is_archive:
        raise HTTPException(status_code=400, detail="File is not an archive")

    # Start processing in background
    background_tasks.add_task(
        process_archive_task,
        processor,
        file_id,
        file_metadata,
    )

    return {
        "status": "archive_processing_started",
        "file_id": file_id,
        "file_name": file_name,
        "message": "Archive extraction and processing started!",
    }


async def process_archive_task(
    processor: GDriveProcessor,
    file_id: str,
    file_metadata: dict[str, Any],
) -> None:
    """Extract and process archive contents"""
    file_name = file_metadata.get("name", "archive")

    try:
        logger.info(f"Downloading archive: {file_name}")

        # Download the archive
        content = await processor.gdrive.download_file(file_id)
        if not content:
            raise ValueError(f"Failed to download archive: {file_name}")

        # Extract based on type
        extracted_files = await extract_archive(content, file_name)

        logger.info(f"Extracted {len(extracted_files)} files from {file_name}")

        # Process each extracted file
        for file_info in extracted_files:
            try:
                # Create fake metadata for extracted file
                fake_metadata = {
                    "id": f"{file_id}_{file_info['name']}",
                    "name": file_info["name"],
                    "mimeType": file_info.get("mime_type", "application/octet-stream"),
                }

                # Process based on type
                if file_info["name"].lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                    # Process as image
                    await process_extracted_image(
                        processor,
                        file_info["content"],
                        fake_metadata,
                    )
                elif file_info["name"].lower().endswith((".txt", ".md", ".log", ".csv")):
                    # Process as text
                    await process_extracted_text(
                        processor,
                        file_info["content"],
                        fake_metadata,
                    )
                else:
                    logger.info(f"Skipping unsupported file type: {file_info['name']}")
                    continue

                processor.processing_stats["processed"] += 1
                logger.info(f"Processed: {file_info['name']}")

            except Exception:
                logger.exception(f"Failed to process {file_info['name']}")
                processor.processing_stats["failed"] += 1

    except Exception:
        logger.exception("Archive processing failed")


async def extract_archive(content: bytes, file_name: str) -> list[dict[str, Any]]:
    """
    Extract files from various archive formats
    Returns list of {'name': str, 'content': bytes, 'mime_type': str}
    """
    extracted_files = []

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_name) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if file_name.lower().endswith(".zip"):
            # Handle ZIP
            with zipfile.ZipFile(tmp_path, "r") as zf:
                for info in zf.infolist():
                    if not info.is_dir():
                        extracted_files.append(
                            {
                                "name": info.filename,
                                "content": zf.read(info.filename),
                                "mime_type": guess_mime_type(info.filename),
                            },
                        )

        elif file_name.lower().endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2")):
            # Handle TAR archives
            mode = (
                "r:gz"
                if file_name.lower().endswith(".gz")
                else "r:bz2" if file_name.lower().endswith(".bz2") else "r"
            )
            with tarfile.open(tmp_path, mode) as tf:
                for member in tf.getmembers():
                    if member.isfile():
                        f = tf.extractfile(member)
                        if f:
                            extracted_files.append(
                                {
                                    "name": member.name,
                                    "content": f.read(),
                                    "mime_type": guess_mime_type(member.name),
                                },
                            )

        elif file_name.lower().endswith(".7z"):
            # Handle 7z
            with py7zr.SevenZipFile(tmp_path, mode="r") as zf:
                for fname, bio in zf.read().items():
                    extracted_files.append(
                        {
                            "name": fname,
                            "content": bio.read(),
                            "mime_type": guess_mime_type(fname),
                        },
                    )

        elif file_name.lower().endswith(".rar"):
            # Handle RAR
            with rarfile.RarFile(tmp_path) as rf:
                for info in rf.infolist():
                    if not info.is_dir():
                        extracted_files.append(
                            {
                                "name": info.filename,
                                "content": rf.read(info.filename),
                                "mime_type": guess_mime_type(info.filename),
                            },
                        )

    finally:
        # Clean up temp file
        os.unlink(tmp_path)

    return extracted_files


def guess_mime_type(filename: str) -> str:
    """Guess MIME type from filename"""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "txt": "text/plain",
        "md": "text/markdown",
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "text/xml",
        "html": "text/html",
        "py": "text/x-python",
        "js": "text/javascript",
    }
    return mime_map.get(ext, "application/octet-stream")


async def process_extracted_image(
    processor: GDriveProcessor,
    content: bytes,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Process an extracted image file"""
    import base64

    import aiohttp

    img_base64 = base64.b64encode(content).decode("utf-8")

    async with aiohttp.ClientSession() as session:
        vision_analysis = await processor.analyze_with_llava(session, img_base64)
        clip_embedding = await processor.generate_clip_embedding(session, content)
        extracted_text = await processor.extract_text_from_image(session, img_base64)
        text_embedding = await processor.generate_text_embedding(
            session,
            f"{metadata['name']}\n{vision_analysis}\n{extracted_text}",
        )

    return {
        "file_id": metadata["id"],
        "file_name": metadata["name"],
        "type": "image",
        "vision_analysis": vision_analysis,
        "extracted_text": extracted_text,
        "clip_embedding": clip_embedding,
        "text_embedding": text_embedding,
        "from_archive": True,
    }


async def process_extracted_text(
    processor: GDriveProcessor,
    content: bytes,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Process an extracted text file"""
    import aiohttp

    text_content = content.decode("utf-8", errors="ignore")

    async with aiohttp.ClientSession() as session:
        text_embedding = await processor.generate_text_embedding(session, text_content)
        key_concepts = await processor.extract_concepts(session, text_content)

    return {
        "file_id": metadata["id"],
        "file_name": metadata["name"],
        "type": "text",
        "content": text_content[:1000],
        "key_concepts": key_concepts,
        "text_embedding": text_embedding,
        "from_archive": True,
    }


@router.post("/smart-sync")
async def smart_sync(
    background_tasks: BackgroundTasks,
    processor: GDriveProcessor = Depends(get_processor),
    include_archives: bool = True,
    max_files: int = 100,
):
    """
    Smart sync that automatically finds and processes:
    - Recent files
    - Archives (extracts and processes contents)
    - Images for vision analysis
    - Documents for text extraction
    """
    gdrive = processor.gdrive
    if not gdrive.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get recent files
    files = await gdrive.list_files(limit=max_files)

    stats = {
        "total_files": len(files),
        "archives": 0,
        "images": 0,
        "documents": 0,
        "other": 0,
    }

    # Categorize files
    for file in files:
        name = file.get("name", "").lower()
        mime = file.get("mimeType", "")

        if any(name.endswith(ext) for ext in [".zip", ".tar", ".gz", ".rar", ".7z"]):
            stats["archives"] += 1
        elif mime.startswith("image/"):
            stats["images"] += 1
        elif mime in ["application/pdf", "application/vnd.google-apps.document", "text/"]:
            stats["documents"] += 1
        else:
            stats["other"] += 1

    # Start processing
    background_tasks.add_task(smart_sync_task, processor, files, include_archives)

    return {
        "status": "smart_sync_started",
        "stats": stats,
        "message": f"Processing {len(files)} files intelligently!",
    }


async def smart_sync_task(
    processor: GDriveProcessor,
    files: list[dict[str, Any]],
    include_archives: bool,
) -> None:
    """Smart sync background task"""
    for file in files:
        name = file.get("name", "").lower()

        # Process archives first (they contain multiple files)
        if include_archives and any(
            name.endswith(ext) for ext in [".zip", ".tar", ".gz", ".rar", ".7z"]
        ):
            logger.info(f"📦 Processing archive: {file['name']}")
            await process_archive_task(processor, file["id"], file)
        else:
            # Process regular file
            await processor.process_file(file)
