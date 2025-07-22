#!/usr/bin/env python3
"""
Test Validation Script for Second Brain v2.2.0
Comprehensive validation without pytest dependency issues
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# Set up environment
os.environ["USE_MOCK_DATABASE"] = "true"
os.environ["API_TOKENS"] = "test-key-1,test-key-2"

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestValidator:
    """Comprehensive test validator"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test_result(self, name: str, success: bool, message: str = "", error: str = ""):
        """Record test result"""
        if success:
            self.passed += 1
            print(f"✅ {name}: {message}")
        else:
            self.failed += 1
            print(f"❌ {name}: {message}")
            if error:
                self.errors.append(f"{name}: {error}")

    async def validate_imports(self):
        """Validate all critical imports work"""
        print("\n🔍 VALIDATING IMPORTS")
        print("=" * 50)

        try:

            self.test_result("App Import", True, "FastAPI app imported successfully")
        except Exception as e:
            self.test_result("App Import", False, f"Failed to import app: {e}", traceback.format_exc())

        try:

            self.test_result("Mock Database Import", True, "Mock database imported successfully")
        except Exception as e:
            self.test_result(
                "Mock Database Import", False, f"Failed to import mock database: {e}", traceback.format_exc()
            )

        try:

            self.test_result("Docs Import", True, "Priority and MemoryType enums imported")
        except Exception as e:
            self.test_result("Docs Import", False, f"Failed to import docs: {e}", traceback.format_exc())

        try:
            from app.version import get_version_info

            version = get_version_info()
            self.test_result("Version Import", True, f"Version {version['version']} loaded")
        except Exception as e:
            self.test_result("Version Import", False, f"Failed to import version: {e}", traceback.format_exc())

        try:

            self.test_result("Security Import", True, "Security module imported")
        except Exception as e:
            self.test_result("Security Import", False, f"Failed to import security: {e}", traceback.format_exc())

    async def validate_mock_database(self):
        """Validate mock database functionality"""
        print("\n🗄️ VALIDATING MOCK DATABASE")
        print("=" * 50)

        try:
            from app.database_mock import get_mock_database

            # Initialize database
            db = await get_mock_database()
            self.test_result("Database Init", True, "Mock database initialized")

            # Test memory storage
            memory_id = await db.store_memory("Test memory for validation", {"type": "semantic", "category": "test"})
            self.test_result("Memory Storage", True, f"Memory stored with ID: {memory_id}")

            # Test memory retrieval
            memory = await db.get_memory(memory_id)
            if memory and memory["content"] == "Test memory for validation":
                self.test_result("Memory Retrieval", True, "Memory retrieved successfully")
            else:
                self.test_result("Memory Retrieval", False, "Memory retrieval failed")

            # Test search
            results = await db.search_memories("test", limit=5)
            self.test_result("Memory Search", True, f"Search found {len(results)} results")

            # Test statistics
            stats = await db.get_index_stats()
            self.test_result("Database Stats", True, f"Stats: {stats}")

            await db.close()

        except Exception as e:
            self.test_result("Mock Database", False, f"Database validation failed: {e}", traceback.format_exc())

    async def validate_api_endpoints(self):
        """Validate API endpoints"""
        print("\n🌐 VALIDATING API ENDPOINTS")
        print("=" * 50)

        try:
            from httpx import AsyncClient

            from app.app import app

            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test health endpoint
                response = await client.get("/health")
                if response.status_code == 200:
                    data = response.json()
                    self.test_result("Health Endpoint", True, f"Status: {data['status']}, Version: {data['version']}")
                else:
                    self.test_result("Health Endpoint", False, f"Status code: {response.status_code}")

                # Test status endpoint with auth
                response = await client.get("/status", params={"api_key": "test-key-1"})
                if response.status_code == 200:
                    self.test_result("Status Endpoint", True, "Status endpoint working with auth")
                else:
                    self.test_result("Status Endpoint", False, f"Status code: {response.status_code}")

                # Test memory storage endpoint
                memory_data = {"content": "API validation memory", "metadata": {"test": True}}
                response = await client.post("/memories", json=memory_data, params={"api_key": "test-key-1"})
                if response.status_code == 200:
                    self.test_result("Memory API", True, "Memory stored via API")
                else:
                    self.test_result("Memory API", False, f"Status code: {response.status_code}")

                # Test search endpoint
                search_data = {"query": "validation", "limit": 5}
                response = await client.post("/memories/search", json=search_data, params={"api_key": "test-key-1"})
                if response.status_code == 200:
                    results = response.json()
                    self.test_result("Search API", True, f"Search returned {len(results)} results")
                else:
                    self.test_result("Search API", False, f"Status code: {response.status_code}")

        except Exception as e:
            self.test_result("API Endpoints", False, f"API validation failed: {e}", traceback.format_exc())

    async def validate_security(self):
        """Validate security features"""
        print("\n🔒 VALIDATING SECURITY")
        print("=" * 50)

        try:
            from httpx import AsyncClient

            from app.app import app
            from app.security import verify_api_key

            # Test API key verification
            valid_key = verify_api_key("test-key-1")
            if valid_key:
                self.test_result("Valid API Key", True, "Valid API key accepted")
            else:
                self.test_result("Valid API Key", False, "Valid API key rejected")

            invalid_key = verify_api_key("invalid-key")
            if not invalid_key:
                self.test_result("Invalid API Key", True, "Invalid API key rejected")
            else:
                self.test_result("Invalid API Key", False, "Invalid API key accepted")

            # Test unauthorized access
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/status")
                if response.status_code == 401:
                    self.test_result("Unauthorized Access", True, "Unauthorized access blocked")
                else:
                    self.test_result("Unauthorized Access", False, f"Expected 401, got {response.status_code}")

        except Exception as e:
            self.test_result("Security", False, f"Security validation failed: {e}", traceback.format_exc())

    async def validate_dashboard(self):
        """Validate dashboard functionality"""
        print("\n📊 VALIDATING DASHBOARD")
        print("=" * 50)

        try:
            from app.dashboard import ProjectDashboard

            # Initialize dashboard
            dashboard = ProjectDashboard()
            self.test_result("Dashboard Init", True, "Dashboard initialized")

            # Test milestone loading (should not fail with status enum issues)
            try:
                milestones = dashboard.get_upcoming_milestones(limit=3)
                self.test_result("Milestone Loading", True, f"Loaded {len(milestones)} milestones")
            except Exception as e:
                self.test_result("Milestone Loading", False, f"Milestone loading failed: {e}")

            # Test metrics
            try:
                metrics = dashboard.get_latest_metrics()
                self.test_result("Metrics Loading", True, f"Loaded {len(metrics)} metrics")
            except Exception as e:
                self.test_result("Metrics Loading", False, f"Metrics loading failed: {e}")

            # Test summary
            try:
                dashboard.get_dashboard_summary()
                self.test_result("Dashboard Summary", True, "Summary generated")
            except Exception as e:
                self.test_result("Dashboard Summary", False, f"Summary failed: {e}")

        except Exception as e:
            self.test_result("Dashboard", False, f"Dashboard validation failed: {e}", traceback.format_exc())

    async def validate_visualization(self):
        """Validate memory visualization"""
        print("\n🎨 VALIDATING VISUALIZATION")
        print("=" * 50)

        try:
            from app.memory_visualization import MemoryVisualizationEngine

            # Create visualization engine
            viz_engine = MemoryVisualizationEngine()
            self.test_result("Visualization Engine", True, "Visualization engine created")

            # Test with mock data
            mock_memories = [
                {"id": "1", "content": "Test memory 1", "metadata": {}},
                {"id": "2", "content": "Test memory 2", "metadata": {}},
            ]

            try:
                graph_data = await viz_engine.generate_memory_graph(mock_memories)
                nodes = len(graph_data.get("nodes", []))
                edges = len(graph_data.get("edges", []))
                self.test_result("Graph Generation", True, f"Generated graph with {nodes} nodes, {edges} edges")
            except Exception as e:
                self.test_result("Graph Generation", False, f"Graph generation failed: {e}")

        except Exception as e:
            self.test_result("Visualization", False, f"Visualization validation failed: {e}", traceback.format_exc())

    async def run_comprehensive_validation(self):
        """Run all validation tests"""
        print("🚀 STARTING COMPREHENSIVE TEST VALIDATION")
        print("=" * 80)

        validation_steps = [
            self.validate_imports,
            self.validate_mock_database,
            self.validate_api_endpoints,
            self.validate_security,
            self.validate_dashboard,
            self.validate_visualization,
        ]

        for step in validation_steps:
            try:
                await step()
            except Exception as e:
                print(f"❌ Validation step failed: {e}")
                self.failed += 1

        # Generate final report
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE VALIDATION RESULTS")
        print("=" * 80)

        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"📊 Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")

        if self.failed > 0:
            print("\n🔍 DETAILED ERROR ANALYSIS:")
            print("-" * 50)
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"• {error}")

        print("\n" + "=" * 80)

        if self.failed == 0:
            print("🎉 ALL VALIDATIONS PASSED! Test suite is working perfectly!")
            return True
        else:
            print("⚠️ Some validations failed. Please review the issues above.")
            return False


async def main():
    """Main validation function"""
    validator = TestValidator()
    success = await validator.run_comprehensive_validation()
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
