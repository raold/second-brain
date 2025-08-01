#!/usr/bin/env python3
"""
Validate that CI is ready to pass by checking all critical dependencies.
"""


def test_imports():
    """Test all critical imports."""
    print("Testing critical imports...")

    try:
        import fastapi

        print("[OK] FastAPI")
        del fastapi  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] FastAPI: {e}")
        return False

    try:
        import pydantic

        print(f"[OK] Pydantic {pydantic.__version__}")
    except ImportError as e:
        print(f"[FAIL] Pydantic: {e}")
        return False

    try:
        import uvicorn

        print("[OK] Uvicorn")
        del uvicorn  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] Uvicorn: {e}")
        return False

    try:
        import sqlalchemy

        print("[OK] SQLAlchemy")
        del sqlalchemy  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] SQLAlchemy: {e}")
        return False

    try:
        import asyncpg

        print("[OK] AsyncPG")
        del asyncpg  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] AsyncPG: {e}")
        return False

    try:
        import httpx

        print("[OK] HTTPX")
        del httpx  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] HTTPX: {e}")
        return False

    try:
        import redis

        print("[OK] Redis")
        del redis  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] Redis: {e}")
        return False

    try:
        import openai

        print("[OK] OpenAI")
        del openai  # Satisfy linter
    except ImportError as e:
        print(f"[FAIL] OpenAI: {e}")
        return False

    return True


def test_versions():
    """Test critical version compatibility."""
    print("\nTesting version compatibility...")

    import fastapi
    import pydantic

    # Check Pydantic version
    if pydantic.__version__.startswith("2.5.3"):
        print(f"[OK] Pydantic version: {pydantic.__version__}")
    else:
        print(f"[WARN] Pydantic version: {pydantic.__version__} (expected 2.5.3)")

    # Check FastAPI version
    if fastapi.__version__.startswith("0.109"):
        print(f"[OK] FastAPI version: {fastapi.__version__}")
    else:
        print(f"[WARN] FastAPI version: {fastapi.__version__} (expected 0.109.x)")

    return True


def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")

    try:
        from fastapi import FastAPI

        FastAPI()
        print("[OK] FastAPI app creation")
    except Exception as e:
        print(f"[FAIL] FastAPI app creation: {e}")
        return False

    try:
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        TestModel(name="test")
        print("[OK] Pydantic model creation")
    except Exception as e:
        print(f"[FAIL] Pydantic model creation: {e}")
        return False

    return True


def main():
    """Run all validation tests."""
    print("=== CI Readiness Validation ===")

    all_passed = True

    if not test_imports():
        all_passed = False

    if not test_versions():
        all_passed = False

    if not test_basic_functionality():
        all_passed = False

    print("\n=== Summary ===")
    if all_passed:
        print("[SUCCESS] All validations passed!")
        print("CI pipeline should work correctly when pushed to main.")
        return True
    else:
        print("[FAILURE] Some validations failed.")
        print("CI pipeline may fail when pushed to main.")
        return False


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
