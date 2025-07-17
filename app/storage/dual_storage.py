"""
Dual storage handler for Second Brain with advanced caching and performance optimizations.
Manages both Markdown file storage (legacy) and PostgreSQL persistence (new).
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.storage.postgres_client import get_postgres_client
from app.utils.cache import CacheConfig, get_cache, get_smart_cache
from app.utils.logger import get_logger
from app.utils.openai_client import get_openai_embedding_async

logger = get_logger()

# Enhanced caching for dual storage operations
_dual_storage_cache = get_smart_cache("dual_storage", CacheConfig(
    max_size=1000,
    ttl_seconds=600,  # 10 minutes
    enable_metrics=True,
    compress_keys=True
))

_intent_detection_cache = get_cache("intent_detection", CacheConfig(
    max_size=500,
    ttl_seconds=3600,  # 1 hour for intent detection
    enable_metrics=True,
    compress_keys=True
))

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    dual_storage_operations = Counter('dual_storage_operations_total', 'Dual storage operations', ['operation', 'storage_type', 'status'])
    dual_storage_latency = Histogram('dual_storage_latency_seconds', 'Dual storage operation latency', ['operation'])
    intent_detection_latency = Histogram('intent_detection_latency_seconds', 'Intent detection latency')
    storage_success_rate = Gauge('storage_success_rate', 'Storage success rate by type', ['storage_type'])
except ImportError:
    dual_storage_operations = dual_storage_latency = intent_detection_latency = storage_success_rate = None


class DualStorageHandler:
    """
    Enhanced dual storage handler with advanced caching, performance monitoring, and graceful degradation.
    Provides backward compatibility while enabling advanced SQL queries and analytics.
    """
    
    def __init__(self):
        self.postgres_enabled = True
        self.markdown_enabled = True
        self._markdown_success_count = 0
        self._markdown_total_count = 0
        self._postgres_success_count = 0
        self._postgres_total_count = 0
        
        # Intent detection patterns (cached)
        self._intent_patterns = {
            "question": ["?", "how", "what", "why", "when", "where", "who", "which", "can you", "could you"],
            "todo": ["todo", "task", "need to", "should", "must", "remember to", "don't forget"],
            "reminder": ["remind", "reminder", "remember", "notify", "alert"],
            "command": ["command", "run", "execute", "start", "stop", "create", "delete", "update"],
        }
    
    async def store_memory(
        self,
        payload_id: str,
        text_content: str,
        intent_type: Optional[str] = None,
        model_version: str = "v1.5.0",
        embedding_model: str = "text-embedding-3-small",
        priority: str = "normal",
        source: str = "api",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        create_embedding: bool = True
    ) -> Tuple[str, Optional[List[float]]]:
        """
        Store memory in both storage systems with enhanced performance monitoring.
        
        Args:
            payload_id: Unique identifier for the payload
            text_content: The text content to store
            intent_type: Optional intent classification
            model_version: Version of the model used
            embedding_model: Model used for embeddings
            priority: Priority level (low, normal, high, urgent)
            source: Source of the memory (api, voice, upload, etc.)
            tags: List of tags for categorization
            metadata: Additional metadata
            user: User identifier
            create_embedding: Whether to generate embeddings
            
        Returns:
            Tuple of (memory_id, embedding_vector)
        """
        start_time = time.time()
        
        # Check cache first for duplicate content
        cache_key = f"store:{hash(text_content)}:{intent_type}:{priority}"
        cached_result = _dual_storage_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for memory storage: {payload_id}")
            return cached_result["memory_id"], cached_result.get("embedding_vector")
        
        try:
            # Auto-detect intent if not provided
            if not intent_type:
                intent_type = await self._detect_intent_cached(text_content)
            
            # Generate embedding if requested (handle failures gracefully)
            embedding_vector = None
            if create_embedding:
                try:
                    embedding_start = time.time()
                    embedding_vector = await get_openai_embedding_async(text_content)
                    embedding_time = time.time() - embedding_start
                    logger.debug(f"Generated embedding for {payload_id} in {embedding_time:.2f}s")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for {payload_id}: {e}")
                    # Continue without embedding - don't fail the entire operation
            
            # Prepare metadata
            full_metadata = {
                "user": user,
                "payload_id": payload_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "performance": {
                    "embedding_generated": embedding_vector is not None,
                    "cache_used": False
                },
                **(metadata or {})
            }
            
            # Storage results tracking
            markdown_success = False
            postgres_success = False
            postgres_memory_id = None
            storage_errors = []
            
            # Store in Markdown (legacy system) - async operation
            if self.markdown_enabled:
                markdown_task = asyncio.create_task(
                    self._store_markdown_async(
                        payload_id, text_content, intent_type, 
                        priority, tags, full_metadata
                    )
                )
            
            # Store in PostgreSQL (new system) - primary operation
            if self.postgres_enabled:
                try:
                    postgres_start = time.time()
                    client = await get_postgres_client()
                    postgres_memory_id = await client.store_memory(
                        text_content=text_content,
                        embedding_vector=embedding_vector,
                        intent_type=intent_type,
                        model_version=model_version,
                        embedding_model=embedding_model,
                        priority=priority,
                        source=source,
                        tags=tags or [],
                        metadata=full_metadata
                    )
                    postgres_success = True
                    self._postgres_success_count += 1
                    
                    postgres_time = time.time() - postgres_start
                    logger.info(f"Stored memory {payload_id} in PostgreSQL as {postgres_memory_id} in {postgres_time:.2f}s")
                    
                    # Record success metric
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='store', storage_type='postgres', status='success'
                        ).inc()
                    
                except Exception as e:
                    storage_errors.append(f"PostgreSQL: {str(e)}")
                    logger.error(f"Failed to store {payload_id} in PostgreSQL: {e}")
                    
                    # Record failure metric
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='store', storage_type='postgres', status='error'
                        ).inc()
                
                finally:
                    self._postgres_total_count += 1
            
            # Wait for Markdown storage to complete
            if self.markdown_enabled:
                try:
                    await markdown_task
                    markdown_success = True
                    self._markdown_success_count += 1
                    logger.info(f"Stored memory {payload_id} in Markdown")
                    
                    # Record success metric
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='store', storage_type='markdown', status='success'
                        ).inc()
                        
                except Exception as e:
                    storage_errors.append(f"Markdown: {str(e)}")
                    logger.error(f"Failed to store {payload_id} in Markdown: {e}")
                    
                    # Record failure metric
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='store', storage_type='markdown', status='error'
                        ).inc()
                
                finally:
                    self._markdown_total_count += 1
            
            # Update success rate metrics
            self._update_success_rate_metrics()
            
            # Log storage results and handle failures
            total_time = time.time() - start_time
            
            if markdown_success and postgres_success:
                logger.info(f"Dual storage successful for {payload_id} in {total_time:.2f}s")
                status = "full_success"
            elif markdown_success or postgres_success:
                storage_type = "Markdown" if markdown_success else "PostgreSQL"
                logger.warning(f"Partial storage success ({storage_type}) for {payload_id} in {total_time:.2f}s")
                status = "partial_success"
            else:
                error_msg = f"Dual storage failed for {payload_id}: {'; '.join(storage_errors)}"
                logger.error(error_msg)
                
                # Record total failure
                if dual_storage_operations:
                    dual_storage_operations.labels(
                        operation='store', storage_type='both', status='error'
                    ).inc()
                
                raise Exception(error_msg)
            
            # Cache successful result
            result = {
                "memory_id": postgres_memory_id or payload_id,
                "embedding_vector": embedding_vector,
                "status": status,
                "storage_time": total_time
            }
            _dual_storage_cache.set(cache_key, result)
            
            # Record overall latency
            if dual_storage_latency:
                dual_storage_latency.labels(operation='store').observe(total_time)
            
            return postgres_memory_id or payload_id, embedding_vector
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Dual storage operation failed for {payload_id} after {total_time:.2f}s: {e}")
            
            # Record failure latency
            if dual_storage_latency:
                dual_storage_latency.labels(operation='store_error').observe(total_time)
            
            raise
    
    async def _detect_intent_cached(self, text_content: str) -> str:
        """Detect intent with caching for performance."""
        cache_key = f"intent:{hash(text_content)}"
        
        # Check cache first
        cached_intent = _intent_detection_cache.get(cache_key)
        if cached_intent is not None:
            return cached_intent
        
        start_time = time.time()
        
        # Simple rule-based intent detection (fast)
        text_lower = text_content.lower()
        
        # Check for question patterns
        if any(pattern in text_lower for pattern in self._intent_patterns["question"]):
            intent = "question"
        # Check for todo patterns
        elif any(pattern in text_lower for pattern in self._intent_patterns["todo"]):
            intent = "todo"
        # Check for reminder patterns
        elif any(pattern in text_lower for pattern in self._intent_patterns["reminder"]):
            intent = "reminder"
        # Check for command patterns
        elif any(pattern in text_lower for pattern in self._intent_patterns["command"]):
            intent = "command"
        else:
            intent = "note"
        
        # Cache the result
        _intent_detection_cache.set(cache_key, intent)
        
        # Record metrics
        if intent_detection_latency:
            intent_detection_latency.observe(time.time() - start_time)
        
        logger.debug(f"Detected intent '{intent}' for text: {text_content[:50]}...")
        return intent
    
    async def _store_markdown_async(
        self, 
        payload_id: str, 
        text_content: str, 
        intent_type: Optional[str], 
        priority: str, 
        tags: Optional[List[str]], 
        metadata: Dict[str, Any]
    ) -> None:
        """Async wrapper for Markdown storage."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._store_markdown_sync, 
                                 payload_id, text_content, intent_type, priority, tags, metadata)
    
    def _store_markdown_sync(
        self, 
        payload_id: str, 
        text_content: str, 
        intent_type: Optional[str], 
        priority: str, 
        tags: Optional[List[str]], 
        metadata: Dict[str, Any]
    ) -> None:
        """Store memory as Markdown file (synchronous)."""
        # Create safe filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_id = "".join(c for c in payload_id if c.isalnum() or c in '-_')[:50]
        safe_filename = f"{timestamp}_{safe_id}"
        
        # Build markdown content with frontmatter
        markdown_content = "---\n"
        markdown_content += f"id: {payload_id}\n"
        markdown_content += f"timestamp: {metadata.get('timestamp', datetime.now(timezone.utc).isoformat())}\n"
        markdown_content += f"intent_type: {intent_type or 'note'}\n"
        markdown_content += f"priority: {priority}\n"
        markdown_content += f"tags: {json.dumps(tags or [])}\n"
        markdown_content += f"user: {metadata.get('user', 'unknown')}\n"
        markdown_content += "---\n\n"
        
        # Add content
        markdown_content += f"# {intent_type.title() if intent_type else 'Note'}\n\n"
        markdown_content += text_content
        
        # Add metadata section
        markdown_content += "\n\n---\n\n## Metadata\n\n"
        markdown_content += f"```json\n{json.dumps(metadata, indent=2, default=str)}\n```\n"
        
        # Ensure directory exists
        data_dir = Path("app/data/memories")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        file_path = data_dir / f"{safe_filename}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        logger.debug(f"Wrote Markdown file: {file_path}")
    
    def _update_success_rate_metrics(self) -> None:
        """Update Prometheus success rate metrics."""
        if storage_success_rate:
            # Calculate success rates
            markdown_rate = (self._markdown_success_count / max(self._markdown_total_count, 1)) * 100
            postgres_rate = (self._postgres_success_count / max(self._postgres_total_count, 1)) * 100
            
            storage_success_rate.labels(storage_type='markdown').set(markdown_rate)
            storage_success_rate.labels(storage_type='postgres').set(postgres_rate)
    
    async def get_memory(
        self, 
        memory_id: str, 
        prefer_postgres: bool = True,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve memory from PostgreSQL or Markdown with caching.
        
        Args:
            memory_id: ID of the memory to retrieve
            prefer_postgres: Whether to try PostgreSQL first
            use_cache: Whether to use caching
            
        Returns:
            Dictionary containing memory data or None
        """
        cache_key = f"get:{memory_id}"
        
        # Check cache first
        if use_cache:
            cached_result = _dual_storage_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for memory retrieval: {memory_id}")
                return cached_result
        
        start_time = time.time()
        
        try:
            if prefer_postgres and self.postgres_enabled:
                try:
                    client = await get_postgres_client()
                    memory = await client.get_memory(memory_id, use_cache=use_cache)
                    if memory:
                        logger.info(f"Retrieved memory {memory_id} from PostgreSQL")
                        
                        # Cache the result
                        if use_cache:
                            _dual_storage_cache.set(cache_key, memory)
                        
                        # Record metrics
                        if dual_storage_operations:
                            dual_storage_operations.labels(
                                operation='get', storage_type='postgres', status='success'
                            ).inc()
                        if dual_storage_latency:
                            dual_storage_latency.labels(operation='get').observe(time.time() - start_time)
                        
                        return memory
                        
                except Exception as e:
                    logger.warning(f"Failed to get {memory_id} from PostgreSQL: {e}")
                    
                    # Record failure metric
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='get', storage_type='postgres', status='error'
                        ).inc()
            
            # Fallback to Markdown (not implemented in current codebase)
            # This would require implementing Markdown reading functionality
            logger.warning(f"Markdown fallback not implemented for {memory_id}")
            
            # Record miss
            if dual_storage_operations:
                dual_storage_operations.labels(
                    operation='get', storage_type='markdown', status='not_implemented'
                ).inc()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            
            # Record total latency even for errors
            if dual_storage_latency:
                dual_storage_latency.labels(operation='get_error').observe(time.time() - start_time)
            
            return None
    
    async def search_memories(
        self,
        query_text: Optional[str] = None,
        intent_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[str] = None,
        source: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
        use_postgres: bool = True,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search memories with advanced filtering and caching.
        
        Args:
            query_text: Text to search for
            intent_types: Filter by intent types
            tags: Filter by tags
            priority: Filter by priority level
            source: Filter by source
            date_from: Filter by creation date (from)
            date_to: Filter by creation date (to)
            limit: Maximum number of results
            offset: Number of results to skip
            use_postgres: Whether to use PostgreSQL for search
            use_cache: Whether to use caching
            
        Returns:
            List of memory dictionaries
        """
        start_time = time.time()
        
        try:
            if use_postgres and self.postgres_enabled:
                client = await get_postgres_client()
                results = await client.search_memories(
                    query_text=query_text,
                    intent_types=intent_types,
                    tags=tags,
                    priority=priority,
                    source=source,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit,
                    offset=offset,
                    use_cache=use_cache
                )
                
                # Record metrics
                if dual_storage_operations:
                    dual_storage_operations.labels(
                        operation='search', storage_type='postgres', status='success'
                    ).inc()
                if dual_storage_latency:
                    dual_storage_latency.labels(operation='search').observe(time.time() - start_time)
                
                logger.info(f"PostgreSQL search returned {len(results)} results")
                return results
            
            else:
                # Fallback to Markdown search (not implemented)
                logger.warning("Markdown search not implemented, returning empty results")
                
                # Record not implemented
                if dual_storage_operations:
                    dual_storage_operations.labels(
                        operation='search', storage_type='markdown', status='not_implemented'
                    ).inc()
                
                return []
                
        except Exception as e:
            logger.error(f"Search failed: {e}")
            
            # Record error metrics
            if dual_storage_operations:
                dual_storage_operations.labels(
                    operation='search', storage_type='postgres', status='error'
                ).inc()
            if dual_storage_latency:
                dual_storage_latency.labels(operation='search_error').observe(time.time() - start_time)
            
            raise
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any],
        use_postgres: bool = True
    ) -> bool:
        """Update memory with cache invalidation."""
        start_time = time.time()
        
        try:
            if use_postgres and self.postgres_enabled:
                client = await get_postgres_client()
                success = await client.update_memory(memory_id, updates)
                
                if success:
                    # Invalidate caches
                    _dual_storage_cache.delete(f"get:{memory_id}")
                    
                    # Record success
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='update', storage_type='postgres', status='success'
                        ).inc()
                    if dual_storage_latency:
                        dual_storage_latency.labels(operation='update').observe(time.time() - start_time)
                    
                    logger.info(f"Updated memory {memory_id}")
                    return True
                else:
                    # Record failure
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='update', storage_type='postgres', status='error'
                        ).inc()
                    
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            
            # Record error metrics
            if dual_storage_operations:
                dual_storage_operations.labels(
                    operation='update', storage_type='postgres', status='error'
                ).inc()
            if dual_storage_latency:
                dual_storage_latency.labels(operation='update_error').observe(time.time() - start_time)
            
            return False
    
    async def add_feedback(
        self,
        memory_id: str,
        feedback_type: str,
        feedback_value: Optional[float] = None,
        feedback_text: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add user feedback with cache invalidation."""
        start_time = time.time()
        
        try:
            if self.postgres_enabled:
                client = await get_postgres_client()
                feedback_id = await client.add_feedback(
                    memory_id=memory_id,
                    feedback_type=feedback_type,
                    feedback_value=feedback_value,
                    feedback_text=feedback_text,
                    user_context=user_context
                )
                
                if feedback_id:
                    # Invalidate related caches
                    _dual_storage_cache.delete(f"get:{memory_id}")
                    
                    # Record success
                    if dual_storage_operations:
                        dual_storage_operations.labels(
                            operation='feedback', storage_type='postgres', status='success'
                        ).inc()
                    if dual_storage_latency:
                        dual_storage_latency.labels(operation='feedback').observe(time.time() - start_time)
                    
                    return feedback_id
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to add feedback for memory {memory_id}: {e}")
            
            # Record error metrics
            if dual_storage_operations:
                dual_storage_operations.labels(
                    operation='feedback', storage_type='postgres', status='error'
                ).inc()
            if dual_storage_latency:
                dual_storage_latency.labels(operation='feedback_error').observe(time.time() - start_time)
            
            return ""
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            "dual_storage_cache": _dual_storage_cache.stats(),
            "intent_detection_cache": _intent_detection_cache.stats(),
            "storage_success_rates": {
                "markdown": {
                    "success_count": self._markdown_success_count,
                    "total_count": self._markdown_total_count,
                    "success_rate": (self._markdown_success_count / max(self._markdown_total_count, 1)) * 100
                },
                "postgres": {
                    "success_count": self._postgres_success_count,
                    "total_count": self._postgres_total_count,
                    "success_rate": (self._postgres_success_count / max(self._postgres_total_count, 1)) * 100
                }
            },
            "configuration": {
                "postgres_enabled": self.postgres_enabled,
                "markdown_enabled": self.markdown_enabled,
                "cache_enabled": True,
                "async_operations": True
            }
        }


# Global instance
_dual_storage_handler = None

async def get_dual_storage() -> DualStorageHandler:
    """Get singleton dual storage handler."""
    global _dual_storage_handler
    if _dual_storage_handler is None:
        _dual_storage_handler = DualStorageHandler()
    return _dual_storage_handler 