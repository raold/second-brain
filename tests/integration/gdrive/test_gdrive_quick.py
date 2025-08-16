#!/usr/bin/env python3
"""
Quick test of Google Drive integration
"""
import os
import asyncio
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

async def test_gdrive():
    """Test Google Drive endpoints"""
    base_url = "http://localhost:8001"
    
    async with aiohttp.ClientSession() as session:
        # Check status
        print("1. Checking Google Drive status...")
        async with session.get(f"{base_url}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            print(f"   Connected: {status.get('connected', False)}")
            print(f"   Configured: {status.get('credentials_configured', False)}")
        
        # If not connected, get auth URL
        if not status.get('connected'):
            print("\n2. Getting authentication URL...")
            async with session.post(f"{base_url}/api/v1/gdrive/connect") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Auth URL: {data.get('auth_url', 'Not available')[:100]}...")
                    print("\n   Visit the auth URL to authenticate with Google")
                else:
                    error = await resp.text()
                    print(f"   Error: {error}")
        else:
            print("\n2. Already connected! Listing files...")
            async with session.get(f"{base_url}/api/v1/gdrive/files") as resp:
                if resp.status == 200:
                    files = await resp.json()
                    print(f"   Found {len(files)} files")
                    for file in files[:5]:
                        print(f"   - {file.get('name', 'Unknown')}")
                else:
                    print(f"   Error: {resp.status}")
        
        print("\n3. Google OAuth Configuration:")
        print(f"   CLIENT_ID: {'SET' if os.getenv('GOOGLE_CLIENT_ID') else 'NOT SET'}")
        print(f"   CLIENT_SECRET: {'SET' if os.getenv('GOOGLE_CLIENT_SECRET') else 'NOT SET'}")
        print(f"   REDIRECT_URI: {os.getenv('GOOGLE_REDIRECT_URI', 'Not set')}")

if __name__ == "__main__":
    asyncio.run(test_gdrive())