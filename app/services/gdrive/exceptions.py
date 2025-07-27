"""
Google Drive integration specific exceptions.
Following Second Brain's Clean Architecture exception patterns.
"""

from app.core.exceptions import ServiceError


class GoogleDriveError(ServiceError):
    """Base exception for Google Drive integration errors"""
    pass


class GoogleAuthError(GoogleDriveError):
    """Google OAuth authentication related errors"""
    pass


class GoogleTokenError(GoogleAuthError):
    """Google token management errors (refresh, encryption, etc.)"""
    pass


class GoogleQuotaError(GoogleDriveError):
    """Google API quota and rate limiting errors"""
    pass


class GoogleAPIError(GoogleDriveError):
    """Google API call errors"""
    
    def __init__(self, message: str, status_code: int = None, error_details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details or {}


class GoogleWebhookError(GoogleDriveError):
    """Google Drive webhook related errors"""
    pass


class GoogleFileError(GoogleDriveError):
    """Google Drive file operation errors"""
    pass


class GoogleStreamingError(GoogleDriveError):
    """File streaming related errors"""
    pass