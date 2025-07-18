"""
Memory Service - Handles all memory-related business logic.
Separates concerns from route handlers, making the code more testable and maintainable.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import Database
from app.database_mock import MockDatabase
from app.docs import (
    MemoryType,
    MemoryResponse,
    SemanticMetadata,
    EpisodicMetadata,
    ProceduralMetadata
)
from app.security import InputValidator

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service layer for memory operations.
    Handles business logic for storing, retrieving, and searching memories.
    """
    
    def __init__(self, database: Database | MockDatabase, input_validator: InputValidator):
        self.db = database
        self.validator = input_validator
        self.logger = logger
    
    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        semantic_metadata: Optional[SemanticMetadata] = None,
        episodic_metadata: Optional[EpisodicMetadata] = None,
        procedural_metadata: Optional[ProceduralMetadata] = None,
        importance_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryResponse:
        """
        Store a new memory with validated content and metadata.
        
        Args:
            content: Memory content
            memory_type: Type of memory (semantic, episodic, procedural)
            semantic_metadata: Metadata for semantic memories
            episodic_metadata: Metadata for episodic memories
            procedural_metadata: Metadata for procedural memories
            importance_score: Initial importance score (0-1)
            metadata: General metadata (legacy support)
            
        Returns:
            MemoryResponse with stored memory details
            
        Raises:
            ValueError: If validation fails
            Exception: If storage fails
        """
        # Validate input
        validated_content = self.validator.validate_memory_content(content)
        validated_metadata = self.validator.validate_metadata(metadata or {})
        
        # Extract type-specific metadata
        semantic_dict = semantic_metadata.dict() if semantic_metadata else {}
        episodic_dict = episodic_metadata.dict() if episodic_metadata else {}
        procedural_dict = procedural_metadata.dict() if procedural_metadata else {}
        
        # Set default importance score if not provided
        final_importance_score = importance_score if importance_score is not None else 0.5
        
        try:
            # Store memory in database
            memory_id = await self.db.store_memory(
                content=validated_content,
                memory_type=memory_type.value,
                semantic_metadata=semantic_dict,
                episodic_metadata=episodic_dict,
                procedural_metadata=procedural_dict,
                importance_score=final_importance_score,
                metadata=validated_metadata
            )
            
            # Retrieve stored memory
            memory = await self.db.get_memory(memory_id)
            if not memory:
                raise Exception(f"Failed to retrieve stored memory {memory_id}")
            
            self.logger.info(f"Successfully stored {memory_type.value} memory: {memory_id}")
            return MemoryResponse(**memory)
            
        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            raise
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        temporal_filter: Optional[str] = None,
        importance_threshold: Optional[float] = None
    ) -> List[MemoryResponse]:
        """
        Search memories using semantic similarity and filters.
        
        Args:
            query: Search query
            limit: Maximum number of results
            memory_types: Filter by memory types
            temporal_filter: Time-based filter (e.g., "last_week")
            importance_threshold: Minimum importance score
            
        Returns:
            List of matching memories
        """
        # Validate input
        validated_query = self.validator.validate_search_query(query)
        validated_limit = self.validator.validate_search_limit(limit)
        
        try:
            # Convert memory types to strings if provided
            type_filter = [mt.value for mt in memory_types] if memory_types else None
            
            # Perform search
            memories = await self.db.search_memories(
                query=validated_query,
                limit=validated_limit,
                memory_types=type_filter,
                temporal_filter=temporal_filter,
                importance_threshold=importance_threshold
            )
            
            self.logger.info(f"Search returned {len(memories)} results for query: {query[:50]}...")
            return [MemoryResponse(**memory) for memory in memories]
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[MemoryResponse]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            Memory details or None if not found
        """
        try:
            memory = await self.db.get_memory(memory_id)
            if memory:
                self.logger.info(f"Retrieved memory: {memory_id}")
                return MemoryResponse(**memory)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            raise
    
    async def update_memory_importance(
        self,
        memory_id: str,
        importance_score: float
    ) -> bool:
        """
        Update the importance score of a memory.
        
        Args:
            memory_id: Memory identifier
            importance_score: New importance score (0-1)
            
        Returns:
            True if successful
        """
        if not 0 <= importance_score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
        
        try:
            success = await self.db.update_memory_importance(memory_id, importance_score)
            if success:
                self.logger.info(f"Updated importance for {memory_id}: {importance_score}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update memory importance: {e}")
            raise
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored memories.
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            stats = await self.db.get_index_stats()
            
            # Add memory type breakdown if available
            if hasattr(self.db, 'get_memory_type_stats'):
                type_stats = await self.db.get_memory_type_stats()
                stats['memory_types'] = type_stats
            
            self.logger.info("Retrieved memory statistics")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get memory statistics: {e}")
            raise
    
    async def contextual_search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        temporal_filter: Optional[str] = None,
        importance_threshold: float = 0.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform advanced contextual search with multi-dimensional scoring.
        
        Args:
            query: Search query
            memory_types: Filter by memory types
            temporal_filter: Time-based filter
            importance_threshold: Minimum importance score
            limit: Maximum results
            
        Returns:
            List of search results with contextual scores
        """
        validated_query = self.validator.validate_search_query(query)
        validated_limit = self.validator.validate_search_limit(limit)
        
        try:
            # Perform contextual search
            results = await self.db.contextual_search(
                query=validated_query,
                memory_types=[mt.value for mt in memory_types] if memory_types else None,
                temporal_filter=temporal_filter,
                importance_threshold=importance_threshold,
                limit=validated_limit
            )
            
            self.logger.info(f"Contextual search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Contextual search failed: {e}")
            raise 