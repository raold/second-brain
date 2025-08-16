#!/usr/bin/env python3
"""
Test Google Drive authentication with new credentials
"""
import os
import asyncio
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

async def test_auth():
    """Test Google Drive OAuth flow"""
    base_url = "http://127.0.0.1:8001"
    
    print("=" * 60)
    print("GOOGLE DRIVE AUTHENTICATION TEST")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Check status
        print("\n1. Checking credentials configuration...")
        async with session.get(f"{base_url}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            print(f"   Connected: {status.get('connected', False)}")
            print(f"   Configured: {status.get('credentials_configured', False)}")
        
        # 2. Get auth URL
        print("\n2. Getting OAuth URL...")
        async with session.post(f"{base_url}/api/v1/gdrive/connect") as resp:
            if resp.status == 200:
                data = await resp.json()
                auth_url = data.get('auth_url', '')
                print(f"   Success! Auth URL generated")
                print(f"\n3. Authentication URL:")
                print("   " + "="*50)
                print(f"   {auth_url}")
                print("   " + "="*50)
                print("\n4. Next steps:")
                print("   a) Click the URL above (or copy to browser)")
                print("   b) Login with: dro@lynchburgsmiles.com")
                print("   c) Grant permissions")
                print("   d) You'll be redirected to the app")
                
                # Also open in browser
                print("\n5. Opening browser automatically...")
                import webbrowser
                webbrowser.open(auth_url)
                
            else:
                error = await resp.text()
                print(f"   Error: {error}")
        
        print("\n6. Credentials being used:")
        print(f"   Client ID: {os.getenv('GOOGLE_CLIENT_ID', 'NOT SET')[:50]}...")
        print(f"   Project: second-brain-469213")
        print(f"   Redirect: {os.getenv('GOOGLE_REDIRECT_URI', 'NOT SET')}")

if __name__ == "__main__":
    asyncio.run(test_auth())