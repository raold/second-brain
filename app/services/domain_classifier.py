import re
from dataclasses import dataclass, field
from typing import Any

from app.ingestion.models import StructuredData
from app.utils.logging_config import get_logger

"""
Domain classification service for intelligent content analysis.

This service analyzes text content to:
- Extract key topics and themes
- Classify content into knowledge domains
- Extract structured data (tables, lists, key-value pairs)
- Provide statistical analysis of content
"""

from collections import Counter

from app.utils.openai_client import get_openai_client

logger = get_logger(__name__)


@dataclass
class Topic:
    """Represents an extracted topic with metadata"""

    name: str
    frequency: int
    confidence: float
    keywords: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)


@dataclass
class Domain:
    """Represents a knowledge domain classification"""

    name: str
    confidence: float
    indicators: list[str] = field(default_factory=list)
    sub_domains: list[str] = field(default_factory=list)


@dataclass
class StructuredData:
    """Container for extracted structured data"""

    key_value_pairs: dict[str, Any] = field(default_factory=dict)
    lists: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    code_snippets: list[dict[str, Any]] = field(default_factory=list)
    metadata_fields: dict[str, Any] = field(default_factory=dict)


class DomainClassifier:
    """Advanced domain classification and content analysis service"""

    # Knowledge domain definitions
    DOMAIN_PATTERNS = {
        "technology": {
            "keywords": [
                "software",
                "code",
                "api",
                "database",
                "algorithm",
                "framework",
                "programming",
                "development",
                "tech",
                "system",
            ],
            "patterns": [r"\b(python|javascript|java|sql|html|css)\b", r"\b(AI|ML|API|SDK)\b"],
            "sub_domains": [
                "software_engineering",
                "data_science",
                "web_development",
                "devops",
                "security",
            ],
        },
        "business": {
            "keywords": [
                "revenue",
                "profit",
                "market",
                "strategy",
                "customer",
                "sales",
                "growth",
                "investment",
                "roi",
                "kpi",
            ],
            "patterns": [r"\$\d+", r"\d+%\s*(growth|increase|decrease)", r"\b(Q[1-4]|FY\d{2,4})\b"],
            "sub_domains": ["finance", "marketing", "strategy", "operations", "hr"],
        },
        "science": {
            "keywords": [
                "research",
                "study",
                "experiment",
                "hypothesis",
                "data",
                "analysis",
                "theory",
                "evidence",
                "methodology",
            ],
            "patterns": [r"\b(p\s*[<=]\s*0\.\d+)\b", r"\b(n\s*=\s*\d+)\b"],
            "sub_domains": ["biology", "physics", "chemistry", "psychology", "medicine"],
        },
        "personal": {
            "keywords": [
                "feeling",
                "thought",
                "experience",
                "life",
                "goal",
                "dream",
                "memory",
                "relationship",
                "emotion",
            ],
            "patterns": [r"\b(I|me|my|myself)\b", r"\b(feel|think|believe|want|need)\b"],
            "sub_domains": ["journal", "goals", "relationships", "health", "reflection"],
        },
        "education": {
            "keywords": [
                "learn",
                "teach",
                "course",
                "lesson",
                "student",
                "knowledge",
                "skill",
                "training",
                "education",
            ],
            "patterns": [
                r"\b(chapter|lesson|module|unit)\s*\d+\b",
                r"\b(assignment|homework|exam|test)\b",
            ],
            "sub_domains": [
                "academic",
                "professional_development",
                "skills_training",
                "certification",
            ],
        },
    }

    def __init__(self, **kwargs):
        self.config = kwargs
        self.openai_client = None
        self.use_ai = kwargs.get("use_ai", True)

        if self.use_ai:
            try:
                self.openai_client = get_openai_client()
            except Exception as e:
                logger.warning(
                    f"Failed to initialize OpenAI client: {e}. Falling back to rule-based analysis."
                )
                self.use_ai = False

        logger.info(f"Initialized DomainClassifier (AI={'enabled' if self.use_ai else 'disabled'})")

    def extract_topics(self, content: str) -> list[Topic]:
        """Extract main topics from content using NLP techniques"""
        try:
            # Preprocess content
            content_lower = content.lower()
            words = re.findall(r"\b\w+\b", content_lower)

            # Extract noun phrases and important terms
            topics = []

            # Use word frequency for basic topic extraction
            word_freq = Counter(words)

            # Filter out common words
            common_words = {
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
                "as",
                "by",
                "is",
                "was",
                "are",
                "were",
            }
            important_words = [
                (word, freq)
                for word, freq in word_freq.most_common(50)
                if word not in common_words and len(word) > 3
            ]

            # Group related words into topics
            for word, freq in important_words[:20]:
                # Find related keywords
                related = [w for w, f in important_words if w != word and (word in w or w in word)]

                # Extract context sentences
                context = []
                sentences = re.split(r"[.!?]+", content)
                for sentence in sentences:
                    if word in sentence.lower():
                        context.append(sentence.strip()[:200])
                        if len(context) >= 3:
                            break

                topic = Topic(
                    name=word.title(),
                    frequency=freq,
                    confidence=min(freq / len(words), 1.0),
                    keywords=related[:5],
                    context=context,
                )
                topics.append(topic)

            # Use AI for advanced topic extraction if available
            if self.use_ai and self.openai_client:
                try:
                    ai_topics = self._extract_topics_with_ai(content)
                    topics.extend(ai_topics)
                except Exception as e:
                    logger.warning(f"AI topic extraction failed: {e}")

            # Deduplicate and sort by confidence
            unique_topics = {}
            for topic in topics:
                if (
                    topic.name not in unique_topics
                    or topic.confidence > unique_topics[topic.name].confidence
                ):
                    unique_topics[topic.name] = topic

            return sorted(unique_topics.values(), key=lambda t: t.confidence, reverse=True)[:10]

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []

    def extract_advanced_topics(self, content: str) -> list[Topic]:
        """Extract advanced topics with deeper analysis"""
        try:
            # Get basic topics
            basic_topics = self.extract_topics(content)

            # Enhance with pattern matching
            enhanced_topics = []

            for domain_name, domain_info in self.DOMAIN_PATTERNS.items():
                # Check patterns
                pattern_matches = 0
                for pattern in domain_info["patterns"]:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    pattern_matches += len(matches)

                # Check keywords
                keyword_matches = sum(
                    1 for keyword in domain_info["keywords"] if keyword in content.lower()
                )

                if pattern_matches > 0 or keyword_matches > 2:
                    confidence = min((pattern_matches * 0.2 + keyword_matches * 0.1), 1.0)

                    topic = Topic(
                        name=f"{domain_name.title()} Topics",
                        frequency=pattern_matches + keyword_matches,
                        confidence=confidence,
                        keywords=domain_info["keywords"][:5],
                        context=[
                            f"Domain: {domain_name}",
                            f"Sub-domains: {', '.join(domain_info['sub_domains'][:3])}",
                        ],
                    )
                    enhanced_topics.append(topic)

            # Combine and deduplicate
            all_topics = basic_topics + enhanced_topics
            unique_topics = {}
            for topic in all_topics:
                key = topic.name.lower()
                if key not in unique_topics or topic.confidence > unique_topics[key].confidence:
                    unique_topics[key] = topic

            return sorted(unique_topics.values(), key=lambda t: t.confidence, reverse=True)[:15]

        except Exception as e:
            logger.error(f"Advanced topic extraction failed: {e}")
            return self.extract_topics(content)

    def get_topic_statistics(self, topics: list[Topic]) -> dict[str, Any]:
        """Generate statistics about extracted topics"""
        try:
            if not topics:
                return {
                    "total_topics": 0,
                    "average_confidence": 0.0,
                    "high_confidence_topics": 0,
                    "topic_distribution": {},
                    "keyword_count": 0,
                }

            # Calculate statistics
            confidences = [t.confidence for t in topics]
            keywords_all = [kw for t in topics for kw in t.keywords]

            # Group topics by confidence level
            confidence_groups = {
                "high": [t for t in topics if t.confidence >= 0.7],
                "medium": [t for t in topics if 0.4 <= t.confidence < 0.7],
                "low": [t for t in topics if t.confidence < 0.4],
            }

            return {
                "total_topics": len(topics),
                "average_confidence": sum(confidences) / len(confidences),
                "high_confidence_topics": len(confidence_groups["high"]),
                "topic_distribution": {
                    level: len(group) for level, group in confidence_groups.items()
                },
                "keyword_count": len(set(keywords_all)),
                "top_topics": [t.name for t in topics[:5]],
                "confidence_range": {"min": min(confidences), "max": max(confidences)},
            }

        except Exception as e:
            logger.error(f"Topic statistics generation failed: {e}")
            return {}

    def extract_structured_data(self, content: str) -> StructuredData:
        """Extract structured data from content"""
        try:
            data = StructuredData()

            # Extract key-value pairs
            data.key_value_pairs = self._extract_key_value_pairs(content)

            # Extract lists
            data.lists = self._extract_lists(content)

            # Extract tables
            data.tables = self._extract_tables(content)

            # Extract code snippets
            data.code_snippets = self._extract_code_snippets(content)

            # Extract metadata
            data.metadata_fields = self._extract_metadata(content)

            return data

        except Exception as e:
            logger.error(f"Structured data extraction failed: {e}")
            return StructuredData()

    def extract_advanced_structured_data(self, content: str) -> StructuredData:
        """Extract advanced structured data with enhanced parsing"""
        try:
            # Get basic structured data
            data = self.extract_structured_data(content)

            # Enhance with AI if available
            if self.use_ai and self.openai_client:
                try:
                    enhanced_data = self._enhance_structured_data_with_ai(content, data)
                    return enhanced_data
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")

            return data

        except Exception as e:
            logger.error(f"Advanced structured data extraction failed: {e}")
            return self.extract_structured_data(content)

    def get_extraction_statistics(self, data: StructuredData) -> dict[str, Any]:
        """Get statistics about extracted structured data"""
        try:
            return {
                "key_value_pairs_count": len(data.key_value_pairs),
                "lists_count": len(data.lists),
                "tables_count": len(data.tables),
                "code_snippets_count": len(data.code_snippets),
                "metadata_fields_count": len(data.metadata_fields),
                "total_structured_elements": (
                    len(data.key_value_pairs)
                    + len(data.lists)
                    + len(data.tables)
                    + len(data.code_snippets)
                ),
                "has_structured_data": any(
                    [data.key_value_pairs, data.lists, data.tables, data.code_snippets]
                ),
            }

        except Exception as e:
            logger.error(f"Extraction statistics generation failed: {e}")
            return {}

    def classify_domain(self, content: str, **kwargs) -> dict[str, Any]:
        """Classify content into knowledge domains"""
        try:
            domains = []
            confidence_scores = {}

            content_lower = content.lower()

            # Analyze each domain
            for domain_name, domain_info in self.DOMAIN_PATTERNS.items():
                score = 0.0
                indicators = []

                # Check keywords
                keyword_matches = 0
                for keyword in domain_info["keywords"]:
                    if keyword in content_lower:
                        keyword_matches += content_lower.count(keyword)
                        indicators.append(f"keyword: {keyword}")

                # Check patterns
                pattern_matches = 0
                for pattern in domain_info["patterns"]:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    pattern_matches += len(matches)
                    if matches:
                        indicators.append(f"pattern: {matches[0]}")

                # Calculate confidence score
                if keyword_matches > 0 or pattern_matches > 0:
                    # Normalize scores
                    keyword_score = min(keyword_matches / 20.0, 0.5)
                    pattern_score = min(pattern_matches / 10.0, 0.5)
                    score = keyword_score + pattern_score

                    domain = Domain(
                        name=domain_name,
                        confidence=score,
                        indicators=indicators[:5],
                        sub_domains=[
                            sd
                            for sd in domain_info["sub_domains"]
                            if any(sd.replace("_", " ") in content_lower for _ in range(1))
                        ],
                    )
                    domains.append(domain)
                    confidence_scores[domain_name] = score

            # Sort by confidence
            domains.sort(key=lambda d: d.confidence, reverse=True)

            # Primary domain is the highest scoring one
            primary_domain = domains[0].name if domains else "general"

            return {
                "primary_domain": primary_domain,
                "domains": [
                    {
                        "name": d.name,
                        "confidence": d.confidence,
                        "indicators": d.indicators,
                        "sub_domains": d.sub_domains,
                    }
                    for d in domains[:3]
                ],
                "confidence_scores": confidence_scores,
                "multi_domain": len([d for d in domains if d.confidence > 0.3]) > 1,
            }

        except Exception as e:
            logger.error(f"Domain classification failed: {e}")
            return {"domains": [], "confidence_scores": {}}

    def get_domain_statistics(self, domains: list[Domain]) -> dict[str, Any]:
        """Get statistics about domain classifications"""
        try:
            if not domains:
                return {
                    "total_domains": 0,
                    "primary_domain": None,
                    "domain_distribution": {},
                    "average_confidence": 0.0,
                }

            # Convert dict domains to Domain objects if needed
            if isinstance(domains[0], dict):
                domains = [
                    Domain(
                        name=d["name"],
                        confidence=d["confidence"],
                        indicators=d.get("indicators", []),
                        sub_domains=d.get("sub_domains", []),
                    )
                    for d in domains
                ]

            confidences = [d.confidence for d in domains]

            return {
                "total_domains": len(domains),
                "primary_domain": domains[0].name if domains else None,
                "domain_distribution": {d.name: d.confidence for d in domains},
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "high_confidence_domains": [d.name for d in domains if d.confidence > 0.7],
                "sub_domains_identified": sum(len(d.sub_domains) for d in domains),
            }

        except Exception as e:
            logger.error(f"Domain statistics generation failed: {e}")
            return {}

    # Private helper methods

    def _extract_key_value_pairs(self, content: str) -> dict[str, Any]:
        """Extract key-value pairs from content"""
        pairs = {}

        # Pattern 1: "key: value" or "key = value"
        patterns = [
            r"([\w\s]+?)\s*[:=]\s*([^\n]+)",
            r"\*\*([\w\s]+?)\*\*\s*[:=]\s*([^\n]+)",
            r"\b([A-Z][\w\s]+?)\s+is\s+([^\n.]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for key, value in matches:
                key = key.strip()
                value = value.strip().rstrip(".,")
                if len(key) < 50 and len(value) < 200 and key.lower() not in pairs:
                    pairs[key] = value

        return pairs

    def _extract_lists(self, content: str) -> list[dict[str, Any]]:
        """Extract lists from content"""
        lists = []

        # Pattern for bullet points or numbered lists
        list_patterns = [
            r"(?:^|\n)\s*[•\-\*]\s+(.+?)(?=\n|$)",
            r"(?:^|\n)\s*\d+\.\s+(.+?)(?=\n|$)",
            r"(?:^|\n)\s*[a-z]\.\s+(.+?)(?=\n|$)",
        ]

        for pattern in list_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            if len(matches) >= 2:
                list_data = {
                    "type": "bullet" if "•" in pattern or "-" in pattern else "numbered",
                    "items": [match.strip() for match in matches],
                    "count": len(matches),
                }
                lists.append(list_data)

        return lists

    def _extract_tables(self, content: str) -> list[dict[str, Any]]:
        """Extract table-like structures from content"""
        tables = []

        # Simple table detection (pipe-separated values)
        lines = content.split("\n")
        potential_table = []

        for line in lines:
            if "|" in line and line.count("|") >= 2:
                potential_table.append(line)
            elif potential_table and len(potential_table) >= 2:
                # Process the table
                headers = [cell.strip() for cell in potential_table[0].split("|") if cell.strip()]
                rows = []

                for row_line in potential_table[2:]:  # Skip separator line
                    cells = [cell.strip() for cell in row_line.split("|") if cell.strip()]
                    if len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells, strict=False)))

                if rows:
                    tables.append(
                        {
                            "headers": headers,
                            "rows": rows,
                            "row_count": len(rows),
                            "column_count": len(headers),
                        }
                    )

                potential_table = []

        return tables

    def _extract_code_snippets(self, content: str) -> list[dict[str, Any]]:
        """Extract code snippets from content"""
        snippets = []

        # Pattern for code blocks
        code_patterns = [
            r"```([\w]*)?\n([\s\S]*?)```",  # Markdown code blocks
            r"(?:^|\n)((?:    |\t)[^\n]+(?:\n(?:    |\t)[^\n]+)*)",  # Indented blocks
        ]

        for pattern in code_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    language = match[0] if match[0] else "unknown"
                    code = match[1] if len(match) > 1 else match[0]
                else:
                    language = "unknown"
                    code = match

                if code.strip():
                    snippets.append(
                        {
                            "language": language,
                            "code": code.strip(),
                            "lines": len(code.strip().split("\n")),
                        }
                    )

        return snippets

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata fields from content"""
        metadata = {}

        # Common metadata patterns
        metadata_patterns = {
            "date": r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
            "time": r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "url": r"https?://[^\s]+",
            "phone": r"\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b",
        }

        for field, pattern in metadata_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                metadata[field] = matches[0] if len(matches) == 1 else matches

        # Extract word and character counts
        metadata["word_count"] = len(re.findall(r"\b\w+\b", content))
        metadata["char_count"] = len(content)
        metadata["line_count"] = len(content.split("\n"))

        return metadata

    def _extract_topics_with_ai(self, content: str) -> list[Topic]:
        """Use AI to extract topics (placeholder for OpenAI integration)"""
        # This would use OpenAI to extract topics
        # For now, return empty list as OpenAI integration is pending
        return []

    def _enhance_structured_data_with_ai(
        self, content: str, data: StructuredData
    ) -> StructuredData:
        """Use AI to enhance structured data extraction (placeholder)"""
        # This would use OpenAI to enhance extraction
        # For now, return original data as OpenAI integration is pending
        return data
