#!/usr/bin/env python3
"""
API Integration tests for v4.2.0
Tests all the API endpoints with the running service
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_api_v42():
    """Test v4.2.0 API endpoints"""
    print("🧪 Testing v4.2.0 API Endpoints")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            print("\n1️⃣ Testing Health Endpoint...")
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            health = response.json()
            print(f"✅ Health check passed: {health}")
            
            # Test root endpoint
            print("\n2️⃣ Testing Root Endpoint...")
            response = await client.get(f"{base_url}/")
            assert response.status_code == 200
            root = response.json()
            assert root["version"] == "4.2.0"
            print(f"✅ Version confirmed: {root['version']}")
            
            # Create a test memory
            print("\n3️⃣ Testing Memory Creation...")
            memory_data = {
                "content": "API test for v4.2.0 with automatic embeddings",
                "memory_type": "test",
                "importance_score": 0.85,
                "tags": ["api", "test", "v4.2.0"]
            }
            response = await client.post(
                f"{base_url}/api/v2/memories/",
                json=memory_data
            )
            assert response.status_code == 201
            created = response.json()
            memory_id = created["memory"]["id"]
            print(f"✅ Created memory: {memory_id}")
            
            # Test vector search
            print("\n4️⃣ Testing Vector Search...")
            search_data = {
                "query": "automatic embeddings API",
                "limit": 5,
                "min_similarity": 0.5
            }
            response = await client.post(
                f"{base_url}/api/v2/search/vector",
                json=search_data
            )
            assert response.status_code == 200
            vector_results = response.json()
            print(f"✅ Vector search returned {vector_results['total']} results")
            
            # Test hybrid search
            print("\n5️⃣ Testing Hybrid Search...")
            hybrid_data = {
                "query": "v4.2.0",
                "limit": 5,
                "vector_weight": 0.6
            }
            response = await client.post(
                f"{base_url}/api/v2/search/hybrid",
                json=hybrid_data
            )
            assert response.status_code == 200
            hybrid_results = response.json()
            print(f"✅ Hybrid search returned {hybrid_results['total']} results")
            
            # Test search suggestions
            print("\n6️⃣ Testing Search Suggestions...")
            response = await client.get(
                f"{base_url}/api/v2/search/suggestions",
                params={"prefix": "api", "limit": 5}
            )
            assert response.status_code == 200
            suggestions = response.json()
            print(f"✅ Got {len(suggestions['suggestions'])} suggestions")
            
            # Test duplicate detection
            print("\n7️⃣ Testing Duplicate Detection...")
            response = await client.get(
                f"{base_url}/api/v2/search/duplicates",
                params={"similarity_threshold": 0.95}
            )
            assert response.status_code == 200
            duplicates = response.json()
            print(f"✅ Found {duplicates['total_found']} potential duplicates")
            
            # Test knowledge graph
            print("\n8️⃣ Testing Knowledge Graph...")
            if memory_id:
                response = await client.get(
                    f"{base_url}/api/v2/search/knowledge-graph/{memory_id}",
                    params={"depth": 1}
                )
                if response.status_code == 200:
                    graph = response.json()
                    print(f"✅ Knowledge graph has {len(graph['nodes'])} nodes")
                else:
                    print("⚠️ Knowledge graph endpoint returned error (expected if no relationships)")
            
            # Test reindexing
            print("\n9️⃣ Testing Reindex Endpoint...")
            response = await client.post(
                f"{base_url}/api/v2/search/reindex",
                params={"batch_size": 10, "max_memories": 100}
            )
            assert response.status_code == 200
            reindex = response.json()
            print(f"✅ Reindexed {reindex['processed']} memories")
            
            # Clean up - delete test memory
            print("\n🧹 Cleaning up test data...")
            response = await client.delete(
                f"{base_url}/api/v2/memories/{memory_id}"
            )
            print(f"   Delete response status: {response.status_code}")
            # Check if successfully deleted
            if response.status_code in [200, 204]:
                print(f"✅ Deleted test memory")
            else:
                print(f"⚠️ Could not delete test memory: {response.status_code}")
            
            print("\n" + "=" * 60)
            print("✅ All API tests passed!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n❌ API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_api_v42())
    sys.exit(0 if success else 1)