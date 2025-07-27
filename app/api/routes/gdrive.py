"""
Google Drive integration API routes.
Enterprise OAuth flow and Drive connectivity endpoints.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_google_auth_service_dep
from app.services.gdrive.auth_service import GoogleAuthService
from app.services.gdrive.exceptions import GoogleAuthError, GoogleTokenError
from app.core.security import get_api_key_user
from app.utils.logging_config import get_logger

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