#!/usr/bin/env python3
"""
Test CI steps locally to ensure they'll pass
"""

import sys
import subprocess
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, description):
    """Run a command and report status"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False


async def test_imports():
    """Test basic imports"""
    try:
        from app.app import app
        print("✅ App imports successfully")
        return True
    except Exception as e:
        print(f"❌ App import failed: {e}")
        return False


async def test_database():
    """Test database connectivity"""
    try:
        from app.storage.postgres_unified import PostgresUnifiedBackend
        
        backend = PostgresUnifiedBackend('postgresql://secondbrain:changeme@localhost:5432/secondbrain')
        await backend.initialize()
        async with backend.acquire() as conn:
            result = await conn.fetchval('SELECT 1')
            assert result == 1
            print('✅ Database connection successful')
        await backend.close()
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


async def test_memory_service():
    """Test memory service"""
    try:
        from app.services.memory_service import MemoryService
        
        service = MemoryService()
        memory = await service.create_memory(
            content='CI test memory',
            memory_type='test',
            importance_score=0.5
        )
        assert memory['id'] is not None
        print(f'✅ Memory created: {memory["id"]}')
        
        # Clean up
        await service.delete_memory(memory['id'])
        return True
    except Exception as e:
        print(f"❌ Memory service test failed: {e}")
        return False


async def main():
    """Run all CI tests locally"""
    print("🧪 Testing CI Pipeline Locally")
    print("=" * 50)
    
    results = []
    
    # Test Python syntax
    results.append(run_command(
        "python -m py_compile app/*.py app/**/*.py 2>/dev/null",
        "Python syntax check"
    ))
    
    # Test imports
    results.append(await test_imports())
    
    # Test database (if available)
    db_available = run_command(
        "pg_isready -h localhost -p 5432 -U secondbrain",
        "Check PostgreSQL availability"
    )
    
    if db_available:
        results.append(await test_database())
        results.append(await test_memory_service())
    else:
        print("⚠️  PostgreSQL not available - skipping database tests")
    
    # Test Docker build
    results.append(run_command(
        "docker build -t second-brain:ci-test . --quiet",
        "Docker build"
    ))
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))