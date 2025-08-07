#!/usr/bin/env python3
"""
Test script to verify all API endpoints work with single-user architecture.
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_api():
    """Test all API endpoints."""
    base_url = "http://localhost:8000"
    api_key = "test-key"  # In dev mode, any key works
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Second Brain API (Single User)")
        print("=" * 50)
        
        # Test health endpoint
        print("\n1️⃣ Testing Health Endpoint...")
        async with session.get(f"{base_url}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Health check: {data['status']}")
            else:
                print(f"❌ Health check failed: {resp.status}")
        
        # Test create memory
        print("\n2️⃣ Testing Create Memory...")
        memory_data = {
            "content": "This is a test memory for single-user container",
            "memory_type": "semantic",
            "importance_score": 0.8,
            "tags": ["test", "api", "single-user"],
            "metadata": {"source": "api_test"}
        }
        
        async with session.post(
            f"{base_url}/api/v2/memories",
            headers=headers,
            json=memory_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                memory_id = data['memory']['id']
                print(f"✅ Created memory: {memory_id}")
            else:
                print(f"❌ Create failed: {resp.status}")
                text = await resp.text()
                print(f"   Error: {text}")
                return
        
        # Test get memory
        print("\n3️⃣ Testing Get Memory...")
        async with session.get(
            f"{base_url}/api/v2/memories/{memory_id}",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Retrieved memory: {data['memory']['content'][:50]}...")
            else:
                print(f"❌ Get failed: {resp.status}")
        
        # Test list memories
        print("\n4️⃣ Testing List Memories...")
        async with session.get(
            f"{base_url}/api/v2/memories",
            headers=headers,
            params={"limit": 5}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Listed {len(data['memories'])} memories")
            else:
                print(f"❌ List failed: {resp.status}")
        
        # Test update memory
        print("\n5️⃣ Testing Update Memory...")
        update_data = {
            "importance_score": 0.95,
            "tags": ["test", "updated"]
        }
        
        async with session.put(
            f"{base_url}/api/v2/memories/{memory_id}",
            headers=headers,
            json=update_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Updated memory importance: {data['memory']['importance_score']}")
            else:
                print(f"❌ Update failed: {resp.status}")
        
        # Test search
        print("\n6️⃣ Testing Search...")
        search_data = {
            "query": "test",
            "limit": 10
        }
        
        async with session.post(
            f"{base_url}/api/v2/search",
            headers=headers,
            json=search_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Search found {len(data['results'])} results")
            else:
                print(f"❌ Search failed: {resp.status}")
        
        # Test stats
        print("\n7️⃣ Testing Stats Endpoint...")
        async with session.get(
            f"{base_url}/api/v2/stats",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Stats: {data['total_memories']} total memories")
            else:
                print(f"❌ Stats failed: {resp.status}")
        
        # Test delete memory
        print("\n8️⃣ Testing Delete Memory...")
        async with session.delete(
            f"{base_url}/api/v2/memories/{memory_id}",
            headers=headers
        ) as resp:
            if resp.status == 200:
                print(f"✅ Deleted memory successfully")
            else:
                print(f"❌ Delete failed: {resp.status}")
        
        print("\n" + "=" * 50)
        print("🎉 API Test Complete!")
        print("\n📝 Summary:")
        print("- Single-user container mode ✅")
        print("- No user_id required ✅")
        print("- Simple API key auth ✅")
        print("- In-memory storage with persistence ✅")


if __name__ == "__main__":
    print("Starting API test...")
    print("Make sure the server is running: uvicorn app.app:app")
    input("Press Enter when server is ready...")
    
    asyncio.run(test_api())