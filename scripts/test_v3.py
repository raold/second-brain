#!/usr/bin/env python3
"""
Test runner for v3.0.0 tests.

Provides convenient commands for running different test suites.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list[str], env: dict = None) -> int:
    """Run a command and return exit code."""
    print(f"Running: {' '.join(cmd)}")

    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    result = subprocess.run(cmd, env=process_env)
    return result.returncode


def run_unit_tests(args):
    """Run unit tests."""
    cmd = [
        "pytest",
        "tests/v3/unit",
        "-v",
        "-m", "unit",
    ]

    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])

    if args.parallel:
        cmd.extend(["-n", "auto"])

    if args.verbose:
        cmd.append("-vv")

    return run_command(cmd)


def run_integration_tests(args):
    """Run integration tests."""
    env = {}

    if args.mock:
        env["        env["MOCK_EMBEDDINGS"] = "true"
        marker = "integration and not requires_real_db"
    else:
        marker = "integration"

    cmd = [
        "pytest",
        "tests/v3/integration",
        "-v",
        "-m", marker,
    ]

    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])

    if args.verbose:
        cmd.append("-vv")

    return run_command(cmd, env)


def run_api_tests(args):
    """Run API endpoint tests."""
    cmd = [
        "pytest",
        "tests/v3/api",
        "-v",
    ]

    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])

    return run_command(cmd)


def run_e2e_tests(args):
    """Run end-to-end tests."""
    cmd = [
        "pytest",
        "tests/v3/e2e",
        "-v",
        "-m", "e2e",
    ]

    if args.slow:
        cmd.extend(["--timeout", "600"])

    return run_command(cmd)


def run_performance_tests(args):
    """Run performance tests."""
    cmd = [
        "pytest",
        "tests/v3/performance",
        "-v",
        "-m", "performance",
        "--benchmark-only",
    ]

    if args.save:
        cmd.extend(["--benchmark-save", args.save])

    if args.compare:
        cmd.extend(["--benchmark-compare", args.compare])

    return run_command(cmd)


def run_all_tests(args):
    """Run all tests."""
    print("Running all v3.0.0 tests...")

    # Run tests in order
    suites = [
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("API Tests", run_api_tests),
        ("E2E Tests", run_e2e_tests),
    ]

    if args.performance:
        suites.append(("Performance Tests", run_performance_tests))

    results = {}
    for name, func in suites:
        print(f"\n{'='*60}")
        print(f"Running {name}")
        print('='*60)

        result = func(args)
        results[name] = result

        if result != 0 and not args.continue_on_failure:
            print(f"\n{name} failed! Stopping test run.")
            break

    # Print summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print('='*60)

    for name, result in results.items():
        status = "PASSED" if result == 0 else "FAILED"
        print(f"{name}: {status}")

    return 0 if all(r == 0 for r in results.values()) else 1


def check_services(args):
    """Check if required services are running."""
    print("Checking required services...")

    services = {
        "PostgreSQL": ("localhost", 5432),
        "Redis": ("localhost", 6379),
        "RabbitMQ": ("localhost", 5672),
        "MinIO": ("localhost", 9000),
    }

    import socket

    all_running = True
    for name, (host, port) in services.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print(f"✓ {name} is running on {host}:{port}")
            else:
                print(f"✗ {name} is not accessible on {host}:{port}")
                all_running = False
        except Exception as e:
            print(f"✗ {name} check failed: {e}")
            all_running = False

    if not all_running and not args.mock:
        print("\nSome services are not running. Use --mock to run with mocks.")
        return 1

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run v3.0.0 tests")

    subparsers = parser.add_subparsers(dest="command", help="Test suite to run")

    # Unit tests
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    unit_parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    unit_parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    unit_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Integration tests
    integration_parser = subparsers.add_parser("integration", help="Run integration tests")
    integration_parser.add_argument("--mock", action="store_true", help="Use mock services")
    integration_parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    integration_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # API tests
    api_parser = subparsers.add_parser("api", help="Run API tests")
    api_parser.add_argument("--coverage", action="store_true", help="Generate coverage report")

    # E2E tests
    e2e_parser = subparsers.add_parser("e2e", help="Run end-to-end tests")
    e2e_parser.add_argument("--slow", action="store_true", help="Run slow tests")

    # Performance tests
    perf_parser = subparsers.add_parser("performance", help="Run performance tests")
    perf_parser.add_argument("--save", help="Save benchmark results")
    perf_parser.add_argument("--compare", help="Compare with saved results")

    # All tests
    all_parser = subparsers.add_parser("all", help="Run all tests")
    all_parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    all_parser.add_argument("--mock", action="store_true", help="Use mock services")
    all_parser.add_argument("--performance", action="store_true", help="Include performance tests")
    all_parser.add_argument("--continue-on-failure", action="store_true", help="Continue even if tests fail")

    # Check services
    check_parser = subparsers.add_parser("check", help="Check if services are running")
    check_parser.add_argument("--mock", action="store_true", help="Check for mock mode")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Map commands to functions
    commands = {
        "unit": run_unit_tests,
        "integration": run_integration_tests,
        "api": run_api_tests,
        "e2e": run_e2e_tests,
        "performance": run_performance_tests,
        "all": run_all_tests,
        "check": check_services,
    }

    func = commands.get(args.command)
    if func:
        return func(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
