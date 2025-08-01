import json
import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.ingestion.models import StructuredData
from app.utils.logging_config import get_logger

# Optional dependencies
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import xml.etree.ElementTree as ET
except ImportError:
    ET = None

"""
Advanced structured data extraction with enhanced parsing capabilities
"""

import ast

from app.models.ingestion import StructuredData
from app.services.structured_data_extractor import StructuredDataExtractor

logger = get_logger(__name__)


class AdvancedStructuredExtractor(StructuredDataExtractor):
    """Advanced structured data extraction with enhanced capabilities"""

    def __init__(
        self,
        enable_form_extraction: bool = True,
        enable_schema_inference: bool = True,
        enable_ast_parsing: bool = True,
        enable_semantic_parsing: bool = True,
    ):
        """
        Initialize advanced structured extractor

        Args:
            enable_form_extraction: Extract form-like data
            enable_schema_inference: Infer schemas from data
            enable_ast_parsing: Use AST for code analysis
            enable_semantic_parsing: Use semantic patterns
        """
        super().__init__()

        self.enable_form_extraction = enable_form_extraction
        self.enable_schema_inference = enable_schema_inference
        self.enable_ast_parsing = enable_ast_parsing
        self.enable_semantic_parsing = enable_semantic_parsing

        # Initialize advanced patterns
        self.form_patterns = self._initialize_form_patterns()
        self.semantic_patterns = self._initialize_semantic_patterns()
        self.data_type_patterns = self._initialize_data_type_patterns()

    def extract_structured_data(self, text: str) -> StructuredData:
        """
        Extract structured data with advanced techniques

        Args:
            text: Input text

        Returns:
            Enhanced structured data
        """
        # Get basic extraction from parent
        base_data = super().extract_structured_data(text)

        # Enhance with advanced extraction
        enhanced_data = self._enhance_structured_data(base_data, text)

        return enhanced_data

    def _enhance_structured_data(self, base_data: StructuredData, text: str) -> StructuredData:
        """Enhance structured data with advanced extraction"""
        # Extract additional structured elements
        forms = self._extract_forms(text) if self.enable_form_extraction else {}
        schemas = self._infer_schemas(base_data) if self.enable_schema_inference else {}
        enhanced_code = (
            self._enhance_code_extraction(base_data.code_snippets, text)
            if self.enable_ast_parsing
            else []
        )
        semantic_data = (
            self._extract_semantic_structures(text) if self.enable_semantic_parsing else {}
        )

        # Extract advanced table formats
        csv_tables = self._extract_csv_tables(text)
        html_tables = self._extract_html_tables(text)

        # Extract configuration data
        config_data = self._extract_configuration_data(text)

        # Extract API specifications
        api_specs = self._extract_api_specifications(text)

        # Combine all tables
        all_tables = base_data.tables + csv_tables + html_tables

        # Combine all code snippets
        all_code = enhanced_code if enhanced_code else base_data.code_snippets

        # Create enhanced metadata
        enhanced_metadata = {
            **base_data.metadata_fields,
            "forms": forms,
            "schemas": schemas,
            "semantic_structures": semantic_data,
            "configurations": config_data,
            "api_specifications": api_specs,
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "enhanced_features": {
                "form_extraction": self.enable_form_extraction,
                "schema_inference": self.enable_schema_inference,
                "ast_parsing": self.enable_ast_parsing,
                "semantic_parsing": self.enable_semantic_parsing,
            },
        }

        return StructuredData(
            key_value_pairs=base_data.key_value_pairs,
            lists=base_data.lists,
            tables=all_tables,
            code_snippets=all_code,
            metadata_fields=enhanced_metadata,
        )

    def _extract_forms(self, text: str) -> dict[str, Any]:
        """Extract form-like structures from text"""
        forms = {}

        # Extract question-answer pairs
        qa_pairs = self._extract_qa_pairs(text)
        if qa_pairs:
            forms["qa_pairs"] = qa_pairs

        # Extract checkbox/radio button patterns
        selections = self._extract_selections(text)
        if selections:
            forms["selections"] = selections

        # Extract form fields
        fields = self._extract_form_fields(text)
        if fields:
            forms["form_fields"] = fields

        return forms

    def _extract_qa_pairs(self, text: str) -> list[dict[str, str]]:
        """Extract question-answer pairs"""
        qa_pairs = []

        # Pattern for Q: ... A: ...
        qa_pattern = r"Q:\s*(.+?)\s*A:\s*(.+?)(?=Q:|$)"
        for match in re.finditer(qa_pattern, text, re.DOTALL | re.IGNORECASE):
            question = match.group(1).strip()
            answer = match.group(2).strip()
            qa_pairs.append({"question": question, "answer": answer})

        # Pattern for numbered questions
        numbered_pattern = r"(\d+)\.\s*(.+?\?)\s*(?:Answer:|A:)?\s*(.+?)(?=\d+\.|$)"
        for match in re.finditer(numbered_pattern, text, re.DOTALL):
            number = match.group(1)
            question = match.group(2).strip()
            answer = match.group(3).strip()
            qa_pairs.append({"number": number, "question": question, "answer": answer})

        return qa_pairs

    def _extract_selections(self, text: str) -> list[dict[str, Any]]:
        """Extract checkbox/radio button selections"""
        selections = []

        # Checkbox patterns: [x], [ ], [X], etc.
        checkbox_pattern = r"\[([ xX])\]\s*(.+?)(?=\[|$)"
        for match in re.finditer(checkbox_pattern, text):
            checked = match.group(1).strip() != ""
            label = match.group(2).strip()
            selections.append({"type": "checkbox", "checked": checked, "label": label})

        # Radio button patterns: (x), ( ), (*), etc.
        radio_pattern = r"\(([ xX*])\)\s*(.+?)(?=\(|$)"
        for match in re.finditer(radio_pattern, text):
            selected = match.group(1).strip() != ""
            label = match.group(2).strip()
            selections.append({"type": "radio", "selected": selected, "label": label})

        return selections

    def _extract_form_fields(self, text: str) -> list[dict[str, Any]]:
        """Extract form field patterns"""
        fields = []

        # Pattern for form fields like: Name: _______ or Name: [        ]
        field_patterns = [
            r"(\w[\w\s]*?):\s*_{3,}",
            r"(\w[\w\s]*?):\s*\[[\s]*\]",
            r"(\w[\w\s]*?):\s*\([\s]*\)",
            r"(\w[\w\s]*?):\s*\.{3,}",
        ]

        for pattern in field_patterns:
            for match in re.finditer(pattern, text):
                field_name = match.group(1).strip()
                fields.append(
                    {
                        "name": field_name,
                        "type": "text",
                        "required": (
                            True if field_name.lower() in ["name", "email", "phone"] else False
                        ),
                    }
                )

        return fields

    def _infer_schemas(self, data: StructuredData) -> dict[str, Any]:
        """Infer data schemas from extracted data"""
        schemas = {}

        # Infer schema from tables
        if data.tables:
            table_schemas = []
            for i, table in enumerate(data.tables):
                schema = self._infer_table_schema(table)
                if schema:
                    table_schemas.append({"table_index": i, "schema": schema})
            if table_schemas:
                schemas["table_schemas"] = table_schemas

        # Infer schema from key-value pairs
        if data.key_value_pairs:
            kv_schema = self._infer_kv_schema(data.key_value_pairs)
            if kv_schema:
                schemas["kv_schema"] = kv_schema

        # Infer schema from lists
        if data.lists:
            list_schemas = self._infer_list_schemas(data.lists)
            if list_schemas:
                schemas["list_schemas"] = list_schemas

        return schemas

    def _infer_table_schema(self, table: dict[str, Any]) -> dict[str, Any] | None:
        """Infer schema for a table"""
        if not table.get("rows"):
            return None

        schema = {
            "columns": {},
            "row_count": len(table["rows"]),
            "nullable_columns": [],
            "unique_columns": [],
        }

        # Analyze each column
        headers = table.get("headers", [])
        for header in headers:
            column_values = [row.get(header) for row in table["rows"] if header in row]

            # Infer column type
            column_type = self._infer_column_type(column_values)
            schema["columns"][header] = {
                "type": column_type,
                "nullable": any(v is None or v == "" for v in column_values),
                "unique": len(set(column_values)) == len(column_values),
                "sample_values": list(set(column_values))[:5],
            }

            if schema["columns"][header]["nullable"]:
                schema["nullable_columns"].append(header)
            if schema["columns"][header]["unique"]:
                schema["unique_columns"].append(header)

        return schema

    def _infer_column_type(self, values: list[Any]) -> str:
        """Infer the data type of a column"""
        non_empty_values = [v for v in values if v and str(v).strip()]

        if not non_empty_values:
            return "empty"

        # Check if all values are numbers
        try:
            numeric_values = [float(v) for v in non_empty_values]
            if all(v.is_integer() for v in numeric_values):
                return "integer"
            return "float"
        except (ValueError, TypeError):
            pass

        # Check if all values are dates
        date_patterns = [r"^\d{4}-\d{2}-\d{2}$", r"^\d{2}/\d{2}/\d{4}$", r"^\d{2}-\d{2}-\d{4}$"]
        if all(any(re.match(p, str(v)) for p in date_patterns) for v in non_empty_values):
            return "date"

        # Check if all values are booleans
        bool_values = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
        if all(str(v).lower() in bool_values for v in non_empty_values):
            return "boolean"

        # Check if values look like emails
        if all("@" in str(v) and "." in str(v) for v in non_empty_values):
            return "email"

        # Check if values look like URLs
        if all(str(v).startswith(("http://", "https://")) for v in non_empty_values):
            return "url"

        return "string"

    def _infer_kv_schema(self, kv_pairs: dict[str, Any]) -> dict[str, Any]:
        """Infer schema from key-value pairs"""
        schema = {"properties": {}, "required": [], "total_fields": len(kv_pairs)}

        for key, value in kv_pairs.items():
            value_type = self._infer_value_type(value)
            schema["properties"][key] = {"type": value_type, "value": value}

            # Common required fields
            if key.lower() in ["id", "name", "title", "type"]:
                schema["required"].append(key)

        return schema

    def _infer_value_type(self, value: Any) -> str:
        """Infer the type of a value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif isinstance(value, str):
            # Check for specific string types
            if re.match(r"^\d{4}-\d{2}-\d{2}", value):
                return "date"
            elif "@" in value and "." in value:
                return "email"
            elif value.startswith(("http://", "https://")):
                return "url"
            else:
                return "string"
        else:
            return "unknown"

    def _infer_list_schemas(self, lists: dict[str, list[str]]) -> dict[str, Any]:
        """Infer schemas from lists"""
        schemas = {}

        for list_name, items in lists.items():
            if items:
                # Analyze list items
                item_types = [self._infer_value_type(item) for item in items]
                unique_types = set(item_types)

                schemas[list_name] = {
                    "item_count": len(items),
                    "unique_items": len(set(items)),
                    "item_types": list(unique_types),
                    "homogeneous": len(unique_types) == 1,
                    "sample_items": items[:5],
                }

        return schemas

    def _enhance_code_extraction(
        self, code_snippets: list[dict[str, str]], text: str
    ) -> list[dict[str, Any]]:
        """Enhance code extraction with AST parsing"""
        enhanced_snippets = []

        for snippet in code_snippets:
            enhanced = dict(snippet)
            code = snippet.get("code", "")
            language = snippet.get("language", "unknown")

            # Add complexity analysis
            enhanced["complexity"] = self._analyze_code_complexity(code, language)

            # Extract code structure
            if language == "python" and self.enable_ast_parsing:
                structure = self._extract_python_structure(code)
                if structure:
                    enhanced["structure"] = structure

            # Extract imports/dependencies
            enhanced["dependencies"] = self._extract_dependencies(code, language)

            # Extract function/class definitions
            enhanced["definitions"] = self._extract_definitions(code, language)

            enhanced_snippets.append(enhanced)

        return enhanced_snippets

    def _analyze_code_complexity(self, code: str, language: str) -> dict[str, Any]:
        """Analyze code complexity metrics"""
        lines = code.split("\n")

        complexity = {
            "lines_of_code": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "comment_lines": 0,
            "max_line_length": max(len(l) for l in lines) if lines else 0,
            "indentation_levels": 0,
        }

        # Count comment lines
        if language == "python":
            complexity["comment_lines"] = len([l for l in lines if l.strip().startswith("#")])
        elif language in ["javascript", "java"]:
            complexity["comment_lines"] = len([l for l in lines if l.strip().startswith("//")])

        # Calculate max indentation
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                complexity["indentation_levels"] = max(
                    complexity["indentation_levels"], indent // 4
                )

        return complexity

    def _extract_python_structure(self, code: str) -> dict[str, Any] | None:
        """Extract structure from Python code using AST"""
        try:
            tree = ast.parse(code)

            structure = {
                "imports": [],
                "functions": [],
                "classes": [],
                "variables": [],
                "decorators": [],
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        structure["imports"].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [
                            d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list
                        ],
                        "docstring": ast.get_docstring(node),
                        "lineno": node.lineno,
                    }
                    structure["functions"].append(func_info)
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "bases": [
                            base.id if isinstance(base, ast.Name) else str(base)
                            for base in node.bases
                        ],
                        "decorators": [
                            d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list
                        ],
                        "docstring": ast.get_docstring(node),
                        "methods": [],
                        "lineno": node.lineno,
                    }

                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append(item.name)

                    structure["classes"].append(class_info)
                elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    if not var_name.startswith("_"):
                        structure["variables"].append(var_name)

            return structure

        except SyntaxError:
            return None

    def _extract_dependencies(self, code: str, language: str) -> list[str]:
        """Extract dependencies from code"""
        dependencies = []

        if language == "python":
            # Extract imports
            import_patterns = [
                r"import\s+(\w+)",
                r"from\s+(\w+)\s+import",
                r"import\s+(\w+)\s+as\s+\w+",
            ]
            for pattern in import_patterns:
                dependencies.extend(re.findall(pattern, code))

        elif language == "javascript":
            # Extract requires and imports
            js_patterns = [
                r'require\([\'"]([^\'"]+ )[\'\"]\)',
                r'import\s+.*\s+from\s+[\'"]([^\'"]+ )[\'"]',
                r'import\s+[\'"]([^\'"]+ )[\'"]',
            ]
            for pattern in js_patterns:
                dependencies.extend(re.findall(pattern, code))

        elif language == "java":
            # Extract imports
            java_pattern = r"import\s+([\w.]+);"
            dependencies.extend(re.findall(java_pattern, code))

        return list(set(dependencies))

    def _extract_definitions(self, code: str, language: str) -> dict[str, list[str]]:
        """Extract function and class definitions"""
        definitions = {"functions": [], "classes": [], "methods": []}

        if language == "python":
            definitions["functions"] = re.findall(r"def\s+(\w+)\s*\(", code)
            definitions["classes"] = re.findall(r"class\s+(\w+)\s*[:\(]", code)

        elif language == "javascript":
            # Function declarations and expressions
            definitions["functions"].extend(re.findall(r"function\s+(\w+)\s*\(", code))
            definitions["functions"].extend(
                re.findall(r"const\s+(\w+)\s*=\s*(?:async\s+)?function", code)
            )
            definitions["functions"].extend(
                re.findall(r"const\s+(\w+)\s*=\s*(?:async\s+)?\(", code)
            )
            definitions["classes"] = re.findall(r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{", code)

        elif language == "java":
            definitions["classes"] = re.findall(
                r"class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{", code
            )
            definitions["functions"] = re.findall(
                r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(", code
            )

        return definitions

    def _extract_semantic_structures(self, text: str) -> dict[str, Any]:
        """Extract semantic structures using patterns"""
        semantic_data = {}

        # Extract definitions
        definitions = self._extract_definitions_semantic(text)
        if definitions:
            semantic_data["definitions"] = definitions

        # Extract specifications
        specifications = self._extract_specifications(text)
        if specifications:
            semantic_data["specifications"] = specifications

        # Extract requirements
        requirements = self._extract_requirements(text)
        if requirements:
            semantic_data["requirements"] = requirements

        # Extract procedures/steps
        procedures = self._extract_procedures(text)
        if procedures:
            semantic_data["procedures"] = procedures

        return semantic_data

    def _extract_definitions_semantic(self, text: str) -> list[dict[str, str]]:
        """Extract definition patterns"""
        definitions = []

        # Pattern: "X is defined as Y"
        patterns = [
            r"(\w[\w\s]*?)\s+is\s+defined\s+as\s+(.+?)(?:\.|$)",
            r"(\w[\w\s]*?):\s*(?:a|an)\s+(.+?)(?:\.|$)",
            r"Definition\s+of\s+(\w[\w\s]*?):\s*(.+?)(?:\.|$)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                term = match.group(1).strip()
                definition = match.group(2).strip()
                definitions.append({"term": term, "definition": definition})

        return definitions

    def _extract_specifications(self, text: str) -> list[dict[str, Any]]:
        """Extract specification patterns"""
        specs = []

        # Look for specification-like patterns
        spec_keywords = ["specification", "spec", "requirement", "must", "shall", "should"]

        lines = text.split("\n")

        for line in lines:
            line_lower = line.lower()

            # Check if line contains spec keywords
            if any(keyword in line_lower for keyword in spec_keywords):
                # Extract spec ID if present
                id_match = re.match(r"([\w\-]+\d+[\w\-]*)\s*[:\-]\s*(.+)", line)
                if id_match:
                    spec_id = id_match.group(1)
                    content = id_match.group(2)
                else:
                    spec_id = None
                    content = line

                specs.append(
                    {
                        "id": spec_id,
                        "content": content.strip(),
                        "type": (
                            "requirement"
                            if any(k in line_lower for k in ["must", "shall"])
                            else "specification"
                        ),
                    }
                )

        return specs

    def _extract_requirements(self, text: str) -> list[dict[str, str]]:
        """Extract requirement patterns"""
        requirements = []

        # Pattern for requirements
        req_patterns = [
            r"(?:must|shall|should)\s+(.+?)(?:\.|$)",
            r"(?:required|requirement):\s*(.+?)(?:\.|$)",
            r"(?:REQ[\-_]?\d+):\s*(.+?)(?:\.|$)",
        ]

        for pattern in req_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                requirement = match.group(1).strip() if match.group(1) else match.group(0).strip()
                requirements.append(
                    {
                        "requirement": requirement,
                        "priority": (
                            "high"
                            if "must" in match.group(0).lower() or "shall" in match.group(0).lower()
                            else "medium"
                        ),
                    }
                )

        return requirements

    def _extract_procedures(self, text: str) -> list[dict[str, Any]]:
        """Extract procedure/step patterns"""
        procedures = []

        # Look for step patterns
        step_pattern = r"(?:step\s+)?(\d+)[.)]\s*(.+?)(?=(?:step\s+)?\d+[.)]|$)"

        matches = list(re.finditer(step_pattern, text, re.IGNORECASE | re.DOTALL))

        if len(matches) > 1:
            steps = []
            for match in matches:
                step_num = match.group(1)
                step_content = match.group(2).strip()
                steps.append({"step_number": int(step_num), "description": step_content})

            if steps:
                procedures.append(
                    {"type": "numbered_procedure", "steps": steps, "total_steps": len(steps)}
                )

        return procedures

    def _extract_csv_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract CSV-formatted tables"""
        tables = []

        # Look for CSV-like patterns
        lines = text.split("\n")
        csv_blocks = []
        current_block = []

        for line in lines:
            # Check if line contains commas and looks like CSV
            if "," in line and len(line.split(",")) >= 2:
                current_block.append(line)
            else:
                if len(current_block) >= 2:
                    csv_blocks.append(current_block)
                current_block = []

        # Process CSV blocks
        for block in csv_blocks:
            if PANDAS_AVAILABLE:
                try:
                    # Try to parse as CSV using pandas
                    import io

                    csv_text = "\n".join(block)
                    df = pd.read_csv(io.StringIO(csv_text))

                    table = {
                        "type": "csv",
                        "headers": df.columns.tolist(),
                        "rows": df.to_dict("records"),
                        "shape": df.shape,
                    }
                    tables.append(table)
                except Exception:
                    pass
            else:
                # Manual CSV parsing
                if block:
                    headers = [h.strip() for h in block[0].split(",")]
                    rows = []

                    for line in block[1:]:
                        cells = [c.strip() for c in line.split(",")]
                        if len(cells) == len(headers):
                            row = dict(zip(headers, cells, strict=False))
                            rows.append(row)

                    if rows:
                        tables.append({"type": "csv", "headers": headers, "rows": rows})

        return tables

    def _extract_html_tables(self, text: str) -> list[dict[str, Any]]:
        """Extract HTML tables"""
        tables = []

        # Look for HTML table tags
        table_pattern = r"<table[^>]*>.*?</table>"

        for match in re.finditer(table_pattern, text, re.DOTALL | re.IGNORECASE):
            table_html = match.group(0)

            if BS4_AVAILABLE:
                try:
                    soup = BeautifulSoup(table_html, "html.parser")
                    table = soup.find("table")

                    if table:
                        # Extract headers
                        headers = []
                        header_row = table.find("tr")
                        if header_row:
                            headers = [
                                th.get_text(strip=True) for th in header_row.find_all(["th", "td"])
                            ]

                        # Extract rows
                        rows = []
                        for tr in table.find_all("tr")[1:]:
                            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                            if len(cells) == len(headers):
                                row = dict(zip(headers, cells, strict=False))
                                rows.append(row)

                        if rows:
                            tables.append({"type": "html", "headers": headers, "rows": rows})
                except Exception:
                    pass
            else:
                # Basic HTML parsing without BeautifulSoup
                # Extract table rows
                row_pattern = r"<tr[^>]*>(.*?)</tr>"
                rows_html = re.findall(row_pattern, table_html, re.DOTALL)

                if rows_html:
                    # Extract headers from first row
                    header_pattern = r"<t[hd][^>]*>(.*?)</t[hd]>"
                    headers = re.findall(header_pattern, rows_html[0])
                    headers = [re.sub(r"<[^>]+>", "", h).strip() for h in headers]

                    # Extract data rows
                    rows = []
                    for row_html in rows_html[1:]:
                        cells = re.findall(header_pattern, row_html)
                        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                        if len(cells) == len(headers):
                            row = dict(zip(headers, cells, strict=False))
                            rows.append(row)

                    if rows:
                        tables.append({"type": "html", "headers": headers, "rows": rows})

        return tables

    def _extract_configuration_data(self, text: str) -> dict[str, Any]:
        """Extract configuration data patterns"""
        configs = {}

        # Extract INI-style configurations
        ini_configs = self._extract_ini_configs(text)
        if ini_configs:
            configs["ini"] = ini_configs

        # Extract environment variable patterns
        env_vars = self._extract_env_vars(text)
        if env_vars:
            configs["environment"] = env_vars

        # Extract XML configurations
        xml_configs = self._extract_xml_configs(text)
        if xml_configs:
            configs["xml"] = xml_configs

        return configs

    def _extract_ini_configs(self, text: str) -> dict[str, dict[str, str]]:
        """Extract INI-style configuration"""
        configs = {}
        current_section = None

        ini_section_pattern = r"^\[([^\]]+)\]"
        ini_kv_pattern = r"^(\w+)\s*=\s*(.+)$"

        for line in text.split("\n"):
            line = line.strip()

            # Check for section
            section_match = re.match(ini_section_pattern, line)
            if section_match:
                current_section = section_match.group(1)
                configs[current_section] = {}
                continue

            # Check for key-value pair
            if current_section:
                kv_match = re.match(ini_kv_pattern, line)
                if kv_match:
                    key = kv_match.group(1)
                    value = kv_match.group(2).strip("\"'")
                    configs[current_section][key] = value

        return configs

    def _extract_env_vars(self, text: str) -> dict[str, str]:
        """Extract environment variable patterns"""
        env_vars = {}

        # Pattern for environment variables
        env_patterns = [
            r"(?:export\s+)?([A-Z_]+)=([^\s]+)",
            r"([A-Z_]+):\s*([^\n]+)",
            r"\$\{?([A-Z_]+)\}?",
        ]

        for pattern in env_patterns[:2]:  # Only use set patterns
            for match in re.finditer(pattern, text):
                var_name = match.group(1)
                var_value = match.group(2).strip("\"'")
                env_vars[var_name] = var_value

        return env_vars

    def _extract_xml_configs(self, text: str) -> dict[str, Any]:
        """Extract XML configuration data"""
        configs = {}

        # Find XML blocks
        xml_pattern = r"<\?xml[^>]*\?>.*?(?=<\?xml|$)"

        for match in re.finditer(xml_pattern, text, re.DOTALL):
            try:
                xml_text = match.group(0)
                root = ET.fromstring(xml_text)

                # Convert XML to dictionary
                xml_dict = self._xml_to_dict(root)
                if xml_dict:
                    configs[root.tag] = xml_dict
            except Exception:
                pass

        return configs

    def _xml_to_dict(self, element: ET.Element) -> dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            result["text"] = element.text.strip()

        # Add child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                # Convert to list if multiple children with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data

        return result

    def _extract_api_specifications(self, text: str) -> dict[str, Any]:
        """Extract API specification patterns"""
        api_specs = {}

        # Extract REST API endpoints
        endpoints = self._extract_api_endpoints(text)
        if endpoints:
            api_specs["endpoints"] = endpoints

        # Extract API responses
        responses = self._extract_api_responses(text)
        if responses:
            api_specs["responses"] = responses

        # Extract API parameters
        parameters = self._extract_api_parameters(text)
        if parameters:
            api_specs["parameters"] = parameters

        return api_specs

    def _extract_api_endpoints(self, text: str) -> list[dict[str, str]]:
        """Extract API endpoint patterns"""
        endpoints = []

        # Pattern for HTTP methods and paths
        endpoint_pattern = r"(GET|POST|PUT|DELETE|PATCH)\s+(/[\w/\-{}:]+)"

        for match in re.finditer(endpoint_pattern, text):
            method = match.group(1)
            path = match.group(2)
            endpoints.append(
                {"method": method, "path": path, "parameters": re.findall(r"\{(\w+)\}", path)}
            )

        return endpoints

    def _extract_api_responses(self, text: str) -> list[dict[str, Any]]:
        """Extract API response examples"""
        responses = []

        # Look for response patterns
        response_keywords = ["response", "returns", "output"]

        # Find JSON responses
        json_pattern = (
            r"(?:" + "|".join(response_keywords) + r")[:\s]*(\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]+\})"
        )

        for match in re.finditer(json_pattern, text, re.IGNORECASE):
            try:
                response_data = json.loads(match.group(1))
                responses.append(
                    {"type": "json", "data": response_data, "status": 200}  # Default assumption
                )
            except Exception:
                pass

        return responses

    def _extract_api_parameters(self, text: str) -> list[dict[str, Any]]:
        """Extract API parameter descriptions"""
        parameters = []

        # Pattern for parameter descriptions
        param_patterns = [
            r"(?:param|parameter)\s+(\w+)\s*:\s*(.+?)(?=param|parameter|$)",
            r"@param\s+\{(\w+)\}\s+(\w+)\s*-?\s*(.+?)(?=@|$)",
        ]

        for pattern in param_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                if len(match.groups()) == 2:
                    param_name = match.group(1)
                    param_desc = match.group(2).strip()
                else:
                    param_type = match.group(1)
                    param_name = match.group(2)
                    param_desc = match.group(3).strip()

                parameters.append(
                    {
                        "name": param_name,
                        "description": param_desc,
                        "type": param_type if len(match.groups()) > 2 else "unknown",
                    }
                )

        return parameters

    def _initialize_form_patterns(self) -> list[dict[str, Any]]:
        """Initialize form detection patterns"""
        return [
            {"pattern": r"Q:\s*(.+?)\s*A:\s*(.+)", "type": "qa"},
            {"pattern": r"\[([ xX])\]\s*(.+)", "type": "checkbox"},
            {"pattern": r"\(([ xX*])\)\s*(.+)", "type": "radio"},
            {"pattern": r"(\w+):\s*_{3,}", "type": "fill_blank"},
        ]

    def _initialize_semantic_patterns(self) -> list[dict[str, Any]]:
        """Initialize semantic pattern detection"""
        return [
            {"pattern": r"is defined as", "type": "definition"},
            {"pattern": r"(?:must|shall|should)\s+", "type": "requirement"},
            {"pattern": r"step\s+\d+", "type": "procedure"},
            {"pattern": r"(?:spec|specification):\s*", "type": "specification"},
        ]

    def _initialize_data_type_patterns(self) -> list[dict[str, Any]]:
        """Initialize data type detection patterns"""
        return [
            {"pattern": r"^\d{4}-\d{2}-\d{2}", "type": "date"},
            {"pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$", "type": "email"},
            {"pattern": r"^https?://", "type": "url"},
            {"pattern": r"^\d+$", "type": "integer"},
            {"pattern": r"^\d+\.\d+$", "type": "float"},
            {"pattern": r"^(?:true|false|yes|no)$", "type": "boolean"},
        ]
