#!/usr/bin/env python3
"""
Direct test of Google Drive API to see what files exist
"""
import os
import asyncio
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.google_drive_simple import google_drive

# Load environment variables
load_dotenv()

async def test_direct():
    """Test Google Drive directly"""
    print("=" * 60)
    print("DIRECT GOOGLE DRIVE TEST")
    print("=" * 60)
    
    # Check if connected
    print("\n1. Connection status:")
    status = google_drive.get_connection_status()
    print(f"   Connected: {status['connected']}")
    print(f"   User: {status.get('user_email', 'Unknown')}")
    
    if not status['connected']:
        print("\n   ERROR: Not connected!")
        return
    
    # Get access token
    access_token = google_drive.tokens.get("access_token")
    if not access_token:
        print("\n   ERROR: No access token!")
        return
    
    print(f"\n2. Access token present: Yes")
    print(f"   Token prefix: {access_token[:20]}...")
    
    # Try different queries
    import aiohttp
    
    queries = [
        ("All files", ""),  # No filter
        ("Non-folders", "mimeType != 'application/vnd.google-apps.folder'"),
        ("Documents", "mimeType = 'application/vnd.google-apps.document'"),
        ("Spreadsheets", "mimeType = 'application/vnd.google-apps.spreadsheet'"),
        ("PDFs", "mimeType = 'application/pdf'"),
        ("Images", "mimeType contains 'image/'"),
        ("Folders", "mimeType = 'application/vnd.google-apps.folder'"),
    ]
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        for name, query in queries:
            params = {
                "fields": "files(id,name,mimeType,size,modifiedTime)",
                "pageSize": 10,
            }
            if query:
                params["q"] = query
            
            print(f"\n3. Testing query: {name}")
            print(f"   Query: {query if query else 'None (all files)'}")
            
            async with session.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    files = data.get('files', [])
                    print(f"   Found {len(files)} files")
                    
                    if files:
                        print("   First 3 files:")
                        for i, file in enumerate(files[:3], 1):
                            print(f"     {i}. {file.get('name', 'Unknown')} ({file.get('mimeType', 'Unknown')})")
                else:
                    error = await resp.text()
                    print(f"   Error {resp.status}: {error[:100]}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_direct())