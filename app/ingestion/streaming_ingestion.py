"""
Streaming ingestion architecture for real-time content processing
"""

import asyncio
import logging
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Union, Tuple

logger = logging.getLogger(__name__)


class StreamStatus(str, Enum):
    """Status of streaming ingestion"""
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class StreamMessage:
    """Message in the streaming pipeline"""
    id: str
    content: str
    metadata: dict[str, Any]
    timestamp: datetime
    source: str
    priority: int = 5
    retry_count: int = 0


@dataclass
class StreamingStats:
    """Statistics for streaming ingestion"""
    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    total_processing_time: float = 0
    average_processing_time: float = 0
    current_queue_size: int = 0
    peak_queue_size: int = 0


class StreamingIngestionPipeline:
    """Asynchronous streaming ingestion pipeline"""

    def __init__(self,
                 max_queue_size: int = 1000,
                 batch_size: int = 10,
                 batch_timeout: float = 5.0,
                 max_workers: int = 4,
                 retry_limit: int = 3):
        """
        Initialize streaming pipeline

        Args:
            max_queue_size: Maximum messages in queue
            batch_size: Size of processing batches
            batch_timeout: Timeout for batch collection
            max_workers: Maximum concurrent workers
            retry_limit: Maximum retries for failed messages
        """
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        self.retry_limit = retry_limit

        # Queues
        self.input_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.dead_letter_queue: deque = deque(maxlen=1000)

        # State
        self.status = StreamStatus.IDLE
        self.stats = StreamingStats()
        self.workers: list[asyncio.Task] = []

        # Processors
        self.preprocessors: list[Callable] = []
        self.processors: list[Callable] = []
        self.postprocessors: list[Callable] = []

        # Event handlers
        self.error_handlers: list[Callable] = []
        self.completion_handlers: list[Callable] = []

        # Control
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused

    async def start(self):
        """Start the streaming pipeline"""
        if self.status != StreamStatus.IDLE:
            raise RuntimeError(f"Pipeline already running with status: {self.status}")

        logger.info("Starting streaming ingestion pipeline")
        self.status = StreamStatus.PROCESSING
        self._stop_event.clear()

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # Start batch collector
        batch_collector = asyncio.create_task(self._batch_collector())
        self.workers.append(batch_collector)

        # Start output processor
        output_processor = asyncio.create_task(self._output_processor())
        self.workers.append(output_processor)

        # Start stats reporter
        stats_reporter = asyncio.create_task(self._stats_reporter())
        self.workers.append(stats_reporter)

    async def stop(self):
        """Stop the streaming pipeline"""
        logger.info("Stopping streaming ingestion pipeline")
        self._stop_event.set()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.status = StreamStatus.COMPLETED
        logger.info(f"Pipeline stopped. Final stats: {self.get_stats()}")

    async def pause(self):
        """Pause processing"""
        logger.info("Pausing pipeline")
        self._pause_event.clear()
        self.status = StreamStatus.PAUSED

    async def resume(self):
        """Resume processing"""
        logger.info("Resuming pipeline")
        self._pause_event.set()
        self.status = StreamStatus.PROCESSING

    async def ingest(self, content: Union[str, StreamMessage], metadata: dict[str, Any] | None = None) -> str:
        """
        Add content to the ingestion pipeline

        Args:
            content: Content to ingest or StreamMessage
            metadata: Optional metadata

        Returns:
            Message ID
        """
        if isinstance(content, str):
            message = StreamMessage(
                id=self._generate_message_id(),
                content=content,
                metadata=metadata or {},
                timestamp=datetime.utcnow(),
                source="direct"
            )
        else:
            message = content

        try:
            await self.input_queue.put(message)
            self.stats.messages_received += 1
            self._update_queue_stats()

            return message.id

        except asyncio.QueueFull:
            logger.error("Input queue is full")
            raise RuntimeError("Pipeline is overloaded")

    async def ingest_stream(self, stream: AsyncIterator[Union[str, dict[str, Any]]]) -> AsyncIterator[str]:
        """
        Ingest from an async stream

        Args:
            stream: Async iterator of content

        Yields:
            Message IDs
        """
        async for item in stream:
            if isinstance(item, str):
                message_id = await self.ingest(item)
            elif isinstance(item, dict):
                content = item.get("content", "")
                metadata = item.get("metadata", {})
                message_id = await self.ingest(content, metadata)
            else:
                logger.warning(f"Skipping invalid stream item: {type(item)}")
                continue

            yield message_id

    def add_preprocessor(self, processor: Callable):
        """Add a preprocessing function"""
        self.preprocessors.append(processor)

    def add_processor(self, processor: Callable):
        """Add a processing function"""
        self.processors.append(processor)

    def add_postprocessor(self, processor: Callable):
        """Add a postprocessing function"""
        self.postprocessors.append(processor)

    def add_error_handler(self, handler: Callable):
        """Add an error handler"""
        self.error_handlers.append(handler)

    def add_completion_handler(self, handler: Callable):
        """Add a completion handler"""
        self.completion_handlers.append(handler)

    async def _worker(self, worker_id: str):
        """Worker process for handling messages"""
        logger.info(f"Worker {worker_id} started")

        while not self._stop_event.is_set():
            try:
                # Wait if paused
                await self._pause_event.wait()

                # Get batch from processing queue
                batch = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )

                # Process batch
                await self._process_batch(batch, worker_id)

            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await self._handle_error(e, worker_id)

        logger.info(f"Worker {worker_id} stopped")

    async def _batch_collector(self):
        """Collect messages into batches"""
        logger.info("Batch collector started")

        while not self._stop_event.is_set():
            try:
                batch = []
                deadline = asyncio.get_event_loop().time() + self.batch_timeout

                # Collect batch
                while len(batch) < self.batch_size:
                    timeout = max(0, deadline - asyncio.get_event_loop().time())

                    if timeout <= 0:
                        break

                    try:
                        message = await asyncio.wait_for(
                            self.input_queue.get(),
                            timeout=timeout
                        )
                        batch.append(message)
                    except TimeoutError:
                        break

                # Send batch if not empty
                if batch:
                    await self.processing_queue.put(batch)

            except Exception as e:
                logger.error(f"Batch collector error: {e}")
                await self._handle_error(e, "batch_collector")

        logger.info("Batch collector stopped")

    async def _process_batch(self, batch: list[StreamMessage], worker_id: str):
        """Process a batch of messages"""
        start_time = asyncio.get_event_loop().time()

        for message in batch:
            try:
                # Apply preprocessors
                for preprocessor in self.preprocessors:
                    message = await self._apply_processor(preprocessor, message)

                # Apply main processors
                processed_content = None
                for processor in self.processors:
                    if processed_content is None:
                        processed_content = await self._apply_processor(processor, message)
                    else:
                        processed_content = await self._apply_processor(processor, processed_content)

                # Apply postprocessors
                for postprocessor in self.postprocessors:
                    processed_content = await self._apply_processor(postprocessor, processed_content)

                # Send to output queue
                await self.output_queue.put((message, processed_content))

                # Update stats
                self.stats.messages_processed += 1

            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")

                # Retry logic
                if message.retry_count < self.retry_limit:
                    message.retry_count += 1
                    await self.input_queue.put(message)
                else:
                    # Send to dead letter queue
                    self.dead_letter_queue.append((message, str(e)))
                    self.stats.messages_failed += 1

        # Update processing time stats
        processing_time = asyncio.get_event_loop().time() - start_time
        self.stats.total_processing_time += processing_time
        self.stats.average_processing_time = (
            self.stats.total_processing_time / max(1, self.stats.messages_processed)
        )

    async def _apply_processor(self, processor: Callable, data: Any) -> Any:
        """Apply a processor function"""
        if asyncio.iscoroutinefunction(processor):
            return await processor(data)
        else:
            # Run sync function in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, processor, data)

    async def _output_processor(self):
        """Process output queue"""
        logger.info("Output processor started")

        while not self._stop_event.is_set():
            try:
                # Get from output queue
                message, processed_content = await asyncio.wait_for(
                    self.output_queue.get(),
                    timeout=1.0
                )

                # Call completion handlers
                for handler in self.completion_handlers:
                    await self._apply_processor(handler, (message, processed_content))

            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Output processor error: {e}")
                await self._handle_error(e, "output_processor")

        logger.info("Output processor stopped")

    async def _stats_reporter(self):
        """Periodically report statistics"""
        while not self._stop_event.is_set():
            await asyncio.sleep(30)  # Report every 30 seconds

            stats = self.get_stats()
            logger.info(f"Pipeline stats: {stats}")

    async def _handle_error(self, error: Exception, context: str):
        """Handle errors"""
        error_info = {
            "error": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }

        for handler in self.error_handlers:
            try:
                await self._apply_processor(handler, error_info)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")

    def _update_queue_stats(self):
        """Update queue statistics"""
        current_size = self.input_queue.qsize()
        self.stats.current_queue_size = current_size

        if current_size > self.stats.peak_queue_size:
            self.stats.peak_queue_size = current_size

    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        import uuid
        return str(uuid.uuid4())

    def get_stats(self) -> dict[str, Any]:
        """Get current pipeline statistics"""
        return {
            "status": self.status,
            "messages_received": self.stats.messages_received,
            "messages_processed": self.stats.messages_processed,
            "messages_failed": self.stats.messages_failed,
            "success_rate": (
                self.stats.messages_processed / max(1, self.stats.messages_received) * 100
            ),
            "average_processing_time": round(self.stats.average_processing_time, 3),
            "current_queue_size": self.stats.current_queue_size,
            "peak_queue_size": self.stats.peak_queue_size,
            "dead_letter_count": len(self.dead_letter_queue)
        }

    def get_dead_letters(self) -> list[Tuple[StreamMessage, str]]:
        """Get messages from dead letter queue"""
        return list(self.dead_letter_queue)

    async def health_check(self) -> dict[str, Any]:
        """Check pipeline health"""
        health = {
            "status": self.status,
            "is_healthy": True,
            "checks": {}
        }

        # Check queue health
        queue_usage = self.stats.current_queue_size / self.max_queue_size
        health["checks"]["queue_usage"] = {
            "value": queue_usage,
            "healthy": queue_usage < 0.8
        }

        # Check processing rate
        if self.stats.messages_received > 0:
            processing_rate = self.stats.messages_processed / self.stats.messages_received
            health["checks"]["processing_rate"] = {
                "value": processing_rate,
                "healthy": processing_rate > 0.9
            }

        # Check error rate
        if self.stats.messages_received > 0:
            error_rate = self.stats.messages_failed / self.stats.messages_received
            health["checks"]["error_rate"] = {
                "value": error_rate,
                "healthy": error_rate < 0.05
            }

        # Overall health
        health["is_healthy"] = all(
            check.get("healthy", True)
            for check in health["checks"].values()
        )

        return health


class StreamingIngestionBuilder:
    """Builder for creating streaming ingestion pipelines"""

    def __init__(self):
        self.config = {
            "max_queue_size": 1000,
            "batch_size": 10,
            "batch_timeout": 5.0,
            "max_workers": 4,
            "retry_limit": 3
        }
        self.preprocessors = []
        self.processors = []
        self.postprocessors = []
        self.error_handlers = []
        self.completion_handlers = []

    def with_queue_size(self, size: int) -> 'StreamingIngestionBuilder':
        """Set maximum queue size"""
        self.config["max_queue_size"] = size
        return self

    def with_batch_config(self, size: int, timeout: float) -> 'StreamingIngestionBuilder':
        """Set batch configuration"""
        self.config["batch_size"] = size
        self.config["batch_timeout"] = timeout
        return self

    def with_workers(self, count: int) -> 'StreamingIngestionBuilder':
        """Set number of workers"""
        self.config["max_workers"] = count
        return self

    def with_retry_limit(self, limit: int) -> 'StreamingIngestionBuilder':
        """Set retry limit"""
        self.config["retry_limit"] = limit
        return self

    def add_preprocessor(self, processor: Callable) -> 'StreamingIngestionBuilder':
        """Add preprocessor"""
        self.preprocessors.append(processor)
        return self

    def add_processor(self, processor: Callable) -> 'StreamingIngestionBuilder':
        """Add processor"""
        self.processors.append(processor)
        return self

    def add_postprocessor(self, processor: Callable) -> 'StreamingIngestionBuilder':
        """Add postprocessor"""
        self.postprocessors.append(processor)
        return self

    def add_error_handler(self, handler: Callable) -> 'StreamingIngestionBuilder':
        """Add error handler"""
        self.error_handlers.append(handler)
        return self

    def add_completion_handler(self, handler: Callable) -> 'StreamingIngestionBuilder':
        """Add completion handler"""
        self.completion_handlers.append(handler)
        return self

    def build(self) -> StreamingIngestionPipeline:
        """Build the pipeline"""
        pipeline = StreamingIngestionPipeline(**self.config)

        # Add processors
        for p in self.preprocessors:
            pipeline.add_preprocessor(p)
        for p in self.processors:
            pipeline.add_processor(p)
        for p in self.postprocessors:
            pipeline.add_postprocessor(p)

        # Add handlers
        for h in self.error_handlers:
            pipeline.add_error_handler(h)
        for h in self.completion_handlers:
            pipeline.add_completion_handler(h)

        return pipeline
