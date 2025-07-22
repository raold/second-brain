"""
Natural Language Query Parser for Knowledge Graphs
Converts natural language queries into graph operations
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class QueryType(Enum):
    """Types of graph queries"""
    FIND_CONNECTIONS = "find_connections"  # Find path between entities
    FIND_RELATED = "find_related"  # Find entities related to a given entity
    FILTER_BY_TYPE = "filter_by_type"  # Filter entities by type
    FIND_CLUSTERS = "find_clusters"  # Find entity clusters
    ANALYZE_ENTITY = "analyze_entity"  # Analyze specific entity
    COMPARE_ENTITIES = "compare_entities"  # Compare two entities
    TEMPORAL_QUERY = "temporal_query"  # Time-based queries
    PATTERN_SEARCH = "pattern_search"  # Search for patterns


@dataclass
class ParsedQuery:
    """Represents a parsed natural language query"""
    query_type: QueryType
    entities: list[str]
    entity_types: list[str]
    filters: dict[str, Any]
    temporal_context: str | None = None
    depth: int = 2
    original_query: str = ""


class GraphQueryParser:
    """
    Parses natural language queries for knowledge graph operations
    """

    def __init__(self):
        self.connection_patterns = [
            r"(?:show|find|what are) (?:the )?(?:connections?|paths?|links?) (?:between|from) (.+?) (?:and|to) (.+)",
            r"how (?:is|are) (.+?) (?:connected|related|linked) to (.+)",
            r"(?:trace|show) (?:the )?path from (.+?) to (.+)",
        ]

        self.related_patterns = [
            r"what (?:is|are) (?:related|connected|linked) to (.+)",
            r"(?:show|find) (?:all )?(?:things|entities|nodes) (?:related|connected) to (.+)",
            r"(.+?) (?:connections|relationships|relations)",
        ]

        self.filter_patterns = [
            r"(?:show|find|list) all (\w+)",  # e.g., "show all people"
            r"(?:filter|only show) (\w+)",
            r"(?:what|which) (\w+) (?:are|is) in the graph",
        ]

        self.analyze_patterns = [
            r"(?:analyze|tell me about|describe) (.+)",
            r"what (?:do you know|can you tell me) about (.+)",
            r"(?:show|give) (?:me )?(?:details|information) (?:about|on) (.+)",
        ]

        self.compare_patterns = [
            r"(?:compare|difference between) (.+?) and (.+)",
            r"how (?:do|does) (.+?) (?:compare|differ) (?:to|from) (.+)",
            r"(?:similarities|differences) between (.+?) and (.+)",
        ]

        self.temporal_patterns = [
            r"(.+?) (?:before|after|during) (.+)",
            r"(?:evolution|history|timeline) of (.+)",
            r"how (?:did|has) (.+?) (?:evolve|change)",
        ]

        self.entity_type_map = {
            "people": "person",
            "persons": "person",
            "person": "person",
            "organizations": "organization",
            "orgs": "organization",
            "companies": "organization",
            "technologies": "technology",
            "tech": "technology",
            "tools": "technology",
            "concepts": "concept",
            "ideas": "concept",
            "topics": "topic",
            "subjects": "topic",
            "skills": "skill",
            "locations": "location",
            "places": "location",
            "events": "event",
        }

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured format

        Args:
            query: Natural language query string

        Returns:
            ParsedQuery object with extracted information
        """
        query = query.strip()
        query_lower = query.lower()

        # Try to match against different query patterns

        # Connection queries
        for pattern in self.connection_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities = [self._clean_entity(match.group(1)),
                           self._clean_entity(match.group(2))]
                return ParsedQuery(
                    query_type=QueryType.FIND_CONNECTIONS,
                    entities=entities,
                    entity_types=[],
                    filters={},
                    original_query=query
                )

        # Related entity queries
        for pattern in self.related_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entity = self._clean_entity(match.group(1))
                return ParsedQuery(
                    query_type=QueryType.FIND_RELATED,
                    entities=[entity],
                    entity_types=[],
                    filters={},
                    original_query=query
                )

        # Filter by type queries
        for pattern in self.filter_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entity_type_raw = match.group(1).lower()
                entity_type = self.entity_type_map.get(entity_type_raw, entity_type_raw)
                return ParsedQuery(
                    query_type=QueryType.FILTER_BY_TYPE,
                    entities=[],
                    entity_types=[entity_type],
                    filters={"type": entity_type},
                    original_query=query
                )

        # Analyze entity queries
        for pattern in self.analyze_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entity = self._clean_entity(match.group(1))
                return ParsedQuery(
                    query_type=QueryType.ANALYZE_ENTITY,
                    entities=[entity],
                    entity_types=[],
                    filters={},
                    original_query=query
                )

        # Compare entities queries
        for pattern in self.compare_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities = [self._clean_entity(match.group(1)),
                           self._clean_entity(match.group(2))]
                return ParsedQuery(
                    query_type=QueryType.COMPARE_ENTITIES,
                    entities=entities,
                    entity_types=[],
                    filters={},
                    original_query=query
                )

        # Temporal queries
        for pattern in self.temporal_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if "evolution" in query_lower or "history" in query_lower:
                    entity = self._clean_entity(match.group(1))
                    return ParsedQuery(
                        query_type=QueryType.TEMPORAL_QUERY,
                        entities=[entity],
                        entity_types=[],
                        filters={"temporal_type": "evolution"},
                        temporal_context="evolution",
                        original_query=query
                    )

        # Pattern search (catch-all for complex queries)
        if "cluster" in query_lower or "group" in query_lower:
            return ParsedQuery(
                query_type=QueryType.FIND_CLUSTERS,
                entities=[],
                entity_types=[],
                filters={},
                original_query=query
            )

        # Default to pattern search
        return ParsedQuery(
            query_type=QueryType.PATTERN_SEARCH,
            entities=self._extract_potential_entities(query),
            entity_types=[],
            filters={},
            original_query=query
        )

    def _clean_entity(self, entity: str) -> str:
        """Clean and normalize entity name"""
        # Remove articles and common words
        stop_words = {"the", "a", "an", "this", "that", "these", "those"}
        words = entity.strip().split()
        cleaned_words = [w for w in words if w.lower() not in stop_words]
        return " ".join(cleaned_words)

    def _extract_potential_entities(self, query: str) -> list[str]:
        """Extract potential entity names from query"""
        # Look for capitalized words or quoted phrases
        entities = []

        # Find quoted phrases
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # Find capitalized sequences (potential proper nouns)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(capitalized)

        return [self._clean_entity(e) for e in entities]

    def suggest_query(self, partial_query: str) -> list[str]:
        """
        Suggest query completions based on partial input

        Args:
            partial_query: Partial query string

        Returns:
            List of suggested completions
        """
        suggestions = []
        partial_lower = partial_query.lower()

        # Connection suggestions
        if "connection" in partial_lower or "path" in partial_lower:
            suggestions.extend([
                "show connections between [entity1] and [entity2]",
                "find path from [entity1] to [entity2]",
                "how is [entity1] connected to [entity2]"
            ])

        # Related suggestions
        if "related" in partial_lower or "connected" in partial_lower:
            suggestions.extend([
                "what is related to [entity]",
                "show all things connected to [entity]",
                "find entities related to [entity]"
            ])

        # Filter suggestions
        if "show all" in partial_lower or "list" in partial_lower:
            suggestions.extend([
                "show all people",
                "show all technologies",
                "show all concepts",
                "list all organizations"
            ])

        # Analyze suggestions
        if "about" in partial_lower or "tell" in partial_lower:
            suggestions.extend([
                "tell me about [entity]",
                "analyze [entity]",
                "what do you know about [entity]"
            ])

        return suggestions

    def get_query_examples(self) -> dict[str, list[str]]:
        """Get example queries organized by type"""
        return {
            "Connections": [
                "Show connections between Python and machine learning",
                "Find path from neural networks to AI systems",
                "How is Dr. Smith connected to MIT"
            ],
            "Related Entities": [
                "What is related to deep learning",
                "Show all things connected to Python",
                "Find entities related to Stanford University"
            ],
            "Filter by Type": [
                "Show all people",
                "List all technologies",
                "Find all organizations"
            ],
            "Analysis": [
                "Tell me about neural networks",
                "Analyze Python",
                "What do you know about Dr. Chen"
            ],
            "Comparisons": [
                "Compare TensorFlow and PyTorch",
                "Differences between supervised and unsupervised learning",
                "How does Python compare to JavaScript"
            ],
            "Temporal": [
                "Evolution of machine learning",
                "History of neural networks",
                "How has AI evolved"
            ]
        }
