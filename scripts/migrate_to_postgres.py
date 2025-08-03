#!/usr/bin/env python3
"""
Migration script from SQLite/JSON to PostgreSQL with pgvector
Supports migrating existing memories to the new unified backend
"""

import os
import sys
import json
import asyncio
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import asyncpg
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.postgres_unified import PostgresUnifiedBackend
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MigrationManager:
    """Manages migration from various sources to PostgreSQL"""
    
    def __init__(self, postgres_backend: PostgresUnifiedBackend):
        self.postgres = postgres_backend
        self.stats = {
            "memories_migrated": 0,
            "errors": 0,
            "skipped": 0
        }
        
    async def migrate_from_json(self, json_path: str) -> bool:
        """Migrate from JSON file storage"""
        
        json_file = Path(json_path)
        if not json_file.exists():
            logger.warning(f"JSON file not found: {json_path}")
            return False
            
        print(f"\n📂 Migrating from JSON: {json_file.name}")
        print("=" * 50)
        
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                
            # Handle both dict and list formats
            if isinstance(data, dict):
                memories = list(data.values())
            elif isinstance(data, list):
                memories = data
            else:
                logger.error(f"Unexpected JSON format: {type(data)}")
                return False
                
            print(f"  Found {len(memories)} memories to migrate")
            
            for i, memory in enumerate(memories, 1):
                try:
                    # Ensure required fields
                    if not memory.get("content"):
                        self.stats["skipped"] += 1
                        continue
                        
                    # Create memory in PostgreSQL
                    await self.postgres.create_memory(memory)
                    self.stats["memories_migrated"] += 1
                    
                    if i % 10 == 0:
                        print(f"  ✓ Migrated {i}/{len(memories)} memories")
                        
                except Exception as e:
                    logger.error(f"Failed to migrate memory {i}: {e}")
                    self.stats["errors"] += 1
                    
            print(f"\n✅ JSON migration complete!")
            self._print_stats()
            return True
            
        except Exception as e:
            logger.error(f"JSON migration failed: {e}")
            return False
            
    async def migrate_from_sqlite(self, sqlite_path: str) -> bool:
        """Migrate from SQLite database"""
        
        db_file = Path(sqlite_path)
        if not db_file.exists():
            logger.warning(f"SQLite database not found: {sqlite_path}")
            return False
            
        print(f"\n🗄️ Migrating from SQLite: {db_file.name}")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if memories table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='memories'
            """)
            
            if not cursor.fetchone():
                logger.error("No 'memories' table found in SQLite database")
                return False
                
            # Get all memories
            cursor.execute("SELECT * FROM memories ORDER BY created_at")
            rows = cursor.fetchall()
            
            print(f"  Found {len(rows)} memories to migrate")
            
            for i, row in enumerate(rows, 1):
                try:
                    # Convert SQLite row to dict
                    memory = {
                        "id": row["id"],
                        "content": row["content"],
                        "memory_type": row["memory_type"],
                        "importance_score": row["importance_score"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "access_count": row.get("access_count", 0)
                    }
                    
                    # Handle timestamps
                    for field in ["created_at", "updated_at", "last_accessed_at"]:
                        if field in row and row[field]:
                            memory[field] = row[field]
                            
                    # Create memory in PostgreSQL
                    await self.postgres.create_memory(memory)
                    self.stats["memories_migrated"] += 1
                    
                    if i % 10 == 0:
                        print(f"  ✓ Migrated {i}/{len(rows)} memories")
                        
                except Exception as e:
                    logger.error(f"Failed to migrate memory {i}: {e}")
                    self.stats["errors"] += 1
                    
            conn.close()
            
            print(f"\n✅ SQLite migration complete!")
            self._print_stats()
            return True
            
        except Exception as e:
            logger.error(f"SQLite migration failed: {e}")
            return False
            
    async def migrate_from_directory(self, directory: str) -> bool:
        """Migrate from a directory of JSON/SQLite files"""
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return False
            
        print(f"\n📁 Migrating from directory: {dir_path}")
        print("=" * 50)
        
        # Find all potential files
        json_files = list(dir_path.glob("*.json"))
        sqlite_files = list(dir_path.glob("*.db")) + list(dir_path.glob("*.sqlite"))
        
        print(f"  Found {len(json_files)} JSON files")
        print(f"  Found {len(sqlite_files)} SQLite databases")
        
        success = True
        
        # Migrate JSON files
        for json_file in json_files:
            if "memories" in json_file.name.lower():
                success &= await self.migrate_from_json(str(json_file))
                
        # Migrate SQLite databases
        for db_file in sqlite_files:
            if "memories" in db_file.name.lower():
                success &= await self.migrate_from_sqlite(str(db_file))
                
        return success
        
    async def add_embeddings(self, model: str = "text-embedding-ada-002") -> bool:
        """Add embeddings to memories that don't have them"""
        
        print(f"\n🤖 Adding embeddings to memories")
        print("=" * 50)
        
        try:
            # Get memories without embeddings
            query = """
                SELECT id, content FROM memories
                WHERE embedding IS NULL
                AND deleted_at IS NULL
                LIMIT 100
            """
            
            async with self.postgres.acquire() as conn:
                rows = await conn.fetch(query)
                
            if not rows:
                print("  ✓ All memories already have embeddings")
                return True
                
            print(f"  Found {len(rows)} memories without embeddings")
            
            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("  ⚠️ OPENAI_API_KEY not set, skipping embedding generation")
                print("  Set the key and run: python scripts/migrate_to_postgres.py --embeddings")
                return False
                
            # Import OpenAI (optional dependency)
            try:
                import openai
                openai.api_key = api_key
            except ImportError:
                print("  ⚠️ OpenAI library not installed")
                print("  Install with: pip install openai")
                return False
                
            # Generate embeddings in batches
            batch_size = 10
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                texts = [row["content"] for row in batch]
                
                try:
                    # Generate embeddings
                    response = await openai.Embedding.acreate(
                        model=model,
                        input=texts
                    )
                    
                    # Update memories with embeddings
                    for j, row in enumerate(batch):
                        embedding = response["data"][j]["embedding"]
                        await self.postgres.update_memory(
                            str(row["id"]),
                            {},
                            new_embedding=embedding
                        )
                        
                    print(f"  ✓ Added embeddings to {min(i+batch_size, len(rows))}/{len(rows)} memories")
                    
                except Exception as e:
                    logger.error(f"Failed to generate embeddings: {e}")
                    
            print(f"\n✅ Embedding generation complete!")
            return True
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return False
            
    def _print_stats(self):
        """Print migration statistics"""
        print(f"\n📊 Migration Statistics:")
        print(f"  ✓ Migrated: {self.stats['memories_migrated']}")
        print(f"  ⚠️ Skipped: {self.stats['skipped']}")
        print(f"  ❌ Errors: {self.stats['errors']}")


async def main():
    """Main migration function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate memories to PostgreSQL")
    parser.add_argument(
        "--source",
        type=str,
        help="Source file or directory to migrate from"
    )
    parser.add_argument(
        "--json",
        type=str,
        help="JSON file to migrate from"
    )
    parser.add_argument(
        "--sqlite",
        type=str,
        help="SQLite database to migrate from"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="/data",
        help="Directory to scan for memory files"
    )
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Generate embeddings for memories without them"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=os.getenv("DATABASE_URL", "postgresql://localhost/second_brain"),
        help="PostgreSQL connection string"
    )
    
    args = parser.parse_args()
    
    print("🚀 Second Brain Migration Tool v4.2")
    print("=" * 50)
    
    # Initialize PostgreSQL backend
    backend = PostgresUnifiedBackend(args.database_url)
    await backend.initialize()
    
    # Create migration manager
    migrator = MigrationManager(backend)
    
    success = True
    
    # Run migrations based on arguments
    if args.json:
        success &= await migrator.migrate_from_json(args.json)
        
    if args.sqlite:
        success &= await migrator.migrate_from_sqlite(args.sqlite)
        
    if args.source:
        # Auto-detect source type
        source_path = Path(args.source)
        if source_path.is_file():
            if source_path.suffix == ".json":
                success &= await migrator.migrate_from_json(str(source_path))
            elif source_path.suffix in [".db", ".sqlite"]:
                success &= await migrator.migrate_from_sqlite(str(source_path))
        elif source_path.is_dir():
            success &= await migrator.migrate_from_directory(str(source_path))
            
    elif not args.json and not args.sqlite and not args.embeddings:
        # Default: scan directory
        success &= await migrator.migrate_from_directory(args.directory)
        
    # Generate embeddings if requested
    if args.embeddings:
        success &= await migrator.add_embeddings()
        
    # Cleanup
    await backend.close()
    
    if success:
        print("\n✅ Migration completed successfully!")
        
        # Show next steps
        print("\n📝 Next steps:")
        print("  1. Verify data: psql -d second_brain -c 'SELECT COUNT(*) FROM memories;'")
        print("  2. Test search: python -c 'from app.storage.postgres_unified import *'")
        print("  3. Update app configuration to use PostgreSQL backend")
        
        return 0
    else:
        print("\n❌ Migration completed with errors")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)