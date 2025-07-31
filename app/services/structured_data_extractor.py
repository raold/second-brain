"""
Structured data extraction service for intelligent parsing.

This service specializes in:
- Extracting key-value pairs, tables, and lists from unstructured text
- Parsing code snippets and technical documentation
- Identifying structured patterns in natural language
- Converting unstructured content to structured formats
"""

import json
import re
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any

import markdown
from bs4 import BeautifulSoup

from app.utils.logging_config import get_logger
from app.utils.openai_client import get_openai_client

logger = get_logger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted table with metadata"""
    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None
    table_type: str = "generic"  # generic, comparison, data, matrix
    confidence: float = 0.0


@dataclass
class ExtractedList:
    """Represents an extracted list with metadata"""
    items: list[str]
    list_type: str = "unordered"  # unordered, ordered, definition
    title: str | None = None
    nested_items: dict[int, list[str]] | None = None


@dataclass
class ExtractedCodeBlock:
    """Represents an extracted code snippet"""
    code: str
    language: str
    line_count: int
    description: str | None = None
    imports: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity (person, place, date, etc.)"""
    text: str
    entity_type: str
    context: str
    confidence: float = 0.0


@dataclass
class StructuredDataContainer:
    """Container for all extracted structured data"""
    key_value_pairs: dict[str, Any] = field(default_factory=dict)
    lists: list[ExtractedList] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    code_snippets: list[ExtractedCodeBlock] = field(default_factory=list)
    metadata_fields: dict[str, Any] = field(default_factory=dict)
    entities: list[ExtractedEntity] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)  # (entity1, relation, entity2)


class StructuredDataExtractor:
    """Advanced structured data extraction service"""

    # Patterns for various structured data types
    KEY_VALUE_PATTERNS = [
        # Standard patterns
        r'^([A-Za-z][A-Za-z0-9\s_-]{0,30}):\s*(.+)$',  # Key: value
        r'^([A-Za-z][A-Za-z0-9\s_-]{0,30})\s*=\s*(.+)$',  # Key = value
        r'^([A-Za-z][A-Za-z0-9\s_-]{0,30})\s*->\s*(.+)$',  # Key -> value
        r'^\*\*([A-Za-z][A-Za-z0-9\s_-]{0,30})\*\*:\s*(.+)$',  # **Key**: value
        # Definition patterns
        r'^([A-Z][A-Za-z0-9\s]{0,30})\s+is\s+(.+)$',  # Term is definition
        r'^([A-Z][A-Za-z0-9\s]{0,30})\s+means\s+(.+)$',  # Term means definition
    ]

    LIST_PATTERNS = {
        'bullet': [
            r'^\s*[\u2022\u2023\u25E6\u2043\u2219]\s+(.+)$',  # Unicode bullets
            r'^\s*[-*+]\s+(.+)$',  # Markdown bullets
        ],
        'numbered': [
            r'^\s*(\d+)[.)]\s+(.+)$',  # 1. or 1)
            r'^\s*\((\d+)\)\s+(.+)$',  # (1)
            r'^\s*([a-z])[.)]\s+(.+)$',  # a. or a)
            r'^\s*\(([a-z])\)\s+(.+)$',  # (a)
        ],
        'definition': [
            r'^([A-Za-z][A-Za-z0-9\s]{0,30}):\s*(.+)$',  # Term: definition
        ]
    }

    # Entity patterns
    ENTITY_PATTERNS = {
        'date': [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
        ],
        'time': [
            r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\b',
        ],
        'email': [
            r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
        ],
        'url': [
            r'(https?://[^\s<>"{}|\\^`\[\]]+)',
        ],
        'phone': [
            r'\b(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b',
        ],
        'money': [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP)',
        ],
    }

    def __init__(self, **kwargs):
        self.config = kwargs
        self.openai_client = None
        self.use_ai = kwargs.get('use_ai', True)

        # Configuration
        self.min_confidence = kwargs.get('min_confidence', 0.5)
        self.extract_entities = kwargs.get('extract_entities', True)
        self.extract_relationships = kwargs.get('extract_relationships', True)

        if self.use_ai:
            try:
                self.openai_client = get_openai_client()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Using pattern-based extraction only.")
                self.use_ai = False

        logger.info(f"Initialized StructuredDataExtractor (AI={'enabled' if self.use_ai else 'disabled'})")

    def extract_structured_data(self, content: str) -> StructuredDataContainer:
        """Extract all types of structured data from content"""
        try:
            container = StructuredDataContainer()

            # Clean content
            content = self._clean_content(content)

            # Extract different types of structured data
            container.key_value_pairs = self._extract_key_value_pairs(content)
            container.lists = self._extract_lists(content)
            container.tables = self._extract_tables(content)
            container.code_snippets = self._extract_code_blocks(content)
            container.metadata_fields = self._extract_metadata(content)

            # Extract entities if enabled
            if self.extract_entities:
                container.entities = self._extract_entities(content)

            # Extract relationships if enabled
            if self.extract_relationships:
                container.relationships = self._extract_relationships(content, container.entities)

            return container

        except Exception as e:
            logger.error(f"Structured data extraction failed: {e}", exc_info=True)
            return StructuredDataContainer()

    def extract_advanced_structured_data(self, content: str) -> StructuredDataContainer:
        """Extract structured data with advanced parsing and AI enhancement"""
        try:
            # Get basic extraction
            container = self.extract_structured_data(content)

            # Enhance with format-specific parsing
            if self._is_markdown(content):
                container = self._enhance_markdown_extraction(content, container)
            elif self._is_html(content):
                container = self._enhance_html_extraction(content, container)
            elif self._is_json(content):
                container = self._enhance_json_extraction(content, container)

            # Apply AI enhancement if available
            if self.use_ai and self.openai_client:
                try:
                    container = self._enhance_with_ai(content, container)
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")

            # Post-process and validate
            container = self._post_process_extraction(container)

            return container

        except Exception as e:
            logger.error(f"Advanced structured data extraction failed: {e}")
            return self.extract_structured_data(content)

    def get_extraction_statistics(self, data: StructuredDataContainer) -> dict[str, Any]:
        """Get detailed statistics about extracted data"""
        try:
            # Calculate statistics
            total_elements = (
                len(data.key_value_pairs) +
                len(data.lists) +
                len(data.tables) +
                len(data.code_snippets)
            )

            # List statistics
            list_items_total = sum(len(lst.items) for lst in data.lists)
            nested_lists = sum(1 for lst in data.lists if lst.nested_items)

            # Table statistics
            table_cells_total = sum(len(table.headers) * len(table.rows) for table in data.tables)
            avg_table_size = table_cells_total / len(data.tables) if data.tables else 0

            # Code statistics
            total_code_lines = sum(block.line_count for block in data.code_snippets)
            languages = list(set(block.language for block in data.code_snippets))

            # Entity statistics
            entity_types = defaultdict(int)
            for entity in data.entities:
                entity_types[entity.entity_type] += 1

            return {
                "total_structured_elements": total_elements,
                "key_value_pairs": {
                    "count": len(data.key_value_pairs),
                    "sample_keys": list(data.key_value_pairs.keys())[:5]
                },
                "lists": {
                    "count": len(data.lists),
                    "total_items": list_items_total,
                    "nested_count": nested_lists,
                    "types": dict(Counter(lst.list_type for lst in data.lists))
                },
                "tables": {
                    "count": len(data.tables),
                    "total_cells": table_cells_total,
                    "average_size": avg_table_size,
                    "types": dict(Counter(table.table_type for table in data.tables))
                },
                "code_snippets": {
                    "count": len(data.code_snippets),
                    "total_lines": total_code_lines,
                    "languages": languages,
                    "functions_found": sum(len(block.functions) for block in data.code_snippets),
                    "classes_found": sum(len(block.classes) for block in data.code_snippets)
                },
                "entities": {
                    "count": len(data.entities),
                    "types": dict(entity_types)
                },
                "relationships": {
                    "count": len(data.relationships)
                },
                "metadata": {
                    "fields": len(data.metadata_fields),
                    "has_dates": any(k in data.metadata_fields for k in ['date', 'created', 'modified']),
                    "has_author": any(k in data.metadata_fields for k in ['author', 'creator', 'by'])
                }
            }

        except Exception as e:
            logger.error(f"Statistics generation failed: {e}")
            return {}

    def extract_topics(self, content: str) -> list[dict[str, Any]]:
        """Extract topic-like structures from content"""
        try:
            # This method focuses on extracting structured topic representations
            topics = []

            # Extract section headers as topics
            headers = self._extract_headers(content)
            for header in headers:
                topics.append({
                    "type": "section",
                    "title": header['text'],
                    "level": header['level'],
                    "content_preview": header.get('preview', '')
                })

            # Extract definition lists as topics
            definitions = self._extract_definitions(content)
            for term, definition in definitions.items():
                topics.append({
                    "type": "definition",
                    "term": term,
                    "definition": definition
                })

            # Extract categorized lists as topics
            data = self.extract_structured_data(content)
            for lst in data.lists:
                if lst.title:
                    topics.append({
                        "type": "list_topic",
                        "title": lst.title,
                        "items": lst.items[:5],  # First 5 items
                        "item_count": len(lst.items)
                    })

            return topics

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []

    def extract_advanced_topics(self, content: str) -> list[dict[str, Any]]:
        """Extract advanced topic structures with hierarchy"""
        try:
            # Get basic topics
            topics = self.extract_topics(content)

            # Build topic hierarchy
            hierarchy = self._build_topic_hierarchy(topics)

            # Enhance with context
            for topic in hierarchy:
                topic['context'] = self._extract_topic_context(content, topic)

            return hierarchy

        except Exception as e:
            logger.error(f"Advanced topic extraction failed: {e}")
            return self.extract_topics(content)

    def get_topic_statistics(self, topics: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about extracted topics"""
        try:
            if not topics:
                return {"total_topics": 0}

            type_counts = Counter(t['type'] for t in topics)

            return {
                "total_topics": len(topics),
                "topic_types": dict(type_counts),
                "has_hierarchy": any('children' in t for t in topics),
                "max_depth": self._calculate_max_depth(topics),
                "average_content_length": sum(len(t.get('content_preview', '')) for t in topics) / len(topics)
            }

        except Exception as e:
            logger.error(f"Topic statistics generation failed: {e}")
            return {}

    def classify_domain(self, content: str, **kwargs) -> dict[str, Any]:
        """Classify content domain based on structured patterns"""
        try:
            # Extract structured data
            data = self.extract_structured_data(content)

            # Domain indicators
            domain_indicators = {
                "technical": {
                    "code_presence": len(data.code_snippets) > 0,
                    "technical_terms": self._count_technical_terms(content),
                    "structured_data": len(data.tables) > 0
                },
                "academic": {
                    "citations": self._count_citations(content),
                    "formal_structure": self._has_formal_structure(content),
                    "references": 'references' in content.lower() or 'bibliography' in content.lower()
                },
                "business": {
                    "financial_data": any('$' in str(v) for v in data.key_value_pairs.values()),
                    "business_terms": self._count_business_terms(content),
                    "metrics": self._has_metrics(data)
                }
            }

            # Calculate domain scores
            domain_scores = {}
            for domain, indicators in domain_indicators.items():
                score = sum(1 for v in indicators.values() if v) / len(indicators)
                if isinstance(list(indicators.values())[0], int):
                    score = min(sum(indicators.values()) / 10, 1.0)
                domain_scores[domain] = score

            # Sort by score
            sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)

            return {
                "domains": [{"name": d, "confidence": s} for d, s in sorted_domains if s > 0.1],
                "confidence_scores": domain_scores,
                "primary_domain": sorted_domains[0][0] if sorted_domains and sorted_domains[0][1] > 0.1 else "general"
            }

        except Exception as e:
            logger.error(f"Domain classification failed: {e}")
            return {"domains": [], "confidence_scores": {}}

    def get_domain_statistics(self, domains: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about domain classifications"""
        return {
            "total_domains": len(domains),
            "primary_domain": domains[0]["name"] if domains else None,
            "average_confidence": sum(d["confidence"] for d in domains) / len(domains) if domains else 0.0
        }

    # Private helper methods

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Normalize quotes
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")

        return content.strip()

    def _extract_key_value_pairs(self, content: str) -> dict[str, Any]:
        """Extract key-value pairs from content"""
        pairs = OrderedDict()
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in self.KEY_VALUE_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # Clean up the value
                    value = value.rstrip('.,;')

                    # Skip if key is too long or value is empty
                    if len(key) > 50 or not value:
                        continue

                    # Type conversion
                    converted_value = self._convert_value_type(value)

                    # Store the pair
                    pairs[key] = converted_value
                    break

        return dict(pairs)

    def _extract_lists(self, content: str) -> list[ExtractedList]:
        """Extract lists from content"""
        lists = []
        lines = content.split('\n')

        current_list = None
        current_type = None
        current_indent = 0

        for i, line in enumerate(lines):
            # Check for list title (line before list starts)
            if i < len(lines) - 1 and not current_list and line.strip() and line.strip().endswith(':'):
                next_line = lines[i + 1].strip()
                for list_type, patterns in self.LIST_PATTERNS.items():
                    for pattern in patterns:
                        if re.match(pattern, next_line):
                            # Start new list with title
                            current_list = ExtractedList(
                                items=[],
                                list_type=list_type,
                                title=line.strip().rstrip(':')
                            )
                            current_type = list_type
                            break

            # Check for list items
            if line.strip():
                indent = len(line) - len(line.lstrip())

                for list_type, patterns in self.LIST_PATTERNS.items():
                    for pattern in patterns:
                        match = re.match(pattern, line.strip())
                        if match:
                            # Get the last captured group (the item text)
                            if match.groups():
                                item_text = match.group(match.lastindex).strip()
                            else:
                                item_text = match.group(0).strip()

                            if current_list and current_type == list_type and abs(indent - current_indent) < 4:
                                # Add to current list
                                current_list.items.append(item_text)
                            else:
                                # Save previous list if exists
                                if current_list and len(current_list.items) >= 2:
                                    lists.append(current_list)

                                # Start new list
                                current_list = ExtractedList(
                                    items=[item_text],
                                    list_type=list_type
                                )
                                current_type = list_type
                                current_indent = indent
                            break
            else:
                # Empty line - end current list
                if current_list and len(current_list.items) >= 2:
                    lists.append(current_list)
                    current_list = None
                    current_type = None

        # Don't forget the last list
        if current_list and len(current_list.items) >= 2:
            lists.append(current_list)

        return lists

    def _extract_tables(self, content: str) -> list[ExtractedTable]:
        """Extract tables from content"""
        tables = []

        # Method 1: Markdown tables
        tables.extend(self._extract_markdown_tables(content))

        # Method 2: ASCII tables
        tables.extend(self._extract_ascii_tables(content))

        # Method 3: Tab-separated values
        tables.extend(self._extract_tsv_tables(content))

        # Remove duplicates
        unique_tables = []
        seen = set()
        for table in tables:
            table_key = (tuple(table.headers), tuple(tuple(row) for row in table.rows))
            if table_key not in seen:
                seen.add(table_key)
                unique_tables.append(table)

        return unique_tables

    def _extract_markdown_tables(self, content: str) -> list[ExtractedTable]:
        """Extract markdown-style tables"""
        tables = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for table header
            if '|' in line and i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Check for separator line
                if re.match(r'^[\|\s\-:]+$', next_line) and '|' in next_line:
                    # Extract headers
                    headers = [cell.strip() for cell in line.split('|') if cell.strip()]

                    # Extract rows
                    rows = []
                    j = i + 2
                    while j < len(lines) and '|' in lines[j]:
                        row = [cell.strip() for cell in lines[j].split('|') if cell.strip()]
                        if len(row) == len(headers):
                            rows.append(row)
                        j += 1

                    if rows:
                        # Determine table type
                        table_type = self._classify_table_type(headers, rows)

                        table = ExtractedTable(
                            headers=headers,
                            rows=rows,
                            table_type=table_type,
                            confidence=0.9
                        )
                        tables.append(table)

                    i = j
                    continue

            i += 1

        return tables

    def _extract_ascii_tables(self, content: str) -> list[ExtractedTable]:
        """Extract ASCII-art style tables"""
        tables = []
        lines = content.split('\n')

        # Look for box-drawing characters
        table_lines = []
        in_table = False

        for line in lines:
            if any(char in line for char in ['+', '-', '|', '═', '║', '╔', '╗', '╚', '╝']):
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
            elif in_table and table_lines:
                # Try to parse the table
                parsed_table = self._parse_ascii_table(table_lines)
                if parsed_table:
                    tables.append(parsed_table)
                in_table = False
                table_lines = []

        return tables

    def _extract_tsv_tables(self, content: str) -> list[ExtractedTable]:
        """Extract tab-separated value tables"""
        tables = []
        lines = content.split('\n')

        # Look for consistent tab-separated lines
        tab_lines = []
        for i, line in enumerate(lines):
            if '\t' in line:
                tab_lines.append((i, line))

        # Group consecutive tab lines
        if tab_lines:
            groups = []
            current_group = [tab_lines[0]]

            for i in range(1, len(tab_lines)):
                if tab_lines[i][0] - tab_lines[i-1][0] == 1:
                    current_group.append(tab_lines[i])
                else:
                    if len(current_group) >= 2:
                        groups.append(current_group)
                    current_group = [tab_lines[i]]

            if len(current_group) >= 2:
                groups.append(current_group)

            # Parse each group as a table
            for group in groups:
                lines_only = [line for _, line in group]
                headers = lines_only[0].split('\t')
                rows = []

                for line in lines_only[1:]:
                    row = line.split('\t')
                    if len(row) == len(headers):
                        rows.append(row)

                if rows:
                    table = ExtractedTable(
                        headers=[h.strip() for h in headers],
                        rows=[[cell.strip() for cell in row] for row in rows],
                        table_type="data",
                        confidence=0.7
                    )
                    tables.append(table)

        return tables

    def _extract_code_blocks(self, content: str) -> list[ExtractedCodeBlock]:
        """Extract code snippets from content"""
        code_blocks = []

        # Pattern 1: Markdown code blocks
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)

        for language, code in matches:
            if not language:
                language = self._detect_language(code)

            block = self._analyze_code_block(code, language)
            code_blocks.append(block)

        # Pattern 2: Indented code blocks
        lines = content.split('\n')
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                if not in_code_block:
                    in_code_block = True
                    code_lines = []
                code_lines.append(line[4:] if line.startswith('    ') else line[1:])
            elif in_code_block and code_lines:
                # End of code block
                code = '\n'.join(code_lines)
                if len(code_lines) >= 2:  # Minimum 2 lines
                    language = self._detect_language(code)
                    block = self._analyze_code_block(code, language)
                    code_blocks.append(block)
                in_code_block = False
                code_lines = []

        # Don't forget last block
        if in_code_block and code_lines and len(code_lines) >= 2:
            code = '\n'.join(code_lines)
            language = self._detect_language(code)
            block = self._analyze_code_block(code, language)
            code_blocks.append(block)

        return code_blocks

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata fields from content"""
        metadata = {}

        # Extract dates
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['dates'] = list(set(matches))[:5]  # First 5 unique dates
                break

        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        if urls:
            metadata['urls'] = list(set(urls))[:10]

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        if emails:
            metadata['emails'] = list(set(emails))[:5]

        # Extract file references
        file_pattern = r'[A-Za-z0-9_\-]+\.(txt|pdf|doc|docx|xls|xlsx|csv|json|xml|html|py|js|java|cpp|c|h)'
        files = re.findall(file_pattern, content, re.IGNORECASE)
        if files:
            metadata['files'] = list(set(f[0] + '.' + f[1] for f in files))[:10]

        # Basic statistics
        metadata['statistics'] = {
            'word_count': len(re.findall(r'\b\w+\b', content)),
            'line_count': len(content.split('\n')),
            'character_count': len(content),
            'paragraph_count': len(re.split(r'\n\s*\n', content))
        }

        return metadata

    def _extract_entities(self, content: str) -> list[ExtractedEntity]:
        """Extract named entities from content"""
        entities = []

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Extract context
                    match_text = match if isinstance(match, str) else match[0]
                    context = self._extract_context(content, match_text, 50)

                    entity = ExtractedEntity(
                        text=match_text,
                        entity_type=entity_type,
                        context=context,
                        confidence=0.8
                    )
                    entities.append(entity)

        # Remove duplicates
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.text, entity.entity_type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    def _extract_relationships(self, content: str, entities: list[ExtractedEntity]) -> list[tuple[str, str, str]]:
        """Extract relationships between entities"""
        relationships = []

        if len(entities) < 2:
            return relationships

        # Simple pattern-based relationship extraction
        relationship_patterns = [
            (r'{0}\s+(?:is|was|are|were)\s+(?:a|an|the)?\s*(\w+)\s+(?:of|for|to)\s+{1}', 'related_to'),
            (r'{0}\s+(?:works|worked)\s+(?:at|for|with)\s+{1}', 'works_at'),
            (r'{0}\s+(?:owns|owned|has|had)\s+{1}', 'owns'),
            (r'{0}\s+(?:created|made|built|developed)\s+{1}', 'created'),
        ]

        # Check pairs of entities
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Skip if same type (e.g., two dates)
                if entity1.entity_type == entity2.entity_type:
                    continue

                # Check each pattern
                for pattern_template, relation in relationship_patterns:
                    pattern = pattern_template.format(
                        re.escape(entity1.text),
                        re.escape(entity2.text)
                    )

                    if re.search(pattern, content, re.IGNORECASE):
                        relationships.append((entity1.text, relation, entity2.text))
                        break

        return relationships[:20]  # Limit to 20 relationships

    def _convert_value_type(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        value = value.strip()

        # Try boolean
        if value.lower() in ['true', 'yes', 'on']:
            return True
        elif value.lower() in ['false', 'no', 'off']:
            return False

        # Try number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Try list (comma-separated)
        if ',' in value:
            items = [item.strip() for item in value.split(',')]
            if len(items) > 1:
                return items

        # Default to string
        return value

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code snippet"""
        # Simple heuristics
        if 'import' in code and 'from' in code:
            return 'python'
        elif 'function' in code or 'const' in code or 'var' in code:
            return 'javascript'
        elif '#include' in code:
            return 'cpp'
        elif 'public class' in code or 'public static' in code:
            return 'java'
        elif 'package main' in code:
            return 'go'
        elif 'def' in code or 'class' in code:
            return 'python'
        else:
            return 'unknown'

    def _analyze_code_block(self, code: str, language: str) -> ExtractedCodeBlock:
        """Analyze a code block to extract metadata"""
        lines = code.split('\n')

        block = ExtractedCodeBlock(
            code=code,
            language=language,
            line_count=len(lines)
        )

        # Extract imports (Python/JavaScript)
        if language in ['python', 'javascript']:
            import_pattern = r'^(?:import|from)\s+[\w\.]+'
            imports = re.findall(import_pattern, code, re.MULTILINE)
            block.imports = imports

        # Extract function definitions
        if language == 'python':
            func_pattern = r'^def\s+(\w+)\s*\('
            functions = re.findall(func_pattern, code, re.MULTILINE)
            block.functions = functions

            class_pattern = r'^class\s+(\w+)'
            classes = re.findall(class_pattern, code, re.MULTILINE)
            block.classes = classes

        return block

    def _extract_context(self, content: str, text: str, window: int = 50) -> str:
        """Extract context around a piece of text"""
        index = content.find(text)
        if index == -1:
            return ""

        start = max(0, index - window)
        end = min(len(content), index + len(text) + window)

        context = content[start:end]

        # Clean up
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context.replace('\n', ' ').strip()

    def _classify_table_type(self, headers: list[str], rows: list[list[str]]) -> str:
        """Classify the type of table based on content"""
        # Check for comparison table
        if any(word in ' '.join(headers).lower() for word in ['vs', 'versus', 'comparison']):
            return 'comparison'

        # Check for data table (numbers)
        numeric_cells = 0
        total_cells = len(rows) * len(headers) if rows else 0

        for row in rows:
            for cell in row:
                try:
                    float(cell.replace(',', '').replace('$', ''))
                    numeric_cells += 1
                except ValueError:
                    pass

        if total_cells > 0 and numeric_cells / total_cells > 0.5:
            return 'data'

        # Check for matrix
        if headers and rows and headers[0] == '' and all(row[0] for row in rows):
            return 'matrix'

        return 'generic'

    def _parse_ascii_table(self, lines: list[str]) -> ExtractedTable | None:
        """Parse an ASCII art table"""
        # This is a simplified parser - in production, use a library
        try:
            # Find header row (usually after first border)
            header_row = None
            data_rows = []

            for _i, line in enumerate(lines):
                if '|' in line and not all(c in '-+=|' for c in line):
                    if header_row is None:
                        header_row = line
                    else:
                        data_rows.append(line)

            if header_row and data_rows:
                # Extract cells
                headers = [cell.strip() for cell in header_row.split('|') if cell.strip()]
                rows = []

                for row_line in data_rows:
                    cells = [cell.strip() for cell in row_line.split('|') if cell.strip()]
                    if len(cells) == len(headers):
                        rows.append(cells)

                if rows:
                    return ExtractedTable(
                        headers=headers,
                        rows=rows,
                        table_type='generic',
                        confidence=0.7
                    )

            return None

        except Exception:
            return None

    def _is_markdown(self, content: str) -> bool:
        """Check if content is markdown formatted"""
        markdown_indicators = ['#', '```', '**', '- ', '1.', '[', ']', '|']
        return sum(1 for indicator in markdown_indicators if indicator in content) >= 3

    def _is_html(self, content: str) -> bool:
        """Check if content is HTML"""
        return bool(re.search(r'<[^>]+>', content))

    def _is_json(self, content: str) -> bool:
        """Check if content is JSON"""
        try:
            json.loads(content)
            return True
        except Exception:
            return False

    def _enhance_markdown_extraction(self, content: str, container: StructuredDataContainer) -> StructuredDataContainer:
        """Enhance extraction for markdown content"""
        try:
            # Parse markdown
            html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
            soup = BeautifulSoup(html, 'html.parser')

            # Extract additional tables
            for table in soup.find_all('table'):
                headers = [th.text.strip() for th in table.find_all('th')]
                rows = []

                for tr in table.find_all('tr')[1:]:  # Skip header row
                    cells = [td.text.strip() for td in tr.find_all('td')]
                    if cells:
                        rows.append(cells)

                if headers and rows:
                    extracted_table = ExtractedTable(
                        headers=headers,
                        rows=rows,
                        table_type=self._classify_table_type(headers, rows),
                        confidence=0.95
                    )
                    container.tables.append(extracted_table)

            return container

        except Exception as e:
            logger.warning(f"Markdown enhancement failed: {e}")
            return container

    def _enhance_html_extraction(self, content: str, container: StructuredDataContainer) -> StructuredDataContainer:
        """Enhance extraction for HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Extract definition lists
            for dl in soup.find_all('dl'):
                for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd'), strict=False):
                    key = dt.text.strip()
                    value = dd.text.strip()
                    if key and value:
                        container.key_value_pairs[key] = value

            # Extract metadata from meta tags
            for meta in soup.find_all('meta'):
                if meta.get('name') and meta.get('content'):
                    container.metadata_fields[meta['name']] = meta['content']

            return container

        except Exception as e:
            logger.warning(f"HTML enhancement failed: {e}")
            return container

    def _enhance_json_extraction(self, content: str, container: StructuredDataContainer) -> StructuredDataContainer:
        """Enhance extraction for JSON content"""
        try:
            data = json.loads(content)

            # Flatten JSON structure
            flattened = self._flatten_json(data)
            container.key_value_pairs.update(flattened)

            return container

        except Exception as e:
            logger.warning(f"JSON enhancement failed: {e}")
            return container

    def _flatten_json(self, obj: Any, prefix: str = '') -> dict[str, Any]:
        """Flatten nested JSON structure"""
        result = {}

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict | list):
                    result.update(self._flatten_json(value, new_key))
                else:
                    result[new_key] = value
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}[{i}]"
                if isinstance(item, dict | list):
                    result.update(self._flatten_json(item, new_key))
                else:
                    result[new_key] = item
        else:
            result[prefix] = obj

        return result

    def _enhance_with_ai(self, content: str, container: StructuredDataContainer) -> StructuredDataContainer:
        """Enhance extraction using AI (placeholder for OpenAI integration)"""
        # This would use OpenAI to identify additional structures
        # For now, return container as-is
        return container

    def _post_process_extraction(self, container: StructuredDataContainer) -> StructuredDataContainer:
        """Post-process and validate extracted data"""
        # Remove duplicates
        container.lists = self._deduplicate_lists(container.lists)

        # Validate tables
        container.tables = [t for t in container.tables if len(t.rows) > 0]

        # Clean key-value pairs
        cleaned_pairs = {}
        for key, value in container.key_value_pairs.items():
            if key and value and not isinstance(value, str | int | float | bool | list):
                value = str(value)
            cleaned_pairs[key] = value
        container.key_value_pairs = cleaned_pairs

        return container

    def _deduplicate_lists(self, lists: list[ExtractedList]) -> list[ExtractedList]:
        """Remove duplicate lists"""
        seen = set()
        unique_lists = []

        for lst in lists:
            list_key = (lst.list_type, tuple(lst.items))
            if list_key not in seen:
                seen.add(list_key)
                unique_lists.append(lst)

        return unique_lists

    def _extract_headers(self, content: str) -> list[dict[str, Any]]:
        """Extract section headers from content"""
        headers = []

        # Markdown headers
        pattern = r'^(#{1,6})\s+(.+)$'
        for match in re.finditer(pattern, content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()

            # Get preview of content after header
            start = match.end()
            end = min(start + 200, len(content))
            preview = content[start:end].strip()

            headers.append({
                'level': level,
                'text': text,
                'preview': preview[:100] + '...' if len(preview) > 100 else preview
            })

        return headers

    def _extract_definitions(self, content: str) -> dict[str, str]:
        """Extract term definitions from content"""
        definitions = {}

        # Pattern: "Term: definition" or "Term - definition"
        patterns = [
            r'^([A-Z][A-Za-z\s]{2,30}):\s*(.+)$',
            r'^([A-Z][A-Za-z\s]{2,30})\s*-\s*(.+)$',
        ]

        for line in content.split('\n'):
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    term = match.group(1).strip()
                    definition = match.group(2).strip()
                    if len(definition) > 20:  # Minimum definition length
                        definitions[term] = definition
                    break

        return definitions

    def _build_topic_hierarchy(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build hierarchical structure from topics"""
        # Simple hierarchy based on section levels
        hierarchy = []
        stack = []

        for topic in topics:
            if topic['type'] == 'section':
                level = topic.get('level', 1)

                # Pop stack until we find parent level
                while stack and stack[-1]['level'] >= level:
                    stack.pop()

                # Add as child to current top of stack
                if stack:
                    if 'children' not in stack[-1]:
                        stack[-1]['children'] = []
                    stack[-1]['children'].append(topic)
                else:
                    hierarchy.append(topic)

                stack.append(topic)
            else:
                # Non-section topics go at current level
                if stack and 'children' in stack[-1]:
                    stack[-1]['children'].append(topic)
                else:
                    hierarchy.append(topic)

        return hierarchy

    def _extract_topic_context(self, content: str, topic: dict[str, Any]) -> str:
        """Extract context for a topic"""
        if 'content_preview' in topic:
            return topic['content_preview']

        # For other topic types, generate context
        if topic['type'] == 'definition':
            return topic.get('definition', '')[:200]
        elif topic['type'] == 'list_topic':
            return f"List with {topic.get('item_count', 0)} items"

        return ""

    def _calculate_max_depth(self, topics: list[dict[str, Any]]) -> int:
        """Calculate maximum depth of topic hierarchy"""
        def get_depth(topic: dict[str, Any]) -> int:
            if 'children' not in topic:
                return 1
            return 1 + max(get_depth(child) for child in topic['children'])

        if not topics:
            return 0

        return max(get_depth(topic) for topic in topics)

    def _count_technical_terms(self, content: str) -> int:
        """Count technical terms in content"""
        technical_terms = [
            'algorithm', 'api', 'database', 'function', 'variable', 'class',
            'method', 'parameter', 'framework', 'library', 'protocol', 'interface'
        ]

        content_lower = content.lower()
        count = sum(content_lower.count(term) for term in technical_terms)
        return count

    def _count_business_terms(self, content: str) -> int:
        """Count business terms in content"""
        business_terms = [
            'revenue', 'profit', 'market', 'customer', 'strategy', 'roi',
            'kpi', 'growth', 'investment', 'stakeholder', 'quarterly', 'fiscal'
        ]

        content_lower = content.lower()
        count = sum(content_lower.count(term) for term in business_terms)
        return count

    def _count_citations(self, content: str) -> int:
        """Count academic citations in content"""
        # Simple pattern for citations like [1], (Smith, 2020), etc.
        patterns = [
            r'\[\d+\]',  # [1], [2], etc.
            r'\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)',  # (Smith, 2020)
            r'\([A-Z][a-z]+\s+&\s+[A-Z][a-z]+,\s*\d{4}\)',  # (Smith & Jones, 2020)
        ]

        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content))

        return count

    def _has_formal_structure(self, content: str) -> bool:
        """Check if content has formal academic structure"""
        formal_sections = [
            'abstract', 'introduction', 'methodology', 'results',
            'discussion', 'conclusion', 'references', 'bibliography'
        ]

        content_lower = content.lower()
        found_sections = sum(1 for section in formal_sections if section in content_lower)

        return found_sections >= 3

    def _has_metrics(self, data: StructuredDataContainer) -> bool:
        """Check if data contains business metrics"""
        metric_keywords = ['rate', 'percentage', 'ratio', 'score', 'index', 'average']

        for key in data.key_value_pairs:
            if any(keyword in key.lower() for keyword in metric_keywords):
                return True

        return False
