"""
Knowledge gap detection and analysis
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import numpy as np

from .models import GapAnalysisRequest, KnowledgeGap
from typing import Any
from fastapi import Query
from datetime import datetime
from datetime import timedelta
from collections import defaultdict


class KnowledgeGapDetector:
    """Detects gaps in knowledge coverage and suggests areas for improvement"""

    def __init__(self, database):
        self.db = database
        self.min_domain_memories = 5
        self.reference_domains = [
            "programming", "machine learning", "databases", "algorithms",
            "system design", "networking", "security", "cloud computing",
            "data structures", "software engineering", "devops", "testing"
        ]

    async def analyze_gaps(
        self,
        request: GapAnalysisRequest
    ) -> list[KnowledgeGap]:
        """Main method to detect knowledge gaps"""
        # Get all memories
        memories = await self._get_all_memories()

        if len(memories) < self.min_domain_memories:
            return []

        # Detect gaps using multiple strategies
        gaps = []

        # Domain coverage gaps
        domain_gaps = await self._detect_domain_gaps(memories, request)
        gaps.extend(domain_gaps)

        # Temporal gaps (areas not updated recently)
        temporal_gaps = await self._detect_temporal_gaps(memories, request)
        gaps.extend(temporal_gaps)

        # Relationship gaps (isolated knowledge areas)
        relationship_gaps = await self._detect_relationship_gaps(memories, request)
        gaps.extend(relationship_gaps)

        # Depth gaps (superficial coverage)
        depth_gaps = await self._detect_depth_gaps(memories, request)
        gaps.extend(depth_gaps)

        # Filter by severity and deduplicate
        filtered_gaps = self._filter_and_deduplicate_gaps(
            gaps,
            request.min_severity
        )

        # Sort by severity
        filtered_gaps.sort(key=lambda g: g.severity, reverse=True)

        # Limit results
        return filtered_gaps[:request.limit]

    async def _get_all_memories(self) -> list[dict[str, Any]]:
        """Get all memories for analysis"""
        query = """
        SELECT id, content, tags, importance, created_at,
               updated_at, metadata, content_vector
        FROM memories
        ORDER BY created_at DESC
        """

        return await self.db.fetch_all(query)

    async def _detect_domain_gaps(
        self,
        memories: list[dict[str, Any]],
        request: GapAnalysisRequest
    ) -> list[KnowledgeGap]:
        """Detect gaps in domain coverage"""
        gaps = []

        # Analyze coverage of specified domains or reference domains
        domains = request.domains or self.reference_domains

        # Categorize memories by domain
        domain_memories = defaultdict(list)
        domain_keywords = self._get_domain_keywords()

        for memory in memories:
            content_lower = memory['content'].lower()
            tags_lower = [tag.lower() for tag in memory.get('tags', [])]

            for domain in domains:
                # Check if memory relates to domain
                if self._memory_matches_domain(
                    content_lower,
                    tags_lower,
                    domain,
                    domain_keywords.get(domain, [])
                ):
                    domain_memories[domain].append(memory)

        # Analyze coverage for each domain
        for domain in domains:
            domain_mems = domain_memories[domain]

            if len(domain_mems) < self.min_domain_memories:
                # Significant gap
                severity = 1.0 - (len(domain_mems) / self.min_domain_memories)

                gap = KnowledgeGap(
                    id=uuid4(),
                    area=f"Domain: {domain}",
                    description=f"Limited coverage of {domain} with only {len(domain_mems)} memories",
                    severity=severity,
                    related_memories=[m['id'] for m in domain_mems],
                    suggested_topics=self._suggest_topics_for_domain(domain),
                    confidence=0.8,
                    detected_at=datetime.utcnow()
                )
                gaps.append(gap)

            elif domain_mems:
                # Check for subtopic gaps within domain
                subtopic_gaps = await self._analyze_domain_subtopics(
                    domain,
                    domain_mems
                )
                gaps.extend(subtopic_gaps)

        return gaps

    async def _detect_temporal_gaps(
        self,
        memories: list[dict[str, Any]],
        request: GapAnalysisRequest
    ) -> list[KnowledgeGap]:
        """Detect areas that haven't been updated recently"""
        gaps = []
        now = datetime.utcnow()
        stale_threshold = timedelta(days=90)  # 3 months

        # Group memories by tags/topics
        topic_memories = defaultdict(list)

        for memory in memories:
            for tag in memory.get('tags', []):
                topic_memories[tag].append(memory)

        # Check for stale topics
        for topic, topic_mems in topic_memories.items():
            if len(topic_mems) >= 3:  # Only consider established topics
                latest_update = max(m['updated_at'] for m in topic_mems)

                if now - latest_update > stale_threshold:
                    days_stale = (now - latest_update).days
                    severity = min(days_stale / 180, 1.0)  # Max severity at 6 months

                    gap = KnowledgeGap(
                        id=uuid4(),
                        area=f"Stale Topic: {topic}",
                        description=f"No updates to '{topic}' in {days_stale} days",
                        severity=severity,
                        related_memories=[m['id'] for m in topic_mems[-5:]],
                        suggested_topics=[
                            f"Recent developments in {topic}",
                            f"New {topic} best practices",
                            f"Updated {topic} techniques"
                        ],
                        confidence=0.7,
                        detected_at=datetime.utcnow()
                    )
                    gaps.append(gap)

        return gaps

    async def _detect_relationship_gaps(
        self,
        memories: list[dict[str, Any]],
        request: GapAnalysisRequest
    ) -> list[KnowledgeGap]:
        """Detect isolated knowledge areas lacking connections"""
        gaps = []

        # Build tag co-occurrence matrix
        tag_cooccurrence = defaultdict(lambda: defaultdict(int))
        tag_frequency = defaultdict(int)

        for memory in memories:
            tags = memory.get('tags', [])
            for tag in tags:
                tag_frequency[tag] += 1

            for i, tag1 in enumerate(tags):
                for tag2 in tags[i+1:]:
                    tag_cooccurrence[tag1][tag2] += 1
                    tag_cooccurrence[tag2][tag1] += 1

        # Find isolated tags (high frequency but low connections)
        for tag, frequency in tag_frequency.items():
            if frequency >= 5:  # Established topic
                connections = sum(tag_cooccurrence[tag].values())
                expected_connections = frequency * 2  # Heuristic

                if connections < expected_connections * 0.3:
                    isolation_score = 1.0 - (connections / expected_connections)
                    severity = isolation_score * 0.8  # Slightly lower severity

                    # Find memories with this tag
                    tag_memories = [
                        m for m in memories
                        if tag in m.get('tags', [])
                    ]

                    gap = KnowledgeGap(
                        id=uuid4(),
                        area=f"Isolated Topic: {tag}",
                        description=f"'{tag}' has limited connections to other topics",
                        severity=severity,
                        related_memories=[m['id'] for m in tag_memories[:5]],
                        suggested_topics=self._suggest_connections_for_tag(
                            tag,
                            tag_cooccurrence,
                            tag_frequency
                        ),
                        confidence=0.6,
                        detected_at=datetime.utcnow()
                    )
                    gaps.append(gap)

        return gaps

    async def _detect_depth_gaps(
        self,
        memories: list[dict[str, Any]],
        request: GapAnalysisRequest
    ) -> list[KnowledgeGap]:
        """Detect areas with superficial coverage"""
        gaps = []

        # Group memories by topic
        topic_memories = defaultdict(list)

        for memory in memories:
            for tag in memory.get('tags', []):
                topic_memories[tag].append(memory)

        # Analyze depth of coverage
        for topic, topic_mems in topic_memories.items():
            if len(topic_mems) >= 3:
                # Calculate average content length and importance
                avg_length = np.mean([len(m['content']) for m in topic_mems])
                avg_importance = np.mean([m.get('importance', 0) for m in topic_mems])

                # Check for superficial coverage
                if avg_length < 200 and avg_importance < 5:
                    severity = 0.6 * (1 - avg_length / 500) + 0.4 * (1 - avg_importance / 10)

                    gap = KnowledgeGap(
                        id=uuid4(),
                        area=f"Shallow Coverage: {topic}",
                        description=f"'{topic}' has superficial coverage with short, low-importance memories",
                        severity=severity,
                        related_memories=[m['id'] for m in topic_mems[:5]],
                        suggested_topics=[
                            f"Deep dive into {topic}",
                            f"{topic} advanced concepts",
                            f"{topic} best practices and patterns",
                            f"{topic} real-world applications"
                        ],
                        confidence=0.7,
                        detected_at=datetime.utcnow()
                    )
                    gaps.append(gap)

        return gaps

    async def _analyze_domain_subtopics(
        self,
        domain: str,
        domain_memories: list[dict[str, Any]]
    ) -> list[KnowledgeGap]:
        """Analyze subtopic coverage within a domain"""
        gaps = []

        # Get expected subtopics for domain
        expected_subtopics = self._get_domain_subtopics(domain)
        if not expected_subtopics:
            return gaps

        # Check coverage of each subtopic
        subtopic_coverage = defaultdict(list)

        for memory in domain_memories:
            content_lower = memory['content'].lower()
            for subtopic in expected_subtopics:
                if subtopic.lower() in content_lower:
                    subtopic_coverage[subtopic].append(memory)

        # Find missing subtopics
        for subtopic in expected_subtopics:
            if len(subtopic_coverage[subtopic]) < 2:
                severity = 0.7 if len(subtopic_coverage[subtopic]) == 0 else 0.4

                gap = KnowledgeGap(
                    id=uuid4(),
                    area=f"Missing Subtopic: {domain}/{subtopic}",
                    description=f"Limited coverage of {subtopic} within {domain}",
                    severity=severity,
                    related_memories=[m['id'] for m in subtopic_coverage[subtopic]],
                    suggested_topics=[
                        f"{subtopic} fundamentals",
                        f"{subtopic} in {domain}",
                        f"Practical {subtopic}"
                    ],
                    confidence=0.6,
                    detected_at=datetime.utcnow()
                )
                gaps.append(gap)

        return gaps

    def _memory_matches_domain(
        self,
        content: str,
        tags: list[str],
        domain: str,
        keywords: list[str]
    ) -> bool:
        """Check if memory matches a domain"""
        domain_lower = domain.lower()

        # Direct match in tags
        if domain_lower in tags:
            return True

        # Domain in content
        if domain_lower in content:
            return True

        # Keyword matches
        if keywords:
            keyword_matches = sum(1 for kw in keywords if kw in content)
            if keyword_matches >= 2:
                return True

        return False

    def _get_domain_keywords(self) -> dict[str, list[str]]:
        """Get keywords for each domain"""
        return {
            "programming": ["code", "function", "variable", "algorithm", "syntax"],
            "machine learning": ["model", "training", "neural", "dataset", "prediction"],
            "databases": ["sql", "query", "table", "index", "transaction"],
            "algorithms": ["complexity", "sorting", "search", "optimization", "recursion"],
            "system design": ["architecture", "scalability", "microservice", "api", "cache"],
            "networking": ["tcp", "http", "protocol", "packet", "routing"],
            "security": ["encryption", "authentication", "vulnerability", "attack", "defense"],
            "cloud computing": ["aws", "azure", "kubernetes", "docker", "serverless"],
            "data structures": ["array", "list", "tree", "graph", "hash"],
            "software engineering": ["design pattern", "testing", "agile", "refactor", "solid"],
            "devops": ["ci/cd", "deployment", "monitoring", "automation", "pipeline"],
            "testing": ["unit test", "integration", "mock", "coverage", "assertion"]
        }

    def _get_domain_subtopics(self, domain: str) -> list[str]:
        """Get expected subtopics for a domain"""
        subtopics = {
            "programming": ["syntax", "data types", "control flow", "functions", "classes"],
            "machine learning": ["supervised learning", "unsupervised learning", "deep learning", "feature engineering", "evaluation"],
            "databases": ["normalization", "indexing", "transactions", "nosql", "optimization"],
            "algorithms": ["sorting", "searching", "dynamic programming", "graph algorithms", "greedy"],
            "system design": ["load balancing", "caching", "message queues", "databases", "monitoring"],
            "security": ["authentication", "authorization", "cryptography", "vulnerabilities", "best practices"]
        }

        return subtopics.get(domain, [])

    def _suggest_topics_for_domain(self, domain: str) -> list[str]:
        """Suggest topics for a domain"""
        base_suggestions = [
            f"{domain} fundamentals",
            f"{domain} best practices",
            f"Advanced {domain} concepts",
            f"{domain} tools and frameworks",
            f"Real-world {domain} examples"
        ]

        # Add domain-specific suggestions
        specific_suggestions = {
            "programming": ["Design patterns", "Code optimization", "Clean code principles"],
            "machine learning": ["Model selection", "Hyperparameter tuning", "MLOps"],
            "databases": ["Query optimization", "Data modeling", "Replication strategies"],
            "security": ["Threat modeling", "Security auditing", "Incident response"]
        }

        if domain in specific_suggestions:
            base_suggestions.extend(specific_suggestions[domain])

        return base_suggestions[:5]

    def _suggest_connections_for_tag(
        self,
        tag: str,
        cooccurrence: dict[str, dict[str, int]],
        frequency: dict[str, int]
    ) -> list[str]:
        """Suggest connections for an isolated tag"""
        suggestions = []

        # Find related tags based on partial matches
        related_tags = []
        for other_tag in frequency.keys():
            if other_tag != tag:
                # Check for semantic similarity
                if any(word in other_tag for word in tag.split('-')):
                    related_tags.append(other_tag)
                elif any(word in tag for word in other_tag.split('-')):
                    related_tags.append(other_tag)

        # Create suggestions
        for related in related_tags[:3]:
            suggestions.append(f"Connect {tag} with {related}")

        # General suggestions
        suggestions.extend([
            f"Practical applications of {tag}",
            f"{tag} in context",
            f"Integrate {tag} with existing knowledge"
        ])

        return suggestions[:5]

    def _filter_and_deduplicate_gaps(
        self,
        gaps: list[KnowledgeGap],
        min_severity: float
    ) -> list[KnowledgeGap]:
        """Filter gaps by severity and remove duplicates"""
        # Filter by severity
        filtered = [g for g in gaps if g.severity >= min_severity]

        # Deduplicate by area similarity
        unique_gaps = []
        seen_areas = set()

        for gap in filtered:
            # Simple deduplication by area prefix
            area_key = gap.area.split(':')[0]

            if area_key not in seen_areas:
                unique_gaps.append(gap)
                seen_areas.add(area_key)
            else:
                # Keep if significantly different severity
                existing = next(
                    (g for g in unique_gaps if g.area.startswith(area_key)),
                    None
                )
                if existing and gap.severity > existing.severity * 1.2:
                    unique_gaps.remove(existing)
                    unique_gaps.append(gap)

        return unique_gaps
