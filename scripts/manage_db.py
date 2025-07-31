"""
Database management script.

Provides commands for database operations.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from src.infrastructure.database import get_connection


def get_alembic_config():
    """Get Alembic configuration."""
    config = Config("alembic.ini")
    return config


@click.group()
def cli():
    """Database management commands."""
    pass


@cli.command()
def init():
    """Initialize database with migrations."""
    click.echo("Initializing database...")

    # Run migrations
    config = get_alembic_config()
    command.upgrade(config, "head")

    click.echo("Database initialized successfully!")


@cli.command()
def migrate():
    """Create a new migration."""
    message = click.prompt("Migration message")

    config = get_alembic_config()
    command.revision(config, autogenerate=True, message=message)

    click.echo(f"Migration created: {message}")


@cli.command()
def upgrade():
    """Apply pending migrations."""
    click.echo("Applying migrations...")

    config = get_alembic_config()
    command.upgrade(config, "head")

    click.echo("Migrations applied successfully!")


@cli.command()
def downgrade():
    """Rollback last migration."""
    if click.confirm("Are you sure you want to rollback?"):
        config = get_alembic_config()
        command.downgrade(config, "-1")

        click.echo("Rollback completed!")


@cli.command()
def history():
    """Show migration history."""
    config = get_alembic_config()
    command.history(config)


@cli.command()
def reset():
    """Reset database (DANGEROUS!)."""
    if not click.confirm("This will DELETE ALL DATA. Are you sure?"):
        return

    if not click.confirm("Are you REALLY sure? This cannot be undone!"):
        return

    async def drop_all():
        conn = await get_connection()
        async with conn.get_session() as session:
            # Drop all tables
            await session.execute(text("DROP SCHEMA public CASCADE"))
            await session.execute(text("CREATE SCHEMA public"))
            await session.commit()

    asyncio.run(drop_all())
    click.echo("Database reset completed!")

    # Re-initialize
    init()


@cli.command()
def seed():
    """Seed database with sample data."""
    click.echo("Seeding database...")

    async def seed_data():
        from uuid import uuid4

        import bcrypt

        conn = await get_connection()
        async with conn.get_session() as session:
            # Create admin user
            from src.infrastructure.database.models import UserModel

            admin = UserModel(
                id=uuid4(),
                email="admin@secondbrain.com",
                username="admin",
                full_name="Admin User",
                password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
                role="admin",
                is_active=True,
                is_verified=True,
                preferences={},
                memory_limit=100000,
                storage_limit_mb=50000,
                api_rate_limit=10000,
            )

            session.add(admin)
            await session.commit()

            click.echo(f"Created admin user: {admin.email}")

    asyncio.run(seed_data())
    click.echo("Database seeded successfully!")


if __name__ == "__main__":
    cli()
