import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from app.utils.logging_config import get_logger
import functools
from collections.abc import Callable
from enum import Enum
from typing import Protocol, TypeVar
            from dataclasses import asdict

"""
Pythonic utilities and patterns for the Second Brain application.

This module demonstrates idiomatic Python usage including:
- Advanced dataclasses with rich functionality
- Sophisticated enums with behavior
- Elegant context managers
- Property descriptors and computed properties
- Functional programming patterns
"""

logger = get_logger(__name__)

T = TypeVar("T")
P = TypeVar("P")

# ============================================================================
# Enhanced Enums with Behavior
# ============================================================================

@unique
class Priority(Enum):
    """Priority levels with computed behavior."""

    LOW = (1, "Low", "🟢")
    MEDIUM = (2, "Medium", "🟡")
    HIGH = (3, "High", "🟠")
    CRITICAL = (4, "Critical", "🔴")

    def __init__(self, value: int, display_name: str, emoji: str):
        self.level = value
        self.display_name = display_name
        self.emoji = emoji

    def __lt__(self, other: "Priority") -> bool:
        """Enable priority comparison."""
        if isinstance(other, Priority):
            return self.level < other.level
        return NotImplemented

    def __str__(self) -> str:
        return f"{self.emoji} {self.display_name}"

    @classmethod
    def from_score(cls, score: float) -> "Priority":
        """Convert numeric score to priority level."""
        if score >= 0.9:
            return cls.CRITICAL
        elif score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        else:
            return cls.LOW

    @property
    def is_urgent(self) -> bool:
        """Check if priority requires immediate attention."""
        return self.level >= Priority.HIGH.level

class ProcessingStatus(Enum):
    """Processing status with transition logic."""

    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

    def can_transition_to(self, target: "ProcessingStatus") -> bool:
        """Check if transition to target status is valid."""
        valid_transitions = {
            self.PENDING: {self.PROCESSING, self.CANCELLED},
            self.PROCESSING: {self.COMPLETED, self.FAILED, self.CANCELLED},
            self.COMPLETED: set(),  # Terminal state
            self.FAILED: {self.PENDING},  # Can retry
            self.CANCELLED: {self.PENDING},  # Can restart
        }
        return target in valid_transitions.get(self, set())

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal status."""
        return self in {self.COMPLETED, self.FAILED}

    @property
    def is_active(self) -> bool:
        """Check if processing is currently active."""
        return self == self.PROCESSING

# ============================================================================
# Rich Dataclasses with Advanced Features
# ============================================================================

@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    """Immutable metric snapshot with computed properties."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Class-level cache for computed properties
    _property_cache: ClassVar[WeakKeyDictionary] = WeakKeyDictionary()

    def __post_init__(self):
        """Post-init validation and setup."""
        if self.value < 0:
            raise ValueError(f"Metric value cannot be negative: {self.value}")

        # Initialize cache for this instance
        MetricSnapshot._property_cache[self] = {}

    @property
    def age_seconds(self) -> float:
        """Calculate age of metric in seconds."""
        cache_key = "age_seconds"
        cache = MetricSnapshot._property_cache.get(self, {})

        if cache_key not in cache:
            cache[cache_key] = time.time() - self.timestamp

        return cache[cache_key]

    @property
    def is_stale(self) -> bool:
        """Check if metric is stale (older than 5 minutes)."""
        return self.age_seconds > 300

    @property
    def priority(self) -> Priority:
        """Determine priority based on value thresholds."""
        return Priority.from_score(self.value)

    def with_tag(self, key: str, value: str) -> "MetricSnapshot":
        """Return new instance with additional tag."""
        new_tags = {**self.tags, key: value}
        return MetricSnapshot(
            name=self.name,
            value=self.value,
            timestamp=self.timestamp,
            tags=new_tags,
            metadata=self.metadata,
        )

    def normalize(self, min_val: float = 0.0, max_val: float = 1.0) -> "MetricSnapshot":
        """Return normalized version of metric."""
        if max_val <= min_val:
            raise ValueError("max_val must be greater than min_val")

        normalized_value = (self.value - min_val) / (max_val - min_val)
        normalized_value = max(0.0, min(1.0, normalized_value))  # Clamp to [0, 1]

        return MetricSnapshot(
            name=f"{self.name}_normalized",
            value=normalized_value,
            timestamp=self.timestamp,
            tags=self.tags,
            metadata={**self.metadata, "normalization": {"min": min_val, "max": max_val}},
        )

@dataclass
class ProcessingTask:
    """Task with lifecycle management and state tracking."""

    id: str
    name: str
    priority: Priority = Priority.MEDIUM
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: float = field(default_factory=time.time)

    # Computed fields
    attempts: int = field(default=0, init=False)
    last_error: str | None = field(default=None, init=False)
    completed_at: float | None = field(default=None, init=False)

    # Metadata
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def transition_to(self, new_status: ProcessingStatus) -> bool:
        """Transition to new status with validation."""
        if not self.status.can_transition_to(new_status):
            logger.warning(
                f"Invalid status transition: {self.status} -> {new_status}",
                extra={"task_id": self.id, "task_name": self.name},
            )
            return False

        old_status = self.status
        self.status = new_status

        # Handle status-specific logic
        if new_status == ProcessingStatus.PROCESSING:
            self.attempts += 1
        elif new_status == ProcessingStatus.COMPLETED:
            self.completed_at = time.time()
        elif new_status == ProcessingStatus.FAILED:
            # Increment attempts, but don't reset completed_at
            pass

        logger.info(
            f"Task status changed: {old_status} -> {new_status}",
            extra={"task_id": self.id, "task_name": self.name, "attempts": self.attempts},
        )
        return True

    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error details."""
        self.last_error = error_message
        self.transition_to(ProcessingStatus.FAILED)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate task duration if completed."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status == ProcessingStatus.FAILED
            and self.attempts < 3
            and self.status.can_transition_to(ProcessingStatus.PENDING)
        )

    def __lt__(self, other: "ProcessingTask") -> bool:
        """Enable priority-based sorting."""
        if not isinstance(other, ProcessingTask):
            return NotImplemented
        return self.priority > other.priority  # Higher priority = lower sort order

# ============================================================================
# Validation Descriptors
# ============================================================================

class ValidatedField(Generic[T]):
    """Descriptor for field validation with type safety."""

    def __init__(
        self,
        validator: Callable[[T], bool],
        error_message: str,
        default: T | None = None,
        transform: Callable[[T], T] | None = None,
    ):
        self.validator = validator
        self.error_message = error_message
        self.default = default
        self.transform = transform
        self.name = None
        self.private_name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None) -> T:
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj, value: T) -> None:
        # Apply transformation if provided
        if self.transform:
            value = self.transform(value)

        # Validate the value
        if not self.validator(value):
            raise ValueError(f"{self.error_message}: {value}")

        setattr(obj, self.private_name, value)

class PositiveFloat(ValidatedField[float]):
    """Descriptor for positive float values."""

    def __init__(self, default: float = 0.0):
        super().__init__(
            validator=lambda x: isinstance(x, int | float) and x >= 0,
            error_message="Value must be a positive number",
            default=default,
            transform=float,
        )

class NonEmptyString(ValidatedField[str]):
    """Descriptor for non-empty string values."""

    def __init__(self, default: str = "", strip: bool = True):
        transform_func = str.strip if strip else str
        super().__init__(
            validator=lambda x: isinstance(x, str) and len(x.strip()) > 0,
            error_message="Value must be a non-empty string",
            default=default,
            transform=transform_func,
        )

# ============================================================================
# Protocol Definitions for Duck Typing
# ============================================================================

@runtime_checkable
class Processable(Protocol):
    """Protocol for objects that can be processed."""

    def process(self) -> Any:
        """Process the object and return result."""
        ...

    @property
    def processing_priority(self) -> Priority:
        """Get processing priority."""
        ...

@runtime_checkable
class Cacheable(Protocol):
    """Protocol for cacheable objects."""

    @property
    def cache_key(self) -> str:
        """Generate cache key for this object."""
        ...

    @property
    def cache_ttl(self) -> int:
        """Cache time-to-live in seconds."""
        ...

@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects."""

    def to_dict(self) -> dict[str, Any]:
        """Convert object to dictionary."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Serializable":
        """Create object from dictionary."""
        ...

class SerializableMixin:
    """Mixin providing default serialization behavior."""

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary."""
        if hasattr(self, "__dataclass_fields__"):

            return asdict(self)

        # Fallback for non-dataclass objects
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Create instance from dictionary."""
        if hasattr(cls, "__dataclass_fields__"):
            # Filter data to only include dataclass fields
            field_names = set(cls.__dataclass_fields__.keys())
            filtered_data = {k: v for k, v in data.items() if k in field_names}
            return cls(**filtered_data)

        # Fallback for non-dataclass objects
        return cls(**data)

# ============================================================================
# Functional Programming Utilities
# ============================================================================

def compose(*functions: Callable) -> Callable:
    """Compose functions right to left."""
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)

def pipe(value: T, *functions: Callable[[T], T]) -> T:
    """Pipe value through sequence of functions."""
    return functools.reduce(lambda acc, func: func(acc), functions, value)

def curry(func: Callable) -> Callable:
    """Curry a function to enable partial application."""

    @functools.wraps(func)
    def curried(*args, **kwargs):
        if len(args) + len(kwargs) >= func.__code__.co_argcount:
            return func(*args, **kwargs)
        return functools.partial(curried, *args, **kwargs)

    return curried

@curry
def filter_by_attribute(attr_name: str, predicate: Callable, items: list[Any]) -> list[Any]:
    """Filter items by attribute value using predicate."""
    return [item for item in items if predicate(getattr(item, attr_name))]

@curry
def group_by_attribute(attr_name: str, items: list[Any]) -> dict[Any, list[Any]]:
    """Group items by attribute value."""
    sorted_items = sorted(items, key=attrgetter(attr_name))
    return {key: list(group) for key, group in groupby(sorted_items, key=attrgetter(attr_name))}

def chunk_iterator(iterable: Iterator[T], chunk_size: int) -> Iterator[list[T]]:
    """Split iterator into chunks of specified size."""
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, chunk_size))
        if not chunk:
            break
        yield chunk

def flatten(nested_iterable: Iterator[Iterator[T]]) -> Iterator[T]:
    """Flatten nested iterables."""
    return chain.from_iterable(nested_iterable)

# ============================================================================
# Advanced Iterator Patterns
# ============================================================================

class BatchProcessor(Generic[T]):
    """Process items in batches with configurable behavior."""

    def __init__(
        self, batch_size: int = 100, processor: Callable[[list[T]], list[T]] | None = None
    ):
        self.batch_size = batch_size
        self.processor = processor or (lambda x: x)

    def process(self, items: Iterator[T]) -> Iterator[T]:
        """Process items in batches."""
        for batch in chunk_iterator(items, self.batch_size):
            processed_batch = self.processor(batch)
            yield from processed_batch

    async def process_async(self, items: AsyncIterator[T]) -> AsyncIterator[T]:
        """Process items in batches asynchronously."""
        batch = []
        async for item in items:
            batch.append(item)

            if len(batch) >= self.batch_size:
                if asyncio.iscoroutinefunction(self.processor):
                    processed_batch = await self.processor(batch)
                else:
                    processed_batch = self.processor(batch)

                for processed_item in processed_batch:
                    yield processed_item

                batch = []

        # Process remaining items
        if batch:
            if asyncio.iscoroutinefunction(self.processor):
                processed_batch = await self.processor(batch)
            else:
                processed_batch = self.processor(batch)

            for processed_item in processed_batch:
                yield processed_item

class SlidingWindow(Generic[T]):
    """Sliding window iterator for time series analysis."""

    def __init__(self, window_size: int, step_size: int = 1):
        if window_size <= 0:
            raise ValueError("Window size must be positive")
        if step_size <= 0:
            raise ValueError("Step size must be positive")

        self.window_size = window_size
        self.step_size = step_size

    def __call__(self, iterable: Iterator[T]) -> Iterator[list[T]]:
        """Create sliding windows from iterable."""
        items = list(iterable)

        for i in range(0, len(items) - self.window_size + 1, self.step_size):
            yield items[i : i + self.window_size]

# ============================================================================
# Named Tuple Extensions
# ============================================================================

class Coordinate(NamedTuple):
    """2D coordinate with computed properties."""

    x: float
    y: float

    @property
    def magnitude(self) -> float:
        """Calculate distance from origin."""
        return (self.x**2 + self.y**2) ** 0.5

    def distance_to(self, other: "Coordinate") -> float:
        """Calculate distance to another coordinate."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __add__(self, other: "Coordinate") -> "Coordinate":
        """Add coordinates."""
        return Coordinate(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Coordinate":
        """Multiply by scalar."""
        return Coordinate(self.x * scalar, self.y * scalar)

class Range(NamedTuple):
    """Range with validation and operations."""

    start: float
    end: float

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"Start ({self.start}) cannot be greater than end ({self.end})")

    @property
    def size(self) -> float:
        """Calculate range size."""
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        """Calculate range midpoint."""
        return (self.start + self.end) / 2

    def contains(self, value: float) -> bool:
        """Check if value is in range."""
        return self.start <= value <= self.end

    def overlaps(self, other: "Range") -> bool:
        """Check if ranges overlap."""
        return self.start <= other.end and other.start <= self.end

    def intersection(self, other: "Range") -> Optional["Range"]:
        """Calculate intersection with another range."""
        if not self.overlaps(other):
            return None

        return Range(start=max(self.start, other.start), end=min(self.end, other.end))

# ============================================================================
# Examples of Usage
# ============================================================================

def demonstration_usage():
    """Demonstrate the pythonic patterns."""

    # Enhanced enums with behavior
    priority = Priority.from_score(0.85)
    assert priority == Priority.HIGH
    assert priority.is_urgent

    # Rich dataclasses
    task = ProcessingTask(id="task_001", name="Process Memories", priority=Priority.HIGH)

    assert task.transition_to(ProcessingStatus.PROCESSING)
    assert not task.transition_to(ProcessingStatus.COMPLETED)  # Invalid transition

    # Validated fields
    class Configuration:
        timeout = PositiveFloat(default=30.0)
        api_key = NonEmptyString(default="")

    config = Configuration()
    config.timeout = 45.0  # Valid
    # config.timeout = -1.0  # Would raise ValueError

    # Functional programming
    numbers = [1, 2, 3, 4, 5]
    result = pipe(
        numbers,
        lambda x: [n * 2 for n in x],  # Double
        lambda x: [n for n in x if n > 5],  # Filter > 5
        sum,  # Sum remaining
    )
    assert result == 18  # (6 + 8 + 10)

    # Protocol usage
    class ProcessableTask:
        def __init__(self, data: str):
            self.data = data

        def process(self) -> str:
            return self.data.upper()

        @property
        def processing_priority(self) -> Priority:
            return Priority.MEDIUM

    # This works due to duck typing and protocols
    def process_item(item: Processable) -> Any:
        return item.process()

    task = ProcessableTask("hello")
    assert isinstance(task, Processable)  # Runtime check
    assert process_item(task) == "HELLO"

    print("All pythonic patterns demonstrated successfully!")

if __name__ == "__main__":
    demonstration_usage()
