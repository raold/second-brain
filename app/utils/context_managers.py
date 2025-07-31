"""
Sophisticated context managers for resource management in the Second Brain application.

This module provides elegant context managers that simplify complexity
and handle resource lifecycle management with proper error handling
and cleanup semantics.
"""

import asyncio
import contextlib
from app.utils.logging_config import get_logger
logger = get_logger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# ============================================================================
# Resource Management Context Managers
# ============================================================================

class ResourceState(Enum):
    """States for managed resources."""
    UNINITIALIZED = "uninitialized"
    ACQUIRING = "acquiring"
    ACTIVE = "active"
    RELEASING = "releasing"
    RELEASED = "released"
    ERROR = "error"


@dataclass
class ResourceMetrics:
    """Metrics for resource usage tracking."""
    acquisition_time: float = 0.0
    usage_duration: float = 0.0
    release_time: float = 0.0
    error_count: int = 0
    total_uses: int = 0
    peak_concurrent_uses: int = 0


class ManagedResource(ABC, Generic[T]):
    """Abstract base for managed resources with lifecycle tracking."""

    def __init__(self, resource_id: str, max_retries: int = 3):
        self.resource_id = resource_id
        self.max_retries = max_retries
        self.state = ResourceState.UNINITIALIZED
        self.metrics = ResourceMetrics()
        self._resource: Optional[T] = None
        self._acquisition_start: Optional[float] = None
        self._usage_start: Optional[float] = None
        self._error_history: list[Exception] = []

    @abstractmethod
    async def _acquire_resource(self) -> T:
        """Acquire the actual resource."""
        pass

    @abstractmethod
    async def _release_resource(self, resource: T) -> None:
        """Release the actual resource."""
        pass

    async def acquire(self) -> T:
        """Acquire resource with retry logic and metrics."""
        if self.state != ResourceState.UNINITIALIZED:
            raise RuntimeError(f"Resource {self.resource_id} is already acquired or in use")

        self.state = ResourceState.ACQUIRING
        self._acquisition_start = time.perf_counter()

        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._resource = await self._acquire_resource()

                # Update metrics
                self.metrics.acquisition_time = time.perf_counter() - self._acquisition_start
                self.metrics.total_uses += 1
                self._usage_start = time.perf_counter()

                self.state = ResourceState.ACTIVE
                logger.debug(f"Resource {self.resource_id} acquired in {self.metrics.acquisition_time:.4f}s")
                return self._resource

            except Exception as e:
                last_error = e
                self._error_history.append(e)
                self.metrics.error_count += 1

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Failed to acquire resource {self.resource_id} (attempt {attempt + 1}): {e}. Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to acquire resource {self.resource_id} after {self.max_retries} attempts: {e}")

        self.state = ResourceState.ERROR
        raise RuntimeError(f"Failed to acquire resource {self.resource_id}") from last_error

    async def release(self) -> None:
        """Release resource with proper cleanup and metrics."""
        if self.state != ResourceState.ACTIVE or not self._resource:
            logger.warning(f"Attempting to release resource {self.resource_id} in state {self.state}")
            return

        self.state = ResourceState.RELEASING
        release_start = time.perf_counter()

        try:
            # Update usage duration
            if self._usage_start:
                self.metrics.usage_duration = time.perf_counter() - self._usage_start

            await self._release_resource(self._resource)
            self.metrics.release_time = time.perf_counter() - release_start

            logger.debug(f"Resource {self.resource_id} released in {self.metrics.release_time:.4f}s")

        except Exception as e:
            self.metrics.error_count += 1
            self._error_history.append(e)
            logger.error(f"Error releasing resource {self.resource_id}: {e}")
            self.state = ResourceState.ERROR
            raise
        finally:
            self._resource = None
            self.state = ResourceState.RELEASED

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive resource metrics."""
        return {
            'resource_id': self.resource_id,
            'state': self.state.value,
            'metrics': {
                'acquisition_time': self.metrics.acquisition_time,
                'usage_duration': self.metrics.usage_duration,
                'release_time': self.metrics.release_time,
                'error_count': self.metrics.error_count,
                'total_uses': self.metrics.total_uses,
                'peak_concurrent_uses': self.metrics.peak_concurrent_uses
            },
            'recent_errors': [str(e) for e in self._error_history[-5:]]  # Last 5 errors
        }


@contextlib.asynccontextmanager
async def managed_resource(resource: ManagedResource[T]) -> AsyncGenerator[T, None]:
    """Context manager for automatic resource lifecycle management."""
    acquired_resource = None
    try:
        acquired_resource = await resource.acquire()
        yield acquired_resource
    finally:
        if acquired_resource:
            try:
                await resource.release()
            except Exception as e:
                logger.error(f"Error in resource cleanup: {e}")


# ============================================================================
# Database Connection Context Managers
# ============================================================================

class DatabaseTransaction:
    """Context manager for database transactions with sophisticated error handling."""

    def __init__(self, connection, isolation_level: str = "READ_COMMITTED", timeout: Optional[float] = None):
        self.connection = connection
        self.isolation_level = isolation_level
        self.timeout = timeout
        self.transaction = None
        self.start_time = None
        self.savepoints = []
        self.operations_count = 0

    async def __aenter__(self):
        self.start_time = time.perf_counter()

        try:
            # Set isolation level if specified
            if self.isolation_level != "READ_COMMITTED":
                await self.connection.execute(f"SET TRANSACTION ISOLATION LEVEL {self.isolation_level}")

            # Start transaction with timeout if specified
            if self.timeout:
                await self.connection.execute(f"SET statement_timeout = {int(self.timeout * 1000)}")

            self.transaction = self.connection.transaction()
            await self.transaction.start()

            logger.debug(f"Transaction started with isolation level {self.isolation_level}")
            return self

        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time

        try:
            if exc_type is None:
                # Commit on success
                await self.transaction.commit()
                logger.debug(f"Transaction committed successfully after {duration:.4f}s ({self.operations_count} operations)")
            else:
                # Rollback on exception
                await self.transaction.rollback()
                logger.warning(f"Transaction rolled back after {duration:.4f}s due to: {exc_val}")

        except Exception as cleanup_error:
            logger.error(f"Error during transaction cleanup: {cleanup_error}")
            # Don't suppress the original exception

        finally:
            # Reset timeout
            if self.timeout:
                try:
                    await self.connection.execute("SET statement_timeout = 0")
                except Exception as e:
                    logger.warning(f"Failed to reset statement timeout: {e}")

    async def savepoint(self, name: str) -> None:
        """Create a savepoint within the transaction."""
        await self.connection.execute(f"SAVEPOINT {name}")
        self.savepoints.append(name)
        logger.debug(f"Savepoint '{name}' created")

    async def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a specific savepoint."""
        await self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        # Remove savepoints created after this one
        while self.savepoints and self.savepoints[-1] != name:
            self.savepoints.pop()
        logger.debug(f"Rolled back to savepoint '{name}'")

    async def release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        await self.connection.execute(f"RELEASE SAVEPOINT {name}")
        if name in self.savepoints:
            self.savepoints.remove(name)
        logger.debug(f"Savepoint '{name}' released")

    def track_operation(self) -> None:
        """Track that an operation was performed in this transaction."""
        self.operations_count += 1


@contextlib.asynccontextmanager
async def database_transaction(
    connection,
    isolation_level: str = "READ_COMMITTED",
    timeout: Optional[float] = None,
    max_retries: int = 3
) -> AsyncGenerator[DatabaseTransaction, None]:
    """Enhanced database transaction context manager with retry logic."""

    last_error = None
    for attempt in range(max_retries):
        try:
            async with DatabaseTransaction(connection, isolation_level, timeout) as tx:
                yield tx
                return  # Success, exit retry loop

        except Exception as e:
            last_error = e

            # Check if error is retryable
            error_str = str(e).lower()
            if any(retryable in error_str for retryable in ['deadlock', 'serialization', 'conflict']):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1  # Short exponential backoff
                    logger.warning(f"Retryable transaction error (attempt {attempt + 1}): {e}. Retrying in {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue

            # Non-retryable error or max retries reached
            logger.error(f"Transaction failed after {attempt + 1} attempts: {e}")
            raise

    raise RuntimeError("Transaction failed after all retry attempts") from last_error


# ============================================================================
# Processing Context Managers
# ============================================================================

@dataclass
class ProcessingContext:
    """Context for processing operations with progress tracking."""
    operation_id: str
    operation_name: str
    priority: Priority = Priority.MEDIUM
    timeout: Optional[float] = None
    progress_callback: Optional[callable] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Runtime state
    start_time: Optional[float] = field(default=None, init=False)
    current_step: str = field(default="", init=False)
    progress_percent: float = field(default=0.0, init=False)
    steps_completed: int = field(default=0, init=False)
    total_steps: Optional[int] = field(default=None, init=False)


class ProcessingManager(Observable):
    """Manager for processing operations with observable progress."""

    def __init__(self):
        super().__init__()
        self.active_operations: dict[str, ProcessingContext] = {}
        self.operation_history: list[ProcessingContext] = []
        self.max_concurrent = 10
        self._lock = asyncio.Lock()

    async def start_operation(self, context: ProcessingContext) -> None:
        """Start a processing operation."""
        async with self._lock:
            if len(self.active_operations) >= self.max_concurrent:
                raise RuntimeError(f"Maximum concurrent operations ({self.max_concurrent}) exceeded")

            context.start_time = time.perf_counter()
            self.active_operations[context.operation_id] = context

            # Notify observers
            await self.notify_observers(ChangeNotification(
                change_type=ChangeType.CREATED,
                entity_id=context.operation_id,
                entity_type="processing_operation",
                new_value=context,
                metadata={'operation_name': context.operation_name, 'priority': context.priority.name}
            ))

            logger.info(f"Started operation '{context.operation_name}' ({context.operation_id})")

    async def update_progress(self, operation_id: str, step: str, progress: float) -> None:
        """Update operation progress."""
        context = self.active_operations.get(operation_id)
        if not context:
            return

        context.current_step = step
        context.progress_percent = min(100.0, max(0.0, progress))

        if context.progress_callback:
            try:
                if asyncio.iscoroutinefunction(context.progress_callback):
                    await context.progress_callback(context)
                else:
                    context.progress_callback(context)
            except Exception as e:
                logger.warning(f"Progress callback failed for operation {operation_id}: {e}")

        # Notify observers
        await self.notify_observers(ChangeNotification(
            change_type=ChangeType.UPDATED,
            entity_id=operation_id,
            entity_type="processing_operation",
            new_value=context,
            metadata={'step': step, 'progress': progress}
        ))

    async def complete_operation(self, operation_id: str, result: Any = None) -> None:
        """Complete a processing operation."""
        async with self._lock:
            context = self.active_operations.pop(operation_id, None)
            if not context:
                return

            duration = time.perf_counter() - context.start_time if context.start_time else 0
            context.metadata['duration'] = duration
            context.metadata['result'] = result

            self.operation_history.append(context)

            # Keep only last 100 operations in history
            if len(self.operation_history) > 100:
                self.operation_history = self.operation_history[-100:]

            # Notify observers
            await self.notify_observers(ChangeNotification(
                change_type=ChangeType.UPDATED,
                entity_id=operation_id,
                entity_type="processing_operation",
                old_value=context,
                new_value=None,
                metadata={'completed': True, 'duration': duration}
            ))

            logger.info(f"Completed operation '{context.operation_name}' ({operation_id}) in {duration:.4f}s")

    def get_active_operations(self) -> dict[str, ProcessingContext]:
        """Get currently active operations."""
        return self.active_operations.copy()

    def get_operation_stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        active_count = len(self.active_operations)
        total_completed = len(self.operation_history)

        if self.operation_history:
            avg_duration = sum(op.metadata.get('duration', 0) for op in self.operation_history) / total_completed
            priority_counts = {}
            for op in self.operation_history:
                priority = op.priority.name
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
        else:
            avg_duration = 0
            priority_counts = {}

        return {
            'active_operations': active_count,
            'completed_operations': total_completed,
            'max_concurrent': self.max_concurrent,
            'average_duration': avg_duration,
            'priority_distribution': priority_counts
        }


@contextlib.asynccontextmanager
async def processing_operation(
    manager: ProcessingManager,
    operation_name: str,
    priority: Priority = Priority.MEDIUM,
    timeout: Optional[float] = None,
    progress_callback: Optional[callable] = None,
    **metadata
) -> AsyncGenerator[ProcessingContext, None]:
    """Context manager for processing operations with automatic lifecycle management."""

    import uuid
    operation_id = str(uuid.uuid4())

    context = ProcessingContext(
        operation_id=operation_id,
        operation_name=operation_name,
        priority=priority,
        timeout=timeout,
        progress_callback=progress_callback,
        metadata=metadata
    )

    try:
        await manager.start_operation(context)

        # Set up timeout if specified
        if timeout:
            try:
                async with asyncio.timeout(timeout):
                    yield context
            except asyncio.TimeoutError:
                logger.error(f"Operation '{operation_name}' ({operation_id}) timed out after {timeout}s")
                raise
        else:
            yield context

        await manager.complete_operation(operation_id, result="success")

    except Exception as e:
        logger.error(f"Operation '{operation_name}' ({operation_id}) failed: {e}")
        await manager.complete_operation(operation_id, result=f"error: {e}")
        raise


# ============================================================================
# File and Path Context Managers
# ============================================================================

@contextlib.contextmanager
def atomic_file_write(
    file_path: Union[str, Path],
    mode: str = 'w',
    encoding: str = 'utf-8',
    backup: bool = True,
    temp_suffix: str = '.tmp'
) -> Generator[Any, None, None]:
    """Context manager for atomic file writes with backup and rollback."""

    file_path = Path(file_path)
    temp_path = file_path.with_suffix(file_path.suffix + temp_suffix)
    backup_path = file_path.with_suffix(file_path.suffix + '.backup') if backup else None

    # Create backup if requested and file exists
    if backup and file_path.exists():
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")

    try:
        # Write to temporary file
        with open(temp_path, mode, encoding=encoding) as f:
            yield f

        # Atomic move to final location
        temp_path.replace(file_path)
        logger.debug(f"Atomically wrote file: {file_path}")

        # Clean up backup on success
        if backup_path and backup_path.exists():
            try:
                backup_path.unlink()
                logger.debug(f"Removed backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to remove backup {backup_path}: {e}")

    except Exception as e:
        logger.error(f"Atomic file write failed for {file_path}: {e}")

        # Clean up temporary file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_path}: {cleanup_error}")

        # Restore from backup if available
        if backup_path and backup_path.exists():
            try:
                backup_path.replace(file_path)
                logger.info(f"Restored from backup: {file_path}")
            except Exception as restore_error:
                logger.error(f"Failed to restore from backup: {restore_error}")

        raise


@contextlib.asynccontextmanager
async def temporary_directory(
    prefix: str = 'temp_',
    cleanup: bool = True,
    base_dir: Optional[Path] = None
) -> AsyncGenerator[Path, None]:
    """Context manager for temporary directories with async cleanup."""

    import shutil
    import tempfile

    base_dir = base_dir or Path(tempfile.gettempdir())
    temp_dir = None

    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))
        logger.debug(f"Created temporary directory: {temp_dir}")
        yield temp_dir

    finally:
        if temp_dir and cleanup:
            try:
                # Async cleanup to avoid blocking
                await asyncio.get_event_loop().run_in_executor(
                    None, shutil.rmtree, temp_dir
                )
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


# ============================================================================
# Memory and Resource Monitoring Context Managers
# ============================================================================

@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage."""
    timestamp: float
    memory_mb: float
    cpu_percent: float
    open_files: int
    thread_count: int
    custom_metrics: dict[str, Any] = field(default_factory=dict)


class ResourceMonitor:
    """Monitor resource usage during operations."""

    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.snapshots: list[ResourceSnapshot] = []
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self.monitoring:
            return

        self.monitoring = True
        self.snapshots.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.debug("Started resource monitoring")

    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.debug(f"Stopped resource monitoring. Collected {len(self.snapshots)} samples")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        import psutil
        process = psutil.Process()

        try:
            while self.monitoring:
                snapshot = ResourceSnapshot(
                    timestamp=time.time(),
                    memory_mb=process.memory_info().rss / 1024 / 1024,
                    cpu_percent=process.cpu_percent(),
                    open_files=len(process.open_files()),
                    thread_count=process.num_threads()
                )

                self.snapshots.append(snapshot)

                # Keep only last 1000 samples
                if len(self.snapshots) > 1000:
                    self.snapshots = self.snapshots[-1000:]

                await asyncio.sleep(self.sample_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Resource monitoring error: {e}")

    def get_summary(self) -> dict[str, Any]:
        """Get resource usage summary."""
        if not self.snapshots:
            return {'error': 'No monitoring data available'}

        memory_values = [s.memory_mb for s in self.snapshots]
        cpu_values = [s.cpu_percent for s in self.snapshots]

        return {
            'duration_seconds': self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            'samples_collected': len(self.snapshots),
            'memory': {
                'peak_mb': max(memory_values),
                'average_mb': sum(memory_values) / len(memory_values),
                'final_mb': memory_values[-1]
            },
            'cpu': {
                'peak_percent': max(cpu_values),
                'average_percent': sum(cpu_values) / len(cpu_values),
            },
            'files': {
                'peak_open': max(s.open_files for s in self.snapshots),
                'final_open': self.snapshots[-1].open_files
            },
            'threads': {
                'peak_count': max(s.thread_count for s in self.snapshots),
                'final_count': self.snapshots[-1].thread_count
            }
        }


@contextlib.asynccontextmanager
async def resource_monitoring(
    sample_interval: float = 1.0,
    log_summary: bool = True
) -> AsyncGenerator[ResourceMonitor, None]:
    """Context manager for resource monitoring during operations."""

    monitor = ResourceMonitor(sample_interval)

    try:
        await monitor.start_monitoring()
        yield monitor
    finally:
        await monitor.stop_monitoring()

        if log_summary:
            summary = monitor.get_summary()
            if 'error' not in summary:
                logger.info(f"Resource usage summary: "
                          f"Peak memory: {summary['memory']['peak_mb']:.1f}MB, "
                          f"Avg CPU: {summary['cpu']['average_percent']:.1f}%, "
                          f"Duration: {summary['duration_seconds']:.1f}s")


# ============================================================================
# Composable Context Manager Utilities
# ============================================================================

@contextlib.asynccontextmanager
async def combine_contexts(*context_managers) -> AsyncGenerator[tuple, None]:
    """Combine multiple async context managers into one."""

    async with contextlib.AsyncExitStack() as stack:
        results = []
        for cm in context_managers:
            result = await stack.enter_async_context(cm)
            results.append(result)
        yield tuple(results)


class ContextManagerChain:
    """Builder for chaining context managers with error handling."""

    def __init__(self):
        self.contexts = []
        self.error_handlers = {}

    def add(self, context_manager, error_handler=None):
        """Add a context manager to the chain."""
        self.contexts.append(context_manager)
        if error_handler:
            self.error_handlers[len(self.contexts) - 1] = error_handler
        return self

    @contextlib.asynccontextmanager
    async def execute(self):
        """Execute the chain of context managers."""
        async with contextlib.AsyncExitStack() as stack:
            results = []

            for i, cm in enumerate(self.contexts):
                try:
                    result = await stack.enter_async_context(cm)
                    results.append(result)
                except Exception as e:
                    if i in self.error_handlers:
                        try:
                            await self.error_handlers[i](e)
                        except Exception as handler_error:
                            logger.error(f"Error handler failed: {handler_error}")
                    raise

            yield tuple(results)


# ============================================================================
# Example Usage and Testing
# ============================================================================

if __name__ == "__main__":
    # Example usage of the context managers

    async def example_usage():
        """Demonstrate context manager usage."""

        # Resource monitoring
        async with resource_monitoring(sample_interval=0.5) as monitor:
            # Simulate some work
            await asyncio.sleep(2)

            # Get real-time summary
            summary = monitor.get_summary()
            print(f"Current memory usage: {summary['memory']['final_mb']:.1f}MB")

        # Processing operation with progress
        manager = ProcessingManager()

        async def progress_callback(context):
            print(f"Progress: {context.progress_percent:.1f}% - {context.current_step}")

        async with processing_operation(
            manager,
            "Data Processing Task",
            priority=Priority.HIGH,
            timeout=10.0,
            progress_callback=progress_callback
        ) as operation:
            # Simulate processing steps
            await manager.update_progress(operation.operation_id, "Loading data", 25.0)
            await asyncio.sleep(0.5)

            await manager.update_progress(operation.operation_id, "Processing", 50.0)
            await asyncio.sleep(0.5)

            await manager.update_progress(operation.operation_id, "Saving results", 100.0)

        # File operations
        test_file = Path("test_atomic.txt")
        try:
            with atomic_file_write(test_file, backup=True) as f:
                f.write("This is a test of atomic file writing.\n")
                f.write("If this fails, the original file is preserved.\n")

            print(f"Successfully wrote to {test_file}")

            # Clean up
            test_file.unlink()

        except Exception as e:
            print(f"File operation failed: {e}")

        # Temporary directory
        async with temporary_directory(prefix="example_") as temp_dir:
            test_path = temp_dir / "example.txt"
            test_path.write_text("Temporary file content")
            print(f"Created temporary file: {test_path}")
            # Directory will be automatically cleaned up

        # Context manager chaining
        chain = ContextManagerChain()
        chain.add(resource_monitoring(0.1))
        chain.add(temporary_directory("chained_"))

        async with chain.execute() as (monitor, temp_dir):
            # Use both contexts
            await asyncio.sleep(1)
            summary = monitor.get_summary()
            temp_file = temp_dir / "chain_test.txt"
            temp_file.write_text("Chained context managers work!")
            print("Chained execution successful")

        print("All context manager examples completed successfully!")

    # Run the example
    asyncio.run(example_usage())
