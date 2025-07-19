"""
Hybrid Detector

Combines multiple detection methods for comprehensive duplicate detection.
Intelligently weights and combines results from exact, fuzzy, and semantic detection.
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from app.interfaces.duplicate_detector_interface import BaseDuplicateDetector
from app.services.duplicate_detectors.exact_match_detector import ExactMatchDetector
from app.services.duplicate_detectors.fuzzy_match_detector import FuzzyMatchDetector
from app.services.duplicate_detectors.semantic_similarity_detector import SemanticSimilarityDetector
from app.models.deduplication_models import (
    DuplicateGroup,
    DeduplicationConfig,
    SimilarityMethod,
    SimilarityScore,
    DetectionStats
)

logger = logging.getLogger(__name__)


class HybridDetector(BaseDuplicateDetector):
    """Hybrid detector combining exact, fuzzy, and semantic similarity methods."""
    
    def __init__(self, cache_enabled: bool = True, embedding_service=None):
        """
        Initialize hybrid detector with all detection methods.
        
        Args:
            cache_enabled: Whether to enable similarity score caching
            embedding_service: Service for semantic embeddings (optional)
        """
        super().__init__(cache_enabled)
        
        # Initialize individual detectors
        self.exact_detector = ExactMatchDetector(cache_enabled)
        self.fuzzy_detector = FuzzyMatchDetector(cache_enabled)
        self.semantic_detector = SemanticSimilarityDetector(cache_enabled, embedding_service)
        
        # Detection method weights for combining results
        self.method_weights = {
            SimilarityMethod.EXACT_MATCH: 1.0,      # Highest weight for exact matches
            SimilarityMethod.FUZZY_MATCH: 0.8,      # High weight for fuzzy matches
            SimilarityMethod.SEMANTIC_SIMILARITY: 0.7  # Moderate weight for semantic
        }
        
        # Statistics for each method
        self.detection_stats: Dict[SimilarityMethod, DetectionStats] = {}
    
    def get_detector_name(self) -> str:
        """Get detector name."""
        return "Hybrid Detector (Exact + Fuzzy + Semantic)"
    
    def get_similarity_method(self) -> SimilarityMethod:
        """Get similarity method."""
        return SimilarityMethod.HYBRID
    
    def get_optimal_batch_size(self) -> int:
        """Hybrid processing requires balanced batch size."""
        return 100
    
    def supports_incremental_detection(self) -> bool:
        """Hybrid supports incremental detection if all methods support it."""
        return (self.exact_detector.supports_incremental_detection() and
                self.semantic_detector.supports_incremental_detection())
    
    async def _find_duplicates_impl(
        self, 
        memories: List[Dict[str, Any]], 
        config: DeduplicationConfig
    ) -> List[DuplicateGroup]:
        """
        Find duplicates using hybrid approach combining multiple methods.
        
        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration
            
        Returns:
            List of duplicate groups found through combined methods
        """
        if not memories:
            return []
        
        logger.debug(f"Starting hybrid detection on {len(memories)} memories")
        
        # Determine which methods to use based on configuration
        methods_to_use = config.get_detection_methods()
        
        # Run detection methods in parallel
        detection_results = await self._run_parallel_detection(memories, config, methods_to_use)
        
        # Combine and merge results from different methods
        combined_groups = await self._combine_detection_results(
            detection_results, 
            memories, 
            config
        )
        
        logger.info(f"Hybrid detection completed: {len(combined_groups)} groups found")
        return combined_groups
    
    async def _run_parallel_detection(
        self, 
        memories: List[Dict[str, Any]], 
        config: DeduplicationConfig,
        methods: List[SimilarityMethod]
    ) -> Dict[SimilarityMethod, List[DuplicateGroup]]:
        """
        Run multiple detection methods in parallel.
        
        Args:
            memories: List of memory dictionaries
            config: Deduplication configuration
            methods: List of methods to run
            
        Returns:
            Map of methods to their detection results
        """
        detection_tasks = []
        method_to_detector = {}
        
        for method in methods:
            if method == SimilarityMethod.EXACT_MATCH:
                detector = self.exact_detector
            elif method == SimilarityMethod.FUZZY_MATCH:
                detector = self.fuzzy_detector
            elif method == SimilarityMethod.SEMANTIC_SIMILARITY:
                detector = self.semantic_detector
            else:
                continue
            
            method_to_detector[method] = detector
            task = asyncio.create_task(
                detector.find_duplicates(memories, config),
                name=f"detect_{method.value}"
            )
            detection_tasks.append((method, task))
        
        # Wait for all detection methods to complete
        results = {}
        for method, task in detection_tasks:
            try:
                groups = await task
                results[method] = groups
                
                # Store statistics
                detector = method_to_detector[method]
                if hasattr(detector, '_get_detection_stats'):
                    self.detection_stats[method] = detector._get_detection_stats()
                
                logger.debug(f"{method.value} detection found {len(groups)} groups")
                
            except Exception as e:
                logger.error(f"Error in {method.value} detection: {e}")
                results[method] = []
        
        return results
    
    async def _combine_detection_results(
        self,
        detection_results: Dict[SimilarityMethod, List[DuplicateGroup]],
        memories: List[Dict[str, Any]],
        config: DeduplicationConfig
    ) -> List[DuplicateGroup]:
        """
        Combine results from multiple detection methods intelligently.
        
        Args:
            detection_results: Results from each detection method
            memories: Original memory list
            config: Deduplication configuration
            
        Returns:
            Combined and merged duplicate groups
        """
        if not detection_results:
            return []
        
        # Create memory ID to memory map for quick lookup
        memory_map = {mem.get('id'): mem for mem in memories}
        
        # Collect all unique memory pairs with their detection methods and scores
        pair_detections = defaultdict(list)
        
        for method, groups in detection_results.items():
            for group in groups:
                for score in group.similarity_scores:
                    pair_key = tuple(sorted([score.memory_id_1, score.memory_id_2]))
                    pair_detections[pair_key].append({
                        'method': method,
                        'score': score,
                        'weight': self.method_weights.get(method, 0.5)
                    })
        
        # Calculate combined scores for each pair
        combined_pairs = []
        for pair_key, detections in pair_detections.items():
            combined_score = self._calculate_combined_score(detections, config)
            
            if combined_score.overall_similarity >= config.similarity_threshold:
                mem1 = memory_map.get(pair_key[0])
                mem2 = memory_map.get(pair_key[1])
                if mem1 and mem2:
                    combined_pairs.append((mem1, mem2, combined_score))
        
        # Group combined pairs into duplicate groups
        if combined_pairs:
            combined_groups = self._group_combined_pairs(combined_pairs, config)
            return combined_groups
        
        return []
    
    def _calculate_combined_score(
        self, 
        detections: List[Dict[str, Any]], 
        config: DeduplicationConfig
    ) -> SimilarityScore:
        """
        Calculate combined similarity score from multiple detection methods.
        
        Args:
            detections: List of detection results for a memory pair
            config: Deduplication configuration
            
        Returns:
            Combined SimilarityScore
        """
        if not detections:
            return None
        
        # Get base information from first detection
        first_detection = detections[0]
        base_score = first_detection['score']
        
        # Calculate weighted averages
        weighted_content_sum = 0.0
        weighted_metadata_sum = 0.0
        weighted_structural_sum = 0.0
        weighted_confidence_sum = 0.0
        total_weight = 0.0
        
        methods_used = []
        reasoning_parts = []
        
        for detection in detections:
            score = detection['score']
            weight = detection['weight']
            method = detection['method']
            
            weighted_content_sum += score.content_similarity * weight
            weighted_metadata_sum += score.metadata_similarity * weight
            weighted_structural_sum += score.structural_similarity * weight
            weighted_confidence_sum += score.confidence * weight
            total_weight += weight
            
            methods_used.append(method)
            reasoning_parts.append(f"{method.value}({score.overall_similarity:.3f})")
        
        # Calculate averages
        if total_weight > 0:
            avg_content = weighted_content_sum / total_weight
            avg_metadata = weighted_metadata_sum / total_weight
            avg_structural = weighted_structural_sum / total_weight
            avg_confidence = weighted_confidence_sum / total_weight
        else:
            avg_content = avg_metadata = avg_structural = avg_confidence = 0.0
        
        # Calculate overall similarity using configuration weights
        overall_similarity = (
            config.content_weight * avg_content +
            config.metadata_weight * avg_metadata +
            config.structural_weight * avg_structural
        )
        
        # Boost score if multiple methods agree (consensus bonus)
        if len(methods_used) > 1:
            consensus_bonus = min(0.1, 0.02 * len(methods_used))
            overall_similarity = min(1.0, overall_similarity + consensus_bonus)
            avg_confidence = min(1.0, avg_confidence + consensus_bonus)
        
        # Create combined similarity score
        combined_score = SimilarityScore(
            memory_id_1=base_score.memory_id_1,
            memory_id_2=base_score.memory_id_2,
            content_similarity=avg_content,
            metadata_similarity=avg_metadata,
            structural_similarity=avg_structural,
            overall_similarity=overall_similarity,
            method_used=SimilarityMethod.HYBRID,
            confidence=avg_confidence,
            reasoning=f"Hybrid detection: {', '.join(reasoning_parts)}"
        )
        
        return combined_score
    
    def _group_combined_pairs(
        self, 
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any], SimilarityScore]], 
        config: DeduplicationConfig
    ) -> List[DuplicateGroup]:
        """
        Group combined pairs into duplicate groups.
        
        Args:
            pairs: List of memory pairs with combined scores
            config: Deduplication configuration
            
        Returns:
            List of duplicate groups
        """
        # Build adjacency map for graph clustering
        adjacency_map = defaultdict(set)
        pair_scores = {}
        
        for mem1, mem2, score in pairs:
            mem1_id = mem1.get('id')
            mem2_id = mem2.get('id')
            
            adjacency_map[mem1_id].add(mem2_id)
            adjacency_map[mem2_id].add(mem1_id)
            pair_scores[(mem1_id, mem2_id)] = score
            pair_scores[(mem2_id, mem1_id)] = score
        
        # Find connected components using DFS
        visited = set()
        duplicate_groups = []
        
        for mem1, mem2, _ in pairs:
            mem1_id = mem1.get('id')
            
            if mem1_id in visited:
                continue
            
            # Find connected component
            group_memory_ids = set()
            stack = [mem1_id]
            
            while stack:
                current_id = stack.pop()
                if current_id in visited:
                    continue
                
                visited.add(current_id)
                group_memory_ids.add(current_id)
                
                # Add connected memories
                for connected_id in adjacency_map[current_id]:
                    if connected_id not in visited:
                        stack.append(connected_id)
            
            if len(group_memory_ids) >= 2:
                group = self._create_hybrid_duplicate_group(
                    group_memory_ids,
                    pair_scores,
                    pairs,
                    config
                )
                if group:
                    duplicate_groups.append(group)
                    self._record_duplicate_found()
        
        return duplicate_groups
    
    def _create_hybrid_duplicate_group(
        self,
        memory_ids: Set[str],
        pair_scores: Dict[Tuple[str, str], SimilarityScore],
        original_pairs: List[Tuple[Dict[str, Any], Dict[str, Any], SimilarityScore]],
        config: DeduplicationConfig
    ) -> DuplicateGroup:
        """
        Create a hybrid duplicate group.
        
        Args:
            memory_ids: Set of memory IDs in the group
            pair_scores: Map of pairwise similarity scores
            original_pairs: Original pair data
            config: Deduplication configuration
            
        Returns:
            Hybrid DuplicateGroup
        """
        if len(memory_ids) < 2:
            return None
        
        # Get memory objects
        id_to_memory = {}
        for mem1, mem2, _ in original_pairs:
            id_to_memory[mem1.get('id')] = mem1
            id_to_memory[mem2.get('id')] = mem2
        
        group_memories = [id_to_memory[mid] for mid in memory_ids if mid in id_to_memory]
        
        if len(group_memories) < 2:
            return None
        
        # Select primary memory using configured strategy
        primary_memory_id = self._select_primary_memory(
            group_memories, 
            config.merge_strategy.value
        )
        
        # Collect similarity scores for all pairs in the group
        similarity_scores = []
        memory_ids_list = list(memory_ids)
        
        for i in range(len(memory_ids_list)):
            for j in range(i + 1, len(memory_ids_list)):
                id1, id2 = memory_ids_list[i], memory_ids_list[j]
                score = pair_scores.get((id1, id2))
                
                if score:
                    similarity_scores.append(score)
        
        # Calculate group confidence as average of all similarity scores
        group_confidence = (
            sum(score.overall_similarity for score in similarity_scores) / len(similarity_scores)
            if similarity_scores else 0.0
        )
        
        # Create group ID
        group_id = f"hybrid_{hash(''.join(sorted(memory_ids)))}"[-12:]
        
        # Create the hybrid duplicate group
        duplicate_group = DuplicateGroup(
            group_id=f"hybrid_{group_id}_{len(memory_ids)}",
            memory_ids=list(memory_ids),
            primary_memory_id=primary_memory_id,
            similarity_scores=similarity_scores,
            merge_strategy=config.merge_strategy,
            confidence_score=group_confidence,
            detected_by=self.get_detector_name()
        )
        
        return duplicate_group
    
    def get_detection_statistics(self) -> Dict[SimilarityMethod, DetectionStats]:
        """
        Get detection statistics for all methods.
        
        Returns:
            Map of methods to their detection statistics
        """
        return self.detection_stats.copy()
    
    def clear_all_caches(self) -> None:
        """Clear caches for all detection methods."""
        self.exact_detector.clear_cache()
        self.fuzzy_detector.clear_cache() if hasattr(self.fuzzy_detector, 'clear_cache') else None
        self.semantic_detector.clear_cache()
        self.similarity_cache.clear()
        logger.debug("All hybrid detector caches cleared")
    
    def update_method_weights(self, weights: Dict[SimilarityMethod, float]) -> None:
        """
        Update weights for combining detection methods.
        
        Args:
            weights: New weights for each method
        """
        for method, weight in weights.items():
            if method in self.method_weights and 0.0 <= weight <= 1.0:
                self.method_weights[method] = weight
        
        logger.debug(f"Updated method weights: {self.method_weights}")
    
    async def validate_configuration(self, config: DeduplicationConfig) -> List[str]:
        """
        Validate configuration for hybrid detection.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate that similarity method is hybrid or compatible
        if config.similarity_method != SimilarityMethod.HYBRID:
            errors.append("Hybrid detector requires similarity_method to be HYBRID")
        
        # Validate weights sum approximately to 1.0
        if not config.validate_weights():
            errors.append("Similarity weights must sum to approximately 1.0")
        
        # Validate threshold is reasonable
        if config.similarity_threshold > 0.95:
            errors.append("Similarity threshold too high for hybrid detection")
        
        # Validate individual detector configurations
        if config.enable_fuzzy_matching and config.fuzzy_threshold < config.similarity_threshold:
            errors.append("Fuzzy threshold should be >= similarity threshold")
        
        return errors
