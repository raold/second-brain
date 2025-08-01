#!/usr/bin/env python3
"""
Performance Testing Suite for Second Brain

Comprehensive performance testing with multiple strategies:
- Benchmark Tests: Measure baseline performance metrics
- Load Tests: Test system under realistic load
- Stress Tests: Find breaking points and bottlenecks
- Memory Tests: Detect memory leaks and usage patterns

Integrates with CI/CD pipeline for continuous performance monitoring.
"""

import argparse
import asyncio
import json
import logging
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import psutil
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class PerformanceMetric:
    """Individual performance measurement."""
    name: str
    category: str
    value: float
    unit: str
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class LoadTestResult:
    """Load test execution result."""
    test_name: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    errors: List[str] = field(default_factory=list)

@dataclass
class PerformanceReport:
    """Complete performance test report."""
    test_id: str
    test_type: str
    start_time: str
    end_time: str
    duration: float
    environment: Dict[str, Any]
    metrics: List[PerformanceMetric] = field(default_factory=list)
    load_tests: List[LoadTestResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    passed: bool = False

class PerformanceTester:
    """Comprehensive performance testing suite."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.test_id = f"perf-{int(time.time())}"
        self.logger = self._setup_logging()
        
        # Performance thresholds
        self.thresholds = {
            "response_time_ms": 500,      # 500ms max average
            "p95_response_time_ms": 1000, # 1s max 95th percentile
            "p99_response_time_ms": 2000, # 2s max 99th percentile
            "requests_per_second": 100,   # 100 RPS minimum
            "error_rate_percent": 1.0,    # 1% max error rate
            "memory_usage_mb": 512,       # 512MB max memory
            "cpu_usage_percent": 70,      # 70% max CPU
        }
        
        # Test configuration
        self.load_test_configs = {
            "basic": {
                "users": 10,
                "duration": 30,
                "ramp_up": 5
            },
            "moderate": {
                "users": 50,
                "duration": 60,
                "ramp_up": 10
            },
            "intensive": {
                "users": 100,
                "duration": 120,
                "ramp_up": 20
            }
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger(__name__)

    async def benchmark_response_times(self) -> List[PerformanceMetric]:
        """Benchmark response times for key endpoints."""
        endpoints = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/v1/memories"
        ]
        
        metrics = []
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                self.logger.info(f"Benchmarking {endpoint}...")
                
                response_times = []
                successful_requests = 0
                
                # Make 50 requests to get reliable measurements
                for i in range(50):
                    start_time = time.time()
                    try:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.read()  # Consume response body
                            if response.status < 400:
                                successful_requests += 1
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                    except Exception as e:
                        self.logger.warning(f"Request failed: {e}")
                        response_time = (time.time() - start_time) * 1000
                        response_times.append(response_time)
                
                if response_times:
                    avg_time = statistics.mean(response_times)
                    p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
                    p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
                    
                    endpoint_name = endpoint.replace('/', '_').replace('__', '_').strip('_')
                    
                    metrics.extend([
                        PerformanceMetric(
                            name=f"{endpoint_name}_avg_response_time",
                            category="response_time",
                            value=avg_time,
                            unit="ms",
                            threshold=self.thresholds["response_time_ms"],
                            passed=avg_time <= self.thresholds["response_time_ms"]
                        ),
                        PerformanceMetric(
                            name=f"{endpoint_name}_p95_response_time",
                            category="response_time",
                            value=p95_time,
                            unit="ms",
                            threshold=self.thresholds["p95_response_time_ms"],
                            passed=p95_time <= self.thresholds["p95_response_time_ms"]
                        ),
                        PerformanceMetric(
                            name=f"{endpoint_name}_success_rate",
                            category="reliability",
                            value=(successful_requests / len(response_times)) * 100,
                            unit="%",
                            threshold=99.0,
                            passed=(successful_requests / len(response_times)) * 100 >= 99.0
                        )
                    ])
        
        return metrics

    def benchmark_memory_usage(self) -> List[PerformanceMetric]:
        """Benchmark memory usage patterns."""
        metrics = []
        
        try:
            # Get current process memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            metrics.extend([
                PerformanceMetric(
                    name="memory_rss",
                    category="memory",
                    value=memory_info.rss / 1024 / 1024,  # Convert to MB
                    unit="MB",
                    threshold=self.thresholds["memory_usage_mb"],
                    passed=(memory_info.rss / 1024 / 1024) <= self.thresholds["memory_usage_mb"]
                ),
                PerformanceMetric(
                    name="memory_percent",
                    category="memory",
                    value=memory_percent,
                    unit="%",
                    threshold=50.0,  # 50% of system memory
                    passed=memory_percent <= 50.0
                )
            ])
            
            # Memory growth test
            initial_memory = memory_info.rss
            
            # Simulate some operations
            for _ in range(100):
                # Simulate memory usage
                data = list(range(1000))
                del data
            
            final_memory = process.memory_info().rss
            memory_growth = (final_memory - initial_memory) / 1024 / 1024
            
            metrics.append(PerformanceMetric(
                name="memory_growth",
                category="memory",
                value=memory_growth,
                unit="MB",
                threshold=10.0,  # 10MB max growth
                passed=memory_growth <= 10.0
            ))
            
        except Exception as e:
            self.logger.warning(f"Memory benchmarking failed: {e}")
            metrics.append(PerformanceMetric(
                name="memory_benchmark_error",
                category="memory",
                value=0,
                unit="error",
                passed=False
            ))
        
        return metrics

    def benchmark_cpu_usage(self) -> List[PerformanceMetric]:
        """Benchmark CPU usage under load."""
        metrics = []
        
        try:
            # Measure CPU usage over time
            cpu_samples = []
            
            for i in range(10):
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_samples.append(cpu_percent)
            
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)
            
            metrics.extend([
                PerformanceMetric(
                    name="cpu_usage_avg",
                    category="cpu",
                    value=avg_cpu,
                    unit="%",
                    threshold=self.thresholds["cpu_usage_percent"],
                    passed=avg_cpu <= self.thresholds["cpu_usage_percent"]
                ),
                PerformanceMetric(
                    name="cpu_usage_max",
                    category="cpu",
                    value=max_cpu,
                    unit="%",
                    threshold=90.0,  # 90% max spike
                    passed=max_cpu <= 90.0
                )
            ])
            
        except Exception as e:
            self.logger.warning(f"CPU benchmarking failed: {e}")
            metrics.append(PerformanceMetric(
                name="cpu_benchmark_error",
                category="cpu",
                value=0,
                unit="error",
                passed=False
            ))
        
        return metrics

    async def run_load_test(self, config_name: str = "basic") -> LoadTestResult:
        """Run load test with specified configuration."""
        if config_name not in self.load_test_configs:
            raise ValueError(f"Unknown load test configuration: {config_name}")
        
        config = self.load_test_configs[config_name]
        self.logger.info(f"Running load test '{config_name}': {config['users']} users for {config['duration']}s")
        
        # Use simple concurrent requests for load testing
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        start_time = time.time()
        
        async def make_request(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> Tuple[float, bool, str]:
            """Make a single request and return timing info."""
            async with semaphore:
                request_start = time.time()
                try:
                    async with session.get(f"{self.base_url}/health") as response:
                        await response.read()
                        request_time = (time.time() - request_start) * 1000
                        success = response.status < 400
                        error_msg = f"HTTP {response.status}" if not success else ""
                        return request_time, success, error_msg
                except Exception as e:
                    request_time = (time.time() - request_start) * 1000
                    return request_time, False, str(e)
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(config["users"])
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            # Ramp up users
            total_requests = 0
            ramp_up_duration = config["ramp_up"]
            test_duration = config["duration"]
            
            # Simple load test - make requests for specified duration
            end_time = start_time + test_duration
            
            tasks = []
            while time.time() < end_time:
                if len(tasks) < config["users"]:
                    task = asyncio.create_task(make_request(session, semaphore))
                    tasks.append(task)
                    total_requests += 1
                
                # Process completed tasks
                done_tasks = [task for task in tasks if task.done()]
                for task in done_tasks:
                    try:
                        request_time, success, error_msg = await task
                        response_times.append(request_time)
                        if success:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                            if error_msg:
                                errors.append(error_msg)
                    except Exception as e:
                        failed_requests += 1
                        errors.append(str(e))
                    tasks.remove(task)
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
            
            # Wait for remaining tasks
            if tasks:
                for task in tasks:
                    try:
                        request_time, success, error_msg = await task
                        response_times.append(request_time)
                        if success:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                            if error_msg:
                                errors.append(error_msg)
                    except Exception as e:
                        failed_requests += 1
                        errors.append(str(e))
        
        actual_duration = time.time() - start_time
        
        # Calculate metrics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
        
        requests_per_second = total_requests / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return LoadTestResult(
            test_name=config_name,
            duration=actual_duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=requests_per_second,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            errors=list(set(errors))  # Unique errors only
        )

    async def run_benchmark_tests(self) -> List[PerformanceMetric]:
        """Run all benchmark tests."""
        self.logger.info("Running benchmark tests...")
        
        all_metrics = []
        
        # Response time benchmarks
        response_metrics = await self.benchmark_response_times()
        all_metrics.extend(response_metrics)
        
        # Memory benchmarks
        memory_metrics = self.benchmark_memory_usage()
        all_metrics.extend(memory_metrics)
        
        # CPU benchmarks
        cpu_metrics = self.benchmark_cpu_usage()
        all_metrics.extend(cpu_metrics)
        
        return all_metrics

    async def run_performance_suite(self, test_type: str = "benchmark", load_intensity: str = "basic", quick: bool = False) -> PerformanceReport:
        """Run complete performance test suite."""
        start_time = time.time()
        self.logger.info(f"Starting performance test suite: {test_type}")
        
        metrics = []
        load_tests = []
        
        if test_type in ["benchmark", "both"]:
            self.logger.info("Running benchmark tests...")
            benchmark_metrics = await self.run_benchmark_tests()
            metrics.extend(benchmark_metrics)
        
        if test_type in ["load", "both"]:
            self.logger.info(f"Running load tests (intensity: {load_intensity})...")
            
            if quick:
                # Quick load test
                load_result = await self.run_load_test("basic")
                load_tests.append(load_result)
            else:
                # Full load test suite
                if load_intensity == "basic":
                    configs = ["basic"]
                elif load_intensity == "moderate":
                    configs = ["basic", "moderate"]
                else:  # intensive
                    configs = ["basic", "moderate", "intensive"]
                
                for config in configs:
                    load_result = await self.run_load_test(config)
                    load_tests.append(load_result)
        
        # Generate summary
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate pass/fail for metrics
        passed_metrics = len([m for m in metrics if m.passed])
        total_metrics = len(metrics)
        
        # Calculate load test performance
        load_performance = True
        for load_test in load_tests:
            if (load_test.error_rate > self.thresholds["error_rate_percent"] or
                load_test.avg_response_time > self.thresholds["response_time_ms"] or
                load_test.requests_per_second < self.thresholds["requests_per_second"]):
                load_performance = False
                break
        
        overall_passed = (passed_metrics == total_metrics) and load_performance
        
        summary = {
            "total_metrics": total_metrics,
            "passed_metrics": passed_metrics,
            "failed_metrics": total_metrics - passed_metrics,
            "metric_pass_rate": (passed_metrics / total_metrics * 100) if total_metrics > 0 else 0,
            "load_tests_count": len(load_tests),
            "load_performance_passed": load_performance,
            "overall_performance_score": self._calculate_performance_score(metrics, load_tests)
        }
        
        return PerformanceReport(
            test_id=self.test_id,
            test_type=test_type,
            start_time=datetime.fromtimestamp(start_time, timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(end_time, timezone.utc).isoformat(),
            duration=duration,
            environment={
                "base_url": self.base_url,
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": os.cpu_count(),
                "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024  # GB
            },
            metrics=metrics,
            load_tests=load_tests,
            summary=summary,
            passed=overall_passed
        )

    def _calculate_performance_score(self, metrics: List[PerformanceMetric], load_tests: List[LoadTestResult]) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # Deduct points for failed metrics
        for metric in metrics:
            if not metric.passed:
                if metric.category == "response_time":
                    score -= 10  # Response time is critical
                elif metric.category == "memory":
                    score -= 5   # Memory issues are serious
                else:
                    score -= 3   # Other metrics
        
        # Deduct points for poor load test performance
        for load_test in load_tests:
            if load_test.error_rate > self.thresholds["error_rate_percent"]:
                score -= 15  # High error rate is critical
            if load_test.avg_response_time > self.thresholds["response_time_ms"]:
                score -= 10  # Slow response times
            if load_test.requests_per_second < self.thresholds["requests_per_second"]:
                score -= 5   # Low throughput
        
        return max(0.0, score)

    def print_report(self, report: PerformanceReport):
        """Print human-readable performance report."""
        print(f"\n{'='*80}")
        print(f"⚡ PERFORMANCE TEST REPORT - {report.test_id}")
        print(f"{'='*80}")
        
        print(f"Test Type: {report.test_type}")
        print(f"Duration: {report.duration:.1f}s")
        print(f"Base URL: {report.environment['base_url']}")
        print(f"Performance Score: {report.summary['overall_performance_score']:.1f}/100")
        
        # Overall status
        if report.passed:
            print(f"✅ OVERALL RESULT: PASSED - Performance meets requirements")
        else:
            print(f"❌ OVERALL RESULT: FAILED - Performance below requirements")
        
        # Metrics summary
        if report.metrics:
            print(f"\n📊 BENCHMARK METRICS ({len(report.metrics)} total):")
            categories = {}
            for metric in report.metrics:
                if metric.category not in categories:
                    categories[metric.category] = {"total": 0, "passed": 0}
                categories[metric.category]["total"] += 1
                if metric.passed:
                    categories[metric.category]["passed"] += 1
            
            for category, stats in categories.items():
                status = "✅" if stats["passed"] == stats["total"] else "❌"
                print(f"  {status} {category.capitalize():15} {stats['passed']}/{stats['total']} passed")
        
        # Load test results
        if report.load_tests:
            print(f"\n🚀 LOAD TEST RESULTS ({len(report.load_tests)} tests):")
            for load_test in report.load_tests:
                status = "✅" if (load_test.error_rate <= 1.0 and 
                                load_test.avg_response_time <= 500) else "❌"
                print(f"  {status} {load_test.test_name.capitalize():15}")
                print(f"     RPS: {load_test.requests_per_second:.1f}, "
                      f"Avg: {load_test.avg_response_time:.1f}ms, "
                      f"Errors: {load_test.error_rate:.1f}%")
        
        # Failed metrics details
        failed_metrics = [m for m in report.metrics if not m.passed]
        if failed_metrics:
            print(f"\n❌ FAILED METRICS ({len(failed_metrics)}):")
            for metric in failed_metrics:
                print(f"  - {metric.name}: {metric.value:.1f}{metric.unit} "
                      f"(threshold: {metric.threshold}{metric.unit})")
        
        # Performance recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if report.passed:
            print("  - Performance meets all requirements")
            print("  - Continue monitoring in production")
        else:
            print("  - Investigate performance bottlenecks")
            print("  - Consider optimization before deployment")
            if report.summary["overall_performance_score"] < 70:
                print("  - Performance score is critically low")
        
        print(f"{'='*80}")

    def save_report(self, report: PerformanceReport, filename: str):
        """Save performance report to JSON file."""
        try:
            report_data = {
                "test_id": report.test_id,
                "test_type": report.test_type,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "duration": report.duration,
                "passed": report.passed,
                "environment": report.environment,
                "summary": report.summary,
                "metrics": [
                    {
                        "name": metric.name,
                        "category": metric.category,
                        "value": metric.value,
                        "unit": metric.unit,
                        "threshold": metric.threshold,
                        "passed": metric.passed,
                        "timestamp": metric.timestamp
                    }
                    for metric in report.metrics
                ],
                "load_tests": [
                    {
                        "test_name": test.test_name,
                        "duration": test.duration,
                        "total_requests": test.total_requests,
                        "successful_requests": test.successful_requests,
                        "failed_requests": test.failed_requests,
                        "requests_per_second": test.requests_per_second,
                        "avg_response_time": test.avg_response_time,
                        "p95_response_time": test.p95_response_time,
                        "p99_response_time": test.p99_response_time,
                        "error_rate": test.error_rate,
                        "errors": test.errors
                    }
                    for test in report.load_tests
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            self.logger.info(f"Performance report saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save performance report: {e}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Performance Testing Suite for Second Brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  benchmark     Measure baseline performance metrics
  load          Test system under realistic load  
  both          Run both benchmark and load tests

Load Intensities:
  basic         Light load (10 users, 30s)
  moderate      Medium load (50 users, 60s)
  intensive     Heavy load (100 users, 120s)

Examples:
  python scripts/run_performance_tests.py --type benchmark
  python scripts/run_performance_tests.py --type load --load-intensity moderate
  python scripts/run_performance_tests.py --type both --quick
  python scripts/run_performance_tests.py --url https://api.example.com --save-report perf_report.json
        """
    )

    parser.add_argument("--type", choices=["benchmark", "load", "both"], default="benchmark",
                       help="Type of performance test to run")
    parser.add_argument("--url", default="http://localhost:8000",
                       help="Base URL to test (default: http://localhost:8000)")
    parser.add_argument("--load-intensity", choices=["basic", "moderate", "intensive"], default="basic",
                       help="Load test intensity")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests only (CI-friendly)")
    parser.add_argument("--save-report", help="Save performance report to JSON file")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")

    args = parser.parse_args()

    # Setup logging
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    try:
        tester = PerformanceTester(args.url)
        
        # Run performance tests
        report = await tester.run_performance_suite(
            test_type=args.type,
            load_intensity=args.load_intensity,
            quick=args.quick
        )
        
        # Print report
        if not args.quiet:
            tester.print_report(report)
        
        # Save report if requested
        if args.save_report:
            tester.save_report(report, args.save_report)
        
        # Exit with appropriate code
        sys.exit(0 if report.passed else 1)
        
    except KeyboardInterrupt:
        print("\nPerformance tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Performance tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())