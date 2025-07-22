"""
Knowledge Graph Builder for Second Brain
Constructs and manages entity-relationship graphs from memories
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.database import Database

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities in the knowledge graph"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    PROJECT = "project"
    EVENT = "event"
    SKILL = "skill"
    TOPIC = "topic"
    OTHER = "other"


class RelationshipType(Enum):
    """Types of relationships between entities"""
    RELATED_TO = "related_to"
    CAUSED_BY = "caused_by"
    LEADS_TO = "leads_to"
    PART_OF = "part_of"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    DEPENDS_ON = "depends_on"
    INFLUENCES = "influences"
    TEMPORAL_BEFORE = "temporal_before"
    TEMPORAL_AFTER = "temporal_after"
    LEARNED_FROM = "learned_from"
    APPLIED_IN = "applied_in"
    EVOLVED_INTO = "evolved_into"
    COMPARED_TO = "compared_to"


@dataclass
class Entity:
    """Represents an entity in the knowledge graph"""
    id: str | None
    name: str
    entity_type: EntityType
    description: str | None = None
    metadata: dict[str, Any] = None
    importance_score: float = 0.5
    occurrence_count: int = 1


@dataclass
class EntityMention:
    """Represents a mention of an entity in a memory"""
    entity: Entity
    memory_id: str
    position_start: int
    position_end: int
    context: str
    confidence: float = 1.0


@dataclass
class Relationship:
    """Represents a relationship between entities"""
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    weight: float = 1.0
    metadata: dict[str, Any] = None


@dataclass
class GraphNode:
    """Node in the knowledge graph for visualization"""
    id: str
    label: str
    type: str
    size: float
    metadata: dict[str, Any]


@dataclass
class GraphEdge:
    """Edge in the knowledge graph for visualization"""
    source: str
    target: str
    type: str
    weight: float
    label: str


class KnowledgeGraphBuilder:
    """
    Builds and manages knowledge graphs from memory content
    """

    def __init__(self, database: Database):
        self.db = database
        self.entity_patterns = self._compile_entity_patterns()
        self.relationship_patterns = self._compile_relationship_patterns()

    def _compile_entity_patterns(self) -> dict[EntityType, list[re.Pattern]]:
        """Compile regex patterns for entity extraction"""
        return {
            EntityType.PERSON: [
                re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),  # Full names
                re.compile(r'\b(?:Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.) [A-Z][a-z]+\b'),  # Titles
            ],
            EntityType.ORGANIZATION: [
                re.compile(r'\b[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*(?:Inc\.|Corp\.|LLC|Ltd\.?)\b'),
                re.compile(r'\b(?:Google|Microsoft|Apple|Amazon|Facebook|Twitter|OpenAI)\b', re.I),
            ],
            EntityType.TECHNOLOGY: [
                re.compile(r'\b(?:Python|JavaScript|React|Node\.js|PostgreSQL|Docker|Kubernetes)\b', re.I),
                re.compile(r'\b(?:AI|ML|NLP|API|REST|GraphQL|SQL)\b'),
            ],
            EntityType.CONCEPT: [
                re.compile(r'\b(?:machine learning|deep learning|neural network|algorithm|data structure)\b', re.I),
                re.compile(r'\b(?:design pattern|architecture|framework|methodology)\b', re.I),
            ],
            EntityType.SKILL: [
                re.compile(r'\b(?:programming|coding|debugging|testing|analysis|design)\b', re.I),
                re.compile(r'\b(?:leadership|communication|problem-solving|critical thinking)\b', re.I),
            ],
        }

    def _compile_relationship_patterns(self) -> dict[RelationshipType, list[re.Pattern]]:
        """Compile regex patterns for relationship extraction"""
        return {
            RelationshipType.CAUSED_BY: [
                re.compile(r'(?:caused by|due to|because of|resulted from)', re.I),
                re.compile(r'(?:led to|resulted in|caused|triggered)', re.I),
            ],
            RelationshipType.DEPENDS_ON: [
                re.compile(r'(?:depends on|requires|needs|relies on)', re.I),
                re.compile(r'(?:based on|built on|uses)', re.I),
            ],
            RelationshipType.PART_OF: [
                re.compile(r'(?:part of|component of|module of|belongs to)', re.I),
                re.compile(r'(?:includes|contains|consists of)', re.I),
            ],
            RelationshipType.LEARNED_FROM: [
                re.compile(r'(?:learned from|studied|took course|read about)', re.I),
                re.compile(r'(?:taught by|mentored by|guided by)', re.I),
            ],
        }

    async def build_graph_from_memories(
        self,
        memory_ids: list[str],
        extract_entities: bool = True,
        extract_relationships: bool = True,
        min_confidence: float = 0.7
    ) -> dict[str, Any]:
        """
        Build a knowledge graph from a set of memories

        Args:
            memory_ids: List of memory IDs to process
            extract_entities: Whether to extract entities
            extract_relationships: Whether to extract relationships
            min_confidence: Minimum confidence threshold

        Returns:
            Graph data with nodes and edges
        """
        # Validate inputs
        if not memory_ids:
            raise ValueError("At least one memory ID is required")

        if len(memory_ids) > 1000:
            raise ValueError("Cannot process more than 1000 memories at once")

        if min_confidence < 0 or min_confidence > 1:
            raise ValueError("min_confidence must be between 0 and 1")

        logger.info(f"Building knowledge graph from {len(memory_ids)} memories")

        # Fetch memories
        memories = []
        for memory_id in memory_ids:
            memory = await self.db.get_memory(memory_id)
            if memory:
                memories.append(memory)

        if not memories:
            logger.warning("No memories found to build graph")
            return {"nodes": [], "edges": [], "stats": {}}

        entities = {}
        relationships = []

        # Extract entities from each memory
        if extract_entities:
            for memory in memories:
                extracted = await self._extract_entities_from_memory(memory)
                for entity_mention in extracted:
                    if entity_mention.confidence >= min_confidence:
                        # Store or update entity
                        entity_key = entity_mention.entity.name.lower()
                        if entity_key in entities:
                            entities[entity_key].occurrence_count += 1
                        else:
                            entities[entity_key] = entity_mention.entity

                        # Store entity mention
                        await self._store_entity_mention(entity_mention)

        # Extract relationships
        if extract_relationships:
            # Between entities in same memory
            for memory in memories:
                memory_entities = await self._get_entities_in_memory(memory["id"])
                if len(memory_entities) >= 2:
                    # Find relationships between entities
                    for i, entity1 in enumerate(memory_entities):
                        for entity2 in memory_entities[i+1:]:
                            rels = await self._extract_entity_relationships(
                                memory["content"], entity1, entity2
                            )
                            relationships.extend(rels)

            # Between memories (co-occurrence based)
            if len(memories) > 1:
                memory_relationships = await self._extract_memory_relationships(memories)
                # Store these separately as they're different from entity relationships
                for rel in memory_relationships:
                    await self._store_memory_relationship(rel)

        # Build graph representation
        graph = await self._build_graph_representation(
            list(entities.values()),
            relationships
        )

        # Calculate graph statistics
        stats = self._calculate_graph_stats(graph)

        # Store graph metadata
        await self._store_graph_metadata(stats)

        return {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "stats": stats,
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }

    async def _extract_entities_from_memory(self, memory: dict[str, Any]) -> list[EntityMention]:
        """Extract entities from a single memory"""
        content = memory["content"]
        memory_id = memory["id"]
        mentions = []

        # Extract using patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(content):
                    entity_name = match.group()
                    start_pos = match.start()
                    end_pos = match.end()

                    # Get context (50 chars before and after)
                    context_start = max(0, start_pos - 50)
                    context_end = min(len(content), end_pos + 50)
                    context = content[context_start:context_end]

                    entity = Entity(
                        id=None,  # Will be assigned when stored
                        name=entity_name,
                        entity_type=entity_type,
                        description=f"Found in memory: {content[:100]}...",
                        metadata={"memory_type": memory.get("memory_type", "unknown")}
                    )

                    mention = EntityMention(
                        entity=entity,
                        memory_id=memory_id,
                        position_start=start_pos,
                        position_end=end_pos,
                        context=context,
                        confidence=0.8  # Pattern-based extraction confidence
                    )

                    mentions.append(mention)

        # Also extract based on NLP patterns (simplified version)
        # In production, you'd use spaCy or similar
        noun_phrases = self._extract_noun_phrases(content)
        for phrase in noun_phrases:
            if self._is_likely_entity(phrase):
                entity = Entity(
                    id=None,
                    name=phrase,
                    entity_type=EntityType.CONCEPT,
                    description=f"Concept from: {content[:100]}...",
                    metadata={}
                )

                # Find position
                pos = content.lower().find(phrase.lower())
                if pos >= 0:
                    mention = EntityMention(
                        entity=entity,
                        memory_id=memory_id,
                        position_start=pos,
                        position_end=pos + len(phrase),
                        context=content[max(0, pos-50):min(len(content), pos+len(phrase)+50)],
                        confidence=0.6
                    )
                    mentions.append(mention)

        return mentions

    def _extract_noun_phrases(self, text: str) -> list[str]:
        """Simple noun phrase extraction"""
        # This is a simplified version - in production use spaCy
        phrases = []

        # Common noun phrase patterns
        patterns = [
            r'\b(?:the |a |an )?[A-Z][a-z]+(?: [A-Z][a-z]+)*\b',
            r'\b[a-z]+ [a-z]+(?:ing|ed|ion|ment|ness|ity)\b',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                phrase = match.group().strip()
                if len(phrase.split()) >= 2 and len(phrase) > 5:
                    phrases.append(phrase)

        return phrases

    def _is_likely_entity(self, phrase: str) -> bool:
        """Check if a phrase is likely an entity"""
        # Simple heuristics
        words = phrase.lower().split()

        # Skip common phrases
        skip_words = {'the', 'a', 'an', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were'}
        if any(word in skip_words for word in words):
            return False

        # Likely entity if it has certain patterns
        if any(word.endswith(('tion', 'ment', 'ing', 'ness', 'ity')) for word in words):
            return True

        # Capitalized phrases are often entities
        if phrase[0].isupper():
            return True

        return False

    async def _extract_entity_relationships(
        self,
        content: str,
        entity1: Entity,
        entity2: Entity
    ) -> list[Relationship]:
        """Extract relationships between two entities in content"""
        relationships = []

        # Check for explicit relationship patterns
        for rel_type, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                # Look for pattern between entities
                text_between = self._get_text_between_entities(
                    content, entity1.name, entity2.name
                )

                if text_between and pattern.search(text_between):
                    rel = Relationship(
                        source_entity_id=entity1.id,
                        target_entity_id=entity2.id,
                        relationship_type=rel_type,
                        confidence=0.8,
                        weight=1.0,
                        metadata={"pattern": pattern.pattern}
                    )
                    relationships.append(rel)

        # If no explicit relationship found, check for co-occurrence
        if not relationships:
            # Calculate semantic similarity between entities
            similarity = self._calculate_entity_similarity(entity1, entity2)

            if similarity > 0.7:
                rel = Relationship(
                    source_entity_id=entity1.id,
                    target_entity_id=entity2.id,
                    relationship_type=RelationshipType.RELATED_TO,
                    confidence=similarity,
                    weight=similarity,
                    metadata={"method": "co-occurrence"}
                )
                relationships.append(rel)

        return relationships

    def _get_text_between_entities(self, content: str, entity1: str, entity2: str) -> str | None:
        """Get text between two entity mentions"""
        # Find positions
        pos1 = content.lower().find(entity1.lower())
        pos2 = content.lower().find(entity2.lower())

        if pos1 >= 0 and pos2 >= 0 and pos1 != pos2:
            start = min(pos1, pos2) + len(entity1 if pos1 < pos2 else entity2)
            end = max(pos1, pos2)
            return content[start:end]

        return None

    def _calculate_entity_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate similarity between two entities"""
        # Simple similarity based on type and name
        similarity = 0.0

        # Same type bonus
        if entity1.entity_type == entity2.entity_type:
            similarity += 0.3

        # Name similarity (simplified)
        name1_words = set(entity1.name.lower().split())
        name2_words = set(entity2.name.lower().split())

        if name1_words & name2_words:  # Common words
            similarity += 0.4

        # Context similarity (if descriptions exist)
        if entity1.description and entity2.description:
            # Simple word overlap
            desc1_words = set(entity1.description.lower().split())
            desc2_words = set(entity2.description.lower().split())

            overlap = len(desc1_words & desc2_words)
            total = len(desc1_words | desc2_words)

            if total > 0:
                similarity += 0.3 * (overlap / total)

        return min(similarity, 1.0)

    async def _extract_memory_relationships(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract relationships between memories based on content similarity"""
        relationships = []

        # Use TF-IDF for content similarity
        contents = [m["content"] for m in memories]

        if len(contents) >= 2:
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(contents)
            similarities = cosine_similarity(tfidf_matrix)

            # Find significant similarities
            for i in range(len(memories)):
                for j in range(i + 1, len(memories)):
                    similarity = similarities[i, j]

                    if similarity > 0.3:  # Threshold for relationship
                        # Determine relationship type based on content
                        rel_type = self._determine_memory_relationship_type(
                            memories[i], memories[j], similarity
                        )

                        relationships.append({
                            "source_memory_id": memories[i]["id"],
                            "target_memory_id": memories[j]["id"],
                            "relationship_type": rel_type,
                            "confidence": similarity,
                            "metadata": {
                                "method": "tfidf_similarity",
                                "similarity_score": float(similarity)
                            }
                        })

        return relationships

    def _determine_memory_relationship_type(
        self,
        memory1: dict[str, Any],
        memory2: dict[str, Any],
        similarity: float
    ) -> str:
        """Determine the type of relationship between two memories"""
        # Check temporal relationship
        if "created_at" in memory1 and "created_at" in memory2:
            time1 = datetime.fromisoformat(memory1["created_at"])
            time2 = datetime.fromisoformat(memory2["created_at"])

            time_diff = abs((time2 - time1).total_seconds())

            # If close in time and similar, likely sequential
            if time_diff < 3600:  # Within an hour
                return "temporal_sequence"

        # Check for causal indicators
        content1 = memory1["content"].lower()
        content2 = memory2["content"].lower()

        causal_words = ["because", "therefore", "led to", "resulted in", "caused"]
        if any(word in content1 or word in content2 for word in causal_words):
            return "potential_causal"

        # High similarity suggests topical relationship
        if similarity > 0.7:
            return "highly_related"
        elif similarity > 0.5:
            return "moderately_related"
        else:
            return "weakly_related"

    async def _get_entities_in_memory(self, memory_id: str) -> list[Entity]:
        """Get all entities mentioned in a memory"""
        # This would query the entity_mentions table
        # For now, return empty list
        return []

    async def _store_entity_mention(self, mention: EntityMention) -> None:
        """Store an entity mention in the database"""
        # First, ensure entity exists
        entity_id = await self._ensure_entity_exists(mention.entity)
        mention.entity.id = entity_id

        # Store the mention
        if self.db.pool:
            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO entity_mentions
                    (entity_id, memory_id, position_start, position_end, context, confidence)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT DO NOTHING
                """, entity_id, mention.memory_id, mention.position_start,
                    mention.position_end, mention.context, mention.confidence)

    async def _ensure_entity_exists(self, entity: Entity) -> str:
        """Ensure entity exists in database and return its ID"""
        if self.db.pool:
            async with self.db.pool.acquire() as conn:
                # Check if entity exists
                existing = await conn.fetchrow("""
                    SELECT id FROM entities
                    WHERE LOWER(name) = LOWER($1) AND entity_type = $2
                """, entity.name, entity.entity_type.value)

                if existing:
                    # Update occurrence count
                    await conn.execute("""
                        UPDATE entities
                        SET occurrence_count = occurrence_count + 1,
                            last_seen = NOW()
                        WHERE id = $1
                    """, existing["id"])
                    return str(existing["id"])
                else:
                    # Insert new entity
                    result = await conn.fetchrow("""
                        INSERT INTO entities
                        (name, entity_type, description, metadata, importance_score)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id
                    """, entity.name, entity.entity_type.value,
                        entity.description, json.dumps(entity.metadata or {}),
                        entity.importance_score)
                    return str(result["id"])

        return ""

    async def _store_memory_relationship(self, relationship: dict[str, Any]) -> None:
        """Store a relationship between memories"""
        if self.db.pool:
            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO memory_relationships
                    (source_memory_id, target_memory_id, relationship_type, confidence, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (source_memory_id, target_memory_id, relationship_type)
                    DO UPDATE SET confidence = EXCLUDED.confidence
                """, relationship["source_memory_id"], relationship["target_memory_id"],
                    relationship["relationship_type"], relationship["confidence"],
                    json.dumps(relationship.get("metadata", {})))

    async def _build_graph_representation(
        self,
        entities: list[Entity],
        relationships: list[Relationship]
    ) -> dict[str, list[dict[str, Any]]]:
        """Build graph representation for visualization"""
        nodes = []
        edges = []

        # Create nodes from entities
        for entity in entities:
            node = GraphNode(
                id=entity.id or entity.name,
                label=entity.name,
                type=entity.entity_type.value,
                size=10 + (entity.importance_score * 20),  # Size based on importance
                metadata={
                    "description": entity.description,
                    "occurrence_count": entity.occurrence_count,
                    "importance": entity.importance_score
                }
            )
            nodes.append({
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "size": node.size,
                "metadata": node.metadata
            })

        # Create edges from relationships
        for rel in relationships:
            edge = GraphEdge(
                source=rel.source_entity_id,
                target=rel.target_entity_id,
                type=rel.relationship_type.value,
                weight=rel.weight,
                label=rel.relationship_type.value.replace("_", " ")
            )
            edges.append({
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "weight": edge.weight,
                "label": edge.label
            })

        return {"nodes": nodes, "edges": edges}

    def _calculate_graph_stats(self, graph: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Calculate statistics about the graph"""
        nodes = graph["nodes"]
        edges = graph["edges"]

        node_count = len(nodes)
        edge_count = len(edges)

        # Calculate density
        max_edges = node_count * (node_count - 1) / 2 if node_count > 1 else 1
        density = edge_count / max_edges if max_edges > 0 else 0

        # Node type distribution
        type_counts = defaultdict(int)
        for node in nodes:
            type_counts[node["type"]] += 1

        # Edge type distribution
        edge_type_counts = defaultdict(int)
        for edge in edges:
            edge_type_counts[edge["type"]] += 1

        # Calculate degree distribution
        degrees = defaultdict(int)
        for edge in edges:
            degrees[edge["source"]] += 1
            degrees[edge["target"]] += 1

        avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0
        max_degree = max(degrees.values()) if degrees else 0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
            "node_types": dict(type_counts),
            "edge_types": dict(edge_type_counts),
            "avg_degree": avg_degree,
            "max_degree": max_degree,
            "connected_components": self._count_connected_components(nodes, edges)
        }

    def _count_connected_components(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]]
    ) -> int:
        """Count the number of connected components in the graph"""
        # Build adjacency list
        adjacency = defaultdict(set)
        node_ids = {node["id"] for node in nodes}

        for edge in edges:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])

        # DFS to find components
        visited = set()
        components = 0

        def dfs(node_id):
            visited.add(node_id)
            for neighbor in adjacency[node_id]:
                if neighbor not in visited:
                    dfs(neighbor)

        for node_id in node_ids:
            if node_id not in visited:
                components += 1
                dfs(node_id)

        return components

    async def _store_graph_metadata(self, stats: dict[str, Any]) -> None:
        """Store graph metadata in database"""
        if self.db.pool:
            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO graph_metadata
                    (graph_name, node_count, edge_count, density, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, "main_graph", stats["node_count"], stats["edge_count"],
                    stats["density"], json.dumps(stats))

    async def get_entity_graph(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        """Get subgraph centered on a specific entity"""
        if not self.db.pool:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []
        visited = set()

        async def explore_entity(eid: str, current_depth: int):
            if eid in visited or current_depth > depth:
                return

            visited.add(eid)

            async with self.db.pool.acquire() as conn:
                # Get entity info
                entity = await conn.fetchrow("""
                    SELECT * FROM entities WHERE id = $1
                """, eid)

                if entity:
                    nodes.append({
                        "id": str(entity["id"]),
                        "label": entity["name"],
                        "type": entity["entity_type"],
                        "size": 10 + (float(entity["importance_score"]) * 20),
                        "metadata": {
                            "description": entity["description"],
                            "occurrence_count": entity["occurrence_count"]
                        }
                    })

                # Get relationships
                relationships = await conn.fetch("""
                    SELECT * FROM entity_relationships
                    WHERE source_entity_id = $1 OR target_entity_id = $1
                """, eid)

                for rel in relationships:
                    edges.append({
                        "source": str(rel["source_entity_id"]),
                        "target": str(rel["target_entity_id"]),
                        "type": rel["relationship_type"],
                        "weight": float(rel["weight"]),
                        "label": rel["relationship_type"].replace("_", " ")
                    })

                    # Explore connected entities
                    other_id = (str(rel["target_entity_id"])
                               if str(rel["source_entity_id"]) == eid
                               else str(rel["source_entity_id"]))

                    await explore_entity(other_id, current_depth + 1)

        await explore_entity(entity_id, 0)

        return {
            "nodes": nodes,
            "edges": edges,
            "center_entity": entity_id,
            "depth": depth
        }
