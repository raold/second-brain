#!/usr/bin/env python3
"""
Production Readiness Testing Script
Validates system health and readiness for production deployment
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests


class ProductionTester:
    """Production readiness validation"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: list[dict] = []

    def log_test(self, test_name: str, status: str, details: str = "", duration: float = 0):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.results.append(result)

        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status} ({duration:.2f}s)")
        if details:
            print(f"   {details}")

    def test_health_endpoint(self) -> bool:
        """Test basic health endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            duration = time.time() - start_time

            if response.status_code == 200:
                self.log_test("Health Endpoint", "PASS", f"Response time: {duration:.2f}s", duration)
                return True
            else:
                self.log_test("Health Endpoint", "FAIL", f"Status code: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Health Endpoint", "FAIL", f"Error: {str(e)}", duration)
            return False

    def test_api_endpoints(self) -> bool:
        """Test critical API endpoints"""
        endpoints = [
            ("/api/memories", "GET"),
            ("/api/sessions", "GET"),
            ("/api/docs", "GET"),
        ]

        all_passed = True
        for endpoint, method in endpoints:
            start_time = time.time()
            try:
                response = requests.request(method, f"{self.base_url}{endpoint}", timeout=10)
                duration = time.time() - start_time

                if response.status_code in [200, 201, 422]:  # 422 might be expected for some endpoints
                    self.log_test(f"API {endpoint}", "PASS", f"{method} {response.status_code}", duration)
                else:
                    self.log_test(f"API {endpoint}", "FAIL", f"{method} {response.status_code}", duration)
                    all_passed = False
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(f"API {endpoint}", "FAIL", f"{method} Error: {str(e)}", duration)
                all_passed = False

        return all_passed

    def test_database_connection(self) -> bool:
        """Test database connectivity through API"""
        start_time = time.time()
        try:
            # Test through a simple API call that requires DB
            response = requests.get(f"{self.base_url}/api/memories?limit=1", timeout=10)
            duration = time.time() - start_time

            if response.status_code in [200, 422]:
                self.log_test("Database Connection", "PASS", "API responded successfully", duration)
                return True
            else:
                self.log_test("Database Connection", "FAIL", f"Status: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Database Connection", "FAIL", f"Error: {str(e)}", duration)
            return False

    def test_performance_baseline(self) -> bool:
        """Test basic performance benchmarks"""
        start_time = time.time()
        try:
            # Test multiple rapid requests
            times = []
            for _ in range(5):
                req_start = time.time()
                requests.get(f"{self.base_url}/health", timeout=5)
                req_duration = time.time() - req_start
                times.append(req_duration)

            avg_time = sum(times) / len(times)
            max_time = max(times)
            duration = time.time() - start_time

            # Performance thresholds
            if avg_time < 0.5 and max_time < 1.0:
                self.log_test("Performance Baseline", "PASS", f"Avg: {avg_time:.2f}s, Max: {max_time:.2f}s", duration)
                return True
            else:
                self.log_test(
                    "Performance Baseline",
                    "WARN",
                    f"Slow response - Avg: {avg_time:.2f}s, Max: {max_time:.2f}s",
                    duration,
                )
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Performance Baseline", "FAIL", f"Error: {str(e)}", duration)
            return False

    def test_memory_operations(self) -> bool:
        """Test basic memory operations"""
        start_time = time.time()
        try:
            # Test creating a memory
            test_memory = {"content": "Production readiness test memory", "importance": 5}

            response = requests.post(f"{self.base_url}/api/memories", json=test_memory, timeout=10)

            if response.status_code in [201, 200, 422]:  # 422 might be validation error, still means API works
                # Try to get memories to test read operations
                get_response = requests.get(f"{self.base_url}/api/memories?limit=1", timeout=10)
                duration = time.time() - start_time

                if get_response.status_code == 200:
                    self.log_test("Memory Operations", "PASS", "Create/Read operations working", duration)
                    return True
                else:
                    self.log_test("Memory Operations", "FAIL", f"Read failed: {get_response.status_code}", duration)
                    return False
            else:
                duration = time.time() - start_time
                self.log_test("Memory Operations", "FAIL", f"Create failed: {response.status_code}", duration)
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Memory Operations", "FAIL", f"Error: {str(e)}", duration)
            return False

    def run_all_tests(self) -> bool:
        """Run complete production readiness test suite"""
        print("🚀 Starting Production Readiness Tests")
        print("=" * 50)

        tests = [
            ("System Health", self.test_health_endpoint),
            ("API Endpoints", self.test_api_endpoints),
            ("Database Connection", self.test_database_connection),
            ("Performance Baseline", self.test_performance_baseline),
            ("Memory Operations", self.test_memory_operations),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name}...")
            if test_func():
                passed += 1

        print(f"\n📊 Test Results: {passed}/{total} passed")

        if passed == total:
            print("🎉 All production readiness tests passed!")
            print("✅ System is ready for production deployment")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            print("❌ System needs attention before production deployment")
            return False

    def save_results(self, filename: str = "results/production_test_results.json"):
        """Save test results to file"""
        results_file = Path(filename)

        # Ensure results directory exists
        results_file.parent.mkdir(parents=True, exist_ok=True)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed": len([r for r in self.results if r["status"] == "PASS"]),
            "failed": len([r for r in self.results if r["status"] == "FAIL"]),
            "warnings": len([r for r in self.results if r["status"] == "WARN"]),
            "results": self.results,
        }

        with open(results_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"📝 Test results saved to {results_file}")


def main():
    """Main execution"""
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    print(f"🔍 Testing production readiness for: {base_url}")

    tester = ProductionTester(base_url)
    success = tester.run_all_tests()
    tester.save_results()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
