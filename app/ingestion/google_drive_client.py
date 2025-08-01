import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import Path

from app.utils.logging_config import get_logger

"""
Google Drive integration for Second Brain
"""

import io
import pickle
from pathlib import Path

# Optional Google Drive dependencies
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    # Create stub classes
    Request = None
    Credentials = None
    Flow = None

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DriveFile:
    """Google Drive file metadata"""

    id: str
    name: str
    mime_type: str
    size: int | None = None
    created_time: datetime | None = None
    modified_time: datetime | None = None
    parents: list[str] = None
    web_view_link: str | None = None
    download_link: str | None = None
    is_folder: bool = False


class GoogleDriveClient:
    """Client for interacting with Google Drive API"""

    # OAuth 2.0 configuration
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    CLIENT_CONFIG = {
        "installed": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # Supported file types for ingestion
    SUPPORTED_MIME_TYPES = {
        # Documents
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/markdown",
        "text/html",
        # Google Docs (will be exported)
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        # Spreadsheets
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
    }

    # Export formats for Google Docs
    EXPORT_FORMATS = {
        "application/vnd.google-apps.document": {
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "extension": ".docx",
        },
        "application/vnd.google-apps.spreadsheet": {
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "extension": ".xlsx",
        },
        "application/vnd.google-apps.presentation": {
            "mime_type": "application/pdf",
            "extension": ".pdf",
        },
    }

    def __init__(self, credentials_path: Path | None = None):
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ImportError(
                "Google Drive dependencies not available. Install with: pip install google-auth google-auth-oauthlib google-api-python-client"
            )

        self.credentials_path = credentials_path or Path("credentials/google_drive_creds.pickle")
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        self.creds: Credentials | None = None
        self.service = None

    def get_auth_url(self) -> str:
        """Get OAuth authorization URL"""
        if not self.CLIENT_CONFIG["installed"]["client_id"]:
            raise ValueError(
                "Google Client ID not configured. Set GOOGLE_CLIENT_ID environment variable."
            )

        flow = Flow.from_client_config(
            self.CLIENT_CONFIG, scopes=self.SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )

        auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true")

        return auth_url

    async def authenticate(self, auth_code: str | None = None) -> bool:
        """
        Authenticate with Google Drive

        Args:
            auth_code: Authorization code from OAuth flow

        Returns:
            True if authentication successful
        """
        # Try to load existing credentials
        if self.credentials_path.exists():
            with open(self.credentials_path, "rb") as token:
                self.creds = pickle.load(token)

        # If no valid credentials, need auth code
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired token
                self.creds.refresh(Request())
            elif auth_code:
                # Exchange auth code for credentials
                flow = Flow.from_client_config(
                    self.CLIENT_CONFIG, scopes=self.SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
                )
                flow.fetch_token(code=auth_code)
                self.creds = flow.credentials
            else:
                return False

            # Save credentials
            with open(self.credentials_path, "wb") as token:
                pickle.dump(self.creds, token)

        # Build service
        self.service = build("drive", "v3", credentials=self.creds)
        return True

    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self.creds is not None and self.creds.valid

    async def list_files(
        self,
        folder_id: str | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        only_supported: bool = True,
    ) -> dict[str, Any]:
        """
        List files in Google Drive

        Args:
            folder_id: ID of folder to list (None for root)
            page_size: Number of files per page
            page_token: Token for next page
            only_supported: Only show supported file types

        Returns:
            Dictionary with files and next page token
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        # Build query
        query_parts = []

        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        else:
            query_parts.append("'root' in parents")

        if only_supported:
            mime_queries = [f"mimeType='{mime}'" for mime in self.SUPPORTED_MIME_TYPES]
            mime_queries.append("mimeType='application/vnd.google-apps.folder'")  # Include folders
            query_parts.append(f"({' or '.join(mime_queries)})")

        query_parts.append("trashed=false")
        query = " and ".join(query_parts)

        # Execute query
        results = (
            self.service.files()
            .list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink)",
            )
            .execute()
        )

        # Convert to DriveFile objects
        files = []
        for item in results.get("files", []):
            file = DriveFile(
                id=item["id"],
                name=item["name"],
                mime_type=item["mimeType"],
                size=int(item.get("size", 0)) if item.get("size") else None,
                created_time=(
                    datetime.fromisoformat(item["createdTime"].replace("Z", "+00:00"))
                    if "createdTime" in item
                    else None
                ),
                modified_time=(
                    datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00"))
                    if "modifiedTime" in item
                    else None
                ),
                parents=item.get("parents", []),
                web_view_link=item.get("webViewLink"),
                is_folder=item["mimeType"] == "application/vnd.google-apps.folder",
            )
            files.append(file)

        return {"files": files, "next_page_token": results.get("nextPageToken")}

    async def download_file(self, file_id: str, file_name: str) -> io.BytesIO:
        """
        Download a file from Google Drive

        Args:
            file_id: Google Drive file ID
            file_name: Name of the file (for determining export format)

        Returns:
            File content as a file-like object
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        # Get file metadata
        file_metadata = self.service.files().get(fileId=file_id, fields="mimeType").execute()

        mime_type = file_metadata["mimeType"]

        # Check if it's a Google Docs file that needs export
        if mime_type in self.EXPORT_FORMATS:
            export_format = self.EXPORT_FORMATS[mime_type]
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_format["mime_type"]
            )
        else:
            # Regular file download
            request = self.service.files().get_media(fileId=file_id)

        # Download file
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.info(f"Download {int(status.progress() * 100)}% complete.")

        file_content.seek(0)
        return file_content

    async def get_file_info(self, file_id: str) -> DriveFile:
        """Get detailed information about a file"""
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        file_metadata = (
            self.service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink",
            )
            .execute()
        )

        return DriveFile(
            id=file_metadata["id"],
            name=file_metadata["name"],
            mime_type=file_metadata["mimeType"],
            size=int(file_metadata.get("size", 0)) if file_metadata.get("size") else None,
            created_time=(
                datetime.fromisoformat(file_metadata["createdTime"].replace("Z", "+00:00"))
                if "createdTime" in file_metadata
                else None
            ),
            modified_time=(
                datetime.fromisoformat(file_metadata["modifiedTime"].replace("Z", "+00:00"))
                if "modifiedTime" in file_metadata
                else None
            ),
            parents=file_metadata.get("parents", []),
            web_view_link=file_metadata.get("webViewLink"),
            is_folder=file_metadata["mimeType"] == "application/vnd.google-apps.folder",
        )

    async def search_files(self, query: str, page_size: int = 50) -> list[DriveFile]:
        """
        Search for files in Google Drive

        Args:
            query: Search query
            page_size: Number of results

        Returns:
            List of matching files
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        # Build search query
        search_parts = [f"fullText contains '{query}'", "trashed=false"]

        # Add supported mime types
        mime_queries = [f"mimeType='{mime}'" for mime in self.SUPPORTED_MIME_TYPES]
        search_parts.append(f"({' or '.join(mime_queries)})")

        full_query = " and ".join(search_parts)

        # Execute search
        results = (
            self.service.files()
            .list(
                q=full_query,
                pageSize=page_size,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink)",
            )
            .execute()
        )

        # Convert to DriveFile objects
        files = []
        for item in results.get("files", []):
            file = DriveFile(
                id=item["id"],
                name=item["name"],
                mime_type=item["mimeType"],
                size=int(item.get("size", 0)) if item.get("size") else None,
                created_time=(
                    datetime.fromisoformat(item["createdTime"].replace("Z", "+00:00"))
                    if "createdTime" in item
                    else None
                ),
                modified_time=(
                    datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00"))
                    if "modifiedTime" in item
                    else None
                ),
                parents=item.get("parents", []),
                web_view_link=item.get("webViewLink"),
            )
            files.append(file)

        return files

    async def monitor_folder(
        self, folder_id: str, callback: callable, check_interval: int = 300  # 5 minutes
    ):
        """
        Monitor a folder for changes

        Args:
            folder_id: Google Drive folder ID
            callback: Async function to call when changes detected
            check_interval: Seconds between checks
        """
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        last_modified = {}

        while True:
            try:
                # List files in folder
                result = await self.list_files(folder_id=folder_id, only_supported=True)
                files = result["files"]

                # Check for changes
                current_files = {f.id: f for f in files if not f.is_folder}

                # New files
                new_files = []
                for file_id, file in current_files.items():
                    if file_id not in last_modified:
                        new_files.append(file)
                    elif file.modified_time > last_modified[file_id]:
                        new_files.append(file)

                # Process new/modified files
                if new_files:
                    logger.info(f"Detected {len(new_files)} new/modified files")
                    await callback(new_files)

                # Update last modified times
                for file_id, file in current_files.items():
                    last_modified[file_id] = file.modified_time

                # Remove deleted files
                deleted_ids = set(last_modified.keys()) - set(current_files.keys())
                for file_id in deleted_ids:
                    del last_modified[file_id]

            except Exception as e:
                logger.error(f"Error monitoring folder: {e}")

            # Wait before next check
            await asyncio.sleep(check_interval)

    def get_export_filename(self, drive_file: DriveFile) -> str:
        """Get appropriate filename for exported Google Docs"""
        if drive_file.mime_type in self.EXPORT_FORMATS:
            export_format = self.EXPORT_FORMATS[drive_file.mime_type]
            # Remove existing extension and add export extension
            base_name = Path(drive_file.name).stem
            return base_name + export_format["extension"]
        return drive_file.name
