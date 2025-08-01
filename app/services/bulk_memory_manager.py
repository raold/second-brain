import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Union

import pandas as pd
from pydantic import BaseModel, Field

from app.database import get_database

#!/usr/bin/env python3
"""
Comprehensive Bulk Memory Management System
Advanced import/export functionality with multiple format support
"""

import csv
import zipfile
from enum import Enum
from io import BytesIO, StringIO


class ImportFormat(str, Enum):
    """Supported import formats"""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON Lines
    XML = "xml"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    EXCEL = "excel"
    PARQUET = "parquet"


class ExportFormat(str, Enum):
    """Supported export formats"""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    XML = "xml"
    MARKDOWN = "markdown"
    EXCEL = "excel"
    PARQUET = "parquet"
    ZIP_ARCHIVE = "zip_archive"


@dataclass
class ImportResult:
    """Result of bulk import operation"""

    total_processed: int
    successful_imports: int
    failed_imports: int
    duplicate_count: int
    processing_time: float
    errors: list[str]
    imported_ids: list[str]
    skipped_items: list[dict[str, Any]]


@dataclass
class ExportResult:
    """Result of bulk export operation"""

    total_exported: int
    file_size_bytes: int
    processing_time: float
    export_format: str
    file_path: str | None = None
    file_content: bytes | None = None


class MemoryImportModel(BaseModel):
    """Model for importing memories"""

    content: str = Field(..., description="Memory content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Memory metadata")
    memory_type: str | None = Field("semantic", description="Memory type")
    importance_score: float | None = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    tags: list[str] | None = Field(default_factory=list, description="Memory tags")
    created_at: str | None = Field(None, description="Creation timestamp")
    source: str | None = Field("bulk_import", description="Import source")


class BulkMemoryManager:
    """Advanced bulk memory management system"""

    def __init__(self):
        self.chunk_size = 100  # Process in chunks
        self.max_file_size = 100 * 1024 * 1024  # 100MB limit
        self.supported_encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

    async def import_memories(
        self,
        data: Union[str, bytes, list[dict], pd.DataFrame],
        format_type: ImportFormat,
        options: dict[str, Any] | None = None,
    ) -> ImportResult:
        """
        Import memories from various formats

        Args:
            data: Input data in specified format
            format_type: Format of the input data
            options: Additional import options

        Returns:
            ImportResult with detailed statistics
        """
        start_time = datetime.now()
        options = options or {}

        try:
            # Parse data based on format
            memories = await self._parse_import_data(data, format_type, options)

            # Validate and process memories
            result = await self._process_memory_imports(memories, options)

            # Calculate processing time
            result.processing_time = (datetime.now() - start_time).total_seconds()

            return result

        except Exception as e:
            return ImportResult(
                total_processed=0,
                successful_imports=0,
                failed_imports=0,
                duplicate_count=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=[f"Import failed: {str(e)}"],
                imported_ids=[],
                skipped_items=[],
            )

    async def export_memories(
        self,
        filter_criteria: dict[str, Any] | None = None,
        format_type: ExportFormat = ExportFormat.JSON,
        options: dict[str, Any] | None = None,
    ) -> ExportResult:
        """
        Export memories to various formats

        Args:
            filter_criteria: Criteria for filtering memories to export
            format_type: Export format
            options: Additional export options

        Returns:
            ExportResult with export details
        """
        start_time = datetime.now()
        options = options or {}

        try:
            # Get database connection
            db = await get_database()

            # Retrieve memories based on filter criteria
            memories = await self._get_memories_for_export(db, filter_criteria)

            # Export memories in specified format
            export_data = await self._format_export_data(memories, format_type, options)

            result = ExportResult(
                total_exported=len(memories),
                file_size_bytes=len(export_data) if isinstance(export_data, str | bytes) else 0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                export_format=format_type.value,
                file_content=(
                    export_data if isinstance(export_data, bytes) else export_data.encode("utf-8")
                ),
            )

            await db.close()
            return result

        except Exception as e:
            return ExportResult(
                total_exported=0,
                file_size_bytes=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                export_format=format_type.value,
                file_content=f"Export failed: {str(e)}".encode(),
            )

    async def _parse_import_data(
        self,
        data: Union[str, bytes, list[dict], pd.DataFrame],
        format_type: ImportFormat,
        options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Parse import data based on format type"""

        if format_type == ImportFormat.JSON:
            return await self._parse_json(data)
        elif format_type == ImportFormat.CSV:
            return await self._parse_csv(data, options)
        elif format_type == ImportFormat.JSONL:
            return await self._parse_jsonl(data)
        elif format_type == ImportFormat.XML:
            return await self._parse_xml(data)
        elif format_type == ImportFormat.MARKDOWN:
            return await self._parse_markdown(data)
        elif format_type == ImportFormat.PLAIN_TEXT:
            return await self._parse_plain_text(data, options)
        elif format_type == ImportFormat.EXCEL:
            return await self._parse_excel(data, options)
        elif format_type == ImportFormat.PARQUET:
            return await self._parse_parquet(data)
        else:
            raise ValueError(f"Unsupported import format: {format_type}")

    async def _parse_json(self, data: Union[str, bytes]) -> list[dict[str, Any]]:
        """Parse JSON data"""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        parsed = json.loads(data)

        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        else:
            raise ValueError("JSON data must be an object or array")

    async def _parse_csv(
        self, data: Union[str, bytes], options: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse CSV data"""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        delimiter = options.get("delimiter", ",")
        has_header = options.get("has_header", True)

        reader = (
            csv.DictReader(StringIO(data), delimiter=delimiter)
            if has_header
            else csv.reader(StringIO(data), delimiter=delimiter)
        )

        memories = []
        for row in reader:
            if has_header:
                memories.append(dict(row))
            else:
                # Assume first column is content, rest is metadata
                memories.append(
                    {
                        "content": row[0] if row else "",
                        "metadata": {"imported_data": row[1:] if len(row) > 1 else []},
                    }
                )

        return memories

    async def _parse_jsonl(self, data: Union[str, bytes]) -> list[dict[str, Any]]:
        """Parse JSON Lines data"""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        memories = []
        for line in data.strip().split("\n"):
            if line.strip():
                memories.append(json.loads(line))

        return memories

    async def _parse_xml(self, data: Union[str, bytes]) -> list[dict[str, Any]]:
        """Parse XML data (basic implementation)"""
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            raise ValueError("XML parsing requires xml library")

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        root = ET.fromstring(data)
        memories = []

        for item in root.findall(".//memory"):
            memory = {}
            for child in item:
                if child.tag == "content":
                    memory["content"] = child.text or ""
                elif child.tag == "metadata":
                    memory["metadata"] = json.loads(child.text) if child.text else {}
                else:
                    memory[child.tag] = child.text

            if "content" in memory:
                memories.append(memory)

        return memories

    async def _parse_markdown(self, data: Union[str, bytes]) -> list[dict[str, Any]]:
        """Parse Markdown data"""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        memories = []
        sections = data.split("\n## ")  # Split by H2 headers

        for i, section in enumerate(sections):
            if section.strip():
                lines = section.strip().split("\n")
                title = lines[0].replace("# ", "").replace("## ", "") if lines else f"Section {i+1}"
                content = "\n".join(lines[1:]) if len(lines) > 1 else lines[0]

                memories.append(
                    {
                        "content": content,
                        "metadata": {"title": title, "format": "markdown", "section": i + 1},
                    }
                )

        return memories

    async def _parse_plain_text(
        self, data: Union[str, bytes], options: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse plain text data"""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        split_method = options.get("split_method", "lines")  # 'lines', 'paragraphs', 'sentences'
        min_length = options.get("min_length", 10)

        if split_method == "lines":
            chunks = [line.strip() for line in data.split("\n") if len(line.strip()) >= min_length]
        elif split_method == "paragraphs":
            chunks = [
                para.strip() for para in data.split("\n\n") if len(para.strip()) >= min_length
            ]
        elif split_method == "sentences":
            # Simple sentence splitting
            import re

            sentences = re.split(r"[.!?]+", data)
            chunks = [sent.strip() for sent in sentences if len(sent.strip()) >= min_length]
        else:
            chunks = [data]

        memories = []
        for i, chunk in enumerate(chunks):
            memories.append(
                {
                    "content": chunk,
                    "metadata": {
                        "format": "plain_text",
                        "chunk_index": i,
                        "split_method": split_method,
                    },
                }
            )

        return memories

    async def _parse_excel(
        self, data: Union[str, bytes], options: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse Excel data"""
        try:
            if isinstance(data, str):
                df = pd.read_excel(data)
            else:
                df = pd.read_excel(BytesIO(data))
        except ImportError:
            raise ValueError("Excel parsing requires pandas and openpyxl libraries")

        return df.to_dict("records")

    async def _parse_parquet(self, data: Union[str, bytes]) -> list[dict[str, Any]]:
        """Parse Parquet data"""
        try:
            if isinstance(data, str):
                df = pd.read_parquet(data)
            else:
                df = pd.read_parquet(BytesIO(data))
        except ImportError:
            raise ValueError("Parquet parsing requires pandas and pyarrow libraries")

        return df.to_dict("records")

    async def _process_memory_imports(
        self, memories: list[dict[str, Any]], options: dict[str, Any]
    ) -> ImportResult:
        """Process and validate memory imports"""
        db = await get_database()

        total_processed = len(memories)
        successful_imports = 0
        failed_imports = 0
        duplicate_count = 0
        errors = []
        imported_ids = []
        skipped_items = []

        # Process in chunks
        for i in range(0, len(memories), self.chunk_size):
            chunk = memories[i : i + self.chunk_size]

            for memory_data in chunk:
                try:
                    # Validate memory data
                    validated_memory = await self._validate_memory_import(memory_data)

                    # Check for duplicates if enabled
                    if options.get("check_duplicates", True):
                        is_duplicate = await self._check_duplicate(db, validated_memory)
                        if is_duplicate:
                            duplicate_count += 1
                            if not options.get("import_duplicates", False):
                                skipped_items.append(memory_data)
                                continue

                    # Import memory
                    memory_id = await db.store_memory(
                        validated_memory["content"], validated_memory["metadata"]
                    )

                    imported_ids.append(memory_id)
                    successful_imports += 1

                except Exception as e:
                    failed_imports += 1
                    errors.append(f"Failed to import memory: {str(e)}")
                    skipped_items.append(memory_data)

        await db.close()

        return ImportResult(
            total_processed=total_processed,
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            duplicate_count=duplicate_count,
            processing_time=0.0,  # Will be set by caller
            errors=errors,
            imported_ids=imported_ids,
            skipped_items=skipped_items,
        )

    async def _validate_memory_import(self, memory_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize memory import data"""
        # Use Pydantic model for validation
        memory_model = MemoryImportModel(**memory_data)

        # Convert to dict and add additional fields
        validated = memory_model.dict()

        # Ensure metadata contains import information
        validated["metadata"].update(
            {
                "imported_at": datetime.now().isoformat(),
                "import_source": validated.get("source", "bulk_import"),
                "memory_type": validated.get("memory_type", "semantic"),
            }
        )

        # Add tags to metadata if they exist
        if validated.get("tags"):
            validated["metadata"]["tags"] = validated["tags"]

        return validated

    async def _check_duplicate(self, db, memory_data: dict[str, Any]) -> bool:
        """Check if memory is a duplicate based on content similarity"""
        # Simple duplicate check based on exact content match
        # In a real implementation, you might use semantic similarity

        search_results = await db.search_memories(
            memory_data["content"][:100],  # Use first 100 chars for search
            limit=5,
        )

        for result in search_results:
            if result["content"] == memory_data["content"]:
                return True

        return False

    async def _get_memories_for_export(
        self, db, filter_criteria: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Get memories for export based on filter criteria"""
        if not filter_criteria:
            # Export all memories
            return await db.get_all_memories(limit=10000)  # Large limit for export

        # Apply filters
        memories = await db.get_all_memories(limit=10000)
        filtered_memories = []

        for memory in memories:
            if self._matches_filter_criteria(memory, filter_criteria):
                filtered_memories.append(memory)

        return filtered_memories

    def _matches_filter_criteria(self, memory: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Check if memory matches filter criteria"""
        for key, value in criteria.items():
            if key == "memory_type" and memory.get("metadata", {}).get("memory_type") != value:
                return False
            elif key == "tags" and not any(
                tag in memory.get("metadata", {}).get("tags", []) for tag in value
            ):
                return False
            elif key == "date_from" and memory.get("created_at", "") < value:
                return False
            elif key == "date_to" and memory.get("created_at", "") > value:
                return False
            elif (
                key == "content_contains" and value.lower() not in memory.get("content", "").lower()
            ):
                return False

        return True

    async def _format_export_data(
        self, memories: list[dict[str, Any]], format_type: ExportFormat, options: dict[str, Any]
    ) -> Union[str, bytes]:
        """Format memories for export"""

        if format_type == ExportFormat.JSON:
            return json.dumps(memories, indent=2, ensure_ascii=False)
        elif format_type == ExportFormat.CSV:
            return await self._format_csv(memories, options)
        elif format_type == ExportFormat.JSONL:
            return "\n".join(json.dumps(memory, ensure_ascii=False) for memory in memories)
        elif format_type == ExportFormat.XML:
            return await self._format_xml(memories)
        elif format_type == ExportFormat.MARKDOWN:
            return await self._format_markdown(memories)
        elif format_type == ExportFormat.EXCEL:
            return await self._format_excel(memories, options)
        elif format_type == ExportFormat.PARQUET:
            return await self._format_parquet(memories)
        elif format_type == ExportFormat.ZIP_ARCHIVE:
            return await self._format_zip_archive(memories, options)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    async def _format_csv(self, memories: list[dict[str, Any]], options: dict[str, Any]) -> str:
        """Format memories as CSV"""
        if not memories:
            return ""

        # Flatten memory structure for CSV
        flattened_memories = []
        for memory in memories:
            flattened = {
                "id": memory.get("id", ""),
                "content": memory.get("content", ""),
                "memory_type": memory.get("metadata", {}).get("memory_type", ""),
                "created_at": memory.get("created_at", ""),
                "tags": ",".join(memory.get("metadata", {}).get("tags", [])),
                "metadata_json": json.dumps(memory.get("metadata", {})),
            }
            flattened_memories.append(flattened)

        # Convert to CSV
        output = StringIO()
        fieldnames = flattened_memories[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_memories)

        return output.getvalue()

    async def _format_xml(self, memories: list[dict[str, Any]]) -> str:
        """Format memories as XML"""
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            raise ValueError("XML formatting requires xml library")

        root = ET.Element("memories")

        for memory in memories:
            memory_elem = ET.SubElement(root, "memory")
            memory_elem.set("id", memory.get("id", ""))

            content_elem = ET.SubElement(memory_elem, "content")
            content_elem.text = memory.get("content", "")

            metadata_elem = ET.SubElement(memory_elem, "metadata")
            metadata_elem.text = json.dumps(memory.get("metadata", {}))

            created_elem = ET.SubElement(memory_elem, "created_at")
            created_elem.text = memory.get("created_at", "")

        return ET.tostring(root, encoding="unicode")

    async def _format_markdown(self, memories: list[dict[str, Any]]) -> str:
        """Format memories as Markdown"""
        output = ["# Exported Memories\n"]

        for i, memory in enumerate(memories, 1):
            title = memory.get("metadata", {}).get("title", f"Memory {i}")
            content = memory.get("content", "")
            created_at = memory.get("created_at", "")
            tags = memory.get("metadata", {}).get("tags", [])

            output.append(f"## {title}\n")
            output.append(f"**Created:** {created_at}\n")
            if tags:
                output.append(f"**Tags:** {', '.join(tags)}\n")
            output.append(f"\n{content}\n\n---\n")

        return "\n".join(output)

    async def _format_excel(self, memories: list[dict[str, Any]], options: dict[str, Any]) -> bytes:
        """Format memories as Excel"""
        try:
            import pandas as pd
        except ImportError:
            raise ValueError("Excel formatting requires pandas library")

        # Flatten memories for DataFrame
        flattened_memories = []
        for memory in memories:
            flattened = {
                "ID": memory.get("id", ""),
                "Content": memory.get("content", ""),
                "Memory Type": memory.get("metadata", {}).get("memory_type", ""),
                "Created At": memory.get("created_at", ""),
                "Tags": ",".join(memory.get("metadata", {}).get("tags", [])),
                "Metadata": json.dumps(memory.get("metadata", {})),
            }
            flattened_memories.append(flattened)

        df = pd.DataFrame(flattened_memories)

        # Save to bytes
        output = BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()

    async def _format_parquet(self, memories: list[dict[str, Any]]) -> bytes:
        """Format memories as Parquet"""
        try:
            import pandas as pd
        except ImportError:
            raise ValueError("Parquet formatting requires pandas and pyarrow libraries")

        # Flatten memories for DataFrame
        flattened_memories = []
        for memory in memories:
            flattened = {
                "id": memory.get("id", ""),
                "content": memory.get("content", ""),
                "memory_type": memory.get("metadata", {}).get("memory_type", ""),
                "created_at": memory.get("created_at", ""),
                "tags": json.dumps(memory.get("metadata", {}).get("tags", [])),
                "metadata": json.dumps(memory.get("metadata", {})),
            }
            flattened_memories.append(flattened)

        df = pd.DataFrame(flattened_memories)

        # Save to bytes
        output = BytesIO()
        df.to_parquet(output)
        return output.getvalue()

    async def _format_zip_archive(
        self, memories: list[dict[str, Any]], options: dict[str, Any]
    ) -> bytes:
        """Format memories as ZIP archive with multiple formats"""
        output = BytesIO()

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add JSON export
            json_data = json.dumps(memories, indent=2, ensure_ascii=False)
            zipf.writestr("memories.json", json_data)

            # Add CSV export
            csv_data = await self._format_csv(memories, options)
            zipf.writestr("memories.csv", csv_data)

            # Add Markdown export
            md_data = await self._format_markdown(memories)
            zipf.writestr("memories.md", md_data)

            # Add individual memory files
            for i, memory in enumerate(memories):
                filename = f"memory_{i+1}_{memory.get('id', 'unknown')}.json"
                zipf.writestr(f"individual/{filename}", json.dumps(memory, indent=2))

        return output.getvalue()


# Global instance
bulk_memory_manager = BulkMemoryManager()


async def get_bulk_memory_manager() -> BulkMemoryManager:
    """Get bulk memory manager instance"""
    return bulk_memory_manager
