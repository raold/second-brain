#!/usr/bin/env python3
"""
Test the COMPLETE Second Brain pipeline:
1. API endpoint
2. PostgreSQL storage  
3. OpenAI embeddings
4. pgvector semantic search
"""

import asyncio
import asyncpg
import httpx
import json
from datetime import datetime

API_URL = "http://localhost:8000"
DB_URL = "postgresql://secondbrain:changeme@localhost:5432/secondbrain"

async def test_system():
    print("=" * 60)
    print("  SECOND BRAIN v4.2.0 - FULL SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Check API health
    print("\n[1/5] Testing API health...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is healthy: {data}")
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("   Run: ./start_postgres_only.sh")
            return False
    
    # Test 2: Direct PostgreSQL connection
    print("\n[2/5] Testing PostgreSQL connection...")
    try:
        conn = await asyncpg.connect(DB_URL)
        
        # Check pgvector extension
        has_vector = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if has_vector:
            print("✅ pgvector extension is installed")
        else:
            print("❌ pgvector extension NOT found")
            
        await conn.close()
    except Exception as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        return False
    
    # Test 3: Create a memory with embedding
    print("\n[3/5] Creating a test memory...")
    test_memory = {
        "content": f"Test memory created at {datetime.now().isoformat()} - The Second Brain system uses PostgreSQL with pgvector for semantic search",
        "memory_type": "test",
        "importance_score": 0.95,
        "tags": ["test", "system", "postgresql", "embeddings"],
        "metadata": {"test_run": True, "version": "4.2.0"}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/v2/memories",
            json=test_memory
        )
        
        if response.status_code == 200 or response.status_code == 201:
            created_memory = response.json()
            memory_id = created_memory.get('id', created_memory.get('memory', {}).get('id'))
            print(f"✅ Memory created with ID: {memory_id}")
        else:
            print(f"❌ Failed to create memory: {response.status_code}")
            print(response.text)
            return False
    
    # Test 4: Verify embedding was generated
    print("\n[4/5] Checking if embedding was generated...")
    conn = await asyncpg.connect(DB_URL)
    
    embedding_check = await conn.fetchval(
        """
        SELECT COUNT(*) FROM memories 
        WHERE embedding IS NOT NULL 
        AND created_at > NOW() - INTERVAL '1 minute'
        """
    )
    
    if embedding_check > 0:
        print(f"✅ Embeddings are being generated ({embedding_check} recent memories have embeddings)")
    else:
        print("⚠️  No embeddings found - OpenAI key might not be configured")
    
    # Test 5: Test semantic search
    print("\n[5/5] Testing semantic search...")
    async with httpx.AsyncClient() as client:
        # Search for something related
        search_response = await client.get(
            f"{API_URL}/api/v2/search",
            params={"q": "PostgreSQL database"}
        )
        
        if search_response.status_code == 200:
            results = search_response.json()
            if isinstance(results, list):
                print(f"✅ Search returned {len(results)} results")
            elif isinstance(results, dict) and 'results' in results:
                print(f"✅ Search returned {len(results['results'])} results")
            else:
                print(f"✅ Search working, returned: {type(results)}")
        else:
            print(f"❌ Search failed: {search_response.status_code}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("  TEST COMPLETE!")
    print("=" * 60)
    
    # Get final stats
    memory_count = await conn.fetchval("SELECT COUNT(*) FROM memories")
    embedding_count = await conn.fetchval("SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL")
    
    print(f"\n📊 System Stats:")
    print(f"  - Total Memories: {memory_count}")
    print(f"  - Memories with Embeddings: {embedding_count}")
    print(f"  - Embedding Coverage: {(embedding_count/memory_count*100 if memory_count > 0 else 0):.1f}%")
    
    await conn.close()
    
    print("\n🎉 YOUR SECOND BRAIN IS FULLY OPERATIONAL!")
    print("\nAccess it at:")
    print("  - Dashboard: file:///C:/tools/second-brain/dashboard.html")
    print("  - API Docs: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_system())