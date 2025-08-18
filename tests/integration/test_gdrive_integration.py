#!/usr/bin/env python3
"""
Test Google Drive Integration with Second Brain v4.2.3
"""

import asyncio
from datetime import datetime

import aiohttp

BASE_URL = "http://localhost:8001"

async def test_gdrive_integration():
    print("=" * 60)
    print("🧪 Testing Google Drive Integration")
    print("=" * 60)
    print()

    async with aiohttp.ClientSession() as session:
        # 1. Check connection status
        print("1️⃣ Checking Google Drive connection status...")
        async with session.get(f"{BASE_URL}/api/v1/gdrive/status") as resp:
            status = await resp.json()

            if status.get("connected"):
                print("✅ Connected to Google Drive")
                print(f"   User: {status.get('user_email')}")
                quota = status.get("storage_quota", {})
                used_gb = quota.get("usage", 0) / (1024**3)
                total_gb = quota.get("limit", 0) / (1024**3)
                print(f"   Storage: {used_gb:.2f} GB / {total_gb:.2f} GB")
            else:
                print("❌ Not connected to Google Drive")
                if status.get("error"):
                    print(f"   Error: {status['error']}")
                if not status.get("credentials_configured"):
                    print("   ⚠️  Google OAuth credentials not configured in .env")
                    print("   Run: python3 setup_google_oauth.py")
                    return

        print()

        # 2. Test memory service integration
        print("2️⃣ Testing Memory Service Integration...")
        async with session.get(f"{BASE_URL}/api/v2/memories") as resp:
            if resp.status == 200:
                memories = await resp.json()
                print("✅ Memory service is working")
                print(f"   Total memories: {len(memories)}")
            else:
                print(f"❌ Memory service returned status {resp.status}")

        print()

        # 3. Test creating a memory
        print("3️⃣ Testing Memory Creation...")
        test_memory = {
            "content": f"Test memory from Google Drive integration test - {datetime.now()}",
            "memory_type": "episodic",
            "importance_score": 0.8,
            "tags": ["test", "google-drive", "integration"],
            "metadata": {
                "source": "test_script",
                "test_time": datetime.now().isoformat(),
            },
        }

        async with session.post(
            f"{BASE_URL}/api/v2/memories",
            json=test_memory,
        ) as resp:
            if resp.status in [200, 201]:
                memory = await resp.json()
                print("✅ Memory created successfully")
                print(f"   ID: {memory.get('id', 'N/A')[:8]}...")
                print(f"   Content: {memory.get('content', '')[:50]}...")
            else:
                print(f"❌ Failed to create memory (status {resp.status})")

        print()

        # 4. Test static files
        print("4️⃣ Testing Static File Serving...")
        static_files = [
            "/static/gdrive-ui.html",
            "/static/css/gdrive-ui.css",
            "/static/js/gdrive-ui.js",
        ]

        all_good = True
        for file_path in static_files:
            async with session.get(f"{BASE_URL}{file_path}") as resp:
                if resp.status == 200:
                    content_length = len(await resp.text())
                    print(f"✅ {file_path} ({content_length} bytes)")
                else:
                    print(f"❌ {file_path} (status {resp.status})")
                    all_good = False

        print()

        # 5. Summary
        print("=" * 60)
        print("📊 Test Summary")
        print("=" * 60)

        if status.get("connected"):
            print("✅ Google Drive: Connected and ready")
            print("🎯 Next: Open http://localhost:8001/static/gdrive-ui.html")
        elif status.get("credentials_configured"):
            print("⚠️  Google Drive: Credentials configured but not connected")
            print("🎯 Next: Click 'Connect Google Drive' in the UI")
        else:
            print("❌ Google Drive: Not configured")
            print("🎯 Next: Run 'python3 setup_google_oauth.py' to configure")

        if all_good:
            print("✅ All static files are being served correctly")

        print()
        print("🌐 UI URL: http://localhost:8001/static/gdrive-ui.html")
        print("📚 API Docs: http://localhost:8001/docs")

if __name__ == "__main__":
    asyncio.run(test_gdrive_integration())
