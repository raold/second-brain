"""
Exact Match Detector

Detects exact duplicate content using content hashing.
Fast and highly accurate for identical content matches.
"""

import hashlib
from collections import defaultdict
from typing import Any, Dict, List
import logging

from app.interfaces.duplicate_detector_interface import BaseDuplicateDetector
from app.models.deduplication_models import (
    DuplicateGroup,
    DeduplicationConfig,
    SimilarityMethod,
    SimilarityScore
)

logger = logging.getLogger(__name__)


class ExactMatchDetector(BaseDuplicateDetector):
    """Detector for exact content matches using MD5 hashing."""
    
    def __init__(self, cache_enabled: bool = True):
        """
        Initialize exact match detector.
        
        Args:
            cache_enabled: Whether to enable similarity score caching
        """
        super().__init__(cache_enabled)
        self.content_hashes: Dict[str, str] = {}
    
    def get_detector_name(self) -> str:
        """Get detector name."""
        return "Exact Match Detector"
    
    def get_similarity_method(self) -> SimilarityMethod:
        """Get similarity method."""
        return SimilarityMethod.EXACT_MATCH
    
    def get_optimal_batch_size(self) -> int:
        """Exact matching works well with larger batches."""
        return 500
    
    def supports_incremental_detection(self) -> bool:
        """Exact matching supports incremental detection via hashing."""
        return True
    
    async def _find_duplicates_impl(
        self, 
        memories: List[Dict[str, Any]], 
        config: DeduplicationConfig
    ) -> List[DuplicateGroup]:
        """
        Find exact duplicate memories using content hashing.
        
        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration
            
        Returns:
            List of duplicate groups found
        """
        if not memories:
            return []
        
        logger.debug(f"Starting exact match detection on {len(memories)} memories")
        
        # Group memories by content hash
        content_hash_map = defaultdict(list)
        
        for memory in memories:
            content = self._extract_content(memory)
            if not content:
                continue
                
            content_hash = self._hash_content(content)
            content_hash_map[content_hash].append(memory)
            
            # Cache the hash for future use
            memory_id = memory.get("id", "unknown")
            self.content_hashes[memory_id] = content_hash
        
        # Find groups with multiple memories (duplicates)
        duplicate_groups = []
        
        for content_hash, memory_group in content_hash_map.items():
            if len(memory_group) <= 1:
                continue  # No duplicates in this group
            
            try:
                group = await self._create_duplicate_group(
                    memory_group, 
                    content_hash, 
                    config
                )
                if group:
                    duplicate_groups.append(group)
                    self._record_duplicate_found()
                    
            except Exception as e:
                logger.error(f"Error creating duplicate group for hash {content_hash[:8]}: {e}")
                continue
        
        logger.info(f"Exact match detection completed: {len(duplicate_groups)} groups found")
        return duplicate_groups
    
    async def _create_duplicate_group(
        self, 
        memories: List[Dict[str, Any]], 
        content_hash: str,
        config: DeduplicationConfig
    ) -> DuplicateGroup:
        """
        Create a duplicate group from memories with identical content.
        
        Args:
            memories: List of memories with identical content
            content_hash: Hash of the identical content
            config: Deduplication configuration
            
        Returns:
            DuplicateGroup instance
        """
        if len(memories) < 2:
            return None
        
        # Extract memory IDs
        memory_ids = [self._get_memory_id(memory) for memory in memories]
        
        # Select primary memory based on merge strategy
        primary_memory_id = self._select_primary_memory(
            memories, 
            config.merge_strategy.value
        )
        
        # Create similarity scores (1.0 for exact matches)
        similarity_scores = []
        
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                memory1, memory2 = memories[i], memories[j]
                
                # Calculate metadata similarity
                metadata_similarity = self._calculate_metadata_similarity(memory1, memory2)
                
                # Create similarity score
                similarity_score = SimilarityScore(
                    memory_id_1=memory_ids[i],
                    memory_id_2=memory_ids[j],
                    content_similarity=1.0,  # Exact match
                    metadata_similarity=metadata_similarity,
                    structural_similarity=1.0,  # Identical structure
                    overall_similarity=1.0,  # Perfect match
                    method_used=SimilarityMethod.EXACT_MATCH,
                    confidence=1.0,  # Maximum confidence for exact matches
                    reasoning=f"Exact content match (hash: {content_hash[:8]})"
                )
                
                similarity_scores.append(similarity_score)
                self._record_comparison(1.0, from_cache=False)
        
        # Create duplicate group
        group_id = f"exact_{content_hash[:12]}_{len(memories)}"
        
        duplicate_group = DuplicateGroup(
            group_id=group_id,
            memory_ids=memory_ids,
            primary_memory_id=primary_memory_id,
            similarity_scores=similarity_scores,
            merge_strategy=config.merge_strategy,
            confidence_score=1.0,  # Maximum confidence for exact matches
            detected_by=self.get_detector_name()
        )
        
        return duplicate_group
    
    def _extract_content(self, memory: Dict[str, Any]) -> str:
        """
        Extract and normalize content from memory for comparison.
        
        Args:
            memory: Memory dictionary
            
        Returns:
            Normalized content string
        """
        content = memory.get("content", "")
        if not isinstance(content, str):
            return ""
        
        # Normalize content by stripping whitespace and converting to lowercase
        # This catches minor formatting differences while maintaining exactness
        return content.strip()
    
    def _hash_content(self, content: str) -> str:
        """
        Generate MD5 hash of content.
        
        Args:
            content: Content string to hash
            
        Returns:
            MD5 hash string
        """
        if not content:
            return "empty_content"
        
        try:
            return hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()
        except Exception as e:
            logger.warning(f"Error hashing content: {e}")
            return f"hash_error_{hash(content)}"
    
    def _get_memory_id(self, memory: Dict[str, Any]) -> str:
        """
        Get memory ID, generating one if missing.
        
        Args:
            memory: Memory dictionary
            
        Returns:
            Memory ID string
        """
        memory_id = memory.get("id")
        if memory_id:
            return str(memory_id)
        
        # Generate ID from content hash if missing
        content = self._extract_content(memory)
        content_hash = self._hash_content(content)
        return f"generated_{content_hash[:16]}"
    
    async def find_incremental_duplicates(
        self, 
        new_memories: List[Dict[str, Any]], 
        existing_hashes: Dict[str, str],
        config: DeduplicationConfig
    ) -> List[DuplicateGroup]:
        """
        Find duplicates incrementally by comparing new memories against existing hashes.
        
        Args:
            new_memories: New memories to check for duplicates
            existing_hashes: Map of existing memory IDs to content hashes
            config: Deduplication configuration
            
        Returns:
            List of duplicate groups found
        """
        if not new_memories or not existing_hashes:
            return []
        
        logger.debug(f"Incremental exact match detection: {len(new_memories)} new vs {len(existing_hashes)} existing")
        
        duplicate_groups = []
        hash_to_memories = defaultdict(list)
        
        # Add existing memories to hash map (as placeholders)
        for memory_id, content_hash in existing_hashes.items():
            hash_to_memories[content_hash].append({"id": memory_id, "content": None})
        
        # Process new memories
        for memory in new_memories:
            content = self._extract_content(memory)
            if not content:
                continue
                
            content_hash = self._hash_content(content)
            hash_to_memories[content_hash].append(memory)
        
        # Find groups with duplicates (new + existing)
        for content_hash, memory_group in hash_to_memories.items():
            if len(memory_group) <= 1:
                continue
            
            # Filter out placeholder entries and include both new and existing
            actual_memories = [m for m in memory_group if m.get("content") is not None]
            if len(actual_memories) < len(memory_group):
                # We have duplicates with existing memories
                try:
                    group = await self._create_duplicate_group(
                        actual_memories, 
                        content_hash, 
                        config
                    )
                    if group:
                        duplicate_groups.append(group)
                        self._record_duplicate_found()
                        
                except Exception as e:
                    logger.error(f"Error creating incremental duplicate group: {e}")
                    continue
        
        logger.info(f"Incremental exact match detection completed: {len(duplicate_groups)} groups found")
        return duplicate_groups
    
    def get_content_hash(self, memory_id: str) -> str:
        """
        Get cached content hash for a memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Content hash or empty string if not found
        """
        return self.content_hashes.get(memory_id, "")
    
    def clear_cache(self) -> None:
        """Clear all cached hashes and similarities."""
        self.content_hashes.clear()
        self.similarity_cache.clear()
        logger.debug("Exact match detector cache cleared")
