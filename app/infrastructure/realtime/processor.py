"""
Real-time processing system for streaming data
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from app.infrastructure.preprocessing import Pipeline, PipelineData
from app.infrastructure.streaming import (
    Event,
    EventBus,
    EventType,
    ProcessingEvent,
    Stream,
    StreamItem,
    StreamProcessor,
    publish_event,
)
from app.infrastructure.validation import ValidationResult, Validator

logger = logging.getLogger(__name__)


class ProcessingPriority(str, Enum):
    """Priority levels for processing"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class ProcessingRequest:
    """Request for real-time processing"""
    id: UUID = field(default_factory=uuid4)
    data: Any = None
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if request has expired"""
        if self.deadline:
            return datetime.utcnow() > self.deadline
        return False
        
    @property
    def age(self) -> timedelta:
        """Get age of request"""
        return datetime.utcnow() - self.created_at


@dataclass
class ProcessingResult:
    """Result of processing"""
    request_id: UUID
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class RealTimeProcessor:
    """
    Real-time processor with priority queues and resource management
    """
    
    def __init__(
        self,
        name: str,
        process_func: Callable[[ProcessingRequest], ProcessingResult],
        max_workers: int = 10,
        max_queue_size: int = 1000,
        timeout: float = 30.0
    ):
        self.name = name
        self.process_func = process_func
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.timeout = timeout
        
        # Priority queues
        self._queues: Dict[ProcessingPriority, asyncio.Queue[ProcessingRequest]] = {
            priority: asyncio.Queue(maxsize=max_queue_size)
            for priority in ProcessingPriority
        }
        
        # Worker management
        self._workers: Set[asyncio.Task] = set()
        self._running = False
        self._semaphore = asyncio.Semaphore(max_workers)
        
        # Metrics
        self._processed_count = 0
        self._error_count = 0
        self._total_duration_ms = 0
        self._queue_times: List[float] = []
        
    async def start(self):
        """Start the processor"""
        if self._running:
            return
            
        self._running = True
        
        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.add(worker)
            
        logger.info(f"Real-time processor {self.name} started with {self.max_workers} workers")
        
    async def stop(self):
        """Stop the processor"""
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
            
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info(f"Real-time processor {self.name} stopped")
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process a request
        
        Args:
            request: Processing request
            
        Returns:
            Processing result
        """
        # Add to appropriate queue
        queue = self._queues[request.priority]
        
        try:
            await queue.put(request)
            
            # Wait for processing
            start_time = time.time()
            
            # Poll for result
            while True:
                # Check if request is being processed
                if hasattr(request, '_result'):
                    queue_time = (time.time() - start_time) * 1000
                    self._queue_times.append(queue_time)
                    return request._result
                    
                # Check timeout
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Processing timeout after {self.timeout}s")
                    
                await asyncio.sleep(0.1)
                
        except asyncio.QueueFull:
            return ProcessingResult(
                request_id=request.id,
                success=False,
                error="Queue full"
            )
            
    async def _worker(self, worker_id: int):
        """Worker coroutine"""
        logger.info(f"Worker {worker_id} started for processor {self.name}")
        
        while self._running:
            try:
                # Get next request from highest priority queue
                request = await self._get_next_request()
                
                if request:
                    async with self._semaphore:
                        await self._process_request(request)
                else:
                    # No requests, sleep briefly
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                
        logger.info(f"Worker {worker_id} stopped")
        
    async def _get_next_request(self) -> Optional[ProcessingRequest]:
        """Get next request from priority queues"""
        # Check queues in priority order
        for priority in ProcessingPriority:
            queue = self._queues[priority]
            
            try:
                # Non-blocking get
                request = queue.get_nowait()
                
                # Skip expired requests
                if request.is_expired:
                    logger.warning(f"Skipping expired request {request.id}")
                    continue
                    
                return request
                
            except asyncio.QueueEmpty:
                continue
                
        return None
        
    async def _process_request(self, request: ProcessingRequest):
        """Process a single request"""
        start_time = time.time()
        
        try:
            # Emit processing started event
            await publish_event(ProcessingEvent(
                event_type=EventType.PROCESSING_STARTED,
                processor_name=self.name,
                data={"request_id": str(request.id), "priority": request.priority.value}
            ))
            
            # Process the request
            if asyncio.iscoroutinefunction(self.process_func):
                result = await self.process_func(request)
            else:
                result = self.process_func(request)
                
            # Update metrics
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            self._processed_count += 1
            self._total_duration_ms += duration_ms
            
            # Store result on request (for polling)
            request._result = result
            
            # Emit processing completed event
            await publish_event(ProcessingEvent(
                event_type=EventType.PROCESSING_COMPLETED,
                processor_name=self.name,
                duration_ms=duration_ms,
                data={"request_id": str(request.id), "success": result.success}
            ))
            
        except Exception as e:
            # Handle processing error
            duration_ms = int((time.time() - start_time) * 1000)
            self._error_count += 1
            
            result = ProcessingResult(
                request_id=request.id,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
            
            request._result = result
            
            # Emit processing failed event
            await publish_event(ProcessingEvent(
                event_type=EventType.PROCESSING_FAILED,
                processor_name=self.name,
                duration_ms=duration_ms,
                error=str(e),
                data={"request_id": str(request.id)}
            ))
            
            logger.error(f"Processing error for request {request.id}: {e}")
            
    @property
    def metrics(self) -> dict[str, Any]:
        """Get processor metrics"""
        queue_sizes = {
            priority.value: self._queues[priority].qsize()
            for priority in ProcessingPriority
        }
        
        avg_duration = (
            self._total_duration_ms / self._processed_count
            if self._processed_count > 0
            else 0
        )
        
        avg_queue_time = (
            sum(self._queue_times) / len(self._queue_times)
            if self._queue_times
            else 0
        )
        
        return {
            "name": self.name,
            "running": self._running,
            "workers": {
                "active": len([w for w in self._workers if not w.done()]),
                "max": self.max_workers
            },
            "queue_sizes": queue_sizes,
            "total_queued": sum(queue_sizes.values()),
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._processed_count),
            "avg_duration_ms": avg_duration,
            "avg_queue_time_ms": avg_queue_time
        }


class StreamingProcessor:
    """
    Processor for streaming data with validation and preprocessing
    """
    
    def __init__(
        self,
        name: str,
        input_stream: Stream,
        validator: Optional[Validator] = None,
        preprocessor: Optional[Pipeline] = None,
        output_stream: Optional[Stream] = None
    ):
        self.name = name
        self.input_stream = input_stream
        self.validator = validator
        self.preprocessor = preprocessor
        self.output_stream = output_stream or Stream(name=f"{name}-output")
        
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._processed_count = 0
        self._error_count = 0
        
    async def start(self):
        """Start streaming processor"""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._process_stream())
        logger.info(f"Streaming processor {self.name} started")
        
    async def stop(self):
        """Stop streaming processor"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logger.info(f"Streaming processor {self.name} stopped")
        
    async def _process_stream(self):
        """Process items from input stream"""
        async for item in self.input_stream:
            if not self._running:
                break
                
            try:
                # Validate if validator provided
                if self.validator:
                    validation_result = await self.validator.validate(item.data)
                    if not validation_result.is_valid:
                        logger.warning(f"Validation failed: {validation_result.issues}")
                        self._error_count += 1
                        continue
                        
                # Preprocess if preprocessor provided
                processed_data = item.data
                if self.preprocessor:
                    pipeline_result = await self.preprocessor.process(item.data)
                    processed_data = pipeline_result.data
                    
                # Emit to output stream
                await self.output_stream.emit(processed_data, item.metadata)
                self._processed_count += 1
                
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                self._error_count += 1
                
    @property
    def metrics(self) -> dict[str, Any]:
        """Get processor metrics"""
        return {
            "name": self.name,
            "running": self._running,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._processed_count),
            "input_stream": self.input_stream.metrics,
            "output_stream": self.output_stream.metrics
        }


class RealTimeOrchestrator:
    """
    Orchestrate multiple real-time processors
    """
    
    def __init__(self, name: str = "orchestrator"):
        self.name = name
        self._processors: Dict[str, RealTimeProcessor] = {}
        self._streaming_processors: Dict[str, StreamingProcessor] = {}
        self._running = False
        
    def add_processor(self, processor: RealTimeProcessor):
        """Add a real-time processor"""
        self._processors[processor.name] = processor
        
    def add_streaming_processor(self, processor: StreamingProcessor):
        """Add a streaming processor"""
        self._streaming_processors[processor.name] = processor
        
    async def start(self):
        """Start all processors"""
        if self._running:
            return
            
        self._running = True
        
        # Start all processors
        tasks = []
        
        for processor in self._processors.values():
            tasks.append(processor.start())
            
        for processor in self._streaming_processors.values():
            tasks.append(processor.start())
            
        await asyncio.gather(*tasks)
        
        logger.info(f"Orchestrator {self.name} started")
        
    async def stop(self):
        """Stop all processors"""
        self._running = False
        
        # Stop all processors
        tasks = []
        
        for processor in self._processors.values():
            tasks.append(processor.stop())
            
        for processor in self._streaming_processors.values():
            tasks.append(processor.stop())
            
        await asyncio.gather(*tasks)
        
        logger.info(f"Orchestrator {self.name} stopped")
        
    async def process(self, processor_name: str, request: ProcessingRequest) -> ProcessingResult:
        """Process a request using specific processor"""
        processor = self._processors.get(processor_name)
        
        if not processor:
            return ProcessingResult(
                request_id=request.id,
                success=False,
                error=f"Processor {processor_name} not found"
            )
            
        return await processor.process(request)
        
    def get_metrics(self) -> dict[str, Any]:
        """Get metrics for all processors"""
        return {
            "name": self.name,
            "running": self._running,
            "processors": {
                name: processor.metrics
                for name, processor in self._processors.items()
            },
            "streaming_processors": {
                name: processor.metrics
                for name, processor in self._streaming_processors.items()
            }
        }