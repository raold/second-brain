"""
Automated workflow system for v2.8.2 Week 4.

This service manages automated workflows for memory synthesis,
analysis, and maintenance tasks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

try:
    import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    croniter = None
    CRONITER_AVAILABLE = False
from enum import Enum

from app.database import Database
from app.models.synthesis.advanced_models import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStep,
    WorkflowTrigger,
)
from app.services.intelligence.analytics_dashboard import AnalyticsDashboardService
from app.services.synthesis.advanced_synthesis import AdvancedSynthesisEngine
from app.services.synthesis.report_generator import ReportGenerator as ReportGeneratorService

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowAutomationService:
    """Service for managing automated workflows."""

    def __init__(
        self,
        database: Database,
        synthesis_engine: AdvancedSynthesisEngine,
        report_service: ReportGeneratorService,
        analytics_service: AnalyticsDashboardService
    ):
        self.db = database
        self.synthesis_engine = synthesis_engine
        self.report_service = report_service
        self.analytics_service = analytics_service

        # Workflow storage (in production, use database)
        self.workflows: dict[UUID, WorkflowDefinition] = {}
        self.executions: dict[UUID, WorkflowExecution] = {}

        # Action handlers
        self.action_handlers = {
            WorkflowAction.SYNTHESIZE: self._action_synthesize,
            WorkflowAction.ANALYZE: self._action_analyze,
            WorkflowAction.EXPORT: self._action_export,
            WorkflowAction.NOTIFY: self._action_notify,
            WorkflowAction.ARCHIVE: self._action_archive,
            WorkflowAction.CONSOLIDATE: self._action_consolidate,
            WorkflowAction.GENERATE_REPORT: self._action_generate_report,
            WorkflowAction.UPDATE_GRAPH: self._action_update_graph
        }

        # Background tasks
        self._scheduler_task = None
        self._execution_tasks: dict[UUID, asyncio.Task] = {}

    async def create_workflow(
        self,
        workflow: WorkflowDefinition
    ) -> WorkflowDefinition:
        """Create a new workflow."""
        # Validate workflow
        self._validate_workflow(workflow)

        # Store workflow
        self.workflows[workflow.id] = workflow

        # Calculate next run if scheduled
        if workflow.trigger == WorkflowTrigger.SCHEDULE:
            workflow.next_run = self._calculate_next_run(workflow)

        logger.info(f"Created workflow: {workflow.name} ({workflow.id})")

        return workflow

    async def update_workflow(
        self,
        workflow_id: UUID,
        updates: dict[str, Any]
    ) -> WorkflowDefinition:
        """Update existing workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]

        # Apply updates
        for key, value in updates.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)

        # Recalculate next run if schedule changed
        if 'schedule' in updates and workflow.trigger == WorkflowTrigger.SCHEDULE:
            workflow.next_run = self._calculate_next_run(workflow)

        return workflow

    async def delete_workflow(self, workflow_id: UUID) -> bool:
        """Delete a workflow."""
        if workflow_id not in self.workflows:
            return False

        # Cancel any running executions
        if workflow_id in self._execution_tasks:
            self._execution_tasks[workflow_id].cancel()

        del self.workflows[workflow_id]

        logger.info(f"Deleted workflow: {workflow_id}")

        return True

    async def execute_workflow(
        self,
        workflow_id: UUID,
        context: Optional[dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING
        )

        self.executions[execution.id] = execution

        # Start execution in background
        task = asyncio.create_task(
            self._execute_workflow_async(workflow, execution, context)
        )
        self._execution_tasks[execution.id] = task

        return execution

    async def _execute_workflow_async(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        context: Optional[dict[str, Any]]
    ):
        """Execute workflow asynchronously."""
        try:
            logger.info(f"Starting workflow execution: {workflow.name}")

            # Initialize context
            if context is None:
                context = {}

            context['workflow_id'] = str(workflow.id)
            context['execution_id'] = str(execution.id)

            # Execute steps
            for i, step in enumerate(workflow.actions):
                execution.current_step = i

                # Check condition
                if step.condition and not self._evaluate_condition(
                    step.condition, context
                ):
                    logger.info(f"Skipping step {i} due to condition")
                    continue

                # Execute action
                try:
                    result = await self._execute_step(step, context)
                    execution.step_results.append({
                        'step': i,
                        'action': step.action.value,
                        'status': 'success',
                        'result': result
                    })
                    execution.actions_completed += 1

                    # Update context with result
                    context[f'step_{i}_result'] = result

                except Exception as e:
                    logger.error(f"Step {i} failed: {e}")
                    execution.step_results.append({
                        'step': i,
                        'action': step.action.value,
                        'status': 'failed',
                        'error': str(e)
                    })

                    if not step.retry_on_failure:
                        raise

                    # Retry logic
                    for retry in range(workflow.max_retries):
                        logger.info(f"Retrying step {i} (attempt {retry + 1})")
                        try:
                            result = await self._execute_step(step, context)
                            execution.step_results[-1]['status'] = 'success'
                            execution.step_results[-1]['result'] = result
                            execution.actions_completed += 1
                            context[f'step_{i}_result'] = result
                            break
                        except Exception as retry_error:
                            logger.error(f"Retry {retry + 1} failed: {retry_error}")
                            if retry == workflow.max_retries - 1:
                                raise

            # Mark as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.execution_time_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

            # Update workflow last run
            workflow.last_run = datetime.utcnow()
            if workflow.trigger == WorkflowTrigger.SCHEDULE:
                workflow.next_run = self._calculate_next_run(workflow)

            logger.info(f"Workflow execution completed: {workflow.name}")

        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.error = "Execution cancelled"
            raise

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Workflow execution failed: {e}")

        finally:
            # Clean up
            if execution.id in self._execution_tasks:
                del self._execution_tasks[execution.id]

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any]
    ) -> Any:
        """Execute a single workflow step."""
        handler = self.action_handlers.get(step.action)
        if not handler:
            raise ValueError(f"Unknown action: {step.action}")

        # Merge step parameters with context
        params = {**context, **step.parameters}

        return await handler(params)

    # Action Handlers

    async def _action_synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute synthesis action."""
        from app.models.synthesis.advanced_models import SynthesisRequest, SynthesisStrategy

        # Extract parameters
        memory_ids = params.get('memory_ids', [])
        strategy = params.get('strategy', SynthesisStrategy.SEMANTIC)
        user_id = params['user_id']

        # Create synthesis request
        request = SynthesisRequest(
            memory_ids=[UUID(id) for id in memory_ids],
            strategy=strategy,
            user_id=user_id,
            parameters=params.get('synthesis_params', {})
        )

        # Execute synthesis
        results = await self.synthesis_engine.synthesize_memories(request)

        return {
            'synthesized_count': len(results),
            'synthesized_ids': [str(r.id) for r in results]
        }

    async def _action_analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute analysis action."""
        from app.models.intelligence.analytics_models import AnalyticsQuery, TimeGranularity

        # Create analytics query
        query = AnalyticsQuery(
            user_id=params['user_id'],
            granularity=params.get('granularity', TimeGranularity.DAY),
            include_insights=params.get('include_insights', True),
            include_anomalies=params.get('include_anomalies', True)
        )

        # Generate dashboard
        dashboard = await self.analytics_service.generate_dashboard(query)

        return {
            'metrics_count': len(dashboard.metrics),
            'insights_count': len(dashboard.insights),
            'anomalies_count': len(dashboard.anomalies),
            'system_health': dashboard.system_health_score
        }

    async def _action_generate_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute report generation action."""
        from app.models.synthesis.report_models import ReportFormat, ReportRequest, ReportType

        # Create report request
        request = ReportRequest(
            report_type=params.get('report_type', ReportType.WEEKLY),
            format=params.get('format', ReportFormat.PDF),
            user_id=params['user_id'],
            include_visualizations=params.get('include_visualizations', True)
        )

        # Generate report
        report = await self.report_service.generate_report(
            params['user_id'], request
        )

        return {
            'report_id': str(report.id),
            'report_url': report.download_url,
            'pages': report.metadata.get('page_count', 0)
        }

    async def _action_export(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute export action."""
        # Export implementation
        format = params.get('format', 'json')
        memory_ids = params.get('memory_ids', [])

        logger.info(f"Exporting {len(memory_ids)} memories to {format}")

        return {
            'exported_count': len(memory_ids),
            'format': format,
            'file_path': f"/exports/export_{datetime.utcnow().timestamp()}.{format}"
        }

    async def _action_notify(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute notification action."""
        # Notification implementation
        message = params.get('message', 'Workflow completed')
        channels = params.get('channels', ['email'])

        logger.info(f"Sending notification: {message}")

        return {
            'notified': True,
            'channels': channels,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def _action_archive(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute archive action."""
        # Archive old memories
        days_old = params.get('days_old', 365)

        logger.info(f"Archiving memories older than {days_old} days")

        return {
            'archived_count': 0,  # Placeholder
            'archive_date': datetime.utcnow().isoformat()
        }

    async def _action_consolidate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute consolidation action."""
        # Consolidate similar memories
        threshold = params.get('similarity_threshold', 0.8)

        logger.info(f"Consolidating memories with similarity > {threshold}")

        return {
            'consolidated_count': 0,  # Placeholder
            'groups_created': 0
        }

    async def _action_update_graph(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute graph update action."""
        # Update knowledge graph
        logger.info("Updating knowledge graph")

        return {
            'nodes_added': 0,  # Placeholder
            'edges_added': 0,
            'graph_density': 0.0
        }

    # Scheduling Methods

    async def start_scheduler(self):
        """Start the workflow scheduler."""
        if self._scheduler_task:
            return

        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Workflow scheduler started")

    async def stop_scheduler(self):
        """Stop the workflow scheduler."""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

        # Cancel all running executions
        for task in self._execution_tasks.values():
            task.cancel()

        logger.info("Workflow scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while True:
            try:
                # Check scheduled workflows
                now = datetime.utcnow()

                for workflow in self.workflows.values():
                    if (workflow.enabled and
                        workflow.trigger == WorkflowTrigger.SCHEDULE and
                        workflow.next_run and
                        workflow.next_run <= now):

                        logger.info(f"Triggering scheduled workflow: {workflow.name}")

                        # Execute workflow
                        await self.execute_workflow(workflow.id)

                        # Update next run
                        workflow.next_run = self._calculate_next_run(workflow)

                # Sleep for a minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    def _calculate_next_run(self, workflow: WorkflowDefinition) -> Optional[datetime]:
        """Calculate next run time for scheduled workflow."""
        if not workflow.schedule:
            return None

        try:
            # Use croniter to parse cron expression
            base_time = workflow.last_run or datetime.utcnow()
            cron = croniter.croniter(workflow.schedule, base_time)
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Invalid cron expression: {workflow.schedule} - {e}")
            return None

    def _validate_workflow(self, workflow: WorkflowDefinition):
        """Validate workflow definition."""
        if not workflow.name:
            raise ValueError("Workflow name is required")

        if not workflow.actions:
            raise ValueError("Workflow must have at least one action")

        if workflow.trigger == WorkflowTrigger.SCHEDULE and not workflow.schedule:
            raise ValueError("Schedule is required for scheduled workflows")

        # Validate actions
        for i, step in enumerate(workflow.actions):
            if step.action not in WorkflowAction:
                raise ValueError(f"Unknown action in step {i}: {step.action}")

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate step condition."""
        try:
            # Simple evaluation (in production, use safe expression evaluator)
            # For now, just check for basic conditions
            if 'step_' in condition:
                # Check previous step results
                return True  # Placeholder

            return True

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    # Query Methods

    async def get_workflow(self, workflow_id: UUID) -> Optional[WorkflowDefinition]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)

    async def list_workflows(
        self,
        enabled_only: bool = False
    ) -> list[WorkflowDefinition]:
        """List all workflows."""
        workflows = list(self.workflows.values())

        if enabled_only:
            workflows = [w for w in workflows if w.enabled]

        return workflows

    async def get_execution(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """Get execution by ID."""
        return self.executions.get(execution_id)

    async def list_executions(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100
    ) -> list[WorkflowExecution]:
        """List workflow executions."""
        executions = list(self.executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        # Sort by start time (newest first)
        executions.sort(key=lambda e: e.started_at, reverse=True)

        return executions[:limit]
