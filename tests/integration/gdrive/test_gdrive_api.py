#!/usr/bin/env python3
"""
Test Google Drive through the API to debug empty file list
"""
import asyncio
import aiohttp
import json

async def test_api():
    """Test via API endpoints"""
    base_url = "http://127.0.0.1:8001"
    
    print("=" * 60)
    print("GOOGLE DRIVE API TEST")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Check status
        print("\n1. Checking status...")
        async with session.get(f"{base_url}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            print(f"   Connected: {status.get('connected')}")
            print(f"   User: {status.get('user_email')}")
            
        if not status.get('connected'):
            print("   Not connected!")
            return
            
        # 2. Try different endpoints
        endpoints = [
            ("/api/v1/gdrive/files", "List files"),
            ("/api/v1/gdrive/files?page_size=5", "List files (limit 5)"),
            ("/api/v1/gdrive/folders", "List folders"),
        ]
        
        for endpoint, description in endpoints:
            print(f"\n2. Testing: {description}")
            print(f"   Endpoint: {endpoint}")
            async with session.get(f"{base_url}{endpoint}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        files = data.get('files', [])
                        count = data.get('count', len(files))
                    else:
                        files = data
                        count = len(files)
                    
                    print(f"   Status: {resp.status}")
                    print(f"   Files found: {count}")
                    
                    if files and count > 0:
                        print("   First file:")
                        file = files[0] if isinstance(files, list) else list(files.values())[0]
                        print(f"     Name: {file.get('name', 'Unknown')}")
                        print(f"     Type: {file.get('mimeType', 'Unknown')}")
                        print(f"     ID: {file.get('id', 'Unknown')}")
                else:
                    print(f"   Error: {resp.status}")
                    error_text = await resp.text()
                    print(f"   Details: {error_text[:200]}")
        
        # 3. Check the actual tokens
        print("\n3. Debug information:")
        async with session.get(f"{base_url}/api/v1/gdrive/debug") as resp:
            if resp.status == 200:
                debug = await resp.json()
                print(f"   Has tokens: {debug.get('has_tokens', False)}")
                print(f"   Token type: {debug.get('token_type', 'Unknown')}")
            else:
                print("   Debug endpoint not available")

if __name__ == "__main__":
    asyncio.run(test_api())