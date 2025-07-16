"""
PostgreSQL client for memory persistence and metadata storage.
Handles database operations for the Second Brain application with advanced performance optimizations.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import asyncpg
from sqlalchemy import MetaData, Table, Column, String, Text, DateTime, JSON, Float, Integer, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import select, insert, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import config
from app.utils.logger import get_logger
from app.utils.cache import (
    get_cache, async_cached_function, CacheConfig,
    ANALYTICS_CACHE_CONFIG, MEMORY_ACCESS_CACHE_CONFIG
)
from app.utils.exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseTimeoutError, 
    DatabaseIntegrityError, DuplicateMemoryError, MemoryNotFoundError,
    map_external_exception
)
from app.utils.retry import database_retry, async_timeout, async_with_semaphore

logger = get_logger()

Base = declarative_base()

# Enhanced caching for PostgreSQL operations
_query_cache = get_cache("postgres_queries", CacheConfig(
    max_size=500,
    ttl_seconds=300,  # 5 minutes for query results
    enable_metrics=True,
    compress_keys=True
))

_memory_cache = get_cache("postgres_memories", MEMORY_ACCESS_CACHE_CONFIG)
_analytics_cache = get_cache("postgres_analytics", ANALYTICS_CACHE_CONFIG)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    postgres_operations = Counter('postgres_operations_total', 'PostgreSQL operations', ['operation', 'status'])
    postgres_query_latency = Histogram('postgres_query_latency_seconds', 'PostgreSQL query latency', ['operation'])
    postgres_connection_pool = Gauge('postgres_connection_pool_stats', 'PostgreSQL connection pool statistics', ['stat'])
    postgres_cache_operations = Counter('postgres_cache_operations_total', 'PostgreSQL cache operations', ['cache_type', 'operation'])
except ImportError:
    postgres_operations = postgres_query_latency = postgres_connection_pool = postgres_cache_operations = None


class Memory(Base):
    """Memory table for storing ingested text and metadata."""
    __tablename__ = 'memories'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_content = Column(Text, nullable=False)
    embedding_vector = Column(JSONB)  # Store as JSON array
    intent_type = Column(String(50))  # question, reminder, note, todo, command, other
    model_version = Column(String(50), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_dimensions = Column(Integer, nullable=False)
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    source = Column(String(100))  # api, voice, upload, plugin
    tags = Column(JSONB)  # Array of tags
    memory_metadata = Column(JSONB)  # Additional flexible metadata (renamed from metadata)
    version = Column(Integer, default=1)
    parent_id = Column(UUID(as_uuid=True))  # For version history
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    feedback_score = Column(Float, default=0.0)  # User feedback rating
    access_count = Column(Integer, default=0)  # How often accessed
    last_accessed = Column(DateTime(timezone=True))


class SearchHistory(Base):
    """Track search patterns for analytics and personalization."""
    __tablename__ = 'search_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(JSONB)
    result_count = Column(Integer)
    clicked_results = Column(JSONB)  # Array of clicked memory IDs
    search_type = Column(String(50))  # semantic, keyword, hybrid
    filters_used = Column(JSONB)  # Filters applied to search
    response_time_ms = Column(Float)
    user_satisfaction = Column(Float)  # User rating of results
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserFeedback(Base):
    """Store user feedback on memories for personalization."""
    __tablename__ = 'user_feedback'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # upvote, downvote, edit, delete
    feedback_value = Column(Float)  # Numeric rating or score
    feedback_text = Column(Text)  # Optional text feedback
    user_context = Column(JSONB)  # Additional context about the user/session
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PostgresClient:
    """
    Enhanced async PostgreSQL client with connection pooling, caching, and performance monitoring.
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.connection_pool = None
        self._initialized = False
        self._health_cache = {}
        self._last_health_check = None
    
    async def initialize(self) -> None:
        """Initialize database connection with enhanced connection pooling."""
        if self._initialized:
            return
            
        try:
            # Create async engine with advanced connection pooling
            database_url = f"postgresql+asyncpg://{config.postgres['username']}:{config.postgres['password']}@{config.postgres['host']}:{config.postgres['port']}/{config.postgres['database']}"
            
            self.engine = create_async_engine(
                database_url,
                # Connection pool settings
                pool_size=config.postgres['pool_size'],  # 20 connections
                max_overflow=config.postgres['max_overflow'],  # 30 additional connections
                pool_timeout=30,  # 30 seconds to get connection
                pool_recycle=3600,  # Recycle connections every hour
                pool_pre_ping=True,  # Validate connections before use
                
                # Performance settings
                echo=config.debug,  # Log SQL queries in debug mode
                echo_pool=config.debug,  # Log pool events in debug mode
                
                # Connection arguments for asyncpg
                connect_args={
                    "command_timeout": 60,  # 60 second query timeout
                    "server_settings": {
                        "jit": "off",  # Disable JIT for smaller queries
                        "application_name": "second-brain-api",
                    },
                },
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Initialize connection pool monitoring
            self._setup_pool_monitoring()
            
            self._initialized = True
            logger.info("Enhanced PostgreSQL client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL client: {e}")
            raise
    
    def _setup_pool_monitoring(self):
        """Set up connection pool monitoring metrics."""
        if postgres_connection_pool:
            # Set initial pool metrics
            pool = self.engine.pool
            postgres_connection_pool.labels(stat='size').set(pool.size())
            postgres_connection_pool.labels(stat='overflow').set(pool.overflow())
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("PostgreSQL client closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with caching and detailed metrics."""
        # Use cached health status if recent
        now = datetime.now(timezone.utc)
        if (self._last_health_check and 
            (now - self._last_health_check).total_seconds() < 30):  # 30 second cache
            return self._health_cache.get("status", {"status": "unknown"})
        
        try:
            start_time = time.time()
            
            async with self.session_factory() as session:
                # Basic connectivity test
                result = await session.execute(select(func.now()))
                db_time = result.scalar()
                
                # Get table counts
                memory_count = await session.execute(select(func.count(Memory.id)))
                total_memories = memory_count.scalar()
                
                active_memory_count = await session.execute(
                    select(func.count(Memory.id)).where(Memory.is_active == True)
                )
                active_memories = active_memory_count.scalar()
                
                # Get search history count
                search_count = await session.execute(select(func.count(SearchHistory.id)))
                total_searches = search_count.scalar()
                
                # Connection pool stats
                pool = self.engine.pool
                pool_stats = {
                    "size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "checked_in": pool.checkedin(),
                }
                
                # Update pool metrics
                if postgres_connection_pool:
                    postgres_connection_pool.labels(stat='checked_out').set(pool_stats["checked_out"])
                    postgres_connection_pool.labels(stat='checked_in').set(pool_stats["checked_in"])
                
                query_time = time.time() - start_time
                
                health_status = {
                    "status": "healthy",
                    "database_time": db_time.isoformat(),
                    "total_memories": total_memories,
                    "active_memories": active_memories,
                    "total_searches": total_searches,
                    "connection_pool": pool_stats,
                    "query_time_ms": round(query_time * 1000, 2),
                    "timestamp": now.isoformat()
                }
                
                # Cache the result
                self._health_cache["status"] = health_status
                self._last_health_check = now
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='health_check', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='health_check').observe(query_time)
                
                return health_status
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='health_check', status='error').inc()
            
            error_status = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": now.isoformat()
            }
            
            # Cache error status for shorter time
            self._health_cache["status"] = error_status
            self._last_health_check = now
            
            return error_status
    
    # Memory CRUD Operations with caching
    
    @database_retry(circuit_breaker_name="postgres_store")
    @async_timeout(30.0, "store_memory")
    @async_with_semaphore(10, "store_memory")
    async def store_memory(
        self,
        text_content: str,
        embedding_vector: Optional[List[float]] = None,
        intent_type: Optional[str] = None,
        model_version: str = "v1.5.0",
        embedding_model: str = "text-embedding-3-small",
        priority: str = "normal",
        source: str = "api",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Store a new memory in the database with enhanced error handling."""
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                memory = Memory(
                    text_content=text_content,
                    embedding_vector=embedding_vector,
                    intent_type=intent_type,
                    model_version=model_version,
                    embedding_model=embedding_model,
                    embedding_dimensions=len(embedding_vector) if embedding_vector else 0,
                    priority=priority,
                    source=source,
                    tags=tags or [],
                    memory_metadata=metadata or {},
                    parent_id=uuid.UUID(parent_id) if parent_id else None
                )
                
                session.add(memory)
                await session.commit()
                await session.refresh(memory)
                
                memory_id = str(memory.id)
                
                # Cache the new memory
                cache_key = f"memory:{memory_id}"
                memory_data = {
                    "id": memory_id,
                    "text_content": text_content,
                    "intent_type": intent_type,
                    "priority": priority,
                    "created_at": memory.created_at.isoformat(),
                    "embedding_dimensions": memory.embedding_dimensions
                }
                _memory_cache.set(cache_key, memory_data)
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='store', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='store').observe(time.time() - start_time)
                
                logger.info(f"Stored memory {memory_id} in {time.time() - start_time:.2f}s")
                return memory_id
                
        except IntegrityError as e:
            # Handle duplicate keys or constraint violations
            if "duplicate key" in str(e).lower():
                raise DuplicateMemoryError(f"Memory with similar content already exists")
            else:
                raise DatabaseIntegrityError(str(e), constraint=getattr(e, 'constraint', None))
                
        except OperationalError as e:
            # Handle database operational errors
            if "connection" in str(e).lower():
                raise DatabaseConnectionError(f"Database connection failed: {e}")
            else:
                raise DatabaseError(f"Database operation failed: {e}")
                
        except asyncpg.exceptions.PostgresError as e:
            # Handle specific PostgreSQL errors
            if e.sqlstate == '23505':  # Unique constraint violation
                raise DuplicateMemoryError(f"Memory already exists")
            elif e.sqlstate == '08003':  # Connection does not exist
                raise DatabaseConnectionError(f"Database connection lost: {e}")
            else:
                raise DatabaseError(f"PostgreSQL error [{e.sqlstate}]: {e}")
                
        except asyncio.TimeoutError:
            # This will be caught by the @async_timeout decorator
            raise
            
        except Exception as e:
            # Map any other exceptions to our hierarchy
            mapped_exc = map_external_exception(e)
            logger.error(f"Unexpected error storing memory: {mapped_exc}")
            
            # Record failure metrics
            if postgres_operations:
                postgres_operations.labels(operation='store', status='error').inc()
            
            raise mapped_exc
    
    async def get_memory(self, memory_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve memory by ID with caching."""
        cache_key = f"memory:{memory_id}"
        
        # Check cache first
        if use_cache:
            cached_result = _memory_cache.get(cache_key)
            if cached_result is not None:
                if postgres_cache_operations:
                    postgres_cache_operations.labels(cache_type='memory', operation='hit').inc()
                return cached_result
        
        if postgres_cache_operations:
            postgres_cache_operations.labels(cache_type='memory', operation='miss').inc()
        
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Memory).where(Memory.id == uuid.UUID(memory_id))
                )
                memory = result.scalar_one_or_none()
                
                if memory:
                    # Update access tracking
                    memory.access_count = (memory.access_count or 0) + 1
                    memory.last_accessed = datetime.now(timezone.utc)
                    await session.commit()
                    
                    memory_data = {
                        "id": str(memory.id),
                        "text_content": memory.text_content,
                        "intent_type": memory.intent_type,
                        "priority": memory.priority,
                        "source": memory.source,
                        "tags": memory.tags or [],
                        "created_at": memory.created_at.isoformat(),
                        "updated_at": memory.updated_at.isoformat(),
                        "access_count": memory.access_count,
                        "feedback_score": memory.feedback_score,
                        "metadata": memory.memory_metadata or {}
                    }
                    
                    # Cache the result
                    if use_cache:
                        _memory_cache.set(cache_key, memory_data)
                    
                    # Record metrics
                    if postgres_operations:
                        postgres_operations.labels(operation='get_memory', status='success').inc()
                    if postgres_query_latency:
                        postgres_query_latency.labels(operation='get_memory').observe(time.time() - start_time)
                    
                    return memory_data
                
                return None
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='get_memory', status='error').inc()
            
            logger.error(f"Failed to get memory {memory_id}: {e}")
            raise
    
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any],
        create_version: bool = True
    ) -> bool:
        """Update memory with version history and cache invalidation."""
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                # Get existing memory
                result = await session.execute(
                    select(Memory).where(Memory.id == uuid.UUID(memory_id))
                )
                memory = result.scalar_one_or_none()
                
                if not memory:
                    return False
                
                # Create version history if requested
                if create_version:
                    version_memory = Memory(
                        text_content=memory.text_content,
                        embedding_vector=memory.embedding_vector,
                        intent_type=memory.intent_type,
                        model_version=memory.model_version,
                        embedding_model=memory.embedding_model,
                        embedding_dimensions=memory.embedding_dimensions,
                        priority=memory.priority,
                        source=memory.source,
                        tags=memory.tags,
                        memory_metadata=memory.memory_metadata,
                        version=memory.version,
                        parent_id=memory.id,  # Link to current version
                        created_at=memory.created_at,
                        updated_at=memory.updated_at,
                        is_active=False  # Mark as historical version
                    )
                    session.add(version_memory)
                
                # Update current memory
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
                
                memory.version = (memory.version or 1) + 1
                memory.updated_at = datetime.now(timezone.utc)
                
                await session.commit()
                
                # Invalidate cache
                cache_key = f"memory:{memory_id}"
                _memory_cache.delete(cache_key)
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='update_memory', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='update_memory').observe(time.time() - start_time)
                
                logger.info(f"Updated memory {memory_id}")
                return True
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='update_memory', status='error').inc()
            
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False
    
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
        include_inactive: bool = False,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Search memories with advanced filtering and caching."""
        # Generate cache key for search results
        cache_key_data = {
            "query": query_text,
            "intents": intent_types,
            "tags": tags,
            "priority": priority,
            "source": source,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "limit": limit,
            "offset": offset,
            "include_inactive": include_inactive
        }
        cache_key = f"search:{hash(str(cache_key_data))}"
        
        # Check cache first
        if use_cache:
            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                if postgres_cache_operations:
                    postgres_cache_operations.labels(cache_type='search', operation='hit').inc()
                return cached_result
        
        if postgres_cache_operations:
            postgres_cache_operations.labels(cache_type='search', operation='miss').inc()
        
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                query = select(Memory)
                
                # Build filters
                filters = []
                
                if not include_inactive:
                    filters.append(Memory.is_active == True)
                
                if query_text:
                    # Full-text search on content
                    filters.append(Memory.text_content.ilike(f"%{query_text}%"))
                
                if intent_types:
                    filters.append(Memory.intent_type.in_(intent_types))
                
                if tags:
                    # Check if any of the provided tags exist in the tags array
                    for tag in tags:
                        filters.append(Memory.tags.op('?')(tag))
                
                if priority:
                    filters.append(Memory.priority == priority)
                
                if source:
                    filters.append(Memory.source == source)
                
                if date_from:
                    filters.append(Memory.created_at >= date_from)
                
                if date_to:
                    filters.append(Memory.created_at <= date_to)
                
                # Apply filters
                if filters:
                    query = query.where(and_(*filters))
                
                # Add ordering by relevance and recency
                query = query.order_by(
                    Memory.feedback_score.desc(),
                    Memory.access_count.desc(),
                    Memory.created_at.desc()
                )
                
                # Add pagination
                query = query.offset(offset).limit(limit)
                
                # Execute query
                result = await session.execute(query)
                memories = result.scalars().all()
                
                # Convert to dict format
                results = []
                for memory in memories:
                    results.append({
                        "id": str(memory.id),
                        "text_content": memory.text_content,
                        "intent_type": memory.intent_type,
                        "priority": memory.priority,
                        "source": memory.source,
                        "tags": memory.tags or [],
                        "created_at": memory.created_at.isoformat(),
                        "updated_at": memory.updated_at.isoformat(),
                        "access_count": memory.access_count or 0,
                        "feedback_score": memory.feedback_score or 0.0,
                        "metadata": memory.memory_metadata or {}
                    })
                
                # Cache the results
                if use_cache:
                    _query_cache.set(cache_key, results)
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='search_memories', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='search_memories').observe(time.time() - start_time)
                
                return results
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='search_memories', status='error').inc()
            
            logger.error(f"Failed to search memories: {e}")
            raise
    
    # Analytics and Feedback with caching
    
    async def record_search(
        self,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        result_count: int = 0,
        search_type: str = "semantic",
        filters_used: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ) -> str:
        """Record a search for analytics with performance tracking."""
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                search_record = SearchHistory(
                    query_text=query_text,
                    query_embedding=query_embedding,
                    result_count=result_count,
                    search_type=search_type,
                    filters_used=filters_used or {},
                    response_time_ms=response_time_ms
                )
                
                session.add(search_record)
                await session.commit()
                await session.refresh(search_record)
                
                # Invalidate analytics cache
                _analytics_cache.clear()
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='record_search', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='record_search').observe(time.time() - start_time)
                
                return str(search_record.id)
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='record_search', status='error').inc()
            
            logger.error(f"Failed to record search: {e}")
            return ""
    
    async def add_feedback(
        self,
        memory_id: str,
        feedback_type: str,
        feedback_value: Optional[float] = None,
        feedback_text: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add user feedback for a memory with cache invalidation."""
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                feedback = UserFeedback(
                    memory_id=uuid.UUID(memory_id),
                    feedback_type=feedback_type,
                    feedback_value=feedback_value,
                    feedback_text=feedback_text,
                    user_context=user_context or {}
                )
                
                session.add(feedback)
                
                # Update memory's feedback score
                if feedback_value is not None:
                    memory_result = await session.execute(
                        select(Memory).where(Memory.id == uuid.UUID(memory_id))
                    )
                    memory = memory_result.scalar_one_or_none()
                    
                    if memory:
                        # Calculate new feedback score (simple average for now)
                        memory.feedback_score = ((memory.feedback_score or 0.0) + feedback_value) / 2
                
                await session.commit()
                await session.refresh(feedback)
                
                # Invalidate caches
                _memory_cache.delete(f"memory:{memory_id}")
                _analytics_cache.clear()
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='add_feedback', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='add_feedback').observe(time.time() - start_time)
                
                return str(feedback.id)
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='add_feedback', status='error').inc()
            
            logger.error(f"Failed to add feedback for memory {memory_id}: {e}")
            return ""
    
    async def get_analytics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get system analytics with caching."""
        cache_key = "system_analytics"
        
        # Check cache first
        if use_cache:
            cached_result = _analytics_cache.get(cache_key)
            if cached_result is not None:
                if postgres_cache_operations:
                    postgres_cache_operations.labels(cache_type='analytics', operation='hit').inc()
                return cached_result
        
        if postgres_cache_operations:
            postgres_cache_operations.labels(cache_type='analytics', operation='miss').inc()
        
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                # Memory statistics
                total_memories = await session.execute(select(func.count(Memory.id)))
                active_memories = await session.execute(
                    select(func.count(Memory.id)).where(Memory.is_active == True)
                )
                
                # Intent distribution
                intent_stats = await session.execute(
                    select(Memory.intent_type, func.count(Memory.id))
                    .where(Memory.is_active == True)
                    .group_by(Memory.intent_type)
                )
                
                # Priority distribution
                priority_stats = await session.execute(
                    select(Memory.priority, func.count(Memory.id))
                    .where(Memory.is_active == True)
                    .group_by(Memory.priority)
                )
                
                # Source distribution
                source_stats = await session.execute(
                    select(Memory.source, func.count(Memory.id))
                    .where(Memory.is_active == True)
                    .group_by(Memory.source)
                )
                
                # Recent activity (today)
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
                recent_memories = await session.execute(
                    select(func.count(Memory.id))
                    .where(Memory.created_at >= today)
                )
                
                recent_searches = await session.execute(
                    select(func.count(SearchHistory.id))
                    .where(SearchHistory.created_at >= today)
                )
                
                # Top accessed memories
                top_memories = await session.execute(
                    select(Memory.id, Memory.text_content, Memory.access_count)
                    .where(Memory.is_active == True)
                    .order_by(Memory.access_count.desc())
                    .limit(5)
                )
                
                analytics_data = {
                    "total_memories": total_memories.scalar(),
                    "active_memories": active_memories.scalar(),
                    "intent_distribution": dict(intent_stats.fetchall()),
                    "priority_distribution": dict(priority_stats.fetchall()),
                    "source_distribution": dict(source_stats.fetchall()),
                    "memories_today": recent_memories.scalar(),
                    "searches_today": recent_searches.scalar(),
                    "top_accessed_memories": [
                        {
                            "id": str(row[0]),
                            "content_preview": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                            "access_count": row[2]
                        }
                        for row in top_memories.fetchall()
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Cache the results
                if use_cache:
                    _analytics_cache.set(cache_key, analytics_data)
                
                # Record metrics
                if postgres_operations:
                    postgres_operations.labels(operation='get_analytics', status='success').inc()
                if postgres_query_latency:
                    postgres_query_latency.labels(operation='get_analytics').observe(time.time() - start_time)
                
                return analytics_data
                
        except Exception as e:
            # Record failure metric
            if postgres_operations:
                postgres_operations.labels(operation='get_analytics', status='error').inc()
            
            logger.error(f"Failed to get analytics: {e}")
            return {}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "query_cache": _query_cache.stats(),
            "memory_cache": _memory_cache.stats(),
            "analytics_cache": _analytics_cache.stats(),
        }


# Global client instance
postgres_client = PostgresClient()


async def get_postgres_client() -> PostgresClient:
    """Dependency to get initialized PostgreSQL client."""
    if not postgres_client._initialized:
        await postgres_client.initialize()
    return postgres_client


# Compatibility functions for old session patterns
async def get_async_session():
    """Compatibility function for old session dependency pattern."""
    client = await get_postgres_client()
    async with client.session_factory() as session:
        yield session


# Compatibility alias for old session factory
AsyncSessionLocal = lambda: get_postgres_client().session_factory


async def close_postgres_client():
    """Compatibility function for closing postgres client."""
    await postgres_client.close() 