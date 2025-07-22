#!/usr/bin/env python3
"""
Performance Benchmarking Suite for Second Brain v2.2.0
Comprehensive performance testing and monitoring setup
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any

import httpx
import psutil
import pytest

from app.database_mock import MockDatabase


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""

    response_time: float
    memory_usage: float
    cpu_usage: float
    database_connections: int
    error_rate: float
    throughput: float


@dataclass
class BenchmarkResult:
    """Benchmark test result"""

    test_name: str
    endpoint: str
    method: str
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    error_rate: float
    success_rate: float
    memory_usage: float
    cpu_usage: float
    total_requests: int
    passed: bool


class PerformanceBenchmark:
    """Performance benchmarking system"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: list[BenchmarkResult] = []
        self.api_key = "test-performance-key"

    async def run_benchmark_suite(self) -> dict[str, Any]:
        """Run complete performance benchmark suite"""
        print("🚀 Starting Performance Benchmark Suite")

        # Start performance monitoring

        # Run individual benchmarks
        await self._benchmark_health_endpoint()
        await self._benchmark_memory_storage()
        await self._benchmark_memory_search()
        await self._benchmark_memory_retrieval()
        await self._benchmark_concurrent_requests()
        await self._benchmark_database_operations()

        # Generate report
        return self._generate_performance_report()

    async def _benchmark_health_endpoint(self):
        """Benchmark health endpoint performance"""
        print("📊 Benchmarking health endpoint...")

        response_times = []
        errors = 0

        async with httpx.AsyncClient() as client:
            for _ in range(100):
                start_time = time.time()
                try:
                    response = await client.get(f"{self.base_url}/health")
                    response_time = time.time() - start_time
                    response_times.append(response_time)

                    if response.status_code != 200:
                        errors += 1

                except Exception as e:
                    errors += 1
                    print(f"Error in health benchmark: {e}")

        if response_times:
            result = BenchmarkResult(
                test_name="Health Endpoint",
                endpoint="/health",
                method="GET",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / sum(response_times),
                error_rate=errors / 100,
                success_rate=(100 - errors) / 100,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=100,
                passed=statistics.mean(response_times) < 0.1,  # Target: <100ms
            )
            self.results.append(result)

    async def _benchmark_memory_storage(self):
        """Benchmark memory storage performance"""
        print("💾 Benchmarking memory storage...")

        response_times = []
        errors = 0

        async with httpx.AsyncClient() as client:
            for i in range(50):
                start_time = time.time()
                try:
                    response = await client.post(
                        f"{self.base_url}/memories",
                        params={"api_key": self.api_key},
                        json={
                            "content": f"Performance test memory {i}",
                            "metadata": {"test": "performance", "index": i},
                        },
                    )
                    response_time = time.time() - start_time
                    response_times.append(response_time)

                    if response.status_code != 200:
                        errors += 1

                except Exception as e:
                    errors += 1
                    print(f"Error in storage benchmark: {e}")

        if response_times:
            result = BenchmarkResult(
                test_name="Memory Storage",
                endpoint="/memories",
                method="POST",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / sum(response_times),
                error_rate=errors / 50,
                success_rate=(50 - errors) / 50,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=50,
                passed=statistics.mean(response_times) < 0.5,  # Target: <500ms
            )
            self.results.append(result)

    async def _benchmark_memory_search(self):
        """Benchmark memory search performance"""
        print("🔍 Benchmarking memory search...")

        response_times = []
        errors = 0

        async with httpx.AsyncClient() as client:
            for i in range(100):
                start_time = time.time()
                try:
                    response = await client.post(
                        f"{self.base_url}/memories/search",
                        params={"api_key": self.api_key},
                        json={"query": f"performance test {i % 10}", "limit": 10},
                    )
                    response_time = time.time() - start_time
                    response_times.append(response_time)

                    if response.status_code != 200:
                        errors += 1

                except Exception as e:
                    errors += 1
                    print(f"Error in search benchmark: {e}")

        if response_times:
            result = BenchmarkResult(
                test_name="Memory Search",
                endpoint="/memories/search",
                method="POST",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / sum(response_times),
                error_rate=errors / 100,
                success_rate=(100 - errors) / 100,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=100,
                passed=statistics.mean(response_times) < 0.1,  # Target: <100ms
            )
            self.results.append(result)

    async def _benchmark_memory_retrieval(self):
        """Benchmark memory retrieval performance"""
        print("📤 Benchmarking memory retrieval...")

        response_times = []
        errors = 0

        async with httpx.AsyncClient() as client:
            for _ in range(100):
                start_time = time.time()
                try:
                    response = await client.get(
                        f"{self.base_url}/memories", params={"api_key": self.api_key, "limit": 10}
                    )
                    response_time = time.time() - start_time
                    response_times.append(response_time)

                    if response.status_code != 200:
                        errors += 1

                except Exception as e:
                    errors += 1
                    print(f"Error in retrieval benchmark: {e}")

        if response_times:
            result = BenchmarkResult(
                test_name="Memory Retrieval",
                endpoint="/memories",
                method="GET",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / sum(response_times),
                error_rate=errors / 100,
                success_rate=(100 - errors) / 100,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=100,
                passed=statistics.mean(response_times) < 0.1,  # Target: <100ms
            )
            self.results.append(result)

    async def _benchmark_concurrent_requests(self):
        """Benchmark concurrent request handling"""
        print("🔄 Benchmarking concurrent requests...")

        async def make_request(client: httpx.AsyncClient, i: int):
            start_time = time.time()
            try:
                response = await client.get(f"{self.base_url}/health")
                return time.time() - start_time, response.status_code == 200
            except Exception:
                return time.time() - start_time, False

        async with httpx.AsyncClient() as client:
            tasks = [make_request(client, i) for i in range(50)]
            results = await asyncio.gather(*tasks)

            response_times = [r[0] for r in results]
            successes = [r[1] for r in results]
            errors = len([s for s in successes if not s])

        if response_times:
            result = BenchmarkResult(
                test_name="Concurrent Requests",
                endpoint="/health",
                method="GET",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / max(response_times),
                error_rate=errors / 50,
                success_rate=(50 - errors) / 50,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=50,
                passed=statistics.mean(response_times) < 0.2,  # Target: <200ms under load
            )
            self.results.append(result)

    async def _benchmark_database_operations(self):
        """Benchmark database operations"""
        print("🗄️ Benchmarking database operations...")

        # This would require database connection
        # For now, we'll simulate with mock database
        mock_db = MockDatabase()
        await mock_db.initialize()

        response_times = []

        for i in range(100):
            start_time = time.time()
            try:
                await mock_db.store_memory(f"Database benchmark test {i}", {"benchmark": True})
                response_time = time.time() - start_time
                response_times.append(response_time)
            except Exception as e:
                print(f"Database benchmark error: {e}")

        if response_times:
            result = BenchmarkResult(
                test_name="Database Operations",
                endpoint="database",
                method="INSERT",
                avg_response_time=statistics.mean(response_times),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                p95_response_time=self._percentile(response_times, 95),
                p99_response_time=self._percentile(response_times, 99),
                throughput=len(response_times) / sum(response_times),
                error_rate=0.0,
                success_rate=1.0,
                memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage=psutil.Process().cpu_percent(),
                total_requests=100,
                passed=statistics.mean(response_times) < 0.05,  # Target: <50ms
            )
            self.results.append(result)

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _generate_performance_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report"""
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.passed])

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "overall_performance": "PASS" if passed_tests >= total_tests * 0.8 else "FAIL",
            },
            "performance_targets": {
                "health_endpoint": "<100ms",
                "memory_storage": "<500ms",
                "memory_search": "<100ms",
                "memory_retrieval": "<100ms",
                "concurrent_requests": "<200ms",
                "database_operations": "<50ms",
            },
            "results": [],
        }

        for result in self.results:
            report["results"].append(
                {
                    "test_name": result.test_name,
                    "endpoint": result.endpoint,
                    "method": result.method,
                    "avg_response_time_ms": result.avg_response_time * 1000,
                    "p95_response_time_ms": result.p95_response_time * 1000,
                    "p99_response_time_ms": result.p99_response_time * 1000,
                    "throughput_rps": result.throughput,
                    "error_rate": result.error_rate,
                    "success_rate": result.success_rate,
                    "memory_usage_mb": result.memory_usage,
                    "cpu_usage_percent": result.cpu_usage,
                    "total_requests": result.total_requests,
                    "status": "PASS" if result.passed else "FAIL",
                }
            )

        return report

    def save_report(self, report: dict[str, Any], filepath: str = "performance_report.json"):
        """Save performance report to file"""
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"📊 Performance report saved to {filepath}")

    def print_report(self, report: dict[str, Any]):
        """Print performance report to console"""
        print("\n" + "=" * 60)
        print("🚀 PERFORMANCE BENCHMARK REPORT")
        print("=" * 60)
        print(f"Overall Performance: {report['summary']['overall_performance']}")
        print(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1%}")
        print("\n" + "-" * 60)
        print("📊 INDIVIDUAL TEST RESULTS")
        print("-" * 60)

        for result in report["results"]:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {result['test_name']}")
            print(f"   Avg Response: {result['avg_response_time_ms']:.1f}ms")
            print(f"   P95 Response: {result['p95_response_time_ms']:.1f}ms")
            print(f"   Throughput: {result['throughput_rps']:.1f} req/s")
            print(f"   Success Rate: {result['success_rate']:.1%}")
            print()


async def main():
    """Main benchmarking function"""
    benchmark = PerformanceBenchmark()

    # Run benchmark suite
    report = await benchmark.run_benchmark_suite()

    # Print and save results
    benchmark.print_report(report)
    benchmark.save_report(report)

    return report


# Pytest test functions
@pytest.mark.asyncio
async def test_performance_benchmarking():
    """Test that performance benchmarking functionality works."""
    # Test basic benchmark class instantiation
    benchmark = PerformanceBenchmark()
    assert benchmark.base_url == "http://localhost:8000"
    assert benchmark.api_key == "test-performance-key"
    assert isinstance(benchmark.results, list)


@pytest.mark.asyncio
async def test_benchmark_metrics_structure():
    """Test that benchmark result structure is correct."""
    # Create a test result
    result = BenchmarkResult(
        test_name="Test",
        endpoint="/test",
        method="GET",
        avg_response_time=0.1,
        min_response_time=0.05,
        max_response_time=0.2,
        p95_response_time=0.15,
        p99_response_time=0.18,
        throughput=100.0,
        error_rate=0.0,
        success_rate=1.0,
        memory_usage=50.0,
        cpu_usage=10.0,
        total_requests=100,
        passed=True,
    )

    assert result.test_name == "Test"
    assert result.avg_response_time == 0.1
    assert result.passed


@pytest.mark.asyncio
async def test_percentile_calculation():
    """Test percentile calculation function."""
    benchmark = PerformanceBenchmark()

    # Test with sample data
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    p50 = benchmark._percentile(data, 50)
    p95 = benchmark._percentile(data, 95)
    p99 = benchmark._percentile(data, 99)

    assert p50 >= 5.0  # 50th percentile should be around middle
    assert p95 >= 9.0  # 95th percentile should be near top
    assert p99 >= 9.0  # 99th percentile should be near top


if __name__ == "__main__":
    # Run performance benchmarks
    asyncio.run(main())
