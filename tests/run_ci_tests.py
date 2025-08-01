#!/usr/bin/env python3
"""
CI Test Runner - Optimized for GitHub Actions
Runs tests with proper timeout, retry, and resource management.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Optional


class CITestRunner:
    """Test runner optimized for CI environments."""

    def __init__(self):
        self.start_time = time.time()
        self.results = {}
        self.project_root = Path(__file__).parent.parent
        self.test_dir = Path(__file__).parent

        # CI environment detection
        self.is_ci = os.getenv("CI", "").lower() in ("true", "1", "yes")
        self.is_github_actions = os.getenv("GITHUB_ACTIONS", "").lower() == "true"

        # Timeout settings (more generous in CI)
        self.timeout_multiplier = 2.0 if self.is_ci else 1.0
        self.max_test_time = int(300 * self.timeout_multiplier)  # 5-10 minutes

        print(f"CI Test Runner starting...")
        print(f"CI Environment: {self.is_ci}")
        print(f"GitHub Actions: {self.is_github_actions}")
        print(f"Timeout Multiplier: {self.timeout_multiplier}")
        print(f"Max Test Time: {self.max_test_time}s")

    def setup_environment(self) -> bool:
        """Setup test environment with proper isolation."""
        try:
            print("\n=== Environment Setup ===")

            # Set critical environment variables
            os.environ["ENVIRONMENT"] = "test"
            os.environ["PYTHONPATH"] = str(self.project_root)
            os.environ["DISABLE_EXTERNAL_SERVICES"] = "true"
            os.environ["MOCK_EXTERNAL_APIS"] = "true"

            # CI-specific settings
            if self.is_ci:
                os.environ["LOG_LEVEL"] = "ERROR"  # Reduce noise
                os.environ["PYTEST_TIMEOUT"] = str(self.max_test_time)

            print("✓ Environment variables set")

            # Verify Python path
            sys.path.insert(0, str(self.project_root))
            print(f"✓ Python path configured: {self.project_root}")

            # Check pytest availability
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"✗ Pytest not available: {result.stderr}")
                return False

            print(f"✓ Pytest available: {result.stdout.strip()}")
            return True

        except Exception as e:
            print(f"✗ Environment setup failed: {e}")
            return False

    def run_validation_tests(self) -> bool:
        """Run basic validation tests first."""
        try:
            print("\n=== Validation Tests ===")

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.test_dir / "validation"),
                "-v",
                "--tb=short",
                "-m",
                "validation",
                "--timeout",
                str(60),  # Short timeout for validation
                "--maxfail=3",  # Stop early on validation failures
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=120,  # 2 minutes max for validation
                capture_output=True,
                text=True,
            )

            self.results["validation"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print("✓ Validation tests passed")
                return True
            else:
                print(f"✗ Validation tests failed: {result.returncode}")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])
                return False

        except subprocess.TimeoutExpired:
            print("✗ Validation tests timed out")
            return False
        except Exception as e:
            print(f"✗ Validation tests error: {e}")
            return False

    def run_unit_tests(self) -> bool:
        """Run unit tests with proper isolation."""
        try:
            print("\n=== Unit Tests ===")

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.test_dir / "unit"),
                "-v",
                "--tb=short",
                "-m",
                "unit",
                "--timeout",
                str(self.max_test_time),
                "--maxfail=10",  # Allow some failures but not too many
                "--disable-warnings",
            ]

            # Add CI-specific options
            if self.is_ci:
                cmd.extend(["--quiet", "--no-header"])

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=self.max_test_time,
                capture_output=True,
                text=True,
            )

            self.results["unit"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print("✓ Unit tests passed")
                return True
            else:
                print(f"✗ Unit tests failed: {result.returncode}")
                print("STDOUT:", result.stdout[-1000:])  # Last 1000 chars
                print("STDERR:", result.stderr[-1000:])
                return False

        except subprocess.TimeoutExpired:
            print(f"✗ Unit tests timed out after {self.max_test_time}s")
            return False
        except Exception as e:
            print(f"✗ Unit tests error: {e}")
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests if enabled."""
        try:
            # Skip integration tests in CI unless explicitly enabled
            if self.is_ci and not os.getenv("RUN_INTEGRATION_TESTS"):
                print("\n=== Integration Tests ===")
                print(
                    "⚠ Integration tests skipped in CI (set RUN_INTEGRATION_TESTS=true to enable)"
                )
                return True

            print("\n=== Integration Tests ===")

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.test_dir / "integration"),
                "-v",
                "--tb=short",
                "-m",
                "integration",
                "--timeout",
                str(self.max_test_time),
                "--maxfail=5",
                "--disable-warnings",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=self.max_test_time,
                capture_output=True,
                text=True,
            )

            self.results["integration"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print("✓ Integration tests passed")
                return True
            else:
                print(f"✗ Integration tests failed: {result.returncode}")
                print("STDOUT:", result.stdout[-1000:])
                print("STDERR:", result.stderr[-1000:])
                return False

        except subprocess.TimeoutExpired:
            print(f"✗ Integration tests timed out after {self.max_test_time}s")
            return False
        except Exception as e:
            print(f"✗ Integration tests error: {e}")
            return False

    def run_example_tests(self) -> bool:
        """Run example tests to verify best practices."""
        try:
            print("\n=== Example Tests ===")

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.test_dir / "examples"),
                "-v",
                "--tb=short",
                "--timeout",
                str(120),  # Examples should be fast
                "--disable-warnings",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=180,  # 3 minutes max
                capture_output=True,
                text=True,
            )

            self.results["examples"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print("✓ Example tests passed")
                return True
            else:
                print(f"⚠ Example tests failed: {result.returncode}")
                # Examples failing shouldn't break CI
                return True

        except Exception as e:
            print(f"⚠ Example tests error: {e}")
            return True  # Non-critical

    def generate_report(self, success: bool) -> None:
        """Generate test report."""
        try:
            total_time = time.time() - self.start_time

            print(f"\n=== Test Report ===")
            print(f"Total Time: {total_time:.2f}s")
            print(f"Overall Result: {'✓ PASSED' if success else '✗ FAILED'}")

            # Summary by category
            for category, result in self.results.items():
                status = "✓ PASSED" if result["returncode"] == 0 else "✗ FAILED"
                print(f"{category.title()}: {status}")

            # Save detailed report for CI
            if self.is_ci:
                report = {
                    "success": success,
                    "total_time": total_time,
                    "timestamp": time.time(),
                    "environment": {
                        "ci": self.is_ci,
                        "github_actions": self.is_github_actions,
                        "timeout_multiplier": self.timeout_multiplier,
                    },
                    "results": self.results,
                }

                report_file = self.project_root / "test_report.json"
                with open(report_file, "w") as f:
                    json.dump(report, f, indent=2)

                print(f"Detailed report saved: {report_file}")

        except Exception as e:
            print(f"Report generation error: {e}")

    def run_all(self) -> bool:
        """Run complete test suite."""
        try:
            # Setup
            if not self.setup_environment():
                return False

            # Run test categories in order
            steps = [
                ("Validation", self.run_validation_tests),
                ("Unit", self.run_unit_tests),
                ("Integration", self.run_integration_tests),
                ("Examples", self.run_example_tests),
            ]

            for step_name, step_func in steps:
                print(f"\n{'='*50}")
                print(f"Running {step_name} Tests")
                print(f"{'='*50}")

                if not step_func():
                    print(f"✗ {step_name} tests failed - stopping execution")
                    return False

            return True

        except KeyboardInterrupt:
            print("\n✗ Test execution interrupted")
            return False
        except Exception as e:
            print(f"✗ Test execution error: {e}")
            return False


def main():
    """Main entry point."""
    runner = CITestRunner()
    success = runner.run_all()
    runner.generate_report(success)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
