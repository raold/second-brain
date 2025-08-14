"""
Google Drive integration API routes.
Enterprise OAuth flow and Drive connectivity endpoints.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_google_auth_service_dep
from app.services.gdrive.auth_service import GoogleAuthService
from app.services.gdrive.exceptions import GoogleAuthError, GoogleTokenError
# Simple user ID for now - in production, get from auth
def get_api_key_user():
    return "default_user"
from app.utils.logging_config import get_logger
from app.services.task_queue import TaskQueue, TaskType, TaskPriority

logger = get_logger(__name__)

router = APIRouter(prefix="/gdrive", tags=["Google Drive"])


# Request/Response Models
class OAuthInitiateRequest(BaseModel):
    """Request to initiate OAuth flow"""
    redirect_after_auth: Optional[str] = Field(
        default="/dashboard", 
        description="URL to redirect to after successful authentication"
    )


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth URL"""
    auth_url: str = Field(description="Google OAuth authorization URL")
    state: str = Field(description="State parameter for verification")
    expires_in: int = Field(default=600, description="URL expires in seconds")


class DriveConnectionStatus(BaseModel):
    """Drive connection status"""
    connected: bool = Field(description="Whether user has active Drive connection")
    user_email: Optional[str] = Field(description="Connected Google account email")
    last_checked: Optional[str] = Field(description="Last connectivity check timestamp")
    storage_quota: Optional[Dict[str, Any]] = Field(description="Google Drive storage info")
    error: Optional[str] = Field(description="Error message if connection failed")
    requires_reauth: bool = Field(default=False, description="Whether re-authentication is needed")


class OAuthCallbackResponse(BaseModel):
    """OAuth callback success response"""
    success: bool = Field(description="Whether OAuth flow completed successfully")
    user_email: str = Field(description="Connected Google account email")
    drive_access: bool = Field(description="Whether Drive access was granted")
    redirect_url: str = Field(description="URL to redirect to")


class FileSyncRequest(BaseModel):
    """Request to sync a specific file"""
    file_id: str = Field(description="Google Drive file ID")
    processing_options: Optional[Dict[str, Any]] = Field(
        default={},
        description="Processing options (extract_text, generate_embeddings, etc.)"
    )


class FolderSyncRequest(BaseModel):
    """Request to sync a folder"""
    folder_id: str = Field(description="Google Drive folder ID")
    recursive: bool = Field(default=False, description="Process subfolders recursively")
    file_types: Optional[List[str]] = Field(
        default=None,
        description="MIME types to process (null for all supported types)"
    )
    processing_options: Optional[Dict[str, Any]] = Field(
        default={},
        description="Processing options for files"
    )


class SyncResponse(BaseModel):
    """Response for sync operations"""
    task_id: str = Field(description="Background task ID")
    status: str = Field(description="Task status")
    message: str = Field(description="Status message")


class WebhookSubscribeRequest(BaseModel):
    """Request to subscribe to Drive change notifications"""
    resource_id: str = Field(description="Resource to watch (file or folder ID)")
    notification_url: str = Field(description="HTTPS URL for notifications")
    expiration_hours: int = Field(
        default=168,  # 7 days
        description="Hours until webhook expires (max 168)"
    )


@router.post("/connect", response_model=OAuthInitiateResponse)
async def initiate_google_oauth(
    request: OAuthInitiateRequest,
    user_id: str = Depends(get_api_key_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> OAuthInitiateResponse:
    """
    Initiate Google OAuth flow for Drive access.
    
    This endpoint generates a Google OAuth URL that the user can visit to
    grant Second Brain read-only access to their Google Drive.
    """
    try:
        logger.info("Initiating Google OAuth flow", extra={
            "user_id": user_id,
            "redirect_after_auth": request.redirect_after_auth
        })
        
        # Generate OAuth URL with state containing user_id
        oauth_data = google_auth.generate_oauth_url(user_id)
        
        # Store redirect preference in state (for callback handling)
        # Note: In production, store this in Redis with state as key
        
        logger.info("Google OAuth URL generated successfully", extra={
            "user_id": user_id,
            "state": oauth_data["state"][:20] + "...",
            "auth_url_length": len(oauth_data["auth_url"])
        })
        
        return OAuthInitiateResponse(
            auth_url=oauth_data["auth_url"],
            state=oauth_data["state"],
            expires_in=600  # Google OAuth URLs expire in 10 minutes
        )
        
    except GoogleAuthError as e:
        logger.error(f"Google OAuth initiation failed: {e}", extra={
            "user_id": user_id,
            "error_type": "GoogleAuthError"
        })
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error during OAuth initiation: {e}", extra={
            "user_id": user_id,
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@router.get("/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for verification"),
    error: Optional[str] = Query(None, description="Error from Google OAuth"),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> RedirectResponse:
    """
    Handle Google OAuth callback.
    
    This endpoint receives the authorization code from Google and exchanges it
    for access and refresh tokens. The user is then redirected to the dashboard.
    """
    try:
        # Handle OAuth errors
        if error:
            logger.warning(f"Google OAuth error: {error}", extra={
                "oauth_error": error,
                "state": state[:20] + "..." if state else None
            })
            return RedirectResponse(
                url=f"/dashboard?error=oauth_denied&details={error}",
                status_code=302
            )
        
        # Extract user_id from state
        if not state or ':' not in state:
            logger.error("Invalid state parameter in OAuth callback", extra={
                "state": state[:50] if state else None
            })
            return RedirectResponse(
                url="/dashboard?error=invalid_state",
                status_code=302
            )
        
        user_id = state.split(':', 1)[0]
        
        logger.info("Processing Google OAuth callback", extra={
            "user_id": user_id,
            "has_code": bool(code),
            "state_length": len(state) if state else 0
        })
        
        # Exchange code for tokens
        result = await google_auth.handle_oauth_callback(code, state, user_id)
        
        logger.info("Google OAuth callback processed successfully", extra={
            "user_id": user_id,
            "user_email": result["user_info"].get("email"),
            "drive_access": result["drive_access"]
        })
        
        # Redirect to dashboard with success message
        return RedirectResponse(
            url=f"/dashboard?connected=true&email={result['user_info'].get('email', '')}",
            status_code=302
        )
        
    except GoogleAuthError as e:
        logger.error(f"Google OAuth callback failed: {e}", extra={
            "error_type": "GoogleAuthError",
            "state": state[:20] + "..." if state else None
        })
        return RedirectResponse(
            url=f"/dashboard?error=auth_failed&details={str(e)}",
            status_code=302
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}", extra={
            "error_type": type(e).__name__,
            "state": state[:20] + "..." if state else None
        })
        return RedirectResponse(
            url="/dashboard?error=callback_failed",
            status_code=302
        )


@router.get("/status", response_model=DriveConnectionStatus)
async def get_drive_connection_status(
    user_id: str = Depends(get_api_key_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> DriveConnectionStatus:
    """
    Check Google Drive connection status for the user.
    
    Returns current connection status, user info, and any errors.
    """
    try:
        logger.debug("Checking Google Drive connection status", extra={
            "user_id": user_id
        })
        
        # Check connectivity
        status = await google_auth.check_drive_connectivity(user_id)
        
        logger.info("Drive connection status checked", extra={
            "user_id": user_id,
            "connected": status.get("connected", False),
            "user_email": status.get("user_email", "unknown")
        })
        
        return DriveConnectionStatus(
            connected=status.get("connected", False),
            user_email=status.get("user_email"),
            last_checked=status.get("last_checked"),
            storage_quota=status.get("storage_quota"),
            error=status.get("error"),
            requires_reauth=status.get("requires_reauth", False)
        )
        
    except Exception as e:
        logger.error(f"Failed to check Drive connection status: {e}", extra={
            "user_id": user_id,
            "error_type": type(e).__name__
        })
        
        return DriveConnectionStatus(
            connected=False,
            error=f"Status check failed: {str(e)}",
            requires_reauth=False
        )


@router.delete("/disconnect")
async def disconnect_google_drive(
    user_id: str = Depends(get_api_key_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> Dict[str, Any]:
    """
    Disconnect Google Drive access for the user.
    
    Revokes tokens and removes stored credentials.
    """
    try:
        logger.info("Disconnecting Google Drive access", extra={
            "user_id": user_id
        })
        
        # Revoke access
        success = await google_auth.revoke_user_access(user_id)
        
        if success:
            logger.info("Google Drive access disconnected successfully", extra={
                "user_id": user_id
            })
            return {
                "success": True,
                "message": "Google Drive access has been revoked",
                "disconnected_at": logger.timestamp()
            }
        else:
            logger.warning("Failed to revoke Google Drive access", extra={
                "user_id": user_id
            })
            return {
                "success": False,
                "message": "Failed to revoke access - may already be disconnected",
                "error": "Revocation failed"
            }
            
    except Exception as e:
        logger.error(f"Error disconnecting Google Drive: {e}", extra={
            "user_id": user_id,
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to disconnect Google Drive: {str(e)}"
        )


# ========== File Sync Endpoints ==========

@router.post("/sync/file", response_model=SyncResponse)
async def sync_drive_file(
    request: FileSyncRequest,
    user_id: str = Depends(get_api_key_user)
) -> SyncResponse:
    """
    Queue a Google Drive file for background processing.
    
    The file will be streamed, processed, and converted to memories
    without storing the file locally.
    """
    try:
        # Initialize task queue
        task_queue = TaskQueue()
        await task_queue.initialize()
        
        # Create dedupe key based on file ID and user
        dedupe_key = f"file_sync:{user_id}:{request.file_id}"
        
        # Enqueue the task
        task_id = await task_queue.enqueue(
            task_type=TaskType.DRIVE_FILE_SYNC,
            payload={
                "file_id": request.file_id,
                "processing_options": request.processing_options or {}
            },
            user_id=user_id,
            priority=TaskPriority.NORMAL,
            dedupe_key=dedupe_key
        )
        
        logger.info("File sync task queued", extra={
            "task_id": task_id,
            "file_id": request.file_id,
            "user_id": user_id
        })
        
        return SyncResponse(
            task_id=task_id,
            status="queued",
            message=f"File sync task queued for processing"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue file sync: {e}", extra={
            "file_id": request.file_id,
            "user_id": user_id
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/folder", response_model=SyncResponse)
async def sync_drive_folder(
    request: FolderSyncRequest,
    user_id: str = Depends(get_api_key_user)
) -> SyncResponse:
    """
    Queue a Google Drive folder for background processing.
    
    All supported files in the folder will be processed.
    Use recursive=true to include subfolders.
    """
    try:
        # Initialize task queue
        task_queue = TaskQueue()
        await task_queue.initialize()
        
        # Create dedupe key
        dedupe_key = f"folder_sync:{user_id}:{request.folder_id}:{request.recursive}"
        
        # Enqueue the task
        task_id = await task_queue.enqueue(
            task_type=TaskType.DRIVE_FOLDER_SYNC,
            payload={
                "folder_id": request.folder_id,
                "recursive": request.recursive,
                "file_types": request.file_types,
                "processing_options": request.processing_options or {}
            },
            user_id=user_id,
            priority=TaskPriority.NORMAL,
            dedupe_key=dedupe_key
        )
        
        logger.info("Folder sync task queued", extra={
            "task_id": task_id,
            "folder_id": request.folder_id,
            "recursive": request.recursive,
            "user_id": user_id
        })
        
        return SyncResponse(
            task_id=task_id,
            status="queued",
            message=f"Folder sync task queued for processing"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue folder sync: {e}", extra={
            "folder_id": request.folder_id,
            "user_id": user_id
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status/{task_id}")
async def get_sync_status(
    task_id: str,
    user_id: str = Depends(get_api_key_user)
) -> Dict[str, Any]:
    """
    Get the status of a sync task.
    
    Returns task status, progress, and results when complete.
    """
    try:
        # Initialize task queue
        task_queue = TaskQueue()
        await task_queue.initialize()
        
        # Get task status
        task_status = await task_queue.get_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Verify task belongs to user
        if task_status.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}", extra={
            "task_id": task_id,
            "user_id": user_id
        })
        raise HTTPException(status_code=500, detail=str(e))


# ========== Webhook Endpoints ==========

@router.post("/webhooks/subscribe", response_model=Dict[str, Any])
async def subscribe_to_changes(
    request: WebhookSubscribeRequest,
    user_id: str = Depends(get_api_key_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> Dict[str, Any]:
    """
    Subscribe to real-time change notifications for a Drive resource.
    
    Google will send notifications to the specified URL when changes occur.
    """
    try:
        from datetime import datetime, timedelta
        from app.services.gdrive.streaming_service import GoogleDriveStreamingService
        
        # Get user credentials
        credentials = await google_auth.get_user_credentials(user_id)
        if not credentials:
            raise HTTPException(status_code=401, detail="No Google Drive credentials found")
        
        # Initialize streaming service
        streaming_service = GoogleDriveStreamingService()
        await streaming_service.initialize(credentials)
        
        # Calculate expiration
        expiration = datetime.utcnow() + timedelta(hours=request.expiration_hours)
        
        # Set up webhook
        webhook_result = await streaming_service.setup_webhook(
            resource_id=request.resource_id,
            notification_url=request.notification_url,
            expiration=expiration
        )
        
        logger.info("Webhook subscription created", extra={
            "user_id": user_id,
            "resource_id": request.resource_id,
            "webhook_id": webhook_result.get("id")
        })
        
        return {
            "success": True,
            "webhook_id": webhook_result.get("id"),
            "resource_id": request.resource_id,
            "expiration": expiration.isoformat(),
            "notification_url": request.notification_url
        }
        
    except Exception as e:
        logger.error(f"Failed to create webhook subscription: {e}", extra={
            "user_id": user_id,
            "resource_id": request.resource_id
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/notify")
async def handle_webhook_notification(
    request: Request
) -> Dict[str, Any]:
    """
    Handle incoming webhook notifications from Google Drive.
    
    This endpoint receives real-time notifications when subscribed
    resources change.
    """
    try:
        # Get notification headers
        headers = dict(request.headers)
        body = await request.body()
        
        # Extract key information
        resource_id = headers.get("x-goog-resource-id")
        resource_state = headers.get("x-goog-resource-state")
        change_type = headers.get("x-goog-changed", "")
        
        logger.info("Webhook notification received", extra={
            "resource_id": resource_id,
            "resource_state": resource_state,
            "changes": change_type
        })
        
        # Initialize task queue
        task_queue = TaskQueue()
        await task_queue.initialize()
        
        # Queue webhook processing task
        task_id = await task_queue.enqueue(
            task_type=TaskType.DRIVE_WEBHOOK,
            payload={
                "resource_id": resource_id,
                "resource_state": resource_state,
                "changes": change_type.split(",") if change_type else [],
                "headers": headers,
                "timestamp": datetime.utcnow().isoformat()
            },
            priority=TaskPriority.HIGH
        )
        
        logger.info("Webhook processing task queued", extra={
            "task_id": task_id,
            "resource_id": resource_id
        })
        
        # Return 200 OK to acknowledge receipt
        return {"status": "acknowledged", "task_id": task_id}
        
    except Exception as e:
        logger.error(f"Failed to process webhook notification: {e}")
        # Still return 200 to prevent Google from retrying
        return {"status": "error", "error": str(e)}


@router.get("/test-connection")
async def test_drive_connection(
    user_id: str = Depends(get_api_key_user),
    google_auth: GoogleAuthService = Depends(get_google_auth_service_dep)
) -> Dict[str, Any]:
    """
    Test Google Drive connection by making a simple API call.
    
    This endpoint can be used to verify that credentials are working
    and the user has proper Drive access.
    """
    try:
        logger.info("Testing Google Drive connection", extra={
            "user_id": user_id
        })
        
        # Get user credentials
        credentials = await google_auth.get_user_credentials(user_id)
        
        if not credentials:
            return {
                "success": False,
                "error": "No Google credentials found",
                "requires_auth": True
            }
        
        # Test Drive API connectivity
        status = await google_auth.check_drive_connectivity(user_id)
        
        logger.info("Drive connection test completed", extra={
            "user_id": user_id,
            "success": status.get("connected", False)
        })
        
        return {
            "success": status.get("connected", False),
            "user_email": status.get("user_email"),
            "storage_info": status.get("storage_quota"),
            "test_timestamp": status.get("last_checked"),
            "error": status.get("error"),
            "requires_reauth": status.get("requires_reauth", False)
        }
        
    except GoogleTokenError as e:
        logger.error(f"Token error during connection test: {e}", extra={
            "user_id": user_id,
            "error_type": "GoogleTokenError"
        })
        return {
            "success": False,
            "error": str(e),
            "requires_reauth": True
        }
    
    except Exception as e:
        logger.error(f"Connection test failed: {e}", extra={
            "user_id": user_id,
            "error_type": type(e).__name__
        })
        return {
            "success": False,
            "error": f"Connection test failed: {str(e)}",
            "requires_reauth": False
        }