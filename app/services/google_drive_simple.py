"""
Simple Google Drive Service for v4.2.3
Direct integration without complex enterprise patterns
"""

import os
import json
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class GoogleDriveSimple:
    """Simple Google Drive integration that actually works"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8001/api/v1/gdrive/callback")
        
        # Store tokens in memory for single user
        self.tokens = {}
        self.user_info = {}
        
    def get_auth_url(self) -> str:
        """Generate Google OAuth URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/drive.readonly email profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        async with aiohttp.ClientSession() as session:
            data = {
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            async with session.post('https://oauth2.googleapis.com/token', data=data) as resp:
                if resp.status == 200:
                    tokens = await resp.json()
                    self.tokens = tokens
                    
                    # Get user info
                    await self.get_user_info(tokens['access_token'])
                    
                    return {
                        'success': True,
                        'email': self.user_info.get('email'),
                        'tokens_stored': True
                    }
                else:
                    error = await resp.text()
                    logger.error(f"Token exchange failed: {error}")
                    return {'success': False, 'error': error}
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers) as resp:
                if resp.status == 200:
                    self.user_info = await resp.json()
                    return self.user_info
                return {}
    
    async def list_files(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files from Google Drive"""
        if not self.tokens.get('access_token'):
            return []
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {self.tokens["access_token"]}'}
            
            # Build query
            query = "mimeType != 'application/vnd.google-apps.folder'"
            if folder_id:
                query = f"'{folder_id}' in parents and {query}"
            
            params = {
                'q': query,
                'fields': 'files(id,name,mimeType,size,modifiedTime,webViewLink)',
                'pageSize': 100
            }
            
            async with session.get(
                'https://www.googleapis.com/drive/v3/files',
                headers=headers,
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('files', [])
                else:
                    logger.error(f"Failed to list files: {resp.status}")
                    return []
    
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """Get file content from Google Drive"""
        if not self.tokens.get('access_token'):
            return None
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {self.tokens["access_token"]}'}
            
            # First get file metadata
            async with session.get(
                f'https://www.googleapis.com/drive/v3/files/{file_id}',
                headers=headers,
                params={'fields': 'name,mimeType'}
            ) as resp:
                if resp.status != 200:
                    return None
                metadata = await resp.json()
            
            # Export Google Docs to plain text
            if 'google-apps' in metadata.get('mimeType', ''):
                export_mime = 'text/plain'
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}/export'
                params = {'mimeType': export_mime}
            else:
                # Download regular files
                url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
                params = {'alt': 'media'}
            
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    return content
                else:
                    logger.error(f"Failed to get file content: {resp.status}")
                    return None
    
    def is_connected(self) -> bool:
        """Check if we have valid tokens"""
        return bool(self.tokens.get('access_token'))
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        if self.is_connected():
            return {
                'connected': True,
                'user_email': self.user_info.get('email'),
                'user_name': self.user_info.get('name'),
                'last_checked': datetime.utcnow().isoformat()
            }
        else:
            return {
                'connected': False,
                'error': 'Not authenticated',
                'requires_auth': True
            }

# Global instance for single user
google_drive = GoogleDriveSimple()