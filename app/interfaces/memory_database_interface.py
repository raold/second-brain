#!/usr/bin/env python3
"""
Memory Database Interface - Abstraction Layer for Testing

This interface abstracts database operations for memory relationships,
enabling proper dependency injection and comprehensive testing.

Created as part of Phase 1: Emergency Stabilization
- Fixes database coupling issues preventing testing
- Enables mock implementations for unit tests
- Provides consistent interface for memory operations
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime


class MemoryDatabaseInterface(ABC):
    """Abstract interface for memory database operations."""
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID.
        
        Args:
            memory_id: UUID of the memory to retrieve
            
        Returns:
            Memory data dict or None if not found
        """
        pass
    
    @abstractmethod
    async def get_candidate_memories(
        self, 
        exclude_id: str, 
        limit: int = 50,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get candidate memories for relationship analysis.
        
        Args:
            exclude_id: Memory ID to exclude from results
            limit: Maximum number of candidates to return
            memory_types: Optional filter by memory types
            
        Returns:
            List of memory data dictionaries
        """
        pass
    
    @abstractmethod
    async def get_memories_for_clustering(
        self,
        memory_types: Optional[List[str]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get memories for clustering analysis.
        
        Args:
            memory_types: Optional filter by memory types
            limit: Maximum number of memories to return
            
        Returns:
            List of memory data dictionaries
        """
        pass
    
    @abstractmethod
    async def get_concept_memories(
        self, 
        concept_pattern: str, 
        cutoff_date: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get memories matching concept pattern since cutoff date.
        
        Args:
            concept_pattern: Regex pattern for concept matching
            cutoff_date: Minimum creation date
            limit: Maximum number of memories to return
            
        Returns:
            List of memory data dictionaries sorted by creation date
        """
        pass


class PostgreSQLMemoryDatabase(MemoryDatabaseInterface):
    """PostgreSQL implementation of memory database interface."""
    
    def __init__(self, database_service):
        """Initialize with database service dependency.
        
        Args:
            database_service: Database service instance (injected)
        """
        self.database_service = database_service
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory from PostgreSQL."""
        async with self.database_service.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT id, content, embedding, memory_type, importance_score,
                       semantic_metadata, episodic_metadata, procedural_metadata,
                       created_at, updated_at
                FROM memories 
                WHERE id = $1
                """,
                memory_id,
            )
            return dict(result) if result else None
    
    async def get_candidate_memories(
        self, 
        exclude_id: str, 
        limit: int = 50,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get candidate memories from PostgreSQL."""
        query_filters = ["id != $1", "embedding IS NOT NULL"]
        params: List[Any] = [exclude_id]
        
        if memory_types:
            params.append(memory_types)
            query_filters.append(f"memory_type = ANY(${len(params)})")
        
        params.append(limit)
        where_clause = " AND ".join(query_filters)
        
        query = f"""
            SELECT id, content, embedding, memory_type, importance_score,
                   semantic_metadata, episodic_metadata, procedural_metadata,
                   created_at, updated_at
            FROM memories 
            WHERE {where_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ${len(params)}
        """
        
        async with self.database_service.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(result) for result in results]
    
    async def get_memories_for_clustering(
        self,
        memory_types: Optional[List[str]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get memories for clustering from PostgreSQL."""
        query_filters = ["embedding IS NOT NULL"]
        params: List[Any] = []
        
        if memory_types:
            params.append(memory_types)
            query_filters.append(f"memory_type = ANY(${len(params)})")
        
        params.append(limit)
        where_clause = " AND ".join(query_filters)
        
        query = f"""
            SELECT id, content, embedding, memory_type, importance_score,
                   semantic_metadata, episodic_metadata, procedural_metadata,
                   created_at
            FROM memories 
            WHERE {where_clause}
            ORDER BY importance_score DESC
            LIMIT ${len(params)}
        """
        
        async with self.database_service.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(result) for result in results]
    
    async def get_concept_memories(
        self, 
        concept_pattern: str, 
        cutoff_date: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get concept memories from PostgreSQL."""
        async with self.database_service.pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT id, content, embedding, memory_type, importance_score,
                       created_at, updated_at
                FROM memories 
                WHERE (content ~* $1 OR 
                       semantic_metadata::text ~* $1 OR
                       episodic_metadata::text ~* $1 OR 
                       procedural_metadata::text ~* $1)
                AND created_at >= $2
                AND embedding IS NOT NULL
                ORDER BY created_at ASC
                LIMIT $3
                """,
                concept_pattern,
                cutoff_date,
                limit
            )
            return [dict(result) for result in results]


class MockMemoryDatabase(MemoryDatabaseInterface):
    """Mock implementation for testing."""
    
    def __init__(self, mock_memories: Optional[List[Dict[str, Any]]] = None):
        """Initialize with optional mock data.
        
        Args:
            mock_memories: Optional list of mock memory data
        """
        self.memories = mock_memories or []
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory from mock data."""
        for memory in self.memories:
            if memory.get('id') == memory_id:
                return memory.copy()
        return None
    
    async def get_candidate_memories(
        self, 
        exclude_id: str, 
        limit: int = 50,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get candidate memories from mock data."""
        candidates = []
        for memory in self.memories:
            if memory.get('id') == exclude_id:
                continue
            if not memory.get('embedding'):
                continue
            if memory_types and memory.get('memory_type') not in memory_types:
                continue
            candidates.append(memory.copy())
            if len(candidates) >= limit:
                break
        
        # Sort by importance and creation date
        return sorted(
            candidates,
            key=lambda m: (m.get('importance_score', 0), m.get('created_at', datetime.min)),
            reverse=True
        )
    
    async def get_memories_for_clustering(
        self,
        memory_types: Optional[List[str]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get memories for clustering from mock data."""
        candidates = []
        for memory in self.memories:
            if not memory.get('embedding'):
                continue
            if memory_types and memory.get('memory_type') not in memory_types:
                continue
            candidates.append(memory.copy())
            if len(candidates) >= limit:
                break
        
        return sorted(
            candidates,
            key=lambda m: m.get('importance_score', 0),
            reverse=True
        )
    
    async def get_concept_memories(
        self, 
        concept_pattern: str, 
        cutoff_date: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get concept memories from mock data."""
        import re
        candidates = []
        pattern = re.compile(concept_pattern, re.IGNORECASE)
        
        for memory in self.memories:
            if not memory.get('embedding'):
                continue
            if memory.get('created_at', datetime.min) < cutoff_date:
                continue
            
            # Check if pattern matches content or metadata
            content = memory.get('content', '')
            if pattern.search(content):
                candidates.append(memory.copy())
            elif any(
                pattern.search(str(memory.get(field, {})))
                for field in ['semantic_metadata', 'episodic_metadata', 'procedural_metadata']
            ):
                candidates.append(memory.copy())
            
            if len(candidates) >= limit:
                break
        
        return sorted(
            candidates,
            key=lambda m: m.get('created_at', datetime.min)
        )
