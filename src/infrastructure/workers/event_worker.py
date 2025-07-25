"""
Event worker service for processing domain events.

Consumes events from message queue and delegates to handlers.
"""

import asyncio
import signal
from typing import Optional

from src.application import get_dependencies
from src.infrastructure.logging import get_logger
from src.infrastructure.messaging.handlers import LoggingEventHandler
from src.infrastructure.messaging.memory_handlers import MemoryEventHandler

logger = get_logger(__name__)


class EventWorker:
    """Background worker for processing events."""
    
    def __init__(self):
        """Initialize event worker."""
        self.dependencies = None
        self.message_broker = None
        self.handlers = []
        self._running = False
        self._tasks = []
    
    async def start(self) -> None:
        """Start the event worker."""
        logger.info("Starting event worker")
        
        # Initialize dependencies
        self.dependencies = await get_dependencies()
        self.message_broker = await self.dependencies.get_message_broker()
        
        if not self.message_broker:
            logger.error("Message broker not available")
            return
        
        # Initialize handlers
        self.handlers = [
            LoggingEventHandler(),
            MemoryEventHandler(self.dependencies),
        ]
        
        # Subscribe to events
        for handler in self.handlers:
            await self.message_broker.subscribe(
                "events.#",  # Subscribe to all events
                handler.handle,
                queue_name=f"secondbrain.worker.{handler.__class__.__name__}",
            )
        
        self._running = True
        logger.info("Event worker started")
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the event worker."""
        logger.info("Stopping event worker")
        
        self._running = False
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close dependencies
        if self.dependencies:
            await self.dependencies.close()
        
        logger.info("Event worker stopped")
    
    def handle_signal(self, signum: int, frame: any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.stop())


async def main():
    """Run the event worker."""
    worker = EventWorker()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, worker.handle_signal)
    signal.signal(signal.SIGTERM, worker.handle_signal)
    
    try:
        await worker.start()
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())