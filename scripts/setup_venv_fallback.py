#!/usr/bin/env python3
"""
Setup .venv as a working fallback for Docker-first development
Installs core dependencies for local development when Docker is unavailable
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Setup virtual environment with core dependencies"""

    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Check if .venv exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print("❌ Virtual environment not found. Please create it first:")
        print("   python3 -m venv .venv")
        sys.exit(1)

    # Determine Python executable
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

    if not python_exe.exists():
        print(f"❌ Python executable not found at {python_exe}")
        sys.exit(1)

    print("🔧 Setting up .venv as Docker fallback...")
    print(f"📍 Using Python: {python_exe}")

    # Upgrade pip first
    print("\n📦 Upgrading pip...")
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # Install build dependencies
    print("\n🔨 Installing build dependencies...")
    subprocess.run([str(pip_exe), "install", "setuptools", "wheel", "cython"], check=True)

    # Core dependencies for basic functionality
    core_deps = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0.post1",
        "pydantic==2.5.2",
        "pydantic-settings==2.1.0",
        "python-dotenv==1.0.0",
        "httpx==0.25.2",
        "python-multipart==0.0.6",
        "aiofiles==23.2.1",
        "pyyaml==6.0.2",
    ]

    # Database dependencies
    db_deps = [
        "sqlalchemy==2.0.23",
        "alembic==1.12.1",
        "asyncpg==0.29.0",
        "redis==5.0.1",
    ]

    # AI/ML dependencies (lighter subset)
    ai_deps = [
        "openai==1.3.8",
        "numpy==1.26.4",  # Updated to Python 3.13 compatible version
        "pandas==2.2.3",   # Updated to Python 3.13 compatible version
        "scikit-learn==1.5.2",  # Updated version
    ]

    # Security dependencies
    security_deps = [
        "python-jose[cryptography]==3.5.0",
        "passlib[bcrypt]==1.7.4",
        "argon2-cffi==23.1.0",
        "cryptography>=42.0.8",
    ]

    # Development tools
    dev_deps = [
        "pytest==7.4.3",
        "pytest-asyncio==0.21.1",
        "ruff==0.12.4",
        "python-json-logger==2.0.7",
        "structlog==24.1.0",
        "psutil==5.9.0",
    ]

    # Install in phases
    phases = [
        ("Core", core_deps),
        ("Database", db_deps),
        ("AI/ML", ai_deps),
        ("Security", security_deps),
        ("Development", dev_deps),
    ]

    failed_packages = []

    for phase_name, deps in phases:
        print(f"\n📦 Installing {phase_name} dependencies...")
        for dep in deps:
            try:
                print(f"   Installing {dep}...")
                subprocess.run(
                    [str(pip_exe), "install", dep],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError:
                print(f"   ⚠️  Failed to install {dep}")
                failed_packages.append((dep, phase_name))

    # Summary
    print("\n" + "="*60)
    print("📊 Installation Summary")
    print("="*60)

    # Check installed packages
    result = subprocess.run(
        [str(pip_exe), "list"],
        capture_output=True,
        text=True
    )

    installed_count = len(result.stdout.strip().split('\n')) - 2  # Subtract header lines
    print(f"✅ Installed packages: {installed_count}")

    if failed_packages:
        print(f"\n⚠️  Failed packages ({len(failed_packages)}):")
        for pkg, phase in failed_packages:
            print(f"   - {pkg} ({phase})")
        print("\nThese packages may require additional system dependencies or")
        print("may not be compatible with Python 3.13. The core functionality")
        print("should still work for basic development.")

    # Test imports
    print("\n🧪 Testing core imports...")
    test_imports = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "redis",
        "httpx",
    ]

    import_failures = []
    for module in test_imports:
        try:
            subprocess.run(
                [str(python_exe), "-c", f"import {module}"],
                check=True,
                capture_output=True
            )
            print(f"   ✅ {module}")
        except subprocess.CalledProcessError:
            print(f"   ❌ {module}")
            import_failures.append(module)

    # Final status
    print("\n" + "="*60)
    if not import_failures and not failed_packages:
        print("✅ Virtual environment setup complete!")
        print("\nYou can now run the app locally with:")
        print(f"   {python_exe} main.py")
    else:
        print("⚠️  Virtual environment partially configured")
        print("\nCore functionality is available, but some features may be limited.")
        print("For full functionality, use Docker: make dev")

    print("\n💡 Tip: Always prefer Docker for development:")
    print("   make dev  # Start full environment")
    print("="*60)

if __name__ == "__main__":
    main()
