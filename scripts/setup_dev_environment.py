#!/usr/bin/env python3
"""
Development Environment Setup Script

This script creates a portable development environment that works on any machine.
Run this on each computer you work on (work, laptop, desktop).
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, description=""):
    """Run command and handle errors."""
    print(f"-> {description or cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {result.stderr}")
        return False
    print(f"[OK] Success")
    return True

def detect_python():
    """Detect the best Python executable to use."""
    python_candidates = [
        "python3.11", "python3.10", "python3.9", "python3", "python"
    ]
    
    for python_cmd in python_candidates:
        try:
            result = subprocess.run([python_cmd, "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"[OK] Found Python: {python_cmd} ({version})")
                return python_cmd
        except FileNotFoundError:
            continue
    
    print("[FAIL] No suitable Python found")
    return None

def setup_virtual_environment():
    """Create or use existing virtual environment."""
    print("\n=== Setting up Virtual Environment ===")
    
    venv_path = Path(".venv")
    
    # Detect platform-specific paths
    if platform.system() == "Windows":
        pip_cmd = ".venv\\Scripts\\python.exe -m pip"
        python_venv = ".venv\\Scripts\\python.exe"
    else:
        pip_cmd = ".venv/bin/python -m pip"
        python_venv = ".venv/bin/python"
    
    # Check if .venv already exists and works
    if venv_path.exists():
        try:
            result = subprocess.run([python_venv, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] Using existing virtual environment: {result.stdout.strip()}")
                # Upgrade pip
                if not run_command(f"{pip_cmd} install --upgrade pip", 
                                  "Upgrading pip"):
                    return False
                return python_venv, pip_cmd
        except FileNotFoundError:
            pass
    
    # Create new virtual environment if needed
    python_cmd = detect_python()
    if not python_cmd:
        return False
    
    if not venv_path.exists():
        if not run_command(f"{python_cmd} -m venv .venv", 
                          "Creating virtual environment"):
            return False
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", 
                      "Upgrading pip"):
        return False
    
    return python_venv, pip_cmd

def install_dependencies(pip_cmd):
    """Install dependencies in correct order to avoid conflicts."""
    print("\n=== Installing Dependencies ===")
    
    # Core dependencies (install in specific order to avoid conflicts)
    core_deps = [
        "fastapi==0.109.0",
        "pydantic==2.5.3", 
        "uvicorn[standard]==0.27.0",
        "sqlalchemy==2.0.25",
        "asyncpg==0.29.0",
        "psycopg2-binary==2.9.10",
    ]
    
    networking_deps = [
        "httpx==0.26.0",
        "python-multipart==0.0.6",
    ]
    
    cache_deps = [
        "redis==5.0.1",
        "python-dotenv==1.0.0",
    ]
    
    ai_deps = [
        "openai==1.3.8",
        "numpy==1.26.3",
        "scikit-learn==1.3.2",
        "pandas==2.0.3",
        "networkx==3.2.1",
    ]
    
    file_deps = [
        "aiofiles==23.2.1",
        "python-magic==0.4.27",
        "PyPDF2==3.0.1",
        "python-docx==0.8.11",
    ]
    
    system_deps = [
        "psutil==5.9.0",
        "structlog==25.4.0",
        "jinja2==3.1.2",
    ]
    
    observability_deps = [
        "opentelemetry-api==1.35.0",
        "opentelemetry-sdk==1.35.0",
    ]
    
    test_deps = [
        "pytest==7.4.4",
        "pytest-asyncio==0.23.3", 
        "pytest-cov==4.1.0",
        "pytest-mock==3.14.1",
    ]
    
    dev_deps = [
        "ruff==0.12.4",
        "black==23.12.1",
        "isort==6.0.1",
        "mypy==1.17.0",
    ]
    
    # Install dependency groups
    dep_groups = [
        ("Core dependencies", core_deps),
        ("Networking dependencies", networking_deps),
        ("Cache dependencies", cache_deps),
        ("AI dependencies", ai_deps),
        ("File handling dependencies", file_deps),
        ("System dependencies", system_deps),
        ("Observability dependencies", observability_deps),
        ("Testing dependencies", test_deps),
        ("Development dependencies", dev_deps),
    ]
    
    for group_name, deps in dep_groups:
        print(f"\n[INSTALL] {group_name}...")
        deps_str = " ".join(deps)
        if not run_command(f"{pip_cmd} install {deps_str}", 
                          f"Installing {group_name.lower()}"):
            print(f"[WARN] Failed to install {group_name}")
            # Continue with other groups
    
    return True

def validate_installation(python_venv):
    """Validate the installation works."""
    print("\n=== Validating Installation ===")
    
    validation_script = '''
import sys
try:
    import fastapi, pydantic, uvicorn, sqlalchemy, asyncpg
    import httpx, redis, openai, psutil, structlog, numpy
    import sklearn, pandas, networkx, jinja2
    import pytest
    print("[OK] All critical imports successful")
    print(f"Python: {sys.version}")
    print(f"FastAPI: {fastapi.__version__}")
    print(f"Pydantic: {pydantic.__version__}")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)
'''
    
    return run_command(f'{python_venv} -c "{validation_script}"',
                      "Validating all imports")

def create_activation_instructions():
    """Create platform-specific activation instructions."""
    print("\n=== Environment Ready ===")
    
    if platform.system() == "Windows":
        activate_cmd = ".venv\\Scripts\\activate"
        python_cmd = ".venv\\Scripts\\python.exe"
    else:
        activate_cmd = "source .venv/bin/activate"
        python_cmd = ".venv/bin/python"
    
    print(f"""
=== Development environment setup complete! ===

To activate your environment:
  {activate_cmd}

To run tests:
  {python_cmd} scripts/test_runner.py --all

To run specific test types:
  {python_cmd} scripts/test_runner.py --unit        # Fast unit tests
  {python_cmd} scripts/test_runner.py --validation  # Environment validation

To run the application:
  {python_cmd} -m uvicorn main:app --reload

To run Docker services:
  docker-compose up -d
""")

def main():
    """Main setup function."""
    print("=== Second Brain Development Environment Setup ===")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Working directory: {os.getcwd()}")
    
    # Setup virtual environment
    result = setup_virtual_environment()
    if not result:
        print("[FAIL] Failed to setup virtual environment")
        return False
    
    python_venv, pip_cmd = result
    
    # Install dependencies
    if not install_dependencies(pip_cmd):
        print("[FAIL] Failed to install dependencies")
        return False
    
    # Validate installation
    if not validate_installation(python_venv):
        print("[FAIL] Installation validation failed")
        return False
    
    # Show activation instructions
    create_activation_instructions()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)