#!/usr/bin/env python3
"""
Validate CI/CD Configuration for Second Brain v2.8.2

This script checks for common CI/CD issues before pushing to main.
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_status(status, message):
    """Print colored status message."""
    if status == "OK":
        print(f"{GREEN}✓{RESET} {message}")
    elif status == "ERROR":
        print(f"{RED}✗{RESET} {message}")
    elif status == "WARNING":
        print(f"{YELLOW}⚠{RESET} {message}")

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print_status("OK", f"{description} exists")
        return True
    else:
        print_status("ERROR", f"{description} missing: {filepath}")
        return False

def check_python_syntax(filepath):
    """Check Python file syntax."""
    try:
        compile(open(filepath).read(), filepath, 'exec')
        return True
    except SyntaxError as e:
        print_status("ERROR", f"Syntax error in {filepath}: {e}")
        return False

def check_imports():
    """Check if key imports work."""
    print("\n=== Checking Imports ===")

    imports_to_check = [
        ("from app.models.synthesis import ReportType", "Synthesis models"),
        ("from app.services.synthesis import ReportGenerator", "Synthesis services"),
        ("from app.routes.synthesis_routes import router", "Synthesis routes"),
    ]

    all_ok = True
    for import_stmt, description in imports_to_check:
        try:
            exec(import_stmt)
            print_status("OK", f"{description} import works")
        except Exception as e:
            print_status("ERROR", f"{description} import failed: {e}")
            all_ok = False

    return all_ok

def check_requirements():
    """Check requirements.txt for version conflicts."""
    print("\n=== Checking Requirements ===")

    # Check ruff version
    with open("requirements.txt") as f:
        reqs = f.read()
        if "ruff==0.12.4" in reqs:
            print_status("OK", "Ruff version matches CI (0.12.4)")
        elif "ruff==" in reqs:
            print_status("ERROR", "Ruff version mismatch - CI expects 0.12.4")
            return False
        else:
            print_status("WARNING", "Ruff not found in requirements.txt")

    return True

def check_test_files():
    """Check if test files exist and are valid."""
    print("\n=== Checking Test Files ===")

    test_files = [
        "tests/unit/synthesis/test_report_models.py",
        "tests/unit/synthesis/test_repetition_models.py",
        "tests/unit/synthesis/test_websocket_models.py",
        "tests/unit/synthesis/test_report_generator.py",
        "tests/unit/synthesis/test_repetition_scheduler.py",
        "tests/unit/synthesis/test_websocket_service.py",
        "tests/integration/synthesis/test_synthesis_integration.py",
    ]

    all_ok = True
    for test_file in test_files:
        if Path(test_file).exists():
            if check_python_syntax(test_file):
                print_status("OK", f"Test file valid: {test_file}")
            else:
                all_ok = False
        else:
            print_status("ERROR", f"Test file missing: {test_file}")
            all_ok = False

    return all_ok

def check_github_actions():
    """Check GitHub Actions workflow files."""
    print("\n=== Checking GitHub Actions ===")

    workflow_file = ".github/workflows/ci-v2.8.yml"
    if check_file_exists(workflow_file, "Main CI workflow"):
        # Check for common issues
        with open(workflow_file) as f:
            content = f.read()
            if "RUFF_VERSION: '0.12.4'" in content:
                print_status("OK", "CI ruff version set correctly")
            else:
                print_status("WARNING", "CI ruff version may not match requirements")

    return True

def main():
    """Run all validation checks."""
    print("=== Second Brain v2.8.2 CI/CD Validation ===\n")

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Add project root to Python path
    sys.path.insert(0, str(project_root))

    checks = [
        ("Python Files", lambda: all([
            check_file_exists("app/models/__init__.py", "Models package init"),
            check_file_exists("app/models/synthesis/__init__.py", "Synthesis models init"),
            check_file_exists("app/services/__init__.py", "Services package init"),
            check_file_exists("app/services/synthesis/__init__.py", "Synthesis services init"),
        ])),
        ("Requirements", check_requirements),
        ("Test Files", check_test_files),
        ("GitHub Actions", check_github_actions),
        ("Imports", check_imports),
    ]

    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print(f"{GREEN}✓ All checks passed!{RESET}")
        print("Your code should pass CI/CD.")
    else:
        print(f"{RED}✗ Some checks failed!{RESET}")
        print("Please fix the issues before pushing to main.")
        sys.exit(1)

if __name__ == "__main__":
    main()
