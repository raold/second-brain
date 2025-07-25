"""
Advanced protocol definitions and duck typing implementations for the Second Brain application.

This module demonstrates sophisticated use of Python's typing system for duck typing,
protocol definitions, and runtime type checking that enable flexible, maintainable code
without sacrificing type safety.
"""

import asyncio
import logging
from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
    Protocol,
    TypeVar,
    get_type_hints,
    runtime_checkable,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# Core Protocols for Second Brain Components
# ============================================================================

@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects that have a unique identifier."""

    @property
    def id(self) -> str:
        """Return unique identifier for this object."""
        ...


@runtime_checkable
class Timestamped(Protocol):
    """Protocol for objects that track creation and modification times."""

    @property
    def created_at(self) -> float:
        """Return creation timestamp."""
        ...

    @property
    def updated_at(self) -> Optional[float]:
        """Return last update timestamp."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to/from dictionaries."""

    def to_dict(self) -> dict[str, Any]:
        """Convert object to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Serializable':
        """Create object from dictionary representation."""
        ...


@runtime_checkable
class Cacheable(Protocol):
    """Protocol for objects that can be cached."""

    @property
    def cache_key(self) -> str:
        """Generate unique cache key for this object."""
        ...

    @property
    def cache_ttl(self) -> int:
        """Return cache time-to-live in seconds."""
        ...

    def is_cache_valid(self) -> bool:
        """Check if cached version is still valid."""
        ...


@runtime_checkable
class Processable(Protocol):
    """Protocol for objects that can be processed."""

    async def process(self) -> Any:
        """Process this object and return result."""
        ...

    @property
    def processing_priority(self) -> int:
        """Return processing priority (higher = more important)."""
        ...

    def can_process(self) -> bool:
        """Check if object is ready for processing."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that can validate themselves."""

    def validate(self) -> bool:
        """Validate object state and return True if valid."""
        ...

    def get_validation_errors(self) -> list[str]:
        """Return list of validation error messages."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for objects that can be configured."""

    def configure(self, **kwargs) -> None:
        """Configure object with provided parameters."""
        ...

    def get_configuration(self) -> dict[str, Any]:
        """Return current configuration."""
        ...

    def reset_configuration(self) -> None:
        """Reset to default configuration."""
        ...


@runtime_checkable
class Observable(Protocol):
    """Protocol for objects that can be observed."""

    def add_observer(self, observer: Callable[[Any], None]) -> None:
        """Add an observer to receive notifications."""
        ...

    def remove_observer(self, observer: Callable[[Any], None]) -> None:
        """Remove an observer."""
        ...

    def notify_observers(self, event: Any) -> None:
        """Notify all observers of an event."""
        ...


# ============================================================================
# Memory and Knowledge Protocols
# ============================================================================

@runtime_checkable
class MemoryLike(Protocol):
    """Protocol for memory-like objects."""

    @property
    def content(self) -> str:
        """Return memory content."""
        ...

    @property
    def memory_type(self) -> str:
        """Return memory type (semantic, episodic, procedural)."""
        ...

    @property
    def importance_score(self) -> float:
        """Return importance score between 0.0 and 1.0."""
        ...

    def get_embedding(self) -> Optional[list[float]]:
        """Return vector embedding if available."""
        ...


@runtime_checkable
class Searchable(Protocol):
    """Protocol for objects that can be searched."""

    async def search(self, query: str, limit: int = 10) -> list[Any]:
        """Search for objects matching the query."""
        ...

    def supports_filters(self) -> bool:
        """Check if advanced filtering is supported."""
        ...

    async def search_with_filters(self, query: str, filters: dict[str, Any]) -> list[Any]:
        """Search with additional filters."""
        ...


@runtime_checkable
class Embeddable(Protocol):
    """Protocol for objects that can generate embeddings."""

    async def generate_embedding(self) -> list[float]:
        """Generate vector embedding for this object."""
        ...

    def get_embedding_dimension(self) -> int:
        """Return the dimension of embeddings."""
        ...

    def supports_batch_embedding(self) -> bool:
        """Check if batch embedding generation is supported."""
        ...


@runtime_checkable
class Retrievable(Protocol[T]):
    """Protocol for objects that can retrieve other objects."""

    async def retrieve(self, query: str, context: Optional[dict[str, Any]] = None) -> list[T]:
        """Retrieve objects based on query and context."""
        ...

    async def retrieve_by_id(self, object_id: str) -> Optional[T]:
        """Retrieve object by its identifier."""
        ...

    async def retrieve_similar(self, reference: T, limit: int = 10) -> list[T]:
        """Retrieve objects similar to the reference."""
        ...


# ============================================================================
# Data Processing Protocols
# ============================================================================

@runtime_checkable
class Transformer(Protocol[T, V]):
    """Protocol for objects that transform data from one type to another."""

    async def transform(self, data: T) -> V:
        """Transform input data to output format."""
        ...

    def can_transform(self, data: T) -> bool:
        """Check if data can be transformed."""
        ...

    async def batch_transform(self, data_list: list[T]) -> list[V]:
        """Transform multiple items efficiently."""
        ...


@runtime_checkable
class Aggregator(Protocol[T]):
    """Protocol for objects that aggregate data."""

    async def aggregate(self, items: list[T]) -> dict[str, Any]:
        """Aggregate list of items into summary statistics."""
        ...

    def get_supported_metrics(self) -> list[str]:
        """Return list of supported aggregation metrics."""
        ...

    async def aggregate_by_group(self, items: list[T], group_key: str) -> dict[str, dict[str, Any]]:
        """Aggregate items grouped by specified key."""
        ...


@runtime_checkable
class Filterable(Protocol[T]):
    """Protocol for objects that can filter collections."""

    def filter(self, items: list[T], predicate: Callable[[T], bool]) -> list[T]:
        """Filter items using predicate function."""
        ...

    def filter_by_attributes(self, items: list[T], **criteria) -> list[T]:
        """Filter items by attribute values."""
        ...

    async def filter_async(self, items: AsyncIterable[T], predicate: Callable[[T], Awaitable[bool]]) -> list[T]:
        """Filter items using async predicate."""
        ...


@runtime_checkable
class Sortable(Protocol[T]):
    """Protocol for objects that can sort collections."""

    def sort(self, items: list[T], key: Optional[Callable[[T], Any]] = None, reverse: bool = False) -> list[T]:
        """Sort items using optional key function."""
        ...

    def sort_by_multiple_keys(self, items: list[T], keys: list[Callable[[T], Any]]) -> list[T]:
        """Sort items by multiple criteria."""
        ...

    def get_default_sort_key(self) -> Callable[[T], Any]:
        """Return default sorting key for this type."""
        ...


# ============================================================================
# Service and Component Protocols
# ============================================================================

@runtime_checkable
class Service(Protocol):
    """Protocol for service components."""

    async def start(self) -> None:
        """Start the service."""
        ...

    async def stop(self) -> None:
        """Stop the service."""
        ...

    def is_running(self) -> bool:
        """Check if service is currently running."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Perform health check and return status."""
        ...


@runtime_checkable
class Middleware(Protocol):
    """Protocol for middleware components."""

    async def process_request(self, request: Any, next_handler: Callable) -> Any:
        """Process incoming request."""
        ...

    async def process_response(self, response: Any) -> Any:
        """Process outgoing response."""
        ...

    def get_priority(self) -> int:
        """Return middleware priority (lower = executed first)."""
        ...


@runtime_checkable
class Plugin(Protocol):
    """Protocol for plugin components."""

    def get_name(self) -> str:
        """Return plugin name."""
        ...

    def get_version(self) -> str:
        """Return plugin version."""
        ...

    async def initialize(self, context: dict[str, Any]) -> None:
        """Initialize plugin with context."""
        ...

    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        ...

    def get_capabilities(self) -> list[str]:
        """Return list of plugin capabilities."""
        ...


@runtime_checkable
class EventHandler(Protocol[T]):
    """Protocol for event handling."""

    async def handle_event(self, event: T) -> None:
        """Handle specific event type."""
        ...

    def can_handle(self, event: T) -> bool:
        """Check if this handler can process the event."""
        ...

    def get_event_types(self) -> list[type]:
        """Return list of event types this handler supports."""
        ...


# ============================================================================
# Repository and Storage Protocols
# ============================================================================

@runtime_checkable
class Repository(Protocol[T]):
    """Protocol for repository pattern implementation."""

    async def save(self, entity: T) -> T:
        """Save entity and return updated version."""
        ...

    async def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID."""
        ...

    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> list[T]:
        """Find all entities with pagination."""
        ...

    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        ...

    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        ...


@runtime_checkable
class Cache(Protocol[K, V]):
    """Protocol for cache implementations."""

    async def get(self, key: K) -> Optional[V]:
        """Get value by key."""
        ...

    async def set(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        ...

    async def delete(self, key: K) -> bool:
        """Delete value by key."""
        ...

    async def clear(self) -> None:
        """Clear all cached values."""
        ...

    async def exists(self, key: K) -> bool:
        """Check if key exists in cache."""
        ...


@runtime_checkable
class Storage(Protocol):
    """Protocol for storage backends."""

    async def store(self, key: str, data: bytes) -> None:
        """Store binary data."""
        ...

    async def retrieve(self, key: str) -> Optional[bytes]:
        """Retrieve binary data."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete stored data."""
        ...

    async def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """List all keys with optional prefix filter."""
        ...

    async def get_metadata(self, key: str) -> Optional[dict[str, Any]]:
        """Get metadata for stored object."""
        ...


# ============================================================================
# Protocol-Based Duck Typing Utilities
# ============================================================================

class ProtocolChecker:
    """Utility class for runtime protocol checking and validation."""

    @staticmethod
    def implements_protocol(obj: Any, protocol: type) -> bool:
        """Check if object implements protocol at runtime."""
        try:
            return isinstance(obj, protocol)
        except TypeError:
            # Protocol might not be runtime_checkable
            return ProtocolChecker._manual_protocol_check(obj, protocol)

    @staticmethod
    def _manual_protocol_check(obj: Any, protocol: type) -> bool:
        """Manually check protocol implementation by inspecting methods."""
        try:
            protocol_annotations = get_type_hints(protocol)

            for attr_name, attr_type in protocol_annotations.items():
                if not hasattr(obj, attr_name):
                    return False

                obj_attr = getattr(obj, attr_name)

                # Check if it's a method/property with correct signature
                if callable(obj_attr):
                    if hasattr(protocol, attr_name):
                        protocol_method = getattr(protocol, attr_name)
                        if hasattr(protocol_method, '__annotations__'):
                            # Could add more sophisticated signature checking here
                            pass

            return True

        except Exception:
            return False

    @staticmethod
    def get_missing_methods(obj: Any, protocol: type) -> list[str]:
        """Get list of methods missing from protocol implementation."""
        missing = []

        try:
            protocol_annotations = get_type_hints(protocol)

            for attr_name in protocol_annotations:
                if not hasattr(obj, attr_name):
                    missing.append(attr_name)
                elif not callable(getattr(obj, attr_name)) and not isinstance(getattr(obj, attr_name), property):
                    # Check if it should be callable based on protocol
                    if hasattr(protocol, attr_name):
                        protocol_attr = getattr(protocol, attr_name)
                        if callable(protocol_attr):
                            missing.append(f"{attr_name} (not callable)")

            return missing

        except Exception as e:
            logger.error(f"Error checking protocol compliance: {e}")
            return [f"Error checking protocol: {e}"]

    @staticmethod
    def validate_protocol_implementations(obj: Any, *protocols: type) -> dict[type, dict[str, Any]]:
        """Validate object against multiple protocols and return detailed results."""
        results = {}

        for protocol in protocols:
            implements = ProtocolChecker.implements_protocol(obj, protocol)
            missing = ProtocolChecker.get_missing_methods(obj, protocol) if not implements else []

            results[protocol] = {
                'implements': implements,
                'missing_methods': missing,
                'protocol_name': getattr(protocol, '__name__', str(protocol))
            }

        return results


class ProtocolAdapter:
    """Adapter for making objects conform to protocols."""

    def __init__(self, target: Any):
        self.target = target
        self._adapters: dict[type, dict[str, Callable]] = {}

    def add_adapter(self, protocol: type, method_name: str, implementation: Callable) -> 'ProtocolAdapter':
        """Add method implementation for protocol compliance."""
        if protocol not in self._adapters:
            self._adapters[protocol] = {}

        self._adapters[protocol][method_name] = implementation

        # Dynamically add method to this adapter
        setattr(self, method_name, implementation)

        return self

    def implements(self, protocol: type) -> bool:
        """Check if adapter implements protocol."""
        if ProtocolChecker.implements_protocol(self.target, protocol):
            return True

        # Check if we have adapters for missing methods
        missing = ProtocolChecker.get_missing_methods(self.target, protocol)
        protocol_adapters = self._adapters.get(protocol, {})

        for missing_method in missing:
            if missing_method not in protocol_adapters:
                return False

        return True

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to target or adapters."""
        # First check adapters
        for protocol_adapters in self._adapters.values():
            if name in protocol_adapters:
                return protocol_adapters[name]

        # Then delegate to target
        return getattr(self.target, name)


# ============================================================================
# Duck Typing Helper Functions
# ============================================================================

def duck_type_check(obj: Any, required_methods: list[str], required_properties: Optional[list[str]] = None) -> bool:
    """Check if object has required methods and properties (duck typing)."""
    required_properties = required_properties or []

    # Check methods
    for method_name in required_methods:
        if not hasattr(obj, method_name):
            return False
        if not callable(getattr(obj, method_name)):
            return False

    # Check properties
    for prop_name in required_properties:
        if not hasattr(obj, prop_name):
            return False

    return True


def make_duck_compatible(obj: Any, target_interface: type) -> Any:
    """Create duck-type compatible wrapper for object."""
    class DuckWrapper:
        def __init__(self, wrapped_obj):
            self._wrapped = wrapped_obj

        def __getattr__(self, name):
            return getattr(self._wrapped, name)

        def __repr__(self):
            return f"DuckWrapper({self._wrapped})"

    wrapper = DuckWrapper(obj)

    # Add missing methods from target interface if possible
    if hasattr(target_interface, '__annotations__'):
        annotations = get_type_hints(target_interface)

        for method_name in annotations:
            if not hasattr(obj, method_name):
                # Create placeholder method
                def placeholder_method(*args, **kwargs):
                    raise NotImplementedError(f"Method {method_name} not implemented in wrapped object")

                setattr(wrapper, method_name, placeholder_method)

    return wrapper


async def call_if_callable(obj: Any, method_name: str, *args, **kwargs) -> Any:
    """Safely call method if it exists and is callable."""
    if hasattr(obj, method_name):
        method = getattr(obj, method_name)
        if callable(method):
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
    return None


def get_protocol_methods(protocol: type) -> list[str]:
    """Extract method names from protocol definition."""
    methods = []

    try:
        annotations = get_type_hints(protocol)

        for name, annotation in annotations.items():
            if hasattr(protocol, name):
                attr = getattr(protocol, name)
                if callable(attr) or isinstance(attr, property):
                    methods.append(name)

        # Also check for methods defined directly on the protocol
        for attr_name in dir(protocol):
            if not attr_name.startswith('_'):
                attr = getattr(protocol, attr_name)
                if callable(attr) and attr_name not in methods:
                    methods.append(attr_name)

    except Exception as e:
        logger.warning(f"Error extracting protocol methods: {e}")

    return methods


# ============================================================================
# Example Implementation Classes
# ============================================================================

@dataclass
class UniversalMemory:
    """Example class implementing multiple memory-related protocols."""

    id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: float
    updated_at: Optional[float] = None
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    # Identifiable protocol
    # (id property already defined)

    # Timestamped protocol
    # (created_at and updated_at already defined)

    # Serializable protocol
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type,
            'importance_score': self.importance_score,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'embedding': self.embedding,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'UniversalMemory':
        return cls(**data)

    # Cacheable protocol
    @property
    def cache_key(self) -> str:
        return f"memory:{self.id}"

    @property
    def cache_ttl(self) -> int:
        return 3600  # 1 hour

    def is_cache_valid(self) -> bool:
        return True  # Always valid for this example

    # MemoryLike protocol
    # (content, memory_type, importance_score already defined)

    def get_embedding(self) -> Optional[list[float]]:
        return self.embedding

    # Validatable protocol
    def validate(self) -> bool:
        errors = self.get_validation_errors()
        return len(errors) == 0

    def get_validation_errors(self) -> list[str]:
        errors = []

        if not self.content or not self.content.strip():
            errors.append("Content cannot be empty")

        if not (0.0 <= self.importance_score <= 1.0):
            errors.append("Importance score must be between 0.0 and 1.0")

        if self.memory_type not in ['semantic', 'episodic', 'procedural']:
            errors.append("Memory type must be semantic, episodic, or procedural")

        return errors


class ProcessingService:
    """Example service implementing multiple service protocols."""

    def __init__(self, name: str):
        self.name = name
        self._running = False
        self._start_time = None

    # Service protocol
    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._start_time = asyncio.get_event_loop().time()
        logger.info(f"Service {self.name} started")

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        logger.info(f"Service {self.name} stopped")

    def is_running(self) -> bool:
        return self._running

    async def health_check(self) -> dict[str, Any]:
        uptime = asyncio.get_event_loop().time() - self._start_time if self._start_time else 0

        return {
            'service': self.name,
            'status': 'healthy' if self._running else 'stopped',
            'uptime_seconds': uptime,
            'timestamp': asyncio.get_event_loop().time()
        }

    # Configurable protocol
    def configure(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, f"config_{key}", value)

    def get_configuration(self) -> dict[str, Any]:
        config = {}
        for attr in dir(self):
            if attr.startswith('config_'):
                config[attr[7:]] = getattr(self, attr)
        return config

    def reset_configuration(self) -> None:
        for attr in list(dir(self)):
            if attr.startswith('config_'):
                delattr(self, attr)


# ============================================================================
# Protocol Testing and Validation
# ============================================================================

def test_protocol_implementations():
    """Test protocol implementations with examples."""

    # Test UniversalMemory
    memory = UniversalMemory(
        id="test_001",
        content="This is test content",
        memory_type="semantic",
        importance_score=0.8,
        created_at=1234567890.0
    )

    # Test protocol compliance
    checker = ProtocolChecker()
    protocols_to_test = [Identifiable, Timestamped, Serializable, Cacheable, MemoryLike, Validatable]

    results = checker.validate_protocol_implementations(memory, *protocols_to_test)

    print("Protocol compliance results for UniversalMemory:")
    for protocol, result in results.items():
        status = "✓" if result['implements'] else "✗"
        print(f"  {status} {result['protocol_name']}")
        if result['missing_methods']:
            print(f"    Missing: {', '.join(result['missing_methods'])}")

    # Test ProcessingService
    service = ProcessingService("test_service")
    service_protocols = [Service, Configurable]

    service_results = checker.validate_protocol_implementations(service, *service_protocols)

    print("\nProtocol compliance results for ProcessingService:")
    for protocol, result in service_results.items():
        status = "✓" if result['implements'] else "✗"
        print(f"  {status} {result['protocol_name']}")
        if result['missing_methods']:
            print(f"    Missing: {', '.join(result['missing_methods'])}")

    # Test duck typing
    class SimpleDuck:
        def quack(self):
            return "Quack!"

        def swim(self):
            return "Swimming..."

    duck = SimpleDuck()
    is_duck_like = duck_type_check(duck, ['quack', 'swim'])
    print(f"\nDuck typing test: {is_duck_like}")

    print("\nAll protocol tests completed!")


if __name__ == "__main__":
    test_protocol_implementations()
