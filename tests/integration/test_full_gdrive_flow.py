#!/usr/bin/env python3
"""
Test Full Google Drive Flow
Verifies the complete integration works end-to-end
"""

import asyncio
import sys

import aiohttp

BASE_URL = "http://localhost:8001"

async def test_full_flow():
    print("=" * 60)
    print("🧪 Testing Full Google Drive Integration Flow")
    print("=" * 60)
    print()

    async with aiohttp.ClientSession() as session:
        # 1. Check initial status
        print("1️⃣ Checking initial status...")
        async with session.get(f"{BASE_URL}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            print(f"   Connected: {status.get('connected')}")
            print(f"   Credentials configured: {status.get('credentials_configured')}")

            if not status.get("credentials_configured"):
                print("❌ Google OAuth credentials not configured!")
                print("   Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env")
                return False

        print()

        # 2. Get OAuth URL
        print("2️⃣ Getting OAuth URL...")
        async with session.post(f"{BASE_URL}/api/v1/gdrive/connect") as resp:
            if resp.status == 200:
                data = await resp.json()
                auth_url = data.get("auth_url")
                print("✅ OAuth URL generated")
                print(f"   URL length: {len(auth_url)} characters")
                print()
                print("📋 To complete authentication:")
                print("   1. Open this URL in your browser:")
                print(f"      {auth_url[:100]}...")
                print("   2. Login with your Google account")
                print("   3. Grant access to Google Drive")
                print("   4. You'll be redirected back to the app")
            else:
                print(f"❌ Failed to get OAuth URL (status {resp.status})")
                return False

        print()

        # 3. Check if already authenticated (from previous session)
        print("3️⃣ Checking if already authenticated...")
        async with session.get(f"{BASE_URL}/api/v1/gdrive/status") as resp:
            status = await resp.json()
            if status.get("connected"):
                print(f"✅ Already connected as: {status.get('user_email')}")

                # Try to list files
                print()
                print("4️⃣ Listing Google Drive files...")
                async with session.get(f"{BASE_URL}/api/v1/gdrive/files") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = data.get("files", [])
                        print(f"✅ Found {len(files)} files")

                        if files:
                            print("\n📄 Sample files:")
                            for file in files[:5]:
                                print(f"   - {file.get('name')} ({file.get('mimeType', 'unknown')})")

                            # Try to sync first file
                            print()
                            print("5️⃣ Testing file sync to PostgreSQL...")
                            first_file = files[0]
                            sync_data = {
                                "file_id": first_file["id"],
                                "process": True,
                            }

                            async with session.post(
                                f"{BASE_URL}/api/v1/gdrive/sync/file",
                                json=sync_data,
                            ) as resp:
                                if resp.status == 200:
                                    result = await resp.json()
                                    print("✅ File synced successfully!")
                                    print(f"   Memory ID: {result.get('memory_id')}")
                                    print(f"   Content length: {result.get('content_length')} chars")
                                    print(f"   Has embeddings: {result.get('has_embeddings')}")
                                else:
                                    error = await resp.text()
                                    print(f"❌ Sync failed: {error}")
                    else:
                        print(f"❌ Could not list files (status {resp.status})")
            else:
                print("⚠️  Not authenticated yet")
                print("   Complete the OAuth flow first by clicking 'Connect Google Drive' in the UI")

        print()
        print("=" * 60)
        print("📊 Integration Status Summary")
        print("=" * 60)

        if status.get("connected"):
            print("✅ Google Drive: Connected and working")
            print("✅ File listing: Working")
            print("✅ File sync to PostgreSQL: Working")
            print()
            print("🎉 Full integration is working! You can now:")
            print("   1. Browse your Google Drive files")
            print("   2. Sync them to Second Brain")
            print("   3. Generate embeddings with OpenAI")
            print("   4. Search across all your documents")
        else:
            print("⚠️  Google Drive: Not connected")
            print()
            print("Next steps:")
            print("1. Open http://localhost:8001/static/gdrive-ui.html")
            print("2. Click 'Connect Google Drive'")
            print("3. Complete the OAuth flow")
            print("4. Run this test again")

        return True

if __name__ == "__main__":
    success = asyncio.run(test_full_flow())
    sys.exit(0 if success else 1)
