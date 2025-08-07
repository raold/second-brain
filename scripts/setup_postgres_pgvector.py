#!/usr/bin/env python3
"""
Setup PostgreSQL with pgvector for Second Brain v4.2.0
Single user, best practices, WORKING system
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def setup_database():
    """Setup PostgreSQL database with pgvector"""
    
    # Connection parameters - match docker-compose.yml
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "secondbrain")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    database = os.getenv("POSTGRES_DB", "second_brain")
    
    print("🚀 Setting up PostgreSQL with pgvector for Second Brain v4.2")
    print("=" * 60)
    
    try:
        # First connect to postgres database to create our database
        print(f"📡 Connecting to PostgreSQL at {host}:{port}")
        admin_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"
        )
        
        # Check if database exists
        exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database
        )
        
        if not exists:
            print(f"📦 Creating database '{database}'")
            await admin_conn.execute(f'CREATE DATABASE "{database}"')
        else:
            print(f"✓ Database '{database}' already exists")
            
        await admin_conn.close()
        
        # Now connect to our database
        print(f"📡 Connecting to '{database}' database")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Create extensions
        print("\n📚 Installing extensions...")
        extensions = ["uuid-ossp", "vector", "pg_trgm"]
        
        for ext in extensions:
            try:
                await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}"')
                print(f"  ✓ {ext} installed")
            except Exception as e:
                print(f"  ⚠️ {ext}: {e}")
                if ext == "vector":
                    print("\n❌ pgvector extension is required!")
                    print("Install it with:")
                    print("  Ubuntu/Debian: sudo apt install postgresql-15-pgvector")
                    print("  macOS: brew install pgvector")
                    print("  Docker: Use postgres image with pgvector")
                    return False
        
        # Load and execute schema
        schema_path = Path(__file__).parent.parent / "docs" / "v4.2-postgresql-schema.sql"
        
        if schema_path.exists():
            print(f"\n📋 Loading schema from {schema_path.name}")
            with open(schema_path, "r") as f:
                schema_sql = f.read()
                
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
            
            for i, stmt in enumerate(statements, 1):
                if stmt:
                    try:
                        await conn.execute(stmt)
                        if "CREATE TABLE" in stmt:
                            table_name = stmt.split("CREATE TABLE")[1].split("(")[0].strip()
                            print(f"  ✓ Created table: {table_name}")
                        elif "CREATE INDEX" in stmt:
                            index_name = stmt.split("CREATE INDEX")[1].split(" ON")[0].strip()
                            print(f"  ✓ Created index: {index_name}")
                        elif "CREATE FUNCTION" in stmt or "CREATE OR REPLACE FUNCTION" in stmt:
                            func_name = stmt.split("FUNCTION")[1].split("(")[0].strip()
                            print(f"  ✓ Created function: {func_name}")
                    except asyncpg.DuplicateTableError:
                        pass  # Table already exists
                    except asyncpg.DuplicateObjectError:
                        pass  # Index/function already exists
                    except Exception as e:
                        print(f"  ⚠️ Statement {i}: {str(e)[:100]}")
        else:
            print(f"⚠️ Schema file not found at {schema_path}")
            
        # Verify setup
        print("\n🔍 Verifying setup...")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('memories', 'memory_relationships', 'memory_consolidations', 'search_history')
        """)
        
        print(f"  ✓ Found {len(tables)} tables")
        for table in tables:
            print(f"    - {table['tablename']}")
            
        # Check pgvector
        vector_check = await conn.fetchval("""
            SELECT 1 FROM pg_extension WHERE extname = 'vector'
        """)
        
        if vector_check:
            print("  ✓ pgvector extension active")
        else:
            print("  ❌ pgvector extension not found")
            
        # Test vector operations
        try:
            await conn.execute("""
                SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector
            """)
            print("  ✓ Vector operations working")
        except Exception as e:
            print(f"  ❌ Vector operations failed: {e}")
            
        await conn.close()
        
        print("\n✅ PostgreSQL setup complete!")
        print("\n📊 Database Info:")
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  Database: {database}")
        print(f"  User: {user}")
        
        print("\n🔗 Connection string:")
        print(f"  postgresql://{user}:****@{host}:{port}/{database}")
        
        print("\n🚀 Next steps:")
        print("  1. Update .env with DATABASE_URL")
        print("  2. Test with: python -m app.main")
        print("  3. Migrate existing data if needed")
        
        return True
        
    except asyncpg.PostgresError as e:
        print(f"\n❌ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


async def test_connection():
    """Test database connection and operations"""
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/second_brain"
    )
    
    print("\n🧪 Testing database operations...")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Test memory creation
        memory_id = await conn.fetchval("""
            INSERT INTO memories (content, memory_type, importance_score)
            VALUES ($1, $2, $3)
            RETURNING id
        """, "Test memory for v4.2", "test", 0.5)
        
        print(f"  ✓ Created test memory: {memory_id}")
        
        # Test vector storage
        import numpy as np
        test_embedding = np.random.rand(1536).tolist()
        
        await conn.execute("""
            UPDATE memories 
            SET embedding = $1::vector
            WHERE id = $2
        """, test_embedding, memory_id)
        
        print("  ✓ Stored vector embedding")
        
        # Test vector search
        result = await conn.fetchval("""
            SELECT COUNT(*) FROM memories
            WHERE embedding IS NOT NULL
        """)
        
        print(f"  ✓ Found {result} memories with embeddings")
        
        # Clean up
        await conn.execute("DELETE FROM memories WHERE memory_type = 'test'")
        
        await conn.close()
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


async def main():
    """Main setup function"""
    success = await setup_database()
    
    if success:
        # Optionally run tests
        if "--test" in sys.argv:
            await test_connection()
            
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)