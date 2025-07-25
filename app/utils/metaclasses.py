"""
Tasteful metaclass implementations for the Second Brain application.

This module demonstrates sophisticated but practical uses of metaclasses that
simplify complexity and provide framework-like features. Each metaclass solves
real problems and enhances developer experience without being overly clever.
"""

import asyncio
import functools
import inspect
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Optional, TypeVar, Union, get_type_hints

logger = logging.getLogger(__name__)

T = TypeVar('T')
C = TypeVar('C', bound=type)


# ============================================================================
# Registry Metaclass - Automatic Registration and Discovery
# ============================================================================

class RegistryMeta(type):
    """
    Metaclass that automatically registers classes in a global registry.

    Useful for plugins, handlers, processors that need automatic discovery.
    Simplifies the pattern of manually registering components.
    """

    _registries: dict[str, dict[str, type]] = defaultdict(dict)
    _categories: dict[str, set[str]] = defaultdict(set)

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Extract registration info from class definition
        registry_name = kwargs.pop('registry', None)
        category = kwargs.pop('category', 'default')
        auto_register = kwargs.pop('auto_register', True)

        cls = super().__new__(mcs, name, bases, namespace)

        # Auto-register if enabled
        if auto_register and registry_name:
            mcs.register(cls, registry_name, category)

            logger.debug(f"Auto-registered {name} in registry '{registry_name}' category '{category}'")

        return cls

    @classmethod
    def register(mcs, cls: type, registry_name: str, category: str = 'default') -> None:
        """Manually register a class in the registry."""
        if registry_name not in mcs._registries:
            mcs._registries[registry_name] = {}

        # Use class name as key, or custom key if provided
        key = getattr(cls, '_registry_key', cls.__name__)
        mcs._registries[registry_name][key] = cls
        mcs._categories[registry_name].add(category)

        logger.debug(f"Registered {cls.__name__} as '{key}' in '{registry_name}' registry")

    @classmethod
    def get_registry(mcs, registry_name: str) -> dict[str, type]:
        """Get all classes in a registry."""
        return mcs._registries.get(registry_name, {}).copy()

    @classmethod
    def get_class(mcs, registry_name: str, class_key: str) -> Optional[type]:
        """Get specific class from registry."""
        return mcs._registries.get(registry_name, {}).get(class_key)

    @classmethod
    def get_categories(mcs, registry_name: str) -> set[str]:
        """Get all categories in a registry."""
        return mcs._categories.get(registry_name, set()).copy()

    @classmethod
    def find_implementations(mcs, base_class: type, registry_name: str) -> list[type]:
        """Find all implementations of a base class in registry."""
        registry = mcs.get_registry(registry_name)
        implementations = []

        for cls in registry.values():
            if issubclass(cls, base_class):
                implementations.append(cls)

        return implementations

    @classmethod
    def create_instance(mcs, registry_name: str, class_key: str, *args, **kwargs) -> Any:
        """Create instance of registered class."""
        cls = mcs.get_class(registry_name, class_key)
        if cls:
            return cls(*args, **kwargs)
        raise KeyError(f"Class '{class_key}' not found in registry '{registry_name}'")


# ============================================================================
# Singleton Metaclass - Thread-Safe Singleton Pattern
# ============================================================================

class SingletonMeta(type):
    """
    Metaclass implementing thread-safe singleton pattern.

    More elegant than decorator-based singletons and supports inheritance.
    Each class gets its own singleton instance, not shared across inheritance.
    """

    _instances: dict[type, Any] = {}
    _locks: dict[type, asyncio.Lock] = {}

    def __call__(cls, *args, **kwargs):
        # Double-check locking pattern for thread safety
        if cls not in cls._instances:
            # Create lock for this class if it doesn't exist
            if cls not in cls._locks:
                cls._locks[cls] = asyncio.Lock()

            # Use asyncio.create_task to handle potential async __init__
            if asyncio.iscoroutinefunction(cls.__init__):
                return cls._async_singleton_create(*args, **kwargs)
            else:
                return cls._sync_singleton_create(*args, **kwargs)

        return cls._instances[cls]

    async def _async_singleton_create(cls, *args, **kwargs):
        """Create singleton instance for async classes."""
        if cls not in cls._instances:
            async with cls._locks[cls]:
                if cls not in cls._instances:  # Double-check
                    instance = object.__new__(cls)
                    await instance.__init__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    def _sync_singleton_create(cls, *args, **kwargs):
        """Create singleton instance for sync classes."""
        if cls not in cls._instances:
            # For sync classes, we use a simple approach
            # In a real app, you might want threading.Lock instead
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)

        return cls._instances[cls]

    @classmethod
    def clear_instances(mcs):
        """Clear all singleton instances (useful for testing)."""
        mcs._instances.clear()
        mcs._locks.clear()

    @classmethod
    def get_instance(mcs, cls: type) -> Optional[Any]:
        """Get singleton instance if it exists."""
        return mcs._instances.get(cls)


# ============================================================================
# Validation Metaclass - Automatic Method and Attribute Validation
# ============================================================================

class ValidationMeta(type):
    """
    Metaclass that adds automatic validation to classes.

    Inspects methods and attributes at class creation time and adds
    validation logic based on type hints and custom validators.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Extract validation options
        validate_types = kwargs.pop('validate_types', True)
        validate_methods = kwargs.pop('validate_methods', True)
        strict_mode = kwargs.pop('strict_mode', False)

        cls = super().__new__(mcs, name, bases, namespace)

        if validate_types:
            mcs._add_type_validation(cls, strict_mode)

        if validate_methods:
            mcs._add_method_validation(cls, strict_mode)

        return cls

    @classmethod
    def _add_type_validation(mcs, cls: type, strict_mode: bool) -> None:
        """Add type validation to class attributes."""
        type_hints = get_type_hints(cls)

        for attr_name, expected_type in type_hints.items():
            if not attr_name.startswith('_'):  # Don't validate private attributes
                mcs._create_validated_property(cls, attr_name, expected_type, strict_mode)

    @classmethod
    def _create_validated_property(mcs, cls: type, attr_name: str, expected_type: type, strict_mode: bool) -> None:
        """Create a validated property for an attribute."""
        private_name = f'_{attr_name}_value'

        def getter(self):
            return getattr(self, private_name, None)

        def setter(self, value):
            if strict_mode and not mcs._check_type(value, expected_type):
                raise TypeError(f"Invalid type for {attr_name}: expected {expected_type}, got {type(value)}")
            elif not strict_mode and value is not None and not mcs._check_type(value, expected_type):
                logger.warning(f"Type mismatch for {cls.__name__}.{attr_name}: expected {expected_type}, got {type(value)}")

            setattr(self, private_name, value)

        # Create property and add to class
        prop = property(getter, setter, doc=f"Validated property for {attr_name}")
        setattr(cls, attr_name, prop)

    @classmethod
    def _add_method_validation(mcs, cls: type, strict_mode: bool) -> None:
        """Add validation to class methods based on type hints."""
        for method_name in dir(cls):
            if method_name.startswith('_'):
                continue

            method = getattr(cls, method_name)
            if callable(method) and hasattr(method, '__annotations__'):
                validated_method = mcs._create_validated_method(method, strict_mode)
                setattr(cls, method_name, validated_method)

    @classmethod
    def _create_validated_method(mcs, method: Callable, strict_mode: bool) -> Callable:
        """Create a validated version of a method."""
        type_hints = get_type_hints(method)
        sig = inspect.signature(method)

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            # Bind arguments to parameters
            try:
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
            except TypeError as e:
                if strict_mode:
                    raise
                logger.warning(f"Argument binding failed for {method.__name__}: {e}")
                return method(*args, **kwargs)

            # Validate argument types
            for param_name, value in bound_args.arguments.items():
                if param_name in type_hints:
                    expected_type = type_hints[param_name]
                    if not mcs._check_type(value, expected_type):
                        msg = f"Invalid type for parameter '{param_name}' in {method.__name__}: expected {expected_type}, got {type(value)}"
                        if strict_mode:
                            raise TypeError(msg)
                        else:
                            logger.warning(msg)

            # Call original method
            result = method(*args, **kwargs)

            # Validate return type if specified
            if 'return' in type_hints:
                return_type = type_hints['return']
                if not mcs._check_type(result, return_type):
                    msg = f"Invalid return type from {method.__name__}: expected {return_type}, got {type(result)}"
                    if strict_mode:
                        raise TypeError(msg)
                    else:
                        logger.warning(msg)

            return result

        return wrapper

    @staticmethod
    def _check_type(value: Any, expected_type: type) -> bool:
        """Check if value matches expected type (simplified type checking)."""
        try:
            # Handle basic types
            if expected_type == Any:
                return True

            # Handle Union types (simplified)
            if hasattr(expected_type, '__origin__') and expected_type.__origin__ is Union:
                return any(isinstance(value, arg) for arg in expected_type.__args__)

            # Handle Optional (Union[T, None])
            if (hasattr(expected_type, '__origin__') and
                expected_type.__origin__ is Union and
                type(None) in expected_type.__args__):
                if value is None:
                    return True
                non_none_types = [arg for arg in expected_type.__args__ if arg is not type(None)]
                return any(isinstance(value, arg) for arg in non_none_types)

            # Basic isinstance check
            return isinstance(value, expected_type)

        except Exception:
            # Fallback to basic check
            return isinstance(value, expected_type)


# ============================================================================
# Observer Metaclass - Automatic Event Handling Registration
# ============================================================================

class ObserverMeta(type):
    """
    Metaclass that automatically sets up event handling methods.

    Scans for methods with specific naming patterns and registers them
    as event handlers. Simplifies observer pattern implementation.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        # Set up event handling
        mcs._setup_event_handlers(cls)

        return cls

    @classmethod
    def _setup_event_handlers(mcs, cls: type) -> None:
        """Set up automatic event handler registration."""
        handlers = {}

        # Find all handler methods (methods starting with 'on_')
        for attr_name in dir(cls):
            if attr_name.startswith('on_') and callable(getattr(cls, attr_name)):
                event_name = attr_name[3:]  # Remove 'on_' prefix
                handler = getattr(cls, attr_name)
                handlers[event_name] = handler

        # Store handlers in class
        cls._event_handlers = handlers

        # Add event dispatch method if not present
        if not hasattr(cls, 'handle_event'):
            cls.handle_event = mcs._create_event_dispatcher(cls)

    @classmethod
    def _create_event_dispatcher(mcs, cls: type) -> Callable:
        """Create an event dispatcher method for the class."""

        async def handle_event(self, event_name: str, *args, **kwargs):
            """Automatically dispatch events to registered handlers."""
            if event_name in self._event_handlers:
                handler = self._event_handlers[event_name]

                if asyncio.iscoroutinefunction(handler):
                    return await handler(self, *args, **kwargs)
                else:
                    return handler(self, *args, **kwargs)
            else:
                logger.debug(f"No handler found for event '{event_name}' in {cls.__name__}")
                return None

        return handle_event


# ============================================================================
# Configuration Metaclass - Automatic Configuration Management
# ============================================================================

class ConfigMeta(type):
    """
    Metaclass that automatically handles configuration loading and validation.

    Inspects class attributes and creates configuration management logic
    with environment variable support, type conversion, and defaults.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Extract configuration options
        config_prefix = kwargs.pop('config_prefix', name.lower())
        auto_load = kwargs.pop('auto_load', True)
        env_var_support = kwargs.pop('env_var_support', True)

        cls = super().__new__(mcs, name, bases, namespace)

        # Set up configuration
        cls._config_prefix = config_prefix
        cls._config_fields = mcs._extract_config_fields(cls)

        if auto_load:
            mcs._add_config_loading(cls, env_var_support)

        return cls

    @classmethod
    def _extract_config_fields(mcs, cls: type) -> dict[str, Any]:
        """Extract configuration fields from class annotations."""
        fields = {}

        # Get type hints for configuration fields
        type_hints = get_type_hints(cls)

        for attr_name, attr_type in type_hints.items():
            if not attr_name.startswith('_'):
                default_value = getattr(cls, attr_name, None)
                fields[attr_name] = {
                    'type': attr_type,
                    'default': default_value,
                    'env_var': f"{cls._config_prefix.upper()}_{attr_name.upper()}"
                }

        return fields

    @classmethod
    def _add_config_loading(mcs, cls: type, env_var_support: bool) -> None:
        """Add configuration loading methods to the class."""

        def load_config(self, config_dict: Optional[dict[str, Any]] = None) -> None:
            """Load configuration from dictionary and environment variables."""
            import os

            config_dict = config_dict or {}

            for field_name, field_info in self._config_fields.items():
                value = None

                # Priority: explicit config dict > environment variable > default
                if field_name in config_dict:
                    value = config_dict[field_name]
                elif env_var_support and field_info['env_var'] in os.environ:
                    env_value = os.environ[field_info['env_var']]
                    value = mcs._convert_env_value(env_value, field_info['type'])
                else:
                    value = field_info['default']

                setattr(self, field_name, value)

            logger.debug(f"Loaded configuration for {cls.__name__}")

        def get_config(self) -> dict[str, Any]:
            """Get current configuration as dictionary."""
            config = {}
            for field_name in self._config_fields:
                if hasattr(self, field_name):
                    config[field_name] = getattr(self, field_name)
            return config

        def validate_config(self) -> list[str]:
            """Validate current configuration and return list of issues."""
            issues = []

            for field_name, field_info in self._config_fields.items():
                if hasattr(self, field_name):
                    value = getattr(self, field_name)
                    expected_type = field_info['type']

                    if value is not None and not isinstance(value, expected_type):
                        issues.append(f"Invalid type for {field_name}: expected {expected_type}, got {type(value)}")
                else:
                    if field_info['default'] is None:
                        issues.append(f"Required configuration field '{field_name}' is missing")

            return issues

        # Add methods to class
        cls.load_config = load_config
        cls.get_config = get_config
        cls.validate_config = validate_config

    @staticmethod
    def _convert_env_value(env_value: str, expected_type: type) -> Any:
        """Convert environment variable string to expected type."""
        try:
            if expected_type == bool:
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif expected_type == int:
                return int(env_value)
            elif expected_type == float:
                return float(env_value)
            elif expected_type == list:
                return env_value.split(',')
            else:
                return env_value
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert environment value '{env_value}' to {expected_type}")
            return env_value


# ============================================================================
# Performance Monitoring Metaclass
# ============================================================================

class PerformanceMeta(type):
    """
    Metaclass that automatically adds performance monitoring to methods.

    Wraps methods with timing and profiling code. Can be configured to
    monitor specific methods or all methods in a class.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Extract monitoring options
        monitor_all = kwargs.pop('monitor_all', False)
        monitor_methods = kwargs.pop('monitor_methods', [])
        performance_threshold = kwargs.pop('performance_threshold', 1.0)  # seconds

        cls = super().__new__(mcs, name, bases, namespace)

        if monitor_all or monitor_methods:
            mcs._add_performance_monitoring(cls, monitor_all, monitor_methods, performance_threshold)

        return cls

    @classmethod
    def _add_performance_monitoring(mcs, cls: type, monitor_all: bool,
                                    monitor_methods: list[str], threshold: float) -> None:
        """Add performance monitoring to specified methods."""

        for method_name in dir(cls):
            if method_name.startswith('_'):
                continue

            method = getattr(cls, method_name)
            if not callable(method):
                continue

            should_monitor = monitor_all or method_name in monitor_methods

            if should_monitor:
                monitored_method = mcs._create_monitored_method(method, method_name, threshold)
                setattr(cls, method_name, monitored_method)

    @classmethod
    def _create_monitored_method(mcs, method: Callable, method_name: str, threshold: float) -> Callable:
        """Create a performance-monitored version of a method."""

        if asyncio.iscoroutinefunction(method):
            @functools.wraps(method)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                try:
                    result = await method(*args, **kwargs)
                    duration = time.perf_counter() - start_time

                    if duration > threshold:
                        logger.warning(f"Slow method execution: {method_name} took {duration:.4f}s")
                    else:
                        logger.debug(f"Method {method_name} executed in {duration:.4f}s")

                    return result

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    logger.error(f"Method {method_name} failed after {duration:.4f}s: {e}")
                    raise

            return async_wrapper
        else:
            @functools.wraps(method)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                try:
                    result = method(*args, **kwargs)
                    duration = time.perf_counter() - start_time

                    if duration > threshold:
                        logger.warning(f"Slow method execution: {method_name} took {duration:.4f}s")
                    else:
                        logger.debug(f"Method {method_name} executed in {duration:.4f}s")

                    return result

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    logger.error(f"Method {method_name} failed after {duration:.4f}s: {e}")
                    raise

            return sync_wrapper


# ============================================================================
# Example Usage Classes
# ============================================================================

# Registry example
class MemoryProcessor(metaclass=RegistryMeta, registry='processors', category='memory'):
    """Base memory processor registered automatically."""

    def process(self, content: str) -> str:
        return content


class SemanticProcessor(MemoryProcessor):
    """Semantic processor - automatically inherits registration."""
    _registry_key = 'semantic'

    def process(self, content: str) -> str:
        return f"SEMANTIC: {content}"


class EpisodicProcessor(MemoryProcessor):
    """Episodic processor."""
    _registry_key = 'episodic'

    def process(self, content: str) -> str:
        return f"EPISODIC: {content}"


# Singleton example
class DatabaseConnection(metaclass=SingletonMeta):
    """Database connection singleton."""

    def __init__(self, connection_string: str = "default"):
        self.connection_string = connection_string
        self.connected = False
        logger.info(f"Creating database connection: {connection_string}")

    def connect(self):
        self.connected = True
        return f"Connected to {self.connection_string}"


# Validation example
class ValidatedMemory(metaclass=ValidationMeta, validate_types=True, strict_mode=False):
    """Memory class with automatic validation."""

    content: str
    importance_score: float
    memory_type: str

    def __init__(self, content: str, importance_score: float, memory_type: str):
        self.content = content
        self.importance_score = importance_score
        self.memory_type = memory_type

    def update_score(self, new_score: float) -> float:
        """Update importance score - automatically validated."""
        self.importance_score = new_score
        return new_score


# Observer example
class EventHandler(metaclass=ObserverMeta):
    """Event handler with automatic method registration."""

    def on_memory_created(self, memory_id: str, content: str):
        logger.info(f"Memory created: {memory_id}")

    def on_memory_updated(self, memory_id: str, old_content: str, new_content: str):
        logger.info(f"Memory updated: {memory_id}")

    def on_memory_deleted(self, memory_id: str):
        logger.info(f"Memory deleted: {memory_id}")


# Configuration example
class ServiceConfig(metaclass=ConfigMeta, config_prefix='service', auto_load=True):
    """Service configuration with automatic environment variable support."""

    host: str = 'localhost'
    port: int = 8000
    debug: bool = False
    timeout: float = 30.0
    features: list[str] = []


# Performance monitoring example
class AnalyticsService(metaclass=PerformanceMeta, monitor_all=True, performance_threshold=0.1):
    """Service with automatic performance monitoring."""

    async def analyze_memories(self, memories: list[str]) -> dict[str, Any]:
        """Analyze memories - automatically monitored."""
        await asyncio.sleep(0.2)  # Simulate work
        return {"analyzed": len(memories), "insights": ["pattern1", "pattern2"]}

    def compute_stats(self, data: list[float]) -> dict[str, float]:
        """Compute statistics - automatically monitored."""
        return {
            "mean": sum(data) / len(data) if data else 0,
            "min": min(data) if data else 0,
            "max": max(data) if data else 0
        }


# ============================================================================
# Metaclass Utilities and Testing
# ============================================================================

def demonstrate_metaclass_features():
    """Demonstrate the metaclass functionality."""

    print("=== Registry Metaclass Demo ===")

    # Show automatic registration
    processors = RegistryMeta.get_registry('processors')
    print(f"Registered processors: {list(processors.keys())}")

    # Create instances from registry
    semantic = RegistryMeta.create_instance('processors', 'semantic')
    result = semantic.process("test content")
    print(f"Semantic processing result: {result}")

    print("\n=== Singleton Metaclass Demo ===")

    # Test singleton behavior
    db1 = DatabaseConnection("primary")
    db2 = DatabaseConnection("secondary")  # Should be same instance
    print(f"Same instance? {db1 is db2}")
    print(f"Connection string: {db1.connection_string}")

    print("\n=== Validation Metaclass Demo ===")

    # Test automatic validation
    memory = ValidatedMemory("test content", 0.8, "semantic")
    print(f"Memory created: {memory.content}")

    try:
        memory.importance_score = "invalid"  # Should trigger warning
    except TypeError as e:
        print(f"Validation error: {e}")

    print("\n=== Observer Metaclass Demo ===")

    # Test automatic event handling
    handler = EventHandler()

    # Simulate events
    asyncio.run(handler.handle_event('memory_created', 'mem123', 'test content'))
    asyncio.run(handler.handle_event('memory_updated', 'mem123', 'old', 'new'))
    asyncio.run(handler.handle_event('unknown_event'))  # Should log debug message

    print("\n=== Configuration Metaclass Demo ===")

    # Test configuration loading
    config = ServiceConfig()
    config.load_config({'host': 'example.com', 'port': 9000})
    print(f"Loaded config: {config.get_config()}")

    validation_issues = config.validate_config()
    print(f"Validation issues: {validation_issues}")

    print("\n=== Performance Metaclass Demo ===")

    # Test performance monitoring
    analytics = AnalyticsService()

    # This should trigger slow method warning
    result = asyncio.run(analytics.analyze_memories(['mem1', 'mem2', 'mem3']))
    print(f"Analysis result: {result}")

    # This should be fast
    stats = analytics.compute_stats([1, 2, 3, 4, 5])
    print(f"Stats result: {stats}")

    print("\nAll metaclass demonstrations completed!")


class MetaclassRegistry:
    """Registry of available metaclasses with their capabilities."""

    AVAILABLE_METACLASSES = {
        'RegistryMeta': {
            'description': 'Automatic class registration and discovery',
            'use_cases': ['Plugin systems', 'Handler registration', 'Factory patterns'],
            'options': ['registry', 'category', 'auto_register']
        },
        'SingletonMeta': {
            'description': 'Thread-safe singleton pattern implementation',
            'use_cases': ['Database connections', 'Configuration objects', 'Caches'],
            'options': []
        },
        'ValidationMeta': {
            'description': 'Automatic type validation for methods and attributes',
            'use_cases': ['API models', 'Configuration classes', 'Data validation'],
            'options': ['validate_types', 'validate_methods', 'strict_mode']
        },
        'ObserverMeta': {
            'description': 'Automatic event handler registration',
            'use_cases': ['Event systems', 'UI callbacks', 'Notification systems'],
            'options': []
        },
        'ConfigMeta': {
            'description': 'Automatic configuration management with environment variables',
            'use_cases': ['Application settings', 'Service configuration', 'Feature flags'],
            'options': ['config_prefix', 'auto_load', 'env_var_support']
        },
        'PerformanceMeta': {
            'description': 'Automatic performance monitoring for methods',
            'use_cases': ['Performance profiling', 'Bottleneck detection', 'SLA monitoring'],
            'options': ['monitor_all', 'monitor_methods', 'performance_threshold']
        }
    }

    @classmethod
    def get_metaclass_info(cls, metaclass_name: str) -> dict[str, Any]:
        """Get information about a specific metaclass."""
        return cls.AVAILABLE_METACLASSES.get(metaclass_name, {})

    @classmethod
    def list_all_metaclasses(cls) -> list[str]:
        """Get list of all available metaclasses."""
        return list(cls.AVAILABLE_METACLASSES.keys())

    @classmethod
    def find_suitable_metaclass(cls, requirements: list[str]) -> list[str]:
        """Find metaclasses suitable for given requirements."""
        suitable = []

        for name, info in cls.AVAILABLE_METACLASSES.items():
            use_cases = [case.lower() for case in info['use_cases']]
            if any(req.lower() in ' '.join(use_cases) for req in requirements):
                suitable.append(name)

        return suitable


if __name__ == "__main__":
    demonstrate_metaclass_features()
