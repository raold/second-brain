"""
Relationship detection component for identifying connections between entities
"""

from app.utils.logging_config import get_logger
from typing import List
from typing import Any
from collections import defaultdict
logger = get_logger(__name__)


class RelationshipDetector:
    """Detect relationships between entities using dependency parsing and patterns"""

    def __init__(self, model_name: str = "en_core_web_trf", enable_patterns: bool = True, use_gpu: bool = False):
        """
        Initialize relationship detector

        Args:
            model_name: SpaCy model to use (defaults to transformer model)
            enable_patterns: Whether to use pattern-based detection
            use_gpu: Whether to use GPU acceleration if available
        """
        self.model_name = model_name
        self.enable_patterns = enable_patterns
        self.use_gpu = use_gpu
        self.nlp = None

        # Initialize relationship patterns
        self.relationship_patterns = self._initialize_relationship_patterns()

        # Initialize transformer-enhanced patterns
        self.transformer_patterns = self._initialize_transformer_patterns()

        if SPACY_AVAILABLE:
            try:
                # Try to load transformer model first
                if model_name == "en_core_web_trf":
                    try:
                        self.nlp = spacy.load(model_name)
                        if self.use_gpu and spacy.prefer_gpu():
                            logger.info("Using GPU for SpaCy transformer model")
                        logger.info(f"Loaded SpaCy transformer model for relationship detection: {model_name}")
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
                    logger.info(f"Loaded SpaCy model for relationship detection: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load SpaCy model {model_name}: {e}")
                logger.info("Relationship detection will use pattern matching only")

    def detect_relationships(self,
                           text: str,
                           entities: list[Entity],
                           min_confidence: float = 0.6) -> list[Relationship]:
        """
        Detect relationships between entities

        Args:
            text: Input text
            entities: List of extracted entities
            min_confidence: Minimum confidence threshold

        Returns:
            List of detected relationships
        """
        if not entities or len(entities) < 2:
            return []

        relationships = []

        # Dependency parsing based detection
        if self.nlp:
            doc = self.nlp(text)
            dep_relationships = self._detect_dependency_relationships(text, entities)
            relationships.extend(dep_relationships)

            # Transformer-based detection if using transformer model
            if self.model_name == "en_core_web_trf" and hasattr(doc, "_.trf_data"):
                transformer_relationships = self.detect_transformer_relationships(doc, entities)
                relationships.extend(transformer_relationships)

        # Pattern-based detection
        if self.enable_patterns:
            pattern_relationships = self._detect_pattern_relationships(text, entities)
            relationships.extend(pattern_relationships)

        # Proximity-based detection
        proximity_relationships = self._detect_proximity_relationships(text, entities)
        relationships.extend(proximity_relationships)

        # Coreference-based detection (if entities refer to same thing)
        coref_relationships = self._detect_coreference_relationships(entities)
        relationships.extend(coref_relationships)

        # Deduplicate and filter relationships
        relationships = self._deduplicate_relationships(relationships)
        relationships = [r for r in relationships if r.confidence >= min_confidence]

        return relationships

    def _detect_dependency_relationships(self,
                                       text: str,
                                       entities: list[Entity]) -> list[Relationship]:
        """Detect relationships using dependency parsing"""
        relationships = []

        try:
            doc = self.nlp(text)

            # Create entity spans in the document
            entity_spans = self._create_entity_spans(doc, entities)

            # Analyze dependencies between entities
            for i, (entity1, span1) in enumerate(entity_spans):
                for _j, (entity2, span2) in enumerate(entity_spans[i+1:], i+1):
                    # Find dependency path between entities
                    path = self._find_dependency_path(span1.root, span2.root)

                    if path:
                        # Analyze the path to determine relationship type
                        rel_type, confidence = self._analyze_dependency_path(path)

                        if rel_type:
                            # Extract evidence text
                            evidence = self._extract_evidence(doc, span1, span2)

                            relationships.append(Relationship(
                                source=entity1,
                                target=entity2,
                                type=rel_type,
                                confidence=confidence,
                                evidence=evidence,
                                metadata={
                                    "detection_method": "dependency_parsing",
                                    "path_length": len(path)
                                }
                            ))

        except Exception as e:
            logger.error(f"Error in dependency relationship detection: {e}")

        return relationships

    def _detect_pattern_relationships(self,
                                    text: str,
                                    entities: list[Entity]) -> list[Relationship]:
        """Detect relationships using predefined patterns"""
        relationships = []

        # Create entity position map
        self._create_entity_position_map(entities)

        for pattern_type, patterns in self.relationship_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                confidence_boost = pattern_info.get("confidence", 0.8)

                # Find all matches
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Extract entities from capture groups
                    if len(match.groups()) >= 2:
                        entity1_text = match.group(1)
                        entity2_text = match.group(2)

                        # Find matching entities
                        entity1 = self._find_entity_by_text(entities, entity1_text, match.start(1))
                        entity2 = self._find_entity_by_text(entities, entity2_text, match.start(2))

                        if entity1 and entity2 and entity1 != entity2:
                            relationships.append(Relationship(
                                source=entity1,
                                target=entity2,
                                type=pattern_type,
                                confidence=confidence_boost,
                                evidence=match.group(0),
                                metadata={
                                    "detection_method": "pattern_matching",
                                    "pattern_name": pattern_info.get("name", "unnamed")
                                }
                            ))

        return relationships

    def _detect_proximity_relationships(self,
                                      text: str,
                                      entities: list[Entity]) -> list[Relationship]:
        """Detect relationships based on entity proximity"""
        relationships = []

        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_pos)

        # Check adjacent entities
        for i in range(len(sorted_entities) - 1):
            entity1 = sorted_entities[i]
            entity2 = sorted_entities[i + 1]

            # Calculate distance
            distance = entity2.start_pos - entity1.end_pos

            # Check if entities are in same sentence
            text_between = text[entity1.end_pos:entity2.start_pos]

            # Determine relationship based on context
            if distance < 50 and distance > 0:  # Close proximity
                # Check for connecting words
                rel_type, confidence = self._analyze_connecting_text(text_between)

                if not rel_type:
                    # Default to MENTIONED_WITH for close entities
                    rel_type = RelationshipType.MENTIONED_WITH
                    confidence = 0.6 - (distance / 100)  # Closer = higher confidence

                if confidence > 0.5:
                    relationships.append(Relationship(
                        source=entity1,
                        target=entity2,
                        type=rel_type,
                        confidence=confidence,
                        evidence=text[entity1.start_pos:entity2.end_pos],
                        metadata={
                            "detection_method": "proximity",
                            "distance": distance
                        }
                    ))

        return relationships

    def _detect_coreference_relationships(self, entities: list[Entity]) -> list[Relationship]:
        """Detect when different entities refer to the same thing"""
        relationships = []

        # Group entities by normalized form and type
        entity_groups = defaultdict(list)

        for entity in entities:
            # Create grouping key
            key = (entity.normalized, entity.type)
            entity_groups[key].append(entity)

        # Create relationships within groups
        for (normalized, _entity_type), group in entity_groups.items():
            if len(group) > 1:
                # Sort by position
                group.sort(key=lambda e: e.start_pos)

                # Create chain of relationships
                for i in range(len(group) - 1):
                    relationships.append(Relationship(
                        source=group[i],
                        target=group[i + 1],
                        type=RelationshipType.SIMILAR_TO,
                        confidence=0.9,
                        evidence=f"Both refer to '{normalized}'",
                        metadata={
                            "detection_method": "coreference",
                            "normalized_form": normalized
                        }
                    ))

        return relationships

    def _create_entity_spans(self, doc: Doc, entities: list[Entity]) -> list[tuple[Entity, Any]]:
        """Create spaCy spans for entities"""
        entity_spans = []

        for entity in entities:
            # Find token indices for entity
            start_token = None
            end_token = None

            for token in doc:
                if token.idx == entity.start_pos:
                    start_token = token.i
                if token.idx + len(token.text) == entity.end_pos:
                    end_token = token.i + 1
                    break

            if start_token is not None and end_token is not None:
                span = doc[start_token:end_token]
                entity_spans.append((entity, span))

        return entity_spans

    def _find_dependency_path(self, token1: Any, token2: Any) -> list[Any] | None:
        """Find dependency path between two tokens"""
        if not token1 or not token2:
            return None

        # Find common ancestor
        ancestors1 = set(token1.ancestors)
        ancestors2 = set(token2.ancestors)

        # Include the tokens themselves
        ancestors1.add(token1)
        ancestors2.add(token2)

        common_ancestors = ancestors1 & ancestors2

        if not common_ancestors:
            return None

        # Find lowest common ancestor (closest to tokens)
        lca = min(common_ancestors, key=lambda t:
                 min(abs(t.i - token1.i), abs(t.i - token2.i)))

        # Build path from token1 to lca to token2
        path1 = self._path_to_ancestor(token1, lca)
        path2 = self._path_to_ancestor(token2, lca)

        # Combine paths (reverse path1 and append path2)
        full_path = list(reversed(path1[:-1])) + path2

        return full_path if len(full_path) <= 5 else None  # Limit path length

    def _path_to_ancestor(self, token: Any, ancestor: Any) -> list[Any]:
        """Build path from token to ancestor"""
        path = [token]
        current = token

        while current != ancestor and current.head != current:
            current = current.head
            path.append(current)

            if len(path) > 10:  # Prevent infinite loops
                break

        return path

    def _analyze_dependency_path(self, path: list[Any]) -> tuple[RelationshipType | None, float]:
        """Analyze dependency path to determine relationship type"""
        if not path:
            return None, 0.0

        # Extract dependency labels and POS tags
        deps = [token.dep_ for token in path]
        pos_tags = [token.pos_ for token in path]
        lemmas = [token.lemma_.lower() for token in path]

        # Check for specific patterns

        # WORKS_FOR pattern
        if any(lemma in ["work", "employ", "job"] for lemma in lemmas):
            if "VERB" in pos_tags:
                return RelationshipType.WORKS_FOR, 0.8

        # LOCATED_IN pattern
        if any(lemma in ["locate", "in", "at", "near"] for lemma in lemmas):
            if any(dep in ["prep", "pobj"] for dep in deps):
                return RelationshipType.LOCATED_IN, 0.75

        # CREATED_BY pattern
        if any(lemma in ["create", "make", "build", "develop", "write"] for lemma in lemmas):
            if "VERB" in pos_tags:
                return RelationshipType.CREATED_BY, 0.8

        # PART_OF pattern
        if any(lemma in ["part", "member", "component", "belong"] for lemma in lemmas):
            return RelationshipType.PART_OF, 0.7

        # DEPENDS_ON pattern
        if any(lemma in ["depend", "require", "need", "rely"] for lemma in lemmas):
            return RelationshipType.DEPENDS_ON, 0.75

        # Temporal relationships
        if any(lemma in ["before", "after", "during", "while"] for lemma in lemmas):
            if "before" in lemmas:
                return RelationshipType.TEMPORAL_BEFORE, 0.8
            elif "after" in lemmas:
                return RelationshipType.TEMPORAL_AFTER, 0.8
            else:
                return RelationshipType.TEMPORAL_DURING, 0.75

        # Default to RELATED_TO with lower confidence
        if len(path) <= 3:
            return RelationshipType.RELATED_TO, 0.6

        return None, 0.0

    def _analyze_connecting_text(self, text: str) -> tuple[RelationshipType | None, float]:
        """Analyze text between entities to determine relationship"""
        text_lower = text.lower().strip()

        # Check for specific connecting phrases
        patterns = {
            RelationshipType.WORKS_FOR: [
                r"\bworks?\s+(?:for|at|with)\b",
                r"\bemployed\s+(?:by|at)\b"
            ],
            RelationshipType.LOCATED_IN: [
                r"\b(?:in|at|near|within)\b",
                r"\blocated\s+(?:in|at)\b"
            ],
            RelationshipType.CREATED_BY: [
                r"\b(?:created|made|built|developed)\s+by\b",
                r"\bby\b"
            ],
            RelationshipType.PART_OF: [
                r"\bpart\s+of\b",
                r"\b(?:member|component)\s+of\b"
            ],
            RelationshipType.DEPENDS_ON: [
                r"\bdepends?\s+on\b",
                r"\brequires?\b"
            ],
            RelationshipType.TEMPORAL_BEFORE: [
                r"\bbefore\b",
                r"\bprior\s+to\b"
            ],
            RelationshipType.TEMPORAL_AFTER: [
                r"\bafter\b",
                r"\bfollowing\b"
            ]
        }

        for rel_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text_lower):
                    return rel_type, 0.8

        # Check for simple connectors
        if text_lower in [",", "and", "&", "with"]:
            return RelationshipType.MENTIONED_WITH, 0.6

        return None, 0.0

    def _extract_evidence(self, doc: Doc, span1: Any, span2: Any) -> str:
        """Extract evidence text for relationship"""
        # Get sentence(s) containing both entities
        start_sent = span1.sent
        end_sent = span2.sent

        if start_sent == end_sent:
            # Same sentence
            return start_sent.text.strip()
        else:
            # Multiple sentences
            start_idx = start_sent.start
            end_idx = end_sent.end
            evidence = doc[start_idx:end_idx].text.strip()

            # Limit evidence length
            if len(evidence) > 200:
                # Extract more focused evidence
                focus_start = max(start_idx, span1.start - 10)
                focus_end = min(end_idx, span2.end + 10)
                evidence = "..." + doc[focus_start:focus_end].text.strip() + "..."

            return evidence

    def _find_entity_by_text(self,
                           entities: list[Entity],
                           text: str,
                           position: int) -> Entity | None:
        """Find entity matching text near position"""
        text_lower = text.lower().strip()

        # First try exact position match
        for entity in entities:
            if entity.start_pos <= position <= entity.end_pos:
                return entity

        # Then try text match within reasonable distance
        for entity in entities:
            if entity.text.lower() == text_lower:
                if abs(entity.start_pos - position) < 50:
                    return entity

        # Try normalized form match
        for entity in entities:
            if entity.normalized == text_lower:
                if abs(entity.start_pos - position) < 100:
                    return entity

        return None

    def _create_entity_position_map(self, entities: list[Entity]) -> dict[int, Entity]:
        """Create a map of positions to entities"""
        position_map = {}
        for entity in entities:
            for pos in range(entity.start_pos, entity.end_pos):
                position_map[pos] = entity
        return position_map

    def _deduplicate_relationships(self, relationships: list[Relationship]) -> list[Relationship]:
        """Remove duplicate relationships"""
        seen = set()
        unique = []

        for rel in relationships:
            # Create a key for the relationship
            key = (
                rel.source.normalized,
                rel.target.normalized,
                rel.type,
                rel.source.start_pos,
                rel.target.start_pos
            )

            # Also check reverse for bidirectional relationships
            reverse_key = (
                rel.target.normalized,
                rel.source.normalized,
                rel.type,
                rel.target.start_pos,
                rel.source.start_pos
            )

            if key not in seen and reverse_key not in seen:
                seen.add(key)
                unique.append(rel)
            else:
                # If duplicate, keep the one with higher confidence
                for i, existing in enumerate(unique):
                    existing_key = (
                        existing.source.normalized,
                        existing.target.normalized,
                        existing.type,
                        existing.source.start_pos,
                        existing.target.start_pos
                    )
                    if existing_key == key and rel.confidence > existing.confidence:
                        unique[i] = rel
                        break

        return unique

    def _initialize_relationship_patterns(self) -> dict[RelationshipType, list[dict[str, Any]]]:
        """Initialize regex patterns for relationship detection"""
        return {
            RelationshipType.WORKS_FOR: [
                {
                    "name": "works_for_pattern",
                    "pattern": r"(\b[A-Z][a-z]+ [A-Z][a-z]+)\s+works?\s+(?:for|at)\s+(\b[A-Z][\w\s&]+)",
                    "confidence": 0.85
                },
                {
                    "name": "employed_by_pattern",
                    "pattern": r"(\b[A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:an?\s+)?employee\s+(?:of|at)\s+(\b[A-Z][\w\s&]+)",
                    "confidence": 0.80
                }
            ],
            RelationshipType.LOCATED_IN: [
                {
                    "name": "located_in_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+(?:is\s+)?(?:located\s+)?in\s+(\b[A-Z][\w\s]+)",
                    "confidence": 0.75
                },
                {
                    "name": "based_in_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+based\s+in\s+(\b[A-Z][\w\s]+)",
                    "confidence": 0.80
                }
            ],
            RelationshipType.CREATED_BY: [
                {
                    "name": "created_by_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+(?:was\s+)?(?:created|developed|built|made)\s+by\s+(\b[A-Z][\w\s]+)",
                    "confidence": 0.85
                },
                {
                    "name": "author_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+by\s+(\b[A-Z][a-z]+ [A-Z][a-z]+)",
                    "confidence": 0.70
                }
            ],
            RelationshipType.PART_OF: [
                {
                    "name": "part_of_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+(?:is\s+)?(?:a\s+)?part\s+of\s+(\b[A-Z][\w\s]+)",
                    "confidence": 0.80
                },
                {
                    "name": "member_of_pattern",
                    "pattern": r"(\b[A-Z][\w\s]+)\s+(?:is\s+)?(?:a\s+)?member\s+of\s+(\b[A-Z][\w\s]+)",
                    "confidence": 0.75
                }
            ]
        }

    def _initialize_transformer_patterns(self) -> dict[str, Any]:
        """Initialize enhanced patterns for transformer-based detection"""
        return {
            "semantic_similarity_threshold": 0.8,
            "contextual_patterns": {
                "causation": ["because", "therefore", "thus", "hence", "consequently", "as a result"],
                "comparison": ["similarly", "likewise", "in contrast", "however", "whereas"],
                "sequence": ["first", "then", "next", "finally", "subsequently", "afterwards"],
                "elaboration": ["specifically", "namely", "in particular", "for example", "such as"],
            },
            "entity_role_patterns": {
                "agent": ["performed", "conducted", "executed", "initiated", "completed"],
                "patient": ["received", "underwent", "experienced", "suffered", "benefited from"],
                "instrument": ["using", "with", "through", "via", "by means of"],
            }
        }

    def detect_transformer_relationships(self, doc: Any, entities: list[Entity]) -> list[Relationship]:
        """
        Use transformer embeddings to detect semantic relationships

        Args:
            doc: SpaCy document with transformer embeddings
            entities: List of entities

        Returns:
            List of detected relationships
        """
        relationships = []

        if not hasattr(doc, "_.trf_data"):
            return relationships

        # Create entity spans
        entity_spans = self._create_entity_spans(doc, entities)

        for i, (entity1, span1) in enumerate(entity_spans):
            for _j, (entity2, span2) in enumerate(entity_spans[i+1:], i+1):
                # Get transformer embeddings for entities
                if hasattr(span1, "_.trf_data") and hasattr(span2, "_.trf_data"):
                    # Calculate semantic similarity using transformer embeddings
                    similarity = span1.similarity(span2)

                    if similarity > self.transformer_patterns["semantic_similarity_threshold"]:
                        # High semantic similarity suggests relationship
                        rel_type = RelationshipType.SIMILAR_TO
                        confidence = similarity

                        # Check contextual patterns for more specific relationship types
                        context_between = doc[span1.end:span2.start].text.lower()

                        for rel_category, keywords in self.transformer_patterns["contextual_patterns"].items():
                            if any(keyword in context_between for keyword in keywords):
                                if rel_category == "causation":
                                    rel_type = RelationshipType.CAUSAL
                                elif rel_category == "sequence":
                                    rel_type = RelationshipType.TEMPORAL_AFTER
                                confidence = min(0.95, similarity + 0.1)
                                break

                        relationships.append(Relationship(
                            source=entity1,
                            target=entity2,
                            type=rel_type,
                            confidence=confidence,
                            evidence=doc[span1.start:span2.end].text,
                            metadata={
                                "detection_method": "transformer_similarity",
                                "similarity_score": float(similarity)
                            }
                        ))

        return relationships

    def get_relationship_statistics(self, relationships: list[Relationship]) -> dict[str, Any]:
        """Get statistics about detected relationships"""
        if not relationships:
            return {
                "total_relationships": 0,
                "relationship_types": {},
                "confidence_stats": {},
                "detection_methods": {}
            }

        # Count by type
        type_counts = defaultdict(int)
        for rel in relationships:
            type_counts[rel.type.value] += 1

        # Confidence statistics
        confidences = [r.confidence for r in relationships]
        confidence_stats = {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "high_confidence": len([c for c in confidences if c >= 0.8])
        }

        # Detection method statistics
        method_counts = defaultdict(int)
        for rel in relationships:
            method = rel.metadata.get("detection_method", "unknown")
            method_counts[method] += 1

        return {
            "total_relationships": len(relationships),
            "relationship_types": dict(type_counts),
            "confidence_stats": confidence_stats,
            "detection_methods": dict(method_counts),
            "avg_evidence_length": sum(len(r.evidence or "") for r in relationships) / len(relationships)
        }
