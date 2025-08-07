#!/usr/bin/env python3
"""
Performance benchmark for Second Brain v4.2.0
Tests vector search, hybrid search, and API performance
"""

import asyncio
import time
import statistics
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.services.memory_service_postgres import MemoryServicePostgres


class V42Benchmark:
    def __init__(self, db_url: str = "postgresql://secondbrain:changeme@localhost/secondbrain"):
        self.db_url = db_url
        self.backend = PostgresUnifiedBackend(db_url)
        self.api_base = "http://localhost:8000"
        self.results = {}
    
    async def setup(self):
        """Initialize backend and create test data"""
        await self.backend.initialize()
        
        # Clean test data
        async with self.backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'benchmark_v42'")
        
        print("🚀 Setting up benchmark data...")
        
        # Create test memories with embeddings
        self.test_memories = []
        self.test_embeddings = []
        
        for i in range(100):
            embedding = np.random.rand(1536).tolist()
            memory = await self.backend.create_memory({
                "content": f"Benchmark test memory {i} with various content for testing search performance",
                "memory_type": "test" if i % 2 == 0 else "benchmark",
                "importance_score": i / 100,
                "tags": [f"tag{i % 10}", "benchmark", "v42"],
                "container_id": "benchmark_v42"
            }, embedding)
            
            self.test_memories.append(memory)
            self.test_embeddings.append(embedding)
            
            if (i + 1) % 20 == 0:
                print(f"  Created {i + 1} test memories...")
        
        print("✅ Benchmark data ready\n")
    
    async def benchmark_vector_search(self, iterations: int = 50):
        """Benchmark vector similarity search"""
        print("📊 Benchmarking Vector Search...")
        
        times = []
        for i in range(iterations):
            # Use random embedding from test set
            query_embedding = self.test_embeddings[i % len(self.test_embeddings)]
            
            start = time.perf_counter()
            results = await self.backend.vector_search(
                embedding=query_embedding,
                limit=10,
                min_similarity=0.5,
                container_id="benchmark_v42"
            )
            end = time.perf_counter()
            
            times.append((end - start) * 1000)  # Convert to ms
        
        self.results["vector_search"] = {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['vector_search']['mean_ms']:.2f}ms")
        print(f"  P95: {self.results['vector_search']['p95_ms']:.2f}ms")
        print(f"  P99: {self.results['vector_search']['p99_ms']:.2f}ms\n")
    
    async def benchmark_text_search(self, iterations: int = 50):
        """Benchmark full-text search"""
        print("📊 Benchmarking Text Search...")
        
        queries = ["test", "benchmark", "memory", "content", "performance"]
        times = []
        
        for i in range(iterations):
            query = queries[i % len(queries)]
            
            start = time.perf_counter()
            results = await self.backend.text_search(
                query=query,
                limit=10,
                container_id="benchmark_v42"
            )
            end = time.perf_counter()
            
            times.append((end - start) * 1000)
        
        self.results["text_search"] = {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['text_search']['mean_ms']:.2f}ms")
        print(f"  P95: {self.results['text_search']['p95_ms']:.2f}ms")
        print(f"  P99: {self.results['text_search']['p99_ms']:.2f}ms\n")
    
    async def benchmark_hybrid_search(self, iterations: int = 50):
        """Benchmark hybrid search"""
        print("📊 Benchmarking Hybrid Search...")
        
        queries = ["test memory", "benchmark content", "search performance"]
        times = []
        
        for i in range(iterations):
            query = queries[i % len(queries)]
            embedding = self.test_embeddings[i % len(self.test_embeddings)]
            
            start = time.perf_counter()
            results = await self.backend.hybrid_search(
                query=query,
                embedding=embedding,
                limit=10,
                vector_weight=0.6,
                container_id="benchmark_v42"
            )
            end = time.perf_counter()
            
            times.append((end - start) * 1000)
        
        self.results["hybrid_search"] = {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
        
        print(f"  Mean: {self.results['hybrid_search']['mean_ms']:.2f}ms")
        print(f"  P95: {self.results['hybrid_search']['p95_ms']:.2f}ms")
        print(f"  P99: {self.results['hybrid_search']['p99_ms']:.2f}ms\n")
    
    async def benchmark_api_endpoints(self, iterations: int = 20):
        """Benchmark API endpoints"""
        print("📊 Benchmarking API Endpoints...")
        
        async with httpx.AsyncClient() as client:
            # Memory creation
            create_times = []
            for i in range(iterations):
                memory_data = {
                    "content": f"API benchmark test {i}",
                    "memory_type": "benchmark",
                    "importance_score": 0.5,
                    "tags": ["api", "benchmark"]
                }
                
                start = time.perf_counter()
                response = await client.post(
                    f"{self.api_base}/api/v2/memories/",
                    json=memory_data
                )
                end = time.perf_counter()
                
                if response.status_code == 201:
                    create_times.append((end - start) * 1000)
            
            # Vector search API
            search_times = []
            for i in range(iterations):
                search_data = {
                    "query": "benchmark test",
                    "limit": 10,
                    "min_similarity": 0.5
                }
                
                start = time.perf_counter()
                response = await client.post(
                    f"{self.api_base}/api/v2/search/vector",
                    json=search_data
                )
                end = time.perf_counter()
                
                if response.status_code == 200:
                    search_times.append((end - start) * 1000)
            
            self.results["api_create"] = {
                "mean_ms": statistics.mean(create_times) if create_times else 0,
                "p95_ms": np.percentile(create_times, 95) if create_times else 0,
                "p99_ms": np.percentile(create_times, 99) if create_times else 0
            }
            
            self.results["api_search"] = {
                "mean_ms": statistics.mean(search_times) if search_times else 0,
                "p95_ms": np.percentile(search_times, 95) if search_times else 0,
                "p99_ms": np.percentile(search_times, 99) if search_times else 0
            }
        
        print(f"  Create Memory - Mean: {self.results['api_create']['mean_ms']:.2f}ms")
        print(f"  Vector Search - Mean: {self.results['api_search']['mean_ms']:.2f}ms\n")
    
    async def benchmark_scalability(self):
        """Test performance with different dataset sizes"""
        print("📊 Testing Scalability...")
        
        sizes = [100, 500, 1000]
        scalability_results = {}
        
        for size in sizes:
            # Add more test data
            while len(self.test_memories) < size:
                embedding = np.random.rand(1536).tolist()
                memory = await self.backend.create_memory({
                    "content": f"Scalability test memory {len(self.test_memories)}",
                    "container_id": "benchmark_v42"
                }, embedding)
                self.test_memories.append(memory)
                self.test_embeddings.append(embedding)
            
            # Test vector search at this size
            times = []
            for _ in range(20):
                embedding = self.test_embeddings[0]
                start = time.perf_counter()
                await self.backend.vector_search(
                    embedding=embedding,
                    limit=10,
                    container_id="benchmark_v42"
                )
                end = time.perf_counter()
                times.append((end - start) * 1000)
            
            scalability_results[size] = {
                "mean_ms": statistics.mean(times),
                "p95_ms": np.percentile(times, 95)
            }
            
            print(f"  {size} memories - Mean: {scalability_results[size]['mean_ms']:.2f}ms")
        
        self.results["scalability"] = scalability_results
        print()
    
    async def cleanup(self):
        """Clean up test data"""
        print("🧹 Cleaning up benchmark data...")
        async with self.backend.acquire() as conn:
            await conn.execute("DELETE FROM memories WHERE container_id = 'benchmark_v42'")
        await self.backend.close()
    
    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 60)
        print("📊 BENCHMARK SUMMARY - Second Brain v4.2.0")
        print("=" * 60)
        
        print("\n🔍 Search Performance:")
        print(f"  Vector Search: {self.results['vector_search']['mean_ms']:.2f}ms (mean), "
              f"{self.results['vector_search']['p95_ms']:.2f}ms (p95)")
        print(f"  Text Search: {self.results['text_search']['mean_ms']:.2f}ms (mean), "
              f"{self.results['text_search']['p95_ms']:.2f}ms (p95)")
        print(f"  Hybrid Search: {self.results['hybrid_search']['mean_ms']:.2f}ms (mean), "
              f"{self.results['hybrid_search']['p95_ms']:.2f}ms (p95)")
        
        print("\n🌐 API Performance:")
        print(f"  Create Memory: {self.results['api_create']['mean_ms']:.2f}ms (mean)")
        print(f"  Vector Search: {self.results['api_search']['mean_ms']:.2f}ms (mean)")
        
        print("\n📈 Scalability:")
        for size, metrics in self.results["scalability"].items():
            print(f"  {size} memories: {metrics['mean_ms']:.2f}ms (mean)")
        
        print("\n✅ Performance Targets:")
        print("  ✓ Sub-100ms search latency" if self.results['vector_search']['p95_ms'] < 100 else "  ✗ Search latency > 100ms")
        print("  ✓ Linear scalability" if self.results['scalability'][1000]['mean_ms'] < self.results['scalability'][100]['mean_ms'] * 2 else "  ✗ Non-linear scalability")
        
        print("\n" + "=" * 60)


async def main():
    """Run all benchmarks"""
    print("🚀 Second Brain v4.2.0 Performance Benchmark")
    print("=" * 60)
    print(f"Started at: {datetime.now()}\n")
    
    benchmark = V42Benchmark()
    
    try:
        await benchmark.setup()
        await benchmark.benchmark_vector_search()
        await benchmark.benchmark_text_search()
        await benchmark.benchmark_hybrid_search()
        await benchmark.benchmark_api_endpoints()
        await benchmark.benchmark_scalability()
        
        benchmark.print_summary()
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await benchmark.cleanup()
    
    print(f"\nCompleted at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())