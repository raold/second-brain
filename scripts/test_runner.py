#!/usr/bin/env python3
"""
Comprehensive Test Runner for Second Brain

This script provides a unified interface to run all types of tests:
- Unit tests (fast, no external dependencies)
- Integration tests (require services like database/redis)
- Validation tests (environment and CI readiness)
- End-to-end tests (full application testing)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.project_root = project_root
        self.python_cmd = self._detect_python()
        
    def _detect_python(self) -> str:
        """Detect the appropriate Python command."""
        # Try virtual environment first
        venv_path = self.project_root / ".venv"
        if venv_path.exists():
            if os.name == 'nt':  # Windows
                python_exe = venv_path / "Scripts" / "python.exe"
            else:  # Unix-like
                python_exe = venv_path / "bin" / "python"
            
            # Test if the venv python works
            try:
                result = subprocess.run([str(python_exe), "--version"], 
                                      check=True, capture_output=True, text=True)
                print(f"[INFO] Using virtual environment Python: {result.stdout.strip()}")
                return str(python_exe)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("[WARN] Virtual environment Python not working, falling back to system Python")
        
        # Fall back to system Python
        for cmd in ["python3", "python"]:
            try:
                result = subprocess.run([cmd, "--version"], check=True, capture_output=True, text=True)
                print(f"[INFO] Using system Python: {result.stdout.strip()}")
                return cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        raise RuntimeError("No Python interpreter found")
    
    def _run_command(self, cmd: List[str], description: str = "") -> bool:
        """Run a command and return success status."""
        print(f"{'='*60}")
        print(f"Running: {description or ' '.join(cmd)}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=True)
            print(f"[SUCCESS] {description}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[FAILED] {description} (exit code: {e.returncode})")
            return False
    
    def run_unit_tests(self, verbose: bool = True) -> bool:
        """Run unit tests."""
        cmd = [
            self.python_cmd, "-m", "pytest", 
            "tests/unit", 
            "-m", "unit",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
            
        return self._run_command(cmd, "Unit Tests")
    
    def run_integration_tests(self, verbose: bool = True) -> bool:
        """Run integration tests."""
        cmd = [
            self.python_cmd, "-m", "pytest",
            "tests/integration",
            "-m", "integration", 
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
            
        return self._run_command(cmd, "Integration Tests")
    
    def run_validation_tests(self) -> bool:
        """Run validation tests."""
        validation_scripts = [
            ("Environment Validation", "tests/validation/validate_ci_ready.py"),
            ("Domain Model Tests", "tests/validation/test_domain_only.py"),
        ]
        
        success = True
        for description, script_path in validation_scripts:
            if (self.project_root / script_path).exists():
                cmd = [self.python_cmd, script_path]
                if not self._run_command(cmd, description):
                    success = False
            else:
                print(f"[SKIP] {description} - script not found: {script_path}")
        
        return success
    
    def run_e2e_tests(self, verbose: bool = True) -> bool:
        """Run end-to-end tests."""
        cmd = [
            self.python_cmd, "-m", "pytest",
            "tests/e2e",
            "-m", "e2e",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
            
        return self._run_command(cmd, "End-to-End Tests")
    
    def run_coverage_report(self) -> bool:
        """Generate coverage report."""
        cmd = [
            self.python_cmd, "-m", "pytest",
            "--cov=src",
            "--cov=app", 
            "--cov-report=html",
            "--cov-report=term-missing",
            "tests/unit"
        ]
        
        return self._run_command(cmd, "Coverage Report")
    
    def run_linting(self) -> bool:
        """Run code linting."""
        linting_commands = [
            ([self.python_cmd, "-m", "ruff", "check", "src", "app"], "Ruff Linting"),
            ([self.python_cmd, "-m", "black", "--check", "src", "app"], "Black Formatting Check"),
            ([self.python_cmd, "-m", "isort", "--check-only", "src", "app"], "Import Sorting Check"),
        ]
        
        success = True
        for cmd, description in linting_commands:
            try:
                if not self._run_command(cmd, description):
                    success = False
            except Exception:
                print(f"[SKIP] {description} - tool not available")
        
        return success
    
    def run_all_tests(self, include_slow: bool = False) -> bool:
        """Run all test suites."""
        print("[RUN] Running Complete Test Suite")
        print(f"Project Root: {self.project_root}")
        print(f"Python: {self.python_cmd}")
        
        results = []
        
        # Quick tests first
        results.append(("Validation", self.run_validation_tests()))
        results.append(("Unit Tests", self.run_unit_tests()))
        results.append(("Linting", self.run_linting()))
        
        # Slower/optional tests
        if include_slow:
            results.append(("Integration Tests", self.run_integration_tests()))
            results.append(("E2E Tests", self.run_e2e_tests()))
            results.append(("Coverage Report", self.run_coverage_report()))
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        all_passed = True
        for test_type, passed in results:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {test_type}")
            if not passed:
                all_passed = False
        
        print(f"\n{'='*60}")
        if all_passed:
            print("[SUCCESS] ALL TESTS PASSED!")
        else:
            print("[FAILURE] SOME TESTS FAILED!")
        print(f"{'='*60}")
        
        return all_passed

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Second Brain Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_runner.py --unit              # Run only unit tests
  python scripts/test_runner.py --integration       # Run only integration tests  
  python scripts/test_runner.py --validation        # Run only validation tests
  python scripts/test_runner.py --all               # Run all tests (fast)
  python scripts/test_runner.py --all --slow        # Run all tests including slow ones
  python scripts/test_runner.py --coverage          # Generate coverage report
  python scripts/test_runner.py --lint              # Run linting only
        """
    )
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests") 
    parser.add_argument("--validation", action="store_true", help="Run validation tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--all", action="store_true", help="Run all test suites")
    parser.add_argument("--slow", action="store_true", help="Include slow tests when using --all")
    parser.add_argument("--quiet", action="store_true", help="Reduce verbosity")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    success = True
    verbose = not args.quiet
    
    # Run specific test types
    if args.unit:
        success &= runner.run_unit_tests(verbose)
    elif args.integration:
        success &= runner.run_integration_tests(verbose)
    elif args.validation:
        success &= runner.run_validation_tests()
    elif args.e2e:
        success &= runner.run_e2e_tests(verbose)
    elif args.coverage:
        success &= runner.run_coverage_report()
    elif args.lint:
        success &= runner.run_linting()
    elif args.all:
        success &= runner.run_all_tests(include_slow=args.slow)
    else:
        # Default: run validation and unit tests
        print("No specific test type specified. Running validation and unit tests...")
        success &= runner.run_validation_tests()
        success &= runner.run_unit_tests(verbose)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()