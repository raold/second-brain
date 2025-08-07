#!/usr/bin/env python3
"""
Simple test to verify v4.2.0 basic functionality
"""

import httpx
import asyncio
import json


async def simple_test():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. Check health
        print("1. Testing health...")
        resp = await client.get(f"{base_url}/health")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
        
        # 2. Create a memory
        print("\n2. Creating memory...")
        memory_data = {
            "content": "Simple test memory for v4.2.0",
            "memory_type": "test",
            "importance_score": 0.5
        }
        resp = await client.post(f"{base_url}/api/v2/memories/", json=memory_data)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 201:
            created = resp.json()
            print(f"   Created: {json.dumps(created, indent=2)}")
            memory_id = created["memory"]["id"]
            
            # 3. List memories
            print("\n3. Listing memories...")
            resp = await client.get(f"{base_url}/api/v2/memories/")
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Total: {data['total']}")
                print(f"   First memory: {data['memories'][0]['content'] if data['memories'] else 'None'}")
            
            # 4. Get specific memory
            print(f"\n4. Getting memory {memory_id}...")
            resp = await client.get(f"{base_url}/api/v2/memories/{memory_id}")
            print(f"   Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"   Error: {resp.text}")
            else:
                print(f"   Found: {resp.json()['memory']['content']}")
            
            # 5. Search
            print("\n5. Testing search...")
            resp = await client.post(
                f"{base_url}/api/v2/search",
                json={"query": "test", "limit": 5}
            )
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                results = resp.json()
                print(f"   Found: {results['total']} results")


if __name__ == "__main__":
    asyncio.run(simple_test())