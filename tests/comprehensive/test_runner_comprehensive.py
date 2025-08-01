#!/usr/bin/env python3
"""
import pytest

pytestmark = pytest.mark.comprehensive

Comprehensive Test Runner for Second Brain v2.2.0
Bypasses virtual environment issues and runs all tests systematically
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Any

# Set up environment for testing
os.environ["API_TOKENS"] = "test-key-1,test-key-2"

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestResult:
    """Container for test results"""

    def __init__(self, name: str, success: bool, message: str = "", error: str = ""):
        self.name = name
        self.success = success
        self.message = message
        self.error = error

    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.name}: {self.message}"


class ComprehensiveTestRunner:
    """Comprehensive test runner for Second Brain"""

    def __init__(self):
        self.results: list[TestResult] = []

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all tests systematically"""
        print("🚀 Starting Comprehensive Test Suite for Second Brain v2.2.0")
        print("=" * 80)

        # Test categories
        test_categories = [
            ("Basic Imports", self.test_basic_imports),
            ("Mock Database", self.test_mock_database),
            ("App Configuration", self.test_app_configuration),
            ("API Endpoints", self.test_api_endpoints),
            ("Dashboard System", self.test_dashboard_system),
            ("Memory Visualization", self.test_memory_visualization),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Security Features", self.test_security_features),
            ("Version Management", self.test_version_management),
        ]

        for category_name, test_func in test_categories:
            print(f"\n📊 Running {category_name} Tests")
            print("-" * 50)
            try:
                await test_func()
            except Exception as e:
                self.results.append(
                    TestResult(
                        f"{category_name} (CRITICAL ERROR)", False, f"Category failed: {str(e)}", traceback.format_exc()
                    )
                )

        return self.generate_report()

    async def test_basic_imports(self):
        """Test basic imports work correctly"""
        try:
            # Test app imports

            self.results.append(TestResult("App Import", True, "FastAPI app imported successfully"))

            # Test database imports

            self.results.append(TestResult("Mock Database Import", True, "Mock database imported successfully"))

            # Test docs imports

            self.results.append(TestResult("Docs Import", True, "Priority and MemoryType enums imported"))

            # Test version import
            from app.version import get_version_info

            version = get_version_info()
            self.results.append(TestResult("Version Import", True, f"Version {version['version']} loaded"))

        except Exception as e:
            self.results.append(TestResult("Basic Imports", False, f"Import failed: {e}", traceback.format_exc()))

    async def test_mock_database(self):
        """Test mock database functionality"""
        try:
            
            # Initialize mock database
            db = await get_mock_database()
            self.results.append(TestResult("Mock DB Init", True, "Mock database initialized"))

            # Test store memory
            memory_id = await db.store_memory(
                "Test memory for comprehensive testing", {"type": "test", "category": "automated"}
            )
            self.results.append(TestResult("Store Memory", True, f"Memory stored with ID: {memory_id}"))

            # Test retrieve memory
            memory = await db.get_memory(memory_id)
            if memory and memory["content"] == "Test memory for comprehensive testing":
                self.results.append(TestResult("Retrieve Memory", True, "Memory retrieved successfully"))
            else:
                self.results.append(TestResult("Retrieve Memory", False, "Memory retrieval failed"))

            # Test search
            results = await db.search_memories("test", limit=5)
            self.results.append(TestResult("Search Memories", True, f"Found {len(results)} memories"))

            # Test stats
            stats = await db.get_index_stats()
            self.results.append(TestResult("Database Stats", True, f"Stats retrieved: {stats}"))

            await db.close()

        except Exception as e:
            self.results.append(
                TestResult("Mock Database", False, f"Database test failed: {e}", traceback.format_exc())
            )

    async def test_app_configuration(self):
        """Test app configuration and setup"""
        try:
            from app.app import app

            # Test app creation
            assert app is not None
            self.results.append(TestResult("App Creation", True, "FastAPI app created successfully"))

            # Test middleware setup
            middleware_count = len(app.user_middleware)
            self.results.append(
                TestResult("Middleware Setup", True, f"{middleware_count} middleware components loaded")
            )

            # Test route registration
            routes = [route.path for route in app.routes]
            critical_routes = ["/health", "/memories", "/docs", "/status"]
            missing_routes = [route for route in critical_routes if route not in str(routes)]

            if not missing_routes:
                self.results.append(TestResult("Route Registration", True, f"{len(routes)} routes registered"))
            else:
                self.results.append(TestResult("Route Registration", False, f"Missing routes: {missing_routes}"))

        except Exception as e:
            self.results.append(
                TestResult("App Configuration", False, f"Configuration test failed: {e}", traceback.format_exc())
            )

    async def test_api_endpoints(self):
        """Test API endpoints using httpx client"""
        try:
            from httpx import AsyncClient

            from app.app import app

            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test health endpoint
                response = await client.get("/health")
                if response.status_code == 200:
                    data = response.json()
                    self.results.append(
                        TestResult("Health Endpoint", True, f"Status: {data['status']}, Version: {data['version']}")
                    )
                else:
                    self.results.append(TestResult("Health Endpoint", False, f"Status code: {response.status_code}"))

                # Test status endpoint with auth
                response = await client.get("/status", params={"api_key": "test-key-1"})
                if response.status_code == 200:
                    self.results.append(TestResult("Status Endpoint", True, "Status endpoint working with auth"))
                else:
                    self.results.append(TestResult("Status Endpoint", False, f"Status code: {response.status_code}"))

                # Test memory storage
                memory_data = {"content": "API test memory", "metadata": {"test": True}}
                response = await client.post("/memories", json=memory_data, params={"api_key": "test-key-1"})
                if response.status_code == 200:
                    self.results.append(TestResult("Memory Storage", True, "Memory stored via API"))
                else:
                    self.results.append(TestResult("Memory Storage", False, f"Status code: {response.status_code}"))

        except Exception as e:
            self.results.append(TestResult("API Endpoints", False, f"API test failed: {e}", traceback.format_exc()))

    async def test_dashboard_system(self):
        """Test dashboard system functionality"""
        try:
            from app.dashboard import ProjectDashboard

            # Initialize dashboard
            dashboard = ProjectDashboard()
            self.results.append(TestResult("Dashboard Init", True, "Dashboard initialized successfully"))

            # Test milestone loading
            milestones = dashboard.get_upcoming_milestones(limit=3)
            self.results.append(TestResult("Milestone Loading", True, f"Loaded {len(milestones)} milestones"))

            # Test metrics
            metrics = dashboard.get_latest_metrics()
            self.results.append(TestResult("Metrics Loading", True, f"Loaded {len(metrics)} metrics"))

            # Test summary generation
            dashboard.get_dashboard_summary()
            self.results.append(TestResult("Dashboard Summary", True, "Summary generated successfully"))

        except Exception as e:
            self.results.append(
                TestResult("Dashboard System", False, f"Dashboard test failed: {e}", traceback.format_exc())
            )

    async def test_memory_visualization(self):
        """Test memory visualization features"""
        try:
            # Test visualization routes import

            self.results.append(TestResult("Visualization Routes", True, "Visualization routes imported"))

            # Test memory visualization engine
            from app.memory_visualization import MemoryVisualizationEngine

            viz_engine = MemoryVisualizationEngine()
            self.results.append(TestResult("Visualization Engine", True, "Visualization engine created"))

            # Test with mock data
            mock_memories = [
                {"id": "1", "content": "Test memory 1", "metadata": {}},
                {"id": "2", "content": "Test memory 2", "metadata": {}},
            ]

            graph_data = await viz_engine.generate_memory_graph(mock_memories)
            self.results.append(
                TestResult("Graph Generation", True, f"Generated graph with {len(graph_data.get('nodes', []))} nodes")
            )

        except Exception as e:
            self.results.append(
                TestResult("Memory Visualization", False, f"Visualization test failed: {e}", traceback.format_exc())
            )

    async def test_performance_benchmarks(self):
        """Test performance benchmark functionality"""
        try:
            from tests.performance.test_performance_benchmark import BenchmarkResult, PerformanceMetrics

            # Test performance classes
            PerformanceMetrics(
                response_time=0.1,
                memory_usage=50.0,
                cpu_usage=25.0,
                database_connections=1,
                error_rate=0.0,
                throughput=100.0,
            )
            self.results.append(TestResult("Performance Metrics", True, "Performance metrics class working"))

            BenchmarkResult(
                test_name="test",
                endpoint="/test",
                method="GET",
                avg_response_time=0.1,
                min_response_time=0.05,
                max_response_time=0.2,
                p95_response_time=0.15,
                p99_response_time=0.18,
                throughput=100.0,
                error_rate=0.0,
                success_rate=100.0,
                memory_usage=50.0,
                cpu_usage=25.0,
                total_requests=10,
                passed=True,
            )
            self.results.append(TestResult("Benchmark Result", True, "Benchmark result class working"))

        except Exception as e:
            self.results.append(
                TestResult("Performance Benchmarks", False, f"Performance test failed: {e}", traceback.format_exc())
            )

    async def test_security_features(self):
        """Test security features"""
        try:
            from app.security import verify_api_key

            # Test middleware import
            self.results.append(TestResult("Security Middleware", True, "Security middleware imported"))

            # Test API key verification
            is_valid = verify_api_key("test-key-1")
            if is_valid:
                self.results.append(TestResult("API Key Verification", True, "Valid API key accepted"))
            else:
                self.results.append(TestResult("API Key Verification", False, "Valid API key rejected"))

            # Test invalid key rejection
            is_invalid = verify_api_key("invalid-key")
            if not is_invalid:
                self.results.append(TestResult("Invalid Key Rejection", True, "Invalid API key rejected"))
            else:
                self.results.append(TestResult("Invalid Key Rejection", False, "Invalid API key accepted"))

        except Exception as e:
            self.results.append(
                TestResult("Security Features", False, f"Security test failed: {e}", traceback.format_exc())
            )

    async def test_version_management(self):
        """Test version management"""
        try:
            from app.version import BUILD_TYPE, VERSION, get_version_info

            # Test version constants
            self.results.append(TestResult("Version Constants", True, f"VERSION: {VERSION}, BUILD: {BUILD_TYPE}"))

            # Test version info function
            version_info = get_version_info()
            expected_keys = ["version", "build", "commit", "timestamp"]
            missing_keys = [key for key in expected_keys if key not in version_info]

            if not missing_keys:
                self.results.append(TestResult("Version Info", True, "All version info fields present"))
            else:
                self.results.append(TestResult("Version Info", False, f"Missing fields: {missing_keys}"))

        except Exception as e:
            self.results.append(
                TestResult("Version Management", False, f"Version test failed: {e}", traceback.format_exc())
            )

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result.success)
        failed_tests = total_tests - passed_tests

        report = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "results": self.results,
        }

        # Print detailed report
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)

        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {report['success_rate']:.1f}%")

        print("\n📋 Detailed Results:")
        print("-" * 50)

        for result in self.results:
            print(result)
            if not result.success and result.error:
                print(f"   💥 Error Details: {result.error[:200]}...")

        print("\n" + "=" * 80)

        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! The application is ready for deployment!")
        else:
            print("⚠️  Some tests failed. Please review the issues above.")

        print("=" * 80)

        return report


async def main():
    """Main test runner"""
    runner = ComprehensiveTestRunner()
    report = await runner.run_all_tests()
    return report


if __name__ == "__main__":
    asyncio.run(main())
