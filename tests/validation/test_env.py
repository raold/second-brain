#!/usr/bin/env python
"""Simple test to verify environment setup."""
import subprocess
import sys


def test_python_environment():
    """Test that we're using the correct Python environment."""
    python_path = sys.executable
    print(f"Python executable: {python_path}")

    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print(f"In virtual environment: {in_venv}")

    # Test that pytest can be imported
    try:
        import pytest

pytestmark = pytest.mark.validation

        print(f"pytest version: {pytest.__version__}")
    except ImportError as e:
        print(f"Failed to import pytest: {e}")
        return False

    # Run a simple pytest command
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        capture_output=True,
        text=True
    )
    print(f"pytest command output: {result.stdout}")

    return result.returncode == 0

if __name__ == "__main__":
    success = test_python_environment()
    sys.exit(0 if success else 1)
