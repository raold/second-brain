"""
Entity extraction component for the sophisticated ingestion engine
"""

import logging
import re
from typing import Any

try:
    import spacy
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from app.ingestion.models import Entity, EntityType

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Sophisticated entity extraction using SpaCy and custom patterns"""

    def __init__(self, model_name: str = "en_core_web_trf", enable_custom: bool = True, use_gpu: bool = False):
        """
        Initialize entity extractor

        Args:
            model_name: SpaCy model to use (defaults to transformer model)
            enable_custom: Whether to enable custom entity patterns
            use_gpu: Whether to use GPU acceleration if available
        """
        self.model_name = model_name
        self.enable_custom = enable_custom
        self.use_gpu = use_gpu
        self.nlp = None
        self.custom_patterns = self._initialize_custom_patterns()

        if SPACY_AVAILABLE:
            try:
                # Try to load transformer model first
                if model_name == "en_core_web_trf":
                    try:
                        self.nlp = spacy.load(model_name)
                        if self.use_gpu and spacy.prefer_gpu():
                            logger.info("Using GPU for SpaCy transformer model")
                        logger.info(f"Loaded SpaCy transformer model: {model_name}")
                    except OSError:
                        # Fall back to smaller model if transformer not available
                        logger.warning("Transformer model not found, falling back to en_core_web_lg")
                        try:
                            self.nlp = spacy.load("en_core_web_lg")
                            self.model_name = "en_core_web_lg"
                        except OSError:
                            logger.warning("Large model not found, falling back to en_core_web_sm")
                            self.nlp = spacy.load("en_core_web_sm")
                            self.model_name = "en_core_web_sm"
                else:
                    self.nlp = spacy.load(model_name)
                    logger.info(f"Loaded SpaCy model: {model_name}")

                # Add custom entity ruler for domain-specific entities
                if "entity_ruler" not in self.nlp.pipe_names:
                    ruler = self.nlp.add_pipe("entity_ruler", before="ner")
                    ruler.add_patterns(self._get_entity_ruler_patterns())

            except Exception as e:
                logger.warning(f"Failed to load SpaCy model {model_name}: {e}")
                logger.info("Entity extraction will use pattern matching only")

    def extract_entities(self, text: str, min_confidence: float = 0.7) -> list[Entity]:
        """
        Extract entities from text using NER and custom patterns

        Args:
            text: Input text to extract entities from
            min_confidence: Minimum confidence threshold

        Returns:
            List of extracted entities
        """
        entities = []

        # SpaCy NER extraction
        if self.nlp:
            entities.extend(self._extract_spacy_entities(text, min_confidence))

        # Custom pattern extraction
        if self.enable_custom:
            entities.extend(self._extract_custom_entities(text))

        # Deduplicate and merge overlapping entities
        entities = self._deduplicate_entities(entities)

        # Normalize entities
        entities = self._normalize_entities(entities)

        return entities

    def _extract_spacy_entities(self, text: str, min_confidence: float) -> list[Entity]:
        """Extract entities using SpaCy NER"""
        entities = []

        try:
            doc = self.nlp(text)

            # Standard NER entities
            for ent in doc.ents:
                entity_type = self._map_spacy_to_entity_type(ent.label_)
                if entity_type:
                    # SpaCy doesn't provide confidence scores, so we use heuristics
                    confidence = self._calculate_entity_confidence(ent)

                    if confidence >= min_confidence:
                        entities.append(Entity(
                            text=ent.text,
                            type=entity_type,
                            normalized=self._normalize_text(ent.text),
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            confidence=confidence,
                            metadata={
                                "spacy_label": ent.label_,
                                "source": "spacy_ner"
                            }
                        ))

            # Extract additional entities from noun phrases
            for chunk in doc.noun_chunks:
                if self._is_potential_entity(chunk):
                    entity_type = self._classify_noun_chunk(chunk)
                    if entity_type:
                        confidence = self._calculate_chunk_confidence(chunk)

                        if confidence >= min_confidence:
                            entities.append(Entity(
                                text=chunk.text,
                                type=entity_type,
                                normalized=self._normalize_text(chunk.text),
                                start_pos=chunk.start_char,
                                end_pos=chunk.end_char,
                                confidence=confidence,
                                metadata={
                                    "source": "noun_chunks",
                                    "root": chunk.root.text
                                }
                            ))

        except Exception as e:
            logger.error(f"Error in SpaCy entity extraction: {e}")

        return entities

    def _extract_custom_entities(self, text: str) -> list[Entity]:
        """Extract entities using custom regex patterns"""
        entities = []

        for pattern_type, patterns in self.custom_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                confidence = pattern_info.get("confidence", 0.9)

                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Extract the main group or full match
                    entity_text = match.group(1) if len(match.groups()) > 0 else match.group(0)

                    entities.append(Entity(
                        text=entity_text,
                        type=pattern_type,
                        normalized=self._normalize_text(entity_text),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        metadata={
                            "source": "custom_pattern",
                            "pattern_name": pattern_info.get("name", "unnamed")
                        }
                    ))

        return entities

    def _initialize_custom_patterns(self) -> dict[EntityType, list[dict[str, Any]]]:
        """Initialize custom regex patterns for entity extraction"""
        return {
            EntityType.EMAIL: [
                {
                    "name": "standard_email",
                    "pattern": r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                    "confidence": 0.95
                }
            ],
            EntityType.URL: [
                {
                    "name": "http_url",
                    "pattern": r'(https?://[^\s<>"{}|\\^`\[\]]+)',
                    "confidence": 0.95
                },
                {
                    "name": "www_url",
                    "pattern": r'(www\.[^\s<>"{}|\\^`\[\]]+\.[^\s<>"{}|\\^`\[\]]+)',
                    "confidence": 0.90
                }
            ],
            EntityType.PHONE: [
                {
                    "name": "us_phone",
                    "pattern": r'\b(\+?1?[-.]?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4})\b',
                    "confidence": 0.85
                },
                {
                    "name": "international_phone",
                    "pattern": r'\b(\+[0-9]{1,3}[-.]?[0-9]{1,4}[-.]?[0-9]{1,4}[-.]?[0-9]{1,9})\b',
                    "confidence": 0.80
                }
            ],
            EntityType.DATE: [
                {
                    "name": "iso_date",
                    "pattern": r'\b(\d{4}-\d{2}-\d{2})\b',
                    "confidence": 0.95
                },
                {
                    "name": "us_date",
                    "pattern": r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
                    "confidence": 0.85
                },
                {
                    "name": "written_date",
                    "pattern": r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b',
                    "confidence": 0.90
                }
            ],
            EntityType.TIME: [
                {
                    "name": "time_12h",
                    "pattern": r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b',
                    "confidence": 0.90
                },
                {
                    "name": "time_24h",
                    "pattern": r'\b([01]?[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?\b',
                    "confidence": 0.85
                }
            ],
            EntityType.PROJECT: [
                {
                    "name": "jira_ticket",
                    "pattern": r'\b([A-Z]{2,10}-\d{1,6})\b',
                    "confidence": 0.80
                },
                {
                    "name": "github_issue",
                    "pattern": r'(?:#|issue )(\d{1,6})\b',
                    "confidence": 0.75
                }
            ],
            EntityType.TECHNOLOGY: [
                {
                    "name": "version_number",
                    "pattern": r'\b(\w+)\s+v?(\d+\.?\d*\.?\d*)\b',
                    "confidence": 0.70
                },
                {
                    "name": "programming_language",
                    "pattern": r'\b(Python|JavaScript|Java|C\+\+|C#|Ruby|Go|Rust|TypeScript|Swift)\b',
                    "confidence": 0.85
                }
            ]
        }

    def _map_spacy_to_entity_type(self, spacy_label: str) -> EntityType | None:
        """Map SpaCy NER labels to our entity types"""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,
            "LOC": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "WORK_OF_ART": EntityType.PROJECT,
            "EVENT": EntityType.PROJECT,
            "PRODUCT": EntityType.TECHNOLOGY,
        }
        return mapping.get(spacy_label)

    def _calculate_entity_confidence(self, ent: Any) -> float:
        """Calculate confidence score for SpaCy entity"""
        # Base confidence on entity label
        label_confidence = {
            "PERSON": 0.85,
            "ORG": 0.80,
            "GPE": 0.85,
            "LOC": 0.80,
            "DATE": 0.90,
            "TIME": 0.85,
        }.get(ent.label_, 0.70)

        # Adjust based on entity length and context
        length_factor = min(1.0, len(ent.text.split()) / 3)

        # Check if entity is in sentence start (often more reliable)
        position_factor = 1.1 if ent.start == ent.sent.start else 1.0

        return min(0.95, label_confidence * length_factor * position_factor)

    def _calculate_chunk_confidence(self, chunk: Any) -> float:
        """Calculate confidence for noun chunk as entity"""
        # Base confidence on chunk properties
        base_confidence = 0.60

        # Boost for proper nouns
        if any(token.pos_ == "PROPN" for token in chunk):
            base_confidence += 0.15

        # Boost for capitalized chunks
        if chunk.text[0].isupper():
            base_confidence += 0.10

        # Penalty for very short or very long chunks
        word_count = len(chunk.text.split())
        if word_count == 1:
            base_confidence -= 0.10
        elif word_count > 5:
            base_confidence -= 0.15

        return min(0.90, max(0.30, base_confidence))

    def _is_potential_entity(self, chunk: Any) -> bool:
        """Check if noun chunk could be an entity"""
        # Skip chunks that are too short or too long
        word_count = len(chunk.text.split())
        if word_count < 1 or word_count > 6:
            return False

        # Skip common words
        if chunk.text.lower() in {"it", "this", "that", "these", "those", "something", "someone"}:
            return False

        # Check for at least one proper noun or capitalized word
        has_proper = any(token.pos_ == "PROPN" for token in chunk)
        is_capitalized = chunk.text[0].isupper()

        return has_proper or is_capitalized

    def _classify_noun_chunk(self, chunk: Any) -> EntityType | None:
        """Classify noun chunk into entity type"""
        text_lower = chunk.text.lower()

        # Check for technology indicators
        tech_keywords = {"system", "software", "application", "platform", "framework", "library", "api", "sdk"}
        if any(keyword in text_lower for keyword in tech_keywords):
            return EntityType.TECHNOLOGY

        # Check for project indicators
        project_keywords = {"project", "initiative", "program", "campaign", "effort"}
        if any(keyword in text_lower for keyword in project_keywords):
            return EntityType.PROJECT

        # Check for concept indicators
        if chunk.root.pos_ in {"NOUN", "PROPN"} and len(chunk.text.split()) > 1:
            return EntityType.CONCEPT

        # Default to concept for other proper nouns
        if any(token.pos_ == "PROPN" for token in chunk):
            return EntityType.CONCEPT

        return None

    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        """Remove duplicate and overlapping entities"""
        if not entities:
            return []

        # Sort by start position and confidence
        sorted_entities = sorted(entities, key=lambda e: (e.start_pos, -e.confidence))

        deduplicated = []
        last_end = -1

        for entity in sorted_entities:
            # Skip if this entity overlaps with a previous one
            if entity.start_pos < last_end:
                continue

            # Check for exact duplicates in different positions
            is_duplicate = False
            for existing in deduplicated:
                if (entity.normalized == existing.normalized and
                    entity.type == existing.type and
                    abs(entity.start_pos - existing.start_pos) < 50):
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(entity)
                last_end = entity.end_pos

        return deduplicated

    def _normalize_entities(self, entities: list[Entity]) -> list[Entity]:
        """Normalize entity text and add additional metadata"""
        normalized = []

        for entity in entities:
            # Update normalized form if not already set
            if not entity.normalized:
                entity.normalized = self._normalize_text(entity.text)

            # Add additional metadata
            entity.metadata["length"] = len(entity.text)
            entity.metadata["word_count"] = len(entity.text.split())

            normalized.append(entity)

        return normalized

    def _normalize_text(self, text: str) -> str:
        """Normalize entity text for comparison"""
        # Remove extra whitespace
        normalized = " ".join(text.split())

        # Convert to lowercase for comparison
        normalized = normalized.lower()

        # Remove common punctuation from edges
        normalized = normalized.strip(".,;:!?'\"")

        return normalized

    def _get_entity_ruler_patterns(self) -> list[dict[str, Any]]:
        """Get patterns for SpaCy entity ruler to improve domain-specific recognition"""
        patterns = [
            # Technology patterns
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "python"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "javascript"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "react"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "docker"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "kubernetes"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "tensorflow"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "pytorch"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "spacy"}]},
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": "transformers"}]},

            # Framework patterns
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": {"IN": ["django", "flask", "fastapi"]}}]},

            # AI/ML concepts
            {"label": "CONCEPT", "pattern": [{"LOWER": "machine"}, {"LOWER": "learning"}]},
            {"label": "CONCEPT", "pattern": [{"LOWER": "deep"}, {"LOWER": "learning"}]},
            {"label": "CONCEPT", "pattern": [{"LOWER": "neural"}, {"LOWER": "network"}]},
            {"label": "CONCEPT", "pattern": [{"LOWER": "natural"}, {"LOWER": "language"}, {"LOWER": "processing"}]},

            # Project management
            {"label": "PROJECT", "pattern": [{"TEXT": {"REGEX": "[A-Z]{2,}-\\d+"}}]},  # JIRA-style

            # Version patterns
            {"label": "VERSION", "pattern": [{"TEXT": {"REGEX": "v?\\d+\\.\\d+(\\.\\d+)?"}}]},
        ]
        return patterns

    def extract_entities_with_context(self, text: str, context_window: int = 50) -> list[dict[str, Any]]:
        """
        Extract entities with surrounding context for better understanding
        
        Args:
            text: Input text
            context_window: Number of characters to include before/after entity
            
        Returns:
            List of entities with context
        """
        entities = self.extract_entities(text)
        entities_with_context = []

        for entity in entities:
            start = max(0, entity.start_pos - context_window)
            end = min(len(text), entity.end_pos + context_window)

            context = {
                "entity": entity.dict(),
                "context": {
                    "before": text[start:entity.start_pos],
                    "after": text[entity.end_pos:end],
                    "full": text[start:end]
                }
            }
            entities_with_context.append(context)

        return entities_with_context

    def get_entity_statistics(self, entities: list[Entity]) -> dict[str, Any]:
        """Get statistics about extracted entities"""
        if not entities:
            return {
                "total_entities": 0,
                "entity_types": {},
                "confidence_stats": {},
                "extraction_sources": {}
            }

        # Count by type
        type_counts = {}
        for entity in entities:
            type_counts[entity.type.value] = type_counts.get(entity.type.value, 0) + 1

        # Confidence statistics
        confidences = [e.confidence for e in entities]
        confidence_stats = {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "high_confidence": len([c for c in confidences if c >= 0.8])
        }

        # Source statistics
        source_counts = {}
        for entity in entities:
            source = entity.metadata.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            "total_entities": len(entities),
            "entity_types": type_counts,
            "confidence_stats": confidence_stats,
            "extraction_sources": source_counts
        }
