"""
Enhanced Google Drive Integration Routes with multimodal support
Production-ready with file validation, duplicate detection, and batch processing
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.services.google_drive_enhanced import google_drive_enhanced
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class BatchIngestRequest(BaseModel):
    """Request model for batch file ingestion"""
    file_ids: list[str]
    force: bool = False


class IngestFileRequest(BaseModel):
    """Request model for single file ingestion"""
    force: bool = False


@router.get("/status")
async def get_status():
    """Get enhanced Google Drive connection status with capabilities"""
    status = google_drive_enhanced.get_connection_status()
    status["credentials_configured"] = bool(
        google_drive_enhanced.client_id and google_drive_enhanced.client_secret
    )
    status["capabilities"] = {
        "multimodal": True,
        "ocr_available": True,
        "max_file_size_mb": 250,
        "batch_processing": True,
        "duplicate_detection": True,
        "supported_categories": ["text", "code", "document", "image", "spreadsheet", "ebook"]
    }
    return status


@router.post("/connect")
async def connect():
    """Initiate OAuth flow"""
    if not google_drive_enhanced.client_id:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    auth_url = google_drive_enhanced.get_auth_url()
    return {"auth_url": auth_url}


@router.get("/callback")
async def oauth_callback(code: str):
    """Handle OAuth callback with enhanced error handling"""
    result = await google_drive_enhanced.exchange_code(code)

    if result.get("success"):
        # Redirect to UI with success
        return RedirectResponse(url="/static/gdrive-ui.html?connected=true", status_code=302)
    else:
        # Show detailed error
        html = (
            "<html><head><title>Connection Failed</title>"
            "<style>"
            "body{font-family:system-ui;display:flex;justify-content:center;"
            "align-items:center;height:100vh;background:#f3f4f6}"
            ".error{background:white;padding:2rem;border-radius:8px;"
            "box-shadow:0 2px 10px rgba(0,0,0,0.1);max-width:500px}"
            "h1{color:#ef4444}"
            "pre{background:#f9fafb;padding:1rem;border-radius:4px;overflow-x:auto}"
            "a{display:inline-block;margin-top:1rem;padding:0.5rem 1rem;"
            "background:#3b82f6;color:white;text-decoration:none;border-radius:4px}"
            "</style></head><body>"
            '<div class="error">'
            "<h1>Connection Failed</h1>"
            "<p>Could not connect to Google Drive:</p>"
            f"<pre>{result.get('error', 'Unknown error')}</pre>"
            '<a href="/static/gdrive-ui.html">Try Again</a>'
            "</div></body></html>"
        )
        return HTMLResponse(content=html)


@router.get("/files")
async def list_files(
    folder_id: Optional[str] = None,
    show_ingested: bool = True
):
    """
    List files from Google Drive with ingestion status

    Args:
        folder_id: Optional folder ID to list files from
        show_ingested: Whether to include already ingested files
    """
    if not google_drive_enhanced.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    files = await google_drive_enhanced.list_files(folder_id)

    # Filter out already ingested if requested
    if not show_ingested:
        files = [f for f in files if not f.get('already_ingested', False)]

    # Add content type info
    for file in files:
        mime_type = file.get('mimeType', '')
        is_supported, category = google_drive_enhanced._validate_content_type(mime_type)
        file['supported'] = is_supported
        file['content_category'] = category if is_supported else None

    return {
        "files": files,
        "total_count": len(files),
        "stats": {
            "ingested": sum(1 for f in files if f.get('already_ingested')),
            "supported": sum(1 for f in files if f.get('supported')),
            "unsupported": sum(1 for f in files if not f.get('supported'))
        }
    }


@router.post("/ingest-file/{file_id}", status_code=status.HTTP_201_CREATED)
async def ingest_file(file_id: str, request: IngestFileRequest = IngestFileRequest()):
    """
    Ingests a single file from Google Drive with enhanced processing
    Handles multimodal content, validates size/type, and checks duplicates

    Args:
        file_id: Google Drive file ID
        request: Ingestion options (force re-ingestion)
    """
    if not google_drive_enhanced.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    try:
        result = await google_drive_enhanced.ingest_file(file_id, force=request.force)

        if result:
            if result.get("status") == "skipped":
                # File was skipped for a valid reason
                return {
                    "status": "skipped",
                    "reason": result.get("reason"),
                    "details": result
                }
            else:
                # Successfully created memory
                return {
                    "status": "success",
                    "memory_id": result.get("id"),
                    "content_category": result.get("content_category"),
                    "details": result
                }
        else:
            raise HTTPException(status_code=500, detail="Failed to create memory for the file")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/batch-ingest", status_code=status.HTTP_202_ACCEPTED)
async def batch_ingest(request: BatchIngestRequest):
    """
    Batch ingest multiple files from Google Drive

    Args:
        request: List of file IDs and options
    """
    if not google_drive_enhanced.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    if not request.file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")

    if len(request.file_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per batch")

    try:
        # Start batch ingestion (could be made async with background tasks)
        results = await google_drive_enhanced.batch_ingest(request.file_ids)

        return {
            "status": "completed",
            "summary": {
                "total": results["total"],
                "successful": results["successful"],
                "skipped": results["skipped"],
                "failed": results["failed"]
            },
            "details": results["details"]
        }

    except Exception as e:
        logger.error(f"Error in batch ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Batch ingestion failed: {e}")


@router.websocket("/ws/batch-ingest")
async def websocket_batch_ingest(websocket: WebSocket):
    """
    WebSocket endpoint for real-time batch ingestion progress

    Client sends: {"file_ids": [...], "force": false}
    Server sends: {"type": "progress", "current": 1, "total": 10, "percentage": 10.0}
                  {"type": "result", "file_id": "...", "status": "success"}
                  {"type": "complete", "summary": {...}}
    """
    await websocket.accept()

    try:
        # Wait for ingestion request
        data = await websocket.receive_json()
        file_ids = data.get("file_ids", [])
        force = data.get("force", False)

        if not google_drive_enhanced.is_connected():
            await websocket.send_json({
                "type": "error",
                "message": "Not connected to Google Drive"
            })
            return

        # Progress callback for WebSocket updates
        async def progress_callback(update):
            await websocket.send_json({
                "type": "progress",
                **update
            })

        # Perform batch ingestion with progress updates
        results = {
            "total": len(file_ids),
            "successful": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }

        for i, file_id in enumerate(file_ids, 1):
            try:
                result = await google_drive_enhanced.ingest_file(file_id, force=force)

                # Send progress
                await websocket.send_json({
                    "type": "progress",
                    "current": i,
                    "total": len(file_ids),
                    "percentage": (i / len(file_ids)) * 100,
                    "file_id": file_id
                })

                # Send result
                if result:
                    if result.get("status") == "skipped":
                        results["skipped"] += 1
                        status_type = "skipped"
                    else:
                        results["successful"] += 1
                        status_type = "success"

                    await websocket.send_json({
                        "type": "result",
                        "file_id": file_id,
                        "status": status_type,
                        "details": result
                    })
                else:
                    results["failed"] += 1
                    await websocket.send_json({
                        "type": "result",
                        "file_id": file_id,
                        "status": "failed"
                    })

            except Exception as e:
                logger.error(f"Error ingesting file {file_id}: {e}")
                results["failed"] += 1
                await websocket.send_json({
                    "type": "result",
                    "file_id": file_id,
                    "status": "error",
                    "error": str(e)
                })

        # Send completion summary
        await websocket.send_json({
            "type": "complete",
            "summary": results
        })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass


@router.get("/validate/{file_id}")
async def validate_file(file_id: str):
    """
    Validate if a file can be ingested without actually ingesting it

    Args:
        file_id: Google Drive file ID

    Returns:
        Validation result with details about the file
    """
    if not google_drive_enhanced.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    try:
        # Check if already ingested
        is_duplicate = await google_drive_enhanced.check_duplicate(file_id)

        # Get file metadata to check type and size
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f'Bearer {google_drive_enhanced.tokens["access_token"]}'}
            metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {"fields": "id,name,mimeType,modifiedTime,webViewLink,size"}

            async with session.get(metadata_url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=404, detail="File not found")
                metadata = await resp.json()

        # Validate content type
        mime_type = metadata.get("mimeType", "")
        is_supported, content_category = google_drive_enhanced._validate_content_type(mime_type)

        # Check file size
        file_size = metadata.get('size')
        size_ok = True
        size_mb = None
        if file_size:
            file_size_int = int(file_size)
            size_mb = file_size_int / (1024 * 1024)
            size_ok = file_size_int <= 250 * 1024 * 1024

        return {
            "file_id": file_id,
            "name": metadata.get("name"),
            "mime_type": mime_type,
            "size_mb": size_mb,
            "validation": {
                "is_duplicate": is_duplicate,
                "type_supported": is_supported,
                "size_ok": size_ok,
                "can_ingest": not is_duplicate and is_supported and size_ok
            },
            "content_category": content_category if is_supported else None,
            "web_link": metadata.get("webViewLink")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.post("/disconnect")
async def disconnect():
    """Disconnect from Google Drive and clear tokens"""
    google_drive_enhanced.tokens = {}
    google_drive_enhanced.user_info = {}
    google_drive_enhanced._ingested_files.clear()
    return {"status": "disconnected", "message": "Successfully disconnected from Google Drive"}

