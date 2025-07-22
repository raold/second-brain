#!/usr/bin/env python3
"""
Advanced Batch Classification Engine
Enhanced classification algorithms with performance optimization and intelligent batching
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.database_mock import get_mock_database


class ClassificationMethod(str, Enum):
    """Classification methods available"""

    KEYWORD_BASED = "keyword_based"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    PATTERN_MATCHING = "pattern_matching"
    MACHINE_LEARNING = "machine_learning"
    HYBRID = "hybrid"
    RULE_BASED = "rule_based"


class BatchMode(str, Enum):
    """Batch processing modes"""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    SMART_BATCHING = "smart_batching"


@dataclass
class ClassificationRule:
    """Classification rule definition"""

    rule_id: str
    name: str
    description: str
    target_type: str
    patterns: list[str]
    keywords: list[str]
    conditions: dict[str, Any]
    confidence_threshold: float = 0.7
    priority: int = 1  # Higher number = higher priority


@dataclass
class ClassificationResult:
    """Result of classification operation"""

    memory_id: str
    original_type: str | None
    predicted_type: str
    confidence: float
    method_used: ClassificationMethod
    reasoning: str
    processing_time: float
    metadata_updates: dict[str, Any]


@dataclass
class BatchClassificationResult:
    """Result of batch classification operation"""

    batch_id: str
    total_memories: int
    processed_memories: int
    successful_classifications: int
    failed_classifications: int
    classification_results: list[ClassificationResult]
    processing_time: float
    performance_metrics: dict[str, Any]
    errors: list[str]
    warnings: list[str]


class ClassificationConfig(BaseModel):
    """Configuration for batch classification"""

    method: ClassificationMethod = Field(ClassificationMethod.HYBRID, description="Classification method to use")
    batch_size: int = Field(50, description="Number of memories to process per batch")
    parallel_workers: int = Field(4, description="Number of parallel workers")
    confidence_threshold: float = Field(0.6, description="Minimum confidence for classification")
    enable_caching: bool = Field(True, description="Enable result caching")
    cache_duration: int = Field(3600, description="Cache duration in seconds")
    auto_apply_results: bool = Field(False, description="Automatically apply classification results")
    backup_before_apply: bool = Field(True, description="Create backup before applying changes")
    validation_enabled: bool = Field(True, description="Enable result validation")
    max_retries: int = Field(3, description="Maximum retries for failed classifications")


class SemanticClassifier:
    """Semantic-based memory classifier"""

    def __init__(self):
        self.memory_type_embeddings = {}
        self.classification_cache = {}

    async def classify_memory(self, memory: dict[str, Any]) -> tuple[str, float, str]:
        """Classify memory using semantic similarity"""
        content = memory.get("content", "")

        # Simple semantic classification based on content patterns
        # In a real implementation, this would use embeddings and similarity

        semantic_patterns = {
            "semantic": [
                "fact",
                "information",
                "knowledge",
                "definition",
                "concept",
                "theory",
                "principle",
                "rule",
                "law",
                "formula",
            ],
            "episodic": [
                "remember",
                "yesterday",
                "today",
                "meeting",
                "event",
                "happened",
                "experience",
                "encounter",
                "situation",
                "moment",
                "time when",
            ],
            "procedural": [
                "how to",
                "step by step",
                "process",
                "procedure",
                "method",
                "technique",
                "algorithm",
                "workflow",
                "instructions",
                "guide",
            ],
        }

        content_lower = content.lower()
        scores = {}

        for memory_type, patterns in semantic_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in content_lower:
                    score += 1

            # Normalize score
            scores[memory_type] = score / len(patterns) if patterns else 0

        # Find best match
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]

        # Add some randomness to simulate more sophisticated classification
        if confidence < 0.1:
            confidence = 0.3  # Minimum confidence

        reasoning = f"Semantic analysis found {sum(1 for p in semantic_patterns[best_type] if p in content_lower)} relevant patterns"

        return best_type, confidence, reasoning


class KeywordClassifier:
    """Keyword-based memory classifier"""

    def __init__(self):
        self.keyword_rules = self._initialize_keyword_rules()

    def _initialize_keyword_rules(self) -> list[ClassificationRule]:
        """Initialize default keyword classification rules"""
        return [
            ClassificationRule(
                rule_id="semantic_keywords",
                name="Semantic Knowledge Keywords",
                description="Keywords indicating semantic/factual memory",
                target_type="semantic",
                patterns=["is defined as", "means that", "refers to"],
                keywords=["fact", "definition", "concept", "theory", "principle"],
                conditions={"min_keywords": 1},
                confidence_threshold=0.8,
                priority=2,
            ),
            ClassificationRule(
                rule_id="episodic_keywords",
                name="Episodic Memory Keywords",
                description="Keywords indicating episodic/experiential memory",
                target_type="episodic",
                patterns=["I remember", "yesterday", "last week", "when I"],
                keywords=["remember", "experience", "event", "meeting", "happened"],
                conditions={"min_keywords": 1},
                confidence_threshold=0.7,
                priority=2,
            ),
            ClassificationRule(
                rule_id="procedural_keywords",
                name="Procedural Knowledge Keywords",
                description="Keywords indicating procedural memory",
                target_type="procedural",
                patterns=["how to", "step 1", "first,", "then,", "finally"],
                keywords=["process", "procedure", "method", "steps", "instructions"],
                conditions={"min_keywords": 1},
                confidence_threshold=0.8,
                priority=3,
            ),
        ]

    async def classify_memory(self, memory: dict[str, Any]) -> tuple[str, float, str]:
        """Classify memory using keyword matching"""
        content = memory.get("content", "").lower()
        memory.get("metadata", {})

        rule_scores = []

        for rule in self.keyword_rules:
            score = 0
            matched_items = []

            # Check patterns
            for pattern in rule.patterns:
                if pattern.lower() in content:
                    score += 0.3
                    matched_items.append(f"pattern '{pattern}'")

            # Check keywords
            for keyword in rule.keywords:
                if keyword.lower() in content:
                    score += 0.2
                    matched_items.append(f"keyword '{keyword}'")

            # Check conditions
            if rule.conditions.get("min_keywords", 0) <= len([k for k in rule.keywords if k.lower() in content]):
                score += 0.1

            # Apply priority weight
            score *= rule.priority

            if score >= rule.confidence_threshold:
                rule_scores.append((rule, score, matched_items))

        if rule_scores:
            # Sort by score and priority
            rule_scores.sort(key=lambda x: (x[1], x[0].priority), reverse=True)
            best_rule, confidence, matched_items = rule_scores[0]

            reasoning = f"Matched {len(matched_items)} items: {', '.join(matched_items[:3])}"
            return best_rule.target_type, min(confidence, 1.0), reasoning

        # Default classification
        return "semantic", 0.3, "No specific patterns found, defaulting to semantic"


class PatternClassifier:
    """Pattern-based memory classifier"""

    def __init__(self):
        self.content_patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> dict[str, list[str]]:
        """Initialize content patterns for classification"""
        return {
            "semantic": [
                r"\b\w+ is (a|an) \w+",  # "X is a Y" definitions
                r"\b\w+ means \w+",  # "X means Y"
                r"according to \w+",  # Citations
                r"\d+(\.\d+)?%",  # Statistics
                r"\bin \d{4}\b",  # Years
            ],
            "episodic": [
                r"\b(yesterday|today|tomorrow)\b",  # Time references
                r"\b(I|we) (went|did|saw|met)\b",  # Personal actions
                r"\bat \d{1,2}:\d{2}\b",  # Time stamps
                r"\bon (monday|tuesday|wednesday|thursday|friday|saturday|sunday)",  # Days
                r"\b(remember|recall) (when|that)\b",  # Memory triggers
            ],
            "procedural": [
                r"\bstep \d+\b",  # Step numbers
                r"\b(first|second|third|then|next|finally)\b",  # Sequence words
                r"\b(click|press|type|select)\b",  # Action verbs
                r"\bhow to \w+",  # How-to patterns
                r"\b(if|when|while) \w+, (then|do)",  # Conditional instructions
            ],
        }

    async def classify_memory(self, memory: dict[str, Any]) -> tuple[str, float, str]:
        """Classify memory using pattern matching"""
        import re

        content = memory.get("content", "")
        pattern_scores = {}
        matched_patterns = {}

        for memory_type, patterns in self.content_patterns.items():
            score = 0
            matches = []

            for pattern in patterns:
                pattern_matches = re.findall(pattern, content, re.IGNORECASE)
                if pattern_matches:
                    score += len(pattern_matches) * 0.2
                    matches.extend(pattern_matches[:2])  # Limit matches per pattern

            pattern_scores[memory_type] = min(score, 1.0)  # Cap at 1.0
            matched_patterns[memory_type] = matches

        if pattern_scores:
            best_type = max(pattern_scores, key=pattern_scores.get)
            confidence = pattern_scores[best_type]

            if confidence > 0:
                matches = matched_patterns[best_type]
                reasoning = f"Pattern analysis found {len(matches)} matches"
                return best_type, confidence, reasoning

        return "semantic", 0.2, "No significant patterns found"


class HybridClassifier:
    """Hybrid classifier combining multiple methods"""

    def __init__(self):
        self.semantic_classifier = SemanticClassifier()
        self.keyword_classifier = KeywordClassifier()
        self.pattern_classifier = PatternClassifier()

        # Weights for combining different methods
        self.method_weights = {"semantic": 0.4, "keyword": 0.4, "pattern": 0.2}

    async def classify_memory(self, memory: dict[str, Any]) -> tuple[str, float, str]:
        """Classify memory using hybrid approach"""
        # Get results from all classifiers
        semantic_result = await self.semantic_classifier.classify_memory(memory)
        keyword_result = await self.keyword_classifier.classify_memory(memory)
        pattern_result = await self.pattern_classifier.classify_memory(memory)

        # Combine results
        combined_scores = {}
        reasoning_parts = []

        for result, weight, method_name in [
            (semantic_result, self.method_weights["semantic"], "semantic"),
            (keyword_result, self.method_weights["keyword"], "keyword"),
            (pattern_result, self.method_weights["pattern"], "pattern"),
        ]:
            memory_type, confidence, reasoning = result

            if memory_type not in combined_scores:
                combined_scores[memory_type] = 0

            combined_scores[memory_type] += confidence * weight
            reasoning_parts.append(f"{method_name}: {reasoning} (conf: {confidence:.2f})")

        # Find best classification
        best_type = max(combined_scores, key=combined_scores.get)
        final_confidence = combined_scores[best_type]

        combined_reasoning = f"Hybrid analysis - {' | '.join(reasoning_parts)}"

        return best_type, final_confidence, combined_reasoning


class BatchClassificationEngine:
    """Advanced batch classification engine"""

    def __init__(self):
        self.classifiers = {
            ClassificationMethod.KEYWORD_BASED: KeywordClassifier(),
            ClassificationMethod.SEMANTIC_SIMILARITY: SemanticClassifier(),
            ClassificationMethod.PATTERN_MATCHING: PatternClassifier(),
            ClassificationMethod.HYBRID: HybridClassifier(),
        }
        self.classification_cache = {}
        self.performance_stats = {}

    async def classify_batch(
        self, memories: list[dict[str, Any]], config: ClassificationConfig
    ) -> BatchClassificationResult:
        """Classify a batch of memories"""
        batch_id = (
            f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(memories).encode()).hexdigest()[:8]}"
        )
        start_time = time.time()

        result = BatchClassificationResult(
            batch_id=batch_id,
            total_memories=len(memories),
            processed_memories=0,
            successful_classifications=0,
            failed_classifications=0,
            classification_results=[],
            processing_time=0.0,
            performance_metrics={},
            errors=[],
            warnings=[],
        )

        try:
            classifier = self.classifiers.get(config.method)
            if not classifier:
                result.errors.append(f"Unknown classification method: {config.method}")
                return result

            # Process memories based on batch mode
            if config.parallel_workers > 1:
                classification_results = await self._classify_parallel(memories, classifier, config, result)
            else:
                classification_results = await self._classify_sequential(memories, classifier, config, result)

            result.classification_results = classification_results
            result.successful_classifications = len(
                [r for r in classification_results if r.confidence >= config.confidence_threshold]
            )
            result.failed_classifications = len(classification_results) - result.successful_classifications
            result.processed_memories = len(classification_results)

        except Exception as e:
            result.errors.append(f"Batch classification failed: {str(e)}")

        result.processing_time = time.time() - start_time
        result.performance_metrics = self._calculate_performance_metrics(result)

        return result

    async def _classify_sequential(
        self,
        memories: list[dict[str, Any]],
        classifier,
        config: ClassificationConfig,
        batch_result: BatchClassificationResult,
    ) -> list[ClassificationResult]:
        """Classify memories sequentially"""
        results = []

        for i, memory in enumerate(memories):
            try:
                start_time = time.time()

                # Check cache first
                cache_key = self._get_cache_key(memory, config.method)
                if config.enable_caching and cache_key in self.classification_cache:
                    cached_result = self.classification_cache[cache_key]
                    if time.time() - cached_result["timestamp"] < config.cache_duration:
                        results.append(cached_result["result"])
                        continue

                # Classify memory
                memory_type, confidence, reasoning = await classifier.classify_memory(memory)

                processing_time = time.time() - start_time

                classification_result = ClassificationResult(
                    memory_id=memory.get("id", f"memory_{i}"),
                    original_type=memory.get("metadata", {}).get("memory_type"),
                    predicted_type=memory_type,
                    confidence=confidence,
                    method_used=config.method,
                    reasoning=reasoning,
                    processing_time=processing_time,
                    metadata_updates={
                        "memory_type": memory_type,
                        "classification_confidence": confidence,
                        "classification_method": config.method.value,
                        "classified_at": datetime.now().isoformat(),
                    },
                )

                results.append(classification_result)

                # Cache result
                if config.enable_caching:
                    self.classification_cache[cache_key] = {"result": classification_result, "timestamp": time.time()}

            except Exception as e:
                batch_result.errors.append(f"Failed to classify memory {i}: {str(e)}")

        return results

    async def _classify_parallel(
        self,
        memories: list[dict[str, Any]],
        classifier,
        config: ClassificationConfig,
        batch_result: BatchClassificationResult,
    ) -> list[ClassificationResult]:
        """Classify memories in parallel"""
        results = []

        # Split memories into chunks for parallel processing
        chunk_size = max(1, len(memories) // config.parallel_workers)
        chunks = [memories[i : i + chunk_size] for i in range(0, len(memories), chunk_size)]

        # Process chunks in parallel
        tasks = []
        for chunk in chunks:
            task = self._classify_sequential(chunk, classifier, config, batch_result)
            tasks.append(task)

        # Wait for all tasks to complete
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        for chunk_result in chunk_results:
            if isinstance(chunk_result, Exception):
                batch_result.errors.append(f"Parallel processing error: {str(chunk_result)}")
            else:
                results.extend(chunk_result)

        return results

    def _get_cache_key(self, memory: dict[str, Any], method: ClassificationMethod) -> str:
        """Generate cache key for memory classification"""
        content_hash = hashlib.md5(memory.get("content", "").encode()).hexdigest()
        return f"{method.value}_{content_hash}"

    def _calculate_performance_metrics(self, result: BatchClassificationResult) -> dict[str, Any]:
        """Calculate performance metrics for batch classification"""
        if result.total_memories == 0:
            return {}

        avg_processing_time = (
            (sum(r.processing_time for r in result.classification_results) / len(result.classification_results))
            if result.classification_results
            else 0
        )

        avg_confidence = (
            (sum(r.confidence for r in result.classification_results) / len(result.classification_results))
            if result.classification_results
            else 0
        )

        success_rate = result.successful_classifications / result.total_memories

        # Calculate type distribution
        type_distribution = {}
        for r in result.classification_results:
            type_distribution[r.predicted_type] = type_distribution.get(r.predicted_type, 0) + 1

        return {
            "throughput": result.total_memories / result.processing_time if result.processing_time > 0 else 0,
            "avg_processing_time_per_memory": avg_processing_time,
            "avg_confidence": avg_confidence,
            "success_rate": success_rate,
            "type_distribution": type_distribution,
            "cache_hit_rate": len([k for k in self.classification_cache.keys()]) / result.total_memories
            if result.total_memories > 0
            else 0,
        }

    async def apply_classification_results(
        self, results: list[ClassificationResult], config: ClassificationConfig
    ) -> dict[str, Any]:
        """Apply classification results to memories"""
        if not config.auto_apply_results:
            return {"message": "Auto-apply disabled", "applied": 0}

        try:
            db = await get_mock_database()
            applied_count = 0
            failed_count = 0
            errors = []

            for result in results:
                if result.confidence >= config.confidence_threshold:
                    try:
                        # In a real implementation, this would update the memory in the database
                        # For mock database, we'll simulate the update
                        applied_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"Failed to apply classification for {result.memory_id}: {str(e)}")

            await db.close()

            return {"applied": applied_count, "failed": failed_count, "errors": errors}

        except Exception as e:
            return {"applied": 0, "failed": len(results), "errors": [f"Failed to apply classifications: {str(e)}"]}

    def get_classification_statistics(self) -> dict[str, Any]:
        """Get classification engine statistics"""
        return {
            "cache_size": len(self.classification_cache),
            "available_methods": list(self.classifiers.keys()),
            "performance_stats": self.performance_stats,
        }

    def clear_cache(self):
        """Clear classification cache"""
        self.classification_cache.clear()


# Global batch classification engine
batch_classification_engine = BatchClassificationEngine()


async def get_batch_classification_engine() -> BatchClassificationEngine:
    """Get batch classification engine instance"""
    return batch_classification_engine
