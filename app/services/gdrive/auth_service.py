"""
Google OAuth authentication service for Drive integration.
Enterprise-grade OAuth 2.0 flow with secure token management.
Based on Gemini 2.5 Pro recommendations.
"""

import os
import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database
from app.utils.encryption import get_token_encryption
from app.utils.logging_config import get_logger
from app.models.gdrive import UserGoogleCredentials
from .exceptions import GoogleAuthError, GoogleTokenError, GoogleAPIError

logger = get_logger(__name__)


class GoogleAuthService:
    """
    Enterprise Google OAuth service for Drive integration.
    Handles secure token management and OAuth flow.
    """
    
    # Google Drive readonly scope - principle of least privilege
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'openid',
        'email',
        'profile'
    ]
    
    def __init__(self):
        """Initialize Google OAuth service"""
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET") 
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        
        if not self.client_id or not self.client_secret:
            raise GoogleAuthError(
                "Google OAuth credentials not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )
        
        self.encryption = get_token_encryption()
        logger.info("Google OAuth service initialized", extra={
            "client_id": self.client_id[:10] + "...",
            "redirect_uri": self.redirect_uri,
            "scopes": self.SCOPES
        })
    
    def generate_oauth_url(self, user_id: str, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate OAuth authorization URL for user
        
        Args:
            user_id: User identifier for state tracking
            state: Optional custom state parameter
            
        Returns:
            Dict with 'auth_url' and 'state' for verification
        """
        try:
            # Generate secure state parameter
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Combine user_id and state for verification
            full_state = f"{user_id}:{state}"
            
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=full_state,
                prompt='consent'  # Force consent to get refresh token
            )
            
            logger.info("OAuth URL generated", extra={
                "user_id": user_id,
                "state": state,
                "auth_url_length": len(auth_url)
            })
            
            return {
                "auth_url": auth_url,
                "state": full_state
            }
            
        except Exception as e:
            logger.error(f"Failed to generate OAuth URL: {e}", extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            })
            raise GoogleAuthError(f"Failed to generate OAuth URL: {e}")
    
    async def handle_oauth_callback(
        self, 
        code: str, 
        state: str, 
        expected_user_id: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:
            code: Authorization code from Google
            state: State parameter for verification
            expected_user_id: Expected user ID from state
            
        Returns:
            Dict with user info and token storage status
        """
        try:
            # Verify state parameter
            if not self._verify_state(state, expected_user_id):
                raise GoogleAuthError("Invalid state parameter - possible CSRF attack")
            
            # Exchange code for tokens
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.SCOPES,
                state=state
            )
            flow.redirect_uri = self.redirect_uri
            
            # Fetch tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info
            user_info = await self._get_user_info(credentials)
            
            # Store encrypted credentials
            await self._store_credentials(expected_user_id, credentials, user_info)
            
            logger.info("OAuth callback handled successfully", extra={
                "user_id": expected_user_id,
                "user_email": user_info.get("email"),
                "has_refresh_token": bool(credentials.refresh_token)
            })
            
            return {
                "user_id": expected_user_id,
                "user_info": user_info,
                "drive_access": True,
                "credentials_stored": True
            }
            
        except GoogleAuthError:
            raise
        except Exception as e:
            logger.error(f"OAuth callback failed: {e}", extra={
                "user_id": expected_user_id,
                "error_type": type(e).__name__
            })
            raise GoogleAuthError(f"OAuth callback failed: {e}")
    
    async def get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Get valid Google credentials for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Valid Google credentials or None if not found/invalid
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(UserGoogleCredentials).where(
                        UserGoogleCredentials.user_id == user_id
                    )
                )
                cred_record = result.scalar_one_or_none()
                
                if not cred_record:
                    logger.debug("No Google credentials found", extra={"user_id": user_id})
                    return None
                
                # Decrypt refresh token
                refresh_token = self.encryption.decrypt_token(cred_record.encrypted_refresh_token)
                
                # Create credentials object
                credentials = Credentials(
                    token=None,  # Will be refreshed
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    scopes=self.SCOPES
                )
                
                # Refresh if needed
                if not credentials.valid:
                    credentials.refresh(Request())
                    logger.debug("Credentials refreshed", extra={"user_id": user_id})
                
                return credentials
                
        except Exception as e:
            logger.error(f"Failed to get user credentials: {e}", extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            })
            raise GoogleTokenError(f"Failed to get user credentials: {e}")
    
    async def revoke_user_access(self, user_id: str) -> bool:
        """
        Revoke Google Drive access for user
        
        Args:
            user_id: User identifier
            
        Returns:
            True if revoked successfully
        """
        try:
            credentials = await self.get_user_credentials(user_id)
            if not credentials:
                logger.warning("No credentials to revoke", extra={"user_id": user_id})
                return True
            
            # Revoke with Google
            if credentials.refresh_token:
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={credentials.refresh_token}"
                import requests
                response = requests.post(revoke_url)
                
                if response.status_code == 200:
                    logger.info("Google token revoked successfully", extra={"user_id": user_id})
                else:
                    logger.warning(f"Google revoke returned {response.status_code}", extra={
                        "user_id": user_id,
                        "status_code": response.status_code
                    })
            
            # Remove from database
            async with get_db_session() as session:
                await session.execute(
                    update(UserGoogleCredentials)
                    .where(UserGoogleCredentials.user_id == user_id)
                    .values(encrypted_refresh_token="REVOKED")
                )
                await session.commit()
            
            logger.info("User Google access revoked", extra={"user_id": user_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke user access: {e}", extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            })
            return False
    
    async def check_drive_connectivity(self, user_id: str) -> Dict[str, Any]:
        """
        Check Google Drive connectivity for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with connectivity status and Drive info
        """
        try:
            credentials = await self.get_user_credentials(user_id)
            if not credentials:
                return {
                    "connected": False,
                    "error": "No credentials found"
                }
            
            # Test Drive API access
            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields='user,storageQuota').execute()
            
            return {
                "connected": True,
                "user_email": about['user']['emailAddress'],
                "storage_quota": about.get('storageQuota', {}),
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}", extra={
                "user_id": user_id,
                "status_code": e.resp.status
            })
            return {
                "connected": False,
                "error": f"Drive API error: {e.resp.status}",
                "requires_reauth": e.resp.status == 401
            }
        except Exception as e:
            logger.error(f"Drive connectivity check failed: {e}", extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            })
            return {
                "connected": False,
                "error": str(e)
            }
    
    def _verify_state(self, state: str, expected_user_id: str) -> bool:
        """Verify OAuth state parameter"""
        try:
            if ':' not in state:
                return False
            
            user_id, _ = state.split(':', 1)
            return user_id == expected_user_id
        except Exception:
            return False
    
    async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get user info from Google"""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False)
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise GoogleAuthError(f"Failed to get user info: {e}")
    
    async def _store_credentials(
        self, 
        user_id: str, 
        credentials: Credentials, 
        user_info: Dict[str, Any]
    ):
        """Store encrypted credentials in database"""
        try:
            if not credentials.refresh_token:
                raise GoogleTokenError("No refresh token received - user may have already granted access")
            
            # Encrypt refresh token
            encrypted_token = self.encryption.encrypt_token(credentials.refresh_token)
            
            # Create access token hash for cache validation
            access_token_hash = None
            if credentials.token:
                access_token_hash = hashlib.sha256(credentials.token.encode()).hexdigest()[:64]
            
            # Store in database
            async with get_db_session() as session:
                # Upsert credentials
                stmt = insert(UserGoogleCredentials).values(
                    user_id=user_id,
                    encrypted_refresh_token=encrypted_token,
                    access_token_hash=access_token_hash,
                    drive_permissions={"scopes": self.SCOPES},
                    quota_info=user_info,
                    updated_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=['user_id'],
                    set_={
                        'encrypted_refresh_token': encrypted_token,
                        'access_token_hash': access_token_hash,
                        'drive_permissions': {"scopes": self.SCOPES},
                        'quota_info': user_info,
                        'updated_at': datetime.utcnow()
                    }
                )
                
                await session.execute(stmt)
                await session.commit()
            
            logger.info("Google credentials stored successfully", extra={
                "user_id": user_id,
                "user_email": user_info.get("email")
            })
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}", extra={
                "user_id": user_id,
                "error_type": type(e).__name__
            })
            raise GoogleTokenError(f"Failed to store credentials: {e}")


def get_google_auth_service() -> GoogleAuthService:
    """Get configured Google auth service instance"""
    return GoogleAuthService()