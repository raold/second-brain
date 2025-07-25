"""
CLI command for running the event worker.

Usage: python -m src.cli.worker
"""

import asyncio
import click

from src.infrastructure.workers import EventWorker


@click.command()
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
def worker(log_level: str):
    """Run the event worker for processing background tasks."""
    import os
    os.environ["LOG_LEVEL"] = log_level
    
    click.echo("Starting Second Brain event worker...")
    asyncio.run(run_worker())


async def run_worker():
    """Run the worker with proper error handling."""
    worker = EventWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        click.echo("\nShutting down worker...")
    except Exception as e:
        click.echo(f"Worker error: {e}", err=True)
    finally:
        await worker.stop()


if __name__ == "__main__":
    worker()