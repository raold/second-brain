"""
Test script for Second Brain performance optimizations.
Verifies cache functionality, database performance, and monitoring endpoints.
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx
import pytest


class PerformanceOptimizationTester:
    """Test suite for performance optimization features."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_token: str = "test-token"):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Test enhanced health endpoint with database metrics."""
        print("🔍 Testing enhanced health endpoint...")
        
        response = await self.client.get(f"{self.base_url}/health", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Health endpoint failed: {response.status_code}")
        
        health_data = response.json()
        print(f"✅ Health endpoint working: {health_data.get('status', 'unknown')}")
        
        # Check for database health information
        if 'database' in health_data:
            print(f"   📊 Database status: {health_data['database'].get('status', 'unknown')}")
        
        return health_data
    
    async def test_performance_endpoint(self) -> Dict[str, Any]:
        """Test comprehensive performance statistics endpoint."""
        print("📈 Testing performance statistics endpoint...")
        
        response = await self.client.get(f"{self.base_url}/performance", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Performance endpoint failed: {response.status_code}")
        
        perf_data = response.json()
        print(f"✅ Performance endpoint working")
        print(f"   🎯 System health score: {perf_data.get('system_health_score', 'N/A')}")
        
        # Check cache performance
        cache_perf = perf_data.get('cache_performance', {})
        if cache_perf:
            summary = cache_perf.get('_summary', {})
            hit_rate = summary.get('overall_hit_rate_percent', 0)
            print(f"   💾 Overall cache hit rate: {hit_rate:.1f}%")
        
        # Check database performance
        db_perf = perf_data.get('database_performance', {})
        if db_perf:
            postgres_status = db_perf.get('postgresql', {}).get('health', {}).get('status', 'unknown')
            qdrant_status = db_perf.get('qdrant', {}).get('status', 'unknown')
            print(f"   🗄️  PostgreSQL: {postgres_status}, Qdrant: {qdrant_status}")
        
        return perf_data
    
    async def test_cache_endpoint(self) -> Dict[str, Any]:
        """Test cache statistics endpoint."""
        print("💾 Testing cache statistics endpoint...")
        
        response = await self.client.get(f"{self.base_url}/performance/cache", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Cache endpoint failed: {response.status_code}")
        
        cache_data = response.json()
        print(f"✅ Cache endpoint working")
        
        # Analyze cache statistics
        analysis = cache_data.get('analysis', {})
        hit_rate = analysis.get('total_cache_hit_rate', 0)
        efficiency = analysis.get('cache_efficiency', {}).get('overall_efficiency', 'unknown')
        
        print(f"   📊 Cache hit rate: {hit_rate:.1f}%")
        print(f"   ⚡ Cache efficiency: {efficiency}")
        
        return cache_data
    
    async def test_database_performance_endpoint(self) -> Dict[str, Any]:
        """Test database performance endpoint."""
        print("🗄️  Testing database performance endpoint...")
        
        response = await self.client.get(f"{self.base_url}/performance/database", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Database performance endpoint failed: {response.status_code}")
        
        db_data = response.json()
        print(f"✅ Database performance endpoint working")
        
        # Check PostgreSQL metrics
        postgres_data = db_data.get('postgresql', {})
        if postgres_data:
            status = postgres_data.get('status', 'unknown')
            pool_util = postgres_data.get('connection_pool_utilization', {})
            util_percent = pool_util.get('utilization_percent', 0)
            print(f"   🐘 PostgreSQL: {status} (Pool: {util_percent:.1f}%)")
        
        # Check Qdrant metrics
        qdrant_data = db_data.get('qdrant', {})
        if qdrant_data:
            status = qdrant_data.get('status', 'unknown')
            print(f"   🔍 Qdrant: {status}")
        
        return db_data
    
    async def test_recommendations_endpoint(self) -> Dict[str, Any]:
        """Test performance recommendations endpoint."""
        print("💡 Testing performance recommendations endpoint...")
        
        response = await self.client.get(f"{self.base_url}/performance/recommendations", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Recommendations endpoint failed: {response.status_code}")
        
        rec_data = response.json()
        print(f"✅ Recommendations endpoint working")
        
        # Show priority actions
        priority_actions = rec_data.get('priority_actions', [])
        if priority_actions:
            print(f"   🚨 Priority actions:")
            for action in priority_actions[:3]:  # Show top 3
                priority = action.get('priority', 'unknown')
                desc = action.get('action', 'Unknown action')
                print(f"      [{priority}] {desc}")
        
        return rec_data
    
    async def test_cache_clearing(self) -> Dict[str, Any]:
        """Test cache clearing functionality."""
        print("🧹 Testing cache clearing endpoint...")
        
        response = await self.client.post(f"{self.base_url}/performance/cache/clear", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Cache clear endpoint failed: {response.status_code}")
        
        clear_data = response.json()
        print(f"✅ Cache clearing working: {clear_data.get('status', 'unknown')}")
        
        return clear_data
    
    async def test_memory_operations_with_caching(self) -> Dict[str, Any]:
        """Test memory operations to verify caching is working."""
        print("🧠 Testing memory operations with caching...")
        
        # Create a test memory
        test_payload = {
            "id": f"test-perf-{int(time.time())}",
            "context": "performance_testing",
            "ttl": "1h",
            "data": {
                "note": "This is a test memory for performance optimization testing. How fast can we retrieve this?"
            },
            "type": "note",
            "priority": "normal",
            "meta": {
                "source": "performance_test",
                "test_run": True
            }
        }
        
        # Ingest the memory
        start_time = time.time()
        response = await self.client.post(
            f"{self.base_url}/ingest",
            headers=self.headers,
            json=test_payload
        )
        ingest_time = time.time() - start_time
        
        if response.status_code != 200:
            raise Exception(f"Memory ingest failed: {response.status_code}")
        
        ingest_data = response.json()
        print(f"   ✅ Memory ingested in {ingest_time:.2f}s")
        
        # Search for the memory multiple times to test caching
        search_query = "performance optimization testing"
        times = []
        
        for i in range(3):
            start_time = time.time()
            search_response = await self.client.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params={"q": search_query}
            )
            search_time = time.time() - start_time
            times.append(search_time)
            
            if search_response.status_code != 200:
                raise Exception(f"Search failed: {search_response.status_code}")
        
        print(f"   🔍 Search times: {[f'{t:.3f}s' for t in times]}")
        
        # Verify caching is working (subsequent searches should be faster)
        if len(times) >= 2 and times[1] < times[0]:
            print(f"   ⚡ Cache acceleration detected!")
        
        return {
            "ingest_time": ingest_time,
            "search_times": times,
            "cache_working": len(times) >= 2 and times[1] < times[0]
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all performance optimization tests."""
        print("🚀 Starting comprehensive performance optimization tests...\n")
        
        results = {
            "timestamp": time.time(),
            "tests_passed": 0,
            "tests_failed": 0,
            "results": {}
        }
        
        tests = [
            ("health", self.test_health_endpoint),
            ("performance", self.test_performance_endpoint),
            ("cache", self.test_cache_endpoint),
            ("database", self.test_database_performance_endpoint),
            ("recommendations", self.test_recommendations_endpoint),
            ("memory_operations", self.test_memory_operations_with_caching),
            ("cache_clearing", self.test_cache_clearing),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*50}")
                test_result = await test_func()
                results["results"][test_name] = {
                    "status": "passed",
                    "data": test_result
                }
                results["tests_passed"] += 1
                print(f"✅ {test_name} test passed")
                
            except Exception as e:
                results["results"][test_name] = {
                    "status": "failed",
                    "error": str(e)
                }
                results["tests_failed"] += 1
                print(f"❌ {test_name} test failed: {e}")
        
        print(f"\n{'='*50}")
        print(f"🎯 Test Summary:")
        print(f"   ✅ Passed: {results['tests_passed']}")
        print(f"   ❌ Failed: {results['tests_failed']}")
        print(f"   📊 Success Rate: {results['tests_passed']/(results['tests_passed']+results['tests_failed'])*100:.1f}%")
        
        return results


async def main():
    """Main test function."""
    async with PerformanceOptimizationTester() as tester:
        results = await tester.run_comprehensive_test()
        
        # Save results to file
        with open("performance_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to performance_test_results.json")
        
        # Return exit code based on results
        if results["tests_failed"] > 0:
            exit(1)
        else:
            print("\n🎉 All performance optimization tests passed!")
            exit(0)


if __name__ == "__main__":
    asyncio.run(main()) 