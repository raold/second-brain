"""
Google Drive integration routes
"""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies import get_current_user, get_db
from app.ingestion.engine import IngestionEngine
from app.ingestion.google_drive_client import DriveFile, GoogleDriveClient
from app.models import User
from app.repositories.memory_repository import MemoryRepository
from app.utils.logger import get_logger
from typing import Optional
from typing import List
from typing import Any
from fastapi import Query
from fastapi import Depends
from fastapi import HTTPException
from fastapi import APIRouter
from pydantic import BaseModel
from pydantic import Field

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/google-drive", tags=["google-drive"])


class GoogleAuthRequest(BaseModel):
    """Request for Google OAuth authentication"""
    auth_code: str = Field(..., description="Authorization code from Google OAuth")


class GoogleDriveFileResponse(BaseModel):
    """Response for Google Drive file"""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None
    is_folder: bool = False
    is_supported: bool = True


class GoogleDriveIngestionRequest(BaseModel):
    """Request for ingesting files from Google Drive"""
    file_ids: list[str] = Field(..., description="List of Google Drive file IDs to ingest")
    tags: Optional[list[str]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class FolderMonitorRequest(BaseModel):
    """Request for monitoring a Google Drive folder"""
    folder_id: str = Field(..., description="Google Drive folder ID to monitor")
    check_interval: int = Field(default=300, ge=60, le=3600, description="Check interval in seconds")
    auto_ingest: bool = Field(default=True, description="Automatically ingest new files")
    tags: Optional[list[str]] = Field(default_factory=list)


# Global client instance (per-user in production)
drive_clients: dict[str, GoogleDriveClient] = {}


def get_drive_client(user_id: str) -> GoogleDriveClient:
    """Get or create Google Drive client for user"""
    if user_id not in drive_clients:
        client_path = f"credentials/google_drive_{user_id}.pickle"
        drive_clients[user_id] = GoogleDriveClient(credentials_path=client_path)
    return drive_clients[user_id]


@router.get("/auth/url")
async def get_auth_url(current_user: User = Depends(get_current_user)):
    """Get Google OAuth authorization URL"""
    try:
        client = get_drive_client(current_user.id)
        auth_url = client.get_auth_url()

        return {
            "auth_url": auth_url,
            "instructions": [
                "1. Click the auth_url to authorize access to Google Drive",
                "2. Copy the authorization code from Google",
                "3. Call POST /api/v1/google-drive/auth/callback with the code"
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/callback")
async def auth_callback(
    request: GoogleAuthRequest,
    current_user: User = Depends(get_current_user)
):
    """Complete Google OAuth authentication"""
    try:
        client = get_drive_client(current_user.id)
        success = await client.authenticate(auth_code=request.auth_code)

        if not success:
            raise HTTPException(status_code=400, detail="Authentication failed")

        return {
            "success": True,
            "message": "Successfully authenticated with Google Drive"
        }
    except Exception as e:
        logger.error(f"Google Drive auth failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/auth/status")
async def get_auth_status(current_user: User = Depends(get_current_user)):
    """Check Google Drive authentication status"""
    client = get_drive_client(current_user.id)

    return {
        "authenticated": client.is_authenticated(),
        "user_id": current_user.id
    }


@router.get("/files", response_model=dict[str, Any])
async def list_files(
    folder_id: Optional[str] = Query(None, description="Google Drive folder ID"),
    page_size: int = Query(50, ge=1, le=100),
    page_token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive"""
    client = get_drive_client(current_user.id)

    if not client.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google Drive. Use /auth/url endpoint first."
        )

    try:
        result = await client.list_files(
            folder_id=folder_id,
            page_size=page_size,
            page_token=page_token,
            only_supported=True
        )

        # Convert DriveFile objects to response format
        files = []
        for file in result['files']:
            files.append(GoogleDriveFileResponse(
                id=file.id,
                name=file.name,
                mime_type=file.mime_type,
                size=file.size,
                created_time=file.created_time.isoformat() if file.created_time else None,
                modified_time=file.modified_time.isoformat() if file.modified_time else None,
                web_view_link=file.web_view_link,
                is_folder=file.is_folder,
                is_supported=file.mime_type in GoogleDriveClient.SUPPORTED_MIME_TYPES
            ))

        return {
            "files": files,
            "next_page_token": result.get('next_page_token'),
            "total": len(files)
        }
    except Exception as e:
        logger.error(f"Failed to list Google Drive files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/search", response_model=list[GoogleDriveFileResponse])
async def search_files(
    query: str = Query(..., description="Search query"),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Search files in Google Drive"""
    client = get_drive_client(current_user.id)

    if not client.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google Drive. Use /auth/url endpoint first."
        )

    try:
        files = await client.search_files(query=query, page_size=page_size)

        # Convert to response format
        return [
            GoogleDriveFileResponse(
                id=file.id,
                name=file.name,
                mime_type=file.mime_type,
                size=file.size,
                created_time=file.created_time.isoformat() if file.created_time else None,
                modified_time=file.modified_time.isoformat() if file.modified_time else None,
                web_view_link=file.web_view_link,
                is_folder=file.is_folder,
                is_supported=file.mime_type in GoogleDriveClient.SUPPORTED_MIME_TYPES
            )
            for file in files
        ]
    except Exception as e:
        logger.error(f"Failed to search Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/ingest")
async def ingest_drive_files(
    background_tasks: BackgroundTasks,
    request: GoogleDriveIngestionRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Ingest files from Google Drive into Second Brain"""
    client = get_drive_client(current_user.id)

    if not client.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google Drive. Use /auth/url endpoint first."
        )

    # Process in background
    background_tasks.add_task(
        process_drive_ingestion,
        client=client,
        file_ids=request.file_ids,
        user_id=current_user.id,
        tags=request.tags,
        metadata=request.metadata,
        db=db
    )

    return {
        "success": True,
        "message": f"Queued {len(request.file_ids)} files for ingestion",
        "file_count": len(request.file_ids)
    }


@router.post("/monitor/folder")
async def monitor_folder(
    background_tasks: BackgroundTasks,
    request: FolderMonitorRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """Monitor a Google Drive folder for new files"""
    client = get_drive_client(current_user.id)

    if not client.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Google Drive. Use /auth/url endpoint first."
        )

    # Start monitoring in background
    background_tasks.add_task(
        monitor_drive_folder,
        client=client,
        folder_id=request.folder_id,
        user_id=current_user.id,
        check_interval=request.check_interval,
        auto_ingest=request.auto_ingest,
        tags=request.tags,
        db=db
    )

    return {
        "success": True,
        "message": f"Started monitoring folder {request.folder_id}",
        "check_interval": request.check_interval,
        "auto_ingest": request.auto_ingest
    }


async def process_drive_ingestion(
    client: GoogleDriveClient,
    file_ids: list[str],
    user_id: str,
    tags: list[str],
    metadata: dict[str, Any],
    db
):
    """Process Google Drive file ingestion"""
    # Initialize services
    memory_repository = MemoryRepository(db)
    service_factory = ServiceFactory(db)
    ingestion_engine = IngestionEngine(
        memory_repository=memory_repository,
        extraction_pipeline=service_factory.core_extraction_pipeline
    )

    results = []

    for file_id in file_ids:
        try:
            # Get file info
            file_info = await client.get_file_info(file_id)

            # Skip folders
            if file_info.is_folder:
                continue

            # Download file
            logger.info(f"Downloading {file_info.name} from Google Drive")
            file_stream = await client.download_file(file_id, file_info.name)

            # Get appropriate filename for export
            filename = client.get_export_filename(file_info)

            # Ingest file
            result = await ingestion_engine.ingest_file(
                file=file_stream,
                filename=filename,
                user_id=user_id,
                tags=tags,
                metadata={
                    **metadata,
                    "source": "google_drive",
                    "source_id": file_id,
                    "drive_metadata": {
                        "original_name": file_info.name,
                        "mime_type": file_info.mime_type,
                        "created_time": file_info.created_time.isoformat() if file_info.created_time else None,
                        "modified_time": file_info.modified_time.isoformat() if file_info.modified_time else None,
                        "web_view_link": file_info.web_view_link
                    }
                }
            )

            results.append({
                "file_name": file_info.name,
                "success": result.success,
                "memories_created": len(result.memories_created) if result.success else 0
            })

        except Exception as e:
            logger.error(f"Failed to ingest file {file_id}: {str(e)}")
            results.append({
                "file_id": file_id,
                "success": False,
                "error": str(e)
            })

    logger.info(f"Google Drive ingestion complete: {len(results)} files processed")
    return results


async def monitor_drive_folder(
    client: GoogleDriveClient,
    folder_id: str,
    user_id: str,
    check_interval: int,
    auto_ingest: bool,
    tags: list[str],
    db
):
    """Monitor Google Drive folder for changes"""

    async def process_new_files(files: list[DriveFile]):
        """Process new/modified files"""
        if not auto_ingest:
            logger.info(f"Detected {len(files)} new/modified files (auto-ingest disabled)")
            return

        file_ids = [f.id for f in files]
        logger.info(f"Auto-ingesting {len(file_ids)} new/modified files")

        await process_drive_ingestion(
            client=client,
            file_ids=file_ids,
            user_id=user_id,
            tags=tags,
            metadata={"auto_ingested": True, "folder_id": folder_id},
            db=db
        )

    # Start monitoring
    await client.monitor_folder(
        folder_id=folder_id,
        callback=process_new_files,
        check_interval=check_interval
    )
