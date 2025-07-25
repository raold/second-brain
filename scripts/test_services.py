#!/usr/bin/env python
"""Test connectivity to all services."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import asyncpg
import redis
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('.env.development')


async def test_postgres():
    """Test PostgreSQL connection."""
    print("Testing PostgreSQL connection...")
    try:
        # Test with asyncpg
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='secondbrain',
            password='changeme',
            database='secondbrain'
        )
        version = await conn.fetchval('SELECT version()')
        print(f"  [OK] Connected to PostgreSQL")
        print(f"  Version: {version}")
        await conn.close()
        
        # Test with SQLAlchemy
        engine = create_engine(os.getenv('DATABASE_URL'))
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("  [OK] SQLAlchemy connection successful")
        
        return True
    except Exception as e:
        print(f"  [FAIL] PostgreSQL connection failed: {e}")
        return False


def test_redis():
    """Test Redis connection."""
    print("\nTesting Redis connection...")
    try:
        r = redis.from_url(os.getenv('REDIS_URL'))
        r.ping()
        print("  [OK] Connected to Redis")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        assert value == b'test_value'
        r.delete('test_key')
        print("  [OK] Redis operations successful")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Redis connection failed: {e}")
        return False


def test_env_vars():
    """Test that all required environment variables are set."""
    print("\nChecking environment variables...")
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL',
        'JWT_SECRET_KEY',
        'OPENAI_API_KEY'
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var} is set")
        else:
            print(f"  [FAIL] {var} is NOT set")
            all_set = False
            
    return all_set


async def main():
    """Run all tests."""
    print("=== Service Connectivity Test ===\n")
    
    # Test environment variables
    env_ok = test_env_vars()
    
    # Test services
    postgres_ok = await test_postgres()
    redis_ok = test_redis()
    
    print("\n=== Summary ===")
    print(f"Environment variables: {'[OK]' if env_ok else '[FAIL]'}")
    print(f"PostgreSQL: {'[OK]' if postgres_ok else '[FAIL]'}")
    print(f"Redis: {'[OK]' if redis_ok else '[FAIL]'}")
    
    if all([env_ok, postgres_ok, redis_ok]):
        print("\nAll services are ready!")
        return 0
    else:
        print("\nSome services are not ready. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)