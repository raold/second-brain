"""
Export/Import system for v2.8.2 Week 4.

This service handles exporting knowledge to various formats
and importing from external sources.
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Optional

import yaml

from app.database import Database
from app.models.memory import Memory, MemoryType
from app.models.synthesis.advanced_models import ExportFormat, ExportRequest, ExportResult, ImportRequest, ImportResult
from app.services.memory_relationship_analyzer import MemoryRelationshipAnalyzer as RelationshipAnalyzer
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ExportImportService:
    """Service for knowledge export and import operations."""

    def __init__(
        self,
        database: Database,
        memory_service: MemoryService,
        relationship_analyzer: RelationshipAnalyzer
    ):
        self.db = database
        self.memory_service = memory_service
        self.relationship_analyzer = relationship_analyzer

        # Export handlers
        self.export_handlers = {
            ExportFormat.MARKDOWN: self._export_markdown,
            ExportFormat.JSON: self._export_json,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.OBSIDIAN: self._export_obsidian,
            ExportFormat.ROAM: self._export_roam,
            ExportFormat.ANKI: self._export_anki,
            ExportFormat.GRAPHML: self._export_graphml,
            ExportFormat.PDF: self._export_pdf
        }

        # Import handlers
        self.import_handlers = {
            ExportFormat.MARKDOWN: self._import_markdown,
            ExportFormat.JSON: self._import_json,
            ExportFormat.CSV: self._import_csv,
            ExportFormat.OBSIDIAN: self._import_obsidian,
            ExportFormat.ROAM: self._import_roam,
            ExportFormat.ANKI: self._import_anki
        }

    async def export_knowledge(
        self,
        request: ExportRequest
    ) -> ExportResult:
        """Export knowledge to specified format."""
        # Fetch memories to export
        memories = await self._fetch_export_memories(request)

        if not memories:
            return ExportResult(
                format=request.format,
                memory_count=0,
                relationship_count=0,
                content="No memories to export"
            )

        # Fetch relationships if requested
        relationships = []
        if request.include_relationships:
            relationships = await self._fetch_relationships(
                memories, request.user_id
            )

        # Execute export
        handler = self.export_handlers.get(request.format)
        if not handler:
            raise ValueError(f"Unsupported export format: {request.format}")

        result = await handler(memories, relationships, request)

        # Update statistics
        result.memory_count = len(memories)
        result.relationship_count = len(relationships)

        return result

    async def import_knowledge(
        self,
        request: ImportRequest
    ) -> ImportResult:
        """Import knowledge from external source."""
        start_time = datetime.utcnow()

        # Parse source content
        handler = self.import_handlers.get(request.format)
        if not handler:
            raise ValueError(f"Unsupported import format: {request.format}")

        # Execute import
        result = await handler(request)

        # Calculate duration
        result.duration_seconds = (
            datetime.utcnow() - start_time
        ).total_seconds()

        return result

    async def _fetch_export_memories(
        self,
        request: ExportRequest
    ) -> list[Memory]:
        """Fetch memories for export."""
        if request.memory_ids:
            # Fetch specific memories
            memories = []
            for memory_id in request.memory_ids:
                try:
                    memory = await self.memory_service.get_memory(str(memory_id))
                    if memory:
                        memories.append(memory)
                except Exception as e:
                    logger.error(f"Error fetching memory {memory_id}: {e}")

            return memories

        # Fetch all memories with filters
        search_result = await self.memory_service.search_memories(
            query="",
            user_id=request.user_id,
            limit=10000  # High limit for export
        )

        memories = search_result.memories if search_result else []

        # Apply filters
        if request.tags:
            tag_set = set(request.tags)
            memories = [
                m for m in memories
                if m.tags and tag_set.intersection(m.tags)
            ]

        if request.importance_threshold is not None:
            memories = [
                m for m in memories
                if m.importance >= request.importance_threshold
            ]

        if request.date_range:
            start = request.date_range.get('start')
            end = request.date_range.get('end')

            if start:
                memories = [m for m in memories if m.created_at >= start]
            if end:
                memories = [m for m in memories if m.created_at <= end]

        return memories

    async def _fetch_relationships(
        self,
        memories: list[Memory],
        user_id: str
    ) -> list[Any]:
        """Fetch relationships between memories."""
        relationships = []
        memory_ids = {m.id for m in memories}

        for memory in memories:
            rels = await self.relationship_analyzer.find_related_memories(
                memory.id, user_id, limit=100
            )

            # Include only relationships within export set
            for rel in rels:
                if rel.target_memory_id in memory_ids:
                    relationships.append(rel)

        return relationships

    # Export Handlers

    async def _export_markdown(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to Markdown format."""
        content_parts = []

        # Add header
        content_parts.append("# Second Brain Export")
        content_parts.append(f"\nExported on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append(f"Total memories: {len(memories)}\n")

        # Sort memories by date or importance
        sort_by = request.format_options.get('sort_by', 'date')
        if sort_by == 'importance':
            memories.sort(key=lambda m: m.importance, reverse=True)
        else:
            memories.sort(key=lambda m: m.created_at)

        # Export memories
        for memory in memories:
            content_parts.append(f"\n## {memory.title}")

            # Metadata
            if request.include_metadata:
                content_parts.append(f"*Type: {memory.memory_type.value}*")
                content_parts.append(f"*Created: {memory.created_at.strftime('%Y-%m-%d')}*")
                content_parts.append(f"*Importance: {memory.importance}/10*")

                if memory.tags:
                    tags_str = ", ".join(f"#{tag}" for tag in memory.tags)
                    content_parts.append(f"*Tags: {tags_str}*")

            content_parts.append("")
            content_parts.append(memory.content)

            # Add relationships
            if relationships:
                related = [
                    r for r in relationships
                    if r.source_memory_id == memory.id
                ]
                if related:
                    content_parts.append("\n**Related to:**")
                    for rel in related:
                        # Find target memory
                        target = next(
                            (m for m in memories if m.id == rel.target_memory_id),
                            None
                        )
                        if target:
                            content_parts.append(
                                f"- [{target.title}](#{target.id}) "
                                f"({rel.relationship_type})"
                            )

            content_parts.append("\n---")

        content = "\n".join(content_parts)

        return ExportResult(
            format=ExportFormat.MARKDOWN,
            content=content,
            file_size_bytes=len(content.encode('utf-8'))
        )

    async def _export_json(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to JSON format."""
        export_data = {
            "version": "2.8.2",
            "exported_at": datetime.utcnow().isoformat(),
            "memories": [],
            "relationships": []
        }

        # Export memories
        for memory in memories:
            memory_data = {
                "id": str(memory.id),
                "title": memory.title,
                "content": memory.content,
                "type": memory.memory_type.value,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat()
            }

            if request.include_metadata:
                memory_data.update({
                    "tags": memory.tags or [],
                    "embedding": memory.embedding.tolist() if memory.embedding is not None else None,
                    "updated_at": memory.updated_at.isoformat() if memory.updated_at else None
                })

            export_data["memories"].append(memory_data)

        # Export relationships
        if relationships:
            for rel in relationships:
                rel_data = {
                    "source": str(rel.source_memory_id),
                    "target": str(rel.target_memory_id),
                    "type": rel.relationship_type,
                    "strength": rel.strength
                }
                export_data["relationships"].append(rel_data)

        content = json.dumps(export_data, indent=2)

        return ExportResult(
            format=ExportFormat.JSON,
            content=content,
            file_size_bytes=len(content.encode('utf-8'))
        )

    async def _export_csv(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to CSV format."""
        output = io.StringIO()

        # Define columns
        columns = ['id', 'title', 'content', 'type', 'importance', 'created_at']
        if request.include_metadata:
            columns.extend(['tags', 'updated_at'])

        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        # Write memories
        for memory in memories:
            row = {
                'id': str(memory.id),
                'title': memory.title,
                'content': memory.content,
                'type': memory.memory_type.value,
                'importance': memory.importance,
                'created_at': memory.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            if request.include_metadata:
                row['tags'] = '|'.join(memory.tags) if memory.tags else ''
                row['updated_at'] = (
                    memory.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    if memory.updated_at else ''
                )

            writer.writerow(row)

        content = output.getvalue()

        return ExportResult(
            format=ExportFormat.CSV,
            content=content,
            file_size_bytes=len(content.encode('utf-8'))
        )

    async def _export_obsidian(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to Obsidian vault format."""
        # Create vault structure
        vault_content = {}

        # Group memories by tags/folders
        use_folders = request.format_options.get('use_folders', True)

        for memory in memories:
            # Determine folder
            if use_folders and memory.tags:
                folder = memory.tags[0]
            else:
                folder = memory.memory_type.value

            # Create Obsidian-compatible markdown
            content_parts = [f"# {memory.title}\n"]

            # Add frontmatter
            frontmatter = {
                'created': memory.created_at.strftime('%Y-%m-%d'),
                'type': memory.memory_type.value,
                'importance': memory.importance,
                'tags': memory.tags or []
            }

            content_parts.append("---")
            content_parts.append(yaml.dump(frontmatter, default_flow_style=False))
            content_parts.append("---\n")

            # Add content
            content_parts.append(memory.content)

            # Add backlinks
            if relationships:
                related = [
                    r for r in relationships
                    if r.source_memory_id == memory.id
                ]
                if related:
                    content_parts.append("\n## Related Notes\n")
                    for rel in related:
                        target = next(
                            (m for m in memories if m.id == rel.target_memory_id),
                            None
                        )
                        if target:
                            content_parts.append(f"- [[{target.title}]]")

            # Store in vault structure
            filename = f"{folder}/{memory.title}.md"
            vault_content[filename] = "\n".join(content_parts)

        # Create index file
        index_content = ["# Second Brain Index\n"]
        for folder in sorted(set(f.split('/')[0] for f in vault_content.keys())):
            index_content.append(f"\n## {folder.title()}\n")
            folder_files = [
                f for f in vault_content.keys()
                if f.startswith(f"{folder}/")
            ]
            for file in sorted(folder_files):
                title = file.split('/')[-1].replace('.md', '')
                index_content.append(f"- [[{title}]]")

        vault_content['_Index.md'] = "\n".join(index_content)

        # Convert to JSON for storage
        content = json.dumps(vault_content, indent=2)

        return ExportResult(
            format=ExportFormat.OBSIDIAN,
            content=content,
            file_size_bytes=len(content.encode('utf-8')),
            metadata={'file_count': len(vault_content)}
        )

    async def _export_roam(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to Roam Research format."""
        roam_data = []

        for memory in memories:
            # Create Roam page
            page = {
                "title": memory.title,
                "children": []
            }

            # Add metadata
            page["children"].append({
                "string": f"Type:: {memory.memory_type.value}"
            })
            page["children"].append({
                "string": f"Created:: {memory.created_at.strftime('%B %d, %Y')}"
            })
            page["children"].append({
                "string": f"Importance:: {memory.importance}/10"
            })

            if memory.tags:
                tags_str = " ".join(f"#{tag}" for tag in memory.tags)
                page["children"].append({
                    "string": f"Tags:: {tags_str}"
                })

            # Add content as blocks
            content_blocks = memory.content.split('\n\n')
            for block in content_blocks:
                if block.strip():
                    page["children"].append({
                        "string": block.strip()
                    })

            # Add references
            if relationships:
                related = [
                    r for r in relationships
                    if r.source_memory_id == memory.id
                ]
                if related:
                    ref_block = {
                        "string": "Related::",
                        "children": []
                    }
                    for rel in related:
                        target = next(
                            (m for m in memories if m.id == rel.target_memory_id),
                            None
                        )
                        if target:
                            ref_block["children"].append({
                                "string": f"[[{target.title}]] ({rel.relationship_type})"
                            })

                    page["children"].append(ref_block)

            roam_data.append(page)

        content = json.dumps(roam_data, indent=2)

        return ExportResult(
            format=ExportFormat.ROAM,
            content=content,
            file_size_bytes=len(content.encode('utf-8'))
        )

    async def _export_anki(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to Anki deck format."""
        # Create Anki deck structure
        deck_data = {
            "name": request.format_options.get('deck_name', 'Second Brain'),
            "cards": []
        }

        # Convert memories to flashcards
        for memory in memories:
            # Create basic card (front/back)
            if memory.memory_type == MemoryType.QUESTION:
                # Question memories become Q&A cards
                card = {
                    "front": memory.title,
                    "back": memory.content,
                    "tags": memory.tags or []
                }
            else:
                # Other memories become concept cards
                card = {
                    "front": f"What is {memory.title}?",
                    "back": memory.content,
                    "tags": memory.tags or []
                }

            deck_data["cards"].append(card)

            # Create reverse card if requested
            if request.format_options.get('create_reverse', False):
                reverse_card = {
                    "front": memory.content[:100] + "...",
                    "back": memory.title,
                    "tags": memory.tags or []
                }
                deck_data["cards"].append(reverse_card)

        content = json.dumps(deck_data, indent=2)

        return ExportResult(
            format=ExportFormat.ANKI,
            content=content,
            file_size_bytes=len(content.encode('utf-8')),
            metadata={'card_count': len(deck_data["cards"])}
        )

    async def _export_graphml(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to GraphML format."""
        # Create GraphML structure
        graphml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="title" for="node" attr.name="title" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="importance" for="node" attr.name="importance" attr.type="int"/>',
            '  <key id="reltype" for="edge" attr.name="relationship_type" attr.type="string"/>',
            '  <key id="strength" for="edge" attr.name="strength" attr.type="double"/>',
            '  <graph id="G" edgedefault="directed">'
        ]

        # Add nodes
        for memory in memories:
            graphml_parts.append(f'    <node id="{memory.id}">')
            graphml_parts.append(f'      <data key="title">{self._escape_xml(memory.title)}</data>')
            graphml_parts.append(f'      <data key="type">{memory.memory_type.value}</data>')
            graphml_parts.append(f'      <data key="importance">{memory.importance}</data>')
            graphml_parts.append('    </node>')

        # Add edges
        for i, rel in enumerate(relationships):
            graphml_parts.append(f'    <edge id="e{i}" source="{rel.source_memory_id}" target="{rel.target_memory_id}">')
            graphml_parts.append(f'      <data key="reltype">{rel.relationship_type}</data>')
            graphml_parts.append(f'      <data key="strength">{rel.strength}</data>')
            graphml_parts.append('    </edge>')

        graphml_parts.extend([
            '  </graph>',
            '</graphml>'
        ])

        content = '\n'.join(graphml_parts)

        return ExportResult(
            format=ExportFormat.GRAPHML,
            content=content,
            file_size_bytes=len(content.encode('utf-8'))
        )

    async def _export_pdf(
        self,
        memories: list[Memory],
        relationships: list[Any],
        request: ExportRequest
    ) -> ExportResult:
        """Export to PDF format."""
        # For PDF export, we would use a library like reportlab
        # For now, return a placeholder
        return ExportResult(
            format=ExportFormat.PDF,
            content="PDF export not implemented",
            file_size_bytes=0
        )

    # Import Handlers

    async def _import_json(self, request: ImportRequest) -> ImportResult:
        """Import from JSON format."""
        result = ImportResult(
            total_items=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_memory_ids=[],
            started_at=datetime.utcnow()
        )

        try:
            # Parse JSON
            data = json.loads(request.source)

            memories_data = data.get('memories', [])
            result.total_items = len(memories_data)

            # Import memories
            for memory_data in memories_data:
                try:
                    # Create memory
                    memory = Memory(
                        title=memory_data['title'],
                        content=memory_data['content'],
                        memory_type=MemoryType(memory_data.get('type', 'semantic')),
                        importance=memory_data.get('importance', 5),
                        tags=memory_data.get('tags', []),
                        user_id=request.user_id
                    )

                    # Check for duplicates if requested
                    if request.detect_duplicates:
                        existing = await self._check_duplicate(memory, request.user_id)
                        if existing:
                            result.skipped_count += 1
                            continue

                    # Create memory
                    created = await self.memory_service.create_memory(memory)
                    result.imported_memory_ids.append(created.id)
                    result.imported_count += 1

                except Exception as e:
                    result.error_count += 1
                    result.errors.append({
                        'item': memory_data.get('title', 'Unknown'),
                        'error': str(e)
                    })

        except Exception as e:
            result.errors.append({
                'item': 'JSON parsing',
                'error': str(e)
            })

        return result

    async def _import_csv(self, request: ImportRequest) -> ImportResult:
        """Import from CSV format."""
        result = ImportResult(
            total_items=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_memory_ids=[],
            started_at=datetime.utcnow()
        )

        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(request.source))
            rows = list(reader)
            result.total_items = len(rows)

            for row in rows:
                try:
                    # Map fields
                    field_mapping = request.field_mapping or {}

                    title = row.get(field_mapping.get('title', 'title'), '')
                    content = row.get(field_mapping.get('content', 'content'), '')
                    memory_type = row.get(field_mapping.get('type', 'type'), 'semantic')
                    importance = int(row.get(field_mapping.get('importance', 'importance'), 5))

                    # Parse tags
                    tags_str = row.get(field_mapping.get('tags', 'tags'), '')
                    tags = [t.strip() for t in tags_str.split('|')] if tags_str else []

                    # Add default tags
                    if request.default_tags:
                        tags.extend(request.default_tags)

                    # Create memory
                    memory = Memory(
                        title=title,
                        content=content,
                        memory_type=MemoryType(memory_type),
                        importance=importance,
                        tags=tags,
                        user_id=request.user_id
                    )

                    # Check for duplicates
                    if request.detect_duplicates:
                        existing = await self._check_duplicate(memory, request.user_id)
                        if existing:
                            result.skipped_count += 1
                            continue

                    # Create memory
                    created = await self.memory_service.create_memory(memory)
                    result.imported_memory_ids.append(created.id)
                    result.imported_count += 1

                except Exception as e:
                    result.error_count += 1
                    result.errors.append({
                        'item': row.get('title', 'Unknown'),
                        'error': str(e)
                    })

        except Exception as e:
            result.errors.append({
                'item': 'CSV parsing',
                'error': str(e)
            })

        return result

    async def _import_markdown(self, request: ImportRequest) -> ImportResult:
        """Import from Markdown format."""
        result = ImportResult(
            total_items=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_memory_ids=[],
            started_at=datetime.utcnow()
        )

        try:
            # Split by headers
            sections = request.source.split('\n## ')

            # Skip first section (usually metadata)
            memory_sections = sections[1:] if len(sections) > 1 else []
            result.total_items = len(memory_sections)

            for section in memory_sections:
                try:
                    lines = section.strip().split('\n')
                    if not lines:
                        continue

                    # Extract title (first line)
                    title = lines[0].strip()

                    # Extract metadata
                    content_start = 1
                    memory_type = 'semantic'
                    importance = 5
                    tags = []

                    for i, line in enumerate(lines[1:], 1):
                        if line.startswith('*Type:'):
                            memory_type = line.split(':')[1].strip().rstrip('*')
                        elif line.startswith('*Importance:'):
                            importance = int(line.split(':')[1].split('/')[0].strip().rstrip('*'))
                        elif line.startswith('*Tags:'):
                            tags_str = line.split(':')[1].strip().rstrip('*')
                            tags = [t.strip('#').strip() for t in tags_str.split(',')]
                        elif not line.startswith('*'):
                            content_start = i
                            break

                    # Extract content
                    content = '\n'.join(lines[content_start:]).strip()

                    # Create memory
                    memory = Memory(
                        title=title,
                        content=content,
                        memory_type=MemoryType(memory_type),
                        importance=importance,
                        tags=tags,
                        user_id=request.user_id
                    )

                    # Check for duplicates
                    if request.detect_duplicates:
                        existing = await self._check_duplicate(memory, request.user_id)
                        if existing:
                            result.skipped_count += 1
                            continue

                    # Create memory
                    created = await self.memory_service.create_memory(memory)
                    result.imported_memory_ids.append(created.id)
                    result.imported_count += 1

                except Exception as e:
                    result.error_count += 1
                    result.errors.append({
                        'item': title if 'title' in locals() else 'Unknown',
                        'error': str(e)
                    })

        except Exception as e:
            result.errors.append({
                'item': 'Markdown parsing',
                'error': str(e)
            })

        return result

    async def _import_obsidian(self, request: ImportRequest) -> ImportResult:
        """Import from Obsidian vault format."""
        # Similar to markdown but handle vault structure
        return await self._import_markdown(request)

    async def _import_roam(self, request: ImportRequest) -> ImportResult:
        """Import from Roam Research format."""
        result = ImportResult(
            total_items=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_memory_ids=[],
            started_at=datetime.utcnow()
        )

        try:
            # Parse Roam JSON
            pages = json.loads(request.source)
            result.total_items = len(pages)

            for page in pages:
                try:
                    title = page.get('title', '')

                    # Extract content from children
                    content_parts = []
                    metadata = {}

                    for child in page.get('children', []):
                        text = child.get('string', '')

                        # Parse metadata
                        if '::' in text:
                            key, value = text.split('::', 1)
                            metadata[key.strip()] = value.strip()
                        else:
                            content_parts.append(text)

                    # Create memory
                    memory = Memory(
                        title=title,
                        content='\n\n'.join(content_parts),
                        memory_type=MemoryType(metadata.get('Type', 'semantic')),
                        importance=int(metadata.get('Importance', '5').split('/')[0]),
                        tags=[t.strip('#') for t in metadata.get('Tags', '').split()],
                        user_id=request.user_id
                    )

                    # Check for duplicates
                    if request.detect_duplicates:
                        existing = await self._check_duplicate(memory, request.user_id)
                        if existing:
                            result.skipped_count += 1
                            continue

                    # Create memory
                    created = await self.memory_service.create_memory(memory)
                    result.imported_memory_ids.append(created.id)
                    result.imported_count += 1

                except Exception as e:
                    result.error_count += 1
                    result.errors.append({
                        'item': page.get('title', 'Unknown'),
                        'error': str(e)
                    })

        except Exception as e:
            result.errors.append({
                'item': 'Roam parsing',
                'error': str(e)
            })

        return result

    async def _import_anki(self, request: ImportRequest) -> ImportResult:
        """Import from Anki deck format."""
        result = ImportResult(
            total_items=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_memory_ids=[],
            started_at=datetime.utcnow()
        )

        try:
            # Parse Anki deck
            deck = json.loads(request.source)
            cards = deck.get('cards', [])
            result.total_items = len(cards)

            for card in cards:
                try:
                    # Convert card to memory
                    front = card.get('front', '')
                    back = card.get('back', '')
                    tags = card.get('tags', [])

                    # Determine title and content
                    if front.startswith('What is'):
                        # Concept card
                        title = front.replace('What is ', '').rstrip('?')
                        content = back
                        memory_type = 'semantic'
                    else:
                        # Q&A card
                        title = front
                        content = back
                        memory_type = 'question'

                    # Create memory
                    memory = Memory(
                        title=title,
                        content=content,
                        memory_type=MemoryType(memory_type),
                        importance=5,  # Default importance
                        tags=tags,
                        user_id=request.user_id
                    )

                    # Check for duplicates
                    if request.detect_duplicates:
                        existing = await self._check_duplicate(memory, request.user_id)
                        if existing:
                            result.skipped_count += 1
                            continue

                    # Create memory
                    created = await self.memory_service.create_memory(memory)
                    result.imported_memory_ids.append(created.id)
                    result.imported_count += 1

                except Exception as e:
                    result.error_count += 1
                    result.errors.append({
                        'item': card.get('front', 'Unknown'),
                        'error': str(e)
                    })

        except Exception as e:
            result.errors.append({
                'item': 'Anki parsing',
                'error': str(e)
            })

        return result

    async def _check_duplicate(
        self,
        memory: Memory,
        user_id: str
    ) -> Optional[Memory]:
        """Check if memory already exists."""
        # Search for similar title
        search_result = await self.memory_service.search_memories(
            query=memory.title,
            user_id=user_id,
            limit=10
        )

        if search_result and search_result.memories:
            for existing in search_result.memories:
                # Check exact title match
                if existing.title.lower() == memory.title.lower():
                    return existing

                # Check content similarity (simple check)
                if len(existing.content) > 100 and len(memory.content) > 100:
                    if existing.content[:100] == memory.content[:100]:
                        return existing

        return None

    def _escape_xml(self, text: str) -> str:
        """Escape special characters for XML."""
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        for char, escape in replacements.items():
            text = text.replace(char, escape)

        return text
