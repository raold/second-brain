#!/usr/bin/env python3
"""
Performance Testing Runner for Second Brain v3.0.0
Orchestrates both benchmark and load testing suites
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import psutil


def setup_performance_environment():
    """Setup environment for performance testing"""
    print("🔧 Setting up performance testing environment...")
    
    # Ensure test database is ready
    env_vars = {
        "ENVIRONMENT": "performance",
        "USE_MOCK_DATABASE": "false", 
        "LOG_LEVEL": "WARNING",  # Reduce logging overhead
        "API_TOKENS": "test-performance-key,test-load-key",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "mock-key-for-testing")
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("✅ Performance environment configured")
    return env_vars


def check_system_resources():
    """Check if system has enough resources for load testing"""
    print("📊 Checking system resources...")
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB
        print("⚠️  Warning: Low available memory ({:.1f}GB). Load testing may fail.".format(
            memory.available / 1024 / 1024 / 1024
        ))
        return False
    
    # Check CPU
    cpu_count = psutil.cpu_count()
    if cpu_count < 2:
        print("⚠️  Warning: Low CPU count ({}). Load testing may be limited.".format(cpu_count))
    
    # Check disk space
    disk = psutil.disk_usage('.')
    if disk.free < 1024 * 1024 * 1024:  # 1GB
        print("⚠️  Warning: Low disk space ({:.1f}GB free).".format(
            disk.free / 1024 / 1024 / 1024
        ))
    
    print(f"✅ System resources OK: {memory.available // 1024 // 1024 // 1024}GB RAM, {cpu_count} CPUs")
    return True


def start_application():
    """Start the application for testing"""
    print("🚀 Starting Second Brain application...")
    
    # Check if already running
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Application already running on http://localhost:8000")
            return None
    except:
        pass
    
    # Start application
    cmd = [sys.executable, "-m", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent
        )
        
        # Wait for startup
        for i in range(30):  # Wait up to 30 seconds
            try:
                import httpx
                response = httpx.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Application started successfully")
                    return process
            except:
                time.sleep(1)
        
        print("❌ Application failed to start within 30 seconds")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return None


async def run_benchmark_tests():
    """Run performance benchmark tests"""
    print("\n📊 Running Performance Benchmarks...")
    print("-" * 50)
    
    try:
        # Import and run benchmark
        sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "performance"))
        from test_performance_benchmark import PerformanceBenchmark
        
        benchmark = PerformanceBenchmark()
        report = await benchmark.run_benchmark_suite()
        
        # Save benchmark report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        benchmark_file = f"benchmark_report_{timestamp}.json"
        benchmark.save_report(report, benchmark_file)
        
        return report, benchmark_file
        
    except Exception as e:
        print(f"❌ Benchmark tests failed: {e}")
        return None, None


async def run_load_tests(test_type: str = "basic"):
    """Run enterprise load tests"""
    print(f"\n🚀 Running Load Tests ({test_type})...")
    print("-" * 50)
    
    try:
        # Import and run load tests
        sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "performance"))
        from test_enterprise_load import EnterpriseLoadTester, LoadTestConfig
        
        # Configure based on test type
        if test_type == "basic":
            config = LoadTestConfig(
                concurrent_users=5,
                test_duration=30,
                ramp_up_time=5
            )
        elif test_type == "moderate":
            config = LoadTestConfig(
                concurrent_users=15,
                test_duration=60,
                ramp_up_time=10
            )
        elif test_type == "intensive":
            config = LoadTestConfig(
                concurrent_users=25,
                test_duration=120,
                ramp_up_time=15
            )
        else:
            config = LoadTestConfig()
        
        tester = EnterpriseLoadTester(config)
        report = await tester.run_load_test_suite()
        
        # Save load test report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        load_test_file = f"load_test_report_{timestamp}.json"
        tester.save_report(report, load_test_file)
        
        return report, load_test_file
        
    except Exception as e:
        print(f"❌ Load tests failed: {e}")
        return None, None


def generate_combined_report(benchmark_report: Dict, load_test_report: Dict,
                           benchmark_file: str, load_test_file: str):
    """Generate combined performance report"""
    print("\n📋 Generating Combined Performance Report...")
    
    combined_report = {
        "test_suite": "Second Brain v3.0.0 - Complete Performance Analysis",
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "disk_free_gb": psutil.disk_usage('.').free / 1024 / 1024 / 1024
        },
        "benchmark_summary": {},
        "load_test_summary": {},
        "overall_assessment": {},
        "files": {
            "benchmark_report": benchmark_file,
            "load_test_report": load_test_file
        }
    }
    
    # Extract benchmark summary
    if benchmark_report:
        combined_report["benchmark_summary"] = {
            "status": benchmark_report["summary"]["overall_performance"],
            "tests_passed": benchmark_report["summary"]["passed_tests"],
            "total_tests": benchmark_report["summary"]["total_tests"],
            "success_rate": benchmark_report["summary"]["success_rate"]
        }
    
    # Extract load test summary
    if load_test_report:
        combined_report["load_test_summary"] = {
            "status": load_test_report["summary"]["overall_status"],
            "grade": load_test_report["summary"]["overall_grade"],
            "total_requests": load_test_report["summary"]["total_requests"],
            "error_rate": load_test_report["summary"]["overall_error_rate"],
            "tests_passed": load_test_report["summary"]["passed_tests"],
            "total_tests": load_test_report["summary"]["total_tests"]
        }
    
    # Overall assessment
    benchmark_passed = benchmark_report and benchmark_report["summary"]["overall_performance"] == "PASS"
    load_test_passed = load_test_report and load_test_report["summary"]["overall_status"] == "PASS"
    
    if benchmark_passed and load_test_passed:
        overall_status = "EXCELLENT"
        readiness = "Production Ready"
    elif benchmark_passed or load_test_passed:
        overall_status = "GOOD"
        readiness = "Staging Ready"
    else:
        overall_status = "NEEDS_IMPROVEMENT"
        readiness = "Development Only"
    
    combined_report["overall_assessment"] = {
        "status": overall_status,
        "readiness": readiness,
        "benchmark_passed": benchmark_passed,
        "load_test_passed": load_test_passed,
        "enterprise_ready": benchmark_passed and load_test_passed
    }
    
    # Save combined report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_file = f"performance_analysis_{timestamp}.json"
    
    with open(combined_file, "w") as f:
        json.dump(combined_report, f, indent=2, default=str)
    
    return combined_report, combined_file


def print_final_summary(combined_report: Dict, combined_file: str):
    """Print final performance summary"""
    print("\n" + "=" * 80)
    print("🎯 SECOND BRAIN v3.0.0 - PERFORMANCE ANALYSIS COMPLETE")
    print("=" * 80)
    
    assessment = combined_report["overall_assessment"]
    print(f"Overall Status: {assessment['status']}")
    print(f"Readiness Level: {assessment['readiness']}")
    print(f"Enterprise Ready: {'✅ YES' if assessment['enterprise_ready'] else '❌ NO'}")
    
    print("\n📊 Test Results Summary:")
    if "benchmark_summary" in combined_report and combined_report["benchmark_summary"]:
        bench = combined_report["benchmark_summary"]
        print(f"   Benchmarks: {bench['status']} ({bench['tests_passed']}/{bench['total_tests']} passed)")
    
    if "load_test_summary" in combined_report and combined_report["load_test_summary"]:
        load = combined_report["load_test_summary"]
        print(f"   Load Tests: {load['status']} (Grade: {load['grade']}, "
              f"{load['tests_passed']}/{load['total_tests']} passed)")
        print(f"   Total Requests: {load['total_requests']:,}, "
              f"Error Rate: {load['error_rate']:.2%}")
    
    print(f"\n📄 Full report saved to: {combined_file}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if assessment['enterprise_ready']:
        print("   ✅ System is ready for enterprise deployment!")
        print("   ✅ Consider setting up production monitoring and alerting")
    elif assessment['status'] == 'GOOD':
        print("   ⚠️  System shows good performance but has some issues")
        print("   ⚠️  Review individual test reports for improvement areas")
    else:
        print("   ❌ System needs performance improvements before deployment")
        print("   ❌ Address failing tests before proceeding to production")
    
    print()


def main():
    """Main performance testing orchestrator"""
    parser = argparse.ArgumentParser(description="Second Brain v3.0.0 Performance Testing")
    parser.add_argument("--type", choices=["benchmark", "load", "both"], default="both",
                       help="Type of performance testing to run")
    parser.add_argument("--load-intensity", choices=["basic", "moderate", "intensive"], 
                       default="moderate", help="Load testing intensity")
    parser.add_argument("--skip-startup", action="store_true", 
                       help="Skip application startup (assume already running)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests only")
    
    args = parser.parse_args()
    
    print("🚀 Second Brain v3.0.0 - Performance Testing Suite")
    print("=" * 60)
    print(f"Test Type: {args.type}")
    print(f"Load Intensity: {args.load_intensity}")
    print("=" * 60)
    
    # Setup
    setup_performance_environment()
    
    if not check_system_resources():
        print("⚠️  Proceeding with limited resources...")
    
    # Start application if needed
    app_process = None
    if not args.skip_startup:
        app_process = start_application()
        if not app_process:
            print("❌ Cannot proceed without running application")
            sys.exit(1)
    
    try:
        # Run tests
        benchmark_report = None
        load_test_report = None
        benchmark_file = None
        load_test_file = None
        
        if args.type in ["benchmark", "both"]:
            benchmark_report, benchmark_file = asyncio.run(run_benchmark_tests())
        
        if args.type in ["load", "both"]:
            intensity = "basic" if args.quick else args.load_intensity
            load_test_report, load_test_file = asyncio.run(run_load_tests(intensity))
        
        # Generate combined report
        if benchmark_report or load_test_report:
            combined_report, combined_file = generate_combined_report(
                benchmark_report or {}, load_test_report or {},
                benchmark_file or "", load_test_file or ""
            )
            
            print_final_summary(combined_report, combined_file)
            
            # Exit with appropriate code for CI/CD
            if combined_report["overall_assessment"]["enterprise_ready"]:
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print("❌ No tests completed successfully")
            sys.exit(1)
            
    finally:
        # Cleanup
        if app_process:
            print("🛑 Stopping application...")
            app_process.terminate()
            app_process.wait()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Performance testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Performance testing failed: {e}")
        sys.exit(1)
