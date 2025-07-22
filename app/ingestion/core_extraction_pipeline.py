"""
Core extraction pipeline that integrates all enhanced NLP components
"""

import asyncio
import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

from app.ingestion.embedding_generator import EmbeddingGenerator
from app.ingestion.entity_extractor import EntityExtractor
from app.ingestion.intent_recognizer import IntentRecognizer
from app.ingestion.models import (
    ContentQuality,
    IngestionConfig,
    IngestionRequest,
    IngestionResponse,
    ProcessedContent,
)
from app.ingestion.relationship_detector import RelationshipDetector
from app.ingestion.structured_extractor import StructuredDataExtractor
from app.ingestion.topic_classifier import TopicClassifier

logger = logging.getLogger(__name__)


class CoreExtractionPipeline:
    """
    Main pipeline for sophisticated content extraction using transformers
    """

    def __init__(self, config: IngestionConfig | None = None, use_gpu: bool = False):
        """
        Initialize the core extraction pipeline

        Args:
            config: Ingestion configuration
            use_gpu: Whether to use GPU acceleration if available
        """
        self.config = config or IngestionConfig()
        self.use_gpu = use_gpu

        # Initialize components with transformer models
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all extraction components"""
        # Entity extraction with transformers
        self.entity_extractor = EntityExtractor(
            model_name=self.config.entity_model,
            enable_custom=self.config.enable_custom_entities,
            use_gpu=self.use_gpu
        )

        # Relationship detection with transformers
        self.relationship_detector = RelationshipDetector(
            model_name=self.config.entity_model,
            enable_patterns=True,
            use_gpu=self.use_gpu
        )

        # Intent recognition with transformers
        self.intent_recognizer = IntentRecognizer(
            enable_sentiment=self.config.enable_sentiment_analysis
        )

        # Topic classification
        self.topic_classifier = TopicClassifier()

        # Structured data extraction
        self.structured_extractor = StructuredDataExtractor()

        # Embedding generation
        embedding_model_type = "openai" if "ada" in self.config.embedding_model else "sentence-transformers"
        self.embedding_generator = EmbeddingGenerator(
            model_type=embedding_model_type,
            model_name=self.config.embedding_model if embedding_model_type == "sentence-transformers" else "auto",
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

    async def process(self, request: IngestionRequest) -> IngestionResponse:
        """
        Process content through the extraction pipeline

        Args:
            request: Ingestion request with content and options

        Returns:
            Ingestion response with processed content
        """
        start_time = time.time()
        request_id = uuid4()
        errors = []
        warnings = []

        try:
            # Create content hash
            content_hash = hashlib.sha256(request.content.encode()).hexdigest()

            # Initialize processed content
            processed_content = ProcessedContent(
                original_content=request.content,
                content_hash=content_hash,
                processor_version="2.0.0"  # Enhanced with transformers
            )

            # Extract entities
            if request.extract_entities:
                try:
                    entities = self.entity_extractor.extract_entities(
                        request.content,
                        min_confidence=self.config.min_entity_confidence
                    )

                    # Limit entities if configured
                    if len(entities) > self.config.max_entities_per_content:
                        entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
                        entities = entities[:self.config.max_entities_per_content]
                        warnings.append(f"Entity count limited to {self.config.max_entities_per_content}")

                    processed_content.entities = entities
                except Exception as e:
                    logger.error(f"Entity extraction failed: {e}")
                    errors.append(f"Entity extraction error: {str(e)}")

            # Extract relationships
            if request.extract_relationships and processed_content.entities:
                try:
                    relationships = self.relationship_detector.detect_relationships(
                        request.content,
                        processed_content.entities,
                        min_confidence=self.config.min_relationship_confidence
                    )

                    # Limit relationships if configured
                    if len(relationships) > self.config.max_relationships_per_content:
                        relationships = sorted(relationships, key=lambda r: r.confidence, reverse=True)
                        relationships = relationships[:self.config.max_relationships_per_content]
                        warnings.append(f"Relationship count limited to {self.config.max_relationships_per_content}")

                    processed_content.relationships = relationships
                except Exception as e:
                    logger.error(f"Relationship detection failed: {e}")
                    errors.append(f"Relationship detection error: {str(e)}")

            # Detect intent
            if request.detect_intent:
                try:
                    intent = self.intent_recognizer.recognize_intent(request.content)
                    processed_content.intent = intent
                except Exception as e:
                    logger.error(f"Intent recognition failed: {e}")
                    errors.append(f"Intent recognition error: {str(e)}")

            # Extract topics
            if request.extract_topics:
                try:
                    topics = await self.topic_classifier.classify_topics(
                        request.content,
                        domain_hint=request.domain_hint
                    )

                    # Filter by relevance
                    topics = [t for t in topics if t.relevance >= self.config.min_topic_relevance]

                    # Limit topics if configured
                    if len(topics) > self.config.max_topics_per_content:
                        topics = sorted(topics, key=lambda t: t.relevance, reverse=True)
                        topics = topics[:self.config.max_topics_per_content]

                    processed_content.topics = topics
                    if topics:
                        processed_content.primary_topic = topics[0]
                        processed_content.domain = topics[0].hierarchy[0] if topics[0].hierarchy else None
                except Exception as e:
                    logger.error(f"Topic classification failed: {e}")
                    errors.append(f"Topic classification error: {str(e)}")

            # Extract structured data
            if request.extract_structured:
                try:
                    structured_data = self.structured_extractor.extract(request.content)
                    processed_content.structured_data = structured_data
                except Exception as e:
                    logger.error(f"Structured extraction failed: {e}")
                    errors.append(f"Structured extraction error: {str(e)}")

            # Generate embeddings
            if request.generate_embeddings:
                try:
                    embeddings, embedding_metadata = await self.embedding_generator.generate_embeddings(
                        request.content,
                        generate_chunks=len(request.content) > self.config.chunk_size
                    )
                    processed_content.embeddings = embeddings
                    processed_content.embedding_metadata = embedding_metadata
                except Exception as e:
                    logger.error(f"Embedding generation failed: {e}")
                    errors.append(f"Embedding generation error: {str(e)}")

            # Calculate quality and importance
            processed_content.quality = self._assess_content_quality(processed_content)
            processed_content.completeness_score = self._calculate_completeness(processed_content)
            processed_content.suggested_importance = self._calculate_importance(processed_content)

            # Generate suggestions
            processed_content.suggested_tags = self._generate_tags(processed_content)
            processed_content.suggested_memory_type = self._suggest_memory_type(processed_content)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            processed_content.processing_time_ms = processing_time_ms

            # Create response
            return IngestionResponse(
                request_id=request_id,
                status="completed" if not errors else "partial",
                processed_content=processed_content,
                errors=errors,
                warnings=warnings,
                processing_stats={
                    "processing_time_ms": processing_time_ms,
                    "entity_count": len(processed_content.entities),
                    "relationship_count": len(processed_content.relationships),
                    "topic_count": len(processed_content.topics),
                    "embedding_count": len(processed_content.embeddings),
                    "model_info": {
                        "entity_model": self.entity_extractor.model_name,
                        "embedding_model": self.embedding_generator.model_name,
                        "use_transformers": True
                    }
                }
            )

        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return IngestionResponse(
                request_id=request_id,
                status="failed",
                errors=[f"Pipeline error: {str(e)}"],
                processing_stats={"processing_time_ms": int((time.time() - start_time) * 1000)}
            )

    def _assess_content_quality(self, content: ProcessedContent) -> ContentQuality:
        """Assess the quality of processed content"""
        # Calculate quality based on extraction success
        quality_score = 0.0

        # Entity quality
        if content.entities:
            avg_entity_confidence = sum(e.confidence for e in content.entities) / len(content.entities)
            quality_score += avg_entity_confidence * 0.3

        # Relationship quality
        if content.relationships:
            avg_rel_confidence = sum(r.confidence for r in content.relationships) / len(content.relationships)
            quality_score += avg_rel_confidence * 0.2

        # Intent clarity
        if content.intent and content.intent.confidence > 0.7:
            quality_score += 0.2

        # Topic relevance
        if content.topics:
            avg_relevance = sum(t.relevance for t in content.topics) / len(content.topics)
            quality_score += avg_relevance * 0.2

        # Content length factor
        word_count = len(content.original_content.split())
        if word_count > 50:
            quality_score += 0.1

        # Map score to quality level
        if quality_score >= 0.8:
            return ContentQuality.HIGH
        elif quality_score >= 0.5:
            return ContentQuality.MEDIUM
        elif quality_score >= 0.3:
            return ContentQuality.LOW
        else:
            return ContentQuality.INCOMPLETE

    def _calculate_completeness(self, content: ProcessedContent) -> float:
        """Calculate completeness score of extraction"""
        completeness = 0.0

        # Check for entities
        if content.entities:
            completeness += 0.25

        # Check for relationships
        if content.relationships and len(content.relationships) >= 2:
            completeness += 0.2

        # Check for intent
        if content.intent:
            completeness += 0.15

        # Check for topics
        if content.topics:
            completeness += 0.2

        # Check for embeddings
        if content.embeddings:
            completeness += 0.2

        return min(1.0, completeness)

    def _calculate_importance(self, content: ProcessedContent) -> float:
        """Calculate suggested importance score"""
        importance = 0.5  # Base importance

        # Boost for high-quality content
        if content.quality == ContentQuality.HIGH:
            importance += 0.2

        # Boost for actionable content
        if content.intent and content.intent.type.value in ["todo", "decision", "problem"]:
            importance += 0.15

        # Boost for high urgency
        if content.intent and content.intent.urgency and content.intent.urgency > 0.7:
            importance += 0.15

        # Boost for rich entity/relationship networks
        if len(content.entities) > 5 and len(content.relationships) > 3:
            importance += 0.1

        # Penalty for low quality
        if content.quality == ContentQuality.LOW:
            importance -= 0.2

        return max(0.0, min(1.0, importance))

    def _generate_tags(self, content: ProcessedContent) -> list[str]:
        """Generate suggested tags for content"""
        tags = []

        # Add intent-based tags
        if content.intent:
            tags.append(content.intent.type.value)
            if content.intent.urgency and content.intent.urgency > 0.7:
                tags.append("urgent")

        # Add topic-based tags
        for topic in content.topics[:3]:  # Top 3 topics
            tags.append(topic.name.lower().replace(" ", "-"))

        # Add entity type tags
        entity_types = set(e.type.value for e in content.entities)
        for entity_type in entity_types:
            if entity_type not in ["date", "time"]:  # Skip common types
                tags.append(f"has-{entity_type}")

        # Add quality tag
        if content.quality == ContentQuality.HIGH:
            tags.append("high-quality")

        return list(set(tags))[:10]  # Limit to 10 unique tags

    def _suggest_memory_type(self, content: ProcessedContent) -> str:
        """Suggest appropriate memory type based on content"""
        if content.intent:
            intent_type = content.intent.type.value

            # Map intent to memory type
            if intent_type in ["todo", "planning"]:
                return "task"
            elif intent_type in ["idea", "reflection"]:
                return "insight"
            elif intent_type in ["question", "problem"]:
                return "question"
            elif intent_type in ["decision", "solution"]:
                return "decision"
            elif intent_type == "reference":
                return "reference"
            elif intent_type == "learning":
                return "knowledge"

        # Default based on content characteristics
        if content.structured_data and (content.structured_data.code_snippets or content.structured_data.tables):
            return "technical"
        elif len(content.entities) > 5:
            return "note"
        else:
            return "general"

    async def batch_process(self, requests: list[IngestionRequest]) -> list[IngestionResponse]:
        """
        Process multiple requests in batch for better performance

        Args:
            requests: List of ingestion requests

        Returns:
            List of ingestion responses
        """
        # Process in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(5)  # Limit concurrent processing

        async def process_with_semaphore(request):
            async with semaphore:
                return await self.process(request)

        tasks = [process_with_semaphore(request) for request in requests]
        return await asyncio.gather(*tasks)

    def get_pipeline_info(self) -> dict[str, Any]:
        """Get information about the pipeline configuration"""
        return {
            "version": "2.0.0",
            "components": {
                "entity_extractor": {
                    "model": self.entity_extractor.model_name,
                    "custom_patterns": self.entity_extractor.enable_custom
                },
                "relationship_detector": {
                    "model": self.relationship_detector.model_name,
                    "patterns_enabled": self.relationship_detector.enable_patterns
                },
                "intent_recognizer": {
                    "sentiment_enabled": self.intent_recognizer.enable_sentiment,
                    "transformer_available": hasattr(self.intent_recognizer, "transformer_classifier") and self.intent_recognizer.transformer_classifier is not None
                },
                "embedding_generator": {
                    "model_type": self.embedding_generator.model_type,
                    "model_name": self.embedding_generator.model_name,
                    "dimensions": self.embedding_generator.dimensions
                }
            },
            "config": self.config.dict(),
            "gpu_enabled": self.use_gpu
        }
