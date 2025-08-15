"""
Real Google Drive Integration Routes
Actually works with Google Drive API
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.services.google_drive_simple import google_drive
from app.services.memory_service_postgres import MemoryServicePostgres
from app.utils.logging_config import get_logger

# Import OpenAI for embeddings
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)
router = APIRouter()


# Models
class SyncFileRequest(BaseModel):
    file_id: str
    process: bool = True


class BatchSyncRequest(BaseModel):
    file_ids: List[str]
    generate_embeddings: bool = True


# Dependency for memory service
async def get_memory_service():
    """Get PostgreSQL memory service"""
    try:
        from app.factory import get_memory_service_instance

        return get_memory_service_instance()
    except ImportError:
        return MemoryServicePostgres()


@router.get("/status")
async def get_status():
    """Get Google Drive connection status"""
    status = google_drive.get_connection_status()
    status["credentials_configured"] = bool(google_drive.client_id and google_drive.client_secret)
    return status


@router.post("/connect")
async def connect():
    """Initiate OAuth flow"""
    if not google_drive.client_id:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    auth_url = google_drive.get_auth_url()
    return {"auth_url": auth_url}


@router.get("/callback")
async def oauth_callback(code: str):
    """Handle OAuth callback"""
    result = await google_drive.exchange_code(code)

    if result.get("success"):
        # Redirect to UI with success
        return RedirectResponse(url="/static/gdrive-ui.html?connected=true", status_code=302)
    else:
        # Show error
        html = (
            "<html><head><title>Connection Failed</title>"
            "<style>"
            "body{font-family:system-ui;display:flex;justify-content:center;"
            "align-items:center;height:100vh;background:#f3f4f6}"
            ".error{background:white;padding:2rem;border-radius:8px;"
            "box-shadow:0 2px 10px rgba(0,0,0,0.1);max-width:500px}"
            "h1{color:#ef4444}"
            "pre{background:#f9fafb;padding:1rem;border-radius:4px}"
            "a{display:inline-block;margin-top:1rem;padding:0.5rem 1rem;"
            "background:#3b82f6;color:white;text-decoration:none;border-radius:4px}"
            "</style></head><body>"
            '<div class="error">'
            "<h1>❌ Connection Failed</h1>"
            "<p>Could not connect to Google Drive:</p>"
            f"<pre>{result.get('error', 'Unknown error')}</pre>"
            '<a href="/static/gdrive-ui.html">Try Again</a>'
            "</div></body></html>"
        )
        return HTMLResponse(content=html)


@router.get("/files")
async def list_files(folder_id: Optional[str] = None):
    """List files from Google Drive"""
    if not google_drive.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    files = await google_drive.list_files(folder_id)
    return {"files": files, "count": len(files)}


@router.post("/sync/file")
async def sync_file(
    request: SyncFileRequest, memory_service: MemoryServicePostgres = Depends(get_memory_service)
):
    """Sync a single file to Second Brain"""
    if not google_drive.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    try:
        # Get file content
        content = await google_drive.get_file_content(request.file_id)
        if not content:
            raise HTTPException(status_code=404, detail="Could not retrieve file content")

        # Get file metadata
        files = await google_drive.list_files()
        file_info = next((f for f in files if f["id"] == request.file_id), None)

        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        # Generate embeddings if OpenAI is available
        embeddings = None
        if (
            OPENAI_AVAILABLE
            and os.getenv("OPENAI_API_KEY")
            and os.getenv("OPENAI_API_KEY") != "sk-mock-key-for-testing-only"
        ):
            try:
                openai.api_key = os.getenv("OPENAI_API_KEY")
                response = await openai.Embedding.acreate(
                    model="text-embedding-ada-002",
                    input=content[:8000],  # Limit to 8000 chars for embedding
                )
                embeddings = response["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"Could not generate embeddings: {e}")

        # Create memory in PostgreSQL
        memory_data = {
            "content": content[:10000],  # Limit content size
            "memory_type": "document",
            "tags": ["google-drive", file_info.get("mimeType", "unknown").split("/")[-1]],
            "metadata": {
                "source": "google_drive",
                "file_id": request.file_id,
                "file_name": file_info.get("name"),
                "mime_type": file_info.get("mimeType"),
                "size": file_info.get("size"),
                "modified_time": file_info.get("modifiedTime"),
                "web_view_link": file_info.get("webViewLink"),
            },
        }

        # Add embeddings to metadata if available
        if embeddings:
            memory_data["metadata"]["embeddings"] = embeddings

        memory = await memory_service.create_memory(**memory_data)

        return {
            "success": True,
            "memory_id": memory.get("id"),
            "file_name": file_info.get("name"),
            "content_length": len(content),
            "has_embeddings": embeddings is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/batch")
async def sync_batch(
    request: BatchSyncRequest, memory_service: MemoryServicePostgres = Depends(get_memory_service)
):
    """Sync multiple files in batch"""
    if not google_drive.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    results = []
    for file_id in request.file_ids[:10]:  # Limit to 10 files at a time
        try:
            result = await sync_file(
                SyncFileRequest(file_id=file_id, process=request.generate_embeddings),
                memory_service,
            )
            results.append(
                {"file_id": file_id, "status": "success", "memory_id": result.get("memory_id")}
            )
        except Exception as e:
            results.append({"file_id": file_id, "status": "failed", "error": str(e)})

    return {
        "processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }


@router.post("/disconnect")
async def disconnect():
    """Disconnect from Google Drive"""
    google_drive.tokens = {}
    google_drive.user_info = {}
    return {"status": "disconnected"}


@router.get("/search")
async def search_drive(q: str = Query(..., description="Search query")):
    """Search files in Google Drive"""
    if not google_drive.is_connected():
        raise HTTPException(status_code=401, detail="Not connected to Google Drive")

    # Search is just listing files for now
    # In production, you'd use the Drive API search
    files = await google_drive.list_files()

    # Simple text search
    query_lower = q.lower()
    matching = [f for f in files if query_lower in f.get("name", "").lower()]

    return {"query": q, "results": matching, "count": len(matching)}
