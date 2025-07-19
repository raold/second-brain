#!/usr/bin/env python3
"""
Cross-Memory-Type Relationship Engine for Second Brain
Models complex relationships between semantic, episodic, and procedural memories
"""

import asyncio
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Types of relationships between memories"""

    # Semantic relationships
    CONCEPTUAL = "conceptual"  # Related concepts/topics
    HIERARCHICAL = "hierarchical"  # Parent-child knowledge
    CAUSAL = "causal"  # Cause-effect relationships
    TEMPORAL = "temporal"  # Time-based sequences
    SPATIAL = "spatial"  # Location-based connections

    # Cross-type relationships
    INSTANTIATION = "instantiation"  # Semantic → Episodic (concept to experience)
    GENERALIZATION = "generalization"  # Episodic → Semantic (experience to concept)
    PROCEDURALIZATION = "proceduralization"  # Semantic → Procedural (knowledge to skill)
    CONTEXTUALIZATION = "contextualization"  # Procedural → Episodic (skill in context)

    # Process relationships
    PREREQUISITE = "prerequisite"  # Required knowledge/skill
    IMPLEMENTATION = "implementation"  # How concept is executed
    VALIDATION = "validation"  # Evidence supporting concept
    CONTRADICTION = "contradiction"  # Conflicting information


class RelationshipStrength(Enum):
    """Strength levels for memory relationships"""

    WEAK = "weak"  # 0.0-0.3 - Loose association
    MODERATE = "moderate"  # 0.3-0.6 - Clear connection
    STRONG = "strong"  # 0.6-0.8 - Important relationship
    CRITICAL = "critical"  # 0.8-1.0 - Essential connection


class MemoryRole(Enum):
    """Roles memories can play in relationships"""

    SOURCE = "source"  # Initiating memory
    TARGET = "target"  # Referenced memory
    BRIDGE = "bridge"  # Connecting different domains
    HUB = "hub"  # Central to many relationships
    PERIPHERAL = "peripheral"  # Few connections


@dataclass
class MemoryNode:
    """Represents a memory in the relationship network"""

    memory_id: str
    memory_type: str  # semantic, episodic, procedural
    content: str
    keywords: set[str] = field(default_factory=set)
    concepts: set[str] = field(default_factory=set)
    entities: set[str] = field(default_factory=set)
    embedding: Optional[list[float]] = None
    importance_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRelationship:
    """Represents a relationship between two memories"""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    strength: float
    confidence: float
    created_at: datetime
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_strength_category(self) -> RelationshipStrength:
        """Get categorical strength level"""
        if self.strength >= 0.8:
            return RelationshipStrength.CRITICAL
        elif self.strength >= 0.6:
            return RelationshipStrength.STRONG
        elif self.strength >= 0.3:
            return RelationshipStrength.MODERATE
        else:
            return RelationshipStrength.WEAK


@dataclass
class KnowledgeCluster:
    """Represents a cluster of related memories"""

    cluster_id: str
    name: str
    memory_ids: set[str]
    dominant_type: str
    coherence_score: float
    keywords: set[str]
    created_at: datetime


@dataclass
class CrossTypePattern:
    """Represents patterns in cross-memory-type relationships"""

    pattern_name: str
    source_type: str
    target_type: str
    relationship_types: list[RelationshipType]
    frequency: int
    strength_avg: float
    examples: list[tuple[str, str]]


class CrossMemoryRelationshipEngine:
    """
    Advanced system for modeling and analyzing cross-memory-type relationships.

    Features:
    - Automatic relationship detection between memory types
    - Semantic similarity analysis using embeddings
    - Knowledge graph construction and analysis
    - Cross-type learning patterns identification
    - Relationship strength calculation
    - Knowledge cluster discovery
    - Memory role classification
    - Relationship evolution tracking
    """

    def __init__(self, database=None):
        self.database = database
        self.memory_nodes: dict[str, MemoryNode] = {}
        self.relationships: list[MemoryRelationship] = []
        self.knowledge_clusters: dict[str, KnowledgeCluster] = {}
        self.cross_type_patterns: list[CrossTypePattern] = []

        # Relationship detection thresholds
        self.similarity_threshold = 0.3
        self.entity_overlap_threshold = 0.2
        self.keyword_overlap_threshold = 0.15

    async def analyze_memory_relationships(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Comprehensive analysis of cross-memory-type relationships.

        Args:
            memories: List of memory dictionaries with content, type, etc.

        Returns:
            Complete relationship analysis results
        """
        # Build memory network
        await self._build_memory_network(memories)

        # Detect relationships
        await self._detect_relationships()

        # Analyze cross-type patterns
        cross_patterns = self._analyze_cross_type_patterns()

        # Discover knowledge clusters
        clusters = await self._discover_knowledge_clusters()

        # Calculate network metrics
        network_metrics = self._calculate_network_metrics()

        # Identify memory roles
        memory_roles = self._classify_memory_roles()

        # Generate insights
        insights = self._generate_relationship_insights()

        return {
            "total_memories": len(self.memory_nodes),
            "total_relationships": len(self.relationships),
            "cross_type_patterns": cross_patterns,
            "knowledge_clusters": clusters,
            "network_metrics": network_metrics,
            "memory_roles": memory_roles,
            "insights": insights,
            "relationship_matrix": self._build_relationship_matrix(),
        }

    async def _build_memory_network(self, memories: list[dict[str, Any]]):
        """Build network of memory nodes with extracted features"""
        self.memory_nodes.clear()

        for memory in memories:
            memory_id = memory.get("id", "")
            content = memory.get("content", "")
            memory_type = memory.get("memory_type", "semantic")

            # Extract features from content
            keywords = self._extract_keywords(content)
            concepts = self._extract_concepts(content, memory_type)
            entities = self._extract_entities(content)

            # Create memory node
            node = MemoryNode(
                memory_id=memory_id,
                memory_type=memory_type,
                content=content,
                keywords=keywords,
                concepts=concepts,
                entities=entities,
                importance_score=memory.get("importance_score", 0.5),
                created_at=datetime.fromisoformat(memory.get("created_at", datetime.now().isoformat())),
                metadata=memory.get("metadata", {}),
            )

            # Add embedding if available
            if "embedding" in memory:
                node.embedding = memory["embedding"]

            self.memory_nodes[memory_id] = node

    async def _detect_relationships(self):
        """Detect relationships between memories using multiple methods"""
        self.relationships.clear()

        memory_list = list(self.memory_nodes.values())

        for i, source_memory in enumerate(memory_list):
            for target_memory in memory_list[i + 1 :]:
                # Skip same memory
                if source_memory.memory_id == target_memory.memory_id:
                    continue

                # Detect various relationship types
                relationships = await self._detect_memory_pair_relationships(source_memory, target_memory)

                self.relationships.extend(relationships)

    async def _detect_memory_pair_relationships(
        self, source: MemoryNode, target: MemoryNode
    ) -> list[MemoryRelationship]:
        """Detect all relationships between a pair of memories"""
        relationships = []

        # 1. Semantic similarity (for all types)
        if source.embedding and target.embedding:
            similarity = self._calculate_semantic_similarity(source, target)
            if similarity > self.similarity_threshold:
                rel_type = self._determine_semantic_relationship_type(source, target)
                relationships.append(
                    MemoryRelationship(
                        source_id=source.memory_id,
                        target_id=target.memory_id,
                        relationship_type=rel_type,
                        strength=similarity,
                        confidence=0.7,
                        created_at=datetime.now(),
                        evidence=[f"Semantic similarity: {similarity:.3f}"],
                    )
                )

        # 2. Entity overlap
        entity_overlap = self._calculate_entity_overlap(source, target)
        if entity_overlap > self.entity_overlap_threshold:
            relationships.append(
                MemoryRelationship(
                    source_id=source.memory_id,
                    target_id=target.memory_id,
                    relationship_type=RelationshipType.CONCEPTUAL,
                    strength=entity_overlap,
                    confidence=0.6,
                    created_at=datetime.now(),
                    evidence=[f"Entity overlap: {entity_overlap:.3f}"],
                )
            )

        # 3. Cross-type specific relationships
        cross_rel = self._detect_cross_type_relationship(source, target)
        if cross_rel:
            relationships.append(cross_rel)

        # 4. Temporal relationships
        temporal_rel = self._detect_temporal_relationship(source, target)
        if temporal_rel:
            relationships.append(temporal_rel)

        # 5. Causal relationships
        causal_rel = self._detect_causal_relationship(source, target)
        if causal_rel:
            relationships.append(causal_rel)

        return relationships

    def _calculate_semantic_similarity(self, source: MemoryNode, target: MemoryNode) -> float:
        """Calculate semantic similarity using embeddings"""
        if not source.embedding or not target.embedding:
            return 0.0

        source_emb = np.array(source.embedding).reshape(1, -1)
        target_emb = np.array(target.embedding).reshape(1, -1)

        similarity = cosine_similarity(source_emb, target_emb)[0, 0]
        return max(0.0, similarity)  # Ensure non-negative

    def _calculate_entity_overlap(self, source: MemoryNode, target: MemoryNode) -> float:
        """Calculate overlap between entities mentioned in memories"""
        if not source.entities or not target.entities:
            return 0.0

        intersection = source.entities & target.entities
        union = source.entities | target.entities

        return len(intersection) / len(union) if union else 0.0

    def _detect_cross_type_relationship(self, source: MemoryNode, target: MemoryNode) -> Optional[MemoryRelationship]:
        """Detect cross-memory-type relationships"""
        source_type = source.memory_type
        target_type = target.memory_type

        if source_type == target_type:
            return None

        # Define cross-type relationship patterns
        patterns = {
            ("semantic", "episodic"): RelationshipType.INSTANTIATION,
            ("episodic", "semantic"): RelationshipType.GENERALIZATION,
            ("semantic", "procedural"): RelationshipType.PROCEDURALIZATION,
            ("procedural", "episodic"): RelationshipType.CONTEXTUALIZATION,
            ("procedural", "semantic"): RelationshipType.IMPLEMENTATION,
            ("episodic", "procedural"): RelationshipType.VALIDATION,
        }

        relationship_type = patterns.get((source_type, target_type))
        if not relationship_type:
            return None

        # Calculate strength based on content analysis
        strength = self._calculate_cross_type_strength(source, target, relationship_type)

        if strength > 0.2:  # Minimum threshold for cross-type relationships
            return MemoryRelationship(
                source_id=source.memory_id,
                target_id=target.memory_id,
                relationship_type=relationship_type,
                strength=strength,
                confidence=0.8,
                created_at=datetime.now(),
                evidence=[f"Cross-type pattern: {source_type} → {target_type}"],
            )

        return None

    def _calculate_cross_type_strength(
        self, source: MemoryNode, target: MemoryNode, rel_type: RelationshipType
    ) -> float:
        """Calculate strength of cross-type relationship"""
        base_strength = 0.3

        # Keyword overlap bonus
        keyword_overlap = len(source.keywords & target.keywords)
        if source.keywords and target.keywords:
            keyword_bonus = keyword_overlap / max(len(source.keywords), len(target.keywords))
        else:
            keyword_bonus = 0.0

        # Concept overlap bonus
        concept_overlap = len(source.concepts & target.concepts)
        if source.concepts and target.concepts:
            concept_bonus = concept_overlap / max(len(source.concepts), len(target.concepts))
        else:
            concept_bonus = 0.0

        # Content length factor (longer content = more potential for relationships)
        length_factor = min(1.0, (len(source.content) + len(target.content)) / 1000)

        # Relationship type specific bonuses
        type_bonus = {
            RelationshipType.INSTANTIATION: 0.1 if "example" in target.content.lower() else 0.0,
            RelationshipType.GENERALIZATION: 0.1 if "pattern" in source.content.lower() else 0.0,
            RelationshipType.PROCEDURALIZATION: 0.1 if "step" in target.content.lower() else 0.0,
            RelationshipType.CONTEXTUALIZATION: 0.1 if "experience" in target.content.lower() else 0.0,
        }.get(rel_type, 0.0)

        total_strength = (
            base_strength + (keyword_bonus * 0.3) + (concept_bonus * 0.2) + (length_factor * 0.1) + type_bonus
        )
        return min(1.0, total_strength)

    def _detect_temporal_relationship(self, source: MemoryNode, target: MemoryNode) -> Optional[MemoryRelationship]:
        """Detect temporal relationships between memories"""
        # Look for temporal indicators in content
        temporal_patterns = [
            r"\b(before|after|then|next|subsequently|previously|later)\b",
            r"\b(\d{4}|\d{1,2}/\d{1,2}|\d{1,2}-\d{1,2})\b",
            r"\b(first|second|third|finally|initially|ultimately)\b",
        ]

        source_has_temporal = any(re.search(pattern, source.content, re.IGNORECASE) for pattern in temporal_patterns)
        target_has_temporal = any(re.search(pattern, target.content, re.IGNORECASE) for pattern in temporal_patterns)

        if source_has_temporal and target_has_temporal:
            # Calculate temporal relationship strength
            time_diff = abs((source.created_at - target.created_at).days)

            # Closer in time = stronger temporal relationship
            strength = max(0.2, 1.0 - (time_diff / 365))  # Decay over a year

            return MemoryRelationship(
                source_id=source.memory_id,
                target_id=target.memory_id,
                relationship_type=RelationshipType.TEMPORAL,
                strength=strength,
                confidence=0.6,
                created_at=datetime.now(),
                evidence=[f"Temporal indicators present, {time_diff} days apart"],
            )

        return None

    def _detect_causal_relationship(self, source: MemoryNode, target: MemoryNode) -> Optional[MemoryRelationship]:
        """Detect causal relationships between memories"""
        causal_patterns = [
            r"\b(because|since|due to|caused by|results in|leads to)\b",
            r"\b(therefore|thus|consequently|as a result)\b",
            r"\b(if.*then|when.*then)\b",
        ]

        source_causal = any(re.search(pattern, source.content, re.IGNORECASE) for pattern in causal_patterns)
        target_causal = any(re.search(pattern, target.content, re.IGNORECASE) for pattern in causal_patterns)

        if source_causal or target_causal:
            # Calculate causal relationship strength
            keyword_overlap = len(source.keywords & target.keywords)
            total_keywords = len(source.keywords | target.keywords)

            if total_keywords > 0:
                strength = 0.3 + (keyword_overlap / total_keywords) * 0.5

                return MemoryRelationship(
                    source_id=source.memory_id,
                    target_id=target.memory_id,
                    relationship_type=RelationshipType.CAUSAL,
                    strength=strength,
                    confidence=0.7,
                    created_at=datetime.now(),
                    evidence=[f"Causal language detected, {keyword_overlap} shared keywords"],
                )

        return None

    def _extract_keywords(self, content: str) -> set[str]:
        """Extract keywords from content"""
        # Simple keyword extraction (in production, use more sophisticated NLP)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", content.lower())

        # Filter out common stop words
        stop_words = {
            "the",
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
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "from",
            "into",
            "about",
        }

        keywords = {word for word in words if word not in stop_words and len(word) > 3}

        # Return top keywords by frequency
        word_freq = Counter(words)
        top_keywords = {word for word, freq in word_freq.most_common(20) if word in keywords}

        return top_keywords

    def _extract_concepts(self, content: str, memory_type: str) -> set[str]:
        """Extract concepts based on memory type"""
        concepts = set()

        # Technical concepts
        tech_patterns = [
            r"\b(API|database|algorithm|function|class|method|framework)\b",
            r"\b(optimization|performance|architecture|design|pattern)\b",
            r"\b(security|authentication|authorization|encryption)\b",
        ]

        # Business concepts
        business_patterns = [
            r"\b(strategy|process|workflow|methodology|approach)\b",
            r"\b(goal|objective|requirement|specification|criteria)\b",
            r"\b(project|task|deliverable|milestone|deadline)\b",
        ]

        # Memory type specific patterns
        if memory_type == "procedural":
            patterns = tech_patterns + [
                r"\b(step|procedure|instruction|guideline|protocol)\b",
                r"\b(implement|execute|perform|configure|setup)\b",
            ]
        elif memory_type == "episodic":
            patterns = [
                r"\b(meeting|discussion|decision|outcome|result)\b",
                r"\b(experience|event|situation|context|scenario)\b",
            ] + business_patterns
        else:  # semantic
            patterns = (
                tech_patterns
                + business_patterns
                + [
                    r"\b(concept|principle|theory|model|framework)\b",
                    r"\b(definition|explanation|description|analysis)\b",
                ]
            )

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            concepts.update(match.lower() for match in matches)

        return concepts

    def _extract_entities(self, content: str) -> set[str]:
        """Extract named entities from content"""
        entities = set()

        # Simple entity patterns (in production, use NER models)
        patterns = [
            r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # Person names
            r"\b[A-Z][a-zA-Z]+ Inc\b|\b[A-Z][a-zA-Z]+ Corp\b",  # Companies
            r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:API|Framework|Library)\b",  # Tech products
            r"\bversion \d+\.\d+\b|\bv\d+\.\d+\b",  # Versions
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            entities.update(matches)

        return entities

    def _determine_semantic_relationship_type(self, source: MemoryNode, target: MemoryNode) -> RelationshipType:
        """Determine the type of semantic relationship"""
        # Check for hierarchical patterns
        hierarchical_patterns = [
            r"\b(parent|child|inherit|extend|implement)\b",
            r"\b(category|subcategory|type|subtype)\b",
            r"\b(general|specific|abstract|concrete)\b",
        ]

        has_hierarchical = any(
            re.search(pattern, source.content + target.content, re.IGNORECASE) for pattern in hierarchical_patterns
        )

        if has_hierarchical:
            return RelationshipType.HIERARCHICAL

        # Check for causal patterns
        causal_patterns = [r"\b(cause|effect|result|consequence)\b", r"\b(because|therefore|thus|hence)\b"]

        has_causal = any(
            re.search(pattern, source.content + target.content, re.IGNORECASE) for pattern in causal_patterns
        )

        if has_causal:
            return RelationshipType.CAUSAL

        # Default to conceptual
        return RelationshipType.CONCEPTUAL

    def _analyze_cross_type_patterns(self) -> list[dict[str, Any]]:
        """Analyze patterns in cross-memory-type relationships"""
        pattern_stats = defaultdict(lambda: {"count": 0, "strengths": [], "examples": []})

        for rel in self.relationships:
            source_node = self.memory_nodes[rel.source_id]
            target_node = self.memory_nodes[rel.target_id]

            if source_node.memory_type != target_node.memory_type:
                pattern_key = f"{source_node.memory_type} → {target_node.memory_type}"
                pattern_stats[pattern_key]["count"] += 1
                pattern_stats[pattern_key]["strengths"].append(rel.strength)

                if len(pattern_stats[pattern_key]["examples"]) < 3:
                    pattern_stats[pattern_key]["examples"].append(
                        {
                            "source_id": rel.source_id,
                            "target_id": rel.target_id,
                            "relationship_type": rel.relationship_type.value,
                            "strength": rel.strength,
                        }
                    )

        patterns = []
        for pattern, stats in pattern_stats.items():
            if stats["count"] > 0:
                patterns.append(
                    {
                        "pattern": pattern,
                        "frequency": stats["count"],
                        "average_strength": sum(stats["strengths"]) / len(stats["strengths"]),
                        "examples": stats["examples"],
                    }
                )

        return sorted(patterns, key=lambda x: x["frequency"], reverse=True)

    async def _discover_knowledge_clusters(self) -> list[dict[str, Any]]:
        """Discover clusters of related memories"""
        # Group memories by strong relationships
        clusters = []
        visited = set()

        for memory_id, memory_node in self.memory_nodes.items():
            if memory_id in visited:
                continue

            # Find connected memories
            cluster_memories = self._find_connected_memories(memory_id, visited)

            if len(cluster_memories) >= 2:  # Minimum cluster size
                cluster_keywords = set()
                memory_types = Counter()

                for mem_id in cluster_memories:
                    node = self.memory_nodes[mem_id]
                    cluster_keywords.update(node.keywords)
                    memory_types[node.memory_type] += 1
                    visited.add(mem_id)

                dominant_type = memory_types.most_common(1)[0][0]

                clusters.append(
                    {
                        "cluster_id": f"cluster_{len(clusters) + 1}",
                        "memory_count": len(cluster_memories),
                        "memory_ids": list(cluster_memories),
                        "dominant_type": dominant_type,
                        "type_distribution": dict(memory_types),
                        "top_keywords": list(cluster_keywords)[:10],
                        "coherence_score": self._calculate_cluster_coherence(cluster_memories),
                    }
                )

        return sorted(clusters, key=lambda x: x["coherence_score"], reverse=True)

    def _find_connected_memories(self, start_id: str, visited: set[str]) -> set[str]:
        """Find all memories connected to a starting memory"""
        connected = {start_id}
        queue = [start_id]

        while queue:
            current_id = queue.pop(0)

            # Find relationships involving current memory
            for rel in self.relationships:
                if rel.strength < 0.4:  # Only consider moderate+ relationships
                    continue

                other_id = None
                if rel.source_id == current_id and rel.target_id not in visited:
                    other_id = rel.target_id
                elif rel.target_id == current_id and rel.source_id not in visited:
                    other_id = rel.source_id

                if other_id and other_id not in connected:
                    connected.add(other_id)
                    queue.append(other_id)

        return connected

    def _calculate_cluster_coherence(self, memory_ids: set[str]) -> float:
        """Calculate coherence score for a memory cluster"""
        if len(memory_ids) < 2:
            return 0.0

        # Calculate average relationship strength within cluster
        internal_relationships = [
            rel for rel in self.relationships if rel.source_id in memory_ids and rel.target_id in memory_ids
        ]

        if not internal_relationships:
            return 0.0

        avg_strength = sum(rel.strength for rel in internal_relationships) / len(internal_relationships)

        # Bonus for cross-type relationships (more interesting clusters)
        cross_type_bonus = 0.0
        memory_types = {self.memory_nodes[mem_id].memory_type for mem_id in memory_ids}
        if len(memory_types) > 1:
            cross_type_bonus = 0.2

        return min(1.0, avg_strength + cross_type_bonus)

    def _calculate_network_metrics(self) -> dict[str, Any]:
        """Calculate various network analysis metrics"""
        if not self.memory_nodes or not self.relationships:
            return {"error": "Insufficient data for network analysis"}

        # Basic metrics
        total_nodes = len(self.memory_nodes)
        total_edges = len(self.relationships)

        # Density: actual edges / possible edges
        max_edges = total_nodes * (total_nodes - 1) / 2
        density = total_edges / max_edges if max_edges > 0 else 0

        # Degree distribution
        node_degrees = defaultdict(int)
        for rel in self.relationships:
            node_degrees[rel.source_id] += 1
            node_degrees[rel.target_id] += 1

        avg_degree = sum(node_degrees.values()) / total_nodes if total_nodes > 0 else 0
        max_degree = max(node_degrees.values()) if node_degrees else 0

        # Cross-type relationship ratio
        cross_type_count = sum(
            1
            for rel in self.relationships
            if self.memory_nodes[rel.source_id].memory_type != self.memory_nodes[rel.target_id].memory_type
        )
        cross_type_ratio = cross_type_count / total_edges if total_edges > 0 else 0

        # Strength distribution
        strengths = [rel.strength for rel in self.relationships]
        avg_strength = sum(strengths) / len(strengths) if strengths else 0

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "network_density": density,
            "average_degree": avg_degree,
            "max_degree": max_degree,
            "cross_type_ratio": cross_type_ratio,
            "average_strength": avg_strength,
            "strong_relationships": sum(1 for s in strengths if s >= 0.6),
            "weak_relationships": sum(1 for s in strengths if s < 0.3),
        }

    def _classify_memory_roles(self) -> dict[str, list[str]]:
        """Classify memories by their role in the network"""
        roles = {"hubs": [], "bridges": [], "specialists": [], "isolates": []}

        # Calculate degree for each memory
        node_degrees = defaultdict(int)
        cross_type_connections = defaultdict(int)

        for rel in self.relationships:
            node_degrees[rel.source_id] += 1
            node_degrees[rel.target_id] += 1

            # Count cross-type connections
            source_type = self.memory_nodes[rel.source_id].memory_type
            target_type = self.memory_nodes[rel.target_id].memory_type
            if source_type != target_type:
                cross_type_connections[rel.source_id] += 1
                cross_type_connections[rel.target_id] += 1

        # Classify nodes
        avg_degree = sum(node_degrees.values()) / len(node_degrees) if node_degrees else 0

        for memory_id in self.memory_nodes:
            degree = node_degrees[memory_id]
            cross_connections = cross_type_connections[memory_id]

            if degree == 0:
                roles["isolates"].append(memory_id)
            elif degree > avg_degree * 2:
                roles["hubs"].append(memory_id)
            elif cross_connections >= 2:
                roles["bridges"].append(memory_id)
            else:
                roles["specialists"].append(memory_id)

        return roles

    def _generate_relationship_insights(self) -> list[str]:
        """Generate insights about the relationship network"""
        insights = []

        if not self.relationships:
            return ["No relationships detected in the memory network"]

        # Cross-type analysis
        cross_type_rels = [
            rel
            for rel in self.relationships
            if self.memory_nodes[rel.source_id].memory_type != self.memory_nodes[rel.target_id].memory_type
        ]

        cross_type_ratio = len(cross_type_rels) / len(self.relationships)

        if cross_type_ratio > 0.4:
            insights.append(
                f"High cross-type connectivity ({cross_type_ratio:.1%}) indicates rich knowledge integration"
            )
        elif cross_type_ratio < 0.1:
            insights.append("Low cross-type connectivity suggests siloed knowledge domains")

        # Strength analysis
        strong_rels = [rel for rel in self.relationships if rel.strength >= 0.6]
        if strong_rels:
            strong_ratio = len(strong_rels) / len(self.relationships)
            insights.append(f"{strong_ratio:.1%} of relationships are strong, indicating well-connected knowledge")

        # Memory type distribution
        type_counts = Counter(node.memory_type for node in self.memory_nodes.values())
        dominant_type = type_counts.most_common(1)[0][0]
        insights.append(
            f"Knowledge base is dominated by {dominant_type} memories ({type_counts[dominant_type]} of {len(self.memory_nodes)})"
        )

        # Hub analysis
        node_degrees = defaultdict(int)
        for rel in self.relationships:
            node_degrees[rel.source_id] += 1
            node_degrees[rel.target_id] += 1

        if node_degrees:
            max_degree = max(node_degrees.values())
            hub_memories = [mem_id for mem_id, degree in node_degrees.items() if degree == max_degree]
            if hub_memories:
                insights.append(f"Memory hub detected with {max_degree} connections")

        return insights

    def _build_relationship_matrix(self) -> dict[str, dict[str, int]]:
        """Build matrix showing relationships between memory types"""
        matrix = {
            "semantic": {"semantic": 0, "episodic": 0, "procedural": 0},
            "episodic": {"semantic": 0, "episodic": 0, "procedural": 0},
            "procedural": {"semantic": 0, "episodic": 0, "procedural": 0},
        }

        for rel in self.relationships:
            source_type = self.memory_nodes[rel.source_id].memory_type
            target_type = self.memory_nodes[rel.target_id].memory_type
            matrix[source_type][target_type] += 1

        return matrix

    async def get_memory_relationships(self, memory_id: str) -> dict[str, Any]:
        """Get all relationships for a specific memory"""
        if memory_id not in self.memory_nodes:
            return {"error": "Memory not found"}

        memory_node = self.memory_nodes[memory_id]
        related_memories = []

        for rel in self.relationships:
            if rel.source_id == memory_id:
                target_node = self.memory_nodes[rel.target_id]
                related_memories.append(
                    {
                        "memory_id": rel.target_id,
                        "memory_type": target_node.memory_type,
                        "relationship_type": rel.relationship_type.value,
                        "strength": rel.strength,
                        "direction": "outgoing",
                        "content_preview": target_node.content[:100] + "...",
                    }
                )
            elif rel.target_id == memory_id:
                source_node = self.memory_nodes[rel.source_id]
                related_memories.append(
                    {
                        "memory_id": rel.source_id,
                        "memory_type": source_node.memory_type,
                        "relationship_type": rel.relationship_type.value,
                        "strength": rel.strength,
                        "direction": "incoming",
                        "content_preview": source_node.content[:100] + "...",
                    }
                )

        # Sort by strength
        related_memories.sort(key=lambda x: x["strength"], reverse=True)

        return {
            "memory_id": memory_id,
            "memory_type": memory_node.memory_type,
            "total_relationships": len(related_memories),
            "related_memories": related_memories[:20],  # Top 20
            "cross_type_count": len([r for r in related_memories if r["memory_type"] != memory_node.memory_type]),
        }


# Example usage and testing
async def demo_cross_memory_relationships():
    """Demonstrate cross-memory-type relationship analysis"""
    print("🧠 Cross-Memory-Type Relationship Analysis Demo")
    print("=" * 55)

    # Sample memories of different types
    sample_memories = [
        {
            "id": "sem_001",
            "memory_type": "semantic",
            "content": "Machine learning algorithms are computational methods that enable systems to learn patterns from data without explicit programming. Key types include supervised learning (classification, regression), unsupervised learning (clustering, dimensionality reduction), and reinforcement learning.",
            "created_at": "2024-01-01T10:00:00",
        },
        {
            "id": "proc_001",
            "memory_type": "procedural",
            "content": "To implement a neural network: 1) Define the architecture (layers, neurons, activation functions), 2) Initialize weights randomly, 3) Forward propagation - compute predictions, 4) Calculate loss using cost function, 5) Backpropagation - compute gradients, 6) Update weights using optimizer, 7) Repeat until convergence.",
            "created_at": "2024-01-02T14:00:00",
        },
        {
            "id": "ep_001",
            "memory_type": "episodic",
            "content": "During the team meeting on January 15th, we discussed implementing a recommendation system. Sarah demonstrated the neural network approach achieving 85% accuracy on the test dataset. The team decided to proceed with this solution for the production deployment.",
            "created_at": "2024-01-15T09:00:00",
        },
        {
            "id": "sem_002",
            "memory_type": "semantic",
            "content": "Neural networks are inspired by biological neurons and consist of interconnected nodes organized in layers. Each connection has a weight that determines the strength of signal transmission. Training involves adjusting these weights to minimize prediction errors.",
            "created_at": "2024-01-03T11:00:00",
        },
        {
            "id": "proc_002",
            "memory_type": "procedural",
            "content": "Database optimization steps: 1) Analyze query performance using EXPLAIN, 2) Identify slow queries in logs, 3) Create appropriate indexes on frequently queried columns, 4) Optimize JOIN operations, 5) Consider query rewriting, 6) Monitor performance improvements.",
            "created_at": "2024-01-05T16:00:00",
        },
        {
            "id": "ep_002",
            "memory_type": "episodic",
            "content": "The database performance issue we experienced last week was resolved by adding a composite index on the user_id and timestamp columns. Query time decreased from 2.3 seconds to 150ms, significantly improving user experience.",
            "created_at": "2024-01-20T13:00:00",
        },
    ]

    # Initialize relationship engine
    engine = CrossMemoryRelationshipEngine()

    # Analyze relationships
    print("\n🔍 Analyzing Cross-Memory-Type Relationships...")
    analysis = await engine.analyze_memory_relationships(sample_memories)

    print("\n📊 Network Statistics:")
    print(f"   Total Memories: {analysis['total_memories']}")
    print(f"   Total Relationships: {analysis['total_relationships']}")

    # Display network metrics
    if "network_metrics" in analysis:
        metrics = analysis["network_metrics"]
        print(f"   Network Density: {metrics.get('network_density', 0):.3f}")
        print(f"   Cross-Type Ratio: {metrics.get('cross_type_ratio', 0):.3f}")
        print(f"   Average Strength: {metrics.get('average_strength', 0):.3f}")

    # Display cross-type patterns
    print("\n🔗 Cross-Type Relationship Patterns:")
    for pattern in analysis.get("cross_type_patterns", []):
        print(
            f"   {pattern['pattern']}: {pattern['frequency']} relationships (avg strength: {pattern['average_strength']:.3f})"
        )

    # Display knowledge clusters
    print("\n🧩 Knowledge Clusters:")
    for cluster in analysis.get("knowledge_clusters", []):
        print(f"   Cluster {cluster['cluster_id']}: {cluster['memory_count']} memories")
        print(f"      Dominant Type: {cluster['dominant_type']}")
        print(f"      Coherence: {cluster['coherence_score']:.3f}")
        print(f"      Keywords: {', '.join(cluster['top_keywords'][:5])}")

    # Display memory roles
    print("\n👥 Memory Roles:")
    roles = analysis.get("memory_roles", {})
    for role, memories in roles.items():
        if memories:
            print(f"   {role.title()}: {len(memories)} memories")

    # Display insights
    print("\n💡 Key Insights:")
    for insight in analysis.get("insights", []):
        print(f"   • {insight}")

    # Display relationship matrix
    print("\n📈 Relationship Matrix:")
    matrix = analysis.get("relationship_matrix", {})
    if matrix:
        print("        Semantic  Episodic  Procedural")
        for source_type, targets in matrix.items():
            row = f"   {source_type:10}"
            for target_type in ["semantic", "episodic", "procedural"]:
                row += f"{targets.get(target_type, 0):8}"
            print(row)

    # Demonstrate individual memory analysis
    print("\n🔍 Individual Memory Analysis (sem_001):")
    memory_analysis = await engine.get_memory_relationships("sem_001")
    if "related_memories" in memory_analysis:
        print(f"   Total Relationships: {memory_analysis['total_relationships']}")
        print(f"   Cross-Type Connections: {memory_analysis['cross_type_count']}")

        for rel in memory_analysis["related_memories"][:3]:
            print(f"   → {rel['memory_type']} memory ({rel['relationship_type']}, strength: {rel['strength']:.3f})")


if __name__ == "__main__":
    asyncio.run(demo_cross_memory_relationships())
