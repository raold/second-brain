#!/usr/bin/env python3
"""
Similarity Analyzers - Memory Relationship Calculations

Focused module for calculating different types of similarity between memories.
Extracted from memory_relationships.py as part of Phase 1: Emergency Stabilization.

Key improvements:
- Fixed method signatures (no longer requiring full memory objects)
- Added comprehensive error handling and input validation
- Separated concerns (pure calculation functions)
- Made fully testable with mock data
"""

import logging
import math
import re
from datetime import datetime
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class SimilarityAnalyzers:
    """Collection of similarity calculation methods for memory relationships."""

    def __init__(self, temporal_window_hours: float = 24.0):
        """Initialize similarity analyzers.

        Args:
            temporal_window_hours: Time window for temporal proximity calculation
        """
        self.temporal_window_hours = temporal_window_hours

    def calculate_semantic_similarity(
        self, embedding1: Optional[list[float]], embedding2: Optional[list[float]]
    ) -> float:
        """Calculate semantic similarity using embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if not embedding1 or not embedding2:
            logger.debug("Missing embeddings for similarity calculation")
            return 0.0

        try:
            # Validate embedding dimensions
            if len(embedding1) != len(embedding2):
                logger.warning(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
                return 0.0

            # Convert to numpy for calculation
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                logger.debug("Zero norm embedding encountered")
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure result is in valid range [0, 1]
            similarity = max(0.0, min(1.0, float(similarity)))

            return similarity

        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0

    def calculate_temporal_proximity(self, created_at1: Optional[datetime], created_at2: Optional[datetime]) -> float:
        """Calculate temporal proximity score between two timestamps.

        Args:
            created_at1: First timestamp
            created_at2: Second timestamp

        Returns:
            Temporal proximity score (0.0 to 1.0)
        """
        if not created_at1 or not created_at2:
            logger.debug("Missing timestamps for temporal proximity calculation")
            return 0.0

        try:
            # Calculate time difference in hours
            time_diff = abs((created_at1 - created_at2).total_seconds()) / 3600

            # Exponential decay with configurable window
            proximity = math.exp(-time_diff / self.temporal_window_hours)

            return max(0.0, min(1.0, proximity))

        except Exception as e:
            logger.warning(f"Temporal proximity calculation failed: {e}")
            return 0.0

    def calculate_content_overlap(self, content1: Optional[str], content2: Optional[str]) -> float:
        """Calculate content overlap using Jaccard similarity.

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            Jaccard similarity score (0.0 to 1.0)
        """
        if not content1 or not content2:
            logger.debug("Missing content for overlap calculation")
            return 0.0

        try:
            # Normalize and tokenize content
            words1 = set(self._tokenize_content(content1.lower()))
            words2 = set(self._tokenize_content(content2.lower()))

            if not words1 or not words2:
                return 0.0

            # Calculate Jaccard similarity
            intersection = len(words1 & words2)
            union = len(words1 | words2)

            jaccard_similarity = intersection / union if union > 0 else 0.0

            return max(0.0, min(1.0, jaccard_similarity))

        except Exception as e:
            logger.warning(f"Content overlap calculation failed: {e}")
            return 0.0

    def calculate_conceptual_hierarchy(self, content1: Optional[str], content2: Optional[str]) -> float:
        """Detect hierarchical relationships (parent-child, general-specific).

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            Hierarchy relationship score (0.0 to 1.0)
        """
        if not content1 or not content2:
            return 0.0

        try:
            content1_lower = content1.lower()
            content2_lower = content2.lower()

            hierarchy_score = 0.0

            # Check for hierarchical indicators
            hierarchy_patterns = [
                (r"\bdefinition\b", r"\bexample\b"),
                (r"\bconcept\b", r"\binstance\b"),
                (r"\bgeneral\b", r"\bspecific\b"),
                (r"\bcategory\b", r"\bitem\b"),
                (r"\boverview\b", r"\bdetail\b"),
                (r"\bsummary\b", r"\belaboration\b"),
            ]

            for parent_pattern, child_pattern in hierarchy_patterns:
                if re.search(parent_pattern, content1_lower) and re.search(child_pattern, content2_lower):
                    hierarchy_score += 0.3
                elif re.search(child_pattern, content1_lower) and re.search(parent_pattern, content2_lower):
                    hierarchy_score += 0.3

            # Check for length-based hierarchy (shorter content might be more general)
            length_ratio = min(len(content1), len(content2)) / max(len(content1), len(content2))
            if length_ratio < 0.5:  # Significant length difference
                hierarchy_score += 0.2

            return max(0.0, min(1.0, hierarchy_score))

        except Exception as e:
            logger.warning(f"Conceptual hierarchy calculation failed: {e}")
            return 0.0

    def detect_causal_relationship(
        self,
        content1: Optional[str],
        content2: Optional[str],
        created_at1: Optional[datetime] = None,
        created_at2: Optional[datetime] = None,
    ) -> float:
        """Detect potential causal relationships between memories.

        Args:
            content1: First content string
            content2: Second content string
            created_at1: Optional first timestamp
            created_at2: Optional second timestamp

        Returns:
            Causal relationship score (0.0 to 1.0)
        """
        if not content1 or not content2:
            return 0.0

        try:
            content1_lower = content1.lower()
            content2_lower = content2.lower()

            causal_score = 0.0

            # Causal indicator words and phrases
            causal_patterns = [
                r"\bbecause\b",
                r"\bdue to\b",
                r"\bcaused by\b",
                r"\bresults in\b",
                r"\bleads to\b",
                r"\btriggers\b",
                r"\benables\b",
                r"\bprevents\b",
                r"\binfluences\b",
                r"\baffects\b",
                r"\btherefore\b",
                r"\bconsequently\b",
                r"\bas a result\b",
                r"\bthus\b",
            ]

            # Check for causal language in either content
            for pattern in causal_patterns:
                if re.search(pattern, content1_lower) or re.search(pattern, content2_lower):
                    causal_score += 0.2

            # Temporal ordering can indicate causality
            if created_at1 and created_at2:
                if created_at1 < created_at2:
                    causal_score += 0.1  # content1 might be cause of content2
                elif created_at2 < created_at1:
                    causal_score += 0.1  # content2 might be cause of content1

            return max(0.0, min(1.0, causal_score))

        except Exception as e:
            logger.warning(f"Causal relationship detection failed: {e}")
            return 0.0

    def calculate_contextual_association(
        self,
        metadata1: Optional[dict[str, Any]],
        metadata2: Optional[dict[str, Any]],
        memory_type1: Optional[str] = None,
        memory_type2: Optional[str] = None,
        importance1: Optional[float] = None,
        importance2: Optional[float] = None,
    ) -> float:
        """Calculate contextual association based on metadata and properties.

        Args:
            metadata1: First memory's metadata
            metadata2: Second memory's metadata
            memory_type1: First memory's type
            memory_type2: Second memory's type
            importance1: First memory's importance score
            importance2: Second memory's importance score

        Returns:
            Contextual association score (0.0 to 1.0)
        """
        try:
            association_score = 0.0

            # Check metadata overlap
            if metadata1 and metadata2:
                metadata_fields = ["semantic_metadata", "episodic_metadata", "procedural_metadata"]

                for field in metadata_fields:
                    meta1 = metadata1.get(field, {}) or {}
                    meta2 = metadata2.get(field, {}) or {}

                    if isinstance(meta1, dict) and isinstance(meta2, dict):
                        common_keys = set(meta1.keys()) & set(meta2.keys())
                        total_keys = set(meta1.keys()) | set(meta2.keys())

                        if common_keys and total_keys:
                            overlap_ratio = len(common_keys) / len(total_keys)
                            association_score += 0.3 * overlap_ratio

            # Memory type similarity
            if memory_type1 and memory_type2 and memory_type1 == memory_type2:
                association_score += 0.2

            # Importance correlation
            if importance1 is not None and importance2 is not None:
                importance_diff = abs(importance1 - importance2)
                importance_similarity = 1.0 - importance_diff  # Assumes scores 0-1
                association_score += 0.2 * max(0.0, importance_similarity)

            return max(0.0, min(1.0, association_score))

        except Exception as e:
            logger.warning(f"Contextual association calculation failed: {e}")
            return 0.0

    def _tokenize_content(self, content: str) -> list[str]:
        """Tokenize content for overlap analysis.

        Args:
            content: Text content to tokenize

        Returns:
            List of meaningful tokens
        """
        if not content:
            return []

        try:
            # Simple tokenization - remove punctuation and split
            # Remove common stop words for better similarity
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "is",
                "are",
                "was",
                "were",
            }

            # Extract meaningful words (alphanumeric, length > 2)
            words = re.findall(r"\b\w{3,}\b", content.lower())

            # Filter out stop words
            meaningful_words = [word for word in words if word not in stop_words]

            return meaningful_words

        except Exception as e:
            logger.warning(f"Content tokenization failed: {e}")
            return []


def calculate_composite_score(relationship_scores: dict[str, float]) -> float:
    """Calculate weighted composite relationship score.

    Args:
        relationship_scores: Dictionary of relationship type -> score

    Returns:
        Weighted composite score (0.0 to 1.0)
    """
    if not relationship_scores:
        return 0.0

    try:
        # Weights for different relationship types
        default_weights = {
            "semantic_similarity": 0.4,
            "temporal_proximity": 0.2,
            "content_overlap": 0.2,
            "conceptual_hierarchy": 0.1,
            "causal_relationship": 0.05,
            "contextual_association": 0.05,
        }

        total_weighted_score = 0.0
        total_weights = 0.0

        for rel_type, score in relationship_scores.items():
            weight = default_weights.get(rel_type, 0.1)  # Default weight for unknown types
            total_weighted_score += score * weight
            total_weights += weight

        # Normalize by total weights used
        composite_score = total_weighted_score / total_weights if total_weights > 0 else 0.0

        return max(0.0, min(1.0, composite_score))

    except Exception as e:
        logger.warning(f"Composite score calculation failed: {e}")
        return 0.0


def categorize_relationship_strength(composite_score: float) -> str:
    """Categorize relationship strength based on composite score.

    Args:
        composite_score: Composite relationship score

    Returns:
        Strength category string
    """
    if composite_score >= 0.8:
        return "very_strong"
    elif composite_score >= 0.6:
        return "strong"
    elif composite_score >= 0.4:
        return "moderate"
    elif composite_score >= 0.2:
        return "weak"
    else:
        return "very_weak"
