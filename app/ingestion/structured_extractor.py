"""
Structured data extraction component for extracting tables, lists, key-value pairs, and code
"""

import json
import logging
import re
from collections import defaultdict
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from app.ingestion.models import StructuredData

logger = logging.getLogger(__name__)


class StructuredDataExtractor:
    """Extract structured data from unstructured text"""

    def __init__(self):
        """Initialize structured data extractor"""
        # Initialize patterns
        self.list_patterns = self._initialize_list_patterns()
        self.table_patterns = self._initialize_table_patterns()
        self.kv_patterns = self._initialize_kv_patterns()
        self.code_patterns = self._initialize_code_patterns()

    def extract_structured_data(self, text: str) -> StructuredData:
        """
        Extract all types of structured data from text

        Args:
            text: Input text

        Returns:
            Extracted structured data
        """
        # Extract different types of structured data
        key_value_pairs = self._extract_key_value_pairs(text)
        lists = self._extract_lists(text)
        tables = self._extract_tables(text)
        code_snippets = self._extract_code_snippets(text)
        metadata_fields = self._extract_metadata_fields(text)

        return StructuredData(
            key_value_pairs=key_value_pairs,
            lists=lists,
            tables=tables,
            code_snippets=code_snippets,
            metadata_fields=metadata_fields
        )

    def _extract_key_value_pairs(self, text: str) -> dict[str, Any]:
        """Extract key-value pairs from text"""
        kv_pairs = {}

        # Try different patterns
        for pattern_info in self.kv_patterns:
            pattern = pattern_info["pattern"]
            processor = pattern_info.get("processor")

            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                if len(match.groups()) >= 2:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # Clean up key
                    key = self._normalize_key(key)

                    # Process value if processor provided
                    if processor:
                        value = processor(value)
                    else:
                        value = self._parse_value(value)

                    # Store the pair
                    if key and value is not None:
                        kv_pairs[key] = value

        # Try to extract JSON/YAML blocks
        json_data = self._extract_json_data(text)
        if json_data:
            kv_pairs.update(self._flatten_dict(json_data, prefix="json"))

        if YAML_AVAILABLE:
            yaml_data = self._extract_yaml_data(text)
            if yaml_data:
                kv_pairs.update(self._flatten_dict(yaml_data, prefix="yaml"))

        return kv_pairs

    def _extract_lists(self, text: str) -> dict[str, list[str]]:
        """Extract lists from text"""
        lists = {}

        # Extract bullet lists
        bullet_lists = self._extract_bullet_lists(text)
        for i, lst in enumerate(bullet_lists):
            if lst:
                lists[f"bullet_list_{i+1}"] = lst

        # Extract numbered lists
        numbered_lists = self._extract_numbered_lists(text)
        for i, lst in enumerate(numbered_lists):
            if lst:
                lists[f"numbered_list_{i+1}"] = lst

        # Extract comma-separated lists
        comma_lists = self._extract_comma_lists(text)
        for i, (title, lst) in enumerate(comma_lists):
            if lst:
                key = self._normalize_key(title) if title else f"comma_list_{i+1}"
                lists[key] = lst

        return lists

    def _extract_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract tables from text"""
        tables = []

        # Extract markdown tables
        markdown_tables = self._extract_markdown_tables(text)
        tables.extend(markdown_tables)

        # Extract ASCII tables
        ascii_tables = self._extract_ascii_tables(text)
        tables.extend(ascii_tables)

        # Extract structured data that looks like tables
        structured_tables = self._extract_structured_tables(text)
        tables.extend(structured_tables)

        return tables

    def _extract_code_snippets(self, text: str) -> list[dict[str, str]]:
        """Extract code snippets from text"""
        snippets = []

        # Extract fenced code blocks (```language ... ```)
        fenced_pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(fenced_pattern, text, re.DOTALL):
            language = match.group(1) or "unknown"
            code = match.group(2).strip()

            snippets.append({
                "language": language,
                "code": code,
                "type": "fenced",
                "lines": str(len(code.splitlines()))
            })

        # Extract indented code blocks
        indented_blocks = self._extract_indented_code(text)
        for block in indented_blocks:
            snippets.append({
                "language": self._detect_language(block),
                "code": block,
                "type": "indented",
                "lines": len(block.splitlines())
            })

        # Extract inline code (single backticks)
        inline_pattern = r'`([^`]+)`'
        inline_codes = re.findall(inline_pattern, text)

        # Only keep substantial inline code (not just single words)
        for code in inline_codes:
            if len(code) > 10 and any(char in code for char in ['(', ')', '{', '}', '=', ':']):
                snippets.append({
                    "language": self._detect_language(code),
                    "code": code,
                    "type": "inline",
                    "lines": 1
                })

        return snippets

    def _extract_metadata_fields(self, text: str) -> dict[str, Any]:
        """Extract metadata-like fields from text"""
        metadata = {}

        # Extract header metadata (e.g., from markdown files)
        header_match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
        if header_match:
            try:
                if YAML_AVAILABLE:
                    header_data = yaml.safe_load(header_match.group(1))
                    if isinstance(header_data, dict):
                        metadata.update(header_data)
            except Exception as e:
                logger.debug(f"Failed to parse header metadata: {e}")

        # Extract common metadata patterns
        metadata_patterns = [
            (r'(?:Author|Created by|By):\s*(.+)', 'author'),
            (r'(?:Date|Created|Updated):\s*(.+)', 'date'),
            (r'(?:Title|Subject|Topic):\s*(.+)', 'title'),
            (r'(?:Tags|Labels|Categories):\s*(.+)', 'tags'),
            (r'(?:Version|Revision):\s*(.+)', 'version'),
            (r'(?:Status|State):\s*(.+)', 'status'),
            (r'(?:Priority|Importance):\s*(.+)', 'priority'),
        ]

        for pattern, field_name in metadata_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Parse tags as list
                if field_name == 'tags':
                    value = [tag.strip() for tag in re.split(r'[,;]', value)]
                metadata[field_name] = value

        return metadata

    def _extract_bullet_lists(self, text: str) -> list[list[str]]:
        """Extract bullet point lists"""
        lists = []
        current_list = []
        in_list = False

        lines = text.split('\n')

        for line in lines:
            # Check if line is a bullet point
            bullet_match = re.match(r'^\s*[-*•]\s+(.+)', line)

            if bullet_match:
                in_list = True
                item = bullet_match.group(1).strip()
                current_list.append(item)
            else:
                # If we were in a list and hit a non-bullet line
                if in_list and current_list:
                    # Check if it's a continuation (indented)
                    if line.strip() and line.startswith('  '):
                        # Add to previous item
                        if current_list:
                            current_list[-1] += ' ' + line.strip()
                    else:
                        # End of list
                        if len(current_list) > 1:  # Only keep lists with multiple items
                            lists.append(current_list)
                        current_list = []
                        in_list = False

        # Don't forget the last list
        if current_list and len(current_list) > 1:
            lists.append(current_list)

        return lists

    def _extract_numbered_lists(self, text: str) -> list[list[str]]:
        """Extract numbered lists"""
        lists = []
        current_list = []
        expected_number = 1

        lines = text.split('\n')

        for line in lines:
            # Check if line is a numbered item
            number_match = re.match(r'^\s*(\d+)[.)]\s+(.+)', line)

            if number_match:
                number = int(number_match.group(1))
                item = number_match.group(2).strip()

                # Check if this continues the current list
                if number == expected_number or number == 1:
                    if number == 1 and current_list and len(current_list) > 1:
                        # New list starting
                        lists.append(current_list)
                        current_list = []

                    current_list.append(item)
                    expected_number = number + 1
                else:
                    # Number doesn't match expected sequence
                    if current_list and len(current_list) > 1:
                        lists.append(current_list)
                    current_list = [item]
                    expected_number = number + 1
            else:
                # Not a numbered line
                if current_list:
                    # Check if it's a continuation
                    if line.strip() and line.startswith('  '):
                        current_list[-1] += ' ' + line.strip()
                    else:
                        # End of list
                        if len(current_list) > 1:
                            lists.append(current_list)
                        current_list = []
                        expected_number = 1

        # Don't forget the last list
        if current_list and len(current_list) > 1:
            lists.append(current_list)

        return lists

    def _extract_comma_lists(self, text: str) -> list[tuple[str, list[str]]]:
        """Extract comma-separated lists with titles"""
        lists = []

        # Pattern for "Title: item1, item2, item3"
        pattern = r'([^:]+):\s*([^.!?\n]+(?:,\s*[^.!?\n]+)+)'

        for match in re.finditer(pattern, text):
            title = match.group(1).strip()
            items_str = match.group(2).strip()

            # Split by comma and clean
            items = [item.strip() for item in items_str.split(',')]

            # Filter out very short items and clean up
            items = [item for item in items if len(item) > 2]

            if len(items) > 2:  # Only keep lists with 3+ items
                lists.append((title, items))

        return lists

    def _extract_markdown_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract markdown-style tables"""
        tables = []

        # Find markdown table blocks
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check if this looks like a table header
            if '|' in line and i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Check if next line is separator
                if re.match(r'^[\|\s\-:]+$', next_line):
                    # Found a table
                    table_data = self._parse_markdown_table(lines[i:])
                    if table_data:
                        tables.append(table_data)
                        i += len(table_data.get('_raw_lines', []))
                        continue

            i += 1

        return tables

    def _parse_markdown_table(self, lines: list[str]) -> dict[str, Any] | None:
        """Parse a markdown table from lines"""
        if len(lines) < 2:
            return None

        # Parse header
        header_line = lines[0].strip()
        headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]

        if not headers:
            return None

        # Skip separator line
        rows = []
        raw_lines = [lines[0], lines[1]]

        for i in range(2, len(lines)):
            line = lines[i].strip()

            if not line or '|' not in line:
                break

            cells = [cell.strip() for cell in line.split('|') if cell.strip()]

            if len(cells) == len(headers):
                row_dict = dict(zip(headers, cells, strict=False))
                rows.append(row_dict)
                raw_lines.append(lines[i])
            else:
                break

        if rows:
            return {
                "headers": headers,
                "rows": rows,
                "type": "markdown",
                "_raw_lines": raw_lines
            }

        return None

    def _extract_ascii_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract ASCII art tables"""
        tables = []

        # Look for patterns like:
        # +------+------+
        # | Col1 | Col2 |
        # +------+------+

        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check if this looks like a table border
            if re.match(r'^[+\-]+$', line) and len(line) > 5:
                # Try to parse as ASCII table
                table_data = self._parse_ascii_table(lines[i:])
                if table_data:
                    tables.append(table_data)
                    i += len(table_data.get('_raw_lines', []))
                    continue

            i += 1

        return tables

    def _parse_ascii_table(self, lines: list[str]) -> dict[str, Any] | None:
        """Parse an ASCII table from lines"""
        # Simple implementation - could be enhanced
        # This is a basic parser that handles simple ASCII tables

        if len(lines) < 3:
            return None

        # Skip implementation for now - ASCII tables are complex to parse
        return None

    def _extract_structured_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract data that appears to be tabular"""
        tables = []

        # Look for repeated patterns that suggest tabular data
        # For example:
        # Name: John, Age: 25, City: NYC
        # Name: Jane, Age: 30, City: LA

        lines = text.split('\n')
        potential_rows = []

        for line in lines:
            # Check if line contains multiple key-value pairs
            kv_matches = list(re.finditer(r'(\w+):\s*([^,\n]+)', line))

            if len(kv_matches) >= 2:
                row = {}
                for match in kv_matches:
                    key = self._normalize_key(match.group(1))
                    value = match.group(2).strip().rstrip(',')
                    row[key] = value

                potential_rows.append(row)

        # Group rows with same keys
        if potential_rows:
            key_groups = defaultdict(list)

            for row in potential_rows:
                key_tuple = tuple(sorted(row.keys()))
                key_groups[key_tuple].append(row)

            # Create tables from groups with multiple rows
            for keys, rows in key_groups.items():
                if len(rows) >= 2:
                    tables.append({
                        "headers": list(keys),
                        "rows": rows,
                        "type": "structured"
                    })

        return tables

    def _extract_indented_code(self, text: str) -> list[str]:
        """Extract indented code blocks"""
        blocks = []
        current_block = []
        in_code_block = False

        lines = text.split('\n')

        for line in lines:
            # Check if line is indented (4 spaces or tab)
            if line.startswith('    ') or line.startswith('\t'):
                in_code_block = True
                # Remove indentation
                code_line = line[4:] if line.startswith('    ') else line[1:]
                current_block.append(code_line)
            else:
                if in_code_block and current_block:
                    # End of code block
                    if len(current_block) > 1:  # Only keep multi-line blocks
                        blocks.append('\n'.join(current_block))
                    current_block = []
                    in_code_block = False

        # Don't forget the last block
        if current_block and len(current_block) > 1:
            blocks.append('\n'.join(current_block))

        return blocks

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code snippet"""
        # Simple heuristic-based detection

        # Python
        if 'def ' in code or 'import ' in code or 'print(' in code:
            return "python"

        # JavaScript
        if 'function' in code or 'const ' in code or 'let ' in code or 'var ' in code:
            return "javascript"

        # Java
        if 'public class' in code or 'private ' in code or 'System.out' in code:
            return "java"

        # SQL
        if any(keyword in code.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM']):
            return "sql"

        # JSON
        if code.strip().startswith('{') and code.strip().endswith('}'):
            try:
                json.loads(code)
                return "json"
            except:
                pass

        # HTML/XML
        if '<' in code and '>' in code:
            return "html"

        # Shell
        if code.startswith('$') or code.startswith('#!'):
            return "shell"

        return "unknown"

    def _extract_json_data(self, text: str) -> dict[str, Any] | None:
        """Extract JSON data from text"""
        # Look for JSON blocks
        json_pattern = r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]+\}'

        for match in re.finditer(json_pattern, text):
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    return data
            except:
                continue

        return None

    def _extract_yaml_data(self, text: str) -> dict[str, Any] | None:
        """Extract YAML data from text"""
        if not YAML_AVAILABLE:
            return None

        # Look for YAML blocks
        yaml_pattern = r'---\n(.*?)\n---'
        match = re.search(yaml_pattern, text, re.DOTALL)

        if match:
            try:
                data = yaml.safe_load(match.group(1))
                if isinstance(data, dict):
                    return data
            except:
                pass

        return None

    def _normalize_key(self, key: str) -> str:
        """Normalize a key for consistency"""
        # Remove special characters and normalize
        key = re.sub(r'[^\w\s]', '', key)
        key = key.strip().lower()
        key = re.sub(r'\s+', '_', key)
        return key

    def _parse_value(self, value: str) -> Any:
        """Parse a string value to appropriate type"""
        value = value.strip()

        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Try to parse as boolean
        if value.lower() in ['true', 'yes', 'on']:
            return True
        elif value.lower() in ['false', 'no', 'off']:
            return False

        # Try to parse as list
        if ',' in value:
            items = [item.strip() for item in value.split(',')]
            if len(items) > 1:
                return items

        # Return as string
        return value

    def _flatten_dict(self, d: dict[str, Any], prefix: str = '') -> dict[str, Any]:
        """Flatten nested dictionary"""
        flattened = {}

        for key, value in d.items():
            new_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, new_key))
            else:
                flattened[new_key] = value

        return flattened

    def _initialize_list_patterns(self) -> list[dict[str, Any]]:
        """Initialize patterns for list detection"""
        return [
            {"pattern": r'^\s*[-*•]\s+', "type": "bullet"},
            {"pattern": r'^\s*\d+[.)]\s+', "type": "numbered"},
            {"pattern": r'^\s*[a-z][.)]\s+', "type": "lettered"},
            {"pattern": r':\s*([^,]+(?:,\s*[^,]+)+)', "type": "comma"}
        ]

    def _initialize_table_patterns(self) -> list[dict[str, Any]]:
        """Initialize patterns for table detection"""
        return [
            {"pattern": r'\|.*\|', "type": "markdown"},
            {"pattern": r'[+\-]{5,}', "type": "ascii"},
            {"pattern": r'(\w+:\s*\w+\s*){3,}', "type": "structured"}
        ]

    def _initialize_kv_patterns(self) -> list[dict[str, Any]]:
        """Initialize patterns for key-value extraction"""
        return [
            {"pattern": r'^(\w[\w\s]*?):\s*(.+)$', "processor": None},
            {"pattern": r'^-\s*(\w[\w\s]*?):\s*(.+)$', "processor": None},
            {"pattern": r'(\w+)\s*=\s*(["\']?)(.+?)\2', "processor": lambda x: x},
            {"pattern": r'(\w+)\s*:\s*(["\']?)(.+?)\2', "processor": lambda x: x}
        ]

    def _initialize_code_patterns(self) -> list[dict[str, Any]]:
        """Initialize patterns for code detection"""
        return [
            {"pattern": r'```(\w*)\n(.*?)```', "type": "fenced"},
            {"pattern": r'`([^`]+)`', "type": "inline"},
            {"pattern": r'^    .+$', "type": "indented"}
        ]

    def get_extraction_statistics(self, structured_data: StructuredData) -> dict[str, Any]:
        """Get statistics about extracted structured data"""
        stats = {
            "total_kv_pairs": len(structured_data.key_value_pairs),
            "total_lists": len(structured_data.lists),
            "total_list_items": sum(len(lst) for lst in structured_data.lists.values()),
            "total_tables": len(structured_data.tables),
            "total_table_rows": sum(len(table.get("rows", [])) for table in structured_data.tables),
            "total_code_snippets": len(structured_data.code_snippets),
            "total_code_lines": sum(snippet.get("lines", 0) for snippet in structured_data.code_snippets),
            "code_languages": list(set(snippet.get("language", "unknown") for snippet in structured_data.code_snippets)),
            "metadata_fields": len(structured_data.metadata_fields)
        }

        return stats

    def extract_advanced_structured_data(self, text: str, **kwargs) -> StructuredData:
        """
        Extract structured data using advanced techniques
        
        Args:
            text: Input text
            **kwargs: Additional arguments for advanced extraction
            
        Returns:
            Advanced structured data
        """
        # Use advanced extractor if available
        try:
            from app.ingestion.advanced_structured_extractor import AdvancedStructuredExtractor
            advanced_extractor = AdvancedStructuredExtractor(**kwargs)
            return advanced_extractor.extract_structured_data(text)
        except ImportError:
            logger.warning("Advanced structured extraction not available, using basic extraction")
            return self.extract_structured_data(text)
