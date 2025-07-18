#!/usr/bin/env python3
"""
Migration CLI Tool for Second Brain

Simple command-line interface for managing database and memory migrations.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.database_migrations import AddImportanceScoreToMemories
from app.memory_migrations import AddMemoryTypeClassification, ConsolidateDuplicateMemories
from app.migration_engine import MigrationEngine
from app.migration_framework import MigrationConfig, MigrationType


async def initialize_engine() -> MigrationEngine:
    """Initialize migration engine with database connection."""
    # Initialize database
    db = Database()
    await db.initialize()

    if not db.pool:
        raise RuntimeError("Database pool not initialized")

    # Create migration engine
    engine = MigrationEngine(db.pool)
    await engine.initialize()

    # Register available migrations
    # Database migrations
    engine.register_migration(AddImportanceScoreToMemories)

    # Memory migrations
    engine.register_migration(AddMemoryTypeClassification)
    engine.register_migration(ConsolidateDuplicateMemories)

    return engine


async def list_migrations(engine: MigrationEngine, migration_type: Optional[str] = None):
    """List pending migrations."""
    pending = await engine.get_pending_migrations()

    if migration_type:
        type_enum = MigrationType[migration_type.upper()]
        pending = [m for m in pending if m.migration_type == type_enum]

    if not pending:
        print("✅ No pending migrations")
        return

    print(f"📋 Pending Migrations ({len(pending)} total):")
    print("-" * 80)

    for m in pending:
        print(f"ID: {m.id}")
        print(f"   Name: {m.name}")
        print(f"   Type: {m.migration_type.value}")
        print(f"   Version: {m.version}")
        print(f"   Dependencies: {', '.join(m.dependencies) if m.dependencies else 'None'}")
        print(f"   Reversible: {'Yes' if m.reversible else 'No'}")
        print()


async def run_migration(engine: MigrationEngine, migration_id: str, dry_run: bool = False, batch_size: int = 1000):
    """Execute a specific migration."""
    print(f"🚀 {'[DRY RUN] ' if dry_run else ''}Executing migration: {migration_id}")

    config = MigrationConfig(
        dry_run=dry_run, batch_size=batch_size, enable_rollback=True, validate_before=True, validate_after=True
    )

    try:
        result = await engine.execute_migration(migration_id, config)

        if result.status.value == "completed":
            print("✅ Migration completed successfully!")
            print(f"   Affected items: {result.affected_items}")
            if result.end_time and result.start_time:
                execution_time = (result.end_time - result.start_time).total_seconds()
                print(f"   Execution time: {execution_time:.2f}s")

            if result.performance_metrics:
                print("   Performance metrics:")
                for key, value in result.performance_metrics.items():
                    print(f"     - {key}: {value}")

        elif result.status.value == "failed":
            print("❌ Migration failed!")
            print(f"   Errors: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"     - {error}")

        elif result.status.value == "rolled_back":
            print("↩️  Migration rolled back due to errors")

    except Exception as e:
        print(f"❌ Error executing migration: {e}")
        sys.exit(1)


async def run_all_migrations(engine: MigrationEngine, migration_type: Optional[str] = None, dry_run: bool = False):
    """Execute all pending migrations."""
    type_enum = MigrationType[migration_type.upper()] if migration_type else None

    config = MigrationConfig(
        dry_run=dry_run, enable_rollback=True, validate_before=True, validate_after=True, continue_on_error=False
    )

    print(f"🚀 {'[DRY RUN] ' if dry_run else ''}Executing all pending migrations...")

    results = await engine.execute_pending_migrations(config, type_enum)

    successful = sum(1 for r in results if r.status.value == "completed")
    failed = sum(1 for r in results if r.status.value == "failed")

    print("\n📊 Summary:")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")

    if failed > 0:
        print("\n❌ Some migrations failed. Check logs for details.")
        sys.exit(1)


async def rollback_migration(engine: MigrationEngine, migration_id: str):
    """Rollback a specific migration."""
    print(f"↩️  Rolling back migration: {migration_id}")

    try:
        result = await engine.rollback_migration(migration_id)

        if result.status.value == "rolled_back":
            print("✅ Migration rolled back successfully!")
        else:
            print("❌ Rollback failed!")
            for error in result.errors:
                print(f"   - {error}")

    except Exception as e:
        print(f"❌ Error rolling back migration: {e}")
        sys.exit(1)


async def show_history(engine: MigrationEngine, limit: int = 10):
    """Show migration history."""
    applied = await engine.history.get_applied_migrations()

    print(f"📜 Migration History (last {limit}):")
    print("-" * 80)

    for migration_id in applied[-limit:]:
        status = await engine.history.get_migration_status(migration_id)
        if status:
            print(f"ID: {migration_id}")
            print(f"   Status: {status['status']}")
            print(f"   Applied: {status.get('applied_at', 'Unknown')}")
            print(f"   Items: {status.get('affected_items', 0)}")
            print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Second Brain Migration Tool", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List pending migrations")
    list_parser.add_argument(
        "--type",
        choices=["database_schema", "database_data", "memory_structure", "memory_data"],
        help="Filter by migration type",
    )

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute migrations")
    run_parser.add_argument("migration_id", nargs="?", help="Specific migration ID")
    run_parser.add_argument("--all", action="store_true", help="Run all pending migrations")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate without applying")
    run_parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for data migrations")
    run_parser.add_argument(
        "--type",
        choices=["database_schema", "database_data", "memory_structure", "memory_data"],
        help="Filter by type (with --all)",
    )

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback a migration")
    rollback_parser.add_argument("migration_id", help="Migration ID to rollback")

    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of entries to show")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run async command
    async def run_command():
        engine = await initialize_engine()

        try:
            if args.command == "list":
                await list_migrations(engine, args.type)

            elif args.command == "run":
                if args.all:
                    await run_all_migrations(engine, args.type, args.dry_run)
                elif args.migration_id:
                    await run_migration(engine, args.migration_id, args.dry_run, args.batch_size)
                else:
                    print("❌ Specify migration ID or use --all")
                    sys.exit(1)

            elif args.command == "rollback":
                await rollback_migration(engine, args.migration_id)

            elif args.command == "history":
                await show_history(engine, args.limit)

        finally:
            # Close database connection
            if engine.pool:
                await engine.pool.close()

    # Run the async command
    asyncio.run(run_command())


if __name__ == "__main__":
    main()
