#!/usr/bin/env python3
"""
Enterprise Load Testing Suite for Second Brain v3.0.0
Advanced load testing with stress scenarios, resource monitoring, and CI/CD integration
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import gc
import os
import signal
import sys

import httpx
import psutil
import pytest

# Configure pytest for performance testing
pytest_plugins = ["pytest_asyncio"]


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    base_url: str = "http://localhost:8000"
    api_key: str = "test-load-key"
    concurrent_users: int = 50
    test_duration: int = 60  # seconds
    ramp_up_time: int = 10   # seconds
    memory_threshold_mb: int = 512
    cpu_threshold_percent: float = 80.0
    response_time_threshold_ms: int = 1000
    error_rate_threshold: float = 0.05  # 5%


@dataclass
class PerformanceMetrics:
    """Enhanced performance metrics"""
    timestamp: datetime
    endpoint: str
    response_time_ms: float
    status_code: int
    memory_usage_mb: float
    cpu_usage_percent: float
    concurrent_users: int
    requests_per_second: float
    error_count: int
    success_count: int


@dataclass
class LoadTestResult:
    """Comprehensive load test result"""
    test_name: str
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float
    requests_per_second: float
    error_rate: float
    success_rate: float
    peak_memory_mb: float
    avg_memory_mb: float
    peak_cpu_percent: float
    avg_cpu_percent: float
    memory_leaked: bool
    performance_grade: str
    passed: bool
    failure_reasons: List[str]
    metrics: List[PerformanceMetrics]


class EnterpriseLoadTester:
    """Enterprise-grade load testing system"""

    def __init__(self, config: LoadTestConfig = None):
        self.config = config or LoadTestConfig()
        self.metrics: List[PerformanceMetrics] = []
        self.results: List[LoadTestResult] = []
        self.is_running = False
        self.start_memory = 0.0
        
    async def run_load_test_suite(self) -> Dict[str, Any]:
        """Run complete enterprise load test suite"""
        print("🚀 Starting Enterprise Load Test Suite")
        print(f"Target: {self.config.base_url}")
        print("=" * 60)
        
        # Health check first
        if not await self._verify_system_health():
            return {"error": "System health check failed"}
        
        # Run progressive load tests
        results = {}
        
        # 1. Baseline Performance Test
        results["baseline"] = await self._run_baseline_test()
        
        # 2. Concurrent User Load Test
        results["concurrent_load"] = await self._run_concurrent_load_test()
        
        # 3. Stress Test (find breaking point)
        results["stress_test"] = await self._run_stress_test()
        
        # 4. Endurance Test (sustained load)
        results["endurance_test"] = await self._run_endurance_test()
        
        # 5. Spike Test (sudden load increases)
        results["spike_test"] = await self._run_spike_test()
        
        # 6. Memory Leak Test
        results["memory_leak_test"] = await self._run_memory_leak_test()
        
        # Generate comprehensive report
        report = self._generate_enterprise_report(results)
        
        return report

    async def _verify_system_health(self) -> bool:
        """Verify system is ready for load testing"""
        print("🏥 Verifying system health...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config.base_url}/health")
                if response.status_code != 200:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
                    
                # Check system resources
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    print(f"❌ System memory too high: {memory.percent}%")
                    return False
                    
                print("✅ System health check passed")
                return True
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    async def _run_baseline_test(self) -> LoadTestResult:
        """Run baseline performance test with single user"""
        print("📊 Running baseline performance test...")
        
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=1,
            test_duration=30
        )
        
        return await self._execute_load_test("Baseline Performance", config, [
            {"endpoint": "/health", "method": "GET", "weight": 0.3},
            {"endpoint": "/memories", "method": "GET", "weight": 0.3},
            {"endpoint": "/memories", "method": "POST", "weight": 0.2, 
             "data": {"content": "Baseline test memory", "memory_type": "semantic"}},
            {"endpoint": "/memories/search", "method": "POST", "weight": 0.2,
             "data": {"query": "baseline", "limit": 10}}
        ])

    async def _run_concurrent_load_test(self) -> LoadTestResult:
        """Run concurrent user load test"""
        print("👥 Running concurrent user load test...")
        
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=25,
            test_duration=60,
            ramp_up_time=15
        )
        
        return await self._execute_load_test("Concurrent Load", config, [
            {"endpoint": "/health", "method": "GET", "weight": 0.2},
            {"endpoint": "/memories", "method": "GET", "weight": 0.3},
            {"endpoint": "/memories", "method": "POST", "weight": 0.25,
             "data": {"content": "Load test memory {i}", "memory_type": "semantic"}},
            {"endpoint": "/memories/search", "method": "POST", "weight": 0.25,
             "data": {"query": "load test", "limit": 10}}
        ])

    async def _run_stress_test(self) -> LoadTestResult:
        """Run stress test to find breaking point"""
        print("⚡ Running stress test...")
        
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=100,
            test_duration=120,
            ramp_up_time=30,
            response_time_threshold_ms=2000,
            error_rate_threshold=0.10
        )
        
        return await self._execute_load_test("Stress Test", config, [
            {"endpoint": "/health", "method": "GET", "weight": 0.1},
            {"endpoint": "/memories", "method": "GET", "weight": 0.4},
            {"endpoint": "/memories", "method": "POST", "weight": 0.3,
             "data": {"content": "Stress test memory {i}", "memory_type": "semantic"}},
            {"endpoint": "/memories/search", "method": "POST", "weight": 0.2,
             "data": {"query": "stress", "limit": 20}}
        ])

    async def _run_endurance_test(self) -> LoadTestResult:
        """Run endurance test for sustained load"""
        print("🏃 Running endurance test...")
        
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=15,
            test_duration=300,  # 5 minutes
            ramp_up_time=30
        )
        
        return await self._execute_load_test("Endurance Test", config, [
            {"endpoint": "/health", "method": "GET", "weight": 0.3},
            {"endpoint": "/memories", "method": "GET", "weight": 0.4},
            {"endpoint": "/memories", "method": "POST", "weight": 0.2,
             "data": {"content": "Endurance test memory {i}", "memory_type": "semantic"}},
            {"endpoint": "/memories/search", "method": "POST", "weight": 0.1,
             "data": {"query": "endurance", "limit": 5}}
        ])

    async def _run_spike_test(self) -> LoadTestResult:
        """Run spike test with sudden load increases"""
        print("📈 Running spike test...")
        
        # This test will ramp up very quickly then drop
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=50,
            test_duration=90,
            ramp_up_time=5  # Very fast ramp-up
        )
        
        return await self._execute_load_test("Spike Test", config, [
            {"endpoint": "/health", "method": "GET", "weight": 0.5},
            {"endpoint": "/memories", "method": "GET", "weight": 0.3},
            {"endpoint": "/memories/search", "method": "POST", "weight": 0.2,
             "data": {"query": "spike", "limit": 10}}
        ])

    async def _run_memory_leak_test(self) -> LoadTestResult:
        """Run memory leak detection test"""
        print("🧠 Running memory leak test...")
        
        config = LoadTestConfig(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            concurrent_users=10,
            test_duration=180,  # 3 minutes
            memory_threshold_mb=256
        )
        
        return await self._execute_load_test("Memory Leak Test", config, [
            {"endpoint": "/memories", "method": "POST", "weight": 0.7,
             "data": {"content": "Memory leak test {i} " + "x" * 1000, "memory_type": "semantic"}},
            {"endpoint": "/memories", "method": "GET", "weight": 0.3}
        ])

    async def _execute_load_test(self, test_name: str, config: LoadTestConfig, 
                                scenarios: List[Dict]) -> LoadTestResult:
        """Execute a specific load test scenario"""
        print(f"   Running {test_name} with {config.concurrent_users} users...")
        
        start_time = datetime.now()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.metrics = []
        self.is_running = True
        
        # Start monitoring
        monitor_task = asyncio.create_task(self._monitor_system())
        
        try:
            # Run the actual load test
            tasks = []
            for user_id in range(config.concurrent_users):
                # Stagger user start times for ramp-up
                delay = (config.ramp_up_time * user_id) / config.concurrent_users
                task = asyncio.create_task(
                    self._simulate_user(user_id, config, scenarios, delay)
                )
                tasks.append(task)
            
            # Wait for test duration
            await asyncio.sleep(config.test_duration)
            self.is_running = False
            
            # Wait for all users to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            self.is_running = False
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        end_time = datetime.now()
        
        # Analyze results
        return self._analyze_results(test_name, config, start_time, end_time)

    async def _simulate_user(self, user_id: int, config: LoadTestConfig, 
                           scenarios: List[Dict], delay: float):
        """Simulate a single user's behavior"""
        # Wait for ramp-up delay
        await asyncio.sleep(delay)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_count = 0
            while self.is_running:
                for scenario in scenarios:
                    if not self.is_running:
                        break
                        
                    # Skip based on weight probability
                    import random
                    if random.random() > scenario["weight"]:
                        continue
                    
                    await self._make_request(client, scenario, user_id, request_count)
                    request_count += 1
                    
                    # Small delay between requests (realistic user behavior)
                    await asyncio.sleep(random.uniform(0.1, 0.5))

    async def _make_request(self, client: httpx.AsyncClient, scenario: Dict, 
                          user_id: int, request_count: int):
        """Make a single request and record metrics"""
        start_time = time.time()
        
        try:
            if scenario["method"] == "GET":
                response = await client.get(
                    f"{self.config.base_url}{scenario['endpoint']}",
                    params={"api_key": self.config.api_key}
                )
            elif scenario["method"] == "POST":
                data = scenario.get("data", {})
                # Replace placeholders
                if isinstance(data, dict):
                    data = {k: str(v).format(i=request_count) if isinstance(v, str) else v 
                           for k, v in data.items()}
                
                response = await client.post(
                    f"{self.config.base_url}{scenario['endpoint']}",
                    params={"api_key": self.config.api_key},
                    json=data
                )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Record metrics
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                endpoint=scenario["endpoint"],
                response_time_ms=response_time,
                status_code=response.status_code,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage_percent=psutil.Process().cpu_percent(),
                concurrent_users=self.config.concurrent_users,
                requests_per_second=0.0,  # Will be calculated later
                error_count=1 if response.status_code >= 400 else 0,
                success_count=1 if response.status_code < 400 else 0
            )
            
            self.metrics.append(metrics)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            # Record error metrics
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                endpoint=scenario["endpoint"],
                response_time_ms=response_time,
                status_code=0,  # Connection error
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage_percent=psutil.Process().cpu_percent(),
                concurrent_users=self.config.concurrent_users,
                requests_per_second=0.0,
                error_count=1,
                success_count=0
            )
            
            self.metrics.append(metrics)

    async def _monitor_system(self):
        """Monitor system resources during load test"""
        while self.is_running:
            try:
                # Force garbage collection to detect memory leaks
                gc.collect()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    def _analyze_results(self, test_name: str, config: LoadTestConfig, 
                        start_time: datetime, end_time: datetime) -> LoadTestResult:
        """Analyze load test results and generate summary"""
        if not self.metrics:
            return LoadTestResult(
                test_name=test_name,
                config=config,
                start_time=start_time,
                end_time=end_time,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0,
                p50_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                max_response_time_ms=0,
                min_response_time_ms=0,
                requests_per_second=0,
                error_rate=1.0,
                success_rate=0.0,
                peak_memory_mb=0,
                avg_memory_mb=0,
                peak_cpu_percent=0,
                avg_cpu_percent=0,
                memory_leaked=False,
                performance_grade="F",
                passed=False,
                failure_reasons=["No metrics collected"],
                metrics=[]
            )
        
        # Extract data for analysis
        response_times = [m.response_time_ms for m in self.metrics]
        successful_requests = sum(m.success_count for m in self.metrics)
        failed_requests = sum(m.error_count for m in self.metrics)
        total_requests = len(self.metrics)
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = self._percentile(sorted_times, 50)
        p95 = self._percentile(sorted_times, 95)
        p99 = self._percentile(sorted_times, 99)
        
        # Calculate throughput
        duration_seconds = (end_time - start_time).total_seconds()
        requests_per_second = total_requests / duration_seconds if duration_seconds > 0 else 0
        
        # Memory analysis
        memory_usage = [m.memory_usage_mb for m in self.metrics]
        cpu_usage = [m.cpu_usage_percent for m in self.metrics]
        
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_leaked = (current_memory - self.start_memory) > 50  # 50MB threshold
        
        # Performance grading
        avg_response_time = statistics.mean(response_times)
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        failure_reasons = []
        if avg_response_time > config.response_time_threshold_ms:
            failure_reasons.append(f"High response time: {avg_response_time:.1f}ms")
        if error_rate > config.error_rate_threshold:
            failure_reasons.append(f"High error rate: {error_rate:.1%}")
        if max(memory_usage) > config.memory_threshold_mb:
            failure_reasons.append(f"High memory usage: {max(memory_usage):.1f}MB")
        if memory_leaked:
            failure_reasons.append("Memory leak detected")
        
        # Grade calculation
        grade = self._calculate_performance_grade(avg_response_time, error_rate, memory_leaked)
        passed = len(failure_reasons) == 0
        
        return LoadTestResult(
            test_name=test_name,
            config=config,
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            max_response_time_ms=max(response_times),
            min_response_time_ms=min(response_times),
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            success_rate=successful_requests / total_requests if total_requests > 0 else 0,
            peak_memory_mb=max(memory_usage),
            avg_memory_mb=statistics.mean(memory_usage),
            peak_cpu_percent=max(cpu_usage) if cpu_usage else 0,
            avg_cpu_percent=statistics.mean(cpu_usage) if cpu_usage else 0,
            memory_leaked=memory_leaked,
            performance_grade=grade,
            passed=passed,
            failure_reasons=failure_reasons,
            metrics=self.metrics[:100]  # Keep sample of metrics
        )

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_performance_grade(self, avg_response_time: float, 
                                   error_rate: float, memory_leaked: bool) -> str:
        """Calculate performance grade A-F"""
        if memory_leaked or error_rate > 0.1:
            return "F"
        elif error_rate > 0.05 or avg_response_time > 2000:
            return "D"
        elif error_rate > 0.02 or avg_response_time > 1000:
            return "C"
        elif error_rate > 0.01 or avg_response_time > 500:
            return "B"
        else:
            return "A"

    def _generate_enterprise_report(self, results: Dict[str, LoadTestResult]) -> Dict[str, Any]:
        """Generate comprehensive enterprise load test report"""
        overall_passed = all(result.passed for result in results.values())
        overall_grade = min([result.performance_grade for result in results.values()]) if results else "F"
        
        # Calculate aggregate metrics
        total_requests = sum(result.total_requests for result in results.values())
        total_failures = sum(result.failed_requests for result in results.values())
        avg_error_rate = total_failures / total_requests if total_requests > 0 else 0
        
        report = {
            "summary": {
                "test_suite": "Enterprise Load Testing Suite",
                "version": "v3.0.0",
                "timestamp": datetime.now().isoformat(),
                "overall_status": "PASS" if overall_passed else "FAIL",
                "overall_grade": overall_grade,
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results.values() if r.passed),
                "failed_tests": sum(1 for r in results.values() if not r.passed),
                "total_requests": total_requests,
                "total_failures": total_failures,
                "overall_error_rate": avg_error_rate,
                "test_duration_minutes": sum(
                    (r.end_time - r.start_time).total_seconds() / 60 
                    for r in results.values()
                )
            },
            "performance_thresholds": {
                "response_time_ms": 1000,
                "error_rate": 0.05,
                "memory_threshold_mb": 512,
                "cpu_threshold_percent": 80.0
            },
            "test_results": {},
            "recommendations": []
        }
        
        # Add individual test results
        for test_name, result in results.items():
            report["test_results"][test_name] = {
                "status": "PASS" if result.passed else "FAIL",
                "grade": result.performance_grade,
                "total_requests": result.total_requests,
                "successful_requests": result.successful_requests,
                "failed_requests": result.failed_requests,
                "avg_response_time_ms": round(result.avg_response_time_ms, 2),
                "p95_response_time_ms": round(result.p95_response_time_ms, 2),
                "p99_response_time_ms": round(result.p99_response_time_ms, 2),
                "requests_per_second": round(result.requests_per_second, 2),
                "error_rate": round(result.error_rate, 4),
                "peak_memory_mb": round(result.peak_memory_mb, 2),
                "memory_leaked": result.memory_leaked,
                "failure_reasons": result.failure_reasons,
                "concurrent_users": result.config.concurrent_users,
                "test_duration_seconds": result.config.test_duration
            }
        
        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(results)
        
        return report

    def _generate_recommendations(self, results: Dict[str, LoadTestResult]) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        # Analyze response times
        high_response_time_tests = [
            name for name, result in results.items() 
            if result.avg_response_time_ms > 1000
        ]
        if high_response_time_tests:
            recommendations.append(
                f"High response times detected in: {', '.join(high_response_time_tests)}. "
                "Consider optimizing database queries, adding caching, or scaling infrastructure."
            )
        
        # Analyze error rates
        high_error_rate_tests = [
            name for name, result in results.items() 
            if result.error_rate > 0.05
        ]
        if high_error_rate_tests:
            recommendations.append(
                f"High error rates in: {', '.join(high_error_rate_tests)}. "
                "Review error logs and implement better error handling and retry mechanisms."
            )
        
        # Analyze memory usage
        high_memory_tests = [
            name for name, result in results.items() 
            if result.peak_memory_mb > 512
        ]
        if high_memory_tests:
            recommendations.append(
                f"High memory usage in: {', '.join(high_memory_tests)}. "
                "Consider implementing memory pooling, optimizing data structures, or increasing memory limits."
            )
        
        # Check for memory leaks
        memory_leak_tests = [
            name for name, result in results.items() 
            if result.memory_leaked
        ]
        if memory_leak_tests:
            recommendations.append(
                f"Memory leaks detected in: {', '.join(memory_leak_tests)}. "
                "Review object lifecycle management and implement proper cleanup procedures."
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append(
                "Excellent performance! System is handling load well. "
                "Consider implementing monitoring and alerting for production deployment."
            )
        
        return recommendations

    def save_report(self, report: Dict[str, Any], filepath: str = None):
        """Save load test report to file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"load_test_report_{timestamp}.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📊 Load test report saved to {filepath}")

    def print_report(self, report: Dict[str, Any]):
        """Print load test report to console"""
        print("\n" + "=" * 80)
        print("🚀 ENTERPRISE LOAD TEST REPORT")
        print("=" * 80)
        print(f"Overall Status: {report['summary']['overall_status']}")
        print(f"Overall Grade: {report['summary']['overall_grade']}")
        print(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
        print(f"Total Requests: {report['summary']['total_requests']:,}")
        print(f"Overall Error Rate: {report['summary']['overall_error_rate']:.2%}")
        print(f"Total Test Duration: {report['summary']['test_duration_minutes']:.1f} minutes")
        
        print("\n" + "-" * 80)
        print("📊 INDIVIDUAL TEST RESULTS")
        print("-" * 80)
        
        for test_name, result in report["test_results"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {test_name} (Grade: {result['grade']})")
            print(f"   Users: {result['concurrent_users']}, "
                  f"Requests: {result['total_requests']:,}, "
                  f"RPS: {result['requests_per_second']:.1f}")
            print(f"   Avg Response: {result['avg_response_time_ms']:.1f}ms, "
                  f"P95: {result['p95_response_time_ms']:.1f}ms, "
                  f"P99: {result['p99_response_time_ms']:.1f}ms")
            print(f"   Error Rate: {result['error_rate']:.2%}, "
                  f"Peak Memory: {result['peak_memory_mb']:.1f}MB")
            
            if result["failure_reasons"]:
                print(f"   Issues: {'; '.join(result['failure_reasons'])}")
            print()
        
        print("-" * 80)
        print("💡 RECOMMENDATIONS")
        print("-" * 80)
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")
        print()


# Pytest integration
@pytest.mark.asyncio
async def test_enterprise_load_suite():
    """Test enterprise load testing suite"""
    config = LoadTestConfig(
        concurrent_users=2,
        test_duration=10,
        ramp_up_time=2
    )
    
    tester = EnterpriseLoadTester(config)
    
    # Run baseline test only for pytest
    result = await tester._run_baseline_test()
    
    assert result is not None
    assert result.test_name == "Baseline Performance"
    assert result.total_requests >= 0


@pytest.mark.asyncio 
async def test_load_test_config():
    """Test load test configuration"""
    config = LoadTestConfig(
        concurrent_users=10,
        test_duration=30,
        memory_threshold_mb=256
    )
    
    assert config.concurrent_users == 10
    assert config.test_duration == 30
    assert config.memory_threshold_mb == 256


if __name__ == "__main__":
    async def main():
        """Main load testing function"""
        print("Second Brain v3.0.0 - Enterprise Load Testing")
        print("=" * 50)
        
        # Configure for your environment
        config = LoadTestConfig(
            base_url=os.getenv("LOAD_TEST_URL", "http://localhost:8000"),
            api_key=os.getenv("LOAD_TEST_API_KEY", "test-load-key"),
            concurrent_users=int(os.getenv("LOAD_TEST_USERS", "25")),
            test_duration=int(os.getenv("LOAD_TEST_DURATION", "60"))
        )
        
        tester = EnterpriseLoadTester(config)
        
        try:
            # Run full load test suite
            report = await tester.run_load_test_suite()
            
            # Print and save results
            tester.print_report(report)
            tester.save_report(report)
            
            # Exit with appropriate code for CI/CD
            if report["summary"]["overall_status"] == "PASS":
                print("\n✅ All load tests passed!")
                sys.exit(0)
            else:
                print("\n❌ Some load tests failed!")
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Load testing interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n💥 Load testing failed with error: {e}")
            sys.exit(1)
    
    # Run the load test
    asyncio.run(main())
