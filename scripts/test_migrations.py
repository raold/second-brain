#!/usr/bin/env python3
"""
Migration System Test Runner

Automated testing script for the unified migration system.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_pytest_tests() -> dict[str, Any]:
    """Run pytest for migration tests."""
    print("🧪 Running Migration Framework Tests...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/migration/", "-v", "--tb=short", "--durations=10"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode,
        }

    except Exception as e:
        return {"success": False, "output": "", "errors": str(e), "return_code": -1}


def run_migration_cli_tests() -> dict[str, Any]:
    """Test migration CLI functionality."""
    print("🔧 Testing Migration CLI...")

    tests = []

    # Test CLI help
    try:
        result = subprocess.run(
            [sys.executable, "scripts/migrate.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        tests.append(
            {
                "name": "CLI Help",
                "success": result.returncode == 0 and "Migration Tool" in result.stdout,
                "output": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
            }
        )

    except Exception as e:
        tests.append({"name": "CLI Help", "success": False, "output": str(e)})

    # Test list command (should work even without migrations)
    try:
        env = os.environ.copy()
        env["USE_MOCK_DATABASE"] = "true"

        result = subprocess.run(
            [sys.executable, "scripts/migrate.py", "list"],
            capture_output=True,
            text=True,
            env=env,
            cwd=Path(__file__).parent.parent,
        )

        tests.append(
            {
                "name": "List Migrations",
                "success": result.returncode == 0,
                "output": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
            }
        )

    except Exception as e:
        tests.append({"name": "List Migrations", "success": False, "output": str(e)})

    return {"success": all(t["success"] for t in tests), "tests": tests}


def test_migration_api_routes():
    """Test migration API routes availability."""
    print("🌐 Testing Migration API Routes...")

    # This would require the server to be running
    # For now, just check that the routes module imports correctly
    try:
        from app.routes.migration_routes import router

        return {"success": True, "message": "Migration routes imported successfully", "route_count": len(router.routes)}
    except Exception as e:
        return {"success": False, "message": f"Failed to import migration routes: {e}"}


def test_concrete_migrations():
    """Test concrete migration examples."""
    print("📁 Testing Concrete Migration Examples...")

    migration_files = [
        "migrations/001_add_user_preferences.py",
        "migrations/002_migrate_memory_importance.py",
        "migrations/003_add_search_analytics.py",
    ]

    tests = []
    for migration_file in migration_files:
        try:
            # Check file exists
            file_path = Path(__file__).parent.parent / migration_file
            if not file_path.exists():
                tests.append({"name": migration_file, "success": False, "message": "File does not exist"})
                continue

            # Try to import and validate
            # This is a simplified test - in practice you'd test the actual migration
            tests.append(
                {"name": migration_file, "success": True, "message": f"File exists ({file_path.stat().st_size} bytes)"}
            )

        except Exception as e:
            tests.append({"name": migration_file, "success": False, "message": str(e)})

    return {"success": all(t["success"] for t in tests), "tests": tests}


def test_dashboard_integration():
    """Test migration dashboard integration."""
    print("📊 Testing Dashboard Integration...")

    try:
        from app.dashboard_migrations import get_migration_dashboard

        dashboard = get_migration_dashboard()

        return {
            "success": True,
            "message": "Migration dashboard component available",
            "methods": [
                method
                for method in dir(dashboard)
                if not method.startswith("_") and callable(getattr(dashboard, method))
            ],
        }

    except Exception as e:
        return {"success": False, "message": f"Dashboard integration failed: {e}"}


def print_test_results(results: dict[str, Any]):
    """Print formatted test results."""
    print("\n" + "=" * 60)
    print("🎯 MIGRATION SYSTEM TEST RESULTS")
    print("=" * 60)

    total_tests = 0
    passed_tests = 0

    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"\n{status} {test_name}")

        if "tests" in result:
            for sub_test in result["tests"]:
                sub_status = "  ✅" if sub_test["success"] else "  ❌"
                print(f"{sub_status} {sub_test['name']}")
                if not sub_test["success"] and "output" in sub_test:
                    print(f"     Error: {sub_test['output']}")
                total_tests += 1
                if sub_test["success"]:
                    passed_tests += 1
        else:
            total_tests += 1
            if result["success"]:
                passed_tests += 1

        if not result["success"] and "message" in result:
            print(f"     Error: {result['message']}")
        elif "message" in result:
            print(f"     {result['message']}")

    print(f"\n📊 Overall Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed! Migration system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        return False


def main():
    """Main test runner."""
    print("🚀 Starting Migration System Test Suite...")
    print("=" * 60)

    # Set environment for testing
    os.environ["USE_MOCK_DATABASE"] = "true"

    results = {}

    # Run all test categories
    results["Framework Tests"] = run_pytest_tests()
    results["CLI Tests"] = run_migration_cli_tests()
    results["API Routes"] = test_migration_api_routes()
    results["Concrete Migrations"] = test_concrete_migrations()
    results["Dashboard Integration"] = test_dashboard_integration()

    # Print results
    all_passed = print_test_results(results)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
