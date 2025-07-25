"""
Integration tests for advanced synthesis API routes (v2.8.2 Week 4).

Tests the complete API endpoints for synthesis, graphs, workflows, and export/import.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.models.synthesis.advanced_models import (
    ExportFormat,
    WorkflowTrigger,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_services():
    """Mock all synthesis services."""
    with patch('app.routes.advanced_synthesis_routes.get_synthesis_engine') as mock_synthesis, \
         patch('app.routes.advanced_synthesis_routes.get_graph_service') as mock_graph, \
         patch('app.routes.advanced_synthesis_routes.get_workflow_service') as mock_workflow, \
         patch('app.routes.advanced_synthesis_routes.get_export_import_service') as mock_export, \
         patch('app.dependencies.get_current_user') as mock_user:

        # Setup mock user
        mock_user.return_value = {"user_id": "test_user"}

        # Setup service mocks
        synthesis_engine = AsyncMock()
        graph_service = AsyncMock()
        workflow_service = AsyncMock()
        export_service = AsyncMock()

        mock_synthesis.return_value = synthesis_engine
        mock_graph.return_value = graph_service
        mock_workflow.return_value = workflow_service
        mock_export.return_value = export_service

        yield {
            "synthesis": synthesis_engine,
            "graph": graph_service,
            "workflow": workflow_service,
            "export": export_service
        }


class TestSynthesisRoutes:
    """Test memory synthesis API endpoints."""

    def test_synthesize_memories(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/synthesize."""
        # Mock synthesis result
        mock_result = Mock()
        mock_result.id = uuid4()
        mock_result.source_memory_ids = [uuid4(), uuid4()]
        mock_result.synthesis_type = "hierarchical"
        mock_result.content = "Synthesized content"
        mock_result.confidence_score = 0.85
        mock_result.created_at = datetime.utcnow()

        mock_services["synthesis"].synthesize_memories.return_value = [mock_result]

        # Make request
        request_data = {
            "memory_ids": [str(uuid4()), str(uuid4())],
            "strategy": "hierarchical",
            "parameters": {"depth": 3}
        }

        response = client.post(
            "/synthesis/advanced/synthesize",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["synthesis_type"] == "hierarchical"
        assert data[0]["content"] == "Synthesized content"

    def test_list_strategies(self, client, auth_headers):
        """Test GET /synthesis/advanced/strategies."""
        response = client.get(
            "/synthesis/advanced/strategies",
            headers=auth_headers
        )

        assert response.status_code == 200
        strategies = response.json()
        assert "hierarchical" in strategies
        assert "temporal" in strategies
        assert "semantic" in strategies
        assert "causal" in strategies
        assert len(strategies) == 6  # All strategies


class TestGraphVisualizationRoutes:
    """Test knowledge graph API endpoints."""

    def test_generate_knowledge_graph(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/graph/generate."""
        # Mock graph result
        mock_graph = Mock()
        mock_graph.nodes = [
            Mock(
                id="node1",
                label="Node 1",
                x=0.5,
                y=0.5,
                type="memory",
                properties={"importance": 8},
                color="#4ECDC4"
            )
        ]
        mock_graph.edges = []
        mock_graph.metadata = {"layout": "force_directed"}
        mock_graph.clusters = None

        # Add method to calculate stats
        mock_graph.calculate_stats = Mock()

        mock_services["graph"].generate_knowledge_graph.return_value = mock_graph

        # Make request
        request_data = {
            "layout": "force_directed",
            "max_nodes": 50,
            "filters": {"min_importance": 5}
        }

        response = client.post(
            "/synthesis/advanced/graph/generate",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["metadata"]["layout"] == "force_directed"

    def test_list_graph_layouts(self, client, auth_headers):
        """Test GET /synthesis/advanced/graph/layouts."""
        response = client.get(
            "/synthesis/advanced/graph/layouts",
            headers=auth_headers
        )

        assert response.status_code == 200
        layouts = response.json()
        assert "force_directed" in layouts
        assert "hierarchical" in layouts
        assert "circular" in layouts
        assert len(layouts) == 6  # All layouts


class TestWorkflowRoutes:
    """Test workflow automation API endpoints."""

    def test_create_workflow(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/workflows."""
        # Mock created workflow
        workflow_id = uuid4()
        mock_workflow = Mock()
        mock_workflow.id = workflow_id
        mock_workflow.name = "Test Workflow"
        mock_workflow.description = "Test description"
        mock_workflow.trigger = WorkflowTrigger.MANUAL
        mock_workflow.actions = []
        mock_workflow.enabled = True
        mock_workflow.created_at = datetime.utcnow()
        mock_workflow.schedule = None
        mock_workflow.next_run = None
        mock_workflow.last_run = None
        mock_workflow.max_retries = 3

        mock_services["workflow"].create_workflow.return_value = mock_workflow

        # Make request
        workflow_data = {
            "name": "Test Workflow",
            "description": "Test description",
            "trigger": "manual",
            "actions": [
                {
                    "action": "synthesize",
                    "parameters": {"strategy": "semantic"}
                }
            ],
            "enabled": True
        }

        response = client.post(
            "/synthesis/advanced/workflows",
            json=workflow_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["trigger"] == "manual"

    def test_list_workflows(self, client, auth_headers, mock_services):
        """Test GET /synthesis/advanced/workflows."""
        mock_workflow = Mock()
        mock_workflow.id = uuid4()
        mock_workflow.name = "Daily Report"
        mock_workflow.enabled = True
        mock_workflow.trigger = WorkflowTrigger.SCHEDULE
        mock_workflow.actions = []
        mock_workflow.created_at = datetime.utcnow()
        mock_workflow.schedule = "0 0 * * *"
        mock_workflow.next_run = datetime.utcnow()
        mock_workflow.last_run = None
        mock_workflow.description = "Daily report generation"
        mock_workflow.max_retries = 3

        mock_services["workflow"].list_workflows.return_value = [mock_workflow]

        response = client.get(
            "/synthesis/advanced/workflows?enabled_only=true",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Daily Report"

    def test_execute_workflow(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/workflows/{id}/execute."""
        workflow_id = uuid4()
        execution_id = uuid4()

        mock_execution = Mock()
        mock_execution.id = execution_id
        mock_execution.workflow_id = workflow_id
        mock_execution.status = "running"
        mock_execution.started_at = datetime.utcnow()
        mock_execution.completed_at = None
        mock_execution.current_step = 0
        mock_execution.actions_completed = 0
        mock_execution.step_results = []
        mock_execution.error = None
        mock_execution.execution_time_ms = None

        mock_services["workflow"].execute_workflow.return_value = mock_execution

        response = client.post(
            f"/synthesis/advanced/workflows/{workflow_id}/execute",
            json={"context": {"test": "value"}},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == str(workflow_id)
        assert data["status"] == "running"


class TestExportImportRoutes:
    """Test export/import API endpoints."""

    def test_export_knowledge(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/export."""
        # Mock export result
        mock_result = Mock()
        mock_result.format = ExportFormat.JSON
        mock_result.content = json.dumps({
            "version": "2.8.2",
            "memories": []
        })
        mock_result.memory_count = 10
        mock_result.relationship_count = 5
        mock_result.file_size_bytes = 1024
        mock_result.created_at = datetime.utcnow()

        mock_services["export"].export_knowledge.return_value = mock_result

        # Make request
        export_request = {
            "format": "json",
            "include_metadata": True,
            "include_relationships": True
        }

        response = client.post(
            "/synthesis/advanced/export",
            json=export_request,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"
        assert data["memory_count"] == 10
        assert data["relationship_count"] == 5

    def test_import_knowledge(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/import."""
        # Mock import result
        mock_result = Mock()
        mock_result.total_items = 5
        mock_result.imported_count = 4
        mock_result.skipped_count = 1
        mock_result.error_count = 0
        mock_result.imported_memory_ids = [uuid4() for _ in range(4)]
        mock_result.started_at = datetime.utcnow()
        mock_result.duration_seconds = 2.5
        mock_result.errors = []

        mock_services["export"].import_knowledge.return_value = mock_result

        # Make request
        import_request = {
            "format": "json",
            "source": json.dumps({
                "version": "2.8.2",
                "memories": []
            }),
            "detect_duplicates": True,
            "merge_strategy": "append"
        }

        response = client.post(
            "/synthesis/advanced/import",
            json=import_request,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 4
        assert data["skipped_count"] == 1
        assert data["total_items"] == 5

    def test_list_export_formats(self, client, auth_headers):
        """Test GET /synthesis/advanced/export/formats."""
        response = client.get(
            "/synthesis/advanced/export/formats",
            headers=auth_headers
        )

        assert response.status_code == 200
        formats = response.json()
        assert "markdown" in formats
        assert "json" in formats
        assert "csv" in formats
        assert "obsidian" in formats
        assert len(formats) == 8  # All formats


class TestWorkflowUtilityRoutes:
    """Test workflow utility endpoints."""

    def test_list_workflow_actions(self, client, auth_headers):
        """Test GET /synthesis/advanced/workflow/actions."""
        response = client.get(
            "/synthesis/advanced/workflow/actions",
            headers=auth_headers
        )

        assert response.status_code == 200
        actions = response.json()
        assert "synthesize" in actions
        assert "analyze" in actions
        assert "generate_report" in actions

    def test_list_workflow_triggers(self, client, auth_headers):
        """Test GET /synthesis/advanced/workflow/triggers."""
        response = client.get(
            "/synthesis/advanced/workflow/triggers",
            headers=auth_headers
        )

        assert response.status_code == 200
        triggers = response.json()
        assert "schedule" in triggers
        assert "event" in triggers
        assert "manual" in triggers

    def test_start_scheduler(self, client, auth_headers, mock_services):
        """Test POST /synthesis/advanced/scheduler/start."""
        mock_services["workflow"].start_scheduler.return_value = None

        response = client.post(
            "/synthesis/advanced/scheduler/start",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "started" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
