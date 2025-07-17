#!/usr/bin/env python3
"""
Quick test runner for Second Brain - focuses on key tests first.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        return True
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr:
            print("STDERR:", result.stderr[:1000])  # Limit output
        if result.stdout:
            print("STDOUT:", result.stdout[:1000])  # Limit output
        return False

def main():
    """Run focused test suite."""
    os.chdir(Path(__file__).parent.parent)
    
    print("🧪 Second Brain - Quick Test Runner")
    
    # Run specific test files one by one
    test_files = [
        ("tests/test_minimal.py", "Basic functionality tests"),
        ("tests/test_health.py", "Health check tests"),
        ("tests/test_ingest.py", "Ingestion tests"),
        ("tests/test_search.py", "Search tests"),
    ]
    
    passed_count = 0
    total_count = len(test_files)
    
    for test_file, description in test_files:
        if Path(test_file).exists():
            command = f"python -m pytest {test_file} -v -x"  # -x stops on first failure
            if run_command(command, description):
                passed_count += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"🏁 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("🎉 All tests PASSED!")
        return 0
    else:
        print(f"❌ {total_count - passed_count} test(s) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
