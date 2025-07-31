#!/usr/bin/env python3
"""
Test Route Imports

Tests that all route files can be imported successfully without import errors.
This will help verify that all the import fixes were successful.
"""

import importlib
import os
import sys
from pathlib import Path


def test_route_imports():
    """Test that all route files can be imported"""

    # Add the project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    routes_dir = project_root / "app" / "routes"
    failed_imports = []
    successful_imports = []

    print("Testing route imports...")
    print("=" * 50)

    for route_file in routes_dir.glob("*.py"):
        if route_file.name == "__init__.py":
            continue

        module_name = f"app.routes.{route_file.stem}"

        try:
            importlib.import_module(module_name)
            successful_imports.append(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            failed_imports.append((module_name, str(e)))
            print(f"❌ {module_name}: {e}")

    print("\n" + "=" * 50)
    print(f"Results: {len(successful_imports)} successful, {len(failed_imports)} failed")

    if failed_imports:
        print("\nFailed imports:")
        for module, error in failed_imports:
            print(f"  {module}: {error}")
        return False
    else:
        print("\n🎉 All route imports successful!")
        return True


def check_common_issues():
    """Check for common import issues in route files"""

    routes_dir = Path("app/routes")
    issues = []

    print("\nChecking for common import issues...")
    print("=" * 50)

    for route_file in routes_dir.glob("*.py"):
        if route_file.name == "__init__.py":
            continue

        with open(route_file) as f:
            content = f.read()

        # Check for bad import patterns
        bad_patterns = [
            ("app.dependencies.auth", "Should use app.dependencies and app.shared"),
            ("app.routes.auth", "Should use app.dependencies"),
            ("app.utils.logger", "Should use app.utils.logging_config"),
            ("get_db_instance", "Should use get_db from app.dependencies"),
        ]

        file_issues = []
        for pattern, message in bad_patterns:
            if pattern in content:
                file_issues.append(f"  - {pattern}: {message}")

        if file_issues:
            issues.append((route_file.name, file_issues))
            print(f"⚠️  {route_file.name}:")
            for issue in file_issues:
                print(issue)
        else:
            print(f"✅ {route_file.name}")

    if issues:
        print(f"\nFound {len(issues)} files with potential issues")
        return False
    else:
        print("\n🎉 No common import issues found!")
        return True


def main():
    """Main function"""

    print("Route Import Testing Tool")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Test 1: Check for common issues
    issues_ok = check_common_issues()

    # Test 2: Try to import all route modules
    imports_ok = test_route_imports()

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    if issues_ok and imports_ok:
        print("🎉 ALL TESTS PASSED!")
        print("The Docker app should now start successfully.")
        print("\nNext steps:")
        print("1. Run: docker-compose up --build")
        print("2. Check that the API starts without import errors")
        print("3. Test some endpoints to verify functionality")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("Review the issues above and fix them before trying to start the app.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
