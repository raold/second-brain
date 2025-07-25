"""
Cache observer implementation for cache invalidation and optimization.

Observes entity changes and intelligently invalidates or updates
cached data to maintain consistency.
"""

import asyncio
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import Any, Optional

from .observable import ChangeNotification, ChangeType, Observer

logger = logging.getLogger(__name__)


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"      # Invalidate immediately
    LAZY = "lazy"               # Invalidate on next access
    BATCH = "batch"             # Batch invalidations
    TTL_BASED = "ttl_based"     # Time-based invalidation


@dataclass
class CacheRule:
    """Rule for cache invalidation."""
    cache_pattern: Pattern[str]          # Regex pattern for cache keys
    entity_types: set[str]               # Entity types that trigger invalidation
    change_types: set[ChangeType]        # Change types that trigger invalidation
    strategy: InvalidationStrategy       # Invalidation strategy
    priority: int = 0                    # Rule priority (higher = more priority)
    condition: Optional[Callable[[ChangeNotification], bool]] = None  # Custom condition


class CacheManager:
    """
    Abstract cache manager interface.

    Provides a standard interface for different cache implementations
    to integrate with the cache observer.
    """

    async def invalidate_key(self, key: str) -> bool:
        """
        Invalidate a specific cache key.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was invalidated successfully
        """
        raise NotImplementedError

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.

        Args:
            pattern: Pattern to match cache keys

        Returns:
            Number of keys invalidated
        """
        raise NotImplementedError

    async def update_key(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Update a cache key with new value.

        Args:
            key: Cache key to update
            value: New value
            ttl: Optional time-to-live in seconds

        Returns:
            True if key was updated successfully
        """
        raise NotImplementedError

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        raise NotImplementedError


class MemoryCacheManager(CacheManager):
    """
    Simple in-memory cache manager for testing and development.
    """

    def __init__(self, max_size: int = 10000):
        self._cache: dict[str, Any] = {}
        self._ttl: dict[str, float] = {}
        self._access_times: dict[str, float] = {}
        self.max_size = max_size
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'updates': 0
        }

    async def invalidate_key(self, key: str) -> bool:
        """Invalidate a specific cache key."""
        if key in self._cache:
            del self._cache[key]
            self._ttl.pop(key, None)
            self._access_times.pop(key, None)
            self._stats['invalidations'] += 1
            return True
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache keys matching a pattern."""
        regex = re.compile(pattern)
        keys_to_remove = [key for key in self._cache.keys() if regex.match(key)]

        for key in keys_to_remove:
            await self.invalidate_key(key)

        return len(keys_to_remove)

    async def update_key(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Update a cache key with new value."""
        # Check size limit
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove least recently used item
            if self._access_times:
                lru_key = min(self._access_times, key=self._access_times.get)
                await self.invalidate_key(lru_key)

        self._cache[key] = value
        self._access_times[key] = time.time()

        if ttl:
            self._ttl[key] = time.time() + ttl

        self._stats['updates'] += 1
        return True

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self._ttl.items()
            if expiry < current_time
        ]

        return {
            'total_keys': len(self._cache),
            'expired_keys': len(expired_keys),
            'max_size': self.max_size,
            'stats': self._stats.copy()
        }

    def get(self, key: str) -> Any:
        """Get value from cache (for testing)."""
        current_time = time.time()

        # Check TTL
        if key in self._ttl and self._ttl[key] < current_time:
            asyncio.create_task(self.invalidate_key(key))
            self._stats['misses'] += 1
            return None

        if key in self._cache:
            self._access_times[key] = current_time
            self._stats['hits'] += 1
            return self._cache[key]

        self._stats['misses'] += 1
        return None


class CacheObserver(Observer):
    """
    Observer that manages cache invalidation based on entity changes.

    Uses configurable rules to determine when and how to invalidate
    cache entries based on domain events.
    """

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.rules: list[CacheRule] = []
        self._invalidation_queue: list[str] = []
        self._batch_size = 100
        self._batch_timeout = 5.0  # seconds
        self._last_batch_process = time.time()
        self._stats = {
            'notifications_processed': 0,
            'invalidations_triggered': 0,
            'rules_matched': 0,
            'batch_processes': 0
        }

    def add_rule(self, rule: CacheRule) -> None:
        """
        Add a cache invalidation rule.

        Args:
            rule: Cache invalidation rule
        """
        self.rules.append(rule)
        # Sort rules by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

        logger.debug(f"Added cache rule for pattern {rule.cache_pattern.pattern}")

    def remove_rule(self, cache_pattern: str) -> bool:
        """
        Remove cache invalidation rules matching the pattern.

        Args:
            cache_pattern: Cache pattern to remove rules for

        Returns:
            True if any rules were removed
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.cache_pattern.pattern != cache_pattern]
        return len(self.rules) < original_count

    async def on_change(self, notification: ChangeNotification) -> None:
        """Handle change notification and process cache invalidation."""
        self._stats['notifications_processed'] += 1

        # Find matching rules
        matching_rules = []
        for rule in self.rules:
            if self._rule_matches(rule, notification):
                matching_rules.append(rule)
                self._stats['rules_matched'] += 1

        if not matching_rules:
            return

        # Process rules by strategy
        for rule in matching_rules:
            await self._process_rule(rule, notification)

    def _rule_matches(self, rule: CacheRule, notification: ChangeNotification) -> bool:
        """Check if a rule matches the notification."""
        # Check entity type
        if rule.entity_types and notification.entity_type not in rule.entity_types:
            return False

        # Check change type
        if rule.change_types and notification.change_type not in rule.change_types:
            return False

        # Check custom condition
        if rule.condition and not rule.condition(notification):
            return False

        return True

    async def _process_rule(self, rule: CacheRule, notification: ChangeNotification) -> None:
        """Process a matching cache rule."""
        try:
            if rule.strategy == InvalidationStrategy.IMMEDIATE:
                await self._invalidate_immediate(rule, notification)
            elif rule.strategy == InvalidationStrategy.BATCH:
                await self._invalidate_batch(rule, notification)
            elif rule.strategy == InvalidationStrategy.TTL_BASED:
                await self._invalidate_ttl_based(rule, notification)
            else:  # LAZY
                await self._invalidate_lazy(rule, notification)

        except Exception as e:
            logger.error(f"Error processing cache rule: {e}")

    async def _invalidate_immediate(self, rule: CacheRule, notification: ChangeNotification) -> None:
        """Immediately invalidate cache entries."""
        # Generate cache keys based on entity
        cache_keys = self._generate_cache_keys(rule, notification)

        for cache_key in cache_keys:
            await self.cache_manager.invalidate_key(cache_key)
            self._stats['invalidations_triggered'] += 1

        # Also invalidate by pattern
        pattern_count = await self.cache_manager.invalidate_pattern(rule.cache_pattern.pattern)
        self._stats['invalidations_triggered'] += pattern_count

    async def _invalidate_batch(self, rule: CacheRule, notification: ChangeNotification) -> None:
        """Add invalidation to batch queue."""
        cache_keys = self._generate_cache_keys(rule, notification)
        self._invalidation_queue.extend(cache_keys)

        # Process batch if needed
        current_time = time.time()
        if (len(self._invalidation_queue) >= self._batch_size or
            current_time - self._last_batch_process >= self._batch_timeout):
            await self._process_invalidation_batch()

    async def _invalidate_lazy(self, rule: CacheRule, notification: ChangeNotification) -> None:
        """Mark cache entries for lazy invalidation."""
        # For lazy invalidation, we might set a flag or metadata
        # This is implementation-specific to the cache system
        cache_keys = self._generate_cache_keys(rule, notification)

        for cache_key in cache_keys:
            # Mark as stale but don't remove immediately
            await self.cache_manager.update_key(f"{cache_key}:stale", True, ttl=300)

    async def _invalidate_ttl_based(self, rule: CacheRule, notification: ChangeNotification) -> None:
        """Set short TTL for affected cache entries."""
        cache_keys = self._generate_cache_keys(rule, notification)

        for cache_key in cache_keys:
            # Reduce TTL to force expiration soon
            current_value = getattr(self.cache_manager, '_cache', {}).get(cache_key)
            if current_value is not None:
                await self.cache_manager.update_key(cache_key, current_value, ttl=60)  # 1 minute TTL

    def _generate_cache_keys(self, rule: CacheRule, notification: ChangeNotification) -> list[str]:
        """Generate specific cache keys to invalidate based on the notification."""
        cache_keys = []

        # Basic entity-based keys
        entity_id = notification.entity_id
        entity_type = notification.entity_type

        # Common cache key patterns
        patterns = [
            f"{entity_type}:{entity_id}",
            f"{entity_type}:*",
            f"user:{notification.metadata.get('user_id', '*')}:{entity_type}",
            f"search:{entity_type}:*",
            f"list:{entity_type}:*"
        ]

        # Filter patterns that match the rule
        for pattern in patterns:
            if rule.cache_pattern.match(pattern):
                cache_keys.append(pattern)

        return cache_keys

    async def _process_invalidation_batch(self) -> None:
        """Process queued invalidations in batch."""
        if not self._invalidation_queue:
            return

        batch = self._invalidation_queue.copy()
        self._invalidation_queue.clear()
        self._last_batch_process = time.time()

        # Group by pattern to optimize invalidation
        pattern_groups: dict[str, list[str]] = {}
        for cache_key in batch:
            # Extract pattern from cache key
            pattern = cache_key.split(':')[0] + ':*'
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(cache_key)

        # Invalidate by pattern
        total_invalidated = 0
        for pattern, keys in pattern_groups.items():
            count = await self.cache_manager.invalidate_pattern(pattern)
            total_invalidated += count

        self._stats['invalidations_triggered'] += total_invalidated
        self._stats['batch_processes'] += 1

        logger.debug(f"Processed batch invalidation: {total_invalidated} cache entries")

    async def flush_batch(self) -> None:
        """Manually flush the invalidation batch."""
        await self._process_invalidation_batch()

    def get_stats(self) -> dict[str, Any]:
        """Get cache observer statistics."""
        return {
            'notifications_processed': self._stats['notifications_processed'],
            'invalidations_triggered': self._stats['invalidations_triggered'],
            'rules_matched': self._stats['rules_matched'],
            'batch_processes': self._stats['batch_processes'],
            'active_rules': len(self.rules),
            'queued_invalidations': len(self._invalidation_queue)
        }


class CacheInvalidationObserver(CacheObserver):
    """
    Specialized cache observer with predefined rules for common scenarios.

    Provides sensible defaults for typical cache invalidation patterns
    in the Second Brain application.
    """

    def __init__(self, cache_manager: CacheManager):
        super().__init__(cache_manager)
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default cache invalidation rules."""

        # Memory-related cache invalidation
        memory_rule = CacheRule(
            cache_pattern=re.compile(r"memory:.*|search:memory:.*|user:.*:memory.*"),
            entity_types={"memory"},
            change_types={ChangeType.CREATED, ChangeType.UPDATED, ChangeType.DELETED},
            strategy=InvalidationStrategy.IMMEDIATE,
            priority=10
        )
        self.add_rule(memory_rule)

        # Search cache invalidation (more aggressive)
        search_rule = CacheRule(
            cache_pattern=re.compile(r"search:.*"),
            entity_types={"memory", "session"},
            change_types={ChangeType.CREATED, ChangeType.UPDATED, ChangeType.DELETED},
            strategy=InvalidationStrategy.BATCH,
            priority=8
        )
        self.add_rule(search_rule)

        # User session cache
        session_rule = CacheRule(
            cache_pattern=re.compile(r"session:.*|user:.*:session.*"),
            entity_types={"session"},
            change_types={ChangeType.CREATED, ChangeType.UPDATED, ChangeType.DELETED},
            strategy=InvalidationStrategy.IMMEDIATE,
            priority=9
        )
        self.add_rule(session_rule)

        # Analytics cache (less urgent)
        analytics_rule = CacheRule(
            cache_pattern=re.compile(r"analytics:.*|metrics:.*"),
            entity_types={"memory", "session"},
            change_types={ChangeType.CREATED, ChangeType.UPDATED, ChangeType.DELETED},
            strategy=InvalidationStrategy.TTL_BASED,
            priority=5
        )
        self.add_rule(analytics_rule)

        # List/collection caches
        list_rule = CacheRule(
            cache_pattern=re.compile(r"list:.*|collection:.*"),
            entity_types={"memory"},
            change_types={ChangeType.CREATED, ChangeType.DELETED},
            strategy=InvalidationStrategy.IMMEDIATE,
            priority=7
        )
        self.add_rule(list_rule)

        # High-importance memory changes get immediate invalidation
        importance_rule = CacheRule(
            cache_pattern=re.compile(r".*"),
            entity_types={"memory"},
            change_types={ChangeType.UPDATED},
            strategy=InvalidationStrategy.IMMEDIATE,
            priority=15,
            condition=lambda n: n.metadata.get('importance_score', 0) > 0.8
        )
        self.add_rule(importance_rule)

        logger.info(f"Setup {len(self.rules)} default cache invalidation rules")


# Utility functions

def create_memory_cache_observer() -> CacheInvalidationObserver:
    """Create a cache observer with in-memory cache manager."""
    cache_manager = MemoryCacheManager()
    return CacheInvalidationObserver(cache_manager)


def create_cache_rule(
    pattern: str,
    entity_types: list[str],
    change_types: list[str],
    strategy: str = "immediate",
    priority: int = 0,
    condition: Optional[Callable[[ChangeNotification], bool]] = None
) -> CacheRule:
    """
    Utility function to create cache rules with string parameters.

    Args:
        pattern: Regex pattern for cache keys
        entity_types: List of entity type strings
        change_types: List of change type strings
        strategy: Invalidation strategy string
        priority: Rule priority
        condition: Optional condition function

    Returns:
        Configured CacheRule
    """
    return CacheRule(
        cache_pattern=re.compile(pattern),
        entity_types=set(entity_types),
        change_types={ChangeType(ct) for ct in change_types},
        strategy=InvalidationStrategy(strategy),
        priority=priority,
        condition=condition
    )
