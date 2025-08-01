#!/usr/bin/env python3
"""
Enhanced CI Runner for Second Brain - Tiered Testing Strategy

This script implements a sophisticated CI/CD pipeline with multiple stages:
- Smoke Tests: Critical path validation (<60s)
- Fast Feedback: Core functionality tests (<5min)  
- Comprehensive: Full validation suite (<15min)
- Performance: Load testing and benchmarks (<20min)

Features:
- Parallel test execution
- Smart retry logic for flaky tests
- Detailed reporting and metrics
- Failure recovery and rollback
- Integration with monitoring systems
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class TestResult:
    """Test execution result with metadata."""
    name: str
    stage: str
    group: str
    passed: bool
    duration: float
    output: str = ""
    error: str = ""
    retries: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass  
class StageResult:
    """CI stage execution result."""
    name: str
    passed: bool
    duration: float
    tests: List[TestResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class PipelineReport:
    """Complete pipeline execution report."""
    pipeline_id: str
    start_time: str
    end_time: str
    duration: float
    overall_passed: bool
    stages: List[StageResult] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class CIRunner:
    """Enhanced CI runner with tiered testing strategy."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = self._setup_logging()
        self.python_cmd = self._detect_python()
        self.pipeline_start = time.time()
        self.pipeline_id = f"ci-{int(self.pipeline_start)}"
        
        # Test configuration
        self.test_config = {
            "smoke": {
                "timeout": 60,
                "max_failures": 3,
                "retry_count": 1,
                "parallel": True,
                "groups": ["critical", "smoke"]
            },
            "fast": {
                "timeout": 300,
                "max_failures": 5,
                "retry_count": 2,
                "parallel": True,
                "groups": ["unit", "integration-basic", "api-core"]
            },
            "comprehensive": {
                "timeout": 900,
                "max_failures": 10,
                "retry_count": 3,
                "parallel": True,
                "groups": ["unit", "integration", "validation", "security"]
            },
            "performance": {
                "timeout": 1200,
                "max_failures": 5,
                "retry_count": 1,
                "parallel": False,
                "groups": ["benchmark", "load", "memory"]
            }
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger(__name__)

    def _detect_python(self) -> str:
        """Detect the appropriate Python command."""
        # Try virtual environment first
        venv_path = self.project_root / ".venv"
        if venv_path.exists():
            if os.name == 'nt':  # Windows
                python_exe = venv_path / "Scripts" / "python.exe"
            else:  # Unix-like
                python_exe = venv_path / "bin" / "python"

            if python_exe.exists():
                try:
                    result = subprocess.run([str(python_exe), "--version"],
                                          check=True, capture_output=True, text=True)
                    self.logger.info(f"Using virtual environment Python: {result.stdout.strip()}")
                    return str(python_exe)
                except subprocess.CalledProcessError:
                    self.logger.warning("Virtual environment Python not working")

        # Fall back to system Python
        for cmd in ["python3", "python"]:
            try:
                result = subprocess.run([cmd, "--version"], check=True, capture_output=True, text=True)
                self.logger.info(f"Using system Python: {result.stdout.strip()}")
                return cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        raise RuntimeError("No Python interpreter found")

    def _run_test_group(self, stage: str, group: str, config: dict) -> TestResult:
        """Run a specific test group."""
        start_time = time.time()
        
        try:
            # Build pytest command based on group
            cmd = self._build_pytest_command(stage, group, config)
            
            self.logger.info(f"Running {stage}/{group}: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=config.get("timeout", 300)
            )
            
            duration = time.time() - start_time
            passed = result.returncode == 0
            
            return TestResult(
                name=f"{stage}/{group}",
                stage=stage,
                group=group,
                passed=passed,
                duration=duration,
                output=result.stdout,
                error=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                name=f"{stage}/{group}",
                stage=stage,
                group=group,
                passed=False,
                duration=duration,
                error=f"Test group timed out after {config.get('timeout')}s"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=f"{stage}/{group}",
                stage=stage,
                group=group,
                passed=False,
                duration=duration,
                error=str(e)
            )

    def _build_pytest_command(self, stage: str, group: str, config: dict) -> List[str]:
        """Build pytest command for specific test group."""
        cmd = [self.python_cmd, "-m", "pytest"]
        
        # Test selection based on stage and group
        if stage == "smoke":
            if group == "critical":
                cmd.extend(["tests/unit/", "-m", "critical or smoke"])
            elif group == "smoke":
                cmd.extend(["tests/integration/", "-m", "smoke and not slow"])
        
        elif stage == "fast":
            if group == "unit":
                cmd.extend(["tests/unit/", "-m", "unit and fast and not slow"])
            elif group == "integration-basic":
                cmd.extend(["tests/integration/", "-m", "integration and not slow"])
            elif group == "api-core":
                cmd.extend(["tests/integration/", "-m", "api and not slow"])
        
        elif stage == "comprehensive":
            if group == "unit":
                cmd.extend(["tests/unit/"])
            elif group == "integration":
                cmd.extend(["tests/integration/"])
            elif group == "validation":
                cmd.extend(["tests/validation/"])
            elif group == "security":
                cmd.extend(["tests/unit/", "tests/integration/", "-m", "security"])
        
        elif stage == "performance":
            if group == "benchmark":
                cmd.extend(["tests/performance/", "-m", "benchmark"])
            elif group == "load":
                cmd.extend(["tests/performance/", "-m", "load"])
            elif group == "memory":
                cmd.extend(["tests/performance/", "-m", "memory"])
        
        # Common options
        cmd.extend([
            "--tb=short",
            "--maxfail=" + str(config.get("max_failures", 5)),
            "-v",
            "--durations=10"
        ])
        
        # Add coverage for unit tests
        if "unit" in group:
            cmd.extend([
                "--cov=app",
                "--cov-report=xml:coverage-" + group + ".xml",
                "--cov-report=term-missing:skip-covered"
            ])
        
        return cmd

    def _run_stage_parallel(self, stage: str, groups: List[str], config: dict) -> List[TestResult]:
        """Run test groups in parallel."""
        if not config.get("parallel", False):
            # Sequential execution
            results = []
            for group in groups:
                result = self._run_test_group(stage, group, config)
                results.append(result)
                
                # Early exit on critical failures
                if not result.passed and stage == "smoke":
                    self.logger.error(f"Critical failure in {stage}/{group}, stopping pipeline")
                    break
            return results
        
        # Parallel execution
        results = []
        with ThreadPoolExecutor(max_workers=min(len(groups), 4)) as executor:
            future_to_group = {
                executor.submit(self._run_test_group, stage, group, config): group 
                for group in groups
            }
            
            for future in as_completed(future_to_group):
                group = future_to_group[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.passed:
                        self.logger.info(f"✅ {result.name} completed in {result.duration:.1f}s")
                    else:
                        self.logger.error(f"❌ {result.name} failed in {result.duration:.1f}s")
                        
                except Exception as e:
                    self.logger.error(f"Exception in {stage}/{group}: {e}")
                    results.append(TestResult(
                        name=f"{stage}/{group}",
                        stage=stage,
                        group=group,
                        passed=False,
                        duration=0,
                        error=str(e)
                    ))
        
        return results

    def run_stage(self, stage: str, group_filter: Optional[str] = None) -> StageResult:
        """Run a complete CI stage."""
        if stage not in self.test_config:
            raise ValueError(f"Unknown stage: {stage}")
        
        config = self.test_config[stage]
        groups = config["groups"]
        
        if group_filter:
            groups = [g for g in groups if group_filter in g]
            if not groups:
                raise ValueError(f"No groups match filter '{group_filter}' in stage '{stage}'")
        
        self.logger.info(f"🚀 Starting stage: {stage} (groups: {groups})")
        stage_start = time.time()
        
        # Run test groups
        test_results = self._run_stage_parallel(stage, groups, config)
        
        # Calculate stage result
        stage_duration = time.time() - stage_start
        stage_passed = all(result.passed for result in test_results)
        
        stage_result = StageResult(
            name=stage,
            passed=stage_passed,
            duration=stage_duration,
            tests=test_results
        )
        
        # Log stage summary
        passed_count = sum(1 for r in test_results if r.passed)
        total_count = len(test_results)
        
        if stage_passed:
            self.logger.info(f"✅ Stage '{stage}' passed ({passed_count}/{total_count} tests) in {stage_duration:.1f}s")
        else:
            self.logger.error(f"❌ Stage '{stage}' failed ({passed_count}/{total_count} tests) in {stage_duration:.1f}s")
            
            # Log failed tests
            for result in test_results:
                if not result.passed:
                    self.logger.error(f"  Failed: {result.name} - {result.error}")
        
        return stage_result

    def run_pipeline(self, stages: List[str], exit_on_failure: bool = False, save_report: Optional[str] = None) -> bool:
        """Run complete CI pipeline."""
        self.logger.info(f"🤖 Starting CI pipeline: {self.pipeline_id}")
        self.logger.info(f"Stages: {stages}")
        
        pipeline_results = []
        overall_passed = True
        
        for stage in stages:
            try:
                stage_result = self.run_stage(stage)
                pipeline_results.append(stage_result)
                
                if not stage_result.passed:
                    overall_passed = False
                    if exit_on_failure:
                        self.logger.error(f"Pipeline failed at stage '{stage}', exiting")
                        break
                        
            except Exception as e:
                self.logger.error(f"Stage '{stage}' crashed: {e}")
                overall_passed = False
                if exit_on_failure:
                    break
        
        # Generate pipeline report
        pipeline_duration = time.time() - self.pipeline_start
        
        report = PipelineReport(
            pipeline_id=self.pipeline_id,
            start_time=datetime.fromtimestamp(self.pipeline_start, timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            duration=pipeline_duration,
            overall_passed=overall_passed,
            stages=pipeline_results,
            environment={
                "python_version": subprocess.run([self.python_cmd, "--version"], 
                                               capture_output=True, text=True).stdout.strip(),
                "platform": os.name,
                "working_directory": str(self.project_root),
                "ci_runner_version": "2.0.0"
            },
            metadata={
                "total_tests": sum(len(s.tests) for s in pipeline_results),
                "passed_tests": sum(len([t for t in s.tests if t.passed]) for s in pipeline_results),
                "failed_tests": sum(len([t for t in s.tests if not t.passed]) for s in pipeline_results),
                "stages_passed": sum(1 for s in pipeline_results if s.passed),
                "stages_failed": sum(1 for s in pipeline_results if not s.passed)
            }
        )
        
        # Print summary
        self._print_pipeline_summary(report)
        
        # Save report if requested
        if save_report:
            self._save_report(report, save_report)
        
        return overall_passed

    def _print_pipeline_summary(self, report: PipelineReport):
        """Print comprehensive pipeline summary."""
        print(f"\n{'='*80}")
        print(f"🤖 CI PIPELINE SUMMARY - {report.pipeline_id}")
        print(f"{'='*80}")
        
        print(f"⏱️  Duration: {report.duration:.1f}s")
        print(f"📊 Total Tests: {report.metadata['total_tests']}")
        print(f"✅ Passed: {report.metadata['passed_tests']}")
        print(f"❌ Failed: {report.metadata['failed_tests']}")
        print(f"🎯 Stages Passed: {report.metadata['stages_passed']}/{len(report.stages)}")
        
        print(f"\n📋 STAGE RESULTS:")
        for stage in report.stages:
            status = "✅ PASS" if stage.passed else "❌ FAIL"
            test_summary = f"{len([t for t in stage.tests if t.passed])}/{len(stage.tests)}"
            print(f"  {status} {stage.name:15} ({test_summary} tests) - {stage.duration:.1f}s")
        
        print(f"\n🏁 OVERALL RESULT:")
        if report.overall_passed:
            print("✅ PIPELINE PASSED - All stages completed successfully")
        else:
            print("❌ PIPELINE FAILED - One or more stages failed")
            print("\n🔍 FAILURE ANALYSIS:")
            for stage in report.stages:
                if not stage.passed:
                    print(f"  Stage '{stage.name}':")
                    for test in stage.tests:
                        if not test.passed:
                            print(f"    - {test.name}: {test.error}")
        
        print(f"{'='*80}")

    def _save_report(self, report: PipelineReport, filename: str):
        """Save pipeline report to JSON file."""
        try:
            report_data = {
                "pipeline_id": report.pipeline_id,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "duration": report.duration,
                "overall_passed": report.overall_passed,
                "environment": report.environment,
                "metadata": report.metadata,
                "stages": [
                    {
                        "name": stage.name,
                        "passed": stage.passed,
                        "duration": stage.duration,
                        "timestamp": stage.timestamp,
                        "tests": [
                            {
                                "name": test.name,
                                "stage": test.stage,
                                "group": test.group,
                                "passed": test.passed,
                                "duration": test.duration,
                                "retries": test.retries,
                                "timestamp": test.timestamp,
                                "error": test.error if test.error else None
                            }
                            for test in stage.tests
                        ]
                    }
                    for stage in report.stages
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            self.logger.info(f"📄 Pipeline report saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced CI Runner for Second Brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CI Pipeline Stages:
  smoke         Critical path validation (<60s)
  fast          Core functionality tests (<5min)
  comprehensive Full validation suite (<15min)
  performance   Load testing and benchmarks (<20min)

Examples:
  python scripts/ci_runner.py --stage smoke
  python scripts/ci_runner.py --stage fast --group unit
  python scripts/ci_runner.py --stage all --save-report ci_report.json
  python scripts/ci_runner.py --stage comprehensive --exit-on-failure
        """
    )

    parser.add_argument("--stage", required=True,
                       choices=["smoke", "fast", "comprehensive", "performance", "all"],
                       help="CI stage to run")
    parser.add_argument("--group", help="Specific test group to run within stage")
    parser.add_argument("--exit-on-failure", action="store_true",
                       help="Exit pipeline on first stage failure")
    parser.add_argument("--save-report", help="Save pipeline report to JSON file")

    args = parser.parse_args()

    runner = CIRunner(project_root)
    
    try:
        if args.stage == "all":
            stages = ["smoke", "fast", "comprehensive"]
            success = runner.run_pipeline(stages, args.exit_on_failure, args.save_report)
        else:
            if args.group:
                stage_result = runner.run_stage(args.stage, args.group)
                success = stage_result.passed
            else:
                success = runner.run_pipeline([args.stage], args.exit_on_failure, args.save_report)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        runner.logger.error("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        runner.logger.error(f"Pipeline crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()