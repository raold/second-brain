"""
Base streaming architecture for real-time data processing
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional, TypeVar, Generic
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class StreamState(str, Enum):
    """States of a stream processor"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BackpressureStrategy(str, Enum):
    """Strategies for handling backpressure"""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BUFFER = "buffer"
    BLOCK = "block"
    SAMPLE = "sample"


@dataclass
class StreamMetadata:
    """Metadata for stream items"""
    stream_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence_number: int = 0
    source: Optional[str] = None
    correlation_id: Optional[UUID] = None
    headers: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamItem(Generic[T]):
    """Container for items in a stream"""
    data: T
    metadata: StreamMetadata = field(default_factory=StreamMetadata)
    
    def with_metadata(self, **kwargs) -> 'StreamItem[T]':
        """Create a new item with updated metadata"""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
            else:
                self.metadata.headers[key] = value
        return self


class StreamProcessor(ABC, Generic[T, R]):
    """Abstract base class for stream processors"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.state = StreamState.IDLE
        self._error: Optional[Exception] = None
        self._processed_count = 0
        self._error_count = 0
        
    @abstractmethod
    async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        """Process a single stream item"""
        pass
    
    async def __call__(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
        """Make processor callable"""
        try:
            self._processed_count += 1
            return await self.process(item)
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in processor {self.name}: {e}")
            raise
    
    @property
    def metrics(self) -> dict[str, Any]:
        """Get processor metrics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._processed_count)
        }


class Stream(Generic[T]):
    """
    Async stream implementation with backpressure and error handling
    """
    
    def __init__(
        self,
        name: str = None,
        buffer_size: int = 1000,
        backpressure_strategy: BackpressureStrategy = BackpressureStrategy.BUFFER
    ):
        self.name = name or f"stream-{uuid4().hex[:8]}"
        self.buffer_size = buffer_size
        self.backpressure_strategy = backpressure_strategy
        
        self._queue: asyncio.Queue[StreamItem[T]] = asyncio.Queue(maxsize=buffer_size)
        self._subscribers: list[Callable[[StreamItem[T]], Any]] = []
        self._processors: list[StreamProcessor] = []
        self._running = False
        self._sequence_number = 0
        
    async def emit(self, data: T, metadata: Optional[StreamMetadata] = None) -> bool:
        """
        Emit data to the stream
        
        Returns:
            bool: True if item was emitted, False if dropped
        """
        if metadata is None:
            metadata = StreamMetadata(
                sequence_number=self._sequence_number,
                source=self.name
            )
        else:
            metadata.sequence_number = self._sequence_number
            
        self._sequence_number += 1
        item = StreamItem(data=data, metadata=metadata)
        
        try:
            if self.backpressure_strategy == BackpressureStrategy.BLOCK:
                await self._queue.put(item)
                return True
            elif self.backpressure_strategy == BackpressureStrategy.DROP_NEWEST:
                if self._queue.full():
                    return False
                await self._queue.put(item)
                return True
            elif self.backpressure_strategy == BackpressureStrategy.DROP_OLDEST:
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                await self._queue.put(item)
                return True
            elif self.backpressure_strategy == BackpressureStrategy.BUFFER:
                await self._queue.put(item)
                return True
            elif self.backpressure_strategy == BackpressureStrategy.SAMPLE:
                # Sample every nth item when queue is getting full
                if self._queue.qsize() > self.buffer_size * 0.8:
                    if self._sequence_number % 10 != 0:  # Keep 1 in 10
                        return False
                await self._queue.put(item)
                return True
        except asyncio.QueueFull:
            logger.warning(f"Stream {self.name} buffer full, item dropped")
            return False
            
    async def __aiter__(self) -> AsyncIterator[StreamItem[T]]:
        """Async iteration over stream items"""
        while self._running or not self._queue.empty():
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield item
            except asyncio.TimeoutError:
                continue
                
    def subscribe(self, callback: Callable[[StreamItem[T]], Any]):
        """Subscribe to stream events"""
        self._subscribers.append(callback)
        
    def unsubscribe(self, callback: Callable[[StreamItem[T]], Any]):
        """Unsubscribe from stream events"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            
    def pipe(self, processor: StreamProcessor[T, R]) -> 'Stream[R]':
        """
        Pipe stream through a processor
        
        Args:
            processor: Stream processor to apply
            
        Returns:
            New stream with processed items
        """
        output_stream = Stream[R](
            name=f"{self.name}->{processor.name}",
            buffer_size=self.buffer_size,
            backpressure_strategy=self.backpressure_strategy
        )
        
        async def process_and_forward(item: StreamItem[T]):
            try:
                processed = await processor(item)
                if processed is not None:
                    await output_stream.emit(processed.data, processed.metadata)
            except Exception as e:
                logger.error(f"Error in pipe {processor.name}: {e}")
                
        self.subscribe(process_and_forward)
        self._processors.append(processor)
        
        return output_stream
        
    def filter(self, predicate: Callable[[T], bool]) -> 'Stream[T]':
        """Filter stream items"""
        class FilterProcessor(StreamProcessor[T, T]):
            async def process(self, item: StreamItem[T]) -> Optional[StreamItem[T]]:
                if predicate(item.data):
                    return item
                return None
                
        return self.pipe(FilterProcessor(name=f"filter-{self.name}"))
        
    def map(self, transform: Callable[[T], R]) -> 'Stream[R]':
        """Transform stream items"""
        class MapProcessor(StreamProcessor[T, R]):
            async def process(self, item: StreamItem[T]) -> Optional[StreamItem[R]]:
                transformed = transform(item.data)
                return StreamItem(data=transformed, metadata=item.metadata)
                
        return self.pipe(MapProcessor(name=f"map-{self.name}"))
        
    def batch(self, size: int, timeout: float = None) -> 'Stream[list[T]]':
        """Batch stream items"""
        class BatchProcessor(StreamProcessor[T, list[T]]):
            def __init__(self, batch_size: int, batch_timeout: float = None):
                super().__init__(name=f"batch-{size}")
                self.batch_size = batch_size
                self.batch_timeout = batch_timeout
                self._buffer: list[StreamItem[T]] = []
                self._last_emit = datetime.utcnow()
                
            async def process(self, item: StreamItem[T]) -> Optional[StreamItem[list[T]]]:
                self._buffer.append(item)
                
                should_emit = len(self._buffer) >= self.batch_size
                if self.batch_timeout:
                    time_since_last = (datetime.utcnow() - self._last_emit).total_seconds()
                    should_emit = should_emit or time_since_last >= self.batch_timeout
                    
                if should_emit and self._buffer:
                    batch_data = [item.data for item in self._buffer]
                    # Use metadata from first item with batch info
                    batch_metadata = self._buffer[0].metadata
                    batch_metadata.headers['batch_size'] = len(batch_data)
                    
                    self._buffer.clear()
                    self._last_emit = datetime.utcnow()
                    
                    return StreamItem(data=batch_data, metadata=batch_metadata)
                    
                return None
                
        return self.pipe(BatchProcessor(size, timeout))
        
    def window(self, duration: float, slide: float = None) -> 'Stream[list[T]]':
        """Window stream items by time"""
        class WindowProcessor(StreamProcessor[T, list[T]]):
            def __init__(self, window_duration: float, window_slide: float = None):
                super().__init__(name=f"window-{duration}s")
                self.window_duration = window_duration
                self.window_slide = window_slide or window_duration
                self._windows: list[tuple[datetime, list[StreamItem[T]]]] = []
                
            async def process(self, item: StreamItem[T]) -> Optional[StreamItem[list[T]]]:
                now = datetime.utcnow()
                
                # Add to all active windows
                for window_start, window_items in self._windows:
                    window_items.append(item)
                    
                # Start new window if needed
                if not self._windows or (now - self._windows[-1][0]).total_seconds() >= self.window_slide:
                    self._windows.append((now, [item]))
                    
                # Check for completed windows
                completed_windows = []
                remaining_windows = []
                
                for window_start, window_items in self._windows:
                    if (now - window_start).total_seconds() >= self.window_duration:
                        completed_windows.append(window_items)
                    else:
                        remaining_windows.append((window_start, window_items))
                        
                self._windows = remaining_windows
                
                # Emit completed windows
                if completed_windows:
                    # Emit the first completed window
                    window_data = [item.data for item in completed_windows[0]]
                    window_metadata = completed_windows[0][0].metadata
                    window_metadata.headers['window_size'] = len(window_data)
                    window_metadata.headers['window_duration'] = self.window_duration
                    
                    return StreamItem(data=window_data, metadata=window_metadata)
                    
                return None
                
        return self.pipe(WindowProcessor(duration, slide))
        
    async def start(self):
        """Start the stream processing"""
        self._running = True
        logger.info(f"Stream {self.name} started")
        
    async def stop(self):
        """Stop the stream processing"""
        self._running = False
        logger.info(f"Stream {self.name} stopped")
        
    @property
    def metrics(self) -> dict[str, Any]:
        """Get stream metrics"""
        return {
            "name": self.name,
            "running": self._running,
            "queue_size": self._queue.qsize(),
            "buffer_size": self.buffer_size,
            "sequence_number": self._sequence_number,
            "subscribers": len(self._subscribers),
            "processors": [p.metrics for p in self._processors]
        }


class StreamMerger(Generic[T]):
    """Merge multiple streams into one"""
    
    def __init__(self, name: str = None):
        self.name = name or f"merger-{uuid4().hex[:8]}"
        self._input_streams: list[Stream[T]] = []
        self._output_stream = Stream[T](name=f"{self.name}-output")
        
    def add_stream(self, stream: Stream[T]):
        """Add a stream to merge"""
        self._input_streams.append(stream)
        
        async def forward_to_output(item: StreamItem[T]):
            item.metadata.headers['merged_from'] = stream.name
            await self._output_stream.emit(item.data, item.metadata)
            
        stream.subscribe(forward_to_output)
        
    @property
    def output(self) -> Stream[T]:
        """Get the merged output stream"""
        return self._output_stream


class StreamSplitter(Generic[T]):
    """Split a stream based on conditions"""
    
    def __init__(self, name: str = None):
        self.name = name or f"splitter-{uuid4().hex[:8]}"
        self._routes: dict[str, tuple[Callable[[T], bool], Stream[T]]] = {}
        
    def add_route(self, name: str, condition: Callable[[T], bool]) -> Stream[T]:
        """Add a routing condition"""
        output_stream = Stream[T](name=f"{self.name}-{name}")
        self._routes[name] = (condition, output_stream)
        return output_stream
        
    async def process(self, item: StreamItem[T]):
        """Process item and route to appropriate streams"""
        for route_name, (condition, stream) in self._routes.items():
            if condition(item.data):
                item.metadata.headers['route'] = route_name
                await stream.emit(item.data, item.metadata)