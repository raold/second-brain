"""
API routes for v2.8.2 Week 4 advanced synthesis features.

This module provides endpoints for memory synthesis, graph visualization,
workflows, and export/import operations.
"""

import io
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.models.synthesis.advanced_models import (
    ExportFormat,
    ExportRequest,
    GraphLayout,
    GraphVisualizationRequest,
    ImportRequest,
    ImportResult,
    KnowledgeGraph,
    SynthesisRequest,
    SynthesisStrategy,
    SynthesizedMemory,
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowTrigger,
)
from app.routes.auth import get_current_user
from app.services.synthesis.advanced_synthesis import AdvancedSynthesisEngine
from app.services.synthesis.export_import import ExportImportService
from app.services.synthesis.graph_visualization import GraphVisualizationService
from app.services.synthesis.workflow_automation import WorkflowAutomationService

router = APIRouter(prefix="/synthesis/advanced", tags=["Advanced Synthesis"])


def get_synthesis_engine() -> AdvancedSynthesisEngine:
    """Get synthesis engine service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_synthesis_engine()


def get_graph_service() -> GraphVisualizationService:
    """Get graph visualization service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_graph_service()


def get_workflow_service() -> WorkflowAutomationService:
    """Get workflow automation service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_workflow_service()


def get_export_import_service() -> ExportImportService:
    """Get export/import service."""
    from app.services.service_factory import get_service_factory
    factory = get_service_factory()
    return factory.get_export_import_service()


# Memory Synthesis Endpoints

@router.post("/synthesize", response_model=list[SynthesizedMemory])
async def synthesize_memories(
    request: SynthesisRequest,
    current_user: dict = Depends(get_current_user),
    synthesis_engine: AdvancedSynthesisEngine = Depends(get_synthesis_engine)
):
    """
    Synthesize memories using advanced strategies.

    Strategies:
    - hierarchical: Create hierarchical summaries
    - temporal: Synthesize along timeline
    - semantic: Group by semantic similarity
    - causal: Identify cause-effect relationships
    - comparative: Compare and contrast
    - abstractive: Extract high-level insights
    """
    try:
        # Set user ID if not provided
        if not request.user_id:
            request.user_id = current_user["user_id"]

        results = await synthesis_engine.synthesize_memories(request)
        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies", response_model=list[str])
async def list_synthesis_strategies(
    current_user: dict = Depends(get_current_user)
):
    """List available synthesis strategies."""
    return [strategy.value for strategy in SynthesisStrategy]


# Knowledge Graph Endpoints

@router.post("/graph/generate", response_model=KnowledgeGraph)
async def generate_knowledge_graph(
    request: GraphVisualizationRequest,
    current_user: dict = Depends(get_current_user),
    graph_service: GraphVisualizationService = Depends(get_graph_service)
):
    """
    Generate interactive knowledge graph visualization.

    Layout algorithms:
    - force_directed: Physics-based layout
    - hierarchical: Tree-like structure
    - circular: Nodes in circle
    - radial: Central node with layers
    - timeline: Temporal arrangement
    - clustered: Group by communities
    """
    try:
        # Set user ID
        request.user_id = current_user["user_id"]

        graph = await graph_service.generate_knowledge_graph(request)
        return graph

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/layouts", response_model=list[str])
async def list_graph_layouts(
    current_user: dict = Depends(get_current_user)
):
    """List available graph layout algorithms."""
    return [layout.value for layout in GraphLayout]


# Workflow Automation Endpoints

@router.post("/workflows", response_model=WorkflowDefinition)
async def create_workflow(
    workflow: WorkflowDefinition,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """
    Create automated workflow.

    Triggers:
    - schedule: Cron-based scheduling
    - event: Triggered by system events
    - threshold: Triggered by metric thresholds
    - manual: Manual execution only
    - chain: Triggered by other workflows
    """
    try:
        created = await workflow_service.create_workflow(workflow)
        return created

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows", response_model=list[WorkflowDefinition])
async def list_workflows(
    enabled_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """List all workflows."""
    try:
        workflows = await workflow_service.list_workflows(enabled_only)
        return workflows

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(
    workflow_id: UUID,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Get workflow by ID."""
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def update_workflow(
    workflow_id: UUID,
    updates: dict,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Update workflow configuration."""
    try:
        updated = await workflow_service.update_workflow(workflow_id, updates)
        return updated

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Delete a workflow."""
    try:
        success = await workflow_service.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {"success": True, "message": "Workflow deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecution)
async def execute_workflow(
    workflow_id: UUID,
    context: Optional[dict] = None,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Manually execute a workflow."""
    try:
        # Add user context
        if context is None:
            context = {}
        context["user_id"] = current_user["user_id"]

        execution = await workflow_service.execute_workflow(workflow_id, context)
        return execution

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/executions", response_model=list[WorkflowExecution])
async def list_workflow_executions(
    workflow_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """List workflow executions."""
    try:
        executions = await workflow_service.list_executions(
            workflow_id=workflow_id,
            status=status,
            limit=limit
        )
        return executions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/executions/{execution_id}", response_model=WorkflowExecution)
async def get_workflow_execution(
    execution_id: UUID,
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Get workflow execution details."""
    try:
        execution = await workflow_service.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return execution

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export/Import Endpoints

@router.post("/export")
async def export_knowledge(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user),
    export_service: ExportImportService = Depends(get_export_import_service)
):
    """
    Export knowledge base to various formats.

    Formats:
    - markdown: Human-readable markdown
    - json: Structured JSON
    - csv: Tabular format
    - obsidian: Obsidian vault
    - roam: Roam Research
    - anki: Anki flashcards
    - graphml: Graph format
    - pdf: PDF document
    """
    try:
        # Set user ID
        request.user_id = current_user["user_id"]

        result = await export_service.export_knowledge(request)

        # Return appropriate response based on format
        if request.format in [ExportFormat.PDF]:
            # For binary formats, return download
            return StreamingResponse(
                io.BytesIO(result.content.encode('utf-8')),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=export.{request.format.value}"
                }
            )
        else:
            # For text formats, return JSON with content
            return {
                "format": result.format.value,
                "content": result.content,
                "memory_count": result.memory_count,
                "relationship_count": result.relationship_count,
                "file_size_bytes": result.file_size_bytes,
                "created_at": result.created_at.isoformat()
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=ImportResult)
async def import_knowledge(
    request: ImportRequest,
    current_user: dict = Depends(get_current_user),
    import_service: ExportImportService = Depends(get_export_import_service)
):
    """Import knowledge from external sources."""
    try:
        # Set user ID
        request.user_id = current_user["user_id"]

        result = await import_service.import_knowledge(request)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/file")
async def import_knowledge_file(
    file: UploadFile = File(...),
    format: ExportFormat = Query(...),
    merge_strategy: str = Query("append"),
    detect_duplicates: bool = Query(True),
    current_user: dict = Depends(get_current_user),
    import_service: ExportImportService = Depends(get_export_import_service)
):
    """Import knowledge from uploaded file."""
    try:
        # Read file content
        content = await file.read()

        # Create import request
        request = ImportRequest(
            user_id=current_user["user_id"],
            format=format,
            source=content.decode('utf-8'),
            merge_strategy=merge_strategy,
            detect_duplicates=detect_duplicates
        )

        result = await import_service.import_knowledge(request)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/formats", response_model=list[str])
async def list_export_formats(
    current_user: dict = Depends(get_current_user)
):
    """List available export formats."""
    return [format.value for format in ExportFormat]


# Utility Endpoints

@router.get("/workflow/actions", response_model=list[str])
async def list_workflow_actions(
    current_user: dict = Depends(get_current_user)
):
    """List available workflow actions."""
    return [action.value for action in WorkflowAction]


@router.get("/workflow/triggers", response_model=list[str])
async def list_workflow_triggers(
    current_user: dict = Depends(get_current_user)
):
    """List available workflow triggers."""
    return [trigger.value for trigger in WorkflowTrigger]


@router.post("/scheduler/start")
async def start_workflow_scheduler(
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Start the workflow scheduler."""
    try:
        await workflow_service.start_scheduler()
        return {"success": True, "message": "Scheduler started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_workflow_scheduler(
    current_user: dict = Depends(get_current_user),
    workflow_service: WorkflowAutomationService = Depends(get_workflow_service)
):
    """Stop the workflow scheduler."""
    try:
        await workflow_service.stop_scheduler()
        return {"success": True, "message": "Scheduler stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
