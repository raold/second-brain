#!/usr/bin/env python3
"""
Performance testing script for PostgreSQL backend
Tests various operations and generates performance report
"""

import asyncio
import time
import random
import statistics
import json
from typing import List, Dict, Any
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.services.memory_service_postgres import MemoryServicePostgres


class PerformanceTester:
    """Performance testing for PostgreSQL backend"""
    
    def __init__(self, connection_string: str = None):
        self.backend = PostgresUnifiedBackend(connection_string)
        self.service = MemoryServicePostgres(connection_string, enable_embeddings=False)
        self.results = {}
        
    async def setup(self):
        """Initialize connections"""
        await self.backend.initialize()
        await self.service.initialize()
        
        # Clean test data
        async with self.backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'perf_test'")
            
    async def teardown(self):
        """Clean up"""
        # Clean test data
        async with self.backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'perf_test'")
            
        await self.backend.close()
        await self.service.close()
        
    async def test_insert_performance(self, count: int = 1000):
        """Test insert performance"""
        print(f"\n📝 Testing INSERT performance ({count} memories)...")
        
        times = []
        
        for i in range(count):
            memory = {
                "content": f"Performance test memory {i}: " + "x" * random.randint(100, 500),
                "memory_type": random.choice(["knowledge", "experience", "task"]),
                "importance_score": random.random(),
                "tags": random.sample(["test", "perf", "benchmark", "data"], k=2),
                "metadata": {"index": i, "batch": "perf_test"},
                "container_id": "perf_test"
            }
            
            start = time.perf_counter()
            await self.backend.create_memory(memory)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
            
            if (i + 1) % 100 == 0:
                print(f"  ✓ Inserted {i + 1}/{count} memories")
                
        self.results["insert"] = {
            "count": count,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99),
            "total_s": sum(times) / 1000
        }
        
        print(f"  Mean: {self.results['insert']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['insert']['p99_ms']:.2f}ms")
        
    async def test_vector_search_performance(self, queries: int = 100):
        """Test vector search performance"""
        print(f"\n🔍 Testing VECTOR SEARCH performance ({queries} queries)...")
        
        # Generate random embeddings for test memories
        print("  Generating test embeddings...")
        memories = await self.backend.list_memories(limit=100, container_id="perf_test")
        
        for memory in memories[:50]:  # Add embeddings to first 50
            embedding = np.random.rand(1536).tolist()
            await self.backend.update_memory(memory["id"], {}, embedding)
            
        times = []
        
        for i in range(queries):
            # Random query embedding
            query_embedding = np.random.rand(1536).tolist()
            
            start = time.perf_counter()
            results = await self.backend.vector_search(
                embedding=query_embedding,
                limit=10,
                container_id="perf_test"
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
            if (i + 1) % 20 == 0:
                print(f"  ✓ Completed {i + 1}/{queries} searches")
                
        self.results["vector_search"] = {
            "queries": queries,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['vector_search']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['vector_search']['p99_ms']:.2f}ms")
        
    async def test_text_search_performance(self, queries: int = 100):
        """Test full-text search performance"""
        print(f"\n📖 Testing TEXT SEARCH performance ({queries} queries)...")
        
        search_terms = ["test", "memory", "performance", "data", "knowledge", "system"]
        times = []
        
        for i in range(queries):
            query = random.choice(search_terms)
            
            start = time.perf_counter()
            results = await self.backend.text_search(
                query=query,
                limit=10,
                container_id="perf_test"
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
            if (i + 1) % 20 == 0:
                print(f"  ✓ Completed {i + 1}/{queries} searches")
                
        self.results["text_search"] = {
            "queries": queries,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['text_search']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['text_search']['p99_ms']:.2f}ms")
        
    async def test_hybrid_search_performance(self, queries: int = 50):
        """Test hybrid search performance"""
        print(f"\n🔄 Testing HYBRID SEARCH performance ({queries} queries)...")
        
        search_terms = ["test", "memory", "performance", "data"]
        times = []
        
        for i in range(queries):
            query = random.choice(search_terms)
            embedding = np.random.rand(1536).tolist()
            
            start = time.perf_counter()
            results = await self.backend.hybrid_search(
                query=query,
                embedding=embedding,
                limit=10,
                container_id="perf_test"
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
            if (i + 1) % 10 == 0:
                print(f"  ✓ Completed {i + 1}/{queries} searches")
                
        self.results["hybrid_search"] = {
            "queries": queries,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['hybrid_search']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['hybrid_search']['p99_ms']:.2f}ms")
        
    async def test_update_performance(self, count: int = 100):
        """Test update performance"""
        print(f"\n✏️ Testing UPDATE performance ({count} updates)...")
        
        # Get memories to update
        memories = await self.backend.list_memories(limit=count, container_id="perf_test")
        
        if len(memories) < count:
            print(f"  ⚠️ Only {len(memories)} memories available for update")
            count = len(memories)
            
        times = []
        
        for i, memory in enumerate(memories[:count]):
            updates = {
                "importance_score": random.random(),
                "tags": random.sample(["updated", "test", "perf"], k=2)
            }
            
            start = time.perf_counter()
            await self.backend.update_memory(memory["id"], updates)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
            if (i + 1) % 20 == 0:
                print(f"  ✓ Updated {i + 1}/{count} memories")
                
        self.results["update"] = {
            "count": count,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['update']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['update']['p99_ms']:.2f}ms")
        
    async def test_relationship_performance(self, count: int = 100):
        """Test relationship creation performance"""
        print(f"\n🔗 Testing RELATIONSHIP performance ({count} relationships)...")
        
        # Get memories for relationships
        memories = await self.backend.list_memories(limit=50, container_id="perf_test")
        
        if len(memories) < 2:
            print("  ⚠️ Not enough memories for relationship testing")
            return
            
        times = []
        
        for i in range(count):
            source = random.choice(memories)
            target = random.choice([m for m in memories if m["id"] != source["id"]])
            
            start = time.perf_counter()
            await self.backend.create_relationship(
                source_id=source["id"],
                target_id=target["id"],
                relationship_type=random.choice(["related", "similar", "follows"]),
                strength=random.random()
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
            if (i + 1) % 20 == 0:
                print(f"  ✓ Created {i + 1}/{count} relationships")
                
        self.results["relationships"] = {
            "count": count,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['relationships']['mean_ms']:.2f}ms")
        print(f"  P99: {self.results['relationships']['p99_ms']:.2f}ms")
        
    async def test_statistics_performance(self):
        """Test statistics query performance"""
        print(f"\n📊 Testing STATISTICS query performance...")
        
        times = []
        
        for i in range(10):
            start = time.perf_counter()
            stats = await self.backend.get_statistics()
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
            
        self.results["statistics"] = {
            "queries": 10,
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "memory_count": stats.get("total_memories", 0)
        }
        
        print(f"  Mean: {self.results['statistics']['mean_ms']:.2f}ms")
        print(f"  Total memories: {self.results['statistics']['memory_count']}")
        
    def generate_report(self):
        """Generate performance report"""
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE TEST REPORT")
        print("=" * 60)
        
        # Summary table
        print("\n📊 Summary (all times in milliseconds):")
        print(f"{'Operation':<20} {'Mean':<10} {'Median':<10} {'P95':<10} {'P99':<10}")
        print("-" * 60)
        
        for op in ["insert", "vector_search", "text_search", "hybrid_search", "update"]:
            if op in self.results:
                r = self.results[op]
                print(f"{op:<20} {r['mean_ms']:<10.2f} {r['median_ms']:<10.2f} "
                      f"{r['p95_ms']:<10.2f} {r['p99_ms']:<10.2f}")
                
        # Throughput
        print("\n📈 Throughput:")
        if "insert" in self.results:
            throughput = self.results["insert"]["count"] / self.results["insert"]["total_s"]
            print(f"  Insert: {throughput:.1f} ops/sec")
            
        # Save results to file
        report_file = Path(__file__).parent.parent / "performance_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Full report saved to: {report_file}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if "insert" in self.results and self.results["insert"]["p99_ms"] > 100:
            print("  ⚠️ Insert P99 > 100ms - Consider batch inserts")
        if "vector_search" in self.results and self.results["vector_search"]["p99_ms"] > 200:
            print("  ⚠️ Vector search P99 > 200ms - Check HNSW index parameters")
        if "text_search" in self.results and self.results["text_search"]["p99_ms"] > 100:
            print("  ⚠️ Text search P99 > 100ms - Check GIN index and vacuum status")
            
        print("\n✅ Performance testing complete!")


async def main():
    """Run performance tests"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="PostgreSQL performance testing")
    parser.add_argument("--insert", type=int, default=1000, help="Number of inserts")
    parser.add_argument("--queries", type=int, default=100, help="Number of queries")
    parser.add_argument("--skip-insert", action="store_true", help="Skip insert test")
    parser.add_argument("--database-url", type=str, help="Database URL")
    
    args = parser.parse_args()
    
    print("🚀 Second Brain PostgreSQL Performance Test")
    print("=" * 60)
    
    # Get database URL
    db_url = args.database_url or os.getenv("DATABASE_URL", "postgresql://localhost/second_brain")
    print(f"📡 Database: {db_url.split('@')[-1]}")
    
    tester = PerformanceTester(db_url)
    
    try:
        await tester.setup()
        
        # Run tests
        if not args.skip_insert:
            await tester.test_insert_performance(args.insert)
            
        await tester.test_text_search_performance(args.queries)
        await tester.test_vector_search_performance(args.queries // 2)
        await tester.test_hybrid_search_performance(args.queries // 4)
        await tester.test_update_performance(args.queries)
        await tester.test_relationship_performance(args.queries)
        await tester.test_statistics_performance()
        
        # Generate report
        tester.generate_report()
        
    finally:
        await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())