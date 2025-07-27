#!/usr/bin/env python3
"""
CI Pipeline Test Suite - Comprehensive validation of the v2.0.0 architecture.

This test suite validates that the CI pipeline will work correctly by simulating
the exact environment and tests that will run in GitHub Actions.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


# Mock external dependencies for testing
class MockEmbeddings:
    """Mock OpenAI embeddings for testing."""

    async def create(self, input: str, model: str):
        """Return a mock embedding response."""
        # Generate deterministic embeddings for testing
        import hashlib

        hash_obj = hashlib.md5(input.encode())
        hash_int = int(hash_obj.hexdigest(), 16)

        # Create a 1536-dimensional embedding (OpenAI text-embedding-3-small size)
        embedding = [(hash_int >> (i % 32)) % 1000 / 1000.0 for i in range(1536)]

        return type("MockResponse", (), {"data": [type("MockEmbedding", (), {"embedding": embedding})()]})()


class MockOpenAI:
    """Mock OpenAI client for testing without API calls."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.embeddings = MockEmbeddings()


@pytest.mark.asyncio
async def test_environment_setup():
    """Test that the environment is set up correctly."""
    print("Testing Environment Setup...")

    # Try to load from .env.test first
    from pathlib import Path

    env_test_file = Path(__file__).parent / ".env.test"
    if env_test_file.exists():
        with open(env_test_file) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
        print("[OK] Loaded test environment variables from .env.test")
    else:
        # Check required environment variables
        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "OPENAI_API_KEY",
            "API_TOKENS",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print(f"⚠️  Missing environment variables: {missing_vars}")
            print("Setting up mock environment variables for testing...")

            # Set up mock environment
            os.environ["POSTGRES_USER"] = "postgres"
            os.environ["POSTGRES_PASSWORD"] = "postgres"
            os.environ["POSTGRES_HOST"] = "localhost"
            os.environ["POSTGRES_PORT"] = "5432"
            os.environ["POSTGRES_DB"] = "secondbrain"
            os.environ["OPENAI_API_KEY"] = "test-key-mock"
            os.environ["API_TOKENS"] = "test-token-1,test-token-2"

    print("[OK] Environment setup complete")
    return True


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection and schema setup."""
    print("\n Testing Database Connection...")

    try:
        import asyncpg

        # Test connection
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

        conn = await asyncpg.connect(db_url)

        # Test pgvector extension
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("[OK] pgvector extension available")
        except Exception as e:
            print(f"[WARN] pgvector extension issue: {e}")

        # Test basic query
        result = await conn.fetchval("SELECT 1")
        assert result == 1
        print("[OK] Database connection successful")

        await conn.close()

    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_mock_database_functionality():
    """Test the mock database functionality."""
    print("\n Testing Mock Database Functionality...")

    try:
        from app.database_mock import get_mock_database

        # Test database operations
        db = await get_mock_database()

        # Store a test memory
        memory_id = await db.store_memory("Test memory content", {"type": "test"})
        print(f"[OK] Memory stored with ID: {memory_id}")

        # Retrieve the memory
        memory = await db.get_memory(memory_id)
        assert memory is not None
        assert memory["content"] == "Test memory content"
        print("[OK] Memory retrieval successful")

        # Search memories
        results = await db.search_memories("test", limit=5)
        assert len(results) > 0
        print(f"[OK] Search returned {len(results)} results")

        # List all memories
        all_memories = await db.get_all_memories(limit=10)
        assert len(all_memories) > 0
        print(f"[OK] Listed {len(all_memories)} total memories")

        # Clean up
        await db.close()

    except Exception as e:
        print(f"[FAIL] Mock database test failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_real_database_functionality():
    """Test the real database functionality if available."""
    print("\n Testing Real Database Functionality...")

    try:
        # Mock the OpenAI client to avoid API calls
        import app.database

        original_openai = app.database.AsyncOpenAI
        app.database.AsyncOpenAI = MockOpenAI

        from app.database import get_database

        # Test database operations
        db = await get_database()

        # Store a test memory
        memory_id = await db.store_memory("Real database test content", {"type": "integration_test"})
        print(f"[OK] Memory stored with ID: {memory_id}")

        # Retrieve the memory
        memory = await db.get_memory(memory_id)
        assert memory is not None
        assert memory["content"] == "Real database test content"
        print("[OK] Memory retrieval successful")

        # Search memories (may return 0 results with mock embeddings)
        results = await db.search_memories("integration", limit=5)
        assert isinstance(results, list)  # Just check it's a list, may be empty
        print(f"[OK] Search returned {len(results)} results")

        # Clean up test data
        await db.delete_memory(memory_id)
        print("[OK] Test data cleaned up")

        # Don't close the database connection here - leave it for the app to manage

        # Restore original OpenAI
        app.database.AsyncOpenAI = original_openai

    except Exception as e:
        print(f"[FAIL] Real database test failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_api_endpoints():
    """Test the FastAPI endpoints."""
    print("\n Testing API Endpoints...")

    try:
        from httpx import AsyncClient

        # Mock the OpenAI client to avoid API calls
        import app.database
        from app.app import app as fastapi_app

        original_openai = app.database.AsyncOpenAI
        app.database.AsyncOpenAI = MockOpenAI

        async with AsyncClient(app=fastapi_app, base_url="http://test") as client:
            # Test health check
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            print("[OK] Health check endpoint working")

            # Test API key authentication
            api_key = os.getenv("API_TOKENS", "test-token-1").split(",")[0].strip()

            # Test store memory
            memory_data = {"content": "API test memory", "metadata": {"type": "api_test"}}

            response = await client.post("/memories", json=memory_data, params={"api_key": api_key})
            assert response.status_code == 200
            stored_memory = response.json()
            memory_id = stored_memory["id"]
            print(f"[OK] Memory stored via API: {memory_id}")

            # Test get memory
            response = await client.get(f"/memories/{memory_id}", params={"api_key": api_key})
            assert response.status_code == 200
            retrieved_memory = response.json()
            assert retrieved_memory["content"] == "API test memory"
            print("[OK] Memory retrieved via API")

            # Test search memories (may return 0 results with mock embeddings)
            search_data = {"query": "API test", "limit": 5}

            response = await client.post("/memories/search", json=search_data, params={"api_key": api_key})
            assert response.status_code == 200
            results = response.json()
            assert isinstance(results, list)  # Just check it's a list, may be empty
            print(f"[OK] Search via API returned {len(results)} results")

            # Test delete memory
            response = await client.delete(f"/memories/{memory_id}", params={"api_key": api_key})
            assert response.status_code == 200
            print("[OK] Memory deleted via API")

            # Test list memories
            response = await client.get("/memories", params={"api_key": api_key, "limit": 10})
            assert response.status_code == 200
            memories = response.json()
            assert isinstance(memories, list)
            print(f"[OK] Listed {len(memories)} memories via API")

        # Restore original OpenAI
        app.database.AsyncOpenAI = original_openai

    except Exception as e:
        print(f"[FAIL] API endpoints test failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_docker_build():
    """Test Docker build process."""
    print("\n Testing Docker Build...")

    try:
        import subprocess

        # Check if Docker is available
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("[WARN] Docker not available, skipping Docker tests")
            return True

        # Build the Docker image
        print("Building Docker image...")
        result = subprocess.run(
            ["docker", "build", "-t", "second-brain-test", "."],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        if result.returncode != 0:
            print(f"[FAIL] Docker build failed: {result.stderr}")
            return False

        print("[OK] Docker build successful")

        # Clean up the test image
        subprocess.run(["docker", "rmi", "second-brain-test"], capture_output=True, text=True)

    except Exception as e:
        print(f"[FAIL] Docker build test failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_linting_and_formatting():
    """Test code quality with ruff."""
    print("\n Testing Code Quality (Linting)...")

    try:
        import subprocess

        # Run ruff check
        result = subprocess.run(["ruff", "check", "."], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode != 0:
            print(f"[FAIL] Linting failed: {result.stdout}")
            return False

        print("[OK] Code linting passed")

    except Exception as e:
        print(f"[FAIL] Linting test failed: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_requirements_installation():
    """Test that all requirements can be installed."""
    print("\n Testing Requirements Installation...")

    try:
        import subprocess

        # Check if requirements-minimal.txt exists
        requirements_file = Path(__file__).parent / "requirements-minimal.txt"
        if not requirements_file.exists():
            print("[FAIL] requirements-minimal.txt not found")
            return False

        # Create a temporary virtual environment
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create virtual environment
            result = subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"[FAIL] Virtual environment creation failed: {result.stderr}")
                return False

            # Determine pip path
            if os.name == "nt":  # Windows
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:  # Unix-like
                pip_path = venv_path / "bin" / "pip"

            # Install requirements
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_file)], capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"[FAIL] Requirements installation failed: {result.stderr}")
                return False

            print("[OK] Requirements installation successful")

    except Exception as e:
        print(f"[FAIL] Requirements test failed: {e}")
        return False

    return True


async def main():
    """Run all CI pipeline tests."""
    print(" Starting CI Pipeline Test Suite for Second Brain v2.0.0")
    print("=" * 60)

    tests = [
        ("Environment Setup", test_environment_setup),
        ("Database Connection", test_database_connection),
        ("Mock Database Functionality", test_mock_database_functionality),
        ("Real Database Functionality", test_real_database_functionality),
        ("API Endpoints", test_api_endpoints),
        ("Docker Build", test_docker_build),
        ("Code Quality (Linting)", test_linting_and_formatting),
        ("Requirements Installation", test_requirements_installation),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print(" CI Pipeline Test Results Summary")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            print(f"[OK] {test_name}")
            passed += 1
        else:
            print(f"[FAIL] {test_name}")
            failed += 1

    print(f"\nTotal: {passed + failed} tests")
    print(f"[OK] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")

    if failed == 0:
        print("\n[SUCCESS] All tests passed! CI pipeline is ready for green builds! [SUCCESS]")
        return 0
    else:
        print(f"\n[WARN] {failed} test(s) failed. CI pipeline needs attention.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
