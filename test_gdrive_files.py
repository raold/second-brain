#!/usr/bin/env python3
"""
Debug Google Drive file listing
"""
import os
import asyncio
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

async def test_files():
    """Test Google Drive file listing"""
    base_url = "http://127.0.0.1:8001"
    
    print("=" * 60)
    print("GOOGLE DRIVE FILE LISTING TEST")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Check connection status
        print("\n1. Connection Status:")
        async with session.get(f"{base_url}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            print(f"   Connected: {status.get('connected')}")
            print(f"   User: {status.get('user_email')}")
        
        if not status.get('connected'):
            print("\n   ERROR: Not connected to Google Drive!")
            return
        
        # 2. List files
        print("\n2. Listing files from Google Drive...")
        async with session.get(f"{base_url}/api/v1/gdrive/files") as resp:
            if resp.status == 200:
                data = await resp.json()
                files = data.get('files', [])
                count = data.get('count', 0)
                
                print(f"   Found {count} files")
                
                if files:
                    print("\n   First 10 files:")
                    for i, file in enumerate(files[:10], 1):
                        print(f"   {i}. {file.get('name', 'Unknown')} ({file.get('mimeType', 'Unknown type')})")
                else:
                    print("   No files returned")
            else:
                error = await resp.text()
                print(f"   Error: {error}")
        
        # 3. Try search endpoint
        print("\n3. Trying search endpoint...")
        async with session.get(f"{base_url}/api/v1/gdrive/search?query=*") as resp:
            if resp.status == 200:
                results = await resp.json()
                print(f"   Search returned {len(results)} results")
            else:
                print(f"   Search endpoint returned: {resp.status}")
        
        # 4. Check raw Google API
        print("\n4. Testing direct Google Drive API call...")
        # Get access token from service
        async with session.get(f"{base_url}/api/v1/gdrive/debug/token") as resp:
            if resp.status == 200:
                token_info = await resp.json()
                access_token = token_info.get('access_token')
                
                if access_token:
                    # Direct Google API call
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with session.get(
                        "https://www.googleapis.com/drive/v3/files?pageSize=10",
                        headers=headers
                    ) as google_resp:
                        if google_resp.status == 200:
                            google_data = await google_resp.json()
                            files = google_data.get('files', [])
                            print(f"   Direct API returned {len(files)} files")
                            if files:
                                print("   First file:", files[0].get('name'))
                        else:
                            print(f"   Direct API error: {google_resp.status}")
            else:
                print("   Could not get access token for testing")

if __name__ == "__main__":
    asyncio.run(test_files())