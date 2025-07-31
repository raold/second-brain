#!/usr/bin/env python3
"""
Comprehensive Test Runner for Second Brain
Executes all test suites with proper reporting and metrics
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
import argparse


@dataclass
class TestResult:
    """Test execution result"""
    suite_name: str
    passed: int
    failed: int
    skipped: int
    duration: float
    coverage_percent: Optional[float] = None
    exit_code: int = 0


class ComprehensiveTestRunner:
    """Runner for all test suites with comprehensive reporting"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results: List[TestResult] = []
        
    def run_test_suite(self, suite_path: str, suite_name: str, args: List[str] = None) -> TestResult:
        """Run a specific test suite and capture results"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name}")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            suite_path,
            "-v",
            "--tb=short",
            "--durations=10"
        ]
        
        if args:
            cmd.extend(args)
            
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            summary_line = None
            
            for line in reversed(output_lines):
                if "passed" in line or "failed" in line or "error" in line:
                    summary_line = line
                    break
            
            # Extract test counts
            passed = failed = skipped = 0
            if summary_line:
                if "passed" in summary_line:
                    try:
                        passed = int(summary_line.split()[0])
                    except (ValueError, IndexError):
                        pass
                        
                for word in summary_line.split():
                    if "failed" in word:
                        try:
                            failed = int(word.replace("failed", "").replace(",", ""))
                        except ValueError:
                            pass
                    elif "skipped" in word:
                        try:
                            skipped = int(word.replace("skipped", "").replace(",", ""))
                        except ValueError:
                            pass
            
            test_result = TestResult(
                suite_name=suite_name,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration,
                exit_code=result.returncode
            )
            
            # Print results
            print(f"\n{suite_name} Results:")
            print(f"  ✅ Passed: {passed}")
            print(f"  ❌ Failed: {failed}")
            print(f"  ⏭️  Skipped: {skipped}")
            print(f"  ⏱️  Duration: {duration:.2f}s")
            print(f"  🔄 Exit Code: {result.returncode}")
            
            if result.returncode != 0:
                print(f"\n❌ {suite_name} had failures:")
                print(result.stdout[-1000:])  # Last 1000 chars
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr[-500:])  # Last 500 chars
                    
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {suite_name} timed out after {duration:.2f}s")
            return TestResult(
                suite_name=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=124  # Timeout exit code
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {suite_name} crashed: {e}")
            return TestResult(
                suite_name=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=1
            )
            
    def run_coverage_analysis(self) -> Optional[float]:
        """Run coverage analysis across all tests"""
        print(f"\n{'='*60}")
        print("Running Coverage Analysis")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "-q"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=900  # 15 minutes
            )
            
            # Parse coverage from JSON report
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                    print(f"📊 Total Coverage: {total_coverage:.1f}%")
                    return total_coverage
                    
        except Exception as e:
            print(f"Coverage analysis failed: {e}")
            
        return None
        
    def run_performance_benchmarks(self) -> Dict[str, float]:
        """Run performance benchmarks"""
        print(f"\n{'='*60}")
        print("Running Performance Benchmarks")
        print(f"{'='*60}")
        
        benchmarks = {}
        
        # Run performance tests with timing
        perf_result = self.run_test_suite(
            "tests/performance/",
            "Performance Benchmarks",
            ["--benchmark-only"] if self.has_benchmark_plugin() else []
        )
        
        benchmarks["performance_suite"] = perf_result.duration
        
        return benchmarks
        
    def has_benchmark_plugin(self) -> bool:
        """Check if pytest-benchmark is available"""
        try:
            import pytest_benchmark
            return True
        except ImportError:
            return False
            
    def generate_report(self, coverage: Optional[float] = None, benchmarks: Dict[str, float] = None):
        """Generate comprehensive test report"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST REPORT")
        print(f"{'='*80}")
        
        total_passed = sum(r.passed for r in self.test_results)
        total_failed = sum(r.failed for r in self.test_results)
        total_skipped = sum(r.skipped for r in self.test_results)
        total_duration = sum(r.duration for r in self.test_results)
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"  ✅ Total Passed:  {total_passed}")
        print(f"  ❌ Total Failed:  {total_failed}")
        print(f"  ⏭️  Total Skipped: {total_skipped}")
        print(f"  ⏱️  Total Duration: {total_duration:.2f}s")
        
        if coverage:
            print(f"  📈 Code Coverage: {coverage:.1f}%")
            
        success_rate = (total_passed / (total_passed + total_failed)) * 100 if (total_passed + total_failed) > 0 else 0
        print(f"  🎯 Success Rate:  {success_rate:.1f}%")
        
        print(f"\n📋 SUITE BREAKDOWN:")
        for result in self.test_results:
            status = "✅" if result.exit_code == 0 else "❌"
            print(f"  {status} {result.suite_name:<25} {result.passed:>3}P {result.failed:>3}F {result.skipped:>3}S ({result.duration:>6.2f}s)")
            
        if benchmarks:
            print(f"\n⚡ PERFORMANCE BENCHMARKS:")
            for name, duration in benchmarks.items():
                print(f"  {name:<30} {duration:>8.2f}s")
                
        # Quality Gates
        print(f"\n🚨 QUALITY GATES:")
        gates = [
            ("Success Rate >= 90%", success_rate >= 90, f"{success_rate:.1f}%"),
            ("No Critical Failures", total_failed == 0, f"{total_failed} failures"),
            ("Coverage >= 80%", coverage and coverage >= 80, f"{coverage:.1f}%" if coverage else "N/A"),
            ("Total Duration < 10min", total_duration < 600, f"{total_duration:.2f}s"),
        ]
        
        all_gates_passed = True
        for name, passed, value in gates:
            status = "✅" if passed else "❌"
            print(f"  {status} {name:<25} {value}")
            if not passed:
                all_gates_passed = False
                
        print(f"\n🏆 OVERALL STATUS: {'✅ PASSED' if all_gates_passed else '❌ FAILED'}")
        
        return all_gates_passed
        
    def save_results(self, filename: str = "test_results.json"):
        """Save test results to JSON file"""
        results_data = {
            "timestamp": time.time(),
            "total_duration": sum(r.duration for r in self.test_results),
            "suites": [
                {
                    "name": r.suite_name,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "duration": r.duration,
                    "exit_code": r.exit_code
                }
                for r in self.test_results
            ]
        }
        
        with open(self.project_root / filename, 'w') as f:
            json.dump(results_data, f, indent=2)
            
        print(f"📝 Results saved to {filename}")


def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--coverage", action="store_true", help="Run coverage analysis")
    parser.add_argument("--no-report", action="store_true", help="Skip final report")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    runner = ComprehensiveTestRunner(project_root)
    
    print("🧠 Second Brain Comprehensive Test Suite")
    print(f"📁 Project Root: {project_root}")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine which test suites to run
    suites_to_run = []
    
    if args.unit or args.fast or (not any([args.integration, args.performance])):
        suites_to_run.extend([
            ("tests/unit/test_basic_modules.py", "Basic Module Tests"),
            ("tests/unit/test_memory_service.py", "Memory Service Tests"),
            ("tests/unit/test_database_operations.py", "Database Operations Tests"),
            ("tests/unit/test_error_handling_comprehensive.py", "Error Handling Tests"),
        ])
        
    if args.integration or (not any([args.unit, args.performance, args.fast])):
        suites_to_run.extend([
            ("tests/integration/test_memory_api_endpoints.py", "Memory API Tests"),
            ("tests/integration/test_security_validation.py", "Security Validation Tests"),
            ("tests/integration/test_monitoring_endpoints.py", "Monitoring Tests"),
            ("tests/integration/test_api_endpoints.py", "Legacy API Tests"),
        ])
        
    if args.performance and not args.fast:
        suites_to_run.extend([
            ("tests/performance/test_load_scenarios.py", "Load Testing"),
            ("tests/performance/test_performance_benchmark.py", "Performance Benchmarks"),
        ])
        
    # Run test suites
    for suite_path, suite_name in suites_to_run:
        full_path = project_root / suite_path
        if full_path.exists():
            result = runner.run_test_suite(str(full_path), suite_name)
            runner.test_results.append(result)
        else:
            print(f"⚠️  Skipping {suite_name} - file not found: {full_path}")
            
    # Run coverage analysis if requested
    coverage = None
    if args.coverage and not args.fast:
        coverage = runner.run_coverage_analysis()
        
    # Run performance benchmarks
    benchmarks = {}
    if args.performance and not args.fast:
        benchmarks = runner.run_performance_benchmarks()
        
    # Generate report
    if not args.no_report:
        all_passed = runner.generate_report(coverage, benchmarks)
        runner.save_results()
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
    else:
        # Just exit with success if any tests passed
        total_failed = sum(r.failed for r in runner.test_results)
        sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()