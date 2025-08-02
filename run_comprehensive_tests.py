#!/usr/bin/env python3
"""
Run comprehensive tests and report real functionality status
"""
import subprocess
import sys
import os
from pathlib import Path

# Setup
project_root = Path(__file__).parent
os.chdir(project_root)

print("🔍 SECOND BRAIN V2 - COMPREHENSIVE TESTING")
print("="*60)
print(f"Working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

# Test 1: Run the reality check
print("\n" + "="*60)
print("RUNNING COMPREHENSIVE REALITY CHECK")
print("="*60)

try:
    result = subprocess.run([
        sys.executable, "test_real_functionality.py"
    ], cwd=project_root, timeout=120)
    print(f"Reality check completed with exit code: {result.returncode}")
except subprocess.TimeoutExpired:
    print("❌ Reality check timed out")
except Exception as e:
    print(f"❌ Reality check failed: {e}")

# Test 2: Try running the existing simple CI runner
print("\n" + "="*60)
print("RUNNING EXISTING CI TESTS")
print("="*60)

try:
    result = subprocess.run([
        sys.executable, "scripts/simple_ci_runner.py"
    ], cwd=project_root, timeout=180)
    print(f"CI tests completed with exit code: {result.returncode}")
except subprocess.TimeoutExpired:
    print("❌ CI tests timed out")
except Exception as e:
    print(f"❌ CI tests failed: {e}")

# Test 3: Basic pytest if available
print("\n" + "="*60)
print("RUNNING BASIC PYTEST")
print("="*60)

try:
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/validation/test_simple.py", "-v"
    ], cwd=project_root, timeout=60)
    print(f"Basic pytest completed with exit code: {result.returncode}")
except subprocess.TimeoutExpired:
    print("❌ Basic pytest timed out")
except Exception as e:
    print(f"❌ Basic pytest failed: {e}")

print("\n" + "="*60)
print("COMPREHENSIVE TESTING COMPLETE")
print("="*60)