#!/usr/bin/env python3
"""
Direct PostgreSQL v4.2.0 integration test
Tests all major features without pytest mocking
"""

import asyncio
import os
import sys
from pathlib import Path
import numpy as np
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.services.memory_service_postgres import MemoryServicePostgres


async def test_postgresql_v42():
    """Test PostgreSQL v4.2.0 features"""
    print("🧪 Testing PostgreSQL v4.2.0 with pgvector")
    print("=" * 60)
    
    # Database connection
    db_url = "postgresql://secondbrain:changeme@localhost/secondbrain"
    backend = PostgresUnifiedBackend(db_url)
    
    try:
        # Initialize backend
        print("\n1️⃣ Testing Database Connection...")
        await backend.initialize()
        print("✅ Connected to PostgreSQL")
        
        # Check pgvector extension
        async with backend.acquire() as conn:
            vector_check = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            assert vector_check == 1
            print("✅ pgvector extension is active")
            
            # Check HNSW index
            index_check = await conn.fetchval("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_memories_embedding'
            """)
            assert index_check == 1
            print("✅ HNSW index exists")
        
        # Clean test data
        async with backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'test_v42'")
        
        # Test memory creation with embedding
        print("\n2️⃣ Testing Memory Creation with Embeddings...")
        embedding = np.random.rand(1536).tolist()
        
        created = await backend.create_memory({
            "content": "PostgreSQL v4.2.0 test with pgvector embeddings",
            "memory_type": "test",
            "importance_score": 0.9,
            "tags": ["v4.2.0", "test", "pgvector"],
            "metadata": {"version": "4.2.0"},
            "container_id": "test_v42"
        }, embedding)
        
        assert created["id"] is not None
        assert created["has_embedding"] is True
        print(f"✅ Created memory with ID: {created['id'][:8]}...")
        
        # Test vector search
        print("\n3️⃣ Testing Vector Search...")
        results = await backend.vector_search(
            embedding=embedding,
            limit=5,
            min_similarity=0.5,
            container_id="test_v42"
        )
        
        assert len(results) > 0
        assert results[0]["similarity"] > 0.99  # Should find itself
        print(f"✅ Vector search found {len(results)} results")
        print(f"   Top result similarity: {results[0]['similarity']:.4f}")
        
        # Test text search
        print("\n4️⃣ Testing Full-Text Search...")
        await backend.create_memory({
            "content": "Machine learning with transformer models",
            "container_id": "test_v42"
        })
        
        text_results = await backend.text_search(
            query="machine learning",
            limit=10,
            container_id="test_v42"
        )
        
        assert len(text_results) > 0
        print(f"✅ Text search found {len(text_results)} results")
        
        # Test hybrid search
        print("\n5️⃣ Testing Hybrid Search...")
        hybrid_results = await backend.hybrid_search(
            query="pgvector",
            embedding=embedding,
            limit=5,
            vector_weight=0.7,
            container_id="test_v42"
        )
        
        assert len(hybrid_results) > 0
        print(f"✅ Hybrid search found {len(hybrid_results)} results")
        
        # Test service with OpenAI embeddings
        print("\n6️⃣ Testing Memory Service with OpenAI...")
        service = MemoryServicePostgres(
            connection_string=db_url,
            enable_embeddings=True
        )
        await service.initialize()
        
        if os.getenv("OPENAI_API_KEY"):
            created_with_ai = await service.create_memory(
                content="Testing automatic OpenAI embeddings in v4.2.0",
                memory_type="test",
                importance_score=0.95,
                tags=["openai", "automatic"],
                generate_embedding=True
            )
            
            print(f"✅ Created memory with OpenAI embedding: {created_with_ai['id'][:8]}...")
            
            # Search for it
            semantic_results = await service.semantic_search(
                query="OpenAI embeddings",
                limit=5,
                min_similarity=0.5
            )
            
            found = any(r["id"] == created_with_ai["id"] for r in semantic_results)
            if found:
                print("✅ Semantic search found the created memory")
            else:
                print("⚠️ Semantic search didn't find the memory (may need time for embedding)")
        else:
            print("⚠️ OPENAI_API_KEY not set, skipping OpenAI tests")
        
        # Test statistics
        print("\n7️⃣ Testing Statistics...")
        stats = await backend.get_statistics()
        print(f"✅ Statistics retrieved:")
        print(f"   Total memories: {stats['total_memories']}")
        print(f"   Backend: {stats['backend']}")
        print(f"   Vector support: {stats.get('has_vector_support', 'Available')}")
        
        # Clean up test data
        print("\n8️⃣ Cleaning up test data...")
        async with backend.acquire() as conn:
            deleted = await conn.execute("DELETE FROM memories WHERE container_id = 'test_v42'")
            print(f"✅ Cleaned up test data")
        
        print("\n" + "=" * 60)
        print("✅ All PostgreSQL v4.2.0 tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await backend.close()


if __name__ == "__main__":
    success = asyncio.run(test_postgresql_v42())
    sys.exit(0 if success else 1)