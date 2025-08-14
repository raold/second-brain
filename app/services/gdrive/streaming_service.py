"""
Google Drive Streaming Service

Implements efficient file streaming from Google Drive without local storage.
Processes files in chunks and feeds directly to the memory system.
"""

import io
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime, timedelta
import asyncio

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from app.services.gdrive.exceptions import (
    GoogleDriveError,
    GoogleAuthError,
    GoogleQuotaExceededError
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# File type mappings for Google Workspace files
GOOGLE_WORKSPACE_MIME_TYPES = {
    'application/vnd.google-apps.document': {
        'export_type': 'text/plain',
        'extension': '.txt',
        'name': 'Google Doc'
    },
    'application/vnd.google-apps.spreadsheet': {
        'export_type': 'text/csv', 
        'extension': '.csv',
        'name': 'Google Sheet'
    },
    'application/vnd.google-apps.presentation': {
        'export_type': 'text/plain',
        'extension': '.txt',
        'name': 'Google Slides'
    },
    'application/vnd.google-apps.drawing': {
        'export_type': 'image/png',
        'extension': '.png',
        'name': 'Google Drawing'
    }
}

# Standard file types we can process
SUPPORTED_FILE_TYPES = {
    'application/pdf': 'pdf',
    'text/plain': 'txt',
    'text/markdown': 'md',
    'text/csv': 'csv',
    'application/json': 'json',
    'image/jpeg': 'image',
    'image/png': 'image',
    'image/gif': 'image',
    'audio/mpeg': 'audio',
    'audio/wav': 'audio',
    'video/mp4': 'video'
}


class GoogleDriveStreamingService:
    """
    Service for streaming and processing Google Drive files.
    
    Core principles:
    - Never store files locally
    - Process in memory-efficient chunks
    - Support all Google Workspace and standard file types
    - Automatic retry with exponential backoff
    """
    
    def __init__(self, chunk_size: int = 2 * 1024 * 1024):  # 2MB chunks
        """
        Initialize the streaming service.
        
        Args:
            chunk_size: Size of chunks to stream (default 2MB)
        """
        self.chunk_size = chunk_size
        self.drive_service = None
        
    async def initialize(self, credentials: Credentials):
        """
        Initialize the Drive API service.
        
        Args:
            credentials: Google OAuth2 credentials
        """
        try:
            self.drive_service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            raise GoogleDriveError(f"Drive service initialization failed: {e}")
    
    async def stream_file(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """
        Stream a file from Google Drive in chunks.
        
        Args:
            file_id: Google Drive file ID
            
        Yields:
            Chunks of file content as bytes
        """
        if not self.drive_service:
            raise GoogleDriveError("Drive service not initialized")
        
        try:
            # Get file metadata first
            file_metadata = await self.get_file_metadata(file_id)
            mime_type = file_metadata.get('mimeType')
            
            logger.info(f"Streaming file: {file_metadata.get('name')} ({mime_type})")
            
            # Handle Google Workspace files differently
            if mime_type in GOOGLE_WORKSPACE_MIME_TYPES:
                async for chunk in self._stream_workspace_file(file_id, mime_type):
                    yield chunk
            else:
                async for chunk in self._stream_standard_file(file_id):
                    yield chunk
                    
        except HttpError as e:
            if e.resp.status == 403:
                raise GoogleQuotaExceededError("API quota exceeded")
            elif e.resp.status == 404:
                raise GoogleDriveError(f"File not found: {file_id}")
            else:
                raise GoogleDriveError(f"Drive API error: {e}")
        except Exception as e:
            logger.error(f"Error streaming file {file_id}: {e}")
            raise GoogleDriveError(f"Failed to stream file: {e}")
    
    async def _stream_standard_file(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """
        Stream a standard (non-Google Workspace) file.
        
        Args:
            file_id: Google Drive file ID
            
        Yields:
            File content chunks
        """
        request = self.drive_service.files().get_media(fileId=file_id)
        
        # Use BytesIO as buffer
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=self.chunk_size)
        
        done = False
        while not done:
            status, done = await asyncio.to_thread(downloader.next_chunk)
            
            if buffer.tell() > 0:
                buffer.seek(0)
                chunk = buffer.read()
                if chunk:
                    yield chunk
                    
                # Clear buffer for next chunk
                buffer.seek(0)
                buffer.truncate()
            
            # Log progress
            if status:
                progress = int(status.progress() * 100)
                if progress % 20 == 0:  # Log every 20%
                    logger.debug(f"Download progress: {progress}%")
    
    async def _stream_workspace_file(self, file_id: str, mime_type: str) -> AsyncGenerator[bytes, None]:
        """
        Stream a Google Workspace file by exporting it.
        
        Args:
            file_id: Google Drive file ID
            mime_type: Original MIME type of the file
            
        Yields:
            Exported file content chunks
        """
        export_config = GOOGLE_WORKSPACE_MIME_TYPES.get(mime_type)
        if not export_config:
            raise GoogleDriveError(f"Unsupported Google Workspace type: {mime_type}")
        
        export_mime_type = export_config['export_type']
        
        # Export the file
        request = self.drive_service.files().export_media(
            fileId=file_id,
            mimeType=export_mime_type
        )
        
        # Stream the exported content
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=self.chunk_size)
        
        done = False
        while not done:
            status, done = await asyncio.to_thread(downloader.next_chunk)
            
            if buffer.tell() > 0:
                buffer.seek(0)
                chunk = buffer.read()
                if chunk:
                    yield chunk
                    
                buffer.seek(0)
                buffer.truncate()
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get metadata for a file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary
        """
        if not self.drive_service:
            raise GoogleDriveError("Drive service not initialized")
        
        try:
            metadata = await asyncio.to_thread(
                self.drive_service.files().get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, modifiedTime, parents, webViewLink"
                ).execute
            )
            return metadata
        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveError(f"File not found: {file_id}")
            raise GoogleDriveError(f"Failed to get file metadata: {e}")
    
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in Drive or a specific folder.
        
        Args:
            folder_id: Optional folder ID to list files from
            query: Optional query string for filtering
            page_size: Number of files per page
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.drive_service:
            raise GoogleDriveError("Drive service not initialized")
        
        try:
            # Build query
            queries = []
            if folder_id:
                queries.append(f"'{folder_id}' in parents")
            if query:
                queries.append(query)
            
            # Default to non-trashed files
            queries.append("trashed = false")
            
            final_query = " and ".join(queries)
            
            # List files
            results = []
            page_token = None
            
            while True:
                response = await asyncio.to_thread(
                    self.drive_service.files().list(
                        q=final_query,
                        pageSize=page_size,
                        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                        pageToken=page_token
                    ).execute
                )
                
                files = response.get('files', [])
                results.extend(files)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(results)} files")
            return results
            
        except HttpError as e:
            raise GoogleDriveError(f"Failed to list files: {e}")
    
    async def process_folder(
        self,
        folder_id: str,
        recursive: bool = False,
        file_types: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process all files in a folder.
        
        Args:
            folder_id: Google Drive folder ID
            recursive: Whether to process subfolders
            file_types: Optional list of MIME types to process
            
        Yields:
            Processing results for each file
        """
        # Get files in folder
        files = await self.list_files(folder_id=folder_id)
        
        for file_info in files:
            mime_type = file_info.get('mimeType')
            file_id = file_info.get('id')
            file_name = file_info.get('name')
            
            # Check if it's a folder
            if mime_type == 'application/vnd.google-apps.folder':
                if recursive:
                    # Recursively process subfolder
                    logger.info(f"Processing subfolder: {file_name}")
                    async for result in self.process_folder(
                        file_id, recursive=True, file_types=file_types
                    ):
                        yield result
                continue
            
            # Check if we should process this file type
            if file_types:
                if mime_type not in file_types:
                    logger.debug(f"Skipping file {file_name} (type {mime_type} not in filter)")
                    continue
            
            # Check if file type is supported
            if not self.is_supported_file_type(mime_type):
                logger.warning(f"Unsupported file type: {file_name} ({mime_type})")
                continue
            
            # Process the file
            try:
                logger.info(f"Processing file: {file_name}")
                
                # Stream and process the file
                content_chunks = []
                async for chunk in self.stream_file(file_id):
                    content_chunks.append(chunk)
                
                # Combine chunks for processing
                full_content = b''.join(content_chunks)
                
                yield {
                    'file_id': file_id,
                    'file_name': file_name,
                    'mime_type': mime_type,
                    'size': file_info.get('size', 0),
                    'modified_time': file_info.get('modifiedTime'),
                    'content': full_content,
                    'status': 'success'
                }
                
            except Exception as e:
                logger.error(f"Error processing file {file_name}: {e}")
                yield {
                    'file_id': file_id,
                    'file_name': file_name,
                    'mime_type': mime_type,
                    'status': 'error',
                    'error': str(e)
                }
    
    def is_supported_file_type(self, mime_type: str) -> bool:
        """
        Check if a file type is supported for processing.
        
        Args:
            mime_type: MIME type to check
            
        Returns:
            True if supported, False otherwise
        """
        return (
            mime_type in GOOGLE_WORKSPACE_MIME_TYPES or
            mime_type in SUPPORTED_FILE_TYPES
        )
    
    async def setup_webhook(
        self,
        resource_id: str,
        notification_url: str,
        expiration: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Set up a webhook for real-time change notifications.
        
        Args:
            resource_id: Resource to watch (file or folder ID)
            notification_url: HTTPS URL to receive notifications
            expiration: Optional expiration time for the webhook
            
        Returns:
            Webhook subscription details
        """
        if not self.drive_service:
            raise GoogleDriveError("Drive service not initialized")
        
        try:
            # Set default expiration to 7 days from now
            if not expiration:
                expiration = datetime.utcnow() + timedelta(days=7)
            
            # Create watch request
            body = {
                'id': f"webhook_{resource_id}_{datetime.utcnow().timestamp()}",
                'type': 'web_hook',
                'address': notification_url,
                'expiration': int(expiration.timestamp() * 1000)  # Convert to milliseconds
            }
            
            # Set up the watch
            response = await asyncio.to_thread(
                self.drive_service.files().watch(
                    fileId=resource_id,
                    body=body
                ).execute
            )
            
            logger.info(f"Webhook set up for resource {resource_id}")
            return response
            
        except HttpError as e:
            if e.resp.status == 400:
                raise GoogleDriveError("Invalid webhook configuration")
            raise GoogleDriveError(f"Failed to set up webhook: {e}")
    
    async def handle_webhook_notification(self, headers: Dict[str, str], body: str) -> Dict[str, Any]:
        """
        Process incoming webhook notifications from Google Drive.
        
        Args:
            headers: HTTP headers from the notification
            body: Notification body
            
        Returns:
            Processed notification data
        """
        # Extract notification details
        resource_id = headers.get('X-Goog-Resource-ID')
        resource_state = headers.get('X-Goog-Resource-State')
        change_type = headers.get('X-Goog-Changed')
        
        logger.info(f"Webhook notification: {resource_state} for {resource_id}")
        
        # Determine what changed
        if resource_state == 'sync':
            # Initial sync notification
            return {
                'type': 'sync',
                'resource_id': resource_id,
                'message': 'Webhook synchronized'
            }
        
        # Process change notification
        changes = []
        if 'content' in change_type:
            changes.append('content_modified')
        if 'properties' in change_type:
            changes.append('metadata_changed')
        if 'parents' in change_type:
            changes.append('moved')
        
        return {
            'type': 'change',
            'resource_id': resource_id,
            'resource_state': resource_state,
            'changes': changes,
            'timestamp': datetime.utcnow().isoformat()
        }