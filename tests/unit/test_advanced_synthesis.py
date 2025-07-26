"""
Unit tests for advanced synthesis features (v2.8.2 Week 4).

Tests cover memory synthesis, graph visualization, workflows, and export/import.
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.memory import Memory, MemoryType
from app.models.synthesis.advanced_models import (
    ExportFormat,
    ExportRequest,
    GraphLayout,
    GraphVisualizationRequest,
    ImportRequest,
    KnowledgeGraph,
    SynthesisRequest,
    SynthesisStrategy,
    WorkflowAction,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTrigger,
)
from app.services.synthesis.advanced_synthesis import AdvancedSynthesisEngine
from app.services.synthesis.export_import import ExportImportService
from app.services.synthesis.graph_visualization import GraphVisualizationService
from app.services.synthesis.workflow_automation import WorkflowAutomationService


class TestAdvancedSynthesisEngine:
    """Test advanced memory synthesis engine."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db = AsyncMock()
        memory_service = AsyncMock()
        relationship_analyzer = AsyncMock()
        openai_client = AsyncMock()

        return db, memory_service, relationship_analyzer, openai_client

    @pytest.fixture
    def synthesis_engine(self, mock_dependencies):
        """Create synthesis engine with mocks."""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies
        return AdvancedSynthesisEngine(db, memory_service, relationship_analyzer, openai_client)

    @pytest.mark.asyncio
    async def test_hierarchical_synthesis(self, synthesis_engine, mock_dependencies):
        """Test hierarchical synthesis strategy."""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies

        # Mock memories
        memories = [
            Memory(
                id=str(uuid4()),
                content="Python Basics: Variables and data types",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.7,
                user_id="test_user",
                tags=["python", "basics"],
                created_at=datetime.utcnow()
            ),
            Memory(
                id=str(uuid4()),
                content="Python Functions: def keyword and parameters",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.8,
                user_id="test_user",
                tags=["python", "functions"],
                created_at=datetime.utcnow()
            )
        ]

        memory_service.get_memories_by_ids.return_value = memories
        relationship_analyzer.find_related_memories.return_value = []
        openai_client.generate_embedding.return_value = [0.1] * 1536
        openai_client.generate_completion.return_value = "Python Programming: A comprehensive overview"

        # Create request
        request = SynthesisRequest(
            memory_ids=[m.id for m in memories],
            strategy=SynthesisStrategy.SUMMARY,
            user_id="test_user"
        )

        # Execute synthesis
        results = await synthesis_engine.synthesize_memories(request)

        # Verify results
        assert len(results) > 0
        assert results[0].synthesis_type == "summary"
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_temporal_synthesis(self, synthesis_engine, mock_dependencies):
        """Test temporal synthesis strategy."""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies

        # Mock memories with time sequence
        base_time = datetime.utcnow()
        memories = [
            Memory(
                id=str(uuid4()),
                content=f"Event {i}: Event {i} happened",
                memory_type=MemoryType.EPISODIC,
                importance_score=0.5,
                user_id="test_user",
                created_at=base_time + timedelta(hours=i),
                tags=[f"event{i}"]
            )
            for i in range(3)
        ]

        memory_service.get_memories_by_ids.return_value = memories
        openai_client.generate_embedding.return_value = [0.1] * 1536
        openai_client.generate_completion.return_value = "Timeline: Events occurred in sequence"

        request = SynthesisRequest(
            memory_ids=[m.id for m in memories],
            strategy=SynthesisStrategy.TIMELINE,
            user_id="test_user"
        )

        results = await synthesis_engine.synthesize_memories(request)

        assert len(results) > 0
        assert results[0].synthesis_type == "timeline"

    @pytest.mark.asyncio
    async def test_causal_synthesis(self, synthesis_engine, mock_dependencies):
        """Test causal relationship synthesis."""
        db, memory_service, relationship_analyzer, openai_client = mock_dependencies

        memories = [
            Memory(
                id=str(uuid4()),
                content="Cause: Heavy rain",
                memory_type=MemoryType.EPISODIC,
                importance_score=0.6,
                user_id="test_user",
                tags=["cause", "weather"]
            ),
            Memory(
                id=str(uuid4()),
                content="Effect: Flooding occurred",
                memory_type=MemoryType.EPISODIC,
                importance_score=0.8,
                user_id="test_user",
                tags=["effect", "weather"]
            )
        ]

        memory_service.get_memories_by_ids.return_value = memories
        openai_client.generate_embedding.return_value = [0.1] * 1536
        openai_client.generate_completion.return_value = "Causal chain: Rain → Flooding"

        request = SynthesisRequest(
            memory_ids=[m.id for m in memories],
            strategy=SynthesisStrategy.ANALYSIS,
            user_id="test_user"
        )

        results = await synthesis_engine.synthesize_memories(request)

        assert len(results) > 0
        assert results[0].synthesis_type == "analysis"


class TestGraphVisualizationService:
    """Test knowledge graph visualization service."""

    @pytest.fixture
    def graph_service(self):
        """Create graph service with mocks."""
        db = AsyncMock()
        memory_service = AsyncMock()
        relationship_analyzer = AsyncMock()

        return GraphVisualizationService(db, memory_service, relationship_analyzer)

    @pytest.mark.asyncio
    async def test_force_directed_layout(self, graph_service):
        """Test force-directed graph layout."""
        # Mock memories
        memories = [
            Memory(
                id=str(uuid4()),
                title=f"Node {i}",
                content=f"Content {i}",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.5,
                user_id="test_user"
            )
            for i in range(3)
        ]

        # Mock search results
        mock_search_result = Mock()
        mock_search_result.memories = memories
        graph_service.memory_service.search_memories.return_value = mock_search_result

        # Mock relationships
        graph_service.relationship_analyzer.find_related_memories.return_value = []

        # Create request
        request = GraphVisualizationRequest(
            user_id="test_user",
            layout=GraphLayout.FORCE_DIRECTED,
            max_nodes=10
        )

        # Generate graph
        with patch('networkx.spring_layout') as mock_layout:
            mock_layout.return_value = {
                str(m.id): (i * 0.5, i * 0.3)
                for i, m in enumerate(memories)
            }

            graph = await graph_service.generate_knowledge_graph(request)

        # Verify graph structure
        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) == 3
        assert all(node.x is not None for node in graph.nodes)
        assert all(node.y is not None for node in graph.nodes)

    @pytest.mark.asyncio
    async def test_hierarchical_layout(self, graph_service):
        """Test hierarchical graph layout."""
        memories = [
            Memory(
                id=str(uuid4()),
                
                content="Root: Root node",
                memory_type=MemoryType.SEMANTIC,
                importance_score=1.0,
                user_id="test_user"
,
                tags=["root"]
            ),
            Memory(
                id=str(uuid4()),
                
                content="Child: Child node",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.7,
                user_id="test_user"
,
                tags=["child"]
            )
        ]

        mock_search_result = Mock()
        mock_search_result.memories = memories
        graph_service.memory_service.search_memories.return_value = mock_search_result
        graph_service.relationship_analyzer.find_related_memories.return_value = []

        request = GraphVisualizationRequest(
            user_id="test_user",
            layout=GraphLayout.HIERARCHICAL,
            max_nodes=10
        )

        graph = await graph_service.generate_knowledge_graph(request)

        assert len(graph.nodes) == 2
        assert graph.metadata["layout"] == "hierarchical"

    @pytest.mark.asyncio
    async def test_graph_filtering(self, graph_service):
        """Test graph filtering by tags and importance."""
        memories = [
            Memory(
                id=str(uuid4()),
                
                content="Important: Very important",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.9,
                tags=["critical"],
                user_id="test_user"
            ),
            Memory(
                id=str(uuid4()),
                
                content="Less Important: Not as important",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.3,
                tags=["optional"],
                user_id="test_user"
            )
        ]

        mock_search_result = Mock()
        mock_search_result.memories = memories
        graph_service.memory_service.search_memories.return_value = mock_search_result
        graph_service.relationship_analyzer.find_related_memories.return_value = []

        request = GraphVisualizationRequest(
            user_id="test_user",
            layout=GraphLayout.FORCE_DIRECTED,
            filters={
                "tags": ["critical"],
                "min_importance": 5
            },
            max_nodes=10
        )

        # Mock NetworkX layout
        with patch('networkx.spring_layout') as mock_layout:
            mock_layout.return_value = {str(memories[0].id): (0.5, 0.5)}
            graph = await graph_service.generate_knowledge_graph(request)

        # Only high importance memory with "critical" tag should be included
        assert len(graph.nodes) == 1
        assert graph.nodes[0].properties["importance"] == 9


class TestWorkflowAutomationService:
    """Test workflow automation service."""

    @pytest.fixture
    def workflow_service(self):
        """Create workflow service with mocks."""
        db = AsyncMock()
        synthesis_engine = AsyncMock()
        report_service = AsyncMock()
        analytics_service = AsyncMock()

        return WorkflowAutomationService(db, synthesis_engine, report_service, analytics_service)

    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_service):
        """Test workflow creation."""
        workflow = WorkflowDefinition(
            name="Test Workflow",
            description="Test workflow",
            trigger=WorkflowTrigger.MANUAL,
            actions=[
                WorkflowStep(
                    action=WorkflowAction.SYNTHESIZE,
                    parameters={"strategy": "semantic"}
                )
            ],
            enabled=True
        )

        created = await workflow_service.create_workflow(workflow)

        assert created.id == workflow.id
        assert created.name == "Test Workflow"
        assert workflow.id in workflow_service.workflows

    @pytest.mark.asyncio
    async def test_execute_workflow(self, workflow_service):
        """Test workflow execution."""
        # Create workflow
        workflow = WorkflowDefinition(
            name="Synthesis Workflow",
            trigger=WorkflowTrigger.MANUAL,
            actions=[
                WorkflowStep(
                    action=WorkflowAction.SYNTHESIZE,
                    parameters={
                        "memory_ids": [],
                        "strategy": "semantic",
                        "user_id": "test_user"
                    }
                )
            ]
        )

        await workflow_service.create_workflow(workflow)

        # Mock synthesis result
        workflow_service.synthesis_engine.synthesize_memories.return_value = [
            Mock(id=uuid4())
        ]

        # Execute workflow
        execution = await workflow_service.execute_workflow(
            workflow.id,
            context={"user_id": "test_user"}
        )

        # Wait for async execution to complete
        await asyncio.sleep(0.1)

        assert execution.workflow_id == workflow.id
        assert execution.id in workflow_service.executions

    @pytest.mark.asyncio
    async def test_scheduled_workflow(self, workflow_service):
        """Test scheduled workflow with cron trigger."""
        workflow = WorkflowDefinition(
            name="Daily Synthesis",
            trigger=WorkflowTrigger.SCHEDULED,
            schedule="0 0 * * *",  # Daily at midnight
            actions=[
                WorkflowStep(
                    action=WorkflowAction.EXPORT,
                    parameters={"report_type": "daily"}
                )
            ]
        )

        created = await workflow_service.create_workflow(workflow)

        assert created.next_run is not None
        assert created.schedule == "0 0 * * *"


class TestExportImportService:
    """Test export/import service."""

    @pytest.fixture
    def export_service(self):
        """Create export service with mocks."""
        db = AsyncMock()
        memory_service = AsyncMock()
        relationship_analyzer = AsyncMock()

        return ExportImportService(db, memory_service, relationship_analyzer)

    @pytest.mark.asyncio
    async def test_export_markdown(self, export_service):
        """Test export to Markdown format."""
        memories = [
            Memory(
                id=str(uuid4()),
                
                content="Test Memory: Test content",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.7,
                tags=["test"],
                user_id="test_user"
            )
        ]

        # Mock memory fetching
        export_service.memory_service.get_memory.return_value = memories[0]
        mock_search_result = Mock()
        mock_search_result.memories = memories
        export_service.memory_service.search_memories.return_value = mock_search_result
        export_service.relationship_analyzer.find_related_memories.return_value = []

        request = ExportRequest(
            user_id="test_user",
            format=ExportFormat.MARKDOWN,
            include_metadata=True
        )

        result = await export_service.export_knowledge(request)

        assert result.format == ExportFormat.MARKDOWN
        assert "# Second Brain Export" in result.content
        assert "Test Memory" in result.content
        assert result.memory_count == 1

    @pytest.mark.asyncio
    async def test_export_json(self, export_service):
        """Test export to JSON format."""
        memory = Memory(
            id=str(uuid4()),
            content="JSON Test: JSON content",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.5,
            user_id="test_user",
            tags=["json_test"]
        )

        mock_search_result = Mock()
        mock_search_result.memories = [memory]
        export_service.memory_service.search_memories.return_value = mock_search_result
        export_service.relationship_analyzer.find_related_memories.return_value = []

        request = ExportRequest(
            user_id="test_user",
            format=ExportFormat.JSON
        )

        result = await export_service.export_knowledge(request)

        assert result.format == ExportFormat.JSON
        exported_data = json.loads(result.content)
        assert exported_data["version"] == "2.8.2"
        assert len(exported_data["memories"]) == 1
        assert exported_data["memories"][0]["title"] == "JSON Test"

    @pytest.mark.asyncio
    async def test_import_json(self, export_service):
        """Test import from JSON format."""
        import_data = {
            "version": "2.8.2",
            "memories": [
                {
                    "title": "Imported Memory",
                    "content": "Imported content",
                    "type": "semantic",
                    "importance": 6,
                    "tags": ["imported"]
                }
            ]
        }

        # Mock duplicate check
        mock_search_result = Mock()
        mock_search_result.memories = []
        export_service.memory_service.search_memories.return_value = mock_search_result

        # Mock memory creation
        created_memory = Memory(
            id=str(uuid4()),
            content="Imported Memory: Imported content",
            memory_type=MemoryType.SEMANTIC,
            importance_score=0.6,
            tags=["imported"],
            user_id="test_user"
        )
        export_service.memory_service.create_memory.return_value = created_memory

        request = ImportRequest(
            user_id="test_user",
            format=ExportFormat.JSON,
            source=json.dumps(import_data),
            detect_duplicates=True
        )

        result = await export_service.import_knowledge(request)

        assert result.imported_count == 1
        assert result.skipped_count == 0
        assert len(result.imported_memory_ids) == 1

    @pytest.mark.asyncio
    async def test_export_obsidian(self, export_service):
        """Test export to Obsidian vault format."""
        memories = [
            Memory(
                id=str(uuid4()),
                
                content="Obsidian Note: Note content with [[links]]",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.8,
                tags=["obsidian", "pkm"],
                user_id="test_user"
            )
        ]

        mock_search_result = Mock()
        mock_search_result.memories = memories
        export_service.memory_service.search_memories.return_value = mock_search_result
        export_service.relationship_analyzer.find_related_memories.return_value = []

        request = ExportRequest(
            user_id="test_user",
            format=ExportFormat.OBSIDIAN,
            format_options={"use_folders": True}
        )

        result = await export_service.export_knowledge(request)

        assert result.format == ExportFormat.OBSIDIAN
        vault_data = json.loads(result.content)
        assert "obsidian/Obsidian Note.md" in vault_data
        assert "_Index.md" in vault_data


@pytest.mark.asyncio
async def test_full_synthesis_workflow():
    """Test complete synthesis workflow from request to result."""
    # This would be an integration test combining all components
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
